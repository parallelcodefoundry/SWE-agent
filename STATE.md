# STATE.md — Current Project State

Last updated: 2026-03-10 (session 48)

## Last Session (Session 48)

### Phase 1: Fixed All Root Causes + Submitted 7 Benchmark Jobs

Fixed remaining 5 root causes from session 47 analysis and submitted corrected benchmark runs.

### Phase 2: GPA CUDA 12.9 Validated on Compute Node

Hotspot + gaussian both built, ran, and validated successfully with CUDA 12.9.41 on compute node.

### Log Analysis: Intermediate Speedups Found

Analyzed historical logs — found agents achieving higher speedups mid-session that were lost:

**Session 46 Kripke (Claude Code)**: Agent achieved 10.71x/20.93x (per-kernel) with fused initialization of ALL 3 kernels, but detected wrong physics itself (particle count 7.65e7 vs 1.41e8). Reverted to safe 2.03x. The harness CORRECTNESS check (3 values) was too weak to catch this — agent's own physics understanding caught it.

**Session 41 Laghos**: Intermediate 1.10x exceeded final 1.0664x (measurement noise from CG max_iter tuning).

**Session 41 QS**: Achieved 1.29x with device LTO but validation timed out → reported as null.

**Session 46 other frameworks**: No intermediate speedups found — Codex/OpenCode/SWE-agent with Qwen never produced edits (known root causes now fixed).

### Design Discussion: Best-State Tracking

Identified need for harness-level "best state" snapshotting:
1. After each `*_run` with CORRECTNESS: PASSED + speedup > best, save `git diff HEAD` to `.best_patch.diff`
2. After agent timeout, benchmark_runner compares current vs stored best
3. If stored is better, applies stored patch for final evaluation
4. Also need: turn/time budget awareness in harness output, stronger Kripke correctness checks (particle count convergence)

**Not yet implemented** — design only. Next session should implement.

### Root Cause Status (all 6 from session 47)

| # | Root Cause | Category | Status |
|---|-----------|----------|--------|
| 1 | GPA: CUDA 12.4 nvcc + GCC 14 | infra | **FIXED** (s47) — validating on compute node |
| 2 | Codex+Qwen: wire_api=responses incompatible | infra | **DROPPED** — permanently broken, documented |
| 3 | OpenCode+Qwen: gpt-5-nano 404 | infra | **FIXED** (s48) — added small_model config |
| 4 | SWE-agent+Qwen: analysis paralysis | model | **FIXED** (s48) — xml_function_calling parse mode, testing |
| 5 | Codex+external: missing --model-name | infra | **FIXED** (s47) — documented in CLAUDE.md |
| 6 | Lulesh MPI disabled by agent | prompt | **FIXED** (s48) — MPI_RUNTIME_GUIDANCE in all prompts |

### Code Changes (committed)

1. **prompt.py**: Added `MPI_RUNTIME_GUIDANCE` constant, injected in `build_prompt()` and `build_sweagent_prompts()`
2. **sweagent.py**: Added `_apply_parse_function_override()` — auto-selects xml_function_calling for Qwen, + `SWEAGENT_PARSE_OVERRIDE` env var for A/B testing
3. **opencode.py**: Added `small_model` to both config branches (external + local vLLM)
4. **codex.py**: Documented Codex+Qwen incompatibility (wire_api=responses only, no workaround)
5. **results_summary.json**: Added session 46 Claude Code results (19 entries total)
6. **Skills docs**: Updated Codex, OpenCode, SWE-agent references

### Session 41 vs 46 Claude Code Comparison

| Metric | Session 41 (s41) | Session 46 (s46) |
|--------|-----------------|-----------------|
| Kripke speedup | 15.08x | 2.03x |
| Kripke baseline | 29.2s (likely np=1) | 72.1s (np=4) |
| Kripke strategy | Compiler flags + RAJA cuda_exec | Algorithmic: fused kConst init |
| Laghos speedup | 1.05x | 1.30x |
| QS speedup | timeout | 1.70x (batched atomics) |
| Build mode | harness | direct |
| Profiling | with+without | without |

Session 41 Kripke 15.08x is likely inflated by np=1 (pre-multi-GPU calibration).

### "Agent run failed" in s46 = timeout

"Agent run failed" means Claude Code hit the 60-minute session timeout (~3600s), NOT that the optimizations failed. Kripke and QS both passed correctness with real speedups.

## Active Experiments

### Session 48 Benchmark Jobs (7 submitted, all pending)

| Job ID | Framework | Model | Apps | Config | Notes |
|--------|-----------|-------|------|--------|-------|
| 49891957 | Claude Code | Anthropic | K/L/Lu/QS | no_profiling, direct | MPI warning added |
| 49892081 | Claude Code | Anthropic | K/L/Lu/QS | with_profiling, direct | Compare vs no-profiling |
| 49891958 | Codex | gpt-5.3-codex | K/L/Lu/QS | no_profiling, direct | First-party OpenAI |
| 49891960 | Claude Code | Anthropic | GPA (16) | no_profiling, direct | Separate GPA job |
| 49892015 | SWE-agent | Qwen3-Coder | Lulesh | xml_function_calling | Parse mode test A |
| 49892016 | SWE-agent | Qwen3-Coder | Lulesh | thought_action | Parse mode test B |
| 49892017 | OpenCode | Qwen3-Coder | Lulesh | small_model fix | Title gen fix test |

### Session 46 Results (already in results_summary.json)

| App | Speedup | Correctness | Strategy |
|-----|---------|-------------|----------|
| Kripke | **2.03x** | PASSED | Fused kConst zero-init into LTimes/LPlusTimes |
| Laghos | **1.30x** | PASSED | Relaxed CG tol, disabled sync, fast_math, NBZ=4 |
| QS | **1.70x** | PASSED | Batched atomics, sincos(), UVM optimization |
| Lulesh | N/A | FAILED | Disabled MPI → segfault (now prevented by MPI warning) |

## Validated LLNL App Timings (4x A100)

| App | np | Parameters | Time | Correctness |
|-----|-----|-----------|------|-------------|
| Kripke | 4 | zones=64³, groups=64, niter=60, quad=8 | 51-55s | PASSED |
| Laghos | 4 | p1, dim=2, rs=4, tf=0.8, -pa -d cuda | 67s | PASSED |
| Lulesh | 8 | s=150, i=5000 | 51-52s | PASSED |
| QS | 4 | Coral2_P2_4.inp, nSteps=67 | 60s | PASSED |

## Available Models

| Model | Cached | Size | TP | GPU Mem | Parser | Status |
|-------|--------|------|-----|---------|--------|--------|
| Qwen/Qwen3-Coder-Next-FP8 | Yes | 80GB | 4 | 0.70 | qwen3_coder | Testing xml_function_calling |
| Qwen/Qwen3.5-27B-FP8 | Yes | 31GB | 4 | 0.60 | qwen3_coder | Same issues |
| Qwen/Qwen3.5-122B-A10B-FP8 | Yes | 127GB | 4 | 0.92 | qwen3_coder | Not tested yet |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `050209a3` — Add SWEAGENT_PARSE_OVERRIDE env var

## Infrastructure Bugs Found

| Bug | Severity | Status |
|-----|----------|--------|
| GPA CUDA 12.4 nvcc + GCC 14 build failure | CRITICAL | **FIXED** (s47) |
| --build-mode direct ignored by SWE-agent | HIGH | **FIXED** (s46) |
| Codex+Qwen wire_api incompatibility | HIGH | **DROPPED** (s48) — permanently broken |
| OpenCode+Qwen gpt-5-nano 404 | HIGH | **FIXED** (s48) — small_model config |
| SWE-agent+Qwen analysis paralysis | HIGH | **TESTING** (s48) — xml_function_calling |
| Codex --model-name required | MEDIUM | **FIXED** (s47) |
| Lulesh MPI prompt missing | MEDIUM | **FIXED** (s48) — MPI_RUNTIME_GUIDANCE |
| Qwen reasoning parser breaks tool calls | CRITICAL | **FIXED** (s45) |
| SWE-agent cost limit crash | CRITICAL | **FIXED** (s45) |
| Kripke CHAI required for CUDA+MPI | CRITICAL | **FIXED** (s43) |
| GPA b+tree/backprop build fail (gcc14) | LOW | Open — upstream |
| GPA lavaMD config error | LOW | Open — upstream |

## Recent Decisions

- 2026-03-10 (s48): Drop Codex+Qwen permanently (wire_api=responses only, no workaround)
- 2026-03-10 (s48): SWE-agent uses xml_function_calling for Qwen (tool docs in system prompt)
- 2026-03-10 (s48): OpenCode uses small_model config for title gen
- 2026-03-10 (s48): MPI_RUNTIME_GUIDANCE added to ALL prompts (prevents USE_MPI=0)
- 2026-03-10 (s48): Submit Claude Code with both profiling modes for comparison
- 2026-03-10 (s48): Design "best-state tracking" — harness saves best patch on each successful run, recovers after timeout
- 2026-03-10 (s48): Kripke correctness check needs strengthening — 3 values insufficient, need particle count convergence
- 2026-03-10 (s47): Cancel all pending Qwen3.5-122B jobs — same root causes
- 2026-03-10 (s47): Run LLNL and GPA as separate jobs
- 2026-03-10 (s47): Always pass --model-name with --external-model

## Next Steps

### Priority 1: Check Session 48 Job Results
1. Check parse mode test results (49892015 vs 49892016) — which produces edits?
2. Check OpenCode small_model fix (49892017) — does title gen crash?
3. Check Claude Code LLNL results (49891957 no_profiling, 49892081 with_profiling)
4. Check Codex + gpt-5.3-codex results (49891958)
5. Check Claude Code GPA results (49891960)

### Priority 2: Implement Best-State Tracking
1. Modify `*_run` harness scripts to save `.best_patch.diff` + `.best_speedup` on each PASSED run
2. Modify `hpc_benchmark_runner.py` to recover best state after timeout
3. Add turn/time budget info to harness output (so agent sees remaining budget)
4. Strengthen Kripke correctness: add particle count convergence check

### Priority 3: Submit Remaining Benchmarks
1. If parse mode test succeeds → submit full SWE-agent + Qwen LLNL run
2. If small_model works → submit full OpenCode + Qwen LLNL run
3. Compare all frameworks for the paper
