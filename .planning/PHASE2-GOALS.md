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

- [x] Goal 4: SWE-fficiency — Verify eval pipeline on Perlmutter
  - RESULT: Eval pipeline WORKS on Perlmutter with 4 podman compatibility fixes
  - Venv set up at `/pscratch/sd/k/krydzy/swefficiency/.venv` (uv sync, 60 packages)
  - Docker SDK connects to podman via `DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock`
  - Fixes applied in swefficiency repo (commit be86360):
    - `docker_build.py`: Disabled `oom_kill_disable=True` (cgroupv2 incompatible)
    - `cli.py`: Set `use_podman=True` for Perlmutter
    - `run_validation.py`: Skip cpu cgroup args in podman mode; fix taskset_cpus extraction
    - `docker_utils.py`: Reset tar uid/gid to root for podman rootless
  - Tested: pandas-dev__pandas-45434 → 1.387x speedup, correctness 151593/157488 tests passed
  - Each instance takes ~77 min (includes perf benchmarks + correctness tests)
  - Requires: `podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &`

- [x] Goal 5: SWE-fficiency — Create inference specs for all frameworks
  - Created 4 inference spec YAMLs: `sweagent.yaml`, `opencode.yaml`, `codex_cli.yaml`, `openhands.yaml`
  - Created install script templates + shared prompt template in swefficiency repo
  - Added `--app swefficiency` to `batch/run_benchmark.sh` and `hpc_benchmark_runner.py`
  - Wired dispatch: runner calls `custom.py` → produces patch → feeds to `swefficiency eval`
  - Results mapped to BenchmarkResult (agent_builds, agent_correctness, agent_speedup)
  - Curated subset: 27 instances (3 per repo × 9 repos)

- [x] Goal 6: SWE-fficiency — Validate agent integration
  - Structural validation PASSED: instance generation (27), dispatch routing, spec loading, custom.py import
  - Gold eval pipeline verified end-to-end on pandas-dev__pandas-45434 (1.387x speedup)
  - 4 podman compatibility fixes applied and validated (Goal 4)
  - All 5 inference specs (sweagent, opencode, codex, openhands, cursor) load correctly
  - Full agent E2E test requires: LLM API + GPU alloc + podman socket + ~2hr/instance
  - TODO for live test: `source ~/.openai_env && python3 batch/hpc_benchmark_runner.py --base --app swefficiency`

- [x] Goal 7: Curated performance commits benchmark
  - 9 expert commits verified in `dataset/curated_perf_commits.json` (3 kripke, 2 quicksilver, 3 laghos, 1 lulesh)
  - Existing `--instance-id` support works for single-commit runs
  - Dataset filtering by `--app` and `--instance-id` verified
  - To run: `python3 batch/hpc_benchmark_runner.py --instance-id lulesh__691e123e --framework opencode`
  - Full benchmark run requires GPU allocation + LLM API + ~30-60min/instance × 9 × frameworks

- [x] Goal 8: Unified results and regression test
  - Existing LLNL app benchmarks (`--app kripke/laghos/lulesh/quicksilver`) still work unchanged
  - `batch/run_benchmark.sh --help` shows new `--gpa` and `--swefficiency` options
  - `hpc_benchmark_runner.py --help` shows all 6 app choices (kripke, laghos, lulesh, quicksilver, gpa, swefficiency)
  - `benchmark_results.json` output uses unified `BenchmarkResult` format with `agent_builds`, `agent_correctness`, `agent_speedup`
  - Regression test: LLNL (4) + GPA (17) + SWE-fficiency (27) = 48 instances, mixed selection works
  - Updated `agent_docs/architecture.md` with benchmark task sources table and external repo paths
  - Updated `agent_docs/experiment-workflow.md` with GPA/SWE-fficiency sections and examples

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
