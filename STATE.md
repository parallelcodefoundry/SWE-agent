# STATE.md — Current Project State

Last updated: 2026-02-26 (session 28)

## Current Focus

**Session 28: Unified SWE-agent prompts into prompt.py, added --baseline-only flag, fixed harness bugs, analyzed completed batch results.**

## Session 28 — Changes Implemented

### Prompt Unification (main deliverable)
1. **`build_sweagent_prompts()` in prompt.py** — New function generates `system_template` + `instance_template` for SWE-agent using the same shared constants all other frameworks use. Single source of truth for all 5 frameworks.
2. **`config/hpc/llnl_base.yaml`** — New single YAML template with placeholders. Replaces 8 per-app YAML configs for SWE-agent plumbing (model, tools, env vars, demonstrations).
3. **`sweagent.py` refactored** — `generate_config()` now calls `build_sweagent_prompts()` from prompt.py and injects into `llnl_base.yaml`. Removed `REPO_CONFIG_TEMPLATES` dict. Added `_build_bundle_list()` for dynamic tool bundles.

### Harness Improvements
4. **`--baseline-only` flag** — Added to all 4 run harnesses (kripke_run, laghos_run, lulesh_run, qs_run), their config.yaml files, and prompt.py workflow. Agents can now get baseline timing without confusion from variance.
5. **Makefile edit restriction removed** — All 8 SWE-agent YAML configs changed from "Do NOT edit Makefiles" to "You CAN edit Makefile to add flags". Root cause of agent refusing to optimize build flags.
6. **qs_build flag allowlist removed** — Only dangerous flags (fno-exceptions, fno-rtti) are filtered now. Previously silently dropped flags like `-g`.

### Validation Bug Fixes
7. **`result.success = False` on early returns** — `_validate_agent_changes()` in hpc_benchmark_runner.py now sets success=False on build timeout, build failure, and run timeout. Previously laghos showed success=True despite timeout.
8. **`.gitignore` for build artifacts** — Written to workspaces after creation. Prevents SWE-agent's `git add -A` from staging 300K+ lines of build artifacts.
9. **Debug logging for unknown correctness** — Saves full run stdout/stderr when correctness is "unknown".

### Kripke-specific Fixes
10. **Timing parser regex** — Fixed column order in `parse_timing_from_output()` and `extract_scientific_values()` (was name/float/int, actual output is name/int/float).
11. **Default `--np` changed 4→1** — Multi-rank MPI hangs with OpenMPI 5.0.7 on Perlmutter.

## Completed Batch Results (Session 27-28)

| Job ID | Framework | Kripke | Laghos | Lulesh | Quicksilver |
|--------|-----------|--------|--------|--------|-------------|
| 49385453 | sweagent (vLLM) | builds, unknown | builds, timeout | builds, unknown | no build |
| 49385454 | sweagent (ext) | crash 60s | crash 27s | builds, unknown | crash 31s |
| 49385456 | openhands | builds, unknown | builds, timeout | builds, unknown | **passed 1.00x** |
| 49385461 | claude | builds, unknown | builds, timeout | builds, unknown | **passed 1.03x** |
| 49387755 | codex | builds, unknown | builds, timeout | builds, unknown | **passed 1.06x** |
| 49387756 | opencode | builds, unknown | builds, timeout | builds, unknown | passed 0.92x |

**Key patterns**: All agents produce `patch=0` (zero source changes). Quicksilver is only app working E2E. Kripke/Lulesh fail on correctness parsing (regex bug, now fixed). Laghos always times out at 600s.

## Previous Sessions

- **Session 27** (2026-02-25): Bug fixes (6), timeout tuning (3), first production vLLM runs
- **Session 26** (2026-02-25): Prompt redesign, --build-mode flag, harness pivot, Kripke correctness
- **Session 25** (2026-02-26): Analyzed benchmark results, fixed MPICH_DIR, Claude argparse, Laghos g++-12
- **Session 24** (2026-02-25): All infra fixes committed. 9 benchmark jobs submitted.

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `d749ac9c` — WIP: Session 28 — unified SWE-agent prompts, --baseline-only, harness fixes
- **Working tree**: clean (STATE.md pending)
- **Ahead of origin/dev**: 14 commits (not yet pushed)

## Open Issues / TODOs

### Infrastructure — Fixed this session
- [x] Unified SWE-agent prompts into prompt.py
- [x] Added --baseline-only flag to all run harnesses
- [x] Removed Makefile edit restriction from SWE-agent configs
- [x] Removed qs_build flag allowlist
- [x] Fixed validation success flag on early returns
- [x] Added .gitignore for build artifacts
- [x] Fixed kripke_run timing parser regex
- [x] Fixed kripke_run default np 4→1

### Infrastructure — Still open
- [ ] **Harness runtime characterization** — Need to test Kripke/Laghos/Lulesh with various parameters on compute node to find configs completing in 10-60s with <2% variance (like the Quicksilver Coral2_P2_1 table). See HANDOFF.md for full plan.
- [ ] **Laghos validation timeout** — 600s not enough for laghos_run baseline+modified. Need shorter problem or higher timeout.
- [ ] **Lulesh validation crash** — Modified version segfaults; harness outputs "ERROR" not "CORRECTNESS: FAILED".
- [ ] **Old per-app YAML configs** — `config/hpc/{app}_{profiling}.yaml` still exist but are no longer used by sweagent.py. Can be removed or kept as reference.
- [ ] **GPA baseline build failures** — backprop/lavaMD missing C headers; exatensor/srad driver issue
- [ ] **GPA BFS/Gaussian correctness** — Float precision from `__ldg()` causes mismatches

### Longer-term
- [ ] **Push dev to origin** — 14 commits ready
- [ ] **Full production benchmark** — 5 frameworks × 4 apps with all fixes applied
- [ ] **Consider stronger model** — gpt-oss-120b via vLLM is slow; agents need better models to actually produce optimizations
- [ ] **Expert commit comparison** — Move to feature/expert-commits-swefficiency branch

## Recent Decisions

- 2026-02-26 (s28): SWE-agent prompts now generated from prompt.py, not hardcoded in YAML configs
- 2026-02-26 (s28): Kripke default MPI ranks reduced to 1 (multi-rank hangs with OpenMPI 5.0.7)
- 2026-02-26 (s28): Only truly dangerous flags filtered in qs_build (removed allowlist approach)
- 2026-02-25 (s27): total_execution_timeout must be set explicitly in HPC configs
- 2026-02-25 (s27): vLLM model names must include full path (`openai/gpt-oss-120b`)

## Next Steps

1. **Characterize harness runtimes** — Run Kripke/Laghos/Lulesh with various params on compute node, build timing tables (see HANDOFF.md)
2. **Analyze batch results thoroughly** — Background agent was launched but interrupted; need to check actual agent logs for openhands/claude/codex/opencode
3. **Resubmit benchmark runs** — With all session 28 fixes (unified prompts, --baseline-only, regex fix, etc.)
4. **Fix Laghos timeout** — Either reduce problem size or increase validation timeout
5. **Fix Lulesh harness** — Output "CORRECTNESS: FAILED" on crash instead of "ERROR"
6. **Push dev to origin** — 14 commits ready
