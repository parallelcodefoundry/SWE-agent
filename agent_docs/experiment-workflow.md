# Experiment Workflow Reference

For setup prerequisites (modules, Perlmutter, salloc), see the `perlmutter` skill. For per-app build/run details, see each app's skill file. This doc covers how to run benchmarks and how the pieces fit together.

## Running a Benchmark

```bash
# Build apps first (one-time, must be on compute node)
./scripts/setup_apps.sh

# Run full benchmark (all apps, all commits, no profiling) — defaults to SWE-agent
sbatch batch/run_benchmark.sh

# Common flags — LLNL proxy apps
sbatch batch/run_benchmark.sh --kripke --laghos          # specific apps
sbatch batch/run_benchmark.sh --profiling with_profiling  # enable profiling tools
sbatch batch/run_benchmark.sh --both                      # run with AND without profiling
sbatch batch/run_benchmark.sh --num-probs 2 --num-runs 3  # limit commits, repeat runs
sbatch batch/run_benchmark.sh --instance-id kripke__07b2b60d  # single commit
sbatch batch/run_benchmark.sh --base --lulesh             # base mode (no expert comparison)

# GPA-Benchmark (17 GPU anti-pattern kernels)
sbatch batch/run_benchmark.sh --gpa --base                # validate all GPA apps
python3 batch/hpc_benchmark_runner.py --base --app gpa    # direct Python invocation

# SWE-fficiency (27 curated Python optimization tasks)
sbatch batch/run_benchmark.sh --swefficiency --base       # validate SWE-fficiency pipeline
python3 batch/hpc_benchmark_runner.py --base --app swefficiency

# Multi-framework: specify --framework to use a different agent
sbatch batch/run_benchmark.sh --base --lulesh --framework opencode --external-model
sbatch batch/run_benchmark.sh --base --lulesh --framework openhands --external-model
sbatch batch/run_benchmark.sh --base --lulesh --framework codex --external-model
```

## Benchmark Mode vs Base Mode

**Benchmark mode** (default) uses `hpc_benchmark_runner.py`. For each expert commit in `dataset/curated_perf_commits.json`:
1. Clones pristine repo, checks out `base_commit` (pre-optimization state)
2. Generates a SWE-agent config pointing to the workspace
3. Runs SWE-agent — agent explores, optionally profiles, edits, builds, runs
4. Extracts agent's patch, compares against the expert's known optimization
5. Records: speedup, correctness, file overlap, patch similarity

**Base mode** (`--base`) uses `hpc_benchmark_runner.py` with the `--base` flag. Creates an isolated workspace copy from `*_test` repos (via rsync). No expert comparison, no git checkout. Useful for testing harness changes or quick iteration.

## What `run_benchmark.sh` Orchestrates

1. Loads modules, sets up HPCToolkit (spack), configures HuggingFace cache
2. Starts vLLM server (`gpt-oss-120b`, 4 GPUs tensor-parallel) via podman-hpc
3. Applies Kripke git fixes (disables 44+ submodule recursion)
4. Calls the appropriate Python runner for each app × profiling variant
5. Cleanup: kills vLLM, resets test repos, optionally deletes profiling data

## With vs Without Profiling

The `--profiling` flag controls which SWE-agent config is used:
- `no_profiling` (default): agent gets only build + run + code editor
- `with_profiling`: agent additionally gets hpc_profile, hatchet_analyze, compiler_analysis, microbench_code
- `--both`: runs each app twice, once per variant

Same prompts, same model, same evaluation. The only variable is whether the agent has access to profiling tools. This is how we isolate the effect of profiling on optimization quality.

## How Correctness Works

Every `app_run` call is self-validating:
1. Builds the **pristine** (unmodified) app from the read-only repo as baseline
2. Runs pristine with fixed parameters → captures output + timing
3. Builds and runs the **agent-modified** version with identical parameters
4. Compares scientific output values (energy, particle counts, iterations) within tolerance
5. Returns `CORRECTNESS: PASSED/FAILED` + `SPEEDUP: X.XXx` to the agent

The agent never self-reports performance. Every measurement is a direct comparison against an untouched baseline. Pristine builds are cached per architecture so they aren't rebuilt every call.

## Results

Output lands in `batch_results/benchmark_<SLURM_JOBID>/`:
- `benchmark_results.json` — per-instance: `instance_id`, `framework`, `success`, `agent_builds`, `agent_correctness`, `agent_speedup`, `file_overlap`, `patch_similarity`, `duration_seconds`
- `*_agent.patch` — the agent's generated diff
- `*_config.yaml` / `*_opencode_config.json` / `*_openhands_config.toml` — framework-specific config
- `workspaces/` — cloned repos at base_commit (benchmark mode only)
- Trajectories in `trajectories/` (SWE-agent's step-by-step execution log)

Results from all three task sources (LLNL, GPA, SWE-fficiency) use the same `BenchmarkResult` format, so results are directly comparable across sources.

## Resetting Between Runs

```bash
./scripts/reset_test_repos.sh                    # all apps
./scripts/reset_test_repos.sh --lulesh --kripke  # specific apps
```

## Adding a New Application

1. **Harness** (`tools/myapp_harness/`): `bin/myapp_build`, `bin/myapp_run`, `config.yaml`. Follow the pattern in `tools/kripke_harness/`.
2. **Configs** (`config/hpc/myapp_{no,with}_profiling.yaml`): set repo path, env vars, tool bundles.
3. **Orchestration**: add to `setup_apps.sh`, `reset_test_repos.sh`, `hpc_benchmark_runner.py` (`REPO_CONFIG_TEMPLATES`), `run_benchmark.sh` (CLI flag).
4. **Dataset** (optional): add entries to `curated_perf_commits.json`.

## Multi-Framework Support

The `--framework` flag selects which agent framework to use. All frameworks share the same workspace setup, harness tools, patch extraction, and evaluation.

| Framework | Flag | Config | Launch | Notes |
|-----------|------|--------|--------|-------|
| SWE-agent | `--framework sweagent` (default) | YAML from config/hpc/ | `sweagent run --config` | Has submit command, YAML tool bundles |
| OpenCode | `--framework opencode` | JSON env var | `opencode run --format json` | Node.js (nvm), no submit |
| OpenHands | `--framework openhands` | TOML | `openhands --headless -t` | Python, local runtime, finish action |
| Codex CLI | `--framework codex` | `-c` flags + AGENTS.md | `codex exec --yolo` | Node.js (nvm), wire_api=chat for vLLM |

Implementation: `batch/frameworks/` contains a `FrameworkLauncher` ABC and per-framework subclasses. The `HPCBenchmarkRunner` delegates config generation, launch command building, and trajectory discovery to the active launcher.

## GPA-Benchmark Tasks

GPA-Benchmark provides 17 GPU kernels with known performance anti-patterns. The agent receives a CUDA kernel file in a workspace and must optimize it.

- **Driver**: `run_driver()` from `/pscratch/sd/k/krydzy/GPA-Benchmark` handles build/run/validate/profile
- **Base mode**: Builds and runs each app's baseline kernel; 16/17 pass (lulesh has empty upstream dir)
- **Agent mode**: Agent edits kernel in workspace → runner calls `run_driver(swaps_override=...)` → measures speedup via nsys timing
- **Configs**: `config/hpc/gpa_{no,with}_profiling.yaml` for SWE-agent; other frameworks use prompt templates

## SWE-fficiency Tasks

SWE-fficiency provides 27 curated Python optimization tasks (3 per repo × 9 repos). The agent runs inside a Docker/podman container.

- **Eval pipeline**: `/pscratch/sd/k/krydzy/swefficiency` — requires podman socket running
- **Inference specs**: `swefficiency/scripts/inference/specs/{sweagent,opencode,codex_cli,openhands}.yaml`
- **Agent mode**: Runner calls `custom.py` → agent produces patch → `swefficiency eval` measures speedup + correctness
- **Podman requirement**: `podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &`
- **Time per instance**: ~77 minutes (includes perf benchmarks + correctness tests)

## Adding a New Framework

To add a new agent framework:
1. Create `batch/frameworks/myframework.py` with a subclass of `FrameworkLauncher`
2. Implement `generate_config()`, `build_launch_command()`, `find_trajectory()`
3. Register in `batch/frameworks/__init__.py`'s `get_launcher()` factory
4. Add prompt completion instructions in `batch/frameworks/prompt.py`'s `COMPLETION_INSTRUCTIONS`
5. Add choice to CLI args in `hpc_benchmark_runner.py` and `run_benchmark.sh`
