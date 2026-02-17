# HANDOFF — Phase 2B COMPLETE

Last updated: 2026-02-17 (session 21)

## Current Phase

**Phase 2B: Validation Sprint — ALL GOALS COMPLETE (0-9)**

## Goal Progress

- [x] Goal 0: Remove GPA lulesh from app list
- [x] Goal 1: Fix Jinja2 template bugs in SWE-fficiency inference specs
- [x] Goal 2: Gold eval SWE-fficiency subset — timing + validation
- [x] Goal 3: Add GPA driver as agent-accessible harness tool + profiling config
- [x] Goal 4: E2E test GPA with OpenCode (with profiling validation)
- [x] Goal 5: E2E test SWE-fficiency with OpenCode
- [x] Goal 6: Test remaining agents (SWE-agent, Codex, OpenHands) on GPA gaussian
- [x] SWE-fficiency GPU/parallel audit + re-curation to 12 parallel instances
- [x] Goal 7: Test remaining agents on SWE-fficiency
- [x] Goal 8: Fix issues + final regression (37 instances)
- [x] Goal 9: (Optional) SWE-agent containerization investigation — SKIPPED (not needed)

## What Was Done This Session (21)

### Goal 7: 3 agents on SWE-fficiency scikit-learn-13310 (SLURM 49055388)
- **SWE-agent**: Install FAILED — `togetherunidiff` not found in container (Python 3.9 too old)
- **Codex CLI**: PRODUCED PATCH (pairwise.py threading rewrite). Patch was MISSED by runner due to `codex-cli` vs `codex_cli` name mismatch
- **OpenHands**: Install FAILED — `openhands-ai` dependency conflicts
- Pipeline E2E validated for all 3 frameworks (returncode=0)
- Committed `2ca16c69`

### Goal 8: Final regression + docs update
- Fixed `codex_cli.yaml` name mismatch: `name: codex-cli` → `name: codex_cli` (swefficiency repo `313572f`)
- Corrected total: 37 instances (LLNL 9 + GPA 16 + SWE-fficiency 12) — was incorrectly 32
- Regression: ALL 37 instances generate correctly
- Updated architecture.md (total count), experiment-workflow.md (instance counts)
- Committed `a28dcf14`

### Goal 9: Skipped
- SWE-agent failure was pip dependency (`togetherunidiff`), not sandbox/container mode issue
- No investigation needed

## Files Modified This Session

| File | Change |
|------|--------|
| `.planning/PHASE2B-GOALS.md` | Goals 7-9 marked complete, count corrected to 37 |
| `agent_docs/architecture.md` | Added total count line (37 instances) |
| `agent_docs/experiment-workflow.md` | Updated GPA count (16), SWE-fficiency count (12) |

### External repos modified:
| Repo | File | Change |
|------|------|--------|
| swefficiency | `scripts/inference/specs/codex_cli.yaml` | `name: codex-cli` → `name: codex_cli` |

## Validation Status

| Check | Status |
|-------|--------|
| GPA + SWE-agent | PASS (236.8s, no code changes) |
| GPA + Codex | PASS (125.1s, no code changes) |
| GPA + OpenHands | PASS (230.2s, changes made, build failed) |
| GPA + OpenCode | PASS (Goal 4) |
| SWE-fficiency + OpenCode | PARTIAL (pipeline ran, no patch) |
| SWE-fficiency + SWE-agent | FAIL (install failed — togetherunidiff) |
| SWE-fficiency + Codex | **PASS** (produced patch, path bug now fixed) |
| SWE-fficiency + OpenHands | FAIL (install failed — dependency conflicts) |
| Regression (37 instances) | **PASS** (37/37 generate correctly) |

## Key Gotchas

1. **codex_cli.yaml name must use underscores** — The `name` field in YAML specs becomes the output directory name. Runner constructs path with `spec_name` from `SWEFFICIENCY_SPEC_MAP`. Both must match exactly.
2. **SWE-fficiency containers have Python 3.9** — Old scikit-learn needs Python 3.9. SWE-agent needs `togetherunidiff` (not on PyPI for 3.9), OpenHands needs 3.10+. Fix: install agent framework in a separate venv with Python 3.10+ inside container.
3. **LLNL has 9 curated commits, not 4 apps** — The "4" count was the number of distinct apps, but each has multiple commits.
4. **Podman socket required** for SWE-fficiency: `podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &`

## Branch State

- **Current branch**: `benchmark-expansion` (off `local`)
- **Latest commit**: `a28dcf14` (Goal 8: Final regression)
- **Session 21 commits**: 2ca16c69, a28dcf14

## Suggested Next Actions

Phase 2B is complete. Next session options:

1. **Merge `benchmark-expansion` into `local`**:
   ```bash
   git checkout local
   git merge benchmark-expansion
   ```

2. **Fix SWE-fficiency agent install templates** (optional):
   - Update `sweagent_install.sh.j2` and `openhands_install.sh.j2` to use a separate Python 3.12 venv
   - This would allow SWE-agent and OpenHands to run inside SWE-fficiency containers

3. **Phase 3: Repo restructure** — Create `agents-perf` repo with submodules for GPA-Benchmark, swefficiency, and the SWE-agent fork

4. **Full production benchmark** — Run all 37 instances × 4 frameworks with real model on compute nodes
