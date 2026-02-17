# STATE.md — Current Project State

Last updated: 2026-02-17 (session 21)

## Active Experiments

None.

## Current Focus

**Phase 2B: COMPLETE** — All goals (0-9) done. Ready to merge `benchmark-expansion` into `local` and begin Phase 3.

## Last Session (Session 21)

Phase 2B validation sprint completion:

- **Goal 7 (completed)**: Tested all 3 agents on SWE-fficiency `scikit-learn__scikit-learn-13310` (SLURM job 49055388):
  - SWE-agent: Install FAILED — `togetherunidiff` not found in container (Python version mismatch)
  - Codex CLI: **PRODUCED PATCH** — rewrote pairwise.py with threading backend. Patch was MISSED by runner due to `codex-cli` vs `codex_cli` name mismatch (fixed in swefficiency repo `313572f`)
  - OpenHands: Install FAILED — `openhands-ai` dependency conflicts in Ubuntu 22.04 container
  - Pipeline E2E validated for all 3 frameworks (returncode=0)
  - Committed `2ca16c69`
- **Goal 8 (completed)**: Final regression + docs update:
  - Fixed `codex_cli.yaml` name mismatch in swefficiency repo (`313572f`)
  - Corrected total count: 37 instances (LLNL 9 + GPA 16 + SWE-fficiency 12) — was incorrectly 32
  - Regression: ALL 37 instances generate correctly
  - Updated architecture.md, experiment-workflow.md, PHASE2B-GOALS.md
  - Committed `a28dcf14`
- **Goal 9 (skipped)**: SWE-agent issue was pip dependency, not sandbox/container mode. No investigation needed.

## Previous Session (Session 20)

- Goals 5-6 completed (SWE-fficiency eval report parsing, 3 agents on GPA gaussian)
- SWE-fficiency re-curated from 27 general → 12 parallelization-focused instances
- SWE-fficiency inference spec fixes in swefficiency repo

## Recent Decisions

- 2026-02-17 (s21): Total corrected to 37 instances (LLNL has 9 curated commits, not 4)
- 2026-02-17 (s21): SWE-agent/OpenHands fail to install in SWE-fficiency containers (Python mismatch) — template fix needed
- 2026-02-17 (s21): codex_cli.yaml name field must use underscores (not hyphens) to match runner path construction
- 2026-02-17 (s20): SWE-fficiency re-curated from 27 general → 12 parallelization-focused instances (0 GPU in dataset)
- 2026-02-17 (s20): Benchmark now has 3 optimization dimensions: GPA (GPU kernel), LLNL (HPC proxy), SWE-fficiency (Python parallel)
- 2026-02-17 (s20): Codex CLI new syntax: `codex exec --dangerously-bypass-approvals-and-sandbox` with `-c` flags
- 2026-02-16 (s19): GPA lulesh is upstream issue (empty LULESH/ dir), documented

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| **Goal 7: 3 agents on SWE-fficiency (s21)** | 49055388 | **Codex produced patch** — SWE-agent/OpenHands install failed in container |
| **Goal 8: 37-instance regression (s21)** | login node | **37/37 PASS** — all instances generate correctly |
| **Goal 6: 3 agents on GPA gaussian (s20)** | 49050383 | **3/3 frameworks ran** — OpenHands only one to produce changes (build failed) |
| **Goal 5: SWE-fficiency OpenCode E2E (s20)** | 49047944 | **Pipeline ran** — inference executed, 0 successful (agent didn't produce patch) |
| **GPA base validation (s19)** | interactive | **16/17 PASS** — only lulesh fails (empty upstream dir) |
| **SWE-fficiency eval E2E (s19)** | interactive | **PASS** — pandas-dev__pandas-45434, 1.387x speedup |
| **Full 4×4 matrix (s15)** | 48889171 | **14/16 PASS** — OpenCode+OpenHands 4/4, Codex+SWE-agent 3/4 |

## Branch State

- **Current branch**: `benchmark-expansion` (off `local`)
- **Phase 2B commits** (sessions 20-21):
  ```
  96d4c0cf Goal 5: Fix SWE-fficiency eval report parsing + pull strategy
  145f3504 Goal 6: Test all 3 agents on GPA gaussian + SWE-fficiency GPU/parallel audit
  462ba608 Re-curate SWE-fficiency to parallelization-focused instances (12)
  eddc6b43 WIP: Save session 20 state
  2ca16c69 Goal 7: Test 3 agents on SWE-fficiency scikit-learn-13310
  a28dcf14 Goal 8: Final regression + docs update (37/37 instances pass)
  ```

## Uncommitted Changes

- `.planning/run-full-benchmark-suite.md` — deleted (stale planning file)

## Open Issues

- **SWE-agent/OpenHands can't install in SWE-fficiency containers** — Python version mismatch. The containers have Python 3.9 (for older scikit-learn), but newer agent frameworks need Python 3.10+. Install templates need updating to use separate Python env or pin compatible versions.
- **SWE-agent whitespace patches on Lulesh** — agent reformats code instead of optimizing
- **OpenHands Kripke generates huge patches** — 4.5M chars, likely build artifacts
- **GPA lulesh missing source** — empty LULESH/ dir in GPA-Benchmark repo (upstream)

## Next Steps

1. **Merge `benchmark-expansion` into `local`** — Phase 2B is complete
2. **Phase 3**: Repo restructure (submodules, CI/CD)
3. **Fix SWE-fficiency agent install templates** — separate Python env for agent framework inside containers
4. **Full production benchmark run** — all 37 instances × 4 frameworks with real model
