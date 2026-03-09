# Benchmark Results Analysis Guide

How to analyze results from HPC agent benchmark runs. Follow this checklist for every completed job.

## Result Locations

```
batch_results/
  benchmark_{JOBID}.out          # SLURM stdout — top-level orchestration log
  benchmark_{JOBID}.err          # SLURM stderr
  {framework}_{model}_{timestamp}_{JOBID}/
    all_results.json             # Master results: speedup, patch stats, correctness per app/mode
    vllm.log                     # vLLM server startup log (if applicable)
    run_1_{no,with}_profiling/{llnl,gpa}/
      agent.log                  # Benchmark runner summary log (small, framework-agnostic)
      benchmark.log              # Harness output (build, run, timing, correctness)
      benchmark_results.json     # Per-app structured results
      {app}__base_agent_realtime.log   # Full agent session log (FRAMEWORK-SPECIFIC FORMAT)
      {app}__base_agent.patch          # Git diff of agent changes
      {app}__base_prompt.txt           # Prompt sent to agent
      {app}__base_*_config.*           # Framework config (YAML/JSON/TOML/TXT)
trajectories/
  {framework}_{model}_{timestamp}_{JOBID}/
    run_1_{mode}/{app}/
      {instance}.traj            # SWE-agent trajectory (JSON)
      {instance}.jsonl           # OpenCode/Claude trajectory (JSON-Lines)
      # OpenHands: no trajectory files generated
```

## Analysis Checklist

### 1. Job Status
```bash
sacct -u krydzy -j {JOBID} --format=JobID,JobName,State,ExitCode,Elapsed -n
```
- COMPLETED with 0:0 → normal finish
- FAILED → check benchmark_{JOBID}.err for SLURM/script errors
- TIMEOUT → walltime exceeded, check if agent was still working

### 2. Top-Level Results (all_results.json)
```bash
jq -r '.[] | "\(.app)\t\(.mode)\t\(.speedup // "null")\t+\(.lines_added // 0)/-\(.lines_removed // 0)\t\(.correctness // "?")"' \
  batch_results/{result_dir}/all_results.json | column -t
```
Key fields (identical schema across all frameworks, 24 fields):
- `speedup` — float or null. >1.0 = improvement, <1.0 = regression, null = no valid timing
- `agent_insertions`/`agent_deletions` — patch size. 0/0 = agent made no edits
- `agent_builds`/`agent_correctness` — PASSED/FAILED/unknown
- `error_message` — if present, describes what went wrong
- `agent_patch` — full diff text

### 3. Did the Agent Try Edits?
- Check `agent_insertions`/`agent_deletions` in all_results.json
- If 0/0: agent either never launched, timed out before editing, or reverted all changes
- Read the `.patch` file: `cat {result_dir}/run_1_*/llnl/{app}__base_agent.patch`

### 4. Agent Behavior Deep-Dive (per app)

This is the core analysis step. The **realtime log** (`*_agent_realtime.log`) contains the full agent session — every tool call, model response, error, and iteration. **Format differs by framework** (see Section 8 below).

For each app, determine:

**Commands/tools executed:**
- Which harness tools did it call? (`*_build`, `*_run`, `hpc_profile`, `hatchet_analyze`, `nsys_*`, `ncu_*`)
- Did it use profiling tools? Which ones? How many times?
- Total iteration count (tool calls / turns)

**Edit patterns:**
- What source files did it modify?
- Were changes meaningful (algorithmic, compiler flags, kernel optimization) or superficial?
- Did it revert changes after seeing regressions?

**Error handling & iteration:**
- Build failures: did the agent retry with fixes or abandon?
- Runtime errors: segfaults, wrong answers — did it debug and iterate?
- How many build-edit-test cycles did it complete?

**Exit reason:**
- Normal completion (agent declared done)
- Timeout (hit walltime or framework timeout)
- Context exhaustion (hit token limit)
- Framework crash (Pydantic error, API error, etc.)
- Early exit (model said "done" prematurely)

### 5. Failure Classification

Classify each run into one of these categories:

| Category | Description | Whose fault? |
|----------|-------------|--------------|
| **model_no_edit** | Agent completed but made no meaningful edits | Model |
| **model_bad_edit** | Agent edited code but broke build or correctness | Model |
| **model_regression** | Agent's changes made performance worse (speedup < 1.0) | Model |
| **model_timeout** | Agent ran out of time mid-optimization | Model (maybe) |
| **model_context_exhaustion** | Agent hit token limit | Model/framework |
| **model_exit_early** | Agent declared done prematurely (e.g., Codex `needs_follow_up=false`) | Model |
| **build_failure** | App failed to build at baseline (before agent) | Infrastructure |
| **harness_bug** | Harness tool error (permissions, parsing, config) | Infrastructure |
| **framework_crash** | Agent framework crashed (Pydantic, OOM, etc.) | Infrastructure |
| **vllm_error** | vLLM server failed to start or crashed mid-run | Infrastructure |
| **slurm_kill** | Job killed by SLURM (walltime, OOM, node failure) | Infrastructure |
| **agent_never_launched** | Benchmark runner skipped agent invocation | Infrastructure |

### 6. Infrastructure Issues
Flag any failures NOT caused by the model — these are bugs we need to fix:
- Harness tools returning errors for valid code
- Build system failures unrelated to agent edits
- Framework crashes (Pydantic validation, import errors)
- vLLM server startup failures
- Incorrect module loads or missing dependencies
- Permission errors on harness scripts

### 7. Cross-Framework Comparison
When multiple frameworks ran on the same apps/model:
- Compare speedups per app across frameworks
- Note which frameworks got farther (more tools called, more iterations)
- Check if the same apps fail across all frameworks (= infrastructure issue)
- Compare patch sizes and approaches — did different agents find different optimizations?

---

## 8. Framework-Specific Log Formats

Each framework produces a `*_agent_realtime.log` with a completely different format. This section documents how to parse each one for the deep-dive analysis in step 4.

### 8.1 SWE-Agent

**Files:**
- `{app}__base_agent_realtime.log` — Plain text with emoji markers (~1.5MB)
- `{app}__base_config.yaml` — SWE-agent YAML config
- Trajectory: `trajectories/.../run_1_{mode}/{app}/{app}__base/{uuid}/{uuid}.traj` (JSON)

**Log format:** Plain text with ANSI color codes and emoji markers per message type:
```
🏃 INFO     — Informational messages
🤖 WARN     — Model warnings
🧰 DEBUG    — Debug output
🤠 INFO SYSTEM / DEMONSTRATION / MODEL INPUT — Structured sections
💭 THOUGHT  — Agent's reasoning text
🎬 ACTION   — Tool execution with command details
```

**How to extract:**
```bash
# Count tool calls
grep -c "🎬 ACTION" {realtime_log}

# List all tool calls
grep "🎬 ACTION" {realtime_log}

# Find errors in tool outputs
grep -A5 "error\|FAILED\|Error" {realtime_log} | head -40

# Check exit reason — look at end of log
tail -50 {realtime_log}

# Check SLURM step cancellations
grep "slurmstepd\|CANCELLED" {realtime_log}
```

**Trajectory file (.traj) format:** JSON with `"trajectory"` array. Each entry has:
```json
{
  "action": "command --args",
  "observation": "tool output or error",
  "response": "full model response",
  "thought": "agent's reasoning",
  "execution_time": 1.23
}
```
- Iteration count = length of `trajectory` array
- Exit reason = last entry's `observation`
- Error iteration = entries where `observation` contains error text

### 8.2 OpenCode

**Files:**
- `{app}__base_agent_realtime.log` — Structured service logs (~148KB)
- `{app}__base_opencode_config.json` — JSON config (provider, model, permissions)
- Trajectory: `trajectories/.../run_1_{mode}/{app}/{app}__base.jsonl` (JSON-Lines)

**Log format:** One log entry per line with structured service fields:
```
LEVEL  TIMESTAMP +OFFSET_MS service=service_name [key=value...]
```
Service names: `default`, `config`, `session`, `provider`, `tool.registry`, `bash-tool`, `bus`

Also contains JSON event objects inline:
```json
{"type":"step_finish","timestamp":...,"sessionID":"...","part":{...}}
```

**How to extract:**
```bash
# Count iterations (step increments)
grep -c "service=session.prompt step=" {realtime_log}

# List tool executions
grep "service=bash-tool\|service=tool.registry" {realtime_log}

# Find errors
grep "ERROR\|error\|failed" {realtime_log}

# Check exit reason
grep "exiting loop" {realtime_log}
tail -20 {realtime_log}
```

### 8.3 OpenHands

**Files:**
- `{app}__base_agent_realtime.log` — Python logging output (~33KB)
- `{app}__base_openhands_config.toml` — TOML config (model, api_base, max_iterations)
- Trajectory: **None generated** (`trajectory_file: null` in results)

**Log format:** Rich Python logging with timestamps:
```
[MM/DD/YY HH:MM:SS] LEVEL logger_module - key=value pairs
```
Contains: configuration dumps, state initialization, agent lifecycle events, full Python tracebacks on errors.

**How to extract:**
```bash
# Find errors and crashes
grep "ERROR\|Traceback\|Exception" {realtime_log}

# Check for specific crash types
grep "ConversationRunError\|LLMBadRequestError\|ValidationError\|Pydantic" {realtime_log}

# Check exit — last lines or exception
tail -30 {realtime_log}

# Find tool usage
grep "terminal\|file_editor\|CmdRunAction\|FileEditAction" {realtime_log}
```

**Key crash patterns:**
- `1 validation error for Message content.0` — Pydantic validation error on API response
- `LLMBadRequestError` — Model API rejected request (e.g., empty tool_calls array)
- `ConversationRunError` — Generic agent loop failure
- Log just stops — hit `max_iterations` (default 200) or `no_change_timeout_seconds` (600s)

### 8.4 Claude Code

**Files:**
- `{app}__base_agent_realtime.log` — JSON-Lines, one event per line (~819KB)
- `{app}__base_claude_config.txt` — Plain text config (version, auth, model, permissions)
- Trajectory: `trajectories/.../run_1_{mode}/{app}/{app}__base.jsonl` (JSON-Lines, same as realtime)

**Log format:** Each line is a JSON object with event type:
```json
{"type":"system","subtype":"init","session_id":"...","message":{...}}
{"type":"assistant","message":{"role":"assistant","content":[
  {"type":"thinking","thinking":"agent reasoning..."},
  {"type":"tool_use","name":"Bash","input":{"command":"..."}},
  {"type":"text","text":"..."}
]}}
{"type":"user","message":{"role":"user","content":[
  {"type":"tool_result","tool_use_id":"...","content":"stdout output"}
]}}
```

**How to extract:**
```bash
# Count turns (assistant messages = iterations)
grep -c '"type":"assistant"' {realtime_log}

# List all tool calls with names
python3 -c "
import json
with open('{realtime_log}') as f:
    for line in f:
        evt = json.loads(line)
        if evt.get('type') == 'assistant':
            for c in evt.get('message',{}).get('content',[]):
                if c.get('type') == 'tool_use':
                    print(f\"{c['name']}: {str(c.get('input',{}))[:100]}\")
"

# Find errors in tool results
grep '"tool_result"' {realtime_log} | grep -i "error\|failed\|traceback"

# Check thinking/reasoning
python3 -c "
import json
with open('{realtime_log}') as f:
    for line in f:
        evt = json.loads(line)
        if evt.get('type') == 'assistant':
            for c in evt.get('message',{}).get('content',[]):
                if c.get('type') == 'thinking':
                    print(c['thinking'][:200])
                    print('---')
"

# Token usage
grep '"usage"' {realtime_log} | tail -1
```

**Key fields:** `usage.input_tokens`, `usage.output_tokens`, `usage.cache_read_input_tokens`, `stop_reason`

### 8.5 Codex CLI

**Files:**
- `{app}__base_agent_realtime.log` — JSON-Lines event stream
- `{app}__base_codex_config.json` — JSON config
- Trajectory: `trajectories/.../run_1_{mode}/{app}/{app}__base.jsonl`

**Key quirk:** Codex may exit early with `needs_follow_up=false` after a single turn. Check the `exec_result` events for `exit_code` and whether it iterated at all.

---

## Quick One-Liner Analysis

```bash
# Summarize all results for a job
jq -r '.[] | "\(.app)\t\(.mode)\t\(.speedup // "null")\t+\(.agent_insertions // 0)/-\(.agent_deletions // 0)\t\(.agent_correctness // "?")"' \
  batch_results/{result_dir}/all_results.json | column -t

# Find apps where agent made real edits
jq -r '.[] | select(.agent_insertions > 0 or .agent_deletions > 0) | "\(.app) \(.mode) +\(.agent_insertions)/-\(.agent_deletions)"' \
  batch_results/{result_dir}/all_results.json

# Find infrastructure failures
jq -r '.[] | select(.error_message != null) | "\(.app): \(.error_message)"' \
  batch_results/{result_dir}/all_results.json

# Compare speedups across frameworks for same model
for d in batch_results/*_{MODEL}_*; do
  echo "=== $(basename $d) ==="
  jq -r '.[] | select(.speedup != null) | "\(.app) \(.mode) \(.speedup)"' $d/all_results.json 2>/dev/null
done
```
