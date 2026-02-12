# Experiment Workflow Reference

For setup prerequisites (modules, Perlmutter, salloc), see the `perlmutter` skill. For per-app build/run details, see each app's skill file. This doc covers how to run benchmarks and how the pieces fit together.

## Running a Benchmark

```bash
# Build apps first (one-time, must be on compute node)
./scripts/setup_apps.sh

# Run full benchmark (all apps, all commits, no profiling)
sbatch batch/run_benchmark.sh

# Common flags
sbatch batch/run_benchmark.sh --kripke --laghos          # specific apps
sbatch batch/run_benchmark.sh --profiling with_profiling  # enable profiling tools
sbatch batch/run_benchmark.sh --both                      # run with AND without profiling
sbatch batch/run_benchmark.sh --num-probs 2 --num-runs 3  # limit commits, repeat runs
sbatch batch/run_benchmark.sh --instance-id kripke__07b2b60d  # single commit
sbatch batch/run_benchmark.sh --base --lulesh             # base mode (no expert comparison)
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
- `benchmark_results.json` — per-instance: `instance_id`, `success`, `agent_speedup`, `agent_correctness`, `file_overlap`, `patch_similarity`, `duration_seconds`
- `*_agent.patch` — the agent's generated diff
- `*_config.yaml` — the SWE-agent config used
- `workspaces/` — cloned repos at base_commit (benchmark mode only)
- Trajectories in `trajectories/` (SWE-agent's step-by-step execution log)

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

## Adding a New Framework

The batch scripts will be expanded with a `--framework` flag. Each framework needs:
1. A launch mechanism (how to start the agent — SWE-agent uses `sweagent run`, Openhands uses `openhands --headless`, etc.)
2. Tool integration (how the framework discovers and calls harness tools — varies by framework)
3. Patch extraction (how to get the agent's final diff — git diff, output parsing, etc.)
4. Same evaluation: the harness tools and correctness checks are framework-agnostic, so results are directly comparable.
