# STATE.md — Current Project State

Last updated: 2026-03-02 (session 32)

## Last Session (Session 32)

### Analysis & Plots
1. Created `analysis/plot_results.py` — generates 6 figures (speedup heatmaps per session + combined, build success rates, error summary table, error timeline)
2. Generated `batch_results/results_summary.json` (6 jobs, 24 app-level results) and `batch_results/error_narrative.json` (86 issues in 6 categories) via subagents
3. Fixed y-axis label rendering on heatmaps (names were concatenated)

### Results Investigation — Key Findings
4. **QS harness overrides all agent Makefile flags** — `qs_build` passes CXX/CXXFLAGS/CPPFLAGS/LDFLAGS as make command-line args, silently ignoring agent changes. Codex "1.11x" QS speedup was noise (agent's `-g` → `-O3` change had no effect; harness already builds with `-O3`).
5. **Laghos N/C runs show 0.98x–1.23x variance** — baseline-vs-baseline noise is huge. Any reported speedup under ~1.3x is indistinguishable from noise.
6. **Lulesh N/C runs consistently ~0.94x** — systematic 5% bias where "modified" (same exe!) runs slower than baseline. Suggests measurement ordering effect.
7. **SWE-agent STILL crashing** despite --baseline_only signature fix. Job 49410718 shows `RuntimeError: Invalid configuration` in realtime logs. Another config issue beyond the signature fix.
8. **No agent produced a real optimization** — across all frameworks × apps × sessions, all reported speedups are either noise (within N/C variance) or correctness failures (OpenCode Lulesh 3.41x with `correctness: failed`).
9. **Patch analysis**: OpenHands/OpenCode Laghos patches add `-O3 -use_fast_math` to CMakeLists — these DO take effect in Laghos harness (no flag overrides), but CMake Release mode already uses `-O3` for CXX and `-O2` for CUDA, so benefit is marginal. OpenCode deleted entire CMakeLists and replaced with 3 flag lines (broken).

### Session 31 Runs Completed (All 5 Jobs)
10. All 5 SLURM jobs (49405192-49410718) have completed. See results table below.

## Active Experiments

All jobs COMPLETED.

| Job ID | Framework | Model | Status | Kripke | Laghos | Lulesh | Quicksilver |
|--------|-----------|-------|--------|--------|--------|--------|-------------|
| 49405192 | SWE-agent | gpt-4o-mini | DONE | N/C 0.93x | N/C 1.23x | N/C 0.95x | N/C 1.05x |
| 49405194 | OpenHands | gpt-4o-mini | DONE | 0.99x (bad unroll) | 1.00x (CMake flags) | BUILD FAIL | N/C timeout |
| 49405195 | OpenCode | gpt-4o-mini | DONE | CRASH | BUILD FAIL (solver.cpp) | 3.41x FAIL correct | CRASH |
| 49405196 | Claude Code | claude-opus-4-6 | DONE | N/C 1.02x | N/C 0.98x | N/C 0.94x | TIMEOUT |
| 49407271 | Codex | gpt-5.3-codex | DONE | N/C 1.01x | N/C 0.99x | N/C 0.94x | TIMEOUT |
| 49410718 | SWE-agent (fix) | gpt-4o-mini | DONE | N/C 1.02x | N/C 1.10x | N/C 0.94x | TIMEOUT |

**N/C** = No real changes (only .gitignore boilerplate). Speedups are baseline-vs-baseline noise.

## Completed Batch Results (Session 29 Runs)

| Job ID | Framework | Kripke | Laghos | Lulesh | Quicksilver |
|--------|-----------|--------|--------|--------|-------------|
| 49392491 | SWE-agent | N/C (crash) | N/C 1.23x* | N/C 0.95x* | N/C 0.97x* |
| 49392492 | Codex (4o-mini) | BUILD FAIL | BUILD FAIL | BUILD FAIL | 1.11x (noise) |
| 49392493 | OpenHands | N/C (timeout) | 1.02x (CMake flags) | BUILD FAIL (312KB) | N/C (timeout) |
| 49392496 | OpenCode | BUILD FAIL | 1.04x (CMake flags) | N/C 0.95x | 1.04x (cudaMalloc) |

*All speedups marked N/C are within measurement noise range

## Harness Flag Handling Audit

| Harness | Build System | Agent Flags Respected? | Issue |
|---------|-------------|----------------------|-------|
| **Quicksilver** | Make | **NO** — CXX/CXXFLAGS/LDFLAGS overridden via make CLI args | **NEEDS FIX** |
| **Kripke** | CMake | YES — detects git diff CMakeLists.txt, adapts | OK |
| **Lulesh** | Make (template) | YES — if Makefile passes validation (sm_80, SRC_DIR, g++-12) | OK |
| **Laghos** | Make | YES — no overrides at all, just `make -j8` | OK |

## Characterization Results

| App | Config | Runtime | CV | Status |
|-----|--------|---------|-----|--------|
| Kripke | zones=32³ groups=64 niter=10 np=1 | 28.4s | 0.46% | Aligned |
| Lulesh | s=150 i=5000 np=1 | 23.6s | 0.28% | Aligned |
| Laghos | p1 dim2 rs=1 tf=0.4 np=1 | 23.8s | TBD | Aligned |
| Quicksilver | Coral2_P2_1 np=4 | ~50s | 0.5% | Not updated in harness |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `6d60d683` — WIP: Session 32 — analysis plots, results investigation, harness flag audit
- **Working tree**: clean (untracked: 5 Laghos characterization scripts in scripts/)
- **Origin/dev**: 1 commit ahead (session 32 WIP not yet pushed)

## Open Issues / TODOs

### Planned (Session 33) — See Plan File
- [ ] **Fix QS harness flag passthrough** — stop overriding agent Makefile flags (plan at `.claude/plans/nifty-cuddling-piglet.md`)
- [ ] **Investigate SWE-agent continued crash** — still failing with `RuntimeError: Invalid configuration` despite signature fix
- [ ] **Update results + plots** — add new job data, annotate noise range on heatmaps
- [ ] **Laghos timing variance** — N/C range 0.98x-1.23x is too high for meaningful speedup detection

### Still Open
- [ ] **Quicksilver consistent timeout** — All 5 frameworks timeout on QS. May need longer timeout or smaller problem.
- [ ] **Quicksilver characterization not reflected in harness** — np=4 still default
- [ ] **Lulesh systematic bias** — N/C runs show ~0.94x consistently (ordering effect?)
- [ ] **Laghos characterization variance** — Job timed out, need rerun for CV data
- [ ] **GPA baseline build failures** — backprop/lavaMD missing C headers
- [ ] **GPA BFS/Gaussian correctness** — Float precision from `__ldg()`

## Recent Decisions

- 2026-03-02 (s32): QS harness needs to follow Kripke pattern — detect agent Makefile changes, only enforce essentials (nvcc, sm_80, g++-12, MPI)
- 2026-03-02 (s32): All reported "speedups" from sessions 29+31 are within measurement noise. No agent has produced a real optimization yet.
- 2026-03-02 (s32): Laghos harness correctly respects agent flags (no overrides). Kripke and Lulesh also OK.
- 2026-02-26 (s31): Warmup run added to all harnesses — discarded run before timing loop absorbs CUDA cold-start
- 2026-02-26 (s31): --timing-runs for harnesses, --validation-runs for benchmark runner, --run-number for experiment iteration
- 2026-02-26 (s31): Default validation_runs=10 in benchmark runner, default timing_runs=1 in harnesses
- 2026-02-26 (s31): Config YAMLs updated with characterization defaults
- 2026-02-26 (s31): Build time is NOT included in harness timing
- 2026-02-26 (s30): Kripke Timing.cpp confirmed: name, count, seconds order
- 2026-02-26 (s30): All baselines already -O3 optimized

## Next Steps

1. Fix QS harness flag passthrough (Part 1 of plan)
2. Investigate and fix SWE-agent continued crash (Part 4 of plan)
3. Update results data + regenerate plots with all job data (Part 3 of plan)
4. Address Laghos timing variance and Lulesh measurement bias
5. Resubmit benchmark runs after fixes
