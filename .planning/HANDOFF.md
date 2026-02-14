# HANDOFF.md — Session 15 Summary

Last updated: 2026-02-13 (session 15)

## What Was Done

Ran the full 4×4 matrix validation: all 4 frameworks (Codex, SWE-agent, OpenCode, OpenHands) × all 4 apps (Kripke, Laghos, Lulesh, Quicksilver) in `--base` mode using gpt-4o-mini via the OpenAI API. Single 4-node interactive allocation (Job 48889171), ~2h48m total.

## Goal Progress

- [x] Goal 1: Reset test repos and pre-flight checks
- [x] Goal 2: Run Codex on all 4 apps (3/4 success, Lulesh failed)
- [x] Goal 3: Run SWE-agent on all 4 apps (3/4 success, Lulesh failed)
- [x] Goal 4: Run OpenCode on all 4 apps (4/4 success — perfect)
- [x] Goal 5: Run OpenHands on all 4 apps (4/4 success — perfect)
- [x] Goal 6: Compile results matrix (14/16 overall)
- [x] Goal 7: Save state
- [ ] Goal 8: Curated performance commits benchmark (**NEXT SESSION**)
- [ ] Goal 9: GPA-Benchmark + SWE-fficiency integration
- [ ] Goal 10: Investigate Lulesh failures for Codex and SWE-agent

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
| `STATE.md` | Updated with session 15 results |
| `.planning/HANDOFF.md` | This file |
| `batch_results/run_full_matrix.sh` | Wrapper script to chain all 4 frameworks (untracked) |

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
