# STATE.md — Current Project State

Last updated: 2026-03-04 (session 40)

## Last Session (Session 40)

### Fix 6 Session-39 Infrastructure Bugs + Cleanup

Analyzed session 39 benchmark results and found all Qwen jobs routed to wrong model (gptoss120b) due to vLLM model switching bug (already fixed in run_benchmark.sh). Diagnosed 6 downstream bugs that would prevent successful runs even with correct model routing. Fixed all 6 and cleaned up 6.4GB of failed/duplicate results.

**Bug fixes (4 framework model routing):**
1. **sweagent.py:264** — Added `openai/` LiteLLM prefix for external models
2. **codex.py:62** — Use full `self.model_name` (not stripped `model_id`) for vLLM
3. **opencode.py:37-57** — Always use `openai` provider + `@ai-sdk/openai` for vLLM models
4. **openhands.py:91** — Added `openai/` LiteLLM prefix for external models

**Bug fixes (2 data quality):**
5. **hpc_benchmark_runner.py** — Commit `.gitignore` in workspace so it doesn't appear in agent patches (with git identity fallback + staged-changes check)
6. **hpc_benchmark_runner.py** — Changed `--validation-runs` default 10→3 (QS timeout: 1800s > 1680s)

**Code review follow-up fixes:**
- Class default `validation_runs: int = 10` → `3` in `__init__` to match CLI
- OpenCode `removeprefix("openai/")` guard against double-prefix
- Git commit robustness: check for staged changes before committing + explicit git identity

**Cleanup:** Deleted 8 batch_results dirs (~6.4GB) + 16 SLURM logs for failed/duplicate jobs (49641327-49641346).

### Session 39 Result Analysis

- **All 16 "Qwen" jobs** actually ran gptoss120b (vLLM model switching bug)
- **Only SWE-agent (49641358)** made real code changes (Laghos pow→mul, 0.997x speedup)
- **OpenCode (49641359)** connected but made no source changes
- **OpenHands (49641360)** hit Pydantic crash mid-session
- **All non-SWE-agent "passes"** are false positives — baseline runs with runner-injected .gitignore patches

## Active Experiments

### Valid gptoss120b Results (Keep)
| Job ID | Framework | Apps | Status |
|--------|-----------|------|--------|
| 49641358 | sweagent | LLNL | Real changes (Laghos pow→mul, 0.997x) |
| 49641359 | opencode | LLNL | Connected, no source changes |
| 49641360 | openhands | LLNL | Pydantic crash mid-session |
| 49641364 | claude | LLNL | TBD |
| 49641361-63 | sweagent/opencode/openhands | GPA | TBD |
| 49641366 | claude | GPA | TBD |

### Deleted (Session 40 Cleanup)
- 49641327, 49641343 — SWE-agent setup failures
- 49641328-30, 49641344-46 — Duplicate gptoss120b runs (intended Qwen)

## Branch State

- **Current branch**: `dev` (23 commits ahead of `origin/dev`)
- **Latest commit**: `9ba3fed6` — Fix 6 session-39 infrastructure bugs + cleanup
- **Working tree**: Clean (only untracked: Laghos char scripts, xyz.asc, output.{out,txt})

## All Infrastructure Fixes — Complete

- [x] All previous fixes (sessions 33-39)
- [x] SWE-agent missing `openai/` LiteLLM prefix (session 40)
- [x] Codex strips HuggingFace org prefix (session 40)
- [x] OpenCode hardcodes `@ai-sdk/{provider}` npm package (session 40)
- [x] OpenHands model name needs `openai/` prefix (session 40)
- [x] .gitignore contamination in agent patches (session 40)
- [x] Quicksilver validation timeout too short (session 40)

## Open Issues / TODOs

### Actionable
- [ ] **Re-submit Qwen benchmark runs** — All 16 Qwen jobs ran wrong model. Need to re-run with fixed framework code.
- [ ] **Check remaining gptoss120b results** — Jobs 49641361-63, 49641364, 49641366 not yet analyzed
- [ ] **Submit Codex gptoss120b external-model** — Needs OPENAI_API_BASE and OPENAI_API_KEY env vars
- [ ] **Empty tool_calls [] from Qwen models** — Monitor for crashes on re-submission

### Persistent Issues
- [ ] **Quicksilver consistent timeout** — All frameworks timeout on QS
- [ ] **Lulesh systematic bias** — N/C runs show ~0.94x consistently
- [ ] **Laghos timing variance** — N/C range 0.98x-1.23x too high
- [ ] **Codex gpt-4.1-mini single-turn exit** — Model exits with needs_follow_up=false
- [ ] **Qwen3.5-122B-A10B-FP8** — BLOCKED: needs 8 GPUs or 4x80GB nodes

## Recent Decisions

- 2026-03-04 (s40): All 4 framework launchers need `openai/` prefix for LiteLLM routing of external models
- 2026-03-04 (s40): Codex uses full `self.model_name` (e.g. `Qwen/Qwen3-Coder-Next-FP8`) because `model_provider=ext` is set separately
- 2026-03-04 (s40): OpenCode always uses `@ai-sdk/openai` npm package — all external models are served via OpenAI-compatible API
- 2026-03-04 (s40): .gitignore committed in workspace to prevent patch contamination
- 2026-03-04 (s40): validation-runs default 10→3 to fix QS timeout (3 runs sufficient for median)
- 2026-03-04 (s39): vLLM container per-model: v0.11.0 for gptoss, nightly for Qwen
- 2026-03-04 (s39): --enforce-eager added to all vLLM launches

## Next Steps

1. **Re-submit Qwen benchmark runs** — Now that framework routing bugs are fixed
2. **Analyze remaining gptoss120b results** — Jobs 49641361-66
3. **Submit Codex gptoss120b** — Source API keys first
4. **Address Laghos timing variance and Lulesh measurement bias**
