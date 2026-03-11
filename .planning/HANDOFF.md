# Handoff — Session 49

Last updated: 2026-03-11

## What We Were Implementing and Why

Session 49 analyzed all 7 session 48 benchmark jobs, identified 3 infrastructure bugs, fixed them, and increased timeouts/steps for all frameworks. Also discovered the Lulesh pristine binary has been missing MPI across ALL sessions.

## Approach Chosen

- Deep analysis via parallel background agents (5 for job results, 4 for root causes)
- Direct bug fixes (Codex config, GPA kwarg, Lulesh MPI)
- Timeout increase across all frameworks (1hr→2hr, 200→300 steps)
- No prompt changes (user decided against hotspot hints and time tracking)

## Goal Progress

- [x] Goal 0: Load state, check job status
- [x] Goal 1: Analyze all 7 session 48 job results (deep dive)
- [x] Goal 2: Fix Codex config crash (OPENAI_BASE_URL env var bridge)
- [x] Goal 3: Fix GPA retain_nsys_profiles kwarg (committed in GPA-Benchmark)
- [x] Goal 4: Fix Lulesh MPI build (MPICH_DIR from OPENMPI_ROOT)
- [x] Goal 5: Increase SESSION_TIMEOUT to 7200s for all frameworks
- [x] Goal 6: Increase max turns/calls to 300 for all frameworks
- [x] Goal 7: Analyze Kripke s41 patches (kConst seq_exec→cuda_exec = legitimate opt)
- [x] Goal 8: Analyze Lulesh MPI root cause (pristine binary genuinely lacks MPI)
- [x] Goal 9: Analyze SWE-agent Qwen reasoning (pure filler, model limitation)
- [x] Goal 10: Compare Claude Code diffs across sessions (QS missing tally batching)
- [x] Goal 11: Check s48 with_profiling results (QS 1.65x vs 1.02x without)
- [x] Goal 12: Commit all fixes
- [ ] Goal 13: Rebuild pristine Lulesh on compute node (NEXT SESSION)
- [ ] Goal 14: Resubmit Codex + gpt-5.3-codex LLNL (NEXT SESSION)
- [ ] Goal 15: Resubmit Claude Code GPA (NEXT SESSION)
- [ ] Goal 16: Resubmit full benchmark matrix with both profiling modes (NEXT SESSION)
- [ ] Goal 17: Implement best-state tracking (NEXT SESSION)
- [ ] Goal 18: Analyze 49892081 QS with_profiling patch vs no_profiling patch (NEXT SESSION)

## Files Modified This Session

- `batch/frameworks/base.py` — SESSION_TIMEOUT 3600→7200
- `batch/frameworks/claude.py` — --max-turns 200→300
- `batch/frameworks/codex.py` — Removed -c model_providers.openai.* flags, added OPENAI_BASE_URL bridge in shell preamble
- `batch/frameworks/openhands.py` — max_iterations 200→300 (both config and CLI)
- `batch/hpc_benchmark_runner.py` — Agent subprocess timeout 3900→7500
- `config/hpc/*.yaml` (11 files) — per_instance_call_limit 200→300
- `tools/lulesh_harness/bin/lulesh_build` — Set MPICH_DIR from OPENMPI_ROOT
- `tools/lulesh_harness/bin/lulesh_run` — Set MPICH_DIR from OPENMPI_ROOT in get_pristine_executable()
- GPA-Benchmark repo (`/pscratch/sd/k/krydzy/GPA-Benchmark`): commit `0a6aece` — removed retain_nsys_profiles kwarg

## Files to Read First Next Session

- `STATE.md` — Full session 49 summary
- `.planning/HANDOFF.md` — This file, goal checklist
- `batch/frameworks/codex.py` lines 42-55 — Codex first-party model config (verify fix)
- `tools/lulesh_harness/bin/lulesh_build` lines 198-210 — MPICH_DIR bridging (verify)
- `tools/lulesh_harness/bin/lulesh_run` lines 190-202 — Same MPICH_DIR fix
- `batch_results/claude_openai-gpt-oss-120b_20260311_005846_49892081/` — with_profiling results (QS 1.65x patch to analyze)

## Gotchas and Decisions

### Critical: Lulesh Pristine Binary Has No MPI
- ALL previous Lulesh results across ALL sessions were affected
- Pristine binary at `/pscratch/sd/k/krydzy/SWE-agent/Lulesh/cuda/lulesh` links NO libmpi
- Root cause: Makefile uses `MPICH_DIR` for MPI paths, but Perlmutter OpenMPI sets `OPENMPI_ROOT` instead
- Fix applied to `lulesh_build` and `lulesh_run` but **pristine binary needs rebuild on compute node**
- Verify after rebuild: `readelf -d Lulesh/cuda/lulesh | grep mpi` should show `libmpi.so.40`

### Profiling Is The Key Differentiator
- QS: 1.65x WITH profiling vs 1.02x WITHOUT (same model, same session)
- No-profiling agent finds micro-opts (sincos, rsqrt) but misses atomic contention
- With-profiling agent (presumably) identified atomic bottleneck via profiling data
- **Must analyze 49892081 QS patch** to confirm what profiling-guided optimizations were applied
- This validates the entire benchmark design premise

### Kripke kConst/kCopy Is Legitimate Optimization
- Upstream Kripke uses `RAJA::seq_exec` for utility functions (kConst, kCopy) intentionally
- Agent changing to `RAJA::cuda_exec<256>` eliminates CPU↔GPU roundtrips via CHAI
- This is a real optimization, not a setup error
- Main compute kernels (LTimes, LPlusTimes, etc.) already use CUDA exec policies correctly
- Kripke pristine build is correct: CHAI=ON, CUDA=ON, MPI=ON, Release mode

### SWE-agent + Qwen Is A Model Limitation
- Both xml_function_calling and thought_action modes: 200+ steps, 0 edits
- Model generates 92.5% filler thoughts ("let me look at...")
- Views same 4 functions 30-40 times without analysis
- Increasing call limit to 300 unlikely to help — agent just loops longer
- May need fundamentally different approach (forced edit after N views?)

### Session 48 Job Results Were From Both Profiling Modes
- s41 had `run_1_with_profiling/` and `run_1_no_profiling/` subdirs
- s46 used `run_1/` (single mode, no_profiling)
- s48 submitted separate jobs per mode (49891957=no_prof, 49892081=with_prof)
- Result dirs at `/global/homes/k/krydzy/SWE-agent/batch_results/` (s41) and `/pscratch/sd/k/krydzy/SWE-agent/batch_results/` (s46+)

### OpenCode + Qwen: Separate Issue from small_model
- small_model fix worked (no gpt-5-nano 404)
- But agent exits after 1 step — Qwen emits `<tool_call>` XML in text content
- OpenCode treats it as plain text, not a real tool call → immediate stop
- Needs investigation: is this an OpenCode bug or a vLLM parser issue?

## Resubmission Plan (Next Session)

### Step 1: Rebuild Lulesh (compute node required)
```bash
salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m5083
module load python cmake openmpi/5.0.7 cudatoolkit/12.4
cd /pscratch/sd/k/krydzy/SWE-agent
rm Lulesh/cuda/lulesh Lulesh/cuda/src/*.o  # clean old build
source ~/envs/sweagent/bin/activate
./scripts/setup_apps.sh --lulesh
readelf -d Lulesh/cuda/lulesh | grep mpi  # verify libmpi.so.40
./scripts/reset_test_repos.sh --lulesh
```

### Step 2: Submit Fixed Jobs
```bash
# From login node:
source ~/.openai_env

# Codex + gpt-5.3-codex (both modes, config fix applied)
bash batch/run_benchmark.sh --base --kripke --laghos --lulesh --quicksilver --framework codex --external-model --model-name gpt-5.3-codex

# Claude Code GPA (retain_nsys fix in GPA-Benchmark)
bash batch/run_benchmark.sh --base --gpa --framework claude --skip-vllm

# Claude Code LLNL (both modes, Lulesh MPI fix, 2hr timeout)
bash batch/run_benchmark.sh --base --kripke --laghos --lulesh --quicksilver --framework claude --skip-vllm

# SWE-agent + Qwen (both modes, 300 calls, xml_function_calling)
bash batch/run_benchmark.sh --base --kripke --laghos --lulesh --quicksilver --framework sweagent --external-model --model-name Qwen/Qwen3-Coder-Next-FP8
```

### Step 3: Analyze with_profiling QS Patch
Compare patches:
- No profiling: `/pscratch/sd/k/krydzy/SWE-agent/batch_results/claude_openai-gpt-oss-120b_20260310_115433_49891957/run_1/quicksilver/quicksilver__base_agent.patch`
- With profiling: `/pscratch/sd/k/krydzy/SWE-agent/batch_results/claude_openai-gpt-oss-120b_20260311_005846_49892081/run_1/quicksilver/quicksilver__base_agent.patch`

## Session 49 Commits

1. `b99bae0f` — WIP: Session 49 — fix infra bugs, increase timeouts, analyze s48 results
2. GPA-Benchmark `0a6aece` — Fix postprocess_nsys_app() retain_nsys_profiles kwarg mismatch
