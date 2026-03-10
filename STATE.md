# STATE.md — Current Project State

Last updated: 2026-03-10 (session 47)

## Last Session (Session 47)

### Comprehensive Analysis of 26 Benchmark Jobs — 6 Root Causes Found

Analyzed all session 46 benchmark results. 17/26 completed, 10 cancelled (would waste ~60 node-hours on same bugs).

**Claude Code was the only success**: 3/4 LLNL apps optimized (Kripke 2.03x, Laghos 1.30x, QS 1.70x). Everything else failed.

### 6 Root Causes Identified

| # | Root Cause | Category | Status |
|---|-----------|----------|--------|
| 1 | GPA: CUDA 12.4 nvcc + GCC 14 | infra | **FIXED** — `run_benchmark.sh` + `hpc_benchmark_runner.py` |
| 2 | Codex+Qwen: XML `<tool_call>` not parsed by Responses API | infra | Open — investigate `wire_api` + vLLM `/v1/responses` |
| 3 | OpenCode+Qwen: same XML + `gpt-5-nano` 404 | infra | Open — title gen model missing |
| 4 | SWE-agent+Qwen: analysis paralysis (0 edits in 196 steps) | model | Open — try `thought_action` parse mode or stronger prompts |
| 5 | Codex+external: missing `--model-name` → bogus URL | infra | Root cause found — submission fix |
| 6 | Claude Code: 3/4 LLNL success, Lulesh disabled MPI | partial | Need MPI warning in prompts |

### GPA CUDA 12.9 Fix Applied
- `run_benchmark.sh:839-846`: Explicit `module unload cudatoolkit; module load cudatoolkit/12.9` for GPA
- `hpc_benchmark_runner.py:1060-1094`: Detect CUDA 12.9 path, set `CUDA_HOME`, prepend to PATH, pass `cuda_home=Path(...)` to `DriverConfig`
- 13/16 GPA apps now build+run+validate (b+tree/backprop: upstream gcc-14; lavaMD: upstream case bug)

### Jobs Cancelled
All 10 pending/running Qwen3.5-122B + remaining 27B jobs: 49878477, 49878479, 49878520-529

## Validated LLNL App Timings (4x A100)

| App | np | Parameters | Time | Correctness |
|-----|-----|-----------|------|-------------|
| Kripke | 4 | zones=64³, groups=64, niter=60, quad=8 | 51-55s | PASSED |
| Laghos | 4 | p1, dim=2, rs=4, tf=0.8, -pa -d cuda | 67s | PASSED |
| Lulesh | 8 | s=150, i=5000 | 51-52s | PASSED |
| QS | 4 | Coral2_P2_4.inp, nSteps=67 | 60s | PASSED |

## Active Experiments

### Session 46 Benchmark Jobs (17 completed, 10 cancelled)

**Claude Code (49878379) — ONLY SUCCESS**:
| App | Speedup | Correctness | Strategy |
|-----|---------|-------------|----------|
| Kripke | **2.03x** | PASSED | Fused kConst zero-init into LTimes/LPlusTimes |
| Laghos | **1.30x** | PASSED | Relaxed CG tol, disabled sync, fast_math, NBZ=4 |
| QS | **1.70x** | PASSED | Batched atomics, sincos(), UVM optimization |
| Lulesh | N/A | FAILED | Disabled MPI → segfault (model error) |
| GPA (16) | N/A | ALL FAILED | CUDA 12.4 build failure (infra, now fixed) |

**All Other Jobs — FAILED** (see `.planning/RESULTS-TRACKING-S46.md` for details):
- SWE-agent+Qwen (4 jobs): 0 edits in 196 steps — model reads files endlessly
- Codex+Qwen (4 jobs): XML tool calls not parsed → 1-turn exit
- OpenCode+Qwen (4 jobs): Same XML issue + gpt-5-nano 404
- OpenHands+Qwen (4 jobs): Mixed — mostly failures, 1/20 success on one run
- Codex+external (1 job): Missing `--model-name` → bogus URL

## Available Models

| Model | Cached | Size | TP | GPU Mem | Parser | Status |
|-------|--------|------|-----|---------|--------|--------|
| Qwen/Qwen3-Coder-Next-FP8 | Yes | 80GB | 4 | 0.70 | qwen3_coder | Tool calls verified but analysis paralysis in SWE-agent |
| Qwen/Qwen3.5-27B-FP8 | Yes | 31GB | 4 | 0.60 | qwen3_coder | Same issues as above |
| Qwen/Qwen3.5-122B-A10B-FP8 | Yes | 127GB | 4 | 0.92 | qwen3_coder | Not tested yet (jobs cancelled) |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `5c5d82a7` — Session 47: analyze results, fix GPA CUDA 12.9

## Infrastructure Bugs Found

| Bug | Severity | Status |
|-----|----------|--------|
| GPA CUDA 12.4 nvcc + GCC 14 build failure | CRITICAL | **FIXED** (session 47) |
| --build-mode direct ignored by SWE-agent | HIGH | **FIXED** (session 46) |
| Codex+Qwen XML tool format via `/v1/responses` | HIGH | Open — vLLM `qwen3_coder` parser may not work on Responses API |
| OpenCode+Qwen `gpt-5-nano` title gen 404 | HIGH | Open — hardcoded model name |
| SWE-agent+Qwen analysis paralysis | HIGH | Open — model never calls str_replace |
| Codex `--model-name` required with `--external-model` | MEDIUM | Root cause found, added to CLAUDE.md |
| Lulesh prompt missing MPI warning | MEDIUM | Open — agent disabled MPI, causing segfault |
| Qwen reasoning parser breaks tool calls | CRITICAL | **FIXED** (session 45) |
| SWE-agent cost limit crash on self-hosted models | CRITICAL | **FIXED** (session 45) |
| Kripke CHAI required for CUDA+MPI | CRITICAL | **FIXED** (session 43) |
| GPA b+tree/backprop build fail (gcc14) | LOW | Open — upstream C code issue |
| GPA lavaMD config error | LOW | Open — case sensitivity bug in GPA driver |

## Recent Decisions

- 2026-03-10 (s47): Cancel all pending Qwen3.5-122B jobs — same root causes would waste ~60 node-hours
- 2026-03-10 (s47): Run LLNL and GPA as separate jobs — co-scheduling wastes a node
- 2026-03-10 (s47): Always pass `--model-name` with `--external-model` — added to CLAUDE.md rule #9
- 2026-03-10 (s47): GPA needs explicit `module load cudatoolkit/12.9` + CUDA_HOME override in runner
- 2026-03-10 (s47): SWE-agent `parse_function: function_calling` works for Qwen (tool calls succeed) but model has behavioral issue
- 2026-03-10 (s46): Fix --build-mode direct for SWE-agent LLNL apps and GPA prompt API consistency
- 2026-03-10 (s46): Submit all 26 benchmark jobs simultaneously
- 2026-03-10 (s45): Remove reasoning parser from all Qwen MODEL_REGISTRY entries
- 2026-03-09 (s44): GPA driver `run_driver()` API changed — must use `DriverConfig` object

## Next Steps

### Priority 1: Fix Remaining Root Causes
1. **SWE-agent+Qwen analysis paralysis** — Try `parse_function: thought_action` mode or add stronger edit-forcing language to prompts. The model makes valid tool calls but never chooses `str_replace`. Check if SWE-agent docs mention alternative parse modes for Qwen.
2. **Codex+Qwen `/v1/responses` tool parsing** — vLLM's `qwen3_coder` parser may only work on `/v1/chat/completions`. Since Codex requires `wire_api=responses`, check if vLLM even supports tool parsing on that endpoint. May need to drop Codex+Qwen.
3. **OpenCode+Qwen `gpt-5-nano` title gen** — Configure OpenCode to use the main model for titles or disable title generation.
4. **Lulesh MPI prompt** — Add explicit "DO NOT disable MPI" warning to prompt templates.

### Priority 2: Re-submit Fixed Runs
1. Submit LLNL-only jobs (`--kripke --laghos --lulesh --quicksilver`) — no `--gpa`
2. Submit GPA-only jobs (`--gpa`) separately
3. Re-submit Codex+gpt-5.3-codex with `--model-name gpt-5.3-codex --external-model`
4. Submit Claude Code + profiling variant (missing from session 46)
5. Only re-submit Qwen runs for frameworks where root causes are fixed

### Priority 3: Deeper Analysis
1. Investigate OpenHands+Qwen (mixed results — one run got 1/20 success)
2. Compare Claude Code's optimization strategies across apps
3. Test if `thought_action` parse mode helps Qwen in SWE-agent
