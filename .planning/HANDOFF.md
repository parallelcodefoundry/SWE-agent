# HANDOFF.md — Session 16 Summary

Last updated: 2026-02-16 (session 16)

## What Was Done

Fixed Lulesh doubled path bug and added post-agent validation to `hpc_benchmark_runner.py`.

## Goal Progress

- [x] Goal 1: Fix Lulesh doubled path bug in YAML configs
- [x] Goal 2: Add post-agent validation to `hpc_benchmark_runner.py`
- [ ] Goal 3: Smoke test validation on compute node (**IN PROGRESS**)
- [x] Goal 4 (s15): Full 4×4 matrix validation (14/16 pass)
- [ ] Goal 5: Curated performance commits benchmark
- [ ] Goal 6: GPA-Benchmark + SWE-fficiency integration
- [ ] Goal 7: Investigate Lulesh failures for Codex and SWE-agent

## Results Matrix

| Framework | Kripke | Laghos | Lulesh | Quicksilver | Total |
|-----------|--------|--------|--------|-------------|-------|
| **Codex** | OK (711s) | OK (221s) | **FAIL** (1582s) | OK (360s) | 3/4 |
| **SWE-agent** | OK (1474s) | OK (593s) | **FAIL** (1990s) | OK (2253s) | 3/4 |
| **OpenCode** | OK (3548s) | OK (197s) | OK (554s) | OK (881s) | **4/4** |
| **OpenHands** | OK (641s) | OK (189s) | OK (190s) | OK (2578s) | **4/4** |

## Files Modified This Session

| File | Change |
|------|--------|
| `config/hpc/lulesh_no_profiling.yaml` | Removed `/cuda` from `env.repo.path` |
| `config/hpc/lulesh_with_profiling.yaml` | Removed `/cuda` from `env.repo.path` |
| `batch/hpc_benchmark_runner.py` | Added `import re`, validation constants, `_validate_agent_changes()`, wired into `run_benchmark()` |
| `STATE.md` | Updated with session 16 bug fixes |
| `.planning/HANDOFF.md` | This file |

## Files to Read First Next Session

1. `STATE.md` — Full state overview
2. `.planning/HANDOFF.md` — This file
3. `dataset/curated_perf_commits.json` — The 9 curated commits for the benchmark run
4. `batch/run_benchmark.sh` — Benchmark runner (supports `--instance-id` for specific commits)

## Output Data Locations

All results are in `batch_results/benchmark_*_48889171/run_1/{app}/`:
- `benchmark_results.json` — structured results (success, duration, patch, etc.)
- `agent.log` — runner stdout (mostly NVM/setup)
- `benchmark.log` — Python benchmark runner log
- `{app}__base_agent_realtime.log` — agent's real-time output (verbose for SWE-agent, minimal for Codex/OpenCode)
- `{app}__base_prompt.txt` — the prompt sent to the agent
- `workspaces/{app}__base/` — the workspace where the agent worked

Trajectories in `trajectories/benchmark_*_48889171/run_1/{app}/{app}__base.jsonl`.

## Key Observations for Next Session

1. **Laghos produces no patches** — all 4 frameworks finish fast but none change code. Laghos may already be well-optimized or the prompt may not guide well enough.
2. **Lulesh is the hardest** — only OpenCode and OpenHands succeed. Investigate Codex/SWE-agent trajectories to understand failure modes.
3. **SWE-agent whitespace issue** — on Lulesh, SWE-agent reformats entire files (1.9M chars, 124K insertions). This is a known but unresolved issue.
4. **OpenHands Kripke generates huge patches** — 4.5M chars with 48K insertions but 0 deletions. Likely includes build artifacts in git diff. May need to filter build directories.
5. **OpenCode non-zero exit NOT observed** — all 4 OpenCode instances succeeded. The bug may have been fixed or is intermittent.

## Running the Curated Commits Benchmark

```bash
# Interactive — preferred
salloc --nodes 4 --qos interactive --time 04:00:00 --constraint gpu --gpus-per-node=4 --account m2404

# Inside allocation:
source ~/.openai_env && source ~/envs/sweagent/bin/activate
bash batch/run_benchmark.sh --framework codex --external-model --model-name openai/gpt-4o-mini
# (no --base flag = benchmark mode = uses curated_perf_commits.json)
```

Note: benchmark mode checks out specific commits, runs agent, compares to expert patch. Different from base mode.

## Branch State

- **Current branch**: `local`
- **Latest commit**: `c8cd35d7` — Clarify next task: E2E validation (base mode)
- **No uncommitted tracked changes**
