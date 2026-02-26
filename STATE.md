# STATE.md — Current Project State

Last updated: 2026-02-25 (session 27)

## Current Focus

**Session 27: Bug fixes, timeout tuning, and first production benchmark runs with vLLM gpt-oss-120b.**

## Session 27 — Changes Implemented

### Bug Fixes
1. **Kripke submodule symlink** (`hpc_benchmark_runner.py`) — Symlink `workspace/.git/modules` → `test_repo/.git/modules` so gitdir pointers resolve after rsync. VERIFIED working.
2. **gpt-4.1-mini empty tool_calls** (`sweagent/agent/models.py:863`) — Filter empty `tool_calls` arrays before sending to API. One-line fix: `and tool_calls`.
3. **vLLM model name mismatch** (`codex.py`, `opencode.py`) — Changed `gpt-oss-120b` → `openai/gpt-oss-120b` to match vLLM registration.
4. **rsync timeout** (`hpc_benchmark_runner.py:559`) — Bumped from 120s to 300s. Was never committed despite being in working tree.
5. **mpirun --oversubscribe** (`kripke_run`) — Added to both baseline and main run paths. Fixes MPI slot errors.
6. **Stale .pyc caches** — Cleaned multiple times; caused Claude framework argparse rejection.

### Timeout / Limit Tuning
7. **per_instance_call_limit: 50→200** (all 10 HPC YAML configs) — SWE-agent was hitting 50 API call limit before iterating on build failures.
8. **OpenHands max_iterations: 50→200** (`openhands.py`) — Same issue.
9. **total_execution_timeout: 3600** (all 10 HPC YAML configs) — SWE-agent default 1800s cumulative command time too low for HPC builds. Quicksilver agent killed at 20 API calls.

### Benchmark Runs Submitted
- **5 sbatch jobs** (vLLM gpt-oss-120b, base mode, 4 LLNL apps):
  - sweagent (49385453) — RUNNING, partial results
  - openhands (49385456) — PENDING
  - claude (49385461) — PENDING
  - codex (49387755) — PENDING (resubmitted after model name fix)
  - opencode (49387756) — PENDING (resubmitted after model name fix)
- **Interactive verification** (perlmutter-executor, gpt-4.1-mini) — running on compute node

### Earlier Completed Runs (this session, pre-fixes)
- codex sbatch (49385454) — ALL 4 FAILED: vLLM model name 404
- interactive_verify_kripke — sweagent ran 448s, build failed (gpt-4.1-mini too weak for RAJA)
- interactive_v2_kripke — rsync timeout (120s, now fixed to 300s)

## Previous Sessions

- **Session 26** (2026-02-25): Prompt redesign, --build-mode flag, harness pivot, Kripke correctness
- **Session 25** (2026-02-26): Analyzed benchmark results (6/9 jobs), fixed MPICH_DIR, Claude argparse, Laghos g++-12
- **Session 24** (2026-02-25): All infra fixes committed. 9 benchmark jobs submitted.

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `7c9bcd71` — Add total_execution_timeout: 3600
- **Working tree**: clean
- **Ahead of origin/dev**: 12 commits (not yet pushed)

## Open Issues / TODOs

### Infrastructure — Fixed this session
- [x] **SWE-agent kripke git submodule** — Fixed: symlink .git/modules
- [x] **SWE-agent gpt-4.1-mini empty tool_calls** — Fixed: filter empty arrays
- [x] **Codex/OpenCode vLLM model name** — Fixed: use `openai/gpt-oss-120b`
- [x] **rsync timeout** — Fixed: 120s → 300s
- [x] **mpirun oversubscribe** — Fixed: added flag
- [x] **Agent iteration limits** — Fixed: 50→200 calls, 1800→3600s execution

### Infrastructure — Still open
- [ ] **GPA baseline build failures** — backprop/lavaMD missing C headers; exatensor/srad driver issue
- [ ] **GPA BFS/Gaussian correctness** — Float precision from `__ldg()` causes mismatches
- [ ] **Other framework execution time limits** — OpenHands has `no_change_timeout_seconds=600`, Codex has `CODEX_DEFAULT_EXEC_TIMEOUT_MS=600000`. Check if these need bumping similar to SWE-agent's total_execution_timeout.
- [ ] **vLLM gpt-oss-120b inference speed** — ~2 min per API call observed (quicksilver). May need TP tuning, higher GPU mem util, or different model.

### Validation — In progress
- [x] **Prompt quality** — Verified: new prompt generates correctly
- [x] **Harness mode** — Verified: kripke_build succeeds, submodule symlink works
- [ ] **Direct mode** — Interactive verification queued (test 4)
- [x] **Kripke correctness** — Agent ran, validation caught bad build correctly
- [ ] **Full regression** — sbatch runs in progress

### Longer-term
- [ ] **Merge dev into local/main** — 12 commits ahead, all fixes ready
- [ ] **Full production benchmark** — 5 frameworks × 4 apps × {harness, direct} modes
- [ ] **Consider stronger model** — gpt-4.1-mini too weak for RAJA/CUDA; gpt-oss-120b slow via vLLM
- [ ] **Expert commit comparison** — Move to feature/expert-commits-swefficiency branch

## Recent Decisions

- 2026-02-25 (s27): total_execution_timeout must be set explicitly in HPC configs (SWE-agent default 1800s insufficient)
- 2026-02-25 (s27): vLLM model names must include full path (`openai/gpt-oss-120b`) to match registration
- 2026-02-25 (s27): rsync timeout for Kripke needs 300s (224MB data on loaded filesystem)

## Next Steps

1. **Check other framework timeout limits** — OpenHands no_change_timeout, Codex exec timeout, OpenCode session limits
2. **Analyze sweagent vLLM results** — Job 49385453 partial results coming in
3. **Wait for sbatch queue** — 4 jobs pending, should start as nodes free up
4. **Investigate vLLM inference speed** — Consider higher GPU mem util or different TP size
5. **Resubmit with all fixes** — Once current batch completes, resubmit with timeout fixes
6. **Push dev to origin** — 12 commits ready
