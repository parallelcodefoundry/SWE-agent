# STATE.md — Current Project State

Last updated: 2026-02-26 (session 31)

## Current Focus

**Session 31: Added multi-run timing with warmup to all harnesses, pushed dev to origin, updated config YAMLs with characterization defaults.**

## Session 31 — Changes Implemented

### Multi-Run Timing (all 4 harness run scripts)
1. **`--timing-runs N`** argument (default 1) — Number of timing repetitions per version. Reports median.
2. **`--timeout-multiplier`** argument (default 3.0) — Modified run timeout = baseline_time * multiplier. Early stops if exceeded.
3. **Warmup run** — Single discarded run before timed loop. Warms CUDA context + Lustre page cache. Fixed 69s cold-start issue observed in testing.
4. **Median-based speedup** — `BASELINE TIME` and `MODIFIED TIME` use medians when multiple runs. Per-run times, stdev reported when N > 1.
5. **Configurable timeout** in run functions — Was hardcoded 600s/300s, now parameter.

### Benchmark Runner (`hpc_benchmark_runner.py`)
6. **`--validation-runs N`** CLI arg (default 10) — Passed as `--timing-runs N` to harnesses for final validation.
7. **Scaled timeout** — `600 + (N-1) * 120` seconds for multi-run validation.
8. **Multi-run stats logging** — Parses TIMING RUNS and Kripke multi_run JSON.

### Config YAML Updates (stale defaults fixed)
9. **Lulesh**: s=150, i=5000, np=1 (was s=30, i=100, np=8)
10. **Kripke**: groups=64, np=1 (was groups=32, np=4). Removed "CRITICAL: use 4 MPI ranks" advice.
11. **Laghos**: rs=1, tf=0.4, np=1 (was rs=3, tf=0.8, np=4)
12. **All**: Added warmup step to tool docstrings.

### Other
13. **Pushed dev to origin** — 22 commits pushed (`0fe0fa38..8bd1e207`).
14. **Flag naming**: Renamed `--num-runs` to `--timing-runs` in harnesses to avoid confusion with `--run-number` (experiment iteration) in benchmark runner.

### Test Results (Perlmutter A100)
- **Lulesh --timing-runs 3 --baseline-only (s=30 i=100)**: PASSED. Shows 3 per-run times + median. Backward-compatible with default.
- **Lulesh --timing-runs 3 full comparison (s=30 i=100)**: PASSED. TIMING RUNS, per-run, stdev all correct.
- **Lulesh default (timing-runs=1)**: PASSED. No extra output, identical to pre-change.
- **Kripke --timing-runs 3 --baseline-only**: PASSED. JSON includes baseline_solve_times + median.
- **Kripke --timing-runs 3 full**: PASSED. JSON multi_run dict with all stats.
- **Lulesh warmup test (s=150 i=5000)**: PASSED. Warmup: 22.210s, runs: 22.189/22.196/22.219s (30ms spread).

### Key Finding: CUDA Cold-Start
- First run on fresh GPU node took 69s for a 0.4s problem (s=30 i=100)
- Caused by CUDA context init + Lustre page cache cold
- Warmup run absorbs this; timed runs are consistent (~30ms spread at 22s)
- Median also handles it, but explicit warmup is cleaner

## Active Experiments

| Job ID | Framework | Model | Apps | Status |
|--------|-----------|-------|------|--------|
| 49405194 | OpenHands | gpt-4o-mini | all 4 LLNL | RUNNING |
| 49405192 | SWE-agent | gpt-4o-mini | all 4 LLNL | PENDING |
| 49405195 | OpenCode | gpt-4o-mini | all 4 LLNL | PENDING |
| 49405196 | Claude Code | claude-opus-4-6 | all 4 LLNL | PENDING |
| 49407271 | Codex | gpt-5.3-codex | all 4 LLNL | PENDING |

Note: These jobs use the OLD harness code (pre-multi-run). Results will still be single-shot. Multi-run validation applies to future runs.

## Completed Batch Results (Session 29 Runs)

| Job ID | Framework | Kripke | Laghos | Lulesh | Quicksilver |
|--------|-----------|--------|--------|--------|-------------|
| 49392491 | SWE-agent | config crash | PASSED 1.23x* | PASSED 0.95x* | PASSED 0.97x* |
| 49392492 | Codex (4o-mini) | BUILD FAIL | BUILD FAIL | BUILD FAIL | PASSED 1.11x |
| 49392493 | OpenHands | unknown (timeout 60m) | PASSED 1.02x | BUILD FAIL (312KB) | unknown (timeout 60m) |
| 49392496 | OpenCode | BUILD FAIL | PASSED 1.04x | PASSED 0.95x | PASSED 1.04x |
| 49392497 | Claude Code | CANCELLED | CANCELLED | CANCELLED | CANCELLED |

*SWE-agent results are baseline-only (agent never started due to config crash)

## Characterization Results

| App | Config | Runtime | CV | Status |
|-----|--------|---------|-----|--------|
| Kripke | zones=32³ groups=64 niter=10 np=1 | 28.4s | 0.46% | Aligned |
| Lulesh | s=150 i=5000 np=1 | 23.6s | 0.28% | Aligned |
| Laghos | p1 dim2 rs=1 tf=0.4 np=1 | 23.8s | TBD | Aligned |
| Quicksilver | Coral2_P2_1 np=4 | ~50s | 0.5% | Not updated in harness (np=4 unchanged) |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `1608f2cf` — WIP: Add multi-run timing, warmup, and baseline-based timeout
- **Working tree**: clean (untracked: 5 Laghos characterization scripts in scripts/)
- **Origin/dev**: up to date (pushed this session)

## Open Issues / TODOs

### Fixed This Session (Session 31)
- [x] Push dev to origin (~22 commits)
- [x] Multi-run timing for statistical rigor
- [x] Warmup run for CUDA cold-start
- [x] Stale config YAML defaults
- [x] Flag naming confusion (--num-runs → --timing-runs)

### Still Open
- [ ] **Quicksilver characterization not reflected in harness** — np=4 still default, no characterization-based update
- [ ] **EDQUOT disk quota** — User says fixed, .claude dir is in home (not symlinked), batch_results on scratch (13GB)
- [ ] **Laghos characterization variance** — Job timed out, need to rerun for CV data
- [ ] **GPA baseline build failures** — backprop/lavaMD missing C headers
- [ ] **GPA BFS/Gaussian correctness** — Float precision from `__ldg()`
- [ ] **Lulesh SRC_DIR trap** — Agents struggle with `SRC_DIR = src` vs `cuda/src/`
- [ ] **Laghos/QS not tested with warmup** — Only Lulesh and Kripke tested on GPU

## Next Steps

1. Check batch job results when they complete (49405192-49407271)
2. Test Laghos and Quicksilver warmup+multi-run on GPU (only Lulesh/Kripke tested so far)
3. Update Quicksilver harness defaults from characterization (np=4 → np=1?)
4. Investigate Lulesh SRC_DIR trap — agents keep getting confused
5. Rerun Laghos characterization for variance data

## Recent Decisions

- 2026-02-26 (s31): Warmup run added to all harnesses — discarded run before timing loop absorbs CUDA cold-start (69s → 22s)
- 2026-02-26 (s31): --timing-runs (not --num-runs) to avoid confusion with --run-number
- 2026-02-26 (s31): Default validation_runs=10 in benchmark runner, default timing_runs=1 in harnesses
- 2026-02-26 (s31): Config YAMLs updated with characterization defaults (s=150/groups=64/rs=1/np=1)
- 2026-02-26 (s31): Build time is NOT included in harness timing (confirmed: get_pristine_executable() runs before timing loop)
- 2026-02-26 (s30): Kripke Timing.cpp confirmed: name, count, seconds order
- 2026-02-26 (s30): First-party Codex models use built-in openai provider
- 2026-02-26 (s30): All baselines already -O3 optimized
