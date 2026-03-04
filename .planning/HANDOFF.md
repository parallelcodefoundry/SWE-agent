# HANDOFF — Session 37 → Session 38

Last updated: 2026-03-04 (session 37)

## What We Were Working On

Session 37: Created nsys_profile tool, aligned all profiling prompts/bundles, improved output naming, fixed ncu_profile basic mode, verified tool outputs. Discovered vLLM Qwen test must use podman-hpc container (not bare Python). Two subagents were still running at session end.

## Goal Progress
- [x] Goal 0: Prompt & bundle alignment (Phase 1) — ncu_profile + nsys_profile in all descriptions
- [x] Goal 1: Create nsys_profile SWE-agent tool (Phase 2) — tested on all proxy apps
- [x] Goal 2: Output naming improvement (Phase 3) — framework + model in dir name
- [x] Goal 3: Workspace cleanup improvements (Phase 4) — ncu/nsys report cleanup
- [x] Goal 4: Mark stale LLNL configs as legacy (8 files)
- [x] Goal 5: Fix ncu_profile basic mode (-s 0 -c 500) — committed, verification running
- [~] Goal 6: Verify ncu_profile -c 500 fix — subagent running at session end
- [~] Goal 7: Test profiling tools on GPA apps — subagent running at session end
- [ ] Goal 8: Test vLLM Qwen via podman-hpc container — MUST use container, not bare Python
- [ ] Goal 9: Submit Qwen benchmark runs (16 jobs) — BLOCKED on Goal 8
- [ ] Goal 10: Check session 36 benchmark results (9 jobs still queued)
- [ ] Goal 11: Cherry-pick SWE-agent upstream fixes (3 bugs)

## Running Subagents at Session End

1. **ncu-verify-and-gpa-test** (ac74377cbd3e3af4d) — verifying ncu_profile `-c 500` on Lulesh + testing both tools on GPA apps. Output at `/pscratch/sd/k/krydzy/SWE-agent/batch_results/profiling_verify/`.

## Key Commits (Session 37)

| Commit | Description |
|--------|-------------|
| `cd7a83f9` | Add nsys_profile tool, align profiling prompts, improve output naming and cleanup |
| `bd77fbbd` | Fix ncu_profile basic mode sample count and add MPI docs to nsys_profile |
| `45e7cceb` | Fix ncu_profile basic mode: -s 0 -c 500 to capture simulation kernels |

## Files Modified This Session

| File | Change |
|------|--------|
| `batch/frameworks/prompt.py` | Added ncu_profile + nsys_profile to PROFILING_DESCRIPTION, workflow steps, SWE-agent tools list, GPA profiling prompt |
| `batch/frameworks/sweagent.py` | Added tools/nsight_compute + tools/nsight_systems to PROFILING_BUNDLES |
| `batch/frameworks/base.py` | Added tools/nsight_systems/bin to PROFILING_TOOL_DIRS |
| `batch/run_benchmark.sh` | Output naming (framework+model), ncu/nsys cleanup, dir size logging |
| `config/hpc/gpa_with_profiling.yaml` | Updated system_template profiling tools + workflow, added nsight_systems bundle |
| `config/hpc/{kripke,laghos,lulesh,quicksilver}_{with,no}_profiling.yaml` (8 files) | Added legacy deprecation comment |
| `tools/nsight_systems/config.yaml` | NEW: nsys_profile SWE-agent tool definition |
| `tools/nsight_systems/bin/nsys_profile` | NEW: nsys profiling script (tested on all 4 proxy apps) |
| `tools/nsight_compute/bin/ncu_profile` | Fixed basic mode: -s 0 -c 500 (was -s 1 -c 5) |
| `tools/nsight_compute/config.yaml` | Updated docstring for new basic mode behavior |
| `.claude/skills/nsight-systems/SKILL.md` | Added tool integration section |
| `.claude/skills/nsight-compute/SKILL.md` | Updated basic mode description |

## Files to Read First Next Session

1. `STATE.md` — Full state overview
2. `.planning/HANDOFF.md` — This file
3. Check subagent results: `ls -la /pscratch/sd/k/krydzy/SWE-agent/batch_results/profiling_verify/`
4. Check benchmark queue: `squeue -u krydzy`

## Verification Status

| Check | Status |
|-------|--------|
| Prompt alignment (ncu_profile in prompts) | PASS — Python assert tests |
| Bundle alignment (PROFILING_BUNDLES) | PASS — Python assert tests |
| nsys_profile on Lulesh (shared storage) | PASS — 934KB report, 13 kernels |
| nsys_profile on Kripke | PASS — 1.7MB report, 6 kernels |
| nsys_profile on Laghos | PASS — needs `-d cuda` flag |
| nsys_profile on Quicksilver (MPI) | PASS — workaround: `mpirun` as executable |
| ncu_profile -c 500 on Lulesh | PENDING — subagent running |
| Profiling tools on GPA apps | PENDING — subagent running |
| vLLM Qwen via container | NOT TESTED — previous agent used wrong approach |
| Output naming change | NOT TESTED (no jobs submitted with new naming yet) |

## Verification Commands (Interactive)

```bash
# Check subagent verification output
ls -lh /pscratch/sd/k/krydzy/SWE-agent/batch_results/profiling_verify/ncu_lulesh_v2/
cat /pscratch/sd/k/krydzy/SWE-agent/batch_results/profiling_verify/ncu_lulesh_v2/summary.txt

# Test vLLM Qwen with the ACTUAL container approach
salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m2404
srun --exclusive --gpus 4 bash -lc '
  export HF_HOME=/pscratch/sd/k/krydzy/hf-cache
  export VLLM_MODEL=Qwen/Qwen3.5-27B-FP8
  export VLLM_GPU_MEM_UTIL=0.60
  export KV_CACHE_DTYPE=bfloat16
  export TOOL_CALL_PARSER=qwen3_coder
  export REASONING_PARSER=qwen3
  bash /pscratch/sd/k/krydzy/SWE-agent/batch/vllm_server.sh
'
# Then from another terminal on same node:
curl -s http://localhost:8008/v1/models | python3 -m json.tool
```

## Gotchas

- **vLLM uses podman-hpc container (v0.11.0)** — NOT bare `python -m vllm`. The `vllm_server.sh` script uses `podman-hpc run docker.io/vllm/vllm-openai:v0.11.0`. Previous test agent found v0.16.0 via bare Python which is NOT what the benchmark pipeline uses.
- **Perlmutter QOS max 2 interactive jobs** — Cannot launch 3+ salloc subagents simultaneously. Serialize or combine tests.
- **ncu_profile -s 1 -c 50 was still broken** — Init kernels dominate early launches. Only `-s 0 -c 500` captures simulation kernels by aggregating the full range.
- **nsys output on compute-node /tmp is node-local** — Files vanish after allocation ends. Must write to shared pscratch for verification.
- **Laghos needs `-d cuda` for GPU profiling** — Without it, runs on CPU and nsys shows no CUDA kernels.
- **MPI apps with nsys_profile** — Pass `mpirun` as executable, rest in app_args. The tool word-splits correctly but the approach is unintuitive.
- **PROFILING_BUNDLES was missing tools/nsight_compute** — Critical bug fixed this session. LLNL apps via dynamic SWE-agent config never got the ncu tool despite it being in static YAML configs.

## Branch State

- **SWE-agent (dev)**: Clean after `45e7cceb`, 12 commits ahead of `origin/dev`
- **GPA-Benchmark (develop)**: Clean after warmup addition in driver_profiling.py
- **Untracked**: `scripts/char_laghos*.{sh,sbatch}`, `xyz.asc`
