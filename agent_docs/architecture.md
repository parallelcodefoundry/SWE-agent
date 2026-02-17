# Architecture Reference

For per-app build details, profiling tool usage, and framework specifics, see the skill files in `.claude/skills/`. This doc covers the system design and research goals.

## Research Goal

Determine which LLM coding agent framework is best at optimizing HPC code, then prove that adding profiling/analysis tools to that framework significantly improves results. The experimental design:

1. **Phase 1**: Run all frameworks (SWE-agent, Openhands, Codex CLI, OpenCode, Cursor) on the same optimization tasks **without** profiling tools. Identify which framework produces the best speedups.
2. **Phase 2**: Add profiling tools (HPCToolkit, Hatchet, Nsight, compiler analysis) to the winning framework. Run the same tasks again **with** profiling.
3. **Phase 3**: Compare with/without profiling results to demonstrate that tool-augmented agents achieve significantly better optimization outcomes.

## Why Harnesses Exist

Agents can't just `make && ./run` — they need structured feedback. Each harness (`tools/*_harness/`) provides:

- **`app_build`**: Wraps the build system, returns JSON success/failure with error context the agent can act on. Handles architecture selection (CUDA/OpenMP), clean rebuilds, and GPU-specific flags.
- **`app_run`**: The core measurement tool. Automatically builds and runs the **pristine** baseline with identical parameters, then runs the agent's modified version. Returns correctness (scientific values within tolerance) and speedup (baseline_time / modified_time) in one call. This is how we get reliable, comparable measurements — the agent doesn't estimate its own performance.

This design means every `app_run` call produces a ground-truth measurement against an unmodified baseline, regardless of what the agent has done to the code.

## With vs Without Profiling

The profiling comparison is controlled by which tool bundles a config loads:

| Config variant | Tools available | Purpose |
|---|---|---|
| `{app}_no_profiling.yaml` | build, run, code editor | Baseline: can the agent optimize from source reading alone? |
| `{app}_with_profiling.yaml` | build, run, code editor, **hpc_profile, hatchet_analyze, compiler_analysis, microbench_code** | Treatment: does profiling data lead to better optimizations? |

Both variants use the same agent prompts, model, and evaluation. The only difference is tool access.

## Project Layout

```
tools/
  {kripke,laghos,lulesh,quicksilver}_harness/  # App harnesses (build/run/correctness)
  hpctoolkit/, hatchet/                         # Profiling + analysis (working)
  profiling/                                    # benchmark_code, microbench_code, compiler_analysis
  nsight_compute/, nsight_systems/              # Nsight wrappers (bin/ only, no config.yaml yet)
config/hpc/
  {app}_{with|no}_profiling.yaml                # SWE-agent configs (one per app × profiling variant)
  gpa_{no|with}_profiling.yaml                  # GPA-Benchmark SWE-agent configs
batch/
  run_benchmark.sh                              # SLURM entrypoint (vLLM + benchmark orchestration)
  hpc_benchmark_runner.py                       # All modes: benchmark, base (--base), all app types
  frameworks/                                   # Multi-framework support
    __init__.py                                 # get_launcher() factory
    base.py                                     # FrameworkLauncher ABC + shared helpers
    prompt.py                                   # Per-app prompt templates for all frameworks
    sweagent.py                                 # SWE-agent launcher (YAML configs)
    opencode.py                                 # OpenCode launcher (JSON config, opencode run)
    openhands.py                                # OpenHands launcher (TOML config, headless mode)
    codex.py                                    # Codex CLI launcher (AGENTS.md, codex exec)
dataset/
  curated_perf_commits.json                     # 9 expert optimization commits across 4 apps
scripts/
  setup_apps.sh, reset_test_repos.sh            # Build and reset app repos
{App}/ → pristine repos (NEVER modify)
{App}_test/ → working copies for experiments

# External repos (separate git repos with their own commits)
/pscratch/sd/k/krydzy/GPA-Benchmark/           # 16 GPU anti-pattern kernels + driver
/pscratch/sd/k/krydzy/swefficiency/            # SWE-fficiency eval pipeline + inference specs
```

## Data Flow

```
pristine repo ──clone──→ workspace (checked out to base_commit)
                              │
                    ┌─────────┴─────────┐
                    │   AGENT SESSION    │
                    │                    │
                    │  read source       │
                    │  (optionally profile: hpc_profile → hatchet_analyze)
                    │  edit source       │
                    │  app_build         │
                    │  app_run ─────→ builds pristine baseline
                    │     │             runs both, compares
                    │     └──→ CORRECTNESS + SPEEDUP returned to agent
                    │  repeat / submit   │
                    └────────────────────┘
                              │
                    benchmark runner extracts agent patch
                    compares to expert patch (file overlap, diff similarity)
                              │
                    benchmark_results.json
```

## Multi-Framework Support

The benchmark pipeline supports 4 agent frameworks via `--framework`:

| Framework | Config Format | Launch Command | Completion Signal |
|-----------|--------------|----------------|-------------------|
| SWE-agent (default) | YAML | `sweagent run --config` | `submit` command |
| OpenCode | JSON env var | `opencode run --format json` | Stops when done |
| OpenHands | TOML | `openhands --headless -t` | `finish` action |
| Codex CLI | `-c` flags + AGENTS.md | `codex exec --yolo` | Stops when done |

All frameworks share:
- Same harness tools (build/run scripts in PATH)
- Same workspace setup (rsync from test repo or git clone from pristine)
- Same patch extraction (`git diff` from workspace)
- Same result format (`benchmark_results.json` with `framework` field)
- Equivalent prompts (tool names adapted per framework)
- SWE_AGENT_ROOT env var (harness scripts need it)
- 3600s session timeout via `timeout` command

```bash
# Cross-framework comparison
bash batch/run_benchmark.sh --base --lulesh --framework sweagent
bash batch/run_benchmark.sh --base --lulesh --framework opencode --external-model
bash batch/run_benchmark.sh --base --lulesh --framework openhands --external-model
bash batch/run_benchmark.sh --base --lulesh --framework codex --external-model
```

## Benchmark Task Sources

The pipeline supports three categories of optimization tasks via `--app`:

| Source | Flag | Tasks | Language | Metric |
|--------|------|-------|----------|--------|
| LLNL Proxy Apps | `--app kripke/laghos/lulesh/quicksilver` | 9 curated commits | C++/CUDA | Speedup vs expert patch |
| GPA-Benchmark | `--app gpa` | 16 GPU kernels | CUDA | Speedup vs baseline (nsys timing) |
| SWE-fficiency | `--app swefficiency` | 12 parallel-focused instances | Python | Speedup vs baseline (containerized eval) |

**LLNL Proxy Apps**: Agent receives a workspace checked out to a pre-optimization commit. Must find and apply the same (or better) optimization as the expert. Harness tools (`app_build`, `app_run`) measure correctness and speedup against a pristine baseline.

**GPA-Benchmark**: Agent receives a CUDA kernel file with a known GPU performance anti-pattern. Must diagnose and fix the issue. The GPA driver (`run_driver()`) compiles, validates, and profiles the optimized code using Nsight Systems to measure kernel execution time speedup.

**SWE-fficiency**: Agent runs inside a Docker/podman container with a Python project. Must optimize Python code to pass performance benchmarks. Eval harness measures correctness (test suite) and speedup (timing benchmarks) in isolation. Instances are curated for parallelization/concurrency optimization (joblib, threading, Cython prange, vectorization). SWE-fficiency is intentionally CPU-Python — no GPU/CUDA instances exist in the dataset.

**Total: 37 benchmark instances** across 3 optimization dimensions (LLNL 9 + GPA 16 + SWE-fficiency 12).

```bash
# Run all task sources
python3 batch/hpc_benchmark_runner.py --base --app kripke --app gpa --app swefficiency

# Single GPA app validation
python3 batch/hpc_benchmark_runner.py --base --app gpa

# Single curated commit
python3 batch/hpc_benchmark_runner.py --instance-id lulesh__691e123e --framework opencode
```

**Unified benchmark**: The pipeline runs any combination of framework × application × profiling variant, producing directly comparable `benchmark_results.json` output with `agent_builds`, `agent_correctness`, and `agent_speedup` fields.
