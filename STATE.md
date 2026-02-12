# STATE.md — Current Project State

Last updated: 2026-02-12 (session 4)

## Active Experiments

None currently running. Previous runs completed or cancelled.

## Current Focus

Implemented 6-fix plan to fix agent build infrastructure so models focus on optimization instead of fighting builds.

## Just Completed (Session 4)

### Fix: Agent Build Infrastructure Overhaul

All 6 fixes implemented across 14 files:

| Fix | Files Changed | Description |
|-----|---------------|-------------|
| 1. Replace srun with mpirun | `tools/kripke_harness/bin/kripke_run` | Eliminates nested srun hang in batch mode. Both baseline and modified runs now use `mpirun -np N --bind-to none` |
| 2. Laghos dep symlinks | `batch/hpc_benchmark_runner.py` | `_symlink_laghos_deps()` creates mfem/hypre/metis symlinks in workspace parent so `../mfem/libmfem.a` resolves |
| 3. Execution timeouts | All 8 `config/hpc/*.yaml` | Kripke 600→900s, Laghos 150→600s, Lulesh 150→300s, QS 150→600s |
| 4. Agent instructions | All 8 `config/hpc/*.yaml` | "PRE-BUILT" baseline-first, "Do NOT edit Makefiles", clean rebuild guidance, QS CXX override note |
| 5. INSIDE_BATCH_RUN env | `batch/run_benchmark.sh` | Exported in srun bash -c block as signal for batch mode |
| 6. Pre-flight check | `batch/hpc_benchmark_runner.py` | `verify_pristine_builds()` fails fast if pristine exes missing |

Skills updated: `swe-agent-framework`, `laghos`, `quicksilver` (removed Makefile from agent-editable lists, updated srun→mpirun note)

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| GPT-4o-mini (all 4 apps) | 48730028 | Completed (agents fought builds) |
| vLLM gpt-oss-120b (3 apps) | 48730084 | Completed (agents fought builds) |
| Kripke-only base test | 48727963 | Cancelled (stuck on nested srun, now fixed) |
| Multi-node 3 apps | 48715768 | Laghos succeeded, Lulesh failed (model error), Kripke incomplete (copytree) |
| Kripke base w/ profiling | 48508352 | Produced agent patch |
| Kripke base no profiling | 48508352 | Produced agent patch |

## Uncommitted Changes

On `local` branch. All session 3 + session 4 changes uncommitted.

**Batch**: `run_benchmark.sh`, `hpc_benchmark_runner.py`
**Harnesses**: `kripke_run` (mpirun fix)
**Configs**: All 8 `config/hpc/*.yaml` (timeouts + instructions)
**Skills**: `swe-agent-framework`, `laghos`, `quicksilver` SKILL.md files

## Open Issues

- Agent sometimes switches GPU builds to OpenMP (model behavior, no fix yet)
- Hatchet "(0)" values confuse agent

## Next Steps

1. Commit all changes (session 3 + session 4)
2. Run validation benchmark: `bash batch/run_benchmark.sh --base --lulesh` to verify fixes
3. Test kripke_run interactively on compute node (verify mpirun works)
4. Run GPT-5.1: `source ~/.openai_env && bash batch/run_benchmark.sh --base --external-model --model-name gpt-5.1`
5. Analyze results across models
6. Wire in SWE-fficiency + GPA-Benchmark
