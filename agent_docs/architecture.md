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
- **`app_check_correct`**: Standalone correctness checker (redundant since `app_run` does this, but available for debugging).

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
batch/
  run_benchmark.sh                              # SLURM entrypoint (vLLM + benchmark orchestration)
  hpc_benchmark_runner.py                       # Benchmark mode: agent vs expert commits
  hpc_runner.py                                 # Base mode: agent on current test repos
dataset/
  curated_perf_commits.json                     # 9 expert optimization commits across 4 apps
scripts/
  setup_apps.sh, reset_test_repos.sh            # Build and reset app repos
{App}/ → pristine repos (NEVER modify)
{App}_test/ → working copies for experiments
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

## Expansion Plan

**More applications**: GPA-Benchmark (20+ GPU anti-pattern benchmarks) and SWE-fficiency (498 Python optimization tasks) will be added as additional task sources. Each needs harnesses following the same build/run/correctness pattern.

**More frameworks**: Openhands, Codex CLI, OpenCode, and Cursor will be integrated into `batch/run_benchmark.sh` via framework-specific flags (e.g., `--framework openhands`). Each framework will use the same harness tools and evaluation, just invoked differently. The batch scripts will be expanded to handle framework selection, and results will be collected in a unified format for cross-framework comparison.

**Unified benchmark**: The end state is a single `run_benchmark.sh` invocation that can run any combination of framework × application × profiling variant, producing directly comparable results.
