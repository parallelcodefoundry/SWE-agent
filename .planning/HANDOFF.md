# HANDOFF.md — Monitoring Active Runs & Next Steps

Last updated: 2026-02-10 (session 3)

## What's Happening

Two parallel benchmark runs are active, testing all the infrastructure fixes from this session:

### Run 1: GPT-4o-mini (external model) — Job 48730028
- **Nodes**: nid[001012,001032,001229,001232] (4 nodes, no vLLM)
- **Apps**: kripke, laghos, lulesh, quicksilver
- **Output**: `batch_results/benchmark_20260210_102538_48730028/`
- **Last observed state** (10:25 AM):
  - Kripke: Step 1, building with CUDA
  - Laghos: Step 4, setting up dependencies (`make setup`)
  - Lulesh: Step 21, optimizing (editing Makefiles)
  - Quicksilver: Step 16, editing Makefile (agent confused by ROCm defaults, not a harness bug)
- **What to check**: All agents should complete or hit the 50-step limit. Look for `benchmark_results.json` in each app subdir.

### Run 2: vLLM gpt-oss-120b — Job 48730084
- **Nodes**: nid[001084,001124,200373,200376] (4 nodes, 1 vLLM + 3 apps)
- **Apps**: kripke, laghos, lulesh
- **Output**: `batch_results/benchmark_20260210_101215_48730084/`
- **Last observed state** (10:25 AM):
  - Kripke: Step 2, building with `--arch CUDA --clean`
  - Laghos: Step 2, building with `laghos_build --clean`
  - Lulesh: Step 10+, already optimizing and running benchmarks
- **What to check**: Same as above. This run uses the OLD code (before SWE_AGENT_ROOT fix), so pristine path issues may occur when agents call `*_run`.

## Monitoring Commands

```bash
# Job status
squeue -u krydzy

# GPT-4o-mini agent progress
for app in kripke laghos lulesh quicksilver; do
  echo "=== $app ===" && tail -20 batch_results/benchmark_20260210_102538_48730028/run_1/$app/${app}__base_agent_realtime.log
done

# vLLM agent progress
for app in kripke laghos lulesh; do
  echo "=== $app ===" && tail -20 batch_results/benchmark_20260210_101215_48730084/run_1/$app/${app}__base_agent_realtime.log
done

# Check for completed results
ls batch_results/benchmark_20260210_102538_48730028/run_1/*/benchmark_results.json 2>/dev/null
ls batch_results/benchmark_20260210_101215_48730084/run_1/*/benchmark_results.json 2>/dev/null

# Check for agent patches
ls batch_results/benchmark_20260210_102538_48730028/run_1/*/*_agent.patch 2>/dev/null
ls batch_results/benchmark_20260210_101215_48730084/run_1/*/*_agent.patch 2>/dev/null
```

## What to Do Next

1. **Check if jobs completed** — `squeue -u krydzy`. If done, check benchmark_results.json and agent patches.

2. **If vLLM run had pristine path errors** — Expected since it used pre-fix code. The SWE_AGENT_ROOT fix is now in place for future runs. May need to rerun.

3. **Run GPT-5.1** — Once a slot is free:
   ```bash
   source ~/.openai_env
   bash batch/run_benchmark.sh --base --external-model --model-name gpt-5.1
   ```
   (4 nodes, external model, no vLLM)

4. **Commit changes** — Nothing committed yet. Many files modified. See STATE.md for full list.

5. **Analyze results** — Compare speedups/correctness across models and apps.

## Fixes Applied This Session (for reference)

All fixes are in the working tree on `local` branch, uncommitted:

| Fix | Files | Issue |
|-----|-------|-------|
| Nested srun | `kripke_run` | `SLURM_STEP_ID` detection |
| Pristine build path | `kripke_run` | Check `build/` before `build_cuda/` |
| Dead check_correct | 4 scripts deleted, 3 configs | Was unused dead code |
| Hardcoded paths | All 8 harness scripts, 2 batch runners | env var → relative → error |
| External model routing | `hpc_benchmark_runner.py` | env var passthrough, strip api_base/api_key |
| Tool schema float | `laghos_harness/config.yaml` | `float` → `number` |
| Pristine path from sandbox | `hpc_benchmark_runner.py`, 4 `*_run` scripts | `SWE_AGENT_ROOT` injection + fallback |

## Key File Locations

- Batch runner: `batch/hpc_benchmark_runner.py`
- Shell entrypoint: `batch/run_benchmark.sh`
- Tool harnesses: `tools/{app}_harness/bin/{app}_{build,run}`
- Config templates: `config/hpc/{app}_{with,no}_profiling.yaml`
- OpenAI credentials: `~/.openai_env` (source before external model runs)
