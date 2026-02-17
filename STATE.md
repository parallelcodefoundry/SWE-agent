# STATE.md — Current Project State

Last updated: 2026-02-17 (session 20)

## Active Experiments

None.

## Current Focus

**Phase 2B: Validation Sprint** — Goals 0-6 complete, Goal 7 paused for SWE-fficiency re-curation (done). Next: resume Goal 7 (test 3 agents on SWE-fficiency), then Goals 8-9.

## Last Session (Session 20)

Phase 2B validation sprint continuation:

- **Goal 5 (completed)**: Fixed SWE-fficiency eval report parsing — `validation_report_*.json` format, keyed by instance_id with `perf_report`/`correctness_report`. Committed `96d4c0cf`.
- **Goal 6 (completed)**: Tested all 3 agents (SWE-agent, Codex, OpenHands) on GPA gaussian with profiling:
  - SWE-agent: Success, 236.8s, no code changes (cost limit)
  - Codex: Success, 125.1s, no code changes
  - OpenHands: Success, 230.2s, produced shared-memory optimization but build failed (extra `}` in Fan2). Full pipeline worked E2E.
  - Committed `145f3504`.
- **SWE-fficiency GPU/parallel audit**: Analyzed all 498 instances. Found 0 GPU/CUDA, 28 with parallelization/concurrency. SWE-fficiency is purely Python.
- **SWE-fficiency re-curation**: Replaced 27 general instances with 12 parallelization-focused ones (4 strict concurrency, 2 Cython prange, 6 vectorization). Committed `462ba608`.
- **SWE-fficiency inference spec fixes** (in swefficiency repo): Fixed codex_cli.yaml (new `codex exec` syntax), opencode.yaml (config content), opencode_install.sh.j2 (Node.js 22). Committed `30bc979` in swefficiency repo.

## Previous Session (Session 19)

Completed Phase 2 Goals 3-8 (GPA validation, SWE-fficiency eval pipeline, inference specs, structural validation, curated commits, docs update).

## Recent Decisions

- 2026-02-17 (s20): SWE-fficiency re-curated from 27 general → 12 parallelization-focused instances (0 GPU in dataset)
- 2026-02-17 (s20): Benchmark now has 3 optimization dimensions: GPA (GPU kernel), LLNL (HPC proxy), SWE-fficiency (Python parallel)
- 2026-02-17 (s20): Total instances: LLNL (4) + GPA (16) + SWE-fficiency (12) = 32
- 2026-02-17 (s20): Codex CLI new syntax: `codex exec --dangerously-bypass-approvals-and-sandbox` with `-c` flags
- 2026-02-16 (s19): GPA lulesh is upstream issue (empty LULESH/ dir), documented
- 2026-02-16 (s19): SWE-fficiency podman socket: `podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &`

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| **Goal 6: 3 agents on GPA gaussian (s20)** | 49050383 | **3/3 frameworks ran** — OpenHands only one to produce changes (build failed) |
| **Goal 5: SWE-fficiency OpenCode E2E (s20)** | 49047944 | **Pipeline ran** — inference executed, 0 successful (agent didn't produce patch) |
| **GPA base validation (s19)** | interactive | **16/17 PASS** — only lulesh fails (empty upstream dir) |
| **SWE-fficiency eval E2E (s19)** | interactive | **PASS** — pandas-dev__pandas-45434, 1.387x speedup |
| **Full 4×4 matrix (s15)** | 48889171 | **14/16 PASS** — OpenCode+OpenHands 4/4, Codex+SWE-agent 3/4 |

## Branch State

- **Current branch**: `benchmark-expansion` (off `local`)
- **Phase 2B commits** (session 20):
  ```
  96d4c0cf Goal 5: Fix SWE-fficiency eval report parsing + pull strategy
  145f3504 Goal 6: Test all 3 agents on GPA gaussian + SWE-fficiency GPU/parallel audit
  462ba608 Re-curate SWE-fficiency to parallelization-focused instances (12)
  ```
- **Phase 2 commits** (sessions 18-19):
  ```
  588ea4ed Add GPA-Benchmark driver integration (Phase 2, Goals 0-1)
  0c9cf511 Add GPA-Benchmark agent prompt and config (Phase 2, Goal 2)
  01d551c5 Goal 3: GPA-Benchmark validation complete (16/17 pass)
  e70edd94 Goal 4: SWE-fficiency eval pipeline verified on Perlmutter
  0e9f0ef6 Goal 5: SWE-fficiency inference specs + runner integration
  51650956 Goal 6: SWE-fficiency agent integration validated (structural)
  3bb5c3b3 Goal 7: Curated performance commits infrastructure verified
  b243537f Goal 8: Update docs and mark Phase 2 complete
  ```

## Uncommitted Changes

- `.planning/run-full-benchmark-suite.md` — deleted (stale planning file)

## Open Issues

- **New SWE-fficiency instances may need image pulls** — The 12 re-curated instances may not all have cached images. Eval pipeline should auto-pull from ghcr.io.
- **SWE-agent whitespace patches on Lulesh** — agent reformats code instead of optimizing
- **OpenHands Kripke generates huge patches** — 4.5M chars, likely build artifacts
- **GPA lulesh missing source** — empty LULESH/ dir in GPA-Benchmark repo (upstream)

## Next Steps

1. **Goal 7**: Test SWE-agent, Codex, OpenHands on SWE-fficiency (use one of the 12 new parallel instances, e.g. scikit-learn__scikit-learn-13310)
2. **Goal 8**: Fix issues, regression test all 32 instances, update docs
3. **Goal 9**: (Optional) Investigate SWE-agent containerization issues
4. **Merge `benchmark-expansion` into `local`** when Phase 2B complete
5. **Phase 3**: Repo restructure (submodules, CI/CD)
