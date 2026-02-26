# HANDOFF — Session 29: Harness Bug Fixes + gpt-4o-mini Benchmark Runs

Last updated: 2026-02-26 (session 29)

## Current Phase

**Fixed all harness bugs found by code review, updated runtime defaults from A100 characterization, submitted 5 batch jobs (4 frameworks × gpt-4o-mini + Claude Code × claude-opus-4-6). Jobs are queued and should complete within ~4 hours.**

## Goal Progress (Session 29 Checklist)

- [x] Goal 1: Load state, check running jobs
- [x] Goal 2: Launch explore agent to analyze batch results from sessions 27-28
- [x] Goal 3: Launch code review agent on session 28 commits
- [x] Goal 4: Launch perlmutter agents for runtime characterization (Kripke, Lulesh, Laghos)
- [x] Goal 5: Fix kripke_run timing regex (critical — completely broken)
- [x] Goal 6: Add CORRECTNESS: FAILED output to all 4 run harnesses
- [x] Goal 7: Fix fallback paths (qs_run, qs_build, kripke_build)
- [x] Goal 8: Fix claude.py nested session (unset CLAUDECODE)
- [x] Goal 9: Remove phantom hpc_analyze from prompt.py
- [x] Goal 10: chmod 755 all harness scripts
- [x] Goal 11: Deep dive agent analysis of all framework execution logs
- [x] Goal 12: Update harness defaults from characterization data
- [x] Goal 13: Commit all changes
- [x] Goal 14: Submit 5 batch jobs (gpt-4o-mini + Claude Code)
- [ ] Goal 15: Check batch results when jobs complete (NEXT SESSION)
- [ ] Goal 16: Push dev to origin (NEXT SESSION)

## Active Batch Jobs

| Job ID | Framework | Model | Nodes | Apps |
|--------|-----------|-------|-------|------|
| 49392491 | SWE-agent | gpt-4o-mini | 4 | kripke, laghos, lulesh, quicksilver |
| 49392492 | Codex | gpt-4o-mini | 4 | kripke, laghos, lulesh, quicksilver |
| 49392493 | OpenHands | gpt-4o-mini | 4 | kripke, laghos, lulesh, quicksilver |
| 49392496 | OpenCode | gpt-4o-mini | 4 | kripke, laghos, lulesh, quicksilver |
| 49392497 | Claude Code | claude-opus-4-6 | 4 | kripke, laghos, lulesh, quicksilver |
| 49392034 | — | — | 1 | Laghos characterization (still running) |

**To check job status**: `squeue -u krydzy`
**To check results**: `ls batch_results/benchmark_*_4939249*/` (once complete)

## Commits This Session

| Commit | Description |
|--------|-------------|
| `bb7d8f3d` | Session 29: Fix harness bugs, update defaults from characterization data |

## Files Modified This Session

| File | Change |
|------|--------|
| `tools/kripke_harness/bin/kripke_run` | Timing regex fix (2 places), CORRECTNESS: FAILED, groups 32→64 |
| `tools/kripke_harness/bin/kripke_build` | Fallback path Kripke→Kripke_test |
| `tools/laghos_harness/bin/laghos_run` | CORRECTNESS: FAILED, rs=3→1, tf=0.8→0.4, np=4→1 |
| `tools/lulesh_harness/bin/lulesh_run` | CORRECTNESS: FAILED, s=30→150, i=100→5000, np=8→1 |
| `tools/quicksilver_harness/bin/qs_run` | CORRECTNESS: FAILED, fallback path fix |
| `tools/quicksilver_harness/bin/qs_build` | Fallback path fix, removed dead ignored_flags |
| `batch/frameworks/claude.py` | Unset CLAUDECODE env var |
| `batch/frameworks/prompt.py` | Removed phantom hpc_analyze tool |

## Files to Read First (Next Session)

1. `STATE.md` — Session 29 state
2. `.planning/HANDOFF.md` — This file
3. `squeue -u krydzy` — Check batch job status
4. `batch_results/benchmark_*_4939249*/run_1/*/agent.log` — Agent logs from gpt-4o-mini runs
5. `batch_results/benchmark_*_4939249*/summary.json` — Results summary

## Validation (Next Session)

Check batch results with interactive session:

```bash
salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m2404

# Check results
for dir in batch_results/benchmark_*_4939249*; do
    echo "=== $(basename $dir) ==="
    cat "$dir/summary.json" 2>/dev/null || echo "No summary yet"
    echo
done

# Check agent logs for any framework
ls batch_results/benchmark_*_49392491/run_1/*/agent.log  # SWE-agent
ls batch_results/benchmark_*_49392492/run_1/*/agent.log  # Codex
```

## Key Findings This Session

### Root Causes of Session 27-28 Failures
- **50% framework bugs**: OpenHands message format, Codex single-turn, Claude nested session, OpenCode rate limit
- **40% model weakness**: gpt-oss-120b (local vLLM) too weak — 1 turn in Codex, pathological loops in SWE-agent
- **10% infrastructure**: External vLLM model not found (404)
- **Prompts are good** — not the bottleneck

### Characterization Results
- Kripke: zones=32³, groups=64, niter=10, np=1 → 28.4s, 0.46% CV
- Lulesh: s=150, i=5000, np=1 → 23.6s, 0.28% CV
- Laghos: p1, dim=2, rs=1, tf=0.4, np=1 → ~23.8s (variance TBD from job 49392034)

## Gotchas

- Claude Code can't use gpt-4o-mini — it only supports Anthropic models (claude-opus-4-6 by default)
- Max 2 interactive SLURM jobs per user (QOS limit)
- Laghos reference value table in laghos_run has entry for (1,2,3,0.8) but NOT for new default (1,2,1,0.4) — correctness still checked via baseline comparison, not reference values
