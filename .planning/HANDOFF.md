# HANDOFF.md — Session State

Last updated: 2026-02-16 (session 18 — Phase 2 Goals 0-1)

## Current Phase

**Phase 2: Benchmark Expansion** — goals tracked in `.planning/PHASE2-GOALS.md`

## What Was Done This Session (18)

- **Goal 0**: Created `benchmark-expansion` branch off `local`
- **Goal 1**: GPA-Benchmark driver integration:
  - Added `--app gpa` to `hpc_benchmark_runner.py` CLI and `--gpa` to `run_benchmark.sh`
  - Added `GPA_BENCHMARK_ROOT` and `sys.path` setup for GPA driver import
  - Implemented 6 new methods in `HPCBenchmarkRunner` for GPA workflow
  - Base mode: iterates all 17 GPA apps, calls `run_driver()` directly (no agent needed)
  - Agent mode: creates workspace with kernel files, runs agent, reads modified files, calls `run_driver(swaps_override=...)` for timing comparison
  - Validated on compute node: gaussian (9.6s, PASS) and hotspot (16.6s, PASS)
  - Pre-requisite: `get_data.sh` downloaded rodinia input data; `alive-progress` pip installed

## What Was Done Session 17

- Fixed Lulesh doubled path: removed `/cuda` from `env.repo.path` in lulesh YAML configs (kept in `LULESH_ROOT`)
- Added post-agent validation: `_validate_agent_changes()` in `hpc_benchmark_runner.py` populates `agent_builds`/`agent_correctness`/`agent_speedup`
- Smoke tested validation on compute node (Job 49013841): both paths verified (no-changes skip + build/run/parse with QS)

## Phase 1 Results (Session 15) — Full 4×4 Matrix

| Framework | Kripke | Laghos | Lulesh | Quicksilver | Total |
|-----------|--------|--------|--------|-------------|-------|
| **Codex** | OK (711s) | OK (221s) | **FAIL** (1582s) | OK (360s) | 3/4 |
| **SWE-agent** | OK (1474s) | OK (593s) | **FAIL** (1990s) | OK (2253s) | 3/4 |
| **OpenCode** | OK (3548s) | OK (197s) | OK (554s) | OK (881s) | **4/4** |
| **OpenHands** | OK (641s) | OK (189s) | OK (190s) | OK (2578s) | **4/4** |

**14/16 cells successful. Both failures on Lulesh (Codex + SWE-agent).**

## Output Data Locations

All Phase 1 results in `batch_results/benchmark_*_48889171/run_1/{app}/`:
- `benchmark_results.json` — structured results
- `agent.log` / `benchmark.log` — runner logs
- `{app}__base_agent_realtime.log` — agent output
- `workspaces/{app}__base/` — agent workspace

Trajectories in `trajectories/benchmark_*_48889171/run_1/{app}/{app}__base.jsonl`.

## Files Modified This Session

| File | Change |
|------|--------|
| `batch/hpc_benchmark_runner.py` | Added GPA support: 6 new methods, --app gpa, import + sys.path |
| `batch/run_benchmark.sh` | Added --gpa flag, CUDA_HOME export, updated help text |
| `.planning/PHASE2-GOALS.md` | Marked Goals 0-1 done |
| `.planning/HANDOFF.md` | This file |
| `STATE.md` | Updated with session 18 |

## Files to Read First Next Session

1. `STATE.md` — Full state overview
2. `.planning/HANDOFF.md` — This file
3. `.planning/PHASE2-GOALS.md` — Phase 2 goal checklist
4. `.claude/skills/gpa-benchmark/SKILL.md` — GPA driver API and CLI
5. `.claude/skills/swefficiency/SKILL.md` — SWE-fficiency eval pipeline
6. `batch/hpc_benchmark_runner.py` — Main benchmark runner
7. `batch/run_benchmark.sh` — Shell entry point

## Key Observations

1. **Laghos produces no patches** — all 4 frameworks finish fast but none change code
2. **Lulesh is hardest** — only OpenCode and OpenHands succeed
3. **SWE-agent whitespace issue** — reformats entire files on Lulesh (1.9M chars)
4. **OpenHands Kripke generates huge patches** — 4.5M chars, likely build artifacts

## Branch State

- **Current branch**: `benchmark-expansion` (off `local`)
- **Latest commit**: (pending commit for Goal 0-1)
