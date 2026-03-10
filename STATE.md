# STATE.md — Current Project State

Last updated: 2026-03-10 (session 45)

## Last Session (Session 45)

### Qwen Job Analysis — Root Cause Found & Fixed
All 6 completed Qwen jobs (4 frameworks × LLNL + 2 × GPA) produced 0 code changes. Two bugs:

1. **vLLM reasoning parser conflict** — `--reasoning-parser qwen3` intercepts `<tool_call>` XML as reasoning content, leaving `tool_calls: []` empty. Removed reasoning parser from MODEL_REGISTRY for all Qwen models. Made `--reasoning-parser` flag conditional (only added when non-empty).

2. **SWE-agent cost limit crash** — `sweagent.py:_apply_model_overrides()` overwrote `per_instance_cost_limit: 0` to `1.0`. LiteLLM can't price self-hosted models → `ModelConfigurationError` crash. Removed the override.

### Verified via live vLLM testing
- Started vLLM with `Qwen/Qwen3-Coder-Next-FP8` on compute node
- With reasoning parser: `tool_calls: []`, tool call XML in reasoning field (BROKEN)
- Without reasoning parser: proper `tool_calls` array with correct function/args (WORKING)
- Multi-tool calls work (read_file + bash in single response)

### Manual Validation (all on compute node, 4x A100)
**LLNL Apps** — all 4 pass (build + run + correctness):
- Kripke np=4: 86.7s (GPU contention), Laghos np=4: 65.4s, Lulesh np=8: 74.5s (contention), QS np=4: 67.6s

**Profiling Tools** — all 4 tested:
| Tool | Status | Notes |
|------|--------|-------|
| nsys_profile | PASS | Full pipeline: profile, kernel/API summary, expert analysis |
| hpc_profile | PASS | hpcrun → hpcstruct → hpcprof complete |
| hatchet_analyze | PASS (partial) | Profile, hot path, top functions, source locations work; call tree has pandas bug |
| ncu_profile | PASS (verified) | 84 kernel captures confirmed working; 500-capture default too slow for testing |

**GPA Apps** — all 13 working apps validated directly via `gpa_bench_driver`:
exatensor, xsbench, bfs, gaussian, heartwall, hotspot, huffman, lud, nw, particlefilter, pathfinder, srad, streamcluster

### Cancelled Jobs
- 49850134 (opencode Qwen GPA) — cancelled, would have failed same way
- 49850135 (openhands Qwen GPA) — cancelled, would have failed same way

## Validated LLNL App Timings (4x A100)

| App | np | Parameters | Time | Correctness |
|-----|-----|-----------|------|-------------|
| Kripke | 4 | zones=64³, groups=64, niter=60, quad=8 | 51-55s | PASSED |
| Laghos | 4 | p1, dim=2, rs=4, tf=0.8, -pa -d cuda | 67s | PASSED |
| Lulesh | 8 | s=150, i=5000 | 51-52s | PASSED |
| QS | 4 | Coral2_P2_4.inp, nSteps=67 | 60s | PASSED |

## Active Experiments

### Qwen Session 42 Jobs (ALL FAILED — bugs fixed in session 45)
| Job ID | Framework | Apps | Status | Root Cause |
|--------|-----------|------|--------|------------|
| 49850096 | sweagent | LLNL | COMPLETED — 0/4 | LiteLLM cost crash |
| 49850097 | codex | LLNL | COMPLETED — 0/4 | Tool calls in reasoning |
| 49850098 | opencode | LLNL | COMPLETED — 0/4 | Tool calls in reasoning |
| 49850099 | openhands | LLNL | COMPLETED — 0/4 | Tool calls in reasoning + cost |
| 49850130 | sweagent | GPA | COMPLETED — 0/16 | LiteLLM cost crash |
| 49850133 | codex | GPA | COMPLETED — 0/16 | Tool calls in reasoning |
| 49850134 | opencode | GPA | CANCELLED | Would have failed same way |
| 49850135 | openhands | GPA | CANCELLED | Would have failed same way |

## Available Models

| Model | Cached | TP | GPU Mem | Parser | Status |
|-------|--------|-----|---------|--------|--------|
| Qwen/Qwen3-Coder-Next-FP8 | Yes | 4 | 0.70 | qwen3_coder | Tool calls verified working (no reasoning parser) |
| Qwen/Qwen3.5-27B-FP8 | Yes | 4 | 0.60 | qwen3_coder | Not yet tested |
| Qwen/Qwen3.5-122B-A10B-FP8 | Yes | 4 | 0.92 | qwen3_coder | Not yet tested |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `219e1405` — Fix Qwen tool calling: remove reasoning parser, fix SWE-agent cost limit

## Infrastructure Bugs Found

| Bug | Severity | Status |
|-----|----------|--------|
| Qwen reasoning parser breaks tool calls | CRITICAL | **FIXED** (session 45) |
| SWE-agent cost limit crash on self-hosted models | CRITICAL | **FIXED** (session 45) |
| Kripke CHAI required for CUDA+MPI | CRITICAL | **FIXED** (session 43) |
| OMP_PROC_BIND=spread in harnesses | HIGH | **FIXED** (session 43) |
| GPA driver API: run_driver() takes DriverConfig | HIGH | **FIXED** (session 44) |
| Harness mpirun path resolution | HIGH | **FIXED** (session 44) |
| Harness LD_LIBRARY_PATH for MPI+CUDA | HIGH | **FIXED** (session 44) |
| QS nSteps recalibration | HIGH | **FIXED** (session 44) — nSteps=67 |
| Hatchet call tree pandas compat | LOW | Open — `'slice' object has no attribute '_hatchet_nid'` |
| GPA b+tree build fail (gcc14) | LOW | Open — upstream C code issue |
| GPA backprop build fail (gcc14) | LOW | Open — upstream C code issue |
| GPA lavaMD config error | LOW | Open — case sensitivity bug in GPA driver |
| vLLM harmony_utils Pydantic crash | CRITICAL | Open — blocks OpenHands+gptoss120b |
| SWE-agent `_state_anthropic` 25s timeout | HIGH | Open |

## Recent Decisions

- 2026-03-10 (s45): Remove reasoning parser from all Qwen MODEL_REGISTRY entries — tool calls don't work with it
- 2026-03-10 (s45): Make `--reasoning-parser` and `--enable-reasoning` conditional on non-empty REASONING_PARSER
- 2026-03-10 (s45): Keep `per_instance_cost_limit: 0` for self-hosted models (don't override)
- 2026-03-09 (s44): GPA driver `run_driver()` API changed — must use `DriverConfig` object
- 2026-03-09 (s43): Kripke requires ENABLE_CHAI=ON for CUDA+MPI
- 2026-03-09 (s43): Remove OMP_PROC_BIND/PLACES from harnesses

## Next Steps

### Priority 1: Verify fixes with remaining Qwen models
1. Test `Qwen3.5-27B-FP8` and `Qwen3.5-122B-A10B-FP8` tool calling via vLLM
2. Run quick validation that each model produces proper tool_calls

### Priority 2: Analyze profiling data for optimization potential
1. Review nsys/ncu profiles for each LLNL app
2. Determine if meaningful optimization opportunities exist (vs init-dominated)
3. Validate that benchmark tasks are reasonable for LLM agents

### Priority 3: Launch comprehensive benchmark runs
All with `--build-mode direct`:

**Claude Code** (Anthropic API, no vLLM):
- LLNL apps (kripke, laghos, lulesh, quicksilver)
- GPA apps
- `bash batch/run_benchmark.sh --base --build-mode direct --framework claude --kripke --laghos --lulesh --quicksilver --gpa`

**Codex** (gpt-5.3-codex model, LLNL only):
- `bash batch/run_benchmark.sh --base --build-mode direct --framework codex --kripke --laghos --lulesh --quicksilver`

**Qwen models** (3 models × all apps × with/without profiling):
- For each of: Qwen3-Coder-Next-FP8, Qwen3.5-27B-FP8, Qwen3.5-122B-A10B-FP8
- All 4 frameworks: sweagent, codex, opencode, openhands
- All apps: LLNL + GPA
- Two configs: no_profiling and with_profiling
- `bash batch/run_benchmark.sh --base --build-mode direct --framework sweagent --kripke --laghos --lulesh --quicksilver --gpa --model Qwen/Qwen3-Coder-Next-FP8`

### Priority 4: Infrastructure improvements
1. Update `setup_apps.sh` to build Kripke with CHAI
2. Verify `--build-mode direct` + `--base` + `--gpa` works end-to-end
3. Fix hatchet call tree pandas compatibility
