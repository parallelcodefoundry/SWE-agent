# Handoff — Session 46

Last updated: 2026-03-10

## What We Were Implementing and Why

Session 46 focused on:
1. Downloading and verifying tool calling for the remaining 2 Qwen models (3.5-27B, 3.5-122B)
2. Profiling LLNL apps to confirm optimization potential (not initialization-dominated)
3. Fixing `--build-mode direct` for SWE-agent and GPA prompts
4. Submitting comprehensive benchmark runs across all models/frameworks

## Approach Chosen

- Downloaded models via `huggingface_hub.snapshot_download()` to `/pscratch/sd/k/krydzy/hf-cache`
- Tested tool calls via `podman-hpc run` vLLM containers with `--tool-call-parser qwen3_coder`
- Profiled with `nsys_profile` tool (our wrapper around nsys)
- Fixed prompt generation to properly support `build_mode="direct"`
- Submitted all 26 jobs via `env -u SLURM_JOB_ID bash batch/run_benchmark.sh` pattern (unset SLURM vars so self-submit logic triggers from compute node)

## Goal Progress

- [x] Goal 0: Load state, verify compute node
- [x] Goal 1: Download Qwen3.5-27B-FP8 (31GB)
- [x] Goal 2: Download Qwen3.5-122B-A10B-FP8 (127GB)
- [x] Goal 3: Test Qwen3.5-27B-FP8 tool calling — PASS
- [x] Goal 4: Test Qwen3.5-122B-A10B-FP8 tool calling — PASS (Marlin FP8 fallback on A100)
- [x] Goal 5: Profile Lulesh — 10+ kernels, well-distributed, good for benchmark
- [x] Goal 6: Profile Kripke — RAJA kernels dominate, memcpy overhead, good for benchmark
- [x] Goal 7: Profile Laghos — 100K+ tiny MFEM kernels, sync overhead, good for benchmark
- [x] Goal 8: Fix --build-mode direct for SWE-agent LLNL prompts (missing build_mode param)
- [x] Goal 9: Fix --build-mode direct API for GPA prompts
- [x] Goal 10: Verify prompt fixes (all tests passed)
- [x] Goal 11: Submit Claude Code benchmark (job 49878379, 5 nodes)
- [x] Goal 12: Submit Codex benchmark (job 49878383, 4 nodes)
- [x] Goal 13: Submit Qwen3-Coder-Next-FP8 (8 jobs: 49878446,454-456,460-463)
- [x] Goal 14: Submit Qwen3.5-27B-FP8 (8 jobs: 49878468-479)
- [x] Goal 15: Submit Qwen3.5-122B-A10B-FP8 (8 jobs: 49878520-529)
- [x] Goal 16: Commit and save state
- [ ] Goal 17: Monitor and analyze benchmark results (NEXT SESSION)

## Files Modified This Session

- `batch/frameworks/prompt.py` — Added `build_mode` param to `build_sweagent_prompts()` (line 398) and `build_gpa_prompt()` (line 567). Updated SWE-agent prompts to use DIRECT_BUILD_INSTRUCTIONS when `build_mode="direct"`.
- `batch/frameworks/sweagent.py` — Pass `self.build_mode` at line 77
- `batch/frameworks/base.py` — Pass `self.build_mode` to `build_gpa_prompt()` at line 400

## Files to Read First Next Session

- `STATE.md` — Full project state with job table
- `batch_results/` — Check for completed job outputs (look for dirs matching job IDs 49878*)
- `squeue -u krydzy` — Check job status

## Gotchas and Decisions

- **Submitting from inside salloc** — Must `env -u SLURM_JOB_ID -u SLURM_JOB_NUM_NODES -u SLURM_NODELIST bash batch/run_benchmark.sh ...` to trigger self-submit. Otherwise script sees SLURM_JOB_ID, thinks it's already in a job, and fails with "Need N nodes but only have 1".
- **Flag is `--model-name` not `--model`** — `batch/run_benchmark.sh` uses `--model-name` for the vLLM model. `--model` is not a valid option.
- **Laghos uses single-dash flags** — `-dim 2 -rs 4 -tf 0.8` NOT `--dim 2 --rs 4 --tf 0.8`. Double-dash causes help text and no CUDA kernels.
- **QS nsys profiling timed out** — Didn't complete within reasonable time. Profiled 3/4 apps which was sufficient to validate optimization potential.
- **122B MoE FP8 on A100** — Warning "GPU does not have native support for FP8 computation". Uses Marlin kernel (weight-only FP8 decompression). Works but slower inference. A100 is compute 8.0, native FP8 needs 8.9+.
- **Qwen3.5-27B-FP8 and 3.5-122B-A10B-FP8 were NOT previously cached** — STATE.md had "Cached: Yes" but they weren't actually downloaded. Fixed in this session.
- **GPA build_mode=direct doesn't change behavior** — GPA apps use `gpa_test` driver for build+run+validation in all modes. The driver IS the only way to validate correctness.

## Job Monitoring Commands

```bash
# Check all benchmark jobs
squeue -u krydzy --sort=i -o "%.10i %.10P %.35j %.2t %.8M %.6D %R" | grep -v "mcqa"

# Check specific job
sacct -j 49878379 --format=JobID,JobName,State,ExitCode,Elapsed

# Check results directory for completed job
ls batch_results/*49878379*/

# Quick results summary for all completed jobs
for d in batch_results/*_4987*; do
  echo "=== $(basename $d) ==="
  cat "$d"/summary.json 2>/dev/null | python3 -m json.tool | head -20
done
```

## Interactive Validation Commands

```bash
salloc --nodes 1 --qos interactive --time 03:00:00 --constraint gpu --gpus 4 --account m5083

source /opt/cray/pe/lmod/lmod/init/bash && module load python cmake && module swap cray-mpich openmpi/5.0.7 && module load cudatoolkit/12.4
source ~/envs/sweagent/bin/activate

# Quick vLLM tool call test for any model
export HF_HOME=/pscratch/sd/k/krydzy/hf-cache
podman-hpc run --rm --gpu --net host --ipc=host \
  -e HF_HOME -e VLLM_ATTENTION_BACKEND=TRITON_ATTN \
  -v "${HF_HOME}:${HF_HOME}" \
  docker.io/vllm/vllm-openai:nightly \
  --model "Qwen/Qwen3.5-27B-FP8" \
  --host 0.0.0.0 --port 8008 \
  --tensor-parallel-size 4 --gpu-memory-utilization 0.60 \
  --download-dir "${HF_HOME}" \
  --tool-call-parser qwen3_coder --enable-auto-tool-choice --enforce-eager

# Then test:
curl -s http://localhost:8008/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3.5-27B-FP8","messages":[{"role":"user","content":"Run ls"}],"tools":[{"type":"function","function":{"name":"bash","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}}],"max_tokens":256}' | python3 -m json.tool
```
