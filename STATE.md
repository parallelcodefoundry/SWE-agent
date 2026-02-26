# STATE.md — Current Project State

Last updated: 2026-02-26 (session 29)

## Current Focus

**Session 29: Fixed harness bugs found by code review, updated runtime defaults from A100 characterization, submitted 5 batch jobs (gpt-4o-mini + Claude Code).**

## Session 29 — Changes Implemented

### Harness Bug Fixes
1. **kripke_run timing regex** — Was `(\d+)\s+([\d.]+)` (int, float) but real output is `([\d.eE+-]+)\s+(\d+)` (float, int). `\d+` could never match `21.809679`. Fixed both `parse_timing_from_output()` and `extract_scientific_values()`.
2. **CORRECTNESS: FAILED output** — All 4 run harnesses (kripke/laghos/lulesh/qs) now output `CORRECTNESS: FAILED` on crash/failure. Previously only output `ERROR` which benchmark runner doesn't parse.
3. **Fallback path fixes** — qs_run, qs_build, kripke_build now fall back to `*_test` repos instead of pristine repos.
4. **qs_build dead code** — Removed unused `ignored_flags` key and stale comment.
5. **claude.py nested session** — Added `unset CLAUDECODE` to prevent "nested session" error when benchmark runner is launched from within Claude Code.
6. **prompt.py phantom tool** — Removed non-existent `hpc_analyze` from profiling tools string.
7. **Harness permissions** — All harness scripts chmod 755 (some were 710/600).

### Runtime Defaults Updated (from A100 characterization)
8. **Kripke**: groups 32→64 (28.4s, 0.46% CV at zones=32³ niter=10 np=1)
9. **Lulesh**: s=30→150, i=100→5000, np=8→1 (23.6s, 0.28% CV)
10. **Laghos**: rs=3→1, tf=0.8→0.4, np=4→1 (23.8s wall time)

### Batch Results Deep Dive (Session 27-28 Runs)
Analyzed all 6 completed batch jobs. Root causes:
- **SWE-agent vLLM**: Got furthest (20+ steps), made 1 real Laghos optimization. Model too weak to finish.
- **Codex**: 120 tokens, 1 turn, needs_follow_up=false immediately. Model weakness.
- **OpenHands**: Pydantic message format error on first API call to vLLM.
- **Claude Code**: `CLAUDECODE` env var blocked nested session. Now fixed.
- **OpenCode**: Rate limited, exited after 1 step.
- **SWE-agent external**: 404 model not found.
- 50% framework bugs, 40% model weakness, 10% infrastructure.

## Active Experiments

| Job ID | Framework | Model | Apps | Status |
|--------|-----------|-------|------|--------|
| 49392491 | SWE-agent | gpt-4o-mini | all 4 LLNL | PENDING |
| 49392492 | Codex | gpt-4o-mini | all 4 LLNL | PENDING |
| 49392493 | OpenHands | gpt-4o-mini | all 4 LLNL | PENDING |
| 49392496 | OpenCode | gpt-4o-mini | all 4 LLNL | PENDING |
| 49392497 | Claude Code | claude-opus-4-6 | all 4 LLNL | PENDING |
| 49392034 | — | — | Laghos char | RUNNING |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `bb7d8f3d` — Session 29: Fix harness bugs, update defaults from characterization data
- **Working tree**: clean (STATE.md/HANDOFF.md pending)
- **Ahead of origin/dev**: ~17 commits (not yet pushed)

## Completed Batch Results (Session 27-28)

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
- 23.8s wall time (single run — Laghos characterization job still running for variance data)
- Alternative: p1 dim2 rs=2 tf=0.1 → 25.7s

## Open Issues / TODOs

### Fixed This Session (Session 29)
- [x] kripke_run timing regex (was completely broken)
- [x] CORRECTNESS: FAILED output on all 4 harness crashes
- [x] Fallback path fixes (qs_run, qs_build, kripke_build)
- [x] Claude Code nested session (CLAUDECODE env var)
- [x] Phantom hpc_analyze tool in prompt.py
- [x] Harness permissions (chmod 755)
- [x] Runtime characterization (Kripke, Lulesh, Laghos)
- [x] Updated harness defaults from characterization data
- [x] Submitted gpt-4o-mini batch runs (all 5 frameworks × 4 apps)

### Still Open
- [ ] **Laghos characterization variance** — Job 49392034 still running, need CV data
- [ ] **Old per-app YAML configs** — Can remove `config/hpc/{app}_{profiling}.yaml`
- [ ] **GPA baseline build failures** — backprop/lavaMD missing C headers
- [ ] **GPA BFS/Gaussian correctness** — Float precision from `__ldg()`
- [ ] **Push dev to origin** — ~17 commits ready

### Next Steps
1. Check batch job results when they complete (49392491-49392497)
2. Get Laghos variance data from characterization job (49392034)
3. Push dev to origin
4. Analyze gpt-4o-mini results vs previous gpt-oss-120b results

## Recent Decisions

- 2026-02-26 (s29): Use gpt-4o-mini for external model benchmarks (better than gpt-oss-120b)
- 2026-02-26 (s29): All apps default to np=1 (single GPU) — minimizes MPI overhead, cleaner benchmarking
- 2026-02-26 (s29): Runtime targets ~24s wall time per harness run (characterization-based)
- 2026-02-26 (s28): SWE-agent prompts generated from prompt.py, not hardcoded in YAML
- 2026-02-26 (s28): Kripke default MPI ranks reduced to 1
- 2026-02-26 (s28): Only truly dangerous flags filtered in qs_build
