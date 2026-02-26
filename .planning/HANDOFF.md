# HANDOFF — Session 27: Bug Fixes + Timeout Tuning + Production Runs

Last updated: 2026-02-25 (session 27)

## Current Phase

**Fixed 6 bugs and 3 timeout issues. First production vLLM runs submitted. Sweagent vLLM job running, 4 more queued. Interactive verification in progress.**

## Goal Progress (Session 27 Checklist)

- [x] Goal 1: Fix Kripke submodule symlink after rsync
- [x] Goal 2: Fix gpt-4.1-mini empty tool_calls crash
- [x] Goal 3: Fix vLLM model name mismatch (Codex/OpenCode)
- [x] Goal 4: Fix rsync timeout (120→300s)
- [x] Goal 5: Fix mpirun --oversubscribe for kripke_run
- [x] Goal 6: Bump per_instance_call_limit 50→200
- [x] Goal 7: Bump OpenHands max_iterations 50→200
- [x] Goal 8: Add total_execution_timeout: 3600 to all HPC configs
- [x] Goal 9: Submit 5 sbatch vLLM production runs
- [x] Goal 10: Launch interactive verification
- [ ] Goal 11: Check other framework timeout limits (OpenHands, Codex, OpenCode)
- [ ] Goal 12: Analyze completed benchmark results
- [ ] Goal 13: Investigate vLLM inference speed

## Commits This Session (7 commits)

| Commit | Description |
|--------|-------------|
| `616da3fe` | Fix Kripke submodule symlink + empty tool_calls |
| `79ad85b8` | Bump call limits 50→200 |
| `b559729e` | Fix vLLM model name for Codex/OpenCode |
| `80f82570` | Bump rsync timeout 120→300s |
| `b1834f03` | Add --oversubscribe to kripke_run mpirun |
| `7c9bcd71` | Add total_execution_timeout: 3600 |
| (pending) | STATE.md update |

## Active SLURM Jobs

| Job ID | Framework | Model | Mode | Status |
|--------|-----------|-------|------|--------|
| 49385453 | sweagent | vLLM gpt-oss-120b | base/LLNL | RUNNING |
| 49385456 | openhands | vLLM gpt-oss-120b | base/LLNL | PENDING |
| 49385461 | claude | Anthropic API | base/LLNL | PENDING |
| 49387755 | codex | vLLM gpt-oss-120b | base/LLNL | PENDING |
| 49387756 | opencode | vLLM gpt-oss-120b | base/LLNL | PENDING |

**Note**: These runs do NOT have the total_execution_timeout fix (committed after submission). Sweagent results may show premature termination. Codex/OpenCode DO have the model name fix.

## Known Issues for Next Session

### Must Address
1. **Other framework timeout limits** — Check if OpenHands, Codex, OpenCode have similar execution time limits that need bumping:
   - OpenHands: `no_change_timeout_seconds=600` in `openhands_runner.py` — may kill agent if it's building for >10 min without visible changes
   - Codex: `CODEX_DEFAULT_EXEC_TIMEOUT_MS=600000` (10 min per command) — probably fine
   - OpenCode: Check if there's a session/execution timeout
   - Claude Code: `--max-turns 200` — probably fine

2. **vLLM gpt-oss-120b inference speed** — ~2 min per API call. At 200 call limit, a full run would take ~400 min (6.7 hours) — way over the 3600s session timeout. Options:
   - Increase GPU memory utilization (currently 0.60)
   - Check if TP=4 is optimal for this model
   - Consider using gpt-4.1-mini via external API for faster iteration (accepts lower quality)

3. **Resubmit all runs** after confirming timeout fix works — current batch may produce partial results

### Observations from Results So Far
- **gpt-4.1-mini** (external API): Fast (~$0.12/instance), but too weak for CUDA/RAJA code. Couldn't handle template metaprogramming. Made syntax errors.
- **gpt-oss-120b** (vLLM): Very slow inference. Quicksilver hit 1800s execution timeout at only 20 API calls. Other apps may fare better if builds are faster.
- **Lulesh sweagent/vLLM**: +124,567 lines — agent dumped huge content instead of making surgical edits. Model may be hallucinating.

## Files to Read First (Next Session)

1. `STATE.md` — Full session 27 state
2. `squeue -u krydzy` — Check if jobs completed
3. `batch_results/benchmark_20260225_223943_49385453/` — Sweagent vLLM results
4. `batch_results/interactive_v2_*/` — Interactive verification results
5. `.planning/HANDOFF.md` — This file

## Files Modified This Session

| File | Change |
|------|--------|
| `sweagent/agent/models.py` | Filter empty tool_calls arrays (line 863) |
| `batch/hpc_benchmark_runner.py` | Kripke submodule symlink + rsync timeout 300s |
| `batch/frameworks/codex.py` | vLLM model name `openai/gpt-oss-120b` |
| `batch/frameworks/opencode.py` | vLLM model name `openai/gpt-oss-120b` |
| `batch/frameworks/openhands.py` | max_iterations 50→200 |
| `tools/kripke_harness/bin/kripke_run` | --oversubscribe for mpirun |
| `config/hpc/*.yaml` (10 files) | call_limit 200, total_execution_timeout 3600 |
| `STATE.md` | Updated |
| `.planning/HANDOFF.md` | Updated |
