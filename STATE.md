# STATE.md — Current Project State

Last updated: 2026-03-10 (session 46)

## Last Session (Session 46)

### All 3 Qwen Models Verified — Tool Calls Working
Downloaded and tested all 3 Qwen models via vLLM on compute node:
- **Qwen3-Coder-Next-FP8** (80GB, verified session 45)
- **Qwen3.5-27B-FP8** (31GB, downloaded + verified this session)
- **Qwen3.5-122B-A10B-FP8** (127GB, downloaded + verified this session)

All produce proper `tool_calls` JSON with `qwen3_coder` parser, no reasoning parser.

Note: 122B MoE on A100 (compute 8.0) uses Marlin kernel fallback for FP8 (native FP8 needs compute 8.9+). Functional but slower inference. KV cache only 4.73 GiB at 0.92 utilization.

### --build-mode direct Fixed for All Frameworks
Found and fixed 3 issues blocking `--build-mode direct`:
1. `build_sweagent_prompts()` missing `build_mode` parameter — SWE-agent ignored direct mode for LLNL apps
2. `build_gpa_prompt()` missing `build_mode` parameter — API consistency
3. Passed `self.build_mode` from `sweagent.py:77` and `base.py:400`

All frameworks now properly generate direct-mode prompts (BUILD INSTRUCTIONS instead of harness tool refs). GPA correctly keeps `gpa_test` in both modes.

### Profiling Analysis — All LLNL Apps Have Real Optimization Potential
Profiled Lulesh, Kripke, and Laghos via nsys_profile:

| App | Total GPU Time | Top Kernel | Key Bottleneck | Verdict |
|-----|---------------|------------|----------------|---------|
| Lulesh | ~8.8ms (100 iter) | ApplyMaterialProperties 22.9% | 10+ kernels, well-distributed | Good for benchmark |
| Kripke | ~97.8ms (5 iter) | RAJA sweep 41.5% | cudaMemcpyAsync 40%, sync 18.5% | Good for benchmark |
| Laghos | ~260ms | MFEM reduction 29.2% | 100K+ tiny kernels, many syncs | Good for benchmark |

None are initialization-dominated. All have meaningful GPU compute work with clear optimization opportunities (kernel fusion, memory coalescing, reduced sync, shared memory).

### 26 Benchmark Jobs Submitted
All with `--build-mode direct`, LLNL + GPA apps:

| Job IDs | Model | Frameworks | Profiling |
|---------|-------|-----------|-----------|
| 49878379 | Claude Code | claude | no |
| 49878383 | gpt-5.3-codex | codex (LLNL only) | no |
| 49878446,454-456 | Qwen3-Coder-Next-FP8 | all 4 | no |
| 49878460-463 | Qwen3-Coder-Next-FP8 | all 4 | yes |
| 49878468-479 | Qwen3.5-27B-FP8 | all 4 | no + yes |
| 49878520-529 | Qwen3.5-122B-A10B-FP8 | all 4 | no + yes |

## Validated LLNL App Timings (4x A100)

| App | np | Parameters | Time | Correctness |
|-----|-----|-----------|------|-------------|
| Kripke | 4 | zones=64³, groups=64, niter=60, quad=8 | 51-55s | PASSED |
| Laghos | 4 | p1, dim=2, rs=4, tf=0.8, -pa -d cuda | 67s | PASSED |
| Lulesh | 8 | s=150, i=5000 | 51-52s | PASSED |
| QS | 4 | Coral2_P2_4.inp, nSteps=67 | 60s | PASSED |

## Active Experiments

### Session 46 Benchmark Jobs (26 jobs, all pending)
| Job ID | Framework | Model | Apps | Profiling | Status |
|--------|-----------|-------|------|-----------|--------|
| 49878379 | claude | Claude Code | LLNL+GPA | no | PD |
| 49878383 | codex | gpt-5.3-codex | LLNL | no | PD |
| 49878446 | sweagent | Qwen3-Coder-Next-FP8 | LLNL+GPA | no | PD |
| 49878454 | codex | Qwen3-Coder-Next-FP8 | LLNL+GPA | no | PD |
| 49878455 | opencode | Qwen3-Coder-Next-FP8 | LLNL+GPA | no | PD |
| 49878456 | openhands | Qwen3-Coder-Next-FP8 | LLNL+GPA | no | PD |
| 49878460 | sweagent | Qwen3-Coder-Next-FP8 | LLNL+GPA | yes | PD |
| 49878461 | codex | Qwen3-Coder-Next-FP8 | LLNL+GPA | yes | PD |
| 49878462 | opencode | Qwen3-Coder-Next-FP8 | LLNL+GPA | yes | PD |
| 49878463 | openhands | Qwen3-Coder-Next-FP8 | LLNL+GPA | yes | PD |
| 49878468 | sweagent | Qwen3.5-27B-FP8 | LLNL+GPA | no | PD |
| 49878469 | sweagent | Qwen3.5-27B-FP8 | LLNL+GPA | yes | PD |
| 49878471 | codex | Qwen3.5-27B-FP8 | LLNL+GPA | no | PD |
| 49878473 | codex | Qwen3.5-27B-FP8 | LLNL+GPA | yes | PD |
| 49878475 | opencode | Qwen3.5-27B-FP8 | LLNL+GPA | no | PD |
| 49878476 | opencode | Qwen3.5-27B-FP8 | LLNL+GPA | yes | PD |
| 49878477 | openhands | Qwen3.5-27B-FP8 | LLNL+GPA | no | PD |
| 49878479 | openhands | Qwen3.5-27B-FP8 | LLNL+GPA | yes | PD |
| 49878520 | sweagent | Qwen3.5-122B-A10B-FP8 | LLNL+GPA | no | PD |
| 49878521 | sweagent | Qwen3.5-122B-A10B-FP8 | LLNL+GPA | yes | PD |
| 49878523 | codex | Qwen3.5-122B-A10B-FP8 | LLNL+GPA | no | PD |
| 49878524 | codex | Qwen3.5-122B-A10B-FP8 | LLNL+GPA | yes | PD |
| 49878525 | opencode | Qwen3.5-122B-A10B-FP8 | LLNL+GPA | no | PD |
| 49878526 | opencode | Qwen3.5-122B-A10B-FP8 | LLNL+GPA | yes | PD |
| 49878528 | openhands | Qwen3.5-122B-A10B-FP8 | LLNL+GPA | no | PD |
| 49878529 | openhands | Qwen3.5-122B-A10B-FP8 | LLNL+GPA | yes | PD |

### Previous Session 42 Jobs (ALL FAILED — bugs fixed)
| Job ID | Framework | Apps | Status | Root Cause |
|--------|-----------|------|--------|------------|
| 49850096 | sweagent | LLNL | COMPLETED — 0/4 | LiteLLM cost crash |
| 49850097 | codex | LLNL | COMPLETED — 0/4 | Tool calls in reasoning |
| 49850098 | opencode | LLNL | COMPLETED — 0/4 | Tool calls in reasoning |
| 49850099 | openhands | LLNL | COMPLETED — 0/4 | Tool calls in reasoning + cost |
| 49850130 | sweagent | GPA | COMPLETED — 0/16 | LiteLLM cost crash |
| 49850133 | codex | GPA | COMPLETED — 0/16 | Tool calls in reasoning |

## Available Models

| Model | Cached | Size | TP | GPU Mem | Parser | Status |
|-------|--------|------|-----|---------|--------|--------|
| Qwen/Qwen3-Coder-Next-FP8 | Yes | 80GB | 4 | 0.70 | qwen3_coder | VERIFIED ✓ |
| Qwen/Qwen3.5-27B-FP8 | Yes | 31GB | 4 | 0.60 | qwen3_coder | VERIFIED ✓ |
| Qwen/Qwen3.5-122B-A10B-FP8 | Yes | 127GB | 4 | 0.92 | qwen3_coder | VERIFIED ✓ (Marlin FP8 fallback) |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `2083b15c` — Fix --build-mode direct for SWE-agent and GPA prompts

## Infrastructure Bugs Found

| Bug | Severity | Status |
|-----|----------|--------|
| --build-mode direct ignored by SWE-agent | HIGH | **FIXED** (session 46) |
| --build-mode direct not passed to GPA prompts | HIGH | **FIXED** (session 46) |
| Qwen reasoning parser breaks tool calls | CRITICAL | **FIXED** (session 45) |
| SWE-agent cost limit crash on self-hosted models | CRITICAL | **FIXED** (session 45) |
| Kripke CHAI required for CUDA+MPI | CRITICAL | **FIXED** (session 43) |
| OMP_PROC_BIND=spread in harnesses | HIGH | **FIXED** (session 43) |
| GPA driver API: run_driver() takes DriverConfig | HIGH | **FIXED** (session 44) |
| Harness mpirun path resolution | HIGH | **FIXED** (session 44) |
| Harness LD_LIBRARY_PATH for MPI+CUDA | HIGH | **FIXED** (session 44) |
| QS nSteps recalibration | HIGH | **FIXED** (session 44) — nSteps=67 |
| 122B MoE FP8 on A100 uses Marlin fallback | LOW | Known — slower inference, functional |
| Hatchet call tree pandas compat | LOW | Open — `'slice' object has no attribute '_hatchet_nid'` |
| GPA b+tree build fail (gcc14) | LOW | Open — upstream C code issue |
| GPA backprop build fail (gcc14) | LOW | Open — upstream C code issue |
| GPA lavaMD config error | LOW | Open — case sensitivity bug in GPA driver |
| vLLM harmony_utils Pydantic crash | CRITICAL | Open — blocks OpenHands+gptoss120b |
| SWE-agent `_state_anthropic` 25s timeout | HIGH | Open |

## Recent Decisions

- 2026-03-10 (s46): Fix --build-mode direct for SWE-agent LLNL apps and GPA prompt API consistency
- 2026-03-10 (s46): GPA apps don't change behavior in direct mode (gpa_test driver handles everything)
- 2026-03-10 (s46): Submit all 26 benchmark jobs simultaneously — queue will schedule them
- 2026-03-10 (s46): 122B MoE on A100 is viable despite Marlin FP8 fallback — functional, just slower
- 2026-03-10 (s45): Remove reasoning parser from all Qwen MODEL_REGISTRY entries
- 2026-03-10 (s45): Make `--reasoning-parser` and `--enable-reasoning` conditional on non-empty REASONING_PARSER
- 2026-03-10 (s45): Keep `per_instance_cost_limit: 0` for self-hosted models
- 2026-03-09 (s44): GPA driver `run_driver()` API changed — must use `DriverConfig` object
- 2026-03-09 (s43): Kripke requires ENABLE_CHAI=ON for CUDA+MPI
- 2026-03-09 (s43): Remove OMP_PROC_BIND/PLACES from harnesses

## Next Steps

### Priority 1: Monitor benchmark jobs
1. Check job status with `squeue -u krydzy` and `sacct`
2. As jobs complete, check `batch_results/` for output
3. Analyze results: speedup achieved, correctness, which frameworks/models perform best

### Priority 2: Analyze results
1. Compare across models: Qwen3-Coder-Next vs 3.5-27B vs 3.5-122B
2. Compare across frameworks: sweagent vs codex vs opencode vs openhands
3. Compare profiling vs no-profiling: does profiling info help?
4. Compare Claude Code vs open-source models
5. Check if any apps consistently fail across all agents

### Priority 3: Infrastructure improvements
1. Update `setup_apps.sh` to build Kripke with CHAI
2. Fix hatchet call tree pandas compatibility
3. Consider reducing 122B model's max_seq_len to increase KV cache capacity
