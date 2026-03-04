# HPC Agent Benchmark Suite

LLM agent benchmark for HPC code optimization. Tests whether coding agents (SWE-agent, OpenHands, Claude Code, Codex, OpenCode) can optimize real proxy apps on NERSC Perlmutter (A100 GPUs). Base mode is the primary benchmark mode: one instance per app, agents optimize from clean source. Built on SWE-agent; `main` tracks upstream, `dev` is our working branch.

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
- `batch/frameworks/` — Per-framework launchers + shared `prompt.py`
- `scripts/` — `setup_apps.sh`, `reset_test_repos.sh`
- `dataset/` — `curated_perf_commits.json` (preserved for future use, not loaded by default)
- `{Kripke,Laghos,Lulesh,Quicksilver}/` — Pristine app clones (NEVER modify)
- `{Kripke,Laghos,Lulesh,Quicksilver}_test/` — Working copies for agent experiments
- `mfem/`, `hypre/`, `metis-4.0.3/` — Shared Laghos dependencies

## Key Commands

```bash
# Interactive GPU node
salloc --nodes 1 --qos interactive --time 03:00:00 --constraint gpu --gpus 4 --account m5083

# Modules (always load before build/run)
module load python cmake openmpi/5.0.7 cuda/12.4

# Build all proxy apps (run on compute node)
./scripts/setup_apps.sh

# Reset test repos to clean state
./scripts/reset_test_repos.sh                    # all apps
./scripts/reset_test_repos.sh --lulesh --kripke  # specific apps

# Run benchmarks (base mode is primary)
sbatch batch/run_benchmark.sh --base --lulesh --framework claude
sbatch batch/run_benchmark.sh --base --kripke --framework codex --external-model
sbatch batch/run_benchmark.sh --base --build-mode direct --lulesh  # agent builds manually

# Python env
source ~/envs/sweagent/bin/activate
```

## Build Modes

- **`harness` (default)**: Harness tools (`*_build`, `*_run`) handle compilation. Agent edits source and optionally build config; harness ensures essential flags are preserved.
- **`direct`**: Agent runs cmake/make/nvcc directly. Only `*_run` is available for validation and timing. Build instructions are provided in the prompt.

## Critical Rules

1. **Never modify pristine repos** (`Kripke/`, `Laghos/`, `Lulesh/`, `Quicksilver/`). Only touch `*_test/` copies.
2. **GPU builds require compute nodes** — never build on login nodes (no nvcc, no GPU libs).
3. **Lulesh and Quicksilver need g++-12** — nvcc is incompatible with g++ 13 for `-std=c++11`.
4. **Kripke has 44+ submodules** — disable submodule recursion in `_test` repos (`git config --local submodule.recurse false`).
5. **Laghos dependencies** — mfem/hypre/metis live as sibling dirs, shared by both pristine and `_test`. METIS download can fail; pre-download if needed.
6. **Always reset `_test` repos** between experiment runs to ensure clean state.
7. **If a command fails with stale Python/tools** — likely an outdated module; load a newer version.
8. **NERSC account**: `m5083` for all SLURM jobs.
