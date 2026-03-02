# STATE.md — Current Project State

Last updated: 2026-03-02 (session 34)

## Last Session (Session 34)

### Fixes Implemented
1. **Codex API hostname fix** — `codex.py:36-48`: First-party models now pass `OPENAI_API_BASE` as `model_providers.openai.base_url` override. Prevents 401 from regional endpoint mismatch.
2. **Claude Code --verbose fix** — `claude.py:135`: Added `--verbose` flag to `claude -p` invocation. Required by CLI v2.1.59 when using `--output-format stream-json`.
3. **Lulesh Makefile deletion fix** — Removed 3 legacy trap files (`cuda/build/Makefile.CRAY`, `openacc/build/Makefile`, `stdpar/build/Makefile`) from both `Lulesh/` and `Lulesh_test/`. Committed proper `cuda/Makefile` (sm_80, g++-12) so it survives `git clean -fd`. Updated Lulesh SKILL.md.

### Session 33 Recap (for context)
4. **SWE-agent signature fix** — Changed `[--baseline_only]` to `[<baseline_only>]` in all 4 config.yaml files.
5. **QS harness flag passthrough** — Agent Makefile changes now respected (only CXX=nvcc enforced).
6. **Deep failure analysis** — 3 of 4 session 32 jobs were infrastructure failures (0 tokens). OpenCode was the only job that actually ran.

## Active Experiments

All session 32 jobs COMPLETED. No active experiments.

| Job ID | Framework | Model | Status | Root Cause | Kripke | Laghos | Lulesh | Quicksilver |
|--------|-----------|-------|--------|------------|--------|--------|--------|-------------|
| 49405195 | OpenCode | gpt-4o-mini | DONE | Agent capability | CRASH (SLURM) | BUILD FAIL (macro) | 3.41x FAIL correct | CRASH (120s timeout) |
| 49405196 | Claude Code | claude | DONE | **CLI flag bug** | N/C 1.02x | N/C 0.98x | N/C 0.94x | TIMEOUT |
| 49407271 | Codex | gpt-5.3-codex | DONE | **API hostname bug** | N/C 1.01x | N/C 0.99x | N/C 0.94x | TIMEOUT |
| 49410718 | SWE-agent | gpt-4o-mini | DONE | **Signature bug (FIXED)** | N/C 1.02x | N/C 1.10x | N/C 0.94x | TIMEOUT |

**N/C** = No real changes (agent never started or made no source edits). Speedups are baseline-vs-baseline noise.

## Completed Batch Results (Sessions 29+31)

| Job ID | Session | Framework | Kripke | Laghos | Lulesh | Quicksilver |
|--------|---------|-----------|--------|--------|--------|-------------|
| 49392491 | 29 | SWE-agent | N/C (crash) | N/C 1.23x* | N/C 0.95x* | N/C 0.97x* |
| 49392492 | 29 | Codex (4o-mini) | BUILD FAIL | BUILD FAIL | BUILD FAIL | 1.11x (noise) |
| 49392493 | 29 | OpenHands | N/C (timeout) | 1.02x (CMake flags) | BUILD FAIL (312KB) | N/C (timeout) |
| 49392496 | 29 | OpenCode | BUILD FAIL | 1.04x (CMake flags) | N/C 0.95x | 1.04x (cudaMalloc) |
| 49405192 | 31 | SWE-agent | N/C 0.93x | N/C 1.23x | N/C 0.95x | N/C 1.05x |
| 49405194 | 31 | OpenHands | 0.99x (bad unroll) | 1.00x (CMake flags) | BUILD FAIL | N/C timeout |

## Harness Flag Handling Audit

| Harness | Build System | Agent Flags Respected? | Status |
|---------|-------------|----------------------|--------|
| **Quicksilver** | Make | **YES** — detects agent Makefile changes, only enforces CXX=nvcc | **FIXED session 33** |
| **Kripke** | CMake | YES — detects git diff CMakeLists.txt, adapts | OK |
| **Lulesh** | Make (template) | YES — if Makefile passes validation (sm_80, SRC_DIR, g++-12) | OK |
| **Laghos** | Make | YES — no overrides at all, just `make -j8` | OK |

## Characterization Results

| App | Config | Runtime | CV | Status |
|-----|--------|---------|-----|--------|
| Kripke | zones=32³ groups=64 niter=10 np=1 | 28.4s | 0.46% | Aligned |
| Lulesh | s=150 i=5000 np=1 | 23.6s | 0.28% | Aligned |
| Laghos | p1 dim2 rs=1 tf=0.4 np=1 | 23.8s | TBD | Aligned |
| Quicksilver | Coral2_P2_1 np=4 | ~50s | 0.5% | Not updated in harness |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: pending — Session 34 fixes (Codex hostname, Claude --verbose, Lulesh Makefiles)
- **Working tree**: modified (codex.py, claude.py, lulesh SKILL.md, STATE.md, HANDOFF.md)

## Open Issues / TODOs

### All Infrastructure Fixes Complete
- [x] **Fix SWE-agent signatures** — Session 33
- [x] **Fix QS harness flag passthrough** — Session 33
- [x] **Fix Codex gpt-5.3 API hostname bug** — Session 34
- [x] **Fix Claude Code --verbose flag** — Session 34
- [x] **Fix Lulesh Makefile deletion** — Session 34
- [ ] **Resubmit benchmark runs** — All 5 fixes ready for retest

### Still Open
- [ ] **Quicksilver consistent timeout** — All frameworks timeout on QS. OpenCode's internal 120s bash timeout is too short. May need smaller problem.
- [ ] **Lulesh systematic bias** — N/C runs show ~0.94x consistently (ordering effect?)
- [ ] **Laghos timing variance** — N/C range 0.98x-1.23x is too high for reliable speedup detection
- [ ] **Laghos characterization variance** — Job timed out, need rerun for CV data
- [ ] **GPA baseline build failures** — backprop/lavaMD missing C headers
- [ ] **GPA BFS/Gaussian correctness** — Float precision from `__ldg()`

## Recent Decisions

- 2026-03-02 (s34): Codex first-party models must pass OPENAI_API_BASE as model_providers.openai.base_url — built-in provider hardcodes api.openai.com
- 2026-03-02 (s34): Claude Code CLI requires --verbose with --output-format stream-json (v2.1.59+)
- 2026-03-02 (s34): Lulesh cuda/Makefile now committed to repo — survives git clean. Legacy Makefiles removed from both pristine and test repos.
- 2026-03-02 (s33): SWE-agent signature format must use `[<arg>]` not `[--flag]` — parser only recognizes `{arg}` and `[<arg>]` patterns
- 2026-03-02 (s33): QS harness now follows Kripke pattern — detect agent Makefile changes, only enforce CXX=nvcc when modified
- 2026-03-02 (s33): OpenCode's 120s bash tool timeout is internal to the binary (not our launcher). SESSION_TIMEOUT=3600s has always been 1 hour.
- 2026-03-02 (s33): 3 of 4 session 32 jobs were infrastructure failures (0 agent tokens). Only OpenCode actually ran.
- 2026-03-02 (s33): OpenCode lulesh agent DID see correctness failure, was investigating fix when context overflowed. Harness feedback is working correctly.
- 2026-03-02 (s32): All reported "speedups" from sessions 29+31 are within measurement noise. No agent has produced a real optimization yet.
- 2026-02-26 (s31): Warmup run added to all harnesses — discarded run before timing loop absorbs CUDA cold-start
- 2026-02-26 (s31): Default validation_runs=10 in benchmark runner, default timing_runs=1 in harnesses
- 2026-02-26 (s30): All baselines already -O3 optimized

## Next Steps

1. **Resubmit benchmark runs** — All infrastructure fixes are now complete. Resubmit all 4 frameworks.
2. Address Laghos timing variance and Lulesh measurement bias
3. Investigate QS consistent timeout across all frameworks
