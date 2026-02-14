# Run Full Benchmark Suite — All Frameworks × All Apps

```
/load-state

Load skills: perlmutter, codex-cli, quicksilver, kripke, laghos, lulesh

CONTEXT: All 4 framework integrations are individually validated. The Codex
timeout patch (session 14) was the last blocker. Time to run the full benchmark
suite on curated commits (9 instances: 3 kripke, 2 quicksilver, 3 laghos, 1 lulesh)
across all 4 agent frameworks (codex, sweagent, opencode, openhands) with gpt-4o-mini.

Dataset: dataset/curated_perf_commits.json (9 instances)
Each run = 1 framework × 1-4 apps × curated commits
SESSION_TIMEOUT per agent = 3600s (1 hour)
Estimated wall time per framework run: ~1-2 hours (agents run in parallel per app)

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

5. Get interactive allocation:
   salloc --nodes 1 --qos interactive --time 04:00:00 --constraint gpu --gpus 4 --account m2404
6. Run Codex on all apps (curated commits, benchmark mode):
   source ~/.openai_env && source ~/envs/sweagent/bin/activate
   INSIDE_BATCH_RUN=1 srun --exclusive --gpus 4 --ntasks 1 --cpus-per-task 64 --gpu-bind=none \
     bash -lc "source ~/.openai_env && source ~/envs/sweagent/bin/activate && \
     cd /pscratch/sd/k/krydzy/SWE-agent && \
     python -m batch.hpc_benchmark_runner --framework codex --external-model \
     --model-name openai/gpt-4o-mini \
     --output-dir /pscratch/sd/k/krydzy/SWE-agent/batch_results/full_codex"
7. Check results in batch_results/full_codex/benchmark_results.json
8. If any app fails, diagnose and fix before proceeding.

PHASE 3 — Run remaining frameworks (one at a time):

9.  Reset test repos: ./scripts/reset_test_repos.sh
10. Run SWE-agent (same pattern, --framework sweagent)
    Output: batch_results/full_sweagent/

11. Reset test repos
12. Run OpenCode (--framework opencode)
    Output: batch_results/full_opencode/
    WATCH FOR: non-zero exit on normal completion

13. Reset test repos
14. Run OpenHands (--framework openhands)
    Output: batch_results/full_openhands/
    WATCH FOR: Makefile deletion guardrail issues

NOTE: Always allocate the max 4 hours for interactive QOS — just end early when done.
Reset test repos between EVERY framework run to ensure clean state.

PHASE 4 — Analyze results:

15. Compare benchmark_results.json across all 4 framework runs
16. For each instance: did the agent produce a patch? Did it improve performance?
17. Create a summary table: framework × app × instance → success/fail/speedup

AFTER EACH FRAMEWORK COMPLETES: check results, note any issues.
AFTER ALL 4 COMPLETE: create comparison report, commit results, /save-state
```
