# HPC Agent Benchmark Suite

LLM agent benchmark for HPC code optimization. Tests whether coding agents (SWE-agent, Openhands, Claude Code, Codex, Cursor, OpenCode) can optimize real proxy apps on NERSC Perlmutter (A100 GPUs). Built on SWE-agent; `main` tracks upstream, `local` is our working branch. Create feature branches off `local`.

## Session Workflow

IMPORTANT: Follow this workflow for EVERY session.

- ALWAYS run /load-state as the VERY FIRST action when starting a new session or after context reset. Do NOT start work until state is loaded.
- Use /compact after verbose build output or every ~30 minutes. Delegate research to subagents to protect main context.
- When context usage exceeds 70%, IMMEDIATELY run /save-state before doing anything else. Autocompact triggers at 90% — this gives a 20% buffer.
- You MUST run /save-state before EVERY exit attempt. NEVER stop without saving state first.
- When compacting, ALWAYS preserve: STATE.md contents, HANDOFF.md goal checklist, all file paths discussed, SLURM job IDs, and current task description.

## Project Structure

- `tools/*_harness/` — Per-app build/run/correctness harnesses (SWE-agent tool format)
- `tools/{hatchet,hpctoolkit,nsight_*,profiling}/` — Profiling tool wrappers
- `config/hpc/` — SWE-agent YAML configs (`{app}_{with|no}_profiling.yaml`)
- `batch/` — `run_benchmark.sh` (entrypoint), `hpc_benchmark_runner.py`
- `scripts/` — `setup_apps.sh`, `reset_test_repos.sh`
- `dataset/` — `curated_perf_commits.json` (expert optimization commits)
- `{Kripke,Laghos,Lulesh,Quicksilver}/` — Pristine app clones (NEVER modify)
- `{Kripke,Laghos,Lulesh,Quicksilver}_test/` — Working copies for agent experiments
- `mfem/`, `hypre/`, `metis-4.0.3/` — Shared Laghos dependencies

## Key Commands

```bash
# Interactive GPU node
salloc --nodes 1 --qos interactive --time 03:00:00 --constraint gpu --gpus 4 --account m2404

# Modules (always load before build/run)
module load python cmake openmpi/5.0.7 cuda/12.4

# Build all proxy apps (run on compute node)
./scripts/setup_apps.sh

# Reset test repos to clean state
./scripts/reset_test_repos.sh                    # all apps
./scripts/reset_test_repos.sh --lulesh --kripke  # specific apps

# Run benchmarks
sbatch batch/run_benchmark.sh                          # all apps, benchmark mode
sbatch batch/run_benchmark.sh --base --lulesh          # base mode, single app
sbatch batch/run_benchmark.sh --instance-id kripke__07b2b60d  # single commit

# Python env
source ~/envs/sweagent/bin/activate
```

## Critical Rules

1. **Never modify pristine repos** (`Kripke/`, `Laghos/`, `Lulesh/`, `Quicksilver/`). Only touch `*_test/` copies.
2. **GPU builds require compute nodes** — never build on login nodes (no nvcc, no GPU libs).
3. **Lulesh and Quicksilver need g++-12** — nvcc is incompatible with g++ 13 for `-std=c++11`.
4. **Kripke has 44+ submodules** — disable submodule recursion in `_test` repos (`git config --local submodule.recurse false`).
5. **Laghos dependencies** — mfem/hypre/metis live as sibling dirs, shared by both pristine and `_test`. METIS download can fail; pre-download if needed.
6. **Always reset `_test` repos** between experiment runs to ensure clean state.
7. **If a command fails with stale Python/tools** — likely an outdated module; load a newer version.
8. **NERSC account**: `m2404` for all SLURM jobs.
