# HANDOFF.md — Session State

Last updated: 2026-02-16 (session 17 — Phase 2 setup)

## Current Phase

**Phase 2: Benchmark Expansion** — goals tracked in `.planning/PHASE2-GOALS.md`

## What Was Done This Session (17)

- Committed session 16 uncommitted changes (Lulesh doubled path fix + post-agent validation)
- Updated `.claude/skills/gpa-benchmark/SKILL.md` with current GPA-Benchmark repo state (17 apps, `run_driver()` API, new CLI flags)
- Updated `.claude/skills/swefficiency/SKILL.md` with inference harness, eval pipeline, podman-hpc notes
- Created `~/swefficiency` symlink to `/pscratch/sd/k/krydzy/swefficiency/`
- Pulled latest changes in both GPA-Benchmark and SWE-fficiency repos
- Created `.planning/PHASE2-GOALS.md` (Ralph loop checklist)
- Created `.planning/RALPH-PROMPT-PHASE2.md` (combined Ralph + Phase 2 prompt)

## What Was Done Last Session (16)

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
| `.claude/skills/gpa-benchmark/SKILL.md` | Updated with current repo state |
| `.claude/skills/swefficiency/SKILL.md` | Updated with inference harness, eval pipeline |
| `.planning/PHASE2-GOALS.md` | NEW — Phase 2 goal checklist |
| `.planning/RALPH-PROMPT-PHASE2.md` | NEW — Ralph loop prompt for Phase 2 |
| `.planning/HANDOFF.md` | This file (restructured) |

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

- **Current branch**: `local`
- **Latest commit**: `f2140f35` — Fix Lulesh doubled path + post-agent validation
