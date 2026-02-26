# STATE.md — Current Project State

Last updated: 2026-02-26 (session 30)

## Current Focus

**Session 30: Fixed 2 critical harness bugs (Kripke regex + SWE-agent tool signatures), deep-analyzed session 29 failures, investigated Codex apply_patch issue, added gpt-5.3-codex support, resubmitted all 5 benchmark jobs.**

## Session 30 — Changes Implemented

### Bug Fixes
1. **Kripke timer regex column order** — Session 29 "fix" still had columns reversed. Confirmed from Kripke source (`Timing.cpp` line 72: `printf("%-16s %12d %12.5lf", name, count, seconds)`). Regex was matching `name float int` but actual output is `name int float`. Fixed in both `parse_timing_from_output()` and `extract_scientific_values()`.
2. **SWE-agent tool signatures missing --baseline-only** — All 4 harness `config.yaml` files had `baseline_only` as an argument but NOT in the `signature:` string. SWE-agent Pydantic validation requires all args in signature. Added `[--baseline-only]` to all 4. Also fixed `qs_run`: empty signature + dict-style argument format → list-style.

### Codex Improvements
3. **First-party model support** — Added `FIRST_PARTY_MODELS` set to `codex.py`. Models like `gpt-5.3-codex` use built-in `openai` provider (native `apply_patch` tool). External models continue using custom `ext` provider. Deduplicated config flag generation into `_build_config_flags()`.
4. **Investigated apply_patch_freeform** — `--enable apply_patch_freeform` sends `type: "custom"` tools, which only GPT-5 class models support. Causes 400 Bad Request with gpt-4o-mini. Reverted. `apply_patch` is a shell command invoked via `exec_command` — gpt-4o-mini just doesn't use it well (model limitation, not config bug).

### Prompt Improvements
5. **Baseline flag clarity** — All 4 apps now state baseline already uses `-O3`. QS specifically warns that Makefile `-g` is AMD HIP config, not used by harness.
6. **Removed optimization hints** — Don't suggest specific flags or focus areas. Let agents decide strategy independently.

### Deep Failure Analysis (Session 29 Results)
Analyzed all 4 frameworks × 4 apps using subagents on `*_agent_realtime.log` files:

**SWE-agent**: Config validation crash (Pydantic). Agent never started. All results are baseline-only.
**Codex (gpt-4o-mini)**: 3/4 BUILD FAIL. Destructive `sed` edits. Lulesh had working 1.16x speedup mid-session but then destroyed it with `sed -i 's|edgeNodes|//edgeNodes|g'`. QS succeeded (1.11x) via `-g`→`-O3` flag (but harness already uses `-O3`).
**OpenHands**: Kripke looped 53× on broken baseline parse. QS looped 11× on baseline timeout. Laghos succeeded (1.02x) with `-use_fast_math`. Lulesh destroyed by wrong `SRC_DIR` diagnosis.
**OpenCode**: Kripke replaced RAJA kernel with broken stub. Laghos single-shot success (1.04x). Lulesh regressed (0.95x). QS accidental speedup from `gpuMallocManaged`→`cudaMalloc`.

### Key Findings
- All 4 baselines already build at `-O3` — no free wins from flag changes
- QS Makefile has misleading `CXXFLAGS = -g` (AMD HIP leftover) but harness overrides with `-O3`
- Codex `apply_patch` is a shell command, not API tool — gpt-4o-mini can't use it, falls back to `sed`
- gpt-5.3-codex (first-party) gets native `apply_patch` via built-in provider
- EDQUOT disk quota killed 2 OpenCode sessions
- No agent demonstrated revert-and-try-different behavior when stuck

## Active Experiments

| Job ID | Framework | Model | Apps | Status |
|--------|-----------|-------|------|--------|
| 49405192 | SWE-agent | gpt-4o-mini | all 4 LLNL | PENDING |
| 49405194 | OpenHands | gpt-4o-mini | all 4 LLNL | PENDING |
| 49405195 | OpenCode | gpt-4o-mini | all 4 LLNL | PENDING |
| 49405196 | Claude Code | claude-opus-4-6 | all 4 LLNL | PENDING |
| 49407271 | Codex | gpt-5.3-codex | all 4 LLNL | PENDING |

## Completed Batch Results (Session 29 Runs)

| Job ID | Framework | Kripke | Laghos | Lulesh | Quicksilver |
|--------|-----------|--------|--------|--------|-------------|
| 49392491 | SWE-agent | config crash | PASSED 1.23x* | PASSED 0.95x* | PASSED 0.97x* |
| 49392492 | Codex (4o-mini) | BUILD FAIL | BUILD FAIL | BUILD FAIL | PASSED 1.11x |
| 49392493 | OpenHands | unknown (timeout 60m) | PASSED 1.02x | BUILD FAIL (312KB) | unknown (timeout 60m) |
| 49392496 | OpenCode | BUILD FAIL | PASSED 1.04x | PASSED 0.95x | PASSED 1.04x |
| 49392497 | Claude Code | CANCELLED | CANCELLED | CANCELLED | CANCELLED |

*SWE-agent results are baseline-only (agent never started due to config crash)

## Characterization Results (Session 29)

### Kripke (RECOMMENDED: zones=32³ groups=64 niter=10 np=1)
- 28.4s wall time, 0.46% CV

### Lulesh (RECOMMENDED: s=150 i=5000 np=1)
- 23.6s wall time, 0.28% CV

### Laghos (RECOMMENDED: p1 dim2 rs=1 tf=0.4 np=1)
- 23.8s wall time (Laghos characterization job timed out — variance TBD)

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `a2f136ab` — Add first-party model support to Codex launcher (gpt-5.3-codex)
- **Working tree**: clean (untracked: 5 Laghos characterization scripts in scripts/)
- **Ahead of origin/dev**: ~22 commits (not yet pushed)

## Open Issues / TODOs

### Fixed This Session (Session 30)
- [x] Kripke timer regex column order (confirmed from Timing.cpp source)
- [x] SWE-agent tool signatures missing --baseline-only
- [x] qs_run empty signature + dict-style argument
- [x] Codex first-party model support (gpt-5.3-codex)
- [x] Prompt baseline flag clarity + removed optimization hints
- [x] Deep failure analysis of all session 29 results

### Still Open
- [ ] **EDQUOT disk quota** — Killed 2 OpenCode sessions. Need to investigate workspace size.
- [ ] **Laghos characterization variance** — Job 49392034 timed out, need to rerun
- [ ] **Old per-app YAML configs** — Can remove `config/hpc/{app}_{profiling}.yaml`
- [ ] **GPA baseline build failures** — backprop/lavaMD missing C headers
- [ ] **GPA BFS/Gaussian correctness** — Float precision from `__ldg()`
- [ ] **Push dev to origin** — ~22 commits ready
- [ ] **Lulesh SRC_DIR trap** — Agents struggle with `SRC_DIR = src` vs `cuda/src/`

## Next Steps

1. Check batch job results when they complete (49405192-49407271)
2. Compare gpt-5.3-codex vs gpt-4o-mini on Codex — does native apply_patch + stronger model help?
3. Verify Kripke correctness now works (regex fix) and SWE-agent actually runs (signature fix)
4. Push dev to origin
5. Investigate EDQUOT disk quota issue

## Recent Decisions

- 2026-02-26 (s30): Kripke Timing.cpp confirmed: `printf("%-16s %12d %12.5lf", name, count, seconds)` — name, count, seconds order
- 2026-02-26 (s30): apply_patch_freeform uses type:"custom" — only GPT-5 class models, not viable for gpt-4o-mini
- 2026-02-26 (s30): First-party Codex models (gpt-5.3-codex, o3) use built-in openai provider for native features
- 2026-02-26 (s30): Don't hint optimization strategies in prompts — let agents decide independently
- 2026-02-26 (s30): All baselines already -O3 optimized — no free wins from flag changes
- 2026-02-26 (s29): Use gpt-4o-mini for external model benchmarks
- 2026-02-26 (s29): All apps default to np=1 (single GPU)
- 2026-02-26 (s29): Runtime targets ~24s wall time per harness run
