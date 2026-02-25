# STATE.md — Current Project State

Last updated: 2026-02-25 (session 23)

## Active Experiments

Debugging infra issues from first 5-framework benchmark run (gpt-4.1-mini). Several fixes applied, rerun needed.

## Current Focus

**Debugging benchmark infra + planning next rerun.** Fixed kripke build (GCC 14 vs nvcc), GPA CUDA global override, improved validation logging. Investigated all agent failures.

## Last Session (Session 23)

Deep investigation of all LLNL benchmark failures from session 22. Fixed 3 infra bugs, analyzed agent behavior:

### Infrastructure Fixes
- **Fixed kripke_build CUDA host compiler** — nvcc requires GCC ≤13 but system default is 14.3. Added `CMAKE_CUDA_HOST_COMPILER=g++-12` to `tools/kripke_harness/bin/kripke_build`.
- **Fixed GPA CUDA global override** — `run_benchmark.sh` loaded `cudatoolkit/12.4` globally (line 464), srun inherited it even for GPA apps. Removed global load; now per-app only. Also fixed `get_module_loads()` in `base.py` to be GPA-aware (unloads cudatoolkit for GPA).
- **Improved validation build logging** — Build failures now save full stdout+stderr to `{repo}_validation_build.log` file.
- **Updated all 5 framework launchers** to pass `repo_name` to `get_module_loads()`.

### Agent Failure Analysis (LLNL gpt-4.1-mini run)

Detailed results with root causes:

| App | SWE-agent | OpenHands | Codex |
|-----|-----------|-----------|-------|
| kripke | FAIL: API error (empty tool_calls) + git submodule broken | builds=False: GCC 14 (NOW FIXED) | builds=False: GCC 14 (NOW FIXED) |
| laghos | builds=False: agent changed types incorrectly | No changes: `laghos_run` timeout (180s+120s) | No changes: explored 70+ actions but never edited |
| lulesh | builds=False: massive reformatting (+4923/-4835) | builds=False: massive reformatting (+4835/-4964) | builds=False: deleted 129 lines |
| quicksilver | **builds+correct, 0.96x** (slight regression) | No changes: `qs_run` timeout (>300s no_change) | No changes: 10s cmd timeout killed qs_run |

### Root Cause Categories
1. **Framework timeouts** — OpenHands `no_change_timeout=300s` and Codex `10s cmd timeout` kill long-running harness commands
2. **gpt-4.1-mini exploration spiral** — agents spend all tokens analyzing code without making edits
3. **Build environment** — kripke GCC 14 + nvcc incompatibility (fixed), GPA CUDA override (fixed)

## Previous Sessions

- **Session 22** (2026-02-25): Fixed logging, sbatch, vLLM, added Claude Code. First 5-fw benchmark (partial).
- **Session 21** (2026-02-17): Phase 2B complete (Goals 7-9). 37/37 regression pass.
- **Session 20** (2026-02-17): Goals 5-6, SWE-fficiency re-curation to 12 parallel instances.

## Recent Decisions

- 2026-02-25 (s23): kripke_build needs `CMAKE_CUDA_HOST_COMPILER=g++-12` for nvcc on Perlmutter
- 2026-02-25 (s23): `get_module_loads(repo_name)` API change — GPA-aware CUDA loading
- 2026-02-25 (s23): Removed global `cudatoolkit/12.4` from run_benchmark.sh Phase 1
- 2026-02-25 (s22): Use `gpt-4.1-mini` ($0.40/$1.60 per 1M tokens) for external model benchmarks
- 2026-02-25 (s22): Added Claude Code as 5th framework (Anthropic API, no vLLM needed)
- 2026-02-25 (s22): `tee` pattern for dual output (trajectory + realtime log) in framework launchers
- 2026-02-17 (s21): Total corrected to 37 instances (LLNL has 9 curated commits, not 4)

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| **5-fw LLNL gpt-4.1-mini (s22)** | 49348466-71,77 | Partial — see s23 analysis above |
| **5-fw GPA gpt-4.1-mini (s22)** | 49348467-73,78 | ALL FAILED — CUDA 12.4 vs 12.9 bug (now fixed) |
| **Goal 7: 3 agents on SWE-fficiency (s21)** | 49055388 | **Codex produced patch** — SWE-agent/OpenHands install failed in container |
| **Goal 8: 37-instance regression (s21)** | login node | **37/37 PASS** — all instances generate correctly |
| **Full 4×4 matrix (s15)** | 48889171 | **14/16 PASS** — OpenCode+OpenHands 4/4, Codex+SWE-agent 3/4 |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `0fe0fa38` (uncommitted changes from s22+s23 pending)

## Uncommitted Changes (Sessions 22+23)

### Modified (from s22 + s23 fixes)
- `batch/frameworks/base.py` — `get_module_loads(repo_name)` GPA-aware
- `batch/frameworks/claude.py` — NEW + repo_name passthrough
- `batch/frameworks/codex.py` — tee logging + repo_name passthrough
- `batch/frameworks/opencode.py` — tee logging + repo_name passthrough
- `batch/frameworks/openhands_runner.py` — modifications
- `batch/frameworks/openhands.py` — repo_name passthrough (via replace_all)
- `batch/frameworks/sweagent.py` — repo_name passthrough (via replace_all)
- `batch/frameworks/prompt.py` — modifications
- `batch/frameworks/__init__.py` — added claude
- `batch/hpc_benchmark_runner.py` — GPA error logging + validation build log + repo_name
- `batch/run_benchmark.sh` — ORIG_ARGS, SWEAGENT_ROOT, vLLM check, Kripke lock, per-app CUDA
- `tools/kripke_harness/bin/kripke_build` — CMAKE_CUDA_HOST_COMPILER=g++-12
- `scripts/setup_apps.sh`, `tools/laghos_harness/`, `tools/lulesh_harness/` — modifications

### Untracked (new files)
- `batch/frameworks/claude.py`
- `batch/run_full_matrix.sh`
- `batch/test_validation.py`

## Open Issues

### Infrastructure (to fix next)
- **OpenHands tool timeout too short** — `no_change_timeout_seconds=300` kills laghos_run/qs_run. Need ~600s.
- **Codex command timeout too short** — 10s default kills all harness commands. Need `CODEX_DEFAULT_EXEC_TIMEOUT_MS` set or patched binary.
- **Claude Code runs failed** — vLLM check was fixed but needs rerun validation.
- **SWE-agent kripke git submodule** — `blt/../.git/modules/blt` broken in workspace copy.
- **SWE-agent gpt-4.1-mini empty tool_calls** — API returns empty array, LiteLLM rejects it.

### Agent Quality (not infrastructure)
- **gpt-4.1-mini exploration spiral** — agents analyze code endlessly without making edits
- **Lulesh massive reformatting** — SWE-agent/OpenHands reformat entire files instead of optimizing
- **GPA lulesh missing source** — empty LULESH/ dir in GPA-Benchmark repo (upstream issue)

### Longer-term
- **Framework launcher code duplication** — All 5 launchers repeat `get_module_loads()` in f-strings. Consider refactoring to parent class pattern.
- **SWE-fficiency agent install** — SWE-agent/OpenHands need Python 3.10+ but containers have 3.9
- **Merge dev into local/main** — Phase 2B is complete

## Next Steps

1. **Fix framework timeouts** — OpenHands `no_change_timeout` → 600s, Codex binary/env var timeout → 600s
2. **Rerun LLNL benchmark** — with kripke fix, timeout fixes, Claude Code fix
3. **Rerun GPA benchmark** — with CUDA fix (all 16 apps should work now)
4. **Refactor framework launchers** — extract common shell preamble to base class (reduce duplication)
5. **Commit all s22+s23 fixes**
6. **Full production benchmark** — all 37 instances × 5 frameworks
