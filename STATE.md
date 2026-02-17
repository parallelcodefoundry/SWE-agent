# STATE.md — Current Project State

Last updated: 2026-02-16 (session 16)

## Active Experiments

None. Full 4×4 matrix validation complete.

## Current Focus

**Phase 2: Benchmark Expansion** — integrating GPA-Benchmark and SWE-fficiency into the runner. Phase 1 bug fixes (Lulesh path + post-agent validation) complete and verified on compute node.

## Last Session (Session 16)

- Fixed Lulesh doubled path: removed `/cuda` from `env.repo.path` in lulesh YAML configs (kept in `LULESH_ROOT`)
- Added post-agent validation: `_validate_agent_changes()` in `hpc_benchmark_runner.py` populates `agent_builds`/`agent_correctness`/`agent_speedup`
- Smoke tested both paths on compute node (Job 49013841): no-changes skips correctly, with-changes → Build OK, Correctness: passed, Speedup: 0.94x

## Previous Session (Session 15)

### Full 4×4 Matrix Validation — COMPLETE

Ran all 4 frameworks × all 4 apps in `--base` mode using `gpt-4o-mini` via the OpenAI API. Used a single 4-node interactive allocation (Job 48889171) for ~2h48m total. Each framework ran all 4 apps in parallel (1 app per node).

#### Results Matrix

| Framework | Kripke | Laghos | Lulesh | Quicksilver | Total |
|-----------|--------|--------|--------|-------------|-------|
| **Codex** | OK (711s) | OK (221s) | **FAIL** (1582s) | OK (360s) | 3/4 |
| **SWE-agent** | OK (1474s) | OK (593s) | **FAIL** (1990s) | OK (2253s) | 3/4 |
| **OpenCode** | OK (3548s) | OK (197s) | OK (554s) | OK (881s) | **4/4** |
| **OpenHands** | OK (641s) | OK (189s) | OK (190s) | OK (2578s) | **4/4** |

**14/16 cells successful. Both failures were on Lulesh.**

#### Framework Timing

| Framework | Exit Code | Duration | Notes |
|-----------|-----------|----------|-------|
| codex | 0 | 1637s (27 min) | Fastest overall |
| sweagent | 0 | 2284s (38 min) | |
| opencode | 0 | 3631s (60 min) | Kripke took 3548s (longest single app) |
| openhands | 0 | 2606s (43 min) | |

#### Key Observations

- **OpenCode and OpenHands: 4/4 perfect** — both handle all apps including Lulesh
- **Codex and SWE-agent: both fail on Lulesh** — Codex errored after 1582s, SWE-agent produced a 1.9M char whitespace reformat
- **Laghos is the easiest** — all frameworks finish fast (189-593s), none produce patches (app is already well-optimized)
- **Kripke takes longest** — large codebase with complex CMake+RAJA build
- **SWE-agent whitespace issue confirmed** — 124K insertions, 4.8K deletions on Lulesh (known issue)
- **OpenHands Kripke**: generated 4.5M char patch (48K insertions) — likely added generated/build artifact files

#### Output Directories

| Framework | Output Dir |
|-----------|-----------|
| Codex | `batch_results/benchmark_20260213_180416_48889171/` |
| SWE-agent | `batch_results/benchmark_20260213_183138_48889171/` |
| OpenCode | `batch_results/benchmark_20260213_190947_48889171/` |
| OpenHands | `batch_results/benchmark_20260213_201023_48889171/` |

All trajectories in corresponding `trajectories/benchmark_*_48889171/` dirs.

### SLURM Job

| Job ID | Type | Nodes | Duration | Status |
|--------|------|-------|----------|--------|
| 48889171 | Interactive (salloc) | 4 (nid001181,001184-001185,001188) | 2h48m / 4h | COMPLETE |

## Recent Decisions

- 2026-02-16 (s16): Post-agent validation runs harness scripts directly (not through agent) — reuses `get_module_loads()` + `get_env_exports()` from launcher base class
- 2026-02-16 (s16): Lulesh `env.repo.path` must NOT include `/cuda` (git root ≠ source dir); `LULESH_ROOT` keeps `/cuda`
- 2026-02-16 (s16): `--model-name` alone is sufficient for external models (no `--external-model` flag needed)
- 2026-02-13 (s15): Run all 4 frameworks sequentially in a single salloc (wrapper script chains them)
- 2026-02-13 (s15): 4-node allocation for parallel per-app execution (1 app per node)
- 2026-02-13 (s15): External model (gpt-4o-mini via OpenAI API) eliminates need for vLLM node
- 2026-02-13 (s14): Default timeout changed from 10s to 300s (not just env var — the fallback itself is 300s)
- 2026-02-13 (s14): Env var name `CODEX_DEFAULT_EXEC_TIMEOUT_MS` (matches the internal constant name pattern)
- 2026-02-13 (s14): Build Codex on login node (gcc-13 available), not compute node — saves allocation time
- 2026-02-13 (s14): Rust toolchain installed at `~/.cargo/bin/` with symlinks for cc/ar/pkg-config
- 2026-02-13 (s14): Updated AGENTS.md guidance to reflect 300s default (agent no longer needs to set timeout_ms manually)
- 2026-02-12 (s13): Remove `HAVE_ASYNC_MPI` — OpenMPI 5 non-blocking collectives broken with QS
- 2026-02-12 (s13): Use temp input files for domain decomposition (QS input overrides CLI)
- 2026-02-12 (s13): Use `--oversubscribe` with mpirun (PRRTE sees only 1 slot from SLURM srun)
- 2026-02-12 (s12): Merged `fix-agent-execution` into `local` after all 3 validations passed

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| **Post-agent validation smoke test (s16)** | 49013841 | **PASS** — Both paths verified (skip + build/run/parse) |
| **Full 4×4 matrix (s15)** | 48889171 | **14/16 PASS** — OpenCode+OpenHands 4/4, Codex+SWE-agent 3/4 (Lulesh fails) |
| **Codex timeout E2E (s14)** | 48887817 | **PASS** — gpt-4o-mini built+ran+edited QS, 249.1s |
| **Codex sleep 15 test (s14)** | 48887761 | **PASS** — 15s sleep survived (would die at 10s default) |
| QS multi-GPU validation (s13) | 48820324 | PASS — 4 GPUs, 4 ranks, 700 values correct |
| E2E Codex/QS pipeline (s13) | 48820324 | PASS (infra) — pipeline works, agent unproductive (timeout) |
| Codex/QS fix validation (s12) | 48817293 | PASS — 483.8s, timeout fix works |
| OpenCode/QS fix validation (s12) | 48817295 | PASS — Permission fix works |
| OpenHands/Lulesh fix validation (s12) | 48817669 | PASS — +1/-130 lines, guardrails work |
| Codex/Quicksilver (s9) | 48811735 | PASS — 141s, agent worked |
| OpenHands/Lulesh (s9) | 48812701 | PASS — 151s, agent worked |
| OpenCode/Quicksilver (ext model) | 48809130 | PASS — framework works |

## Uncommitted Changes

Session 17 setup files (skills updates, Phase 2 goals/prompts) — to be committed.

## Open Issues

- ~~**Codex 10s shell timeout**~~ — **RESOLVED** (session 14)
- ~~**OpenCode exits non-zero on normal completion**~~ — **NOT OBSERVED** in session 15 (all 4 OpenCode instances succeeded)
- **SWE-agent whitespace patches on Lulesh** — agent reformats code instead of optimizing (1.9M char patch, 124K insertions)
- **Codex Lulesh failure** — agent errored after 1582s; produced 15K char patch but marked as failed
- **OpenHands Kripke generates huge patches** — 4.5M chars (48K insertions, 0 deletions); likely includes build artifacts
- ~~SWE-agent doubled path bug: workspace ends in `/cuda` + git diff gives `cuda/src/...`~~ — **FIXED** (session 16): removed `/cuda` from `env.repo.path` in lulesh YAMLs, kept it in `LULESH_ROOT`
- vLLM model cache incomplete — needs HF_TOKEN
- **run_benchmark.sh only supports one framework per run** — used wrapper script (`batch_results/run_full_matrix.sh`) to chain them

## Next Steps

1. ~~**E2E validation: all frameworks × all apps (base mode)**~~ — **DONE** (session 15)
2. **Curated commits benchmark** — Run the 9 curated performance commits (dataset/curated_perf_commits.json) to compare agent vs expert patches. Use same 4-node parallel setup.
3. **Phase 2: GPA-Benchmark + SWE-fficiency integration**
4. **Phase 3: Restructure repo with submodules**
5. **Investigate Lulesh failures** — Why do Codex and SWE-agent fail while OpenCode and OpenHands succeed?
