# Phase 2: Benchmark Expansion — Goal Checklist

## Design Decisions (already made — do not revisit)

1. **GPA agent workspace model**: Agent gets a workspace directory with kernel `.cu` file(s), profiling output, and a prompt file. Agent edits files in place. We read modified files and pass to `run_driver(swaps_override=...)`. This is consistent with the LLNL proxy app flow.
2. **GPA: no git patches**: GPA comparison is timing-based (baseline vs optimized speedup), not patch-based. The `BenchmarkResult.agent_patch` field stores the optimized code. `agent_speedup` stores the timing ratio. No `expert_commit` or `file_overlap` for GPA tasks.
3. **GPA scope**: All 17 active apps from `driver_apps.yaml`. Validate with easy tier first (gaussian, hotspot, particlefilter, xsbench), then enable all apps once infra works.
4. **SWE-fficiency**: Full integration — verify eval pipeline on Perlmutter, then create inference specs for all 4 frameworks and wire into benchmark runner.
5. **Curated commits benchmark**: Run the 9 expert commits from `dataset/curated_perf_commits.json` across frameworks.

## Goals

- [x] Goal 0: Create feature branch `benchmark-expansion` off `local`

- [x] Goal 1: GPA-Benchmark — Workspace setup and driver integration
  - Add `/pscratch/sd/k/krydzy/GPA-Benchmark` to `sys.path` in `hpc_benchmark_runner.py`
  - Add `--app gpa` support to `batch/run_benchmark.sh` arg parsing
  - Implement GPA workspace setup in the runner:
    - For each GPA app instance, create a workspace dir
    - Copy kernel file(s) from `driver_apps.yaml` `kernel_file` + `extra_files` into workspace
    - Optionally include baseline profiling output (nsys/ncu) if `--profiling` flag
  - Implement GPA result collection:
    - After agent runs, read modified kernel file(s) from workspace
    - Call `run_driver(app=X, swaps_override={app: {filename: modified_code}}, sm_version=80, nsys=True)`
    - `run_driver()` returns `(results, operations, long_results)`:
      - `results[app]` is `AppResults` with `.build`, `.run`, `.validate` bools + `.swap_builds_numerator/denominator` etc.
      - `long_results[app]` is `List[DriverPassResult]` — first entry is baseline, rest are swaps
      - Each `DriverPassResult` has `.build`, `.run`, `.validate`, `.run_stdout`, `.nsys_data`
      - Timing from `nsys_data`: `[d["exec_time"] for d in pass_result.nsys_data]` (list of kernel times)
    - Map to `BenchmarkResult` fields:
      - `agent_builds` = swap pass `.build` succeeded
      - `agent_correctness` = swap pass `.validate` succeeded
      - `agent_speedup` = baseline nsys exec_time.mean / swap nsys exec_time.mean
      - `agent_patch` = the modified kernel code (for logging)
  - For `--base` mode: just run `run_driver(app=X)` with no swaps to verify baseline works
  - IMPORTANT: `run_driver()` runs from the GPA-Benchmark repo root. Either `os.chdir("/pscratch/sd/k/krydzy/GPA-Benchmark")` before calling, or ensure paths resolve correctly.
  - Support all 17 apps from `driver_apps.yaml` (iterate over app configs)
  - Read `.claude/skills/gpa-benchmark/SKILL.md` for driver API details

- [x] Goal 2: GPA-Benchmark — Agent prompt and config
  - Create prompt template for GPA tasks that includes:
    - The kernel source code (from `kernel_file`)
    - Baseline profiling output (nsys/ncu kernel timing) so the agent can see performance characteristics
    - Instructions: "optimize this CUDA kernel for better GPU performance, write your changes to [filename]"
    - Available tools: build, run, profile (if applicable)
    - Do NOT tell the agent what the anti-pattern is — they should diagnose it themselves
  - Create `config/hpc/gpa_no_profiling.yaml` and `gpa_with_profiling.yaml` (for SWE-agent)
  - For other frameworks (OpenCode, Codex, OpenHands): generate equivalent prompt/config
    using the same pattern as existing LLNL app configs in `config/hpc/`
  - The prompt should tell the agent to modify the kernel file(s) in-place in the workspace

- [x] Goal 3: GPA-Benchmark — Validate on compute node
  - Base mode all 17 apps: 16/17 PASS, 1 FAIL (lulesh — empty upstream LULESH/ dir)
  - Fixed lavaMD case-sensitivity bug in GPA driver (app name comparisons now case-insensitive)
  - Agent mode infrastructure verified: workspace setup, config generation, launch scripts all work
  - NOTE: GPA lulesh is an upstream issue (missing source in GPA-Benchmark/LULESH/), not our integration

- [ ] Goal 4: SWE-fficiency — Verify eval pipeline on Perlmutter
  - Check podman-hpc compatibility:
    - Can `podman-hpc pull ghcr.io/swefficiency/swefficiency-images:<instance_id>` work?
    - Does `swefficiency eval` use Docker SDK or shell commands?
    - If Docker SDK: check if podman socket is available or if we need `DOCKER_HOST` env var
  - Set up SWE-fficiency Python env:
    - `cd /pscratch/sd/k/krydzy/swefficiency && uv venv --python 3.12 && source .venv/bin/activate && uv sync`
  - Test eval on a small subset using existing predictions:
    - Pick 2-3 instances from `predictions/converted/oh_claude45sonnet.jsonl`
    - Run `swefficiency eval --run_id test_perlmutter --prediction_path <subset.jsonl> --instances_regex "<selected_ids>" --num_workers 1`
    - If podman issues: document blocker, try workarounds (DOCKER_HOST, podman socket)
  - If eval works: run `swefficiency report` and verify output
  - This goal is DONE when we know: (a) eval works on Perlmutter, or (b) it's blocked with documented reason

- [ ] Goal 5: SWE-fficiency — Create inference specs for all frameworks (DEPENDS ON Goal 4 — if Goal 4 is BLOCKED, mark this BLOCKED too)
  - Create inference spec YAMLs for each framework in `/pscratch/sd/k/krydzy/swefficiency/scripts/inference/specs/`:
    - `sweagent.yaml`, `opencode.yaml`, `codex_cli.yaml`, `openhands.yaml`
    - Follow the pattern in `cursor_cli.yaml`: docker config, prework (install framework), inference command, patch extraction
  - Add `--app swefficiency` support to `batch/run_benchmark.sh` and `hpc_benchmark_runner.py`
  - Wire into our dispatch: runner calls `custom.py` with the right spec, then feeds patches to `swefficiency eval`
  - Map SWE-fficiency results (SR, correctness) to `BenchmarkResult` format
  - Select a curated subset of instances for benchmarking (not all 498 — pick ~20-50 representative ones across repos)

- [ ] Goal 6: SWE-fficiency — Validate agent integration (DEPENDS ON Goals 4+5)
  - Test one framework (e.g., opencode) on 2-3 SWE-fficiency instances end-to-end
  - Verify: agent runs inside container, produces patch, eval computes SR, results in `benchmark_results.json`
  - If podman/container issues: document and try workarounds

- [ ] Goal 7: Curated performance commits benchmark
  - Run the 9 expert commits from `dataset/curated_perf_commits.json`
  - Use existing `--instance-id` support in `run_benchmark.sh`
  - Test with at least 2 frameworks (e.g., opencode + codex)
  - Collect results: compare agent patches vs expert patches (file overlap, patch similarity, speedup)

- [ ] Goal 8: Unified results and regression test
  - Existing LLNL app benchmarks (`--app kripke/laghos/lulesh/quicksilver`) still work unchanged
  - `batch/run_benchmark.sh --help` shows new `--app gpa` and `--app swefficiency` options
  - `benchmark_results.json` output includes GPA and SWE-fficiency results in compatible format
  - Update skills and docs
  - Commit all changes

## Key Integration Points

**GPA-Benchmark driver API:**
```python
import os, sys
sys.path.insert(0, "/pscratch/sd/k/krydzy/GPA-Benchmark")
os.chdir("/pscratch/sd/k/krydzy/GPA-Benchmark")  # driver uses relative paths from repo root
from gpa_bench_driver import run_driver

# Base mode — just build+run+validate
results, operations, long_results = run_driver(app="gaussian", sm_version=80)
# results["gaussian"].build / .run / .validate  (booleans)
# long_results["gaussian"][0].run_stdout  (baseline stdout)

# Agent mode — swap in optimized code + profile for timing
results, operations, long_results = run_driver(
    app="gaussian",
    sm_version=80,
    nsys=True,  # enables timing via Nsight Systems
    swaps_override={"gaussian": {"gaussian.cu": optimized_code_string}},
)
# long_results["gaussian"][0] = baseline DriverPassResult
# long_results["gaussian"][1] = swap DriverPassResult
# Timing: pass_result.nsys_data -> [{"exec_time": float, ...}, ...]
# Speedup: baseline_exec_time_mean / swap_exec_time_mean
# Correctness: results["gaussian"].swap_valid_numerator / swap_valid_denominator
```

**GPA `driver_apps.yaml` fields per app:**
- `name` — app identifier (e.g., "gaussian")
- `kernel_file` — path to the CUDA file the agent should optimize (e.g., "rodinia/cuda/gaussian/gaussian.cu")
- `extra_files` — additional source files the agent might need to see
- `kernel_name` — the specific GPU kernel function name
- `path` — build directory
- `run_command` — how to execute
- Validation: `fail_check_text`, `pass_check_text`, `reference_output`, `float_grep`

**SWE-fficiency eval:**
```bash
cd /pscratch/sd/k/krydzy/swefficiency
source .venv/bin/activate
swefficiency eval --run_id test --prediction_path predictions/converted/oh_claude45sonnet.jsonl --instances_regex "numpy__numpy-18065" --num_workers 1
swefficiency report --gold_run logs/run_evaluation/test/gold --pred_run logs/run_evaluation/test/oh_claude45sonnet
```

**SWE-fficiency inference harness:**
```bash
python scripts/inference/custom.py \
  --run-id my_run \
  --spec scripts/inference/specs/opencode.yaml \
  --num-workers 4 \
  --instance-ids numpy__numpy-18065 pandas-dev__pandas-28447
```
Output: `logs/run_inference/<run_id>/<spec_name>/<instance_id>/patch.diff`
