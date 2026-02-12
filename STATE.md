# STATE.md — Current Project State

Last updated: 2026-02-12 (session 12)

## Active Experiments

None. All fixes validated and merged into `local`.

## Current Focus

**Ready for full benchmark suite** — All 3 agent execution fixes validated on compute nodes and merged. Pre-existing `qs_run` harness bug discovered (pristine binary MPI hang). Next: fix qs_run, then run full benchmark.

## Last Session (Session 12)

### Validated & Merged `fix-agent-execution` → `local`

Ran all 3 validation tests on compute nodes via `salloc`. Also discovered and fixed a relative-path bug in the benchmark runner.

| Validation | Job IDs | Result | Evidence |
|-----------|---------|--------|----------|
| Codex/Quicksilver timeout fix | 48817293 | **PASS** | Agent ran 483.8s. qs_run produced non-empty output ("Run timed out") with `exit_code: 1` (not null). |
| OpenCode/Quicksilver permission fix | 48817295 | **PASS** | `qs_build` succeeded via bash tool. No Zod validation errors. Tool calls work. |
| OpenHands/Lulesh guardrails | 48817669 | **PASS** | +1/-130 lines (vs pre-fix +4837/-4966). Main `cuda/Makefile` preserved. Legitimate source change made. |

### Additional Bug Found & Fixed

| Bug | Root Cause | Fix | File |
|-----|-----------|-----|------|
| Benchmark runner paths break on direct invocation | `output_dir`/`trajectory_dir` were relative; shell scripts `cd` to workspace making relative paths invalid. `run_benchmark.sh` passes absolute paths (worked), but direct `python hpc_benchmark_runner.py` uses defaults (broke). | `.resolve()` all paths + fix double "benchmark_" in trajectory dir name | `batch/hpc_benchmark_runner.py` |

### Pre-existing Bug Discovered: `qs_run` Hangs

**Root cause**: Pristine QS binary (`Quicksilver/src/qs`) is linked against MPI (`libmpi.so.40`), built by `setup_apps.sh` with MPI. But `qs_run` harness runs the binary directly as `[exe_path, '-i', input_file]` without `mpirun`. The binary hangs on `MPI_Init()`.

The `qs_build` harness builds WITHOUT MPI (single-GPU mode), so modified binaries work. Only the pristine baseline binary hangs.

**Fix options**:
1. Rebuild pristine binary without MPI (match qs_build's no-MPI build)
2. Run with `mpirun -np 1 --bind-to none` in qs_run (works for both MPI and non-MPI binaries)
3. Use `qs_build` to build the pristine binary (not just the workspace copy)

### Commits Merged to `local`

- `e12b2205` — Fix relative path bug in benchmark runner for direct invocation
- `247f65ee` — Update skills and state docs with session 11 diagnostic findings
- `88b0a398` — Add FORBIDDEN ACTIONS guardrails to all app prompts
- `2d20e83a` — Fix Codex timeout and OpenCode permission bugs

### Validation Output Locations

- Codex: `batch_results/benchmark_20260212_125227/` (trajectory: `trajectories/benchmark_20260212_125227/`)
- OpenCode: `batch_results/benchmark_20260212_125229/` (trajectory: `trajectories/benchmark_20260212_125229/`)
- OpenHands: `batch_results/benchmark_20260212_130304/` (trajectory: `trajectories/benchmark_20260212_130304/`)

## Recent Decisions

- 2026-02-12 (s12): Merged `fix-agent-execution` into `local` after all 3 validations passed
- 2026-02-12 (s12): Resolve output_dir/trajectory_dir to absolute paths (direct invocation fix)
- 2026-02-12 (s12): Fix double "benchmark_" prefix: `trajectories/{output_dir.name}` not `trajectories/benchmark_{output_dir.name}`
- 2026-02-12 (s11): Use object form `{"*": "allow"}` for OpenCode permission (not string shorthand)
- 2026-02-12 (s11): Add CODEX_TIMEOUT_GUIDANCE to prompt (model sets timeout_ms: 300000 per-command)
- 2026-02-12 (s11): Add FORBIDDEN ACTIONS section to all 4 app prompts to prevent build destruction
- 2026-02-12 (s10): Use custom Codex provider name `ext` (not `openai`) to bypass built-in provider shadow
- 2026-02-12 (s10): Merged framework-integration into local (Phase 1 complete)

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| **Codex/QS fix validation (s12)** | 48817293 | **PASS** — 483.8s, timeout fix works, qs_run returns non-empty output |
| **OpenCode/QS fix validation (s12)** | 48817295 | **PASS** — Permission fix works, bash tool succeeds, no Zod errors |
| **OpenHands/Lulesh fix validation (s12)** | 48817669 | **PASS** — +1/-130 lines, guardrails dramatically reduce destruction |
| Codex/Quicksilver (session 9, final) | 48811735 | PASS — 141s, agent worked (but qs_run timeout bug) |
| OpenHands/Lulesh (session 9, final) | 48812701 | PASS — 151s, agent worked (but deleted Makefiles) |
| OpenCode/Quicksilver (ext model) | 48809130 | PASS — framework works (but permission bug blocked tools) |
| SWE-agent/Lulesh (ext model) | 48810087 | Agent worked 621s, whitespace-only changes |

## Uncommitted Changes

None. All changes committed on `local` branch.

## Open Issues

- **`qs_run` pristine binary MPI hang** — Pristine QS built with MPI, hangs without mpirun. Need to rebuild without MPI or add mpirun wrapper.
- **Codex `timeout_ms` not always set by gpt-4o-mini** — 49 of ~96 commands had `exit_code: null` (10s timeout killed them). Model doesn't reliably follow timeout guidance. Works well enough (12 commands succeeded with exit_code: 0) but not perfect.
- **OpenHands still deletes some Makefiles** — Deleted 3 non-essential build Makefiles (CRAY, OpenACC, stdpar variants). Main `cuda/Makefile` preserved. Guardrails work but aren't 100%.
- **SWE-agent whitespace patches** — agent reformats code instead of optimizing (LOW — model behavior)
- SWE-agent doubled path bug: workspace ends in `/cuda` + git diff gives `cuda/src/...` → `cuda/cuda/src/...` (pre-existing)
- vLLM model cache (`openai/gpt-oss-120b`) is incomplete — needs HF_TOKEN for full download

## Next Steps

1. **Fix `qs_run` pristine binary MPI hang** — Rebuild pristine QS without MPI or add `mpirun -np 1` wrapper
2. **Run full benchmark suite** with all 4 frameworks on all 4 apps (use `run_benchmark.sh`)
3. **Phase 2: GPA-Benchmark + SWE-fficiency integration**
4. **Phase 3: Restructure repo with submodules**
