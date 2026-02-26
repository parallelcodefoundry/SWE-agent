# STATE.md — Current Project State

Last updated: 2026-02-26 (session 30)

## Current Focus

**Session 30: Fixed 2 remaining harness bugs (Kripke regex column order + SWE-agent tool signatures), analyzed session 29 results, resubmitted all 5 benchmark jobs.**

## Session 30 — Changes Implemented

### Bug Fixes
1. **Kripke timer regex column order** — Session 29 "fix" still had columns reversed. Kripke source (Timing.cpp) prints `name count(int) seconds(float)` via `printf("%-16s %12d %12.5lf")`. Regex was matching `name float int`. Fixed in both `parse_timing_from_output()` and `extract_scientific_values()`.
2. **SWE-agent tool signatures missing --baseline-only** — All 4 harness config.yaml files had `baseline_only` defined as an argument but NOT in the signature string. SWE-agent's Pydantic validation requires all args in the signature. Added `[--baseline-only]` to all 4 signatures.
3. **qs_run config format** — Signature was empty string (no args), argument used dict format instead of list format. Fixed both.

### Session 29 Results Analysis
- **Laghos timeout fixed**: 0/6 → 3/4 passing (runtime param tuning worked)
- **Lulesh improved**: 0/6 "unknown" → 2/4 passing
- **Kripke still broken**: regex bug caused all "unknown" (now fixed)
- **SWE-agent never started**: config validation crash (now fixed)
- **Claude Code job cancelled**: Never ran (resubmitted)
- Build failures are now agent-caused (model weakness), not infrastructure

## Active Experiments

| Job ID | Framework | Model | Apps | Status |
|--------|-----------|-------|------|--------|
| 49405192 | SWE-agent | gpt-4o-mini | all 4 LLNL | PENDING |
| 49405193 | Codex | gpt-4o-mini | all 4 LLNL | PENDING |
| 49405194 | OpenHands | gpt-4o-mini | all 4 LLNL | PENDING |
| 49405195 | OpenCode | gpt-4o-mini | all 4 LLNL | PENDING |
| 49405196 | Claude Code | claude-opus-4-6 | all 4 LLNL | PENDING |

## Completed Batch Results (Session 29 Runs)

| Job ID | Framework | Kripke | Laghos | Lulesh | Quicksilver |
|--------|-----------|--------|--------|--------|-------------|
| 49392491 | SWE-agent | config crash | PASSED 1.23x* | PASSED 0.95x* | PASSED 0.97x* |
| 49392492 | Codex | BUILD FAIL | BUILD FAIL | BUILD FAIL | **PASSED 1.11x** |
| 49392493 | OpenHands | unknown (timeout) | PASSED 1.02x | BUILD FAIL | unknown (timeout) |
| 49392496 | OpenCode | BUILD FAIL | PASSED 1.04x | PASSED 0.95x | PASSED 1.04x |
| 49392497 | Claude Code | CANCELLED | CANCELLED | CANCELLED | CANCELLED |

*SWE-agent results are baseline-only (agent never started due to config crash)

### Session 29 Failure Analysis
- **SWE-agent**: Config validation crash → agent never ran. All "results" are just pristine baselines.
- **Codex (gpt-4o-mini)**: Destructive changes — spammed Kripke CMakeLists, deleted Laghos files, broke Lulesh CUDA. Only QS succeeded (compiler flags + kernel launch config → 1.11x).
- **OpenHands**: Timed out on Kripke/QS (60 min each, no changes). Made moderate Laghos improvement. Destroyed Lulesh with 312KB rewrite.
- **OpenCode**: Most consistent (3/4 passing). Kripke failed trying raw CUDA inside RAJA abstractions. Modest speedups (1.04x).

## Completed Batch Results (Session 27-28 Runs)

| Job ID | Framework | Kripke | Laghos | Lulesh | Quicksilver |
|--------|-----------|--------|--------|--------|-------------|
| 49385453 | sweagent (vLLM) | builds, unknown | builds, timeout | builds, unknown | no build |
| 49385454 | sweagent (ext) | crash 60s | crash 27s | builds, unknown | crash 31s |
| 49385456 | openhands | builds, unknown | builds, timeout | builds, unknown | **passed 1.00x** |
| 49385461 | claude | builds, unknown | builds, timeout | builds, unknown | **passed 1.03x** |
| 49387755 | codex | builds, unknown | builds, timeout | builds, unknown | **passed 1.06x** |
| 49387756 | opencode | builds, unknown | builds, timeout | builds, unknown | passed 0.92x |

## Characterization Results (Session 29)

### Kripke (RECOMMENDED: zones=32³ groups=64 niter=10 np=1)
- 28.4s wall time, 0.46% CV

### Lulesh (RECOMMENDED: s=150 i=5000 np=1)
- 23.6s wall time, 0.28% CV

### Laghos (RECOMMENDED: p1 dim2 rs=1 tf=0.4 np=1)
- 23.8s wall time (Laghos characterization job timed out — variance TBD)

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `82e6212e` — Fix Kripke timer regex column order + add --baseline-only to SWE-agent tool signatures
- **Working tree**: clean (STATE.md pending)
- **Ahead of origin/dev**: ~19 commits (not yet pushed)

## Open Issues / TODOs

### Fixed This Session (Session 30)
- [x] Kripke timer regex column order (was STILL reversed after session 29 fix)
- [x] SWE-agent tool signatures missing --baseline-only (Pydantic crash)
- [x] qs_run empty signature + dict-style argument format
- [x] Resubmitted all 5 benchmark jobs

### Still Open
- [ ] **Laghos characterization variance** — Job 49392034 timed out, need to rerun
- [ ] **Old per-app YAML configs** — Can remove `config/hpc/{app}_{profiling}.yaml`
- [ ] **GPA baseline build failures** — backprop/lavaMD missing C headers
- [ ] **GPA BFS/Gaussian correctness** — Float precision from `__ldg()`
- [ ] **Push dev to origin** — ~19 commits ready

### Next Steps
1. Check batch job results when they complete (49405192-49405196)
2. Push dev to origin
3. Analyze session 30 results — expect Kripke correctness to work now + SWE-agent to actually run

## Recent Decisions

- 2026-02-26 (s30): Confirmed Kripke Timing.cpp format: `printf("%-16s %12d %12.5lf", name, count, seconds)`
- 2026-02-26 (s29): Use gpt-4o-mini for external model benchmarks (better than gpt-oss-120b)
- 2026-02-26 (s29): All apps default to np=1 (single GPU) — minimizes MPI overhead, cleaner benchmarking
- 2026-02-26 (s29): Runtime targets ~24s wall time per harness run (characterization-based)
- 2026-02-26 (s28): SWE-agent prompts generated from prompt.py, not hardcoded in YAML
