# STATE.md — Current Project State

Last updated: 2026-03-12 (session 50)

## Last Session (Session 50)

### Phase 1: Lulesh MPI Rebuild + Recalibration

Rebuilt pristine Lulesh binary on compute node with MPI support. **Key discovery**: previous "51-52s" Lulesh timing was fake — the non-MPI binary had ranks running independently with no communication. Real MPI timing at i=5000 was ~131s.

- Pristine binary now links `libmpi.so.40` (997KB vs old 659KB)
- Recalibrated: i=5000→i=2000 for ~52.5s internal / ~63s wall target
- Added `OMPI_MCA_btl=^smcuda` to fix OpenMPI 5.0.7 + CUDA finalization segfault
- Harness validated: CORRECTNESS PASSED, nsys profiling works, ncu needs dcgmi pause (handled by wrappers)

### Phase 2: QS Profiling Patch Analysis (Goal 18 from s49)

Compared QS with-profiling (1.65x) vs no-profiling (1.02x) patches. **The bottleneck was NOT GPU kernels — it was CPU-side vault iteration overhead.**

- GPU kernel (`CycleTrackingKernel`) only ~1.06s of 59.5s total (< 2% of runtime)
- No-profiling agent spent entire session on GPU micro-opts (sincos, rsqrt, restrict) — wrong 2%
- With-profiling agent saw nsys data: 195 GPU kernel launches vs 77,419 timer calls → 99.7% empty vaults
- Fix: consolidated all particles into single batch (2-line change, +20/-16 lines)
- **Textbook Amdahl's Law**: profiling gave correct mental model, source-code-only missed it entirely

### Phase 3: Pre-Flight Validation (all 4 framework+model combos)

Ran code review agents for each framework before submission:

| Framework + Model | Status | Issues Found & Fixed |
|---|---|---|
| Codex + gpt-5.3-codex | PASS | SAFE_MODEL naming fix (output dir used wrong model name) |
| SWE-agent + Qwen3-Coder-Next | PASS | No issues, xml_function_calling auto-applied correctly |
| OpenHands + Qwen3-Coder-Next | PASS (was MEDIUM risk) | Added "qwen" + "gpt-oss" to FORCE_STRING_SERIALIZER_PATTERNS |
| Claude Code + GPA | PASS | lavaMD `.lower()` fix, profiling prompt expanded |

### Phase 4: GPA Build Failure Investigation + Fixes

Investigated all 6 GPA app build failures. All fixable:

| App | Root Cause | Fix Applied |
|---|---|---|
| exatensor, xsbench, srad | Bare `nvcc` resolves to CUDA 12.4 (rejects gcc14) | PATH fix in driver's `setup_app_config()` |
| b+tree, backprop | K&R C code + gcc 14 strict mode | `-Wno-implicit-int -Wno-implicit-function-declaration` flags |
| lavaMD | Case-sensitivity in `run_all()` filter | `.lower()` on DriverConfig app name |
| srad (additional) | Hardcoded bare `nvcc` in compile step | Changed to `$(CC)` |

GPA-Benchmark commits: `dd38308` (5 build fixes)

### Phase 5: Profiling Prompt Improvements

- `PROFILING_DESCRIPTION`: Added `microbench_code`, `check_profiling_ready`, `system_summary` (was 7 tools, now 10)
- GPA profiling prompt: Added all profiling tools + guidance on how to profile GPA apps (binary is built by gpa_test internally)
- SWE-agent instance hint: Updated profiling_tools string to include new tools

### Phase 6: Job Submissions (10 jobs)

| Job ID | Framework | Model | Apps | Status | Duration |
|--------|-----------|-------|------|--------|----------|
| 49936642 | Codex | gpt-5.3-codex | LLNL | COMPLETED | 01:28:56 |
| 49936643 | SWE-agent | Qwen3-Coder-Next | LLNL | COMPLETED | 00:10:34 (likely crashed) |
| 49936644 | SWE-agent | Qwen3-Coder-Next | GPA | TIMEOUT | 04:00:23 |
| 49936645 | OpenHands | Qwen3-Coder-Next | LLNL | COMPLETED | 02:16:26 |
| 49936646 | OpenHands | Qwen3-Coder-Next | GPA | TIMEOUT | 04:00:24 |
| 49936647 | OpenHands | gptoss120b | GPA | FAILED | 00:04:09 |
| 49936648 | SWE-agent | gptoss120b | GPA | FAILED | 00:04:27 |
| 49936649 | OpenCode | gptoss120b | GPA | FAILED | 00:03:25 |
| 49940919 | Claude Code | Anthropic | LLNL | COMPLETED | 01:06:15 |
| 49940920 | Claude Code | Anthropic | GPA | TIMEOUT | 04:00:00 |

**Immediate issues**: gptoss120b jobs all failed in ~4 min (likely vLLM startup or model loading issue). SWE-agent+Qwen LLNL completed in 10 min (probably crashed early). Need to analyze logs next session.

## Active Experiments

### Session 50 — All 10 Jobs Completed/Failed

Results need analysis next session. Key questions:
1. Why did all 3 gptoss120b jobs fail in ~4 min?
2. Why did SWE-agent+Qwen LLNL finish in only 10 min?
3. Did Codex + gpt-5.3-codex produce valid results? (first successful Codex run)
4. Did OpenHands + Qwen produce any edits? (first OpenHands+Qwen test)
5. Did Lulesh work correctly with MPI fix across all frameworks?
6. Claude Code LLNL — any Lulesh improvement over s48?
7. Claude Code GPA — did the 5 build fixes help?

### Scheduled Claude Code Jobs (via nohup+sleep)
- PID 2080497 — submitted Claude Code LLNL + GPA 3 hours after session start
- Jobs 49940919 (LLNL, COMPLETED) and 49940920 (GPA, TIMEOUT) — need log analysis

## Validated LLNL App Timings (4x A100)

| App | np | Parameters | Time | Correctness |
|-----|-----|-----------|------|-------------|
| Kripke | 4 | zones=64³, groups=64, niter=60, quad=8 | 51-55s | PASSED |
| Laghos | 4 | p1, dim=2, rs=4, tf=0.8, -pa -d cuda | 67s | PASSED |
| Lulesh | 8 | s=150, i=2000 | ~63s | PASSED (MPI rebuilt s50) |
| QS | 4 | Coral2_P2_4.inp, nSteps=67 | 60s | PASSED |

## Available Models

| Model | Cached | Size | TP | GPU Mem | Parser | Status |
|-------|--------|------|-----|---------|--------|--------|
| Qwen/Qwen3-Coder-Next-FP8 | Yes | 80GB | 4 | 0.70 | qwen3_coder | SWE-agent paralysis; OpenHands untested |
| Qwen/Qwen3.5-27B-FP8 | Yes | 31GB | 4 | 0.60 | qwen3_coder | Not tested |
| Qwen/Qwen3.5-122B-A10B-FP8 | Yes | 127GB | 4 | 0.92 | qwen3_coder | Not tested |
| openai/gpt-oss-120b | Yes | ~120GB | 4 | 0.92 | (default) | s50 GPA jobs failed in ~4 min |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `da0d04e4` — WIP: Session 50

## Infrastructure Bugs Found

| Bug | Severity | Status |
|-----|----------|--------|
| Lulesh pristine binary lacks MPI | CRITICAL | **FIXED+REBUILT** (s50) — i=2000, btl fix |
| Codex OPENAI_BASE_URL config crash | CRITICAL | **FIXED** (s49) — bridge env var |
| GPA retain_nsys_profiles kwarg | CRITICAL | **FIXED** (s49) — committed in GPA-Benchmark |
| GPA 5 app build failures | HIGH | **FIXED** (s50) — PATH, K&R flags, srad, lavaMD |
| OpenHands structured content crash | HIGH | **FIXED** (s50) — FORCE_STRING_SERIALIZER for qwen+gpt-oss |
| SAFE_MODEL naming wrong model | LOW | **FIXED** (s50) — use MODEL_NAME when available |
| Profiling prompt missing tools | MEDIUM | **FIXED** (s50) — added microbench_code, check_profiling_ready, system_summary |
| OpenCode exits after 1 step (Qwen XML) | HIGH | Open — Qwen tool_call XML not parsed by OpenCode |
| SWE-agent+Qwen analysis paralysis | HIGH | Open — model limitation, not solvable via parse mode |
| gptoss120b jobs fail in ~4 min | HIGH | Open — need log analysis (s50 jobs 49936647-49936649) |

## Recent Decisions

- 2026-03-12 (s50): Lulesh recalibrated to i=2000 (was i=5000, which was ~131s with real MPI)
- 2026-03-12 (s50): OMPI_MCA_btl=^smcuda added to lulesh_run to fix finalization segfault
- 2026-03-12 (s50): Previous "51-52s" Lulesh timing was invalid (non-MPI binary, ranks ran independently)
- 2026-03-12 (s50): GPA build fixes applied locally (not upstream) — PATH, K&R flags, srad, lavaMD
- 2026-03-12 (s50): OpenHands FORCE_STRING_SERIALIZER patched for all vLLM-hosted models
- 2026-03-12 (s50): Best-state tracking should be done on a separate feature branch
- 2026-03-12 (s50): Schedule Claude Code runs via nohup+sleep (atd not running on Perlmutter)
- 2026-03-12 (s50): QS profiling analysis confirmed: vault batching overhead (not GPU kernels) was bottleneck

## Next Steps

### Priority 1: Analyze Session 50 Job Results
1. Check all 10 job logs in `batch_results/`
2. Diagnose gptoss120b failures (jobs 49936647-49936649) — likely vLLM startup issue
3. Diagnose SWE-agent+Qwen LLNL early completion (49936643, 10 min)
4. Check Codex results (49936642) — first successful Codex run
5. Check OpenHands+Qwen LLNL results (49936645)
6. Check Claude Code LLNL results (49940919) — Lulesh MPI fix validation
7. Check Claude Code GPA results (49940920) — 5 build fixes validation

### Priority 2: Fix gptoss120b Issues
Based on log analysis, fix whatever caused the 4-min failures and resubmit.

### Priority 3: Implement Best-State Tracking (separate branch)
Design from session 48 HANDOFF.md. Prevents QS-type regressions on timeout.
Create `feature/best-state-tracking` branch.

### Priority 4: Investigate OpenCode + Qwen Tool Calling
Qwen emits `<tool_call>` XML in text content, OpenCode doesn't parse it.
