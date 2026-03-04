# HANDOFF — Session 38 → Session 39

Last updated: 2026-03-04 (session 38)

## What We Were Working On

Session 38: Verified profiling tools on GPA apps (all passed), added `nsys analyze` expert rules, improved ncu bottleneck guidance, cherry-picked 3 upstream SWE-agent fixes. vLLM Qwen container test still in progress at session end.

## Goal Progress
- [x] Goal 0: Verify ncu_profile `-c 500` fix — CONFIRMED, 13 kernel types, 93.1% simulation
- [x] Goal 1: Test profiling tools on GPA apps — 4 apps tested (streamcluster, XSBench, hotspot, gaussian), all PASS
- [x] Goal 2: Add nsys analyze expert rules — 6 CUDA rules, compatible with 12.4 and 12.9
- [x] Goal 3: Improve ncu bottleneck guidance — code-level suggestions (fast math, launch_bounds, etc.)
- [x] Goal 4: Cherry-pick SWE-agent upstream fixes — blocklist, shlex, deepcopy (all clean)
- [~] Goal 5: Test vLLM Qwen via podman-hpc container — subagent running at session end
- [ ] Goal 6: Submit Qwen benchmark runs (16 jobs) — BLOCKED on Goal 5
- [ ] Goal 7: Check session 36 benchmark results (9 jobs still queued)

## Running Subagents at Session End

1. **vLLM Qwen container test** (a9e9a6fa5a32ca652) — Testing vLLM server startup with Qwen3.5-27B-FP8 via `podman-hpc run docker.io/vllm/vllm-openai:v0.11.0`. Allocation: 49640456 on nid001068.

## Key Commits (Session 38)

| Commit | Description |
|--------|-------------|
| `00751329` | Add nsys analyze expert rules and improve profiling tool guidance |
| `14c9e5be` | Cherry-pick: User-Agent header + deepcopy fix (#1346) |
| `67936ffd` | Cherry-pick: shlex.quote for command injection fix (#1325) |
| `2180db79` | Cherry-pick: blocklist inversion fix (#1336) |

## Files Modified This Session

| File | Change |
|------|--------|
| `tools/nsight_systems/bin/nsys_profile` | Added `nsys analyze` step with 6 expert rules, output to stdout + expert_analysis.txt |
| `tools/nsight_systems/config.yaml` | Documented expert analysis outputs and rule descriptions |
| `tools/nsight_compute/bin/ncu_profile` | Improved bottleneck guidance with code-level suggestions |
| `sweagent/tools/tools.py` | Cherry-pick: blocklist `action.startswith(f)` (was inverted) |
| `sweagent/environment/repo.py` | Cherry-pick: `shlex.quote()` for base_commit/url |
| `sweagent/agent/models.py` | Cherry-pick: `copy.deepcopy(completion_kwargs)` + User-Agent header |
| `tests/test_models.py` | Cherry-pick: 3 test cases for User-Agent header behavior |

## Files to Read First Next Session

1. `STATE.md` — Full state overview
2. `.planning/HANDOFF.md` — This file
3. Check vLLM subagent result: output at `/tmp/claude-111589/-pscratch-sd-k-krydzy-SWE-agent/tasks/a9e9a6fa5a32ca652.output` (or check `squeue -u krydzy`)
4. Check benchmark queue: `squeue -u krydzy`

## Verification Status

| Check | Status |
|-------|--------|
| ncu_profile `-c 500` on Lulesh | PASS — 370 launches, 13 kernel types, 93.1% simulation |
| nsys_profile on 4 proxy apps | PASS — All sessions 37 |
| nsys_profile on 4 GPA apps | PASS — streamcluster, XSBench, hotspot, gaussian |
| ncu_profile on 4 GPA apps | PASS — All bottleneck types detected correctly |
| nsys analyze compatibility (12.4 vs 12.9) | PASS — Same rules, same syntax |
| ncu metric compatibility (12.4 vs 12.9) | PASS — Same basic/detailed/full sets |
| Cherry-pick blocklist fix | PASS — Clean apply |
| Cherry-pick shlex.quote fix | PASS — Clean apply |
| Cherry-pick deepcopy/User-Agent fix | PASS — Clean apply |
| vLLM Qwen via container | PENDING — subagent running |
| Output naming change | NOT TESTED (no jobs submitted with new naming yet) |

## Verification Commands (Interactive)

```bash
# Check vLLM subagent result
squeue -u krydzy  # Is allocation still running?

# Test vLLM Qwen manually if subagent failed
salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m2404
srun --exclusive --gpus 4 bash -lc '
  export HF_HOME=/pscratch/sd/k/krydzy/hf-cache
  export VLLM_MODEL=Qwen/Qwen3.5-27B-FP8
  export VLLM_GPU_MEM_UTIL=0.60
  export KV_CACHE_DTYPE=bfloat16
  export TOOL_CALL_PARSER=qwen3_coder
  export REASONING_PARSER=qwen3
  bash /pscratch/sd/k/krydzy/SWE-agent/batch/vllm_server.sh &
  sleep 180
  curl -s http://localhost:8008/v1/models | python3 -m json.tool
  curl -s http://localhost:8008/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d "{\"model\": \"Qwen/Qwen3.5-27B-FP8\", \"messages\": [{\"role\": \"user\", \"content\": \"Say hello\"}], \"max_tokens\": 10}" | python3 -m json.tool
'

# Submit Qwen benchmark runs (after vLLM test passes)
for FW in sweagent opencode openhands codex; do
  sbatch batch/run_benchmark.sh --base --both --kripke --laghos --lulesh --quicksilver --framework $FW --model-name Qwen/Qwen3.5-27B-FP8
  sbatch batch/run_benchmark.sh --base --both --gpa --framework $FW --model-name Qwen/Qwen3.5-27B-FP8
done
# Same for Qwen3-Coder-Next-FP8
```

## Gotchas

- **vLLM uses podman-hpc container (v0.11.0)** — NOT bare `python -m vllm`. The `vllm_server.sh` script uses `podman-hpc run docker.io/vllm/vllm-openai:v0.11.0`. Previous test agents repeatedly used the wrong approach.
- **Perlmutter QOS max 2 interactive jobs** — Cannot launch 3+ salloc subagents simultaneously. Previous sessions hit this MULTIPLE times.
- **srun "nodes are busy"** — If a previous srun step on an allocation is stale, new steps fail. Use a single srun for everything, or cancel+restart the allocation.
- **ncu_profile `-c 500` takes >10 minutes for some apps** — Lulesh (12+ kernels/iteration) = 5000 replay passes. Consider reducing to -c 200.
- **ncu_profile arg parsing** — Non-dash app args after output_dir get interpreted as kernel filter. Pass explicit filter or empty `""`.
- **nsys output on compute-node /tmp is node-local** — Files vanish after allocation ends. Must write to shared pscratch.
- **Laghos needs `-d cuda` for GPU profiling** — Without it, runs on CPU and nsys/ncu show no CUDA kernels.
- **MPI apps with nsys_profile** — Pass `mpirun` as executable, rest in app_args.
- **GPA apps need CUDA 12.9 (default)** — Don't load `cudatoolkit/12.4` for GPA apps. `get_module_loads(repo_name)` in base.py handles this.
- **nsys analyze works on both 12.4 and 12.9** — Same rules, same syntax. No version gating needed.

## Branch State

- **SWE-agent (dev)**: Clean after `00751329`, 17 commits ahead of `origin/dev`
- **GPA-Benchmark (develop)**: Clean after warmup addition in driver_profiling.py
- **Untracked**: `scripts/char_laghos*.{sh,sbatch}`, `xyz.asc`, `output.{out,txt}`
