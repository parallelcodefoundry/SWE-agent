# HANDOFF — Session 23: Benchmark Debugging + Infra Fixes

Last updated: 2026-02-25 (session 23)

## Current Phase

**Debugging infra from first production benchmark.** Fixed 3 infra bugs. Next: fix timeouts, rerun.

## Goal Progress (Session 24 Checklist)

- [x] Goal 0: Investigate all LLNL failures from s22 benchmark (DONE s23)
- [x] Goal 1: Fix kripke_build GCC 14 vs nvcc (DONE s23)
- [x] Goal 2: Fix GPA CUDA global override (DONE s23)
- [x] Goal 3: Improve validation build logging (DONE s23)
- [ ] Goal 4: Fix OpenHands tool timeout (300s → 600s for harness commands)
- [ ] Goal 5: Fix Codex command timeout (10s kills harness commands)
- [ ] Goal 6: Refactor framework launchers to reduce duplication (parent class pattern)
- [ ] Goal 7: Rerun LLNL benchmark (kripke + timeout fixes)
- [ ] Goal 8: Rerun GPA benchmark (CUDA fix)
- [ ] Goal 9: Validate Claude Code on LLNL apps
- [ ] Goal 10: Commit all s22+s23+s24 changes

## What Was Done This Session (23)

### kripke_build CUDA host compiler fix
- **File**: `tools/kripke_harness/bin/kripke_build` (lines 73-76)
- **Change**: Added `CMAKE_CUDA_HOST_COMPILER=g++-12` to cmake args when `arch == 'CUDA'`
- **Why**: System GCC is 14.3, nvcc requires ≤13. Lulesh/quicksilver already handled this; kripke didn't.
- **g++-12 location**: `/usr/bin/g++-12` (confirmed on both login and compute nodes)

### GPA CUDA global override fix
- **Files**: `batch/run_benchmark.sh` (line 464), `batch/frameworks/base.py` (get_module_loads)
- **Change**: Removed global `module load cudatoolkit/12.4`. Now per-app: LLNL loads 12.4, GPA unloads it.
- **Also changed**: All 5 framework launchers (`claude.py`, `codex.py`, `opencode.py`, `openhands.py`, `sweagent.py`) to pass `repo_name` to `get_module_loads()`.

### Validation build logging
- **File**: `batch/hpc_benchmark_runner.py` (lines 661-675)
- **Change**: On build failure, saves full stdout+stderr to `{workspace.parent}/{repo}_validation_build.log`

## Agent Failure Root Causes (Detailed)

### OpenHands Timeout Issues
- `no_change_timeout_seconds=300` in OpenHands config kills commands that produce no terminal output for 5 min
- `laghos_run` and `qs_run` take 60-120s but may buffer output, causing timeout
- **Fix approach**: Increase to 600s in the OpenHands TOML config. File: check `batch/frameworks/openhands_runner.py` for where config is generated.

### Codex Command Timeout
- Codex CLI has a per-command timeout (default 10s)
- Previously patched binary at npm path; env var `CODEX_DEFAULT_EXEC_TIMEOUT_MS` overrides
- **Memory note says**: "Codex timeout patched — Binary at npm path rebuilt from `/pscratch/sd/k/krydzy/codex/`. Env var `CODEX_DEFAULT_EXEC_TIMEOUT_MS` overrides default (300s fallback). Original backed up as `.bak`."
- **Likely cause**: The env var may not be getting passed through to the compute node srun. Or the patched binary isn't in PATH on compute nodes.
- **Fix approach**: Verify `CODEX_DEFAULT_EXEC_TIMEOUT_MS=600000` (10 min in ms) is exported in codex.py's shell preamble. Load the `codex-cli` skill for details.

### SWE-agent gpt-4.1-mini API error
- `Invalid 'messages[17].tool_calls': empty array` — model returns empty tool_calls, LiteLLM rejects it
- This is a gpt-4.1-mini quirk; may need to filter empty tool_calls in SWE-agent's model handling or switch models

### Framework Launcher Refactoring (Goal 6)
- Currently: each of 5 launchers has an f-string with `{self.get_module_loads(repo_name)}` and similar patterns
- All inherit from `FrameworkLauncher` in `base.py` but duplicate the shell preamble
- **Proposed**: Add a `build_shell_preamble(repo_name, workspace)` method to base class that generates the common module loads + env exports + venv activation. Each subclass only overrides the framework-specific parts.
- **Files to read first**: `batch/frameworks/base.py`, then any one launcher (e.g., `codex.py`) to see the pattern.

## Files Modified This Session

| File | Change |
|------|--------|
| `tools/kripke_harness/bin/kripke_build` | Added CMAKE_CUDA_HOST_COMPILER=g++-12 (lines 73-76) |
| `batch/run_benchmark.sh` | Removed global cudatoolkit/12.4 load (line 464), updated echo |
| `batch/frameworks/base.py` | `get_module_loads(repo_name)` with GPA conditional |
| `batch/frameworks/claude.py` | `get_module_loads(repo_name)` |
| `batch/frameworks/codex.py` | `get_module_loads(repo_name)` |
| `batch/frameworks/opencode.py` | `get_module_loads(repo_name)` |
| `batch/frameworks/openhands.py` | `get_module_loads(repo_name)` |
| `batch/frameworks/sweagent.py` | `get_module_loads(repo_name)` |
| `batch/hpc_benchmark_runner.py` | Validation build log + repo_name passthrough |
| `STATE.md` | Updated for session 23 |
| `.planning/HANDOFF.md` | This file |

## Files to Read First (Next Session)

1. `batch/frameworks/base.py` (lines 198-210) — `get_module_loads()` method
2. `batch/frameworks/codex.py` (lines 140-170) — shell preamble with timeout env vars
3. `batch/frameworks/openhands_runner.py` — OpenHands config generation (look for `no_change_timeout`)
4. `batch/frameworks/openhands.py` (lines 55-120) — OpenHands launch command builder
5. `tools/kripke_harness/bin/kripke_build` (lines 60-80) — CUDA host compiler fix

## Validation Status

| Check | Status |
|-------|--------|
| kripke_build with g++-12 | NOT YET TESTED (need compute node) |
| GPA CUDA unload | NOT YET TESTED (need compute node) |
| Validation build logging | NOT YET TESTED |
| OpenHands timeout fix | NOT STARTED |
| Codex timeout fix | NOT STARTED |
| Claude Code LLNL | NOT STARTED |

## Validation Commands (Interactive)

```bash
# Get interactive GPU node
salloc --nodes 1 --qos interactive --time 03:00:00 --constraint gpu --gpus 4 --account m2404

# Test kripke build fix
module load openmpi/5.0.7 cudatoolkit/12.4 python
source ~/envs/sweagent/bin/activate
export KRIPKE_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Kripke_test
python tools/kripke_harness/bin/kripke_build --clean --arch CUDA

# Test GPA CUDA (should use default 12.9)
module unload cudatoolkit
python -c "from gpa_bench_driver.gpa_bench_driver import run_driver; run_driver(app='gaussian', sm_version=80)"
```

## Key Gotchas

1. **g++-12 is at `/usr/bin/g++-12`** on Perlmutter, NOT under Cray compiler paths
2. **`module unload cudatoolkit`** is safe — reverts to default CUDA 12.9 on GPU nodes
3. **`get_module_loads()` now requires `repo_name` param** — all callers updated, but any new framework launcher must pass it
4. **SWE-agent workspace copies break git submodule refs** — `blt/../.git/modules/blt` not found after rsync. Affects kripke patch extraction.
5. **gpt-4.1-mini returns empty `tool_calls` arrays** — crashes SWE-agent via LiteLLM BadRequestError
