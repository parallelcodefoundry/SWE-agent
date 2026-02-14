# Run Full E2E Validation — All Frameworks × All Apps (Base Mode)

```
/load-state

Load skills: perlmutter

If a specific framework or app fails, load the relevant skill on demand:
- Framework issues: codex-cli, swe-agent-framework, opencode, openhands
- App build/run issues: quicksilver, kripke, laghos, lulesh

CONTEXT: All 4 framework integrations are individually validated on single apps.
Time to run every framework × every app combination in base mode to confirm the
full matrix works. This is NOT the curated performance commits benchmark — just
a validation that each framework can build, run, and attempt optimization on each app.

The benchmark runner (run_benchmark.sh) already supports multi-node parallel
execution. With --external-model (API key, no vLLM), it runs 1 app per node
in parallel. 4 nodes = all 4 apps simultaneously. Interactive QOS allows up
to 4 nodes — exactly what we need.

Matrix: 4 frameworks × 4 apps = 16 runs (base mode, --base flag)
Frameworks: codex, sweagent, opencode, openhands
Apps: quicksilver, kripke, laghos, lulesh (all run in parallel on 4 nodes)
Model: gpt-4o-mini via external OpenAI API (--external-model)
SESSION_TIMEOUT per agent = 3600s (1 hour)

KNOWN ISSUES (may need fixing during runs):
- OpenCode exits non-zero on normal completion → benchmark runner may mark as failed
- OpenHands still deletes some non-essential Makefiles → guardrails partial
- SWE-agent whitespace patches → agent reformats code instead of optimizing
- SWE-agent doubled path bug → workspace ends in /cuda + git diff gives cuda/src/...

PHASE 1 — Pre-flight checks:

1. Reset all test repos to clean state:
   ./scripts/reset_test_repos.sh
2. Verify API keys are set: source ~/.openai_env
3. Verify patched Codex binary still works: codex --version
4. Check no stale SLURM jobs: squeue -u krydzy

PHASE 2 — Run Codex framework first (most recently validated):

5. Get 4-node interactive allocation (max time, end early when done):
   salloc --nodes 4 --qos interactive --time 04:00:00 --constraint gpu --gpus-per-node=4 --account m2404
6. Run Codex on all 4 apps in parallel (base mode):
   source ~/.openai_env
   bash batch/run_benchmark.sh --base --framework codex --external-model --model-name openai/gpt-4o-mini
   (The runner auto-detects 4 nodes, maps 1 app per node, runs all in parallel)
7. Check results in the output dir printed by the runner (batch_results/benchmark_*/)
8. If any app fails, diagnose and fix before proceeding.

PHASE 3 — Run remaining frameworks (one at a time, same 4-node allocation):

9.  bash batch/run_benchmark.sh --base --framework sweagent --external-model --model-name openai/gpt-4o-mini

10. bash batch/run_benchmark.sh --base --framework opencode --external-model --model-name openai/gpt-4o-mini
    WATCH FOR: non-zero exit on normal completion

11. bash batch/run_benchmark.sh --base --framework openhands --external-model --model-name openai/gpt-4o-mini
    WATCH FOR: Makefile deletion guardrail issues

Always allocate the max 4 hours — end early when done.
All 4 framework runs can reuse the same salloc if time permits.
No need to reset test repos between runs — the runner rsyncs *_test/ into
isolated per-instance workspaces, so the source repos are never modified.

PHASE 4 — Analyze results:

15. Compare benchmark_results.json across all 4 framework output dirs
16. For each framework × app: did the agent produce a patch? Did it build? Did it run?
17. Create a summary table: framework × app → success/fail/patch produced

Success criteria per cell: agent launched, built the app, ran it, produced a
non-empty patch. Performance improvement is a bonus, not required for this validation.

AFTER EACH FRAMEWORK COMPLETES: check results, note any issues.
AFTER ALL 4 COMPLETE: create comparison table, commit results, /save-state
```
