# Session 46 Benchmark Results Tracking

Last updated: 2026-03-10 (session 47, analysis in progress)

## Overview

26 benchmark jobs submitted in session 46, all with `--build-mode direct`, across 5 models and 4 frameworks.

**Overall: Near-total failure. 6 distinct root causes identified — 4 infrastructure, 1 model, 1 partial success.**

## Root Cause Summary

| # | Root Cause | Category | Scope | Fix Needed |
|---|-----------|----------|-------|------------|
| 1 | **GPA baseline builds all fail** | `build_failure` (infra) | ALL GPA instances (16/20 per run) | nvcc 12.4 rejects GCC >13. GPA needs CUDA 12.9 but getting 12.4's nvcc |
| 2 | **Codex+Qwen: `<tool_call>` XML not parsed** | `model_exit_early` (framework) | ALL Codex+Qwen runs (4 jobs) | Codex doesn't parse Qwen's XML tool format → `needs_follow_up=false` → 1-turn exit |
| 3 | **OpenCode+Qwen: same XML issue + gpt-5-nano 404** | `framework_crash` (infra) | ALL OpenCode+Qwen runs (4 jobs) | Qwen XML not parsed + OpenCode title gen calls `gpt-5-nano` → 404 on vLLM → crash |
| 4 | **SWE-agent+Qwen: model reads but never edits** | `model_no_edit` (model) | ALL SWE-agent+Qwen runs (4 jobs) | Agent does 180+ `view` calls, 0 `str_replace` calls across 196 steps |
| 5 | **Codex+external (gpt-5.3): wrong base_url** | `framework_crash` (infra) | 1 job (49878383) | Missing `--model-name` → `model_name=None` → falls into local vLLM path → `http://external:0/v1` |
| 6 | **Claude Code: partial success (3/4 LLNL)** | mixed | 1 job (49878379) | Not a failure — Kripke 2.03x, Laghos 1.30x, QS 1.70x; Lulesh failed (disabled MPI) |

## Job Inventory

### Completed (17/26)

| Job ID | Nodes | Framework | Model | Prof | Time | Success | Root Cause |
|--------|-------|-----------|-------|------|------|---------|------------|
| 49878379 | 5N | claude | Claude Code | no | 1h11m | **3/20** | GPA infra fail (#1); LLNL partial success |
| 49878383 | 4N | codex | gpt-5.3-codex (ext) | no | 3m28s | 0/4 | #5: model_no_edit |
| 49878446 | 6N | sweagent | Qwen3-Coder | no | 1h10m | 0/20 | #1 (GPA) + #4 (LLNL: 196 steps, 0 edits) |
| 49878454 | 6N | codex | Qwen3-Coder | no | 8m51s | 0/20 | #1 (GPA) + #2 (LLNL: 1-turn exit, XML) |
| 49878455 | 6N | opencode | Qwen3-Coder | no | 10m42s | 0/20 | #1 (GPA) + #3 (LLNL: XML + gpt-5-nano 404) |
| 49878456 | 6N | openhands | Qwen3-Coder | no | 1h08m | 0/20 | #1 (GPA) + TBD (LLNL: needs log check) |
| 49878460 | 6N | sweagent | Qwen3-Coder | yes | 1h13m | 0/18 | #1 (GPA) + #4 (LLNL) |
| 49878461 | 6N | codex | Qwen3-Coder | yes | 10m38s | 0/20 | #1 (GPA) + #2 (LLNL) |
| 49878462 | 6N | opencode | Qwen3-Coder | yes | 10m18s | 0/20 | #1 (GPA) + #3 (LLNL) |
| 49878463 | 6N | openhands | Qwen3-Coder | yes | 1h19m | 1/20 | #1 (GPA); LLNL: 1/4 somehow succeeded |
| 49878468 | 6N | sweagent | Qwen3.5-27B | no | 1h10m | 0/20 | #1 (GPA) + #4 (LLNL) |
| 49878469 | 6N | sweagent | Qwen3.5-27B | yes | 57m10s | 0/16 | #1 (GPA) + #4 (LLNL) |
| 49878471 | 6N | codex | Qwen3.5-27B | no | 9m32s | 0/20 | #1 (GPA) + #2 (LLNL) |
| 49878473 | 6N | codex | Qwen3.5-27B | yes | 10m56s | 0/20 | #1 (GPA) + #2 (LLNL) |
| 49878475 | 6N | opencode | Qwen3.5-27B | no | 9m10s | 0/20 | #1 (GPA) + #3 (LLNL) |
| 49878476 | 6N | opencode | Qwen3.5-27B | yes | 10m42s | 0/20 | #1 (GPA) + #3 (LLNL) |
| 49878479 | 6N | openhands | Qwen3.5-27B | yes | 8m17s | 0/20 | #1 (GPA) + TBD (LLNL) |

### Still Pending/Running (9/26 — all Qwen3.5-122B)

| Job ID | Framework | Model | Profiling | Status |
|--------|-----------|-------|-----------|--------|
| 49878477 | openhands | Qwen3.5-27B | no | RUNNING |
| 49878520-529 | all 4 | Qwen3.5-122B | both | 8 PENDING |

**Note**: Pending 122B jobs will hit same root causes #1-4. Results will be wasted node-hours.

## Submission Issues

1. **Codex external (49878383)**: Submitted WITHOUT `--gpa` — only 4 LLNL apps.
2. **GPA co-scheduled with LLNL**: 6 nodes = 5 apps + 1 vLLM. GPA consumes a node for the entire 1hr+ job but has ~16 short tasks. Should run separately.
3. **No Claude Code + profiling run**: Only submitted no-profiling variant for Claude Code.

## Detailed Failure Analysis

### Root Cause #1: GPA Baseline Build Failures — FIXED

**Scope**: ALL 16 GPA sub-apps fail with "Build failed for baseline" across EVERY run.
**Category**: `build_failure` (infrastructure)
**Impact**: 16/20 instances per run were dead-on-arrival.
**Root cause**: nvcc from CUDA 12.4 rejects GCC 14 (`#error -- unsupported GNU version!`). Two bugs:
1. `run_benchmark.sh` only skipped loading 12.4 for GPA but didn't unload inherited 12.4 or load 12.9
2. `hpc_benchmark_runner.py:_run_gpa_driver()` didn't pass `cuda_home` to `DriverConfig` — GPA driver's `detect_cuda_home()` found 12.4's nvcc from PATH
**Fix applied** (session 47):
- `run_benchmark.sh`: Explicit `module unload cudatoolkit; module load cudatoolkit/12.9` for GPA
- `hpc_benchmark_runner.py`: Detect CUDA 12.9, set `CUDA_HOME`, prepend to PATH, pass to `DriverConfig`
**Test result**: 13/16 GPA apps now build+run+validate. Remaining 3 are known upstream bugs:
- b+tree, backprop: K&R C code + gcc-14 (upstream)
- lavaMD: case-sensitivity bug in GPA driver (upstream)

### Root Cause #2: Codex CLI + Qwen — XML Tool Call Format Mismatch

**Scope**: ALL Codex + Qwen model runs (49878454, 49878461, 49878471, 49878473)
**Category**: `model_exit_early` (framework-model incompatibility)
**Evidence** (job 49878454, kripke):
```
{"type":"item.completed","item":{"text":"I'll start by building the application...\n\n<tool_call>\n<function=update_plan>..."}}
...
needs_follow_up=false
Shutting down Codex instance
```
**Root cause**: Qwen outputs `<tool_call><function=name>` XML in its text response. Codex CLI expects OpenAI Responses API tool calling format. The XML is treated as plain text → Codex sees no tool calls → `needs_follow_up=false` → shuts down after 1 turn.
**Fix options**:
- Use `wire_api=chat` for vLLM (already set?) — check if vLLM's `qwen3_coder` parser intercepts these
- Or: Codex doesn't support arbitrary OpenAI-compatible models well

### Root Cause #3: OpenCode + Qwen — Same XML Issue + gpt-5-nano 404

**Scope**: ALL OpenCode + Qwen model runs (49878455, 49878462, 49878475, 49878476)
**Category**: `framework_crash` (infrastructure)
**Evidence** (job 49878455, kripke):
```
{"type":"text","text":"I'll start by building...\n\n<tool_call>\n<function=bash>..."}
...
step_finish reason="stop"  (NOT tool_use — XML not parsed)
...
service=llm modelID=gpt-5-nano ... error=404 "The model gpt-5-nano does not exist."
...
"No output generated. Check the stream for errors." rejection
exiting loop
```
**Root cause**: Two-part failure:
1. Same Qwen XML format issue as Codex — tool calls in text not recognized
2. After step finishes, OpenCode tries to generate a title using `gpt-5-nano` (hardcoded small model). vLLM only serves the Qwen model → 404 → crash → exit after 1 step.
**Fix options**:
- Configure OpenCode to skip title generation or use the same model for titles
- Same XML parsing issue as Codex

### Root Cause #4: SWE-agent + Qwen — Model Stuck in Read-Only Analysis

**Scope**: ALL SWE-agent + Qwen runs, both models (49878446, 49878460, 49878468, 49878469)
**Category**: `model_no_edit` (model behavior)
**Evidence** (job 49878446, all 4 LLNL apps):
```
kripke: 196 steps, 182 views, 0 edits, 0 creates, 13 bash
laghos: 201 steps, 168 views, 0 edits, 0 creates, 33 bash
lulesh: 196 steps, 180 views, 0 edits, 0 creates, 15 bash
quicksilver: 201 steps, 177 views, 0 edits, 0 creates, 24 bash
```
Same for Qwen3.5-27B (49878468):
```
kripke: 84 steps, 67 views, 0 edits, 16 bash
lulesh: 172 steps, 2 views, 0 edits, 166 bash (!)
quicksilver: 152 steps, 145 views, 0 edits, 5 bash
```
**Root cause**: Qwen models make valid function calls (bash, str_replace_editor/view) but NEVER call `str_replace` or `create` to edit files. They explore the entire codebase but don't commit to changes. The 27B model on lulesh ran 166 bash commands (probably cmake/make over and over) but still no source edits.
**Note**: SWE-agent warns "Model does not support function calling" at startup but function calling clearly works (all calls succeed). The warning may be cosmetic.
**Fix options**: This is a model capability issue. The Qwen models may need stronger prompting to force edits, or they may simply not be capable of the edit loop in SWE-agent's tool format.

### Root Cause #5: Codex + External Model (gpt-5.3-codex) — Wrong base_url

**Scope**: Job 49878383 (4 LLNL apps)
**Category**: `framework_crash` (infrastructure bug in benchmark runner)
**Evidence**: All 4 apps failed with connection errors to `http://external:0/v1/responses`. Every API request got instant connection refused. 25 retries per app, then shutdown.
**Root cause**: Job was submitted with `--external-model` but **without `--model-name`**. In `codex.py:_build_config_flags()`:
- `self.model_name` was `None` → fell into "Local vLLM" code path (line 66)
- `run_benchmark.sh` sets `VLLM_HOST="external"` and `VLLM_PORT="0"` for external model mode
- Constructed bogus URL `http://external:0/v1` from these dummy values
- Model was hardcoded to `openai/gpt-oss-120b` (wrong — should be `gpt-5.3-codex`)
**Fix**: Always pass `--model-name` when using `--external-model`, OR fix the None-model fallback in codex.py

## Claude Code Results (49878379) — The Partial Success

**LLNL Results (3/4 success — excellent for a first run!)**:

| App | Patch | Speedup | Correctness | Strategy | Classification |
|-----|-------|---------|-------------|----------|---------------|
| Kripke | 4 files, +19/-9 | **2.03x** | PASSED | Fused kConst zero-init into LTimes/LPlusTimes kernels, eliminating 2 kernel launches/iter | model_success |
| Laghos | 4 files, +17/-54 | **1.30x** | PASSED | Relaxed CG tol 1e-8→1e-6, reduced max iters, disabled sync, fast_math, NBZ=4 batch | model_success |
| Lulesh | 2 lines, +2/-2 | N/A | **FAILED** (segfault) | Disabled MPI (`USE_MPI=0`) — harness runs np=8, causing segfault | **model_bad_edit** |
| Quicksilver | 7 files, +123/-50 | **1.70x** | PASSED | Batched atomics, sincos(), eliminated stack array, cached UVM pointers, reduced nBatches | model_success |

**Average speedup across 3 successful LLNL apps: 1.68x**

**GPA Results**: ALL 16 failed — `build_failure` (Root Cause #1: nvcc 12.4 + GCC 14)
**Total**: 3/20 (16 GPA infra failures + 1 LLNL model_bad_edit)

## Action Items

### Cancel Pending Jobs (IMMEDIATE)
- [ ] Cancel all 8 pending Qwen3.5-122B jobs (49878520-529) — they will hit the same root causes
- [ ] Cancel 49878477, 49878479 if still running — same issues

### Fix Root Causes Before Re-submitting
- [x] **RC#1**: GPA baseline build failures — **FIXED** (CUDA 12.9 path + DriverConfig cuda_home). 13/16 pass.
- [ ] **RC#2+3**: Codex/OpenCode + Qwen XML format — check if `wire_api=chat` + vLLM parser can fix this, or if these frameworks fundamentally can't support Qwen
- [ ] **RC#3 extra**: OpenCode `gpt-5-nano` title gen — configure to use main model or disable
- [ ] **RC#4**: SWE-agent + Qwen no-edit — try stronger prompting ("You MUST call str_replace_editor with command=str_replace") or accept this is a model limitation
- [x] **RC#5**: Codex + gpt-5.3 external model — root cause confirmed: missing `--model-name` flag. Fix: always pass `--model-name` with `--external-model`

### Re-submission Plan (after fixes)
- [ ] Run LLNL and GPA as **SEPARATE** jobs (not co-scheduled — saves 1 node per job)
- [ ] Submit Claude Code + profiling variant (was missing from session 46)
- [ ] Re-submit Codex + gpt-5.3-codex with `--model-name gpt-5.3-codex`
- [ ] Consider dropping Codex+Qwen and OpenCode+Qwen if XML issue is unfixable
- [ ] For SWE-agent+Qwen: try stronger edit-forcing prompts before dropping
