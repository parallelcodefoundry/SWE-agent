# STATE.md — Current Project State

Last updated: 2026-02-10 (session 3)

## Active Experiments

| Name | Status | Job ID | Output Dir |
|------|--------|--------|------------|
| GPT-4o-mini (all 4 apps) | **RUNNING** | 48730028 | `batch_results/benchmark_20260210_102538_48730028/` |
| vLLM gpt-oss-120b (3 apps) | **RUNNING** | 48730084 | `batch_results/benchmark_20260210_101215_48730084/` |

### GPT-4o-mini run (external model, 4 nodes)
- Apps: kripke, laghos, lulesh, quicksilver
- Last check: All agents active. Kripke building CUDA, Laghos setting up deps, Lulesh step 21, QS step 16.
- Uses all session 3 fixes (API routing, schema, SWE_AGENT_ROOT).

### vLLM run (4 nodes: 1 vLLM + 3 apps)
- Apps: kripke, laghos, lulesh
- Last check: All agents active. Kripke/Laghos building, Lulesh step 10+.
- Uses OLD code (pre-SWE_AGENT_ROOT fix). May hit pristine path issues on `*_run`.

## Current Focus

Monitoring the two parallel test runs. Both validate infrastructure fixes. Next: analyze results, run GPT-5.1, commit.

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| Kripke-only base test | 48727963 | Cancelled (stuck on nested srun, now fixed) |
| Multi-node 3 apps | 48715768 | Laghos succeeded, Lulesh failed (model error), Kripke incomplete (copytree) |
| Kripke base w/ profiling | 48508352 | Produced agent patch |
| Kripke base no profiling | 48508352 | Produced agent patch |

## Uncommitted Changes

On `local` branch. See HANDOFF.md for detailed fix descriptions.

**Batch**: `run_benchmark.sh`, `hpc_benchmark_runner.py`, `hpc_runner.py`, `hpc_batch_runner.sh`
**Harnesses**: All 8 `*_build`/`*_run` scripts, 3 `config.yaml` files
**Configs**: All 8 `config/hpc/*.yaml`
**Deleted**: 4 `*_check_correct` scripts

## Open Issues

- Agent sometimes switches GPU builds to OpenMP (model behavior, no fix yet)
- GPT-4o-mini struggles with Quicksilver's ROCm Makefile (agent behavior, not harness bug)
- Hatchet "(0)" values confuse agent

## Next Steps

1. Monitor active runs (jobs 48730028, 48730084)
2. Run GPT-5.1: `source ~/.openai_env && bash batch/run_benchmark.sh --base --external-model --model-name gpt-5.1`
3. Commit all changes
4. Analyze results across models
5. Wire in SWE-fficiency + GPA-Benchmark
