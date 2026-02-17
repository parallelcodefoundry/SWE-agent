# STATE.md — Current Project State

Last updated: 2026-02-16 (session 19)

## Active Experiments

None.

## Current Focus

**Phase 2: Benchmark Expansion — COMPLETE.** All 9 goals (0-8) done on `benchmark-expansion` branch. Ready to merge into `local`.

## Last Session (Session 19)

Completed remaining Phase 2 goals (3-8):

- **Goal 3**: GPA-Benchmark validation — fixed lavaMD case-sensitivity bug in GPA driver (5 locations in 2 files). 16/17 apps PASS (lulesh fails due to empty upstream LULESH/ dir).
- **Goal 4**: SWE-fficiency eval pipeline — set up venv, found 4 podman compatibility issues (oom_kill_disable, cpu cgroups, taskset parsing, tar uid/gid), fixed all. E2E test: pandas-dev__pandas-45434 → 1.387x speedup.
- **Goal 5**: SWE-fficiency inference specs — created 4 YAML specs (sweagent, opencode, codex_cli, openhands), 4 install templates, shared prompt template. Wired `--app swefficiency` into runner.
- **Goal 6**: SWE-fficiency structural validation — 27 instances generate, dispatch routes correctly, all 5 specs load.
- **Goal 7**: Curated commits — verified 9 expert commits, dataset filtering by `--app` and `--instance-id` works.
- **Goal 8**: Updated architecture.md and experiment-workflow.md. Regression test: LLNL (4) + GPA (17) + SWE-fficiency (27) = 48 instances, mixed selection works.

## Previous Session (Session 18)

- Created `benchmark-expansion` branch off `local` (Goal 0)
- GPA-Benchmark driver integration (Goals 0-1): Added `--app gpa` support, 6 new methods in `HPCBenchmarkRunner`, validated gaussian + hotspot on compute node
- GPA agent prompt and config (Goal 2): Created `gpa_{no,with}_profiling.yaml`, GPA prompt in `prompt.py`

## Recent Decisions

- 2026-02-16 (s19): GPA lulesh is an upstream issue (empty LULESH/ dir in GPA-Benchmark), not our bug — documented but not fixed
- 2026-02-16 (s19): SWE-fficiency podman socket must be started manually: `podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &`
- 2026-02-16 (s19): SWE-fficiency curated subset: 27 instances (3 per repo × 9 repos)
- 2026-02-16 (s19): Each SWE-fficiency instance takes ~77 min (includes perf benchmarks + correctness tests)
- 2026-02-16 (s18): GPA case-insensitive app name matching needed (driver lowercases but YAML has mixed case)
- 2026-02-16 (s16): Post-agent validation runs harness scripts directly (not through agent)
- 2026-02-16 (s16): Lulesh `env.repo.path` must NOT include `/cuda`
- 2026-02-13 (s15): Run all 4 frameworks sequentially in a single salloc
- 2026-02-13 (s14): Codex default timeout changed to 300s; env var `CODEX_DEFAULT_EXEC_TIMEOUT_MS`

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| **GPA base validation (s19)** | interactive | **16/17 PASS** — only lulesh fails (empty upstream dir) |
| **SWE-fficiency eval E2E (s19)** | interactive | **PASS** — pandas-dev__pandas-45434, 1.387x speedup |
| **SWE-fficiency structural validation (s19)** | N/A (local) | **PASS** — 27 instances, dispatch, spec loading |
| **Post-agent validation smoke test (s16)** | 49013841 | **PASS** — Both paths verified |
| **Full 4×4 matrix (s15)** | 48889171 | **14/16 PASS** — OpenCode+OpenHands 4/4, Codex+SWE-agent 3/4 |
| **Codex timeout E2E (s14)** | 48887817 | **PASS** — gpt-4o-mini built+ran+edited QS, 249.1s |
| QS multi-GPU validation (s13) | 48820324 | PASS — 4 GPUs, 4 ranks, 700 values correct |

## Branch State

- **Current branch**: `benchmark-expansion` (off `local`)
- **8 commits** covering Goals 0-8
- Ready to merge into `local`

### Phase 2 Commits

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

None.

## Open Issues

- **SWE-agent whitespace patches on Lulesh** — agent reformats code instead of optimizing
- **Codex Lulesh failure** — agent errored after 1582s
- **OpenHands Kripke generates huge patches** — 4.5M chars, likely build artifacts
- **GPA lulesh missing source** — empty LULESH/ dir in GPA-Benchmark repo (upstream)
- vLLM model cache incomplete — needs HF_TOKEN

## Next Steps

1. **Merge `benchmark-expansion` into `local`** — Phase 2 complete, squash or fast-forward merge
2. **Live agent E2E test** — Run one GPA app + one SWE-fficiency instance with a real LLM to validate full agent loop
3. **Curated commits benchmark** — Run the 9 expert commits across frameworks
4. **Full benchmark runs** — GPA (17 apps) + SWE-fficiency (27 instances) across all 4 frameworks
5. **Phase 3: Repo restructure** — submodules, CI/CD
