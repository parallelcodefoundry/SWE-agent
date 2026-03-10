# Handoff — Session 47

Last updated: 2026-03-10

## What We Were Implementing and Why

Session 47 analyzed ALL 26 benchmark jobs submitted in session 46. The goal was to understand why nearly everything failed (only Claude Code got 3/20 successes) and fix what we could.

## Approach Chosen

- Launched 4 parallel analysis agents to investigate different failure categories
- Manually traced agent logs for SWE-agent, Codex, and OpenCode to identify exact failure points
- GPA analysis agent both diagnosed AND fixed the CUDA 12.9 issue
- Cancelled 10 pending jobs to save node-hours

## Goal Progress

- [x] Goal 0: Load state, check job status
- [x] Goal 1: Identify and categorize all failure modes across 17 completed jobs
- [x] Goal 2: Analyze Claude Code results (3/4 LLNL success: Kripke 2.03x, Laghos 1.30x, QS 1.70x)
- [x] Goal 3: Diagnose Codex+Qwen XML tool format mismatch (`<tool_call>` XML not parsed by Responses API)
- [x] Goal 4: Diagnose OpenCode+Qwen (same XML + `gpt-5-nano` 404)
- [x] Goal 5: Diagnose SWE-agent+Qwen analysis paralysis (196 steps, 182 views, 0 edits)
- [x] Goal 6: Diagnose Codex+external missing `--model-name` → bogus `http://external:0/v1` URL
- [x] Goal 7: Fix GPA CUDA 12.9 build failure (13/16 apps now work)
- [x] Goal 8: Cancel pending 122B jobs (10 jobs, ~60 node-hours saved)
- [x] Goal 9: Create `.planning/RESULTS-TRACKING-S46.md` tracking file
- [x] Goal 10: Add `--model-name` and GPA separation rules to CLAUDE.md
- [x] Goal 11: Commit and save state
- [ ] Goal 12: Fix SWE-agent+Qwen parse mode (NEXT SESSION)
- [ ] Goal 13: Fix Codex/OpenCode+Qwen tool format (NEXT SESSION)
- [ ] Goal 14: Add MPI warning to prompts (NEXT SESSION)
- [ ] Goal 15: Re-submit fixed runs (NEXT SESSION)

## Files Modified This Session

- `batch/hpc_benchmark_runner.py:1057-1094` — GPA CUDA 12.9 fix: detect correct cuda_home, set CUDA_HOME env, prepend to PATH, pass to DriverConfig
- `batch/run_benchmark.sh:837-846` — GPA module fix: explicit `module unload cudatoolkit; module load cudatoolkit/12.9` for GPA sruns
- `CLAUDE.md:89-90` — Added rules #9 (`--model-name` with `--external-model`) and #10 (separate LLNL/GPA jobs)
- `.planning/RESULTS-TRACKING-S46.md` — Created: full failure analysis with per-job root causes

## Files to Read First Next Session

- `.planning/RESULTS-TRACKING-S46.md` — Complete failure analysis (read first to remember all 6 root causes)
- `batch/frameworks/sweagent.py` — SWE-agent launcher, may need `parse_function` changes for Qwen
- `batch/frameworks/codex.py:28-77` — `_build_config_flags()` with 3-branch model routing (first-party/external/local-vLLM)
- `batch/frameworks/opencode.py` — OpenCode launcher, check if title gen model is configurable
- `batch/frameworks/prompt.py:~200-400` — Prompt templates, need to add MPI warning for Lulesh
- `config/hpc/llnl_base.yaml` — SWE-agent YAML template with `parse_function: type: function_calling`

## Gotchas and Decisions

- **SWE-agent `parse_function: function_calling` DOES work for Qwen** — tool calls (bash, str_replace_editor/view) all execute correctly. The problem is purely behavioral: the model never chooses to call `str_replace` (edit). The "does not support function calling" warning at startup is a false positive (SWE-agent checks model name against a hardcoded list).
- **Codex uses `wire_api=responses` exclusively** — `wire_api=chat` is explicitly commented as "no longer supported" in codex.py. This means vLLM's `qwen3_coder` parser (which works on `/v1/chat/completions`) may not apply to the Responses API endpoint.
- **OpenCode tries `gpt-5-nano` for title gen** — Hardcoded small model call. When vLLM only serves Qwen, this 404s and kills the session after 1 step.
- **Qwen outputs `<tool_call><function=name>` XML in Codex/OpenCode** — This is the raw Qwen tool call format. In SWE-agent (via `/v1/chat/completions` + `qwen3_coder` parser), vLLM intercepts this and returns proper `tool_calls` JSON. In Codex/OpenCode (via `/v1/responses`), it passes through as plain text.
- **Claude Code Lulesh: agent set `USE_MPI ?= 0`** — Makefile already has `# MPI enabled by default for multi-GPU execution (8 ranks = 2x2x2 on 4 GPUs)` comment, but agent ignored it. Prompt needs explicit "DO NOT disable MPI".
- **GPA CUDA fix tested on login node only** — Login nodes have different CUDA/gcc than compute nodes. Need to validate on compute node with `salloc`.

## Specific Next-Session Investigation Tasks

### Task A: SWE-agent + Qwen Parse Mode (use subagent)
**Goal**: Determine if changing `parse_function` helps Qwen produce edits.
**Files**: `config/hpc/llnl_base.yaml`, SWE-agent docs at `docs/usage/cl_tutorial.md`
**Approach**:
1. Check SWE-agent source for available `parse_function` types — is `thought_action` an option?
2. Try a quick interactive test: run SWE-agent on a single app (e.g., lulesh) with `thought_action` parse mode
3. If that doesn't help, try adding explicit "YOU MUST USE str_replace_editor command=str_replace TO EDIT FILES" to system prompt
4. Consider if the issue is that Qwen's `<tool_call>` XML is being parsed correctly but the model genuinely can't/won't edit HPC code

### Task B: Codex/OpenCode + Qwen Responses API (use subagent)
**Goal**: Determine if Codex/OpenCode can work with Qwen at all.
**Files**: `batch/frameworks/codex.py`, `batch/frameworks/opencode.py`
**Approach**:
1. Check if vLLM supports tool call parsing on `/v1/responses` endpoint (read vLLM docs/source)
2. If not, Codex+Qwen is fundamentally broken and should be dropped
3. For OpenCode: check if the title gen model is configurable (env var? config option?)
4. Check if OpenCode can use `/v1/chat/completions` instead of `/v1/responses`

### Task C: Add MPI Warning to Prompts
**Goal**: Prevent agents from disabling MPI.
**Files**: `batch/frameworks/prompt.py`
**Approach**: Add to all LLNL prompt templates:
```
CRITICAL: Do NOT disable MPI. The validation harness runs with mpirun -np N.
Disabling MPI (e.g., USE_MPI=0) will cause segfaults during validation.
```

### Task D: Validate GPA Fix on Compute Node
**Goal**: Confirm GPA CUDA 12.9 fix works on actual compute nodes.
**Approach**:
```bash
salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m5083
# Then test:
source ~/envs/sweagent/bin/activate
module load python cmake openmpi/5.0.7
module load cudatoolkit/12.9
python3 batch/hpc_benchmark_runner.py --base --app gpa --framework claude --skip-vllm
```

### Task E: Re-submit Corrected Runs
**Goal**: Get real benchmark data.
**Submission plan** (separate LLNL and GPA):
```bash
# Claude Code LLNL (no profiling)
bash batch/run_benchmark.sh --base --build-mode direct --framework claude --kripke --laghos --lulesh --quicksilver

# Claude Code LLNL (with profiling)
bash batch/run_benchmark.sh --base --build-mode direct --framework claude --kripke --laghos --lulesh --quicksilver --profiling with_profiling

# Claude Code GPA (separate)
bash batch/run_benchmark.sh --base --build-mode direct --framework claude --gpa

# Codex + gpt-5.3-codex (with correct --model-name)
bash batch/run_benchmark.sh --base --build-mode direct --framework codex --external-model --model-name gpt-5.3-codex --kripke --laghos --lulesh --quicksilver

# SWE-agent + Qwen (only if Task A shows parse mode fix works)
bash batch/run_benchmark.sh --base --build-mode direct --framework sweagent --model-name Qwen/Qwen3-Coder-Next-FP8 --kripke --laghos --lulesh --quicksilver
```

## Interactive Validation Commands

```bash
salloc --nodes 1 --qos interactive --time 03:00:00 --constraint gpu --gpus 4 --account m5083

# Module setup
source /opt/cray/pe/lmod/lmod/init/bash
module load python cmake openmpi/5.0.7
source ~/envs/sweagent/bin/activate

# Quick GPA validation (compute node)
module load cudatoolkit/12.9
python3 -c "
from pathlib import Path
import sys; sys.path.insert(0, '/pscratch/sd/k/krydzy/GPA-Benchmark')
from gpa_bench_driver.gpa_bench_driver import run_driver
from gpa_bench_driver.driver_src.driver_models import DriverConfig
config = DriverConfig(app='hotspot', sm_version=80, cuda_home=Path('/opt/nvidia/hpc_sdk/Linux_x86_64/25.5/cuda/12.9'), no_sanitize=True)
result = run_driver(config)
print(f'Result: {result}')
"

# Quick SWE-agent parse mode test
# (after changing config/hpc/llnl_base.yaml parse_function type)
```
