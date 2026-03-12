# Handoff — Session 50

Last updated: 2026-03-12

## What We Were Implementing and Why

Session 50 focused on: rebuilding Lulesh with MPI, fixing GPA build failures, running pre-flight validation on all framework+model combos, and submitting a large batch of benchmark jobs (10 total).

## Approach Chosen

- Parallel background agents for pre-flight validation (4 frameworks), QS patch analysis, GPA investigation, Lulesh rebuild
- Fix-then-submit: applied all fixes before submitting jobs
- Scheduled Claude Code runs +3hr via nohup+sleep (atd not available on Perlmutter)

## Goal Progress

- [x] Goal 0: Load state from session 49
- [x] Goal 1: Rebuild pristine Lulesh with MPI on compute node
- [x] Goal 2: Recalibrate Lulesh timing (i=5000→i=2000 for ~63s with real MPI)
- [x] Goal 3: Add OMPI_MCA_btl fix for MPI finalization segfault
- [x] Goal 4: Analyze QS profiling vs no-profiling patches (vault batching = real bottleneck)
- [x] Goal 5: Pre-flight Codex + gpt-5.3-codex (PASS)
- [x] Goal 6: Pre-flight SWE-agent + Qwen (PASS)
- [x] Goal 7: Pre-flight OpenHands + Qwen (PASS, patched FORCE_STRING_SERIALIZER)
- [x] Goal 8: Pre-flight Claude Code + GPA (PASS, lavaMD fix)
- [x] Goal 9: Investigate GPA build failures (5 apps fixed)
- [x] Goal 10: Fix SAFE_MODEL naming in run_benchmark.sh
- [x] Goal 11: Expand profiling prompt (PROFILING_DESCRIPTION + GPA prompt)
- [x] Goal 12: Submit all 10 benchmark jobs
- [x] Goal 13: Commit all changes
- [ ] Goal 14: Analyze session 50 job results (NEXT SESSION)
- [ ] Goal 15: Diagnose gptoss120b failures — 3 jobs failed in ~4 min (NEXT SESSION)
- [ ] Goal 16: Diagnose SWE-agent+Qwen LLNL early exit — 10 min (NEXT SESSION)
- [ ] Goal 17: Implement best-state tracking on feature branch (NEXT SESSION)
- [ ] Goal 18: Investigate OpenCode + Qwen tool calling issue (NEXT SESSION)

## Files Modified This Session

### SWE-agent repo (committed as `da0d04e4`)
- `CLAUDE.md` — Updated Lulesh timing: i=2000, ~63s
- `batch/run_benchmark.sh` — SAFE_MODEL uses MODEL_NAME when available
- `batch/hpc_benchmark_runner.py` — lavaMD `.lower()` fix in `_run_gpa_driver()`
- `batch/frameworks/prompt.py` — Added microbench_code/check_profiling_ready/system_summary to PROFILING_DESCRIPTION; expanded GPA profiling prompt; updated SWE-agent instance hint
- `tools/gpa_harness/bin/gpa_test` — lavaMD `.lower()` fix in DriverConfig
- `tools/lulesh_harness/bin/lulesh_run` — DEFAULT_ITERATIONS 5000→2000, OMPI_MCA_btl=^smcuda

### GPA-Benchmark repo (committed as `dd38308`)
- `gpa_bench_driver/driver_src/driver_config.py` — Prepend cuda_home/bin to PATH
- `rodinia/b+tree/Makefile` — K&R C warning suppression flags + `-allow-unsupported-compiler`
- `rodinia/backprop/Makefile` — K&R C warning suppression flags
- `rodinia/srad/srad_v1/Makefile` — Use `$(CC)` instead of bare `nvcc`

### OpenHands SDK (installed package, NOT in git)
- `/global/homes/k/krydzy/envs/sweagent/lib/python3.13/site-packages/openhands/sdk/llm/utils/model_features.py`
  - Added "qwen" and "gpt-oss" to FORCE_STRING_SERIALIZER_PATTERNS (lines 101-102)
  - Prevents structured content crash when vLLM-hosted models receive tool results

## Files to Read First Next Session

- `STATE.md` — Full session 50 summary
- `.planning/HANDOFF.md` — This file
- `batch_results/` — Check for new result directories from jobs 49936642-49936649, 49940919-49940920
- For gptoss120b failures: `batch_results/*gpt-oss*49936647/` (or similar) — check agent.log for crash reason
- For SWE-agent early exit: `batch_results/*Qwen*49936643/` — check why it finished in 10 min

## Job Results to Analyze (Session 50 Submissions)

| Job ID | Framework | Model | Apps | Status | Duration | Notes |
|--------|-----------|-------|------|--------|----------|-------|
| 49936642 | Codex | gpt-5.3-codex | LLNL | COMPLETED | 01:28:56 | First successful Codex run! |
| 49936643 | SWE-agent | Qwen3-Coder-Next | LLNL | COMPLETED | 00:10:34 | Suspiciously fast — crashed? |
| 49936644 | SWE-agent | Qwen3-Coder-Next | GPA | TIMEOUT | 04:00:23 | Ran full walltime |
| 49936645 | OpenHands | Qwen3-Coder-Next | LLNL | COMPLETED | 02:16:26 | First OpenHands+Qwen test |
| 49936646 | OpenHands | Qwen3-Coder-Next | GPA | TIMEOUT | 04:00:24 | Ran full walltime |
| 49936647 | OpenHands | gptoss120b | GPA | FAILED | 00:04:09 | Crashed fast — vLLM? |
| 49936648 | SWE-agent | gptoss120b | GPA | FAILED | 00:04:27 | Crashed fast — vLLM? |
| 49936649 | OpenCode | gptoss120b | GPA | FAILED | 00:03:25 | Crashed fast — vLLM? |
| 49940919 | Claude Code | Anthropic | LLNL | COMPLETED | 01:06:15 | Scheduled +3hr |
| 49940920 | Claude Code | Anthropic | GPA | TIMEOUT | 04:00:00 | Scheduled +3hr |

## Gotchas and Decisions

### Lulesh Timing Was Always Wrong
- Previous "51-52s" measurements used a non-MPI binary where ranks ran independently
- With real MPI communication, i=5000 takes ~131s → recalibrated to i=2000 (~63s)
- ALL previous Lulesh benchmark results are invalid (agents were optimizing a single-GPU program)

### QS Profiling Analysis (Amdahl's Law in Action)
- GPU kernel = only 2% of runtime (1.06s / 59.5s)
- No-profiling agent: optimized wrong 2% (GPU micro-opts), got 1.02x
- With-profiling agent: saw 195 GPU launches vs 77,419 timer calls → 99.7% empty vaults
- Fix: consolidate particles into single batch (2-line change) → 1.65x
- This validates the entire benchmark design premise

### OpenHands FORCE_STRING_SERIALIZER Is an Installed Package Patch
- `/global/homes/k/krydzy/envs/sweagent/lib/python3.13/site-packages/openhands/sdk/llm/utils/model_features.py`
- NOT in git — will be lost if OpenHands is reinstalled
- Added "qwen" and "gpt-oss" patterns
- Any future vLLM-hosted model needs an entry here too

### gptoss120b Model Needs Investigation
- All 3 gptoss120b jobs (49936647-49936649) failed in ~4 min
- Likely vLLM server startup failure — model is 120GB, may need TP>4 or larger GPU allocation
- Or the model name `openai/gpt-oss-120b` isn't in MODEL_REGISTRY (uses default settings)
- Check logs to determine root cause before resubmitting

### OpenCode + Qwen Still Broken
- OpenCode expects tool calls via API `tool_calls` field
- Qwen emits `<tool_call>` XML in text content → OpenCode treats as plain text → exits after 1 step
- This is NOT the same issue as the OpenHands structured content fix
- Needs investigation: is vLLM `qwen3_coder` parser not extracting XML into tool_calls?

### GPA Build Fixes Are Local, Not Upstream
- Upstream GPA-Benchmark has 13 unmerged commits (none fix our issues)
- Our fixes (PATH, K&R flags, srad, lavaMD) are local commits
- If we pull upstream, may need to rebase/merge

### nohup+sleep for Scheduling
- `atd` not running on Perlmutter login nodes
- Used `nohup bash -c 'sleep 10800 && ...' &` (PID 2080497)
- Claude Code jobs successfully submitted as 49940919 + 49940920

## Session 50 Commits

1. SWE-agent repo: `da0d04e4` — WIP: Session 50
2. GPA-Benchmark repo: `dd38308` — Fix 5 GPA app build failures on Perlmutter
