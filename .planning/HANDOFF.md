# HANDOFF — Session 28: Unified Prompts + Harness Fixes

Last updated: 2026-02-26 (session 28)

## Current Phase

**Unified SWE-agent prompts into prompt.py (single source of truth). Fixed multiple harness bugs. All batch jobs completed but need thorough analysis. Harness runtime characterization planned but not yet executed.**

## Goal Progress (Session 28 Checklist)

- [x] Goal 1: Analyze completed sweagent batch results (trajectory analysis from pre-compaction)
- [x] Goal 2: Fix validation success flag bug in _validate_agent_changes()
- [x] Goal 3: Add .gitignore for build artifacts in workspaces
- [x] Goal 4: Add debug logging for unknown correctness
- [x] Goal 5: Remove "Do NOT edit Makefiles" from SWE-agent YAML configs (all 8)
- [x] Goal 6: Remove qs_build flag allowlist
- [x] Goal 7: Add --baseline-only flag to all 4 run harnesses + configs + prompt.py
- [x] Goal 8: Unify SWE-agent prompts into prompt.py (llnl_base.yaml + build_sweagent_prompts)
- [x] Goal 9: Commit all changes
- [ ] Goal 10: Thoroughly analyze openhands/claude/codex/opencode batch results (DEFERRED to next session)
- [ ] Goal 11: Characterize harness runtimes for Kripke/Laghos/Lulesh (DEFERRED to next session)
- [ ] Goal 12: Resubmit benchmark runs with all fixes (DEFERRED)

## Commits This Session

| Commit | Description |
|--------|-------------|
| `d749ac9c` | WIP: Session 28 — unified prompts, --baseline-only, harness fixes (21 files) |

## Deferred Task 1: Review Batch Result Analysis + Fix New Issues

A background analysis agent completed and found the following root causes (verify these next session):

**Kripke (correct=unknown, all 4 frameworks)**:
- `kripke_run` had permissions 600 (not executable!) → "Permission denied" → validation finds no CORRECTNESS output → "unknown"
- **Fix needed**: `chmod 755 tools/kripke_harness/bin/kripke_run` (NOTE: the session 28 commit may have fixed this — check)

**Laghos (correct=timeout, all 4 frameworks)**:
- Baseline Laghos itself takes >600s to run → validation times out before even getting results
- **Fix needed**: Either increase validation timeout or find a faster problem configuration (Deferred Task 2)

**Lulesh (correct=unknown, all 4 frameworks)**:
- Modified binary segfaults (signal 11) during validation
- Agents accidentally deleted old Makefiles from `cuda/build/Makefile.CRAY` etc.
- **Fix needed**: Add those paths to .gitignore or protect them; fix harness to output "CORRECTNESS: FAILED" on crash

**Quicksilver (works E2E)**:
- Only app where validation completes successfully
- OpenHands 1.00x, Claude 1.03x, Codex 1.06x, OpenCode 0.92x
- All speedups are just noise — agents made zero source changes (only .gitignore)

**All agents made zero source changes** — only .gitignore modifications. Agent durations were very short (18-77s). Need to verify whether agents even attempted to read/optimize code or just immediately stopped.

**Where to look**: `batch_results/benchmark_2026022*/run_1/*/agent.log`

## Deferred Task 2: Harness Runtime Characterization

**What**: Test Kripke, Laghos, and Lulesh with various parameter configurations on a compute node to find settings that complete in 10-60 seconds with <2% variance. Build a table like we did for Quicksilver:

```
Example         Params              Time     Metric Range        Variance
Coral2_P2_1     53K particles       ~50s     9.103e6 - 9.151e6   ~0.5% ✓✓
```

**Why**: Current harness defaults may be too slow (Laghos times out at 600s). Agents need fast iteration cycles (build → run → measure → iterate). Ideal: 10-60s per run, <2% variance.

**How (step-by-step)**:
1. Get interactive session: `salloc --nodes 1 --qos interactive --time 04:00:00 --constraint gpu --gpus 4 --account m2404`
2. Load modules: `module load python cmake openmpi/5.0.7 cudatoolkit/12.4`
3. For each app, run harness with various parameter combos using a timeout:
   ```bash
   # Kripke — vary zones, groups, niter
   timeout 120 kripke_run --arch CUDA --baseline-only --zones 16,16,16 --groups 16 --niter 5
   timeout 120 kripke_run --arch CUDA --baseline-only --zones 32,32,32 --groups 32 --niter 10
   # etc.

   # Laghos — vary problem, dim, rs, tf
   timeout 120 laghos_run --baseline-only -p 0 --dim 2 --rs 1 --tf 0.1
   timeout 120 laghos_run --baseline-only -p 1 --dim 2 --rs 2 --tf 0.4
   # etc.

   # Lulesh — vary size, iterations
   timeout 120 lulesh_run --baseline-only -s 10 -i 50
   timeout 120 lulesh_run --baseline-only -s 20 -i 100
   timeout 120 lulesh_run --baseline-only -s 30 -i 100
   # etc.
   ```
4. For configs that complete in 10-60s, run 3-5 times to measure variance
5. Build the characterization table
6. Update harness defaults if needed

**Known starting points** (from explore agent):
- Kripke: default 32³ zones/32 groups/10 iter. Quick: 16,16,16 zones
- Laghos: default p1/dim=2/rs=3/tf=0.8. Quick: p0/dim=2/rs=1
- Lulesh: default s=30/i=100. Quick: s=10

**Use 2 perlmutter-executor subagents** to parallelize testing (one for Kripke+Lulesh, one for Laghos, since Laghos has more problem types).

## Files Modified This Session

| File | Change |
|------|--------|
| `batch/frameworks/prompt.py` | +211 lines: `build_sweagent_prompts()`, per-app constants |
| `batch/frameworks/sweagent.py` | Refactored: uses prompt.py + llnl_base.yaml instead of per-app YAMLs |
| `config/hpc/llnl_base.yaml` | NEW: single YAML template with placeholders |
| `config/hpc/*_{no,with}_profiling.yaml` (8) | Makefile edit restriction removed |
| `batch/hpc_benchmark_runner.py` | 3 fixes: success flag, .gitignore, debug logging |
| `tools/kripke_harness/bin/kripke_run` | --baseline-only, regex fix, np=1 default |
| `tools/laghos_harness/bin/laghos_run` | --baseline-only |
| `tools/lulesh_harness/bin/lulesh_run` | --baseline-only |
| `tools/quicksilver_harness/bin/qs_run` | --baseline-only |
| `tools/quicksilver_harness/bin/qs_build` | Removed flag allowlist |
| `tools/*/config.yaml` (4) | baseline_only argument added |

## Files to Read First (Next Session)

1. `STATE.md` — Session 28 state
2. `.planning/HANDOFF.md` — This file
3. `squeue -u krydzy` — Check for any running jobs
4. `batch_results/benchmark_20260226_000013_49385456/run_1/*/agent.log` — Openhands agent logs (not yet analyzed)
5. `batch_results/benchmark_20260225_235903_49385461/run_1/*/agent.log` — Claude agent logs
6. `batch/frameworks/prompt.py` — The unified prompt builder (new code)
7. `batch/frameworks/sweagent.py` — Refactored launcher (new code)

## Gotchas / Notes

- The old per-app YAML configs (`config/hpc/{app}_{profiling}.yaml`) still exist but are **no longer used** by sweagent.py. They could be removed or kept as reference.
- The `--baseline-only` flag is in the run scripts and config.yamls but the **SWE-agent YAML configs still have old prompts** (since we no longer use them — prompts come from prompt.py now). The old YAMLs won't reflect the --baseline-only workflow.
- All batch runs completed with **old code** (before session 28 fixes). Results reflect pre-fix behavior.
- Kripke multi-rank MPI hangs with OpenMPI 5.0.7. Default np changed to 1. Root cause not investigated.
- A background analysis agent was launched but interrupted (agent ID: aabdf161e277b41f6). Its partial results may be in `/tmp/claude-111589/` but shouldn't be relied upon.
