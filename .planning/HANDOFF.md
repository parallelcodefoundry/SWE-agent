# Handoff — Session 48

Last updated: 2026-03-10

## What We Were Implementing and Why

Session 48 fixed all 6 root causes from session 47's analysis and submitted 7 benchmark jobs to test the fixes. Focus: MPI warning in prompts, SWE-agent xml_function_calling for Qwen, OpenCode small_model, Codex+Qwen dropped.

## Approach Chosen

- Phase 1: All code changes on login node, committed in 2 commits
- Phase 2: GPA validation on compute node (via perlmutter-executor agent), parse mode tests submitted as batch jobs
- Phase 3: Submitted 7 benchmark jobs covering Claude Code (2 configs), Codex, SWE-agent (2 parse modes), OpenCode

## Goal Progress

- [x] Goal 0: Load state, check job status
- [x] Goal 1: Add session 46 Claude Code results to results_summary.json (19 entries)
- [x] Goal 2: Add MPI_RUNTIME_GUIDANCE to prompts (all frameworks, all apps)
- [x] Goal 3: SWE-agent xml_function_calling parse mode for Qwen + env var override
- [x] Goal 4: OpenCode small_model config for title gen
- [x] Goal 5: Document Codex+Qwen incompatibility (permanently dropped)
- [x] Goal 6: Update skills docs (Codex, OpenCode, SWE-agent)
- [x] Goal 7: Commit Phase 1 changes
- [x] Goal 8: Submit Claude Code LLNL no_profiling (49891957)
- [x] Goal 9: Submit Claude Code LLNL with_profiling (49892081)
- [x] Goal 10: Submit Codex + gpt-5.3-codex LLNL (49891958)
- [x] Goal 11: Submit Claude Code GPA (49891960)
- [x] Goal 12: Submit SWE-agent parse mode test A: xml_function_calling (49892015)
- [x] Goal 13: Submit SWE-agent parse mode test B: thought_action (49892016)
- [x] Goal 14: Submit OpenCode small_model test (49892017)
- [x] Goal 15: Compare session 41 vs 46 Claude Code results
- [ ] Goal 16: Analyze session 48 job results (NEXT SESSION)
- [ ] Goal 17: Submit full SWE-agent/OpenCode runs if tests pass (NEXT SESSION)
- [ ] Goal 18: Update memory files with findings (NEXT SESSION)

## Files Modified This Session

- `batch/frameworks/prompt.py` — MPI_RUNTIME_GUIDANCE constant + 2 injection points
- `batch/frameworks/sweagent.py` — `_apply_parse_function_override()` method + SWEAGENT_PARSE_OVERRIDE env var
- `batch/frameworks/opencode.py` — small_model in both config branches
- `batch/frameworks/codex.py` — Codex+Qwen incompatibility docstring
- `batch_results/results_summary.json` — Session 46 Claude Code results (entry #19)
- `.claude/skills/codex-cli/references/internals.md` — wire_api=chat removed, Qwen incompatible
- `.claude/skills/opencode/references/architecture.md` — Title gen / small_model section
- `.claude/skills/swe-agent-framework/references/config-details.md` — Parse function types table

## Files to Read First Next Session

- `STATE.md` — Session 48 summary with job table
- Check `squeue -u krydzy` for completed jobs
- `batch_results/` for new output directories matching job IDs above
- Parse mode test results (49892015 vs 49892016) are the highest priority

## Gotchas and Decisions

- **Codex+Qwen is permanently incompatible** — wire_api=responses only, vLLM qwen3_coder parser only on /v1/chat/completions
- **XMLFunctionCallingParser handles Qwen's `<tool_call>` wrapper** — re.search() finds `<function=...>` inside it
- **"Agent run failed" = timeout** — Claude Code hits 60-min timeout but optimizations are valid
- **Session 41 Kripke 15.08x is inflated** — likely np=1 (pre-calibration), session 46 uses np=4
- **sbatch --export=ALL** passes env vars through, so SWEAGENT_PARSE_OVERRIDE works

## Specific Next-Session Investigation Tasks

### Task A: Analyze Parse Mode Test Results
**Job 49892015** (xml_function_calling) vs **49892016** (thought_action)
- Success criterion: at least 1 str_replace / file edit call
- Check agent trajectories for edit behavior
- Winner becomes default for Qwen

### Task B: Analyze All Session 48 Results
- Claude Code with profiling vs without (49892081 vs 49891957)
- Codex + gpt-5.3-codex performance (49891958)
- OpenCode small_model fix (49892017) — did title gen crash?
- GPA results (49891960)

### Task C: Submit Full Runs Based on Test Results
- If parse mode test passes → submit SWE-agent + Qwen for all 4 LLNL apps
- If small_model works → submit OpenCode + Qwen for all 4 LLNL apps

## Session 48 Commits

1. `6aff1565` — Session 48 Phase 1: Fix root causes for benchmark resubmission
2. `050209a3` — Add SWEAGENT_PARSE_OVERRIDE env var for A/B testing parse modes
