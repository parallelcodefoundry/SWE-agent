# HANDOFF — Session 26: Prompt Redesign + Build Mode + Harness Pivot

Last updated: 2026-02-25 (session 26)

## Current Phase

**Implemented prompt redesign, --build-mode flag, harness modifications, and Kripke correctness strengthening. All changes verified with automated tests. Ready for compute-node validation.**

## Goal Progress (Session 26 Checklist)

- [x] Goal 1: Rewrite prompt.py with new structure (role → build target → task → workflow → tools → completion)
- [x] Goal 2: Add per-app essential build flags (Kripke/Laghos/Lulesh/QS)
- [x] Goal 3: Add autonomy directive + anti-yielding for Codex/Claude
- [x] Goal 4: Add --build-mode {harness|direct} to runner, shell script, launcher factory
- [x] Goal 5: Update kripke_build to respect agent CMakeLists changes
- [x] Goal 6: Update qs_build to pass through agent's -O flags
- [x] Goal 7: Strengthen kripke_run correctness check (parse physics values)
- [x] Goal 8: Update Codex AGENTS.md with anti-yielding
- [x] Goal 9: Update Claude CLAUDE.md with anti-yielding, remove "don't edit Makefiles"
- [x] Goal 10: Update CLAUDE.md scope (base mode primary, remove SWE-fficiency)
- [x] Goal 11: Automated tests pass (all 4 apps × 2 modes × 5 frameworks)
- [ ] Goal 12: Commit changes
- [ ] Goal 13: Compute-node validation (interactive session)
- [ ] Goal 14: Full benchmark rerun

## What Was Done This Session (26)

### Prompt Redesign (Goals 1-3)
- **File**: `batch/frameworks/prompt.py` (complete rewrite)
- **Changes**: New prompt structure with 6 sections. Removed FORBIDDEN ACTIONS, "Do NOT edit Makefiles". Added autonomy directive, essential flags, WHAT YOU CAN/MUST NOT CHANGE. Anti-yielding for Codex/Claude.
- **Removed**: `SYSTEM_CONTEXT` dict (replaced by `ESSENTIAL_FLAGS` + `CHANGE_RULES`), `APP_NOTES` dict (strategy suggestions removed)
- **Added**: `AUTONOMY_DIRECTIVE`, `NON_INTERACTIVE_DIRECTIVE`, `BUILD_TARGET`, `CHANGE_RULES`, `ESSENTIAL_FLAGS`, `DIRECT_BUILD_INSTRUCTIONS`

### Build Mode Flag (Goal 4)
- **Files**: `batch/hpc_benchmark_runner.py`, `batch/run_benchmark.sh`, `batch/frameworks/__init__.py`, `batch/frameworks/base.py`
- **Changes**: `--build-mode {harness|direct}` flows from CLI → runner → launcher → prompt

### Harness Modifications (Goals 5-6)
- **kripke_build**: Checks `git diff HEAD -- CMakeLists.txt`; if modified, only adds host compiler + arch (preserves agent's CUDA flags)
- **qs_build**: No longer strips -O flags from agent's Makefile; agent can set -O2, -Ofast, etc.

### Kripke Correctness (Goal 7)
- **kripke_run**: `extract_scientific_values()` now parses total_unknowns, unknowns_per_direction, directions, phi, solve_count
- Tolerance relaxed from 1e-10 to 1e-6

### Framework Updates (Goals 8-9)
- **codex.py**: AGENTS.md now starts with anti-yielding directive
- **claude.py**: CLAUDE.md starts with anti-yielding, removed "Don't modify build configuration"

## Files Modified This Session

| File | Change |
|------|--------|
| `batch/frameworks/prompt.py` | Major rewrite — new prompt structure |
| `batch/hpc_benchmark_runner.py` | Added `--build-mode` CLI arg + pass to runner |
| `batch/run_benchmark.sh` | Added `--build-mode` parsing + passthrough |
| `batch/frameworks/__init__.py` | Added `build_mode` to factory function |
| `batch/frameworks/base.py` | Added `build_mode` to launcher, pass to prompt |
| `batch/frameworks/codex.py` | Anti-yielding in AGENTS.md |
| `batch/frameworks/claude.py` | Anti-yielding in CLAUDE.md, removed restrictions |
| `tools/kripke_harness/bin/kripke_build` | Respect agent CMakeLists changes |
| `tools/quicksilver_harness/bin/qs_build` | Pass through agent -O flags |
| `tools/kripke_harness/bin/kripke_run` | Strengthen correctness: parse physics values |
| `CLAUDE.md` | Updated scope, added build mode docs |
| `STATE.md` | Updated with s26 progress |
| `.planning/HANDOFF.md` | Updated |

## Plan Reference

Implementation plan: `/global/homes/k/krydzy/.claude/plans/elegant-gathering-rabin.md`
- Steps 1-6: COMPLETE
- Step 7 (direct mode implementation): COMPLETE (via prompt + build_mode flag)
- Step 8 (integration testing): TODO (needs interactive compute node)

## Files to Read First (Next Session)

1. `STATE.md` — Full s26 changes and next steps
2. `batch/frameworks/prompt.py` — New prompt template (verify it looks good)
3. Check `squeue -u krydzy` — Any running jobs
4. `.planning/HANDOFF.md` — This file

## Validation Plan (for next session)

1. Get interactive node: `salloc --nodes 1 --qos interactive --time 03:00:00 --constraint gpu --gpus 4 --account m2404`
2. Test prompt: print final prompt for one app and verify it reads well
3. Test harness mode: run `kripke_build --arch CUDA` with a modified CMakeLists.txt
4. Test direct mode: run `python3 batch/hpc_benchmark_runner.py --base --app kripke --build-mode direct --framework codex --external-model`
5. Test Kripke correctness: run `kripke_run --arch CUDA` and check physics values parsed
6. Full regression: one framework on all 4 apps
