# STATE.md — Current Project State

Last updated: 2026-02-25 (session 24)

## Active Experiments

**10 benchmark jobs submitted** — 5 frameworks × (LLNL + GPA). All infra fixes applied. Waiting for results.

| Job ID | Framework | Apps | Nodes | Status |
|--------|-----------|------|-------|--------|
| 49366706 | Codex | LLNL (4 apps) | 4 | QUEUED |
| 49366707 | SWE-agent | LLNL (4 apps) | 4 | QUEUED |
| 49366708 | OpenCode | LLNL (4 apps) | 4 | QUEUED |
| 49366709 | OpenHands | LLNL (4 apps) | 4 | QUEUED |
| 49366710 | Claude Code | LLNL (4 apps) | 4 | QUEUED |
| 49366711 | Codex | GPA | 1 | QUEUED |
| 49366712 | SWE-agent | GPA | 1 | QUEUED |
| 49366713 | OpenCode | GPA | 1 | QUEUED |
| 49366714 | OpenHands | GPA | 1 | QUEUED |
| ~~49366715~~ | ~~Claude Code~~ | ~~GPA~~ | ~~1~~ | ~~CANCELLED per user~~ |

All use `--base` mode, `openai/gpt-4.1-mini` external model (except Claude Code which uses Anthropic API).

## Current Focus

**Session 24 complete.** All infra fixes committed and validated. Benchmark reruns submitted. Next session: check results.

## Last Session (Session 24)

### Infrastructure Fixes (this session)
- **Fixed OpenHands timeout** — `no_change_timeout_seconds` 300→600 in `openhands_runner.py:97`
- **Fixed Codex timeout** — `CODEX_DEFAULT_EXEC_TIMEOUT_MS` 300000→600000 in `codex.py:147`
- **Refactored framework launchers** — Added `get_spack_setup()` and `build_shell_preamble()` to base class. Claude/Codex/OpenCode use full preamble; OpenHands/SWE-agent use `get_spack_setup()`.
- **Fixed kripke_build redundant import** — `import shutil` inside CUDA conditional shadowed top-level import, causing `UnboundLocalError`. Removed redundant import.
- **Fixed test repo reset** — `reset_test_repo()` was dead code (never called). Added `git reset HEAD` to handle staged files, now called before workspace creation in base mode.
- **Updated `run_full_matrix.sh`** — Added 5th framework (claude), configurable model/frameworks/GPA flags.

### Validation Results
- **Kripke build with g++-12**: PASSED on compute node (job 49366003, node nid001185)
- **Claude CLI availability**: PASSED — version 2.1.58 at `~/.local/bin/claude`

### Previous Session (23) Fixes
- kripke_build: `CMAKE_CUDA_HOST_COMPILER=g++-12`
- GPA CUDA: Removed global `cudatoolkit/12.4`, per-app loading
- Validation build logging: Full stdout+stderr to file
- All 5 launchers: `repo_name` passthrough to `get_module_loads()`

## Previous Sessions

- **Session 23** (2026-02-25): Deep investigation of LLNL failures. Fixed kripke build, GPA CUDA, logging.
- **Session 22** (2026-02-25): Fixed logging, sbatch, vLLM, added Claude Code. First 5-fw benchmark (partial).
- **Session 21** (2026-02-17): Phase 2B complete (Goals 7-9). 37/37 regression pass.
- **Session 20** (2026-02-17): Goals 5-6, SWE-fficiency re-curation to 12 parallel instances.

## Recent Decisions

- 2026-02-25 (s24): Framework launchers use `build_shell_preamble()` base class method to reduce duplication
- 2026-02-25 (s24): Test repos auto-reset before base mode workspace creation
- 2026-02-25 (s24): OpenHands/Codex timeouts set to 600s/600000ms (10 min) for harness commands
- 2026-02-25 (s23): kripke_build needs `CMAKE_CUDA_HOST_COMPILER=g++-12` for nvcc on Perlmutter
- 2026-02-25 (s23): `get_module_loads(repo_name)` API change — GPA-aware CUDA loading
- 2026-02-25 (s23): Removed global `cudatoolkit/12.4` from run_benchmark.sh Phase 1
- 2026-02-25 (s22): Use `gpt-4.1-mini` ($0.40/$1.60 per 1M tokens) for external model benchmarks
- 2026-02-25 (s22): Added Claude Code as 5th framework (Anthropic API, no vLLM needed)

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| **5-fw LLNL rerun (s24)** | 49366706-10 | SUBMITTED — pending |
| **5-fw GPA rerun (s24)** | 49366711-15 | SUBMITTED — pending |
| **Kripke build validation (s24)** | 49366003 | PASSED — g++-12 fix works |
| **5-fw LLNL gpt-4.1-mini (s22)** | 49348466-71,77 | Partial — see s23 analysis |
| **5-fw GPA gpt-4.1-mini (s22)** | 49348467-73,78 | ALL FAILED — CUDA 12.4 vs 12.9 bug (now fixed) |
| **Goal 7: 3 agents on SWE-fficiency (s21)** | 49055388 | **Codex produced patch** — SWE-agent/OpenHands install failed |
| **Goal 8: 37-instance regression (s21)** | login node | **37/37 PASS** |
| **Full 4×4 matrix (s15)** | 48889171 | **14/16 PASS** |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `f7a1ec53` — Fix test repo reset

## Recent Commits (Session 24)

- `f7a1ec53` — Fix test repo reset: unstage files + call before workspace creation
- `4a9fd7ea` — Fix kripke_build redundant import + update full matrix script
- `44bf5ee2` — Fix framework timeouts + refactor launchers to use base class preamble
- `6e1c88ba` — WIP: Save sessions 22-23 — benchmark debugging + infra fixes

## Open Issues

### Infrastructure (fixed, pending rerun results)
- ~~**OpenHands tool timeout too short**~~ — FIXED s24
- ~~**Codex command timeout too short**~~ — FIXED s24
- ~~**Claude Code runs failed**~~ — FIXED s22 (vLLM skip), validated s24
- ~~**kripke_build CUDA host compiler**~~ — FIXED s23, validated s24
- ~~**GPA CUDA global override**~~ — FIXED s23, pending rerun validation
- ~~**Test repo reset dead code**~~ — FIXED s24
- **SWE-agent kripke git submodule** — `blt/../.git/modules/blt` broken in workspace copy (not fixed)
- **SWE-agent gpt-4.1-mini empty tool_calls** — API returns empty array, LiteLLM rejects it (model quirk)

### Agent Quality (not infrastructure)
- **gpt-4.1-mini exploration spiral** — agents analyze code endlessly without making edits
- **Lulesh massive reformatting** — SWE-agent/OpenHands reformat entire files instead of optimizing
- **GPA lulesh missing source** — empty LULESH/ dir in GPA-Benchmark repo (upstream issue)

### Longer-term
- ~~**Framework launcher code duplication**~~ — FIXED s24
- **SWE-fficiency agent install** — SWE-agent/OpenHands need Python 3.10+ but containers have 3.9
- **Merge dev into local/main** — Phase 2B is complete

## Next Steps

1. **Check benchmark results** — 10 jobs queued (49366706-49366715)
2. **Analyze rerun results** — Compare with s22 run to measure impact of fixes
3. **Address remaining SWE-agent issues** — git submodule, empty tool_calls
4. **Full production benchmark** — all 37 instances × 5 frameworks (if reruns look good)
5. **Merge dev → local/main** — All fixes are stable
