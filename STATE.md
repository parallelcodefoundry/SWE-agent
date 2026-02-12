# STATE.md — Current Project State

Last updated: 2026-02-12 (session 13)

## Active Experiments

None. QS harness multi-GPU work complete. Codex shell timeout patch is next priority.

## Current Focus

**Codex CLI shell timeout patch** — The 10s default `DEFAULT_EXEC_COMMAND_TIMEOUT_MS` in Codex's Rust core kills all long-running commands (qs_build ~2min, qs_run ~4min). gpt-4o-mini doesn't reliably set `timeout_ms` per-command despite prompt guidance. Need to patch the Codex binary to increase the default to 300000ms.

## Last Session (Session 13)

### QS Harnesses Updated for Multi-GPU MPI+CUDA

Updated both `qs_build` and `qs_run` for multi-GPU execution on dedicated compute nodes (4 A100 GPUs per app).

| Change | File | Details |
|--------|------|---------|
| MPI+CUDA build | `tools/quicksilver_harness/bin/qs_build` | `find_mpi_flags()` via `mpicxx --showme`, nvcc flag filtering (`-pthread`→remove, `-Wl,X`→`-Xlinker X`), `-DHAVE_MPI` (no `HAVE_ASYNC_MPI`) |
| Multi-GPU run | `tools/quicksilver_harness/bin/qs_run` | `mpirun -np N --bind-to none --oversubscribe`, temp input files for domain decomp, `--np`/`--omp-threads` args |
| Pristine repo fix | `Quicksilver/` | Was on detached HEAD `f174550` — fixed to `master` (`e558e0c`). Only QS was misaligned; Kripke/Laghos/Lulesh fine. |

### Validation Results

| Test | Result | Details |
|------|--------|---------|
| qs_build MPI+CUDA | **PASS** | Builds with `-DHAVE_MPI -DHAVE_CUDA`, links against `libmpi.so.40` + `libcudart.so.12` |
| qs_run 4-GPU | **PASS** | 4 ranks, 2x2x1 decomp, 700 physics values correct, baseline 260.90s |
| E2E Codex/QS pipeline | **PASS (infra)** | Workspace isolation, config gen, Codex launch, API connection all work. Agent (gpt-4o-mini) made no changes due to 10s timeout. |

### Bugs Found & Fixed

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| `HAVE_ASYNC_MPI` crash | OpenMPI 5 `MPI_Iallreduce` fails with internal tag -33 error | Removed `HAVE_ASYNC_MPI` from `qs_build` defines |
| nvcc rejects `-pthread` | `mpicxx --showme:compile` returns `-pthread` which nvcc doesn't understand | Filter nvcc-incompatible flags in `find_mpi_flags()` |
| nvcc rejects `-Wl,-rpath` | `mpicxx --showme:link` returns `-Wl,X` format | Convert to `-Xlinker X` format |
| QS CLI `-I/-J/-K` ignored | `Parameters.cc:88` parses input file AFTER CLI, overriding domain decomp flags | `qs_run` creates temp input file with correct `xDom/yDom/zDom` |
| Pristine QS wrong commit | `git checkout f1745507` on 2026-02-04 (early manual test) | `git checkout master` in pristine |
| Module name `cuda/12.4` | Doesn't exist on Perlmutter, causes Lmod error | Use `cudatoolkit/12.4` (loaded by default on GPU nodes) |

### Commits

- `b92079e7` — WIP: QS harnesses updated for multi-GPU MPI+CUDA execution

## Recent Decisions

- 2026-02-12 (s13): Remove `HAVE_ASYNC_MPI` — OpenMPI 5 non-blocking collectives broken with QS
- 2026-02-12 (s13): Use temp input files for domain decomposition (QS input overrides CLI)
- 2026-02-12 (s13): Use `--oversubscribe` with mpirun (PRRTE sees only 1 slot from SLURM srun)
- 2026-02-12 (s13): Keep QS pristine on `master` (not `dev`) — dataset commits exist on both, but `dev` removes `MC_Particle` class (breaking refactor for agent optimization tasks)
- 2026-02-12 (s13): Next priority: Patch Codex CLI default shell timeout from 10s to 300s
- 2026-02-12 (s12): Merged `fix-agent-execution` into `local` after all 3 validations passed
- 2026-02-12 (s12): Resolve output_dir/trajectory_dir to absolute paths (direct invocation fix)
- 2026-02-12 (s11): Use object form `{"*": "allow"}` for OpenCode permission
- 2026-02-12 (s11): Add CODEX_TIMEOUT_GUIDANCE to prompt (model sets timeout_ms: 300000)
- 2026-02-12 (s11): Add FORBIDDEN ACTIONS section to all 4 app prompts
- 2026-02-12 (s10): Use custom Codex provider name `ext` (not `openai`)

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| **QS multi-GPU validation (s13)** | 48820324 | **PASS** — 4 GPUs, 4 ranks, 700 values correct |
| **E2E Codex/QS pipeline (s13)** | 48820324 | **PASS (infra)** — pipeline works, agent unproductive (timeout) |
| Codex/QS fix validation (s12) | 48817293 | PASS — 483.8s, timeout fix works |
| OpenCode/QS fix validation (s12) | 48817295 | PASS — Permission fix works |
| OpenHands/Lulesh fix validation (s12) | 48817669 | PASS — +1/-130 lines, guardrails work |
| Codex/Quicksilver (s9) | 48811735 | PASS — 141s, agent worked |
| OpenHands/Lulesh (s9) | 48812701 | PASS — 151s, agent worked |
| OpenCode/Quicksilver (ext model) | 48809130 | PASS — framework works |

## Uncommitted Changes

None. All changes committed on `local` branch.

## Open Issues

- **Codex 10s shell timeout** — `DEFAULT_EXEC_COMMAND_TIMEOUT_MS = 10_000` in `codex-rs/core/src/exec.rs:38`. gpt-4o-mini doesn't reliably set `timeout_ms`. **HIGH PRIORITY** — need to patch Codex binary.
- **OpenCode exits non-zero on normal completion** — benchmark runner marks as failed
- **OpenHands still deletes some non-essential Makefiles** — guardrails partial
- **SWE-agent whitespace patches** — agent reformats code instead of optimizing
- SWE-agent doubled path bug: workspace ends in `/cuda` + git diff gives `cuda/src/...`
- vLLM model cache incomplete — needs HF_TOKEN

## Next Steps

1. **Patch Codex CLI default shell timeout** — Change `DEFAULT_EXEC_COMMAND_TIMEOUT_MS` from 10,000 to 300,000 in Codex Rust source. Build and install patched version. (see `.planning/fix-codex-timeout.md`)
2. **Run full benchmark suite** with all 4 frameworks on all 4 apps
3. **Phase 2: GPA-Benchmark + SWE-fficiency integration**
4. **Phase 3: Restructure repo with submodules**
