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
      agent.log                  # Agent session log (commands, model responses, tool calls)
      benchmark.log              # Harness output (build, run, timing, correctness)
      benchmark_results.json     # Per-app structured results
      workspaces/{app}/          # Agent's working copy (source edits, build artifacts)
trajectories/
  {framework}_{model}_{timestamp}_{JOBID}/
    {app}_{mode}.traj            # SWE-agent trajectory files (if sweagent framework)
```

## Analysis Checklist

### 1. Job Status
```bash
sacct -u krydzy -j {JOBID} --format=JobID,JobName,State,ExitCode,Elapsed -n
```
- COMPLETED with 0:0 → normal finish
- FAILED → check benchmark_{JOBID}.err for SLURM/script errors
- TIMEOUT → walltime exceeded, check if agent was still working

### 2. Top-Level Results
```bash
python3 -c "
import json
with open('batch_results/{result_dir}/all_results.json') as f:
    results = json.load(f)
for r in results:
    print(f\"{r['app']:20s} {r['mode']:20s} speedup={r.get('speedup','N/A'):>8s} patch={r.get('lines_added',0):+d}/{r.get('lines_removed',0):-d} correct={r.get('correctness','?')}\")
"
```
Key fields in each result entry:
- `speedup` — float or null. >1.0 = improvement, <1.0 = regression, null = no valid timing
- `lines_added`/`lines_removed` — patch size. 0/0 = agent made no edits
- `correctness` — PASSED/FAILED/unknown
- `error_message` — if present, describes what went wrong

### 3. Did the Agent Try Edits?
- Check `lines_added`/`lines_removed` in all_results.json
- If 0/0: agent either never launched, timed out before editing, or reverted all changes
- Look at `workspaces/{app}/` for actual file diffs: `git -C workspaces/{app} diff HEAD`

### 4. Agent Behavior Deep-Dive (per app)
Read `agent.log` for the full session. Look for:

**Commands executed:**
- Which harness tools did it call? (`*_build`, `*_run`, `hpc_profile`, `hatchet_analyze`, `nsys_*`, `ncu_*`)
- Did it use profiling tools? Which ones? How many times?
- Did it iterate on build errors or give up?

**Edit patterns:**
- What source files did it modify?
- Were changes meaningful (algorithmic, compiler flags, kernel optimization) or superficial?
- Did it revert changes after seeing regressions?

**Error handling:**
- Build failures: did the agent retry with fixes or abandon?
- Runtime errors: segfaults, wrong answers — did it debug?
- Tool errors: did harness/profiler tools fail? (indicates infrastructure bug, not model issue)

### 5. Failure Classification

Classify each failed run into one of these categories:

| Category | Description | Whose fault? |
|----------|-------------|--------------|
| **model_no_edit** | Agent completed but made no meaningful edits | Model |
| **model_bad_edit** | Agent edited code but broke build or correctness | Model |
| **model_timeout** | Agent ran out of time mid-optimization | Model (maybe) |
| **model_context_exhaustion** | Agent hit token limit | Model/framework |
| **model_exit_early** | Agent declared done prematurely (e.g., Codex `needs_follow_up=false`) | Model |
| **build_failure** | App failed to build at baseline (before agent) | Infrastructure |
| **harness_bug** | Harness tool error (permissions, parsing, config) | Infrastructure |
| **framework_crash** | Agent framework crashed (Pydantic, OOM, etc.) | Infrastructure |
| **vllm_error** | vLLM server failed to start or crashed mid-run | Infrastructure |
| **slurm_kill** | Job killed by SLURM (walltime, OOM, node failure) | Infrastructure |
| **agent_never_launched** | Benchmark runner skipped agent invocation (e.g., GPA bug) | Infrastructure |

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

## Quick One-Liner Analysis

```bash
# Summarize all results for a job
jq -r '.[] | "\(.app)\t\(.mode)\t\(.speedup // "null")\t+\(.lines_added // 0)/-\(.lines_removed // 0)\t\(.correctness // "?")"' \
  batch_results/{result_dir}/all_results.json | column -t

# Find apps where agent made real edits
jq -r '.[] | select(.lines_added > 0 or .lines_removed > 0) | "\(.app) \(.mode) +\(.lines_added)/-\(.lines_removed)"' \
  batch_results/{result_dir}/all_results.json

# Find infrastructure failures (baseline build failures)
jq -r '.[] | select(.error_message != null) | "\(.app): \(.error_message)"' \
  batch_results/{result_dir}/all_results.json

# Count tool calls in agent log
grep -c "COMMAND:" batch_results/{result_dir}/run_1_*/llnl/agent.log
```
