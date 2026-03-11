# STATE.md — Current Project State

Last updated: 2026-03-11 (session 49)

## Last Session (Session 49)

### Phase 1: Thorough Analysis of Session 48 Job Results

All 7 session 48 jobs completed (6 finished before session, 1 during). Deep analysis via parallel agents:

**Session 48 Results Summary:**

| Job ID | Framework | Model | Config | Result |
|--------|-----------|-------|--------|--------|
| 49891957 | Claude Code | Anthropic | no_prof LLNL | Laghos 1.37x, QS 1.02x, Kripke no_edit, Lulesh MPI fail |
| 49892081 | Claude Code | Anthropic | with_prof LLNL | Laghos 1.35x, **QS 1.65x**, Kripke no_edit, Lulesh MPI fail |
| 49891958 | Codex | gpt-5.3-codex | no_prof LLNL | **CRASH**: missing `name` in model_providers.openai |
| 49891960 | Claude Code | Anthropic | no_prof GPA | **CRASH**: `retain_nsys_profiles` kwarg (10/16 agents ran but results lost) |
| 49892015 | SWE-agent | Qwen3-Coder | xml_func Lulesh | No edits (200 calls, analysis paralysis) |
| 49892016 | SWE-agent | Qwen3-Coder | thought_act Lulesh | No edits (200 calls, format errors) |
| 49892017 | OpenCode | Qwen3-Coder | small_model Lulesh | small_model fix worked, but agent exits after 1 step |

**Key finding: QS 1.65x WITH profiling vs 1.02x WITHOUT** — profiling tools are the key differentiator for finding atomic contention optimizations.

### Phase 2: Root Cause Analysis

1. **Lulesh pristine binary has NO MPI** — `MPICH_DIR` not set during build, Makefile resolves to invalid `/include` and `/lib`. Agent's `nm` analysis was correct. All Lulesh results across ALL sessions were affected.
2. **QS no_profiling regression** — Agent found micro-optimizations (sincos, rsqrt) but missed atomic contention. Also made late tally replication change (regression) and timed out before reverting. Best-state tracking would have saved 1.04x.
3. **Kripke s41 15x "optimization"** — Part was fixing `kConst`/`kCopy` from `RAJA::seq_exec` (CPU) to `RAJA::cuda_exec<256>` (GPU). This is a legitimate optimization in upstream Kripke code (utility functions intentionally use seq_exec, not a setup error).
4. **SWE-agent Qwen analysis paralysis** — 92.5% filler thoughts ("let me look at..."), zero substantive analysis, views same 4 functions 30-40 times each. Model limitation, not parse mode issue.

### Phase 3: Bug Fixes (committed)

1. **Codex config** (`codex.py`): Bridge `OPENAI_API_BASE` → `OPENAI_BASE_URL` env var. Codex natively reads `OPENAI_BASE_URL` in `create_openai_provider()`. Removed `-c model_providers.openai.*` flags.
2. **GPA driver** (GPA-Benchmark repo, commit `0a6aece`): Removed stale `retain_nsys_profiles` kwarg from `postprocess_nsys_app()` call.
3. **Lulesh MPI** (`lulesh_build` + `lulesh_run`): Set `MPICH_DIR` from `OPENMPI_ROOT` with Perlmutter fallback path.

### Phase 4: Timeout/Steps Increase (committed)

All frameworks: SESSION_TIMEOUT 3600→7200, max turns/calls 200→300. Agent subprocess timeout 3900→7500.

### Profiling Mode Comparison (first real data)

| App | No Profiling | With Profiling | Delta |
|-----|-------------|----------------|-------|
| Laghos | 1.37x | 1.35x | ~same |
| QS | 1.02x | **1.65x** | +63% from profiling |
| Kripke | no_edit | no_edit | no change |
| Lulesh | MPI fail | MPI fail | both broken |

## Active Experiments

### Session 49 — No Active Jobs

All session 48 jobs completed. Need to:
1. Rebuild pristine Lulesh with MPI on compute node
2. Resubmit with fixes applied

### Session 48+49 Combined Results (all in results_summary.json or batch_results/)

Refer to HANDOFF.md for resubmission plan.

## Validated LLNL App Timings (4x A100)

| App | np | Parameters | Time | Correctness |
|-----|-----|-----------|------|-------------|
| Kripke | 4 | zones=64³, groups=64, niter=60, quad=8 | 51-55s | PASSED |
| Laghos | 4 | p1, dim=2, rs=4, tf=0.8, -pa -d cuda | 67s | PASSED |
| Lulesh | 8 | s=150, i=5000 | 51-52s | PASSED (but pristine binary lacks MPI!) |
| QS | 4 | Coral2_P2_4.inp, nSteps=67 | 60s | PASSED |

## Available Models

| Model | Cached | Size | TP | GPU Mem | Parser | Status |
|-------|--------|------|-----|---------|--------|--------|
| Qwen/Qwen3-Coder-Next-FP8 | Yes | 80GB | 4 | 0.70 | qwen3_coder | Analysis paralysis confirmed |
| Qwen/Qwen3.5-27B-FP8 | Yes | 31GB | 4 | 0.60 | qwen3_coder | Same issues |
| Qwen/Qwen3.5-122B-A10B-FP8 | Yes | 127GB | 4 | 0.92 | qwen3_coder | Not tested yet |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `b99bae0f` — WIP: Session 49 fixes

## Infrastructure Bugs Found

| Bug | Severity | Status |
|-----|----------|--------|
| Lulesh pristine binary lacks MPI | CRITICAL | **FIXED** (s49) — needs rebuild on compute node |
| Codex OPENAI_BASE_URL config crash | CRITICAL | **FIXED** (s49) — bridge env var |
| GPA retain_nsys_profiles kwarg | CRITICAL | **FIXED** (s49) — committed in GPA-Benchmark |
| OpenCode exits after 1 step (Qwen XML) | HIGH | Open — Qwen tool_call XML not parsed by OpenCode |
| SWE-agent+Qwen analysis paralysis | HIGH | Open — model limitation, not solvable via parse mode |
| GPA b+tree/backprop build fail (gcc14) | LOW | Open — upstream |
| GPA lavaMD config error | LOW | Open — upstream |

## Recent Decisions

- 2026-03-11 (s49): Increase SESSION_TIMEOUT to 7200s (2hr) and max turns to 300 for ALL frameworks
- 2026-03-11 (s49): Keep SLURM walltime at 4 hours (user decision)
- 2026-03-11 (s49): Lulesh MPICH_DIR fix via OPENMPI_ROOT bridging (not a Lulesh upstream bug, just Perlmutter env issue)
- 2026-03-11 (s49): Codex uses OPENAI_BASE_URL env var natively (no -c flags for first-party models)
- 2026-03-11 (s49): Kripke kConst seq_exec→cuda_exec is legitimate optimization in upstream code (not setup error)
- 2026-03-11 (s49): Profiling tools confirmed as key differentiator (QS 1.65x with vs 1.02x without)
- 2026-03-11 (s49): Do NOT add hotspot hints to no_profiling prompts (undermines profiling comparison)
- 2026-03-11 (s49): Do NOT add time/iteration tracking to prompts (models can't track internally)

## Next Steps

### Priority 1: Rebuild Pristine Lulesh + Validate
1. Get compute node (`salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m5083`)
2. `module load python cmake openmpi/5.0.7 cudatoolkit/12.4`
3. Clean and rebuild: `rm /pscratch/sd/k/krydzy/SWE-agent/Lulesh/cuda/lulesh && ./scripts/setup_apps.sh --lulesh`
4. Verify: `readelf -d Lulesh/cuda/lulesh | grep mpi` — should show `libmpi.so.40`
5. Reset test repo: `./scripts/reset_test_repos.sh --lulesh`

### Priority 2: Resubmit Fixed Jobs
Submit both with_profiling and no_profiling for each framework:
- Claude Code LLNL (both modes) — already have s48 results, rerun for Lulesh MPI fix
- Codex + gpt-5.3-codex LLNL (both modes) — config fix applied
- Claude Code GPA — retain_nsys fix applied
- SWE-agent + Qwen LLNL (both modes, xml_function_calling, 300 calls) — may still fail but worth trying
- OpenCode + Qwen — needs investigation of XML tool call issue first

### Priority 3: Implement Best-State Tracking
Design from session 48 HANDOFF.md. Prevents QS-type regressions on timeout.

### Priority 4: Analyze with_profiling Results
Job 49892081 QS patch (1.65x) — read the patch to see what profiling-guided optimizations the agent found vs the no_profiling run (1.02x).
