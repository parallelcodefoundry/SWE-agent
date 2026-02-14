---
name: swe-agent-framework
description: "SWE-agent framework configuration and benchmarking. Use when user mentions 'swe-agent', 'sweagent', agent configuration, tool bundles, benchmark instances, or SWE-agent sandbox issues."
---

# SWE-agent Framework

## Branch Structure

- **`main`** tracks upstream SWE-agent (last synced at `fc0469ad`).
- **`local`** is our working branch (all HPC customizations). Create feature branches off `local`, not `main`.

## CLI

Entry: `sweagent/__main__.py` -> `sweagent/run/run.py`.

```bash
# Single run
sweagent run --config config/hpc/kripke_no_profiling.yaml \
    --agent.model.per_instance_cost_limit=0 \
    --agent.model.max_input_tokens=120000

# Batch run
sweagent run-batch \
    --instances.type file --instances.path dataset/curated_perf_commits.json \
    --config config/hpc/kripke_no_profiling.yaml \
    --agent.model.name gpt-4o
```

Other subcommands: `run-replay`, `merge-preds`, `inspect` (`i`), `shell` (`sh`), `quick-stats` (`qs`).

## HPC Harness Tools Per App

| App | Build | Run |
|-----|-------|-----|
| Kripke | `kripke_build` | `kripke_run` |
| Laghos | `laghos_build` | `laghos_run` |
| Lulesh | `lulesh_build` | `lulesh_run` |
| Quicksilver | `qs_build` | `qs_run` |

Each `*_run` tool runs pristine baseline, runs agent's modified version, compares timing (speedup) and outputs (correctness), and reports: CORRECTNESS, BASELINE TIME, MODIFIED TIME, SPEEDUP.

## Benchmark Pipeline

Two modes. See `batch/run_benchmark.sh --help` for all arguments.

- **Benchmark mode** (default): Checks out pre-optimization commits from `dataset/curated_perf_commits.json`, runs agent, compares agent patch vs expert patch.
- **Base mode** (`--base`): Runs agent on current `_test` repo state, no dataset checkout.

```bash
sbatch batch/run_benchmark.sh --lulesh --num-probs 2        # benchmark mode
sbatch batch/run_benchmark.sh --base --lulesh --both         # base mode
sbatch batch/run_benchmark.sh --instance-id kripke__07b2b60d # single instance
```

Results: `batch_results/benchmark_*/benchmark_results.json` (benchmark) or `results.json` (base).

## Local Deployment Key Facts

- `deployment.type: local` -- commands execute directly on the host via bash
- `tools_base_path: /tmp/sweagent` (replaces Docker's `/root`)
- Tool scripts uploaded to `/tmp/sweagent/tools/`
- Repository used in-place (no copying for `LocalRepoConfig`)

## Critical Known Issues

1. **Double openai prefix**: vLLM models need `openai/openai/MODEL` (not `openai/MODEL`)
2. **Tool schema types**: Use `number` not `float` -- OpenAI rejects `float`
3. **SWE-agent copies tools to `/tmp/sweagent/`**: Script-relative paths break. Use `SWE_AGENT_ROOT` env var
4. **MPI execution**: `kripke_run` uses `mpirun` (not `srun`) to avoid nested srun hangs
5. **Parser auto-submit**: Patched parser auto-submits on unparseable actions
6. **External model routing**: Config `api_base`/`api_key` must be stripped so LiteLLM uses env vars
7. **g++-12 required**: Lulesh/Quicksilver need `g++-12` -- nvcc incompatible with g++ 13

For detailed reference, see references/ in this skill directory.
