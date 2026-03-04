# HANDOFF — Session 36 → Session 37

Last updated: 2026-03-04 (session 36)

## What We Were Working On

Session 36: Implemented GPA improvements (timing robustness + diff storage), vLLM model registry, NCU profiling tool. Tested NCU on all proxy apps (all passed). Fixed `bf16`→`bfloat16` for vLLM. Downloaded 3 Qwen FP8 models. Submitted 9 benchmark jobs. vLLM Qwen testing agent still running.

## Goal Progress
- [x] Goal 0: Commit previous changes (session 33)
- [x] Goal 1: Fix SWE-agent config signatures (session 33)
- [x] Goal 2: Fix QS harness flag passthrough (session 33)
- [x] Goal 3: Update results_summary.json + plots (session 33)
- [x] Goal 4: Update QS SKILL.md (session 33)
- [x] Goal 5: Deep failure analysis of session 32 jobs (session 33)
- [x] Goal 6: Fix Codex gpt-5.3 API hostname bug (session 34)
- [x] Goal 7: Fix Claude Code --verbose flag (session 34)
- [x] Goal 8: Fix Lulesh Makefile deletion issue (session 34)
- [x] Goal 9: GPA deep analysis — diffs, upstream merge, SKILL update (session 35)
- [x] Goal 10: Add OpenAI regional endpoint validation + --openai-region flag (session 35)
- [x] Goal 11: GPA timing robustness (nsys 3→5 + warmup) + diff storage (session 36)
- [x] Goal 12: vLLM model registry — model-aware parser/dtype/gpu_mem_util (session 36)
- [x] Goal 13: NCU profiling tool — tested on all 4 proxy apps (session 36)
- [x] Goal 14: Download Qwen FP8 models (27B, Coder-Next, 122B-A10B) (session 36)
- [~] Goal 15: Resubmit LLNL benchmark runs — SUBMITTED (jobs 49639229-49639232)
- [~] Goal 16: Resubmit GPA benchmark runs — SUBMITTED (jobs 49639233-49639235, 49639241)
- [~] Goal 17: GPT-5.3-Codex Lulesh — SUBMITTED (job 49639242)
- [ ] Goal 18: Cherry-pick SWE-agent upstream fixes (3 bugs)
- [ ] Goal 19: Address Laghos timing variance / Lulesh measurement bias
- [ ] Goal 20: Qwen3.5-27B-FP8 benchmark runs (downloaded, `--kv-cache-dtype bfloat16`)
- [ ] Goal 21: Qwen3-Coder-Next-FP8 benchmark runs (downloaded, `--kv-cache-dtype bfloat16`)
- [ ] Goal 22: Qwen3.5-122B-A10B-FP8 benchmark runs (BLOCKED: needs 8 GPUs or 4x80GB nodes)

## Submitted Benchmark Jobs (Session 36)

| Job ID | Framework | Apps | Model | Notes |
|--------|-----------|------|-------|-------|
| 49639229 | sweagent | LLNL (4 apps) | gptoss120b | --base --both |
| 49639230 | opencode | LLNL (4 apps) | gptoss120b | --base --both |
| 49639231 | openhands | LLNL (4 apps) | gptoss120b | --base --both |
| 49639232 | claude | LLNL (4 apps) | Anthropic API | --base --both, SKIP_VLLM |
| 49639233 | sweagent | GPA | gptoss120b | --base --both |
| 49639234 | opencode | GPA | gptoss120b | --base --both |
| 49639235 | openhands | GPA | gptoss120b | --base --both |
| 49639241 | claude | GPA | Anthropic API | --base --both, SKIP_VLLM |
| 49639242 | codex | Lulesh only | gpt-5.3-codex | --base --both --external-model |

## Key Commits (Session 36)

| Commit | Description |
|--------|-------------|
| `a388d58d` | Add NCU profiling tool, GPA timing/diff improvements, vLLM model registry |
| `c6e8daa9` | Add per-model gpu_mem_util to vLLM model registry |
| `f42541b8` | Fix vLLM kv-cache-dtype (bf16→bfloat16) and NCU profiling bugs |

## Files Modified This Session

| File | Change |
|------|--------|
| `batch/hpc_benchmark_runner.py` | Added `num_samples=5` to GPA runner, replaced full-content agent_patch with unified diff |
| `batch/run_benchmark.sh` | Added MODEL_REGISTRY, `_lookup_model_settings()`, dynamic vLLM parser flags |
| `batch/vllm_server.sh` | Updated hardcoded parsers to use env var defaults |
| `batch/frameworks/base.py` | Added nsight_compute to PROFILING_TOOL_DIRS |
| `tools/nsight_compute/config.yaml` | NEW: SWE-agent tool definition for ncu_profile |
| `tools/nsight_compute/bin/ncu_profile` | NEW: NCU profiling script (tested on all 4 apps) |
| `config/hpc/*_with_profiling.yaml` (5 files) | Added `tools/nsight_compute` to bundles |
| `GPA-Benchmark/.../driver_profiling.py` | Added warmup run before nsys profiling loop |
| `.planning/HANDOFF.md` | This file |

## Files to Read First Next Session

1. `STATE.md` — Full state overview
2. `.planning/HANDOFF.md` — This file
3. `squeue -u krydzy` — Check if benchmark jobs completed

## NCU Tool Testing Results

All 5 tests passed on Perlmutter (job 49638907):

| App | Mode | Wall Time | Key Finding |
|-----|------|-----------|-------------|
| Lulesh | Basic | 8s | LATENCY-BOUND (SM 1.6%, DRAM 0.1%) |
| Kripke | Basic | 15s | LATENCY-BOUND (SM 10.6%, DRAM 3.6%) |
| Laghos | Basic | 16s | LATENCY-BOUND (problem too small) |
| Quicksilver | Basic | 32s | LATENCY-BOUND (SM 26.8%, DRAM 15.2%, 116 regs) |
| Lulesh | Detailed (CalcVolume) | 9s | MIXED (SM 45.8%, DRAM 15.3%, 252 regs!) |

Bugs found and fixed in ncu_profile:
1. Comma-in-numbers CSV parsing (`1,024` → `float()` error)
2. Wrong DRAM metric name (`dram__throughput` → `dram__cycles_active`)
3. L1 metric suffix (`_elapsed` → `_active`)
4. Regex prefix needed for kernel filter
5. Time unit detection (ns/us/ms)
6. Python heredoc variable interpolation
7. Word-splitting for quoted app_args

## vLLM Testing Findings

- `--kv-cache-dtype bf16` is INVALID in vLLM v0.11.0 — must use `bfloat16`
- Valid choices: `auto, bfloat16, fp8, fp8_e4m3, fp8_e5m2, fp8_inc`
- Fixed in MODEL_REGISTRY (commit `f42541b8`)
- Qwen model testing with corrected `bfloat16` flag was in progress at session end

## Gotchas

- **bf16 vs bfloat16**: vLLM v0.11.0 rejects `bf16`. Use `bfloat16` everywhere.
- **NCU metric names**: `dram__throughput.avg.pct_of_peak_sustained_elapsed` doesn't exist. Use `dram__cycles_active.avg.pct_of_peak_sustained_elapsed`.
- **NCU CSV commas**: ncu exports integers with thousands separators. Must strip commas before float conversion.
- **RAJA apps generic kernels**: Lulesh/Kripke wrap GPU work in `_kernel_agent`/`CudaKernelLauncherFixed`. Use detailed mode + regex filter for useful profiling data.
- **Codex with gptoss120b**: Confirmed broken — never makes code changes. Do NOT resubmit.
- SWE-agent upstream has 3 cherry-pickable fixes: blocklist logic inversion (`c69d6f56`), shlex.quote (`3ff833d9`), completion_kwargs deepcopy (`ed7dd55c`).

## Branch State

- **SWE-agent (dev)**: Clean after `f42541b8` — Fix vLLM kv-cache-dtype + NCU bugs
- **GPA-Benchmark (develop)**: Clean after warmup addition in driver_profiling.py
- **Untracked**: `scripts/char_laghos*.{sh,sbatch}`, `xyz.asc`
