# Handoff — Session 45

Last updated: 2026-03-10

## What We Were Implementing and Why

Session 45 focused on:
1. Manual validation of all LLNL apps, profiling tools, and GPA apps on a compute node
2. Diagnosing why all Qwen benchmark runs produced 0 code changes
3. Testing vLLM tool calling to find and fix the root cause

## Approach Chosen

- Launched a vLLM server with `Qwen/Qwen3-Coder-Next-FP8` on compute node
- Tested tool calls via curl with and without `--reasoning-parser qwen3`
- Identified that reasoning parser intercepts tool call XML tags
- Fixed MODEL_REGISTRY + made reasoning parser conditional + fixed SWE-agent cost limit

## Goal Progress

- [x] Goal 0: Load state, verify compute node
- [x] Goal 1: Run all 4 LLNL apps (Kripke, Laghos, Lulesh, QS) — all pass
- [x] Goal 2: Test nsys_profile — works, full pipeline
- [x] Goal 3: Test hpc_profile — works, all 3 steps complete
- [x] Goal 4: Test hatchet_analyze — mostly works, call tree has pandas bug
- [x] Goal 5: Test ncu_profile — works, verified 84 kernel captures
- [x] Goal 6: Validate all 13 working GPA apps directly — all pass
- [x] Goal 7: Check Qwen job results — all 6 completed with 0 code changes
- [x] Goal 8: Diagnose root cause — reasoning parser + cost limit
- [x] Goal 9: Fix MODEL_REGISTRY (remove reasoning parser for Qwen)
- [x] Goal 10: Fix run_benchmark.sh (conditional --reasoning-parser)
- [x] Goal 11: Fix sweagent.py (don't override per_instance_cost_limit)
- [x] Goal 12: Verify fix via live vLLM tool call test — confirmed working
- [x] Goal 13: Commit all fixes
- [x] Goal 14: Cancel doomed pending Qwen GPA jobs
- [ ] Goal 15: Test Qwen3.5-27B-FP8 tool calling
- [ ] Goal 16: Test Qwen3.5-122B-A10B-FP8 tool calling
- [ ] Goal 17: Analyze profiling data for optimization potential
- [ ] Goal 18: Verify --build-mode direct + --base + --gpa works end-to-end
- [ ] Goal 19: Submit Claude Code benchmark (all apps, --build-mode direct)
- [ ] Goal 20: Submit Codex benchmark (gpt-5.3-codex, LLNL only, --build-mode direct)
- [ ] Goal 21: Submit Qwen3-Coder-Next-FP8 benchmarks (all frameworks, all apps, ±profiling, --build-mode direct)
- [ ] Goal 22: Submit Qwen3.5-27B-FP8 benchmarks (same matrix)
- [ ] Goal 23: Submit Qwen3.5-122B-A10B-FP8 benchmarks (same matrix)

## Files Modified This Session

- `batch/run_benchmark.sh` — Removed qwen3 reasoning parser from MODEL_REGISTRY; made --reasoning-parser and --enable-reasoning conditional on non-empty REASONING_PARSER
- `batch/frameworks/sweagent.py` — Removed per_instance_cost_limit override (was 0→1.0, now stays at 0 for self-hosted models)

## Files to Read First Next Session

- `STATE.md` — Full project state with all TODOs
- `batch/run_benchmark.sh` (lines 70-78) — MODEL_REGISTRY (updated, no reasoning parser)
- `batch/run_benchmark.sh` (lines 667-671) — vLLM launch (conditional reasoning parser)
- `batch/frameworks/sweagent.py` (lines 261-279) — Model override logic (cost limit fix)

## Gotchas and Decisions

- **Reasoning parser + tool calls are incompatible for Qwen** — The `qwen3` reasoning parser captures `<tool_call>` XML before the `qwen3_coder` tool call parser can extract it. Don't re-enable.
- **vLLM must be launched via `podman-hpc run`** — vLLM is not installed natively. The benchmark runner uses podman-hpc containers.
- **vLLM startup takes ~5-7 min** — Model loading + tensor parallel init is slow. Budget accordingly.
- **OpenCode uses gpt-5-nano for title generation** — This model doesn't exist on vLLM. It's a non-fatal error (title generation fails, agent still works). Not blocking.
- **ncu_profile 500-capture default is too slow** — For testing, use a small problem size. For actual profiling, consider filtering by kernel name.
- **Hatchet call tree bug** — `'slice' object has no attribute '_hatchet_nid'` in pandas indexing. Non-blocking; hot path + top functions still work.

## Benchmark Submission Plan

### Models to test:
1. **Qwen/Qwen3-Coder-Next-FP8** — Already verified tool calls work
2. **Qwen/Qwen3.5-27B-FP8** — Needs tool call verification first
3. **Qwen/Qwen3.5-122B-A10B-FP8** — Needs tool call verification first
4. **Claude Code** (Anthropic API) — Uses `--skip-vllm --framework claude`
5. **gpt-5.3-codex** — Codex framework, LLNL apps only

### Run matrix:
| Model | Framework(s) | Apps | Build Mode | Profiling | Priority |
|-------|-------------|------|------------|-----------|----------|
| Claude | claude | LLNL + GPA | direct | no | HIGH |
| gpt-5.3-codex | codex | LLNL only | direct | no | HIGH |
| Qwen3-Coder-Next-FP8 | sweagent, codex, opencode, openhands | LLNL + GPA | direct | no | HIGH |
| Qwen3-Coder-Next-FP8 | sweagent, codex, opencode, openhands | LLNL + GPA | direct | yes | MED |
| Qwen3.5-27B-FP8 | all 4 | LLNL + GPA | direct | no + yes | MED |
| Qwen3.5-122B-A10B-FP8 | all 4 | LLNL + GPA | direct | no + yes | MED |

### Example submission commands:
```bash
# Claude Code (all apps, no vLLM needed)
bash batch/run_benchmark.sh --base --build-mode direct --framework claude \
  --kripke --laghos --lulesh --quicksilver --gpa

# Codex with gpt-5.3-codex (LLNL only)
bash batch/run_benchmark.sh --base --build-mode direct --framework codex \
  --kripke --laghos --lulesh --quicksilver --external-model

# Qwen3-Coder-Next-FP8 no profiling (one framework at a time)
bash batch/run_benchmark.sh --base --build-mode direct --framework sweagent \
  --kripke --laghos --lulesh --quicksilver --gpa \
  --model Qwen/Qwen3-Coder-Next-FP8

# Qwen3-Coder-Next-FP8 with profiling
bash batch/run_benchmark.sh --base --build-mode direct --framework sweagent \
  --kripke --laghos --lulesh --quicksilver --gpa \
  --model Qwen/Qwen3-Coder-Next-FP8 --profiling with_profiling
```

### Pre-submission checklist:
- [ ] Verify Qwen3.5-27B-FP8 produces valid tool_calls
- [ ] Verify Qwen3.5-122B-A10B-FP8 produces valid tool_calls
- [ ] Verify `--build-mode direct --base --gpa` works end-to-end
- [ ] Verify `--profiling with_profiling` flag works with direct build mode
- [ ] Check gpt-5.3-codex model availability/pricing
- [ ] Analyze profiles to confirm optimization potential

## Interactive Validation Commands

```bash
salloc --nodes 1 --qos interactive --time 03:00:00 --constraint gpu --gpus 4 --account m5083

source /opt/cray/pe/lmod/lmod/init/bash && module load python cmake && module swap cray-mpich openmpi/5.0.7 && module load cudatoolkit/12.4
source ~/envs/sweagent/bin/activate

# Quick vLLM tool call test (for new Qwen models)
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

# LLNL apps (same as session 44)
export KRIPKE_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Kripke
python3 tools/kripke_harness/bin/kripke_run --np 4 --baseline-only --timing-runs 1

# Profiling (nsys on Lulesh, small problem)
export PATH="/pscratch/sd/k/krydzy/SWE-agent/tools/nsight_systems/bin:$PATH"
nsys_profile /pscratch/sd/k/krydzy/SWE-agent/Lulesh/cuda/lulesh /tmp/nsys_lulesh "-s 30 -i 100"
```
