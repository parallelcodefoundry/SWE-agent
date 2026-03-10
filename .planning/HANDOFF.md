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
- [x] Goal 16: Analyze historical logs for intermediate speedups (s41 + s46 all frameworks)
- [x] Goal 17: Design best-state tracking approach (harness-level snapshotting)
- [x] Goal 18: Validate GPA CUDA 12.9 on compute node (hotspot + gaussian PASSED)
- [ ] Goal 19: Check session 48 job results (NEXT SESSION)
- [ ] Goal 20: Implement best-state tracking in harness scripts (NEXT SESSION)
- [ ] Goal 21: Submit full SWE-agent/OpenCode runs if tests pass (NEXT SESSION)

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

## Key Log Analysis Findings (Late Session 48)

### Kripke 4 speedup values = per-kernel-phase, NOT per-rank
The `kripke_run` harness reports 4 speedups: Solve (overall), SweepSolver, LTimes, LPlusTimes. See lines 434-464 of `tools/kripke_harness/bin/kripke_run`.

### Session 46 Kripke: Agent achieved 20.93x then intentionally reverted
- Agent fused initialization of ALL 3 kernels (LTimes, LPlusTimes, Scattering)
- Removed 3 `kConst()` calls from `SteadyStateSolver.cpp` (these use `RAJA::seq_exec` → expensive CHAI GPU↔CPU transfers)
- Got 10.71x/1.89x/20.93x/2.60x (per-kernel) with CORRECTNESS: PASSED
- But agent detected wrong physics: particle count converged to 7.65e7 instead of 1.41e8
- Root cause: Scattering.cpp was reverted to original (uses `+=`) but `kConst(phi_out, 0.0)` was still removed → stale accumulation
- Agent restored `kConst(phi_out, 0.0)`, kept only LTimes + LPlusTimes fused init → safe 2.03x
- **Critical finding**: Harness CORRECTNESS check (3 values) too weak — missed the physics error
- Agent reasoning at **line 273** of `kripke__base_agent_realtime.log` (context compaction summary)

### Session 46 Other Frameworks: Zero intermediate speedups
- Codex/OpenCode/SWE-agent with Qwen: no edits attempted (known root causes now fixed)
- OpenHands: QS 1.00x (baseline match), Lulesh crashed, rest incomplete

### Session 41 Lost Speedups
- Laghos: intermediate 1.10x > final 1.0664x (measurement noise from CG tuning)
- QS: achieved 1.29x with device LTO but validation timed out → reported null

### Best-State Tracking Design (NOT YET IMPLEMENTED)
**Concept**: Harness saves best patch on each PASSED run, benchmark_runner recovers after timeout.
**Hook points**:
- `kripke_run` line ~727 (after `format_speedup_summary`) — save `git diff HEAD` + speedup
- `hpc_benchmark_runner.py` line ~687 (after `run_agent`) — check `.best_patch.diff` vs current
- All 4 harness scripts need same logic (kripke_run, laghos_run, lulesh_run, qs_run)
**Also needed**:
- Stronger Kripke correctness: particle count convergence (compare iter-by-iter convergence profile)
- Turn/time budget in harness output (agent sees "Best: 1.4x | Run 3/N | ~40 min remaining")

## Specific Next-Session Tasks

### Task A: Check Session 48 Job Results (HIGHEST PRIORITY)
Check `squeue -u krydzy` then `batch_results/` for completed jobs:
- 49892015/49892016: SWE-agent parse mode tests (xml_function_calling vs thought_action)
- 49892017: OpenCode small_model test
- 49891957/49892081: Claude Code LLNL (no/with profiling)
- 49891958: Codex + gpt-5.3-codex
- 49891960: Claude Code GPA

### Task B: Implement Best-State Tracking
1. Add `.best_patch.diff` + `.best_speedup` saving to all 4 `*_run` harness scripts
2. Add best-state recovery to `hpc_benchmark_runner.py:_validate_agent_changes()`
3. Add status line to harness output: "Best speedup: X.XXx | Run N"
4. Strengthen Kripke correctness check (particle count convergence)

### Task C: Submit Full Runs Based on Test Results
- If parse mode test passes → submit SWE-agent + Qwen for all 4 LLNL apps
- If small_model works → submit OpenCode + Qwen for all 4 LLNL apps

## Session 48 Commits

1. `6aff1565` — Session 48 Phase 1: Fix root causes for benchmark resubmission
2. `050209a3` — Add SWEAGENT_PARSE_OVERRIDE env var for A/B testing parse modes
3. `ddc32744` — Save session 48 state — 7 benchmark jobs submitted
