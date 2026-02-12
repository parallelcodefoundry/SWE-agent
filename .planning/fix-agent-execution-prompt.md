# Fix Agent Execution Issues

```
/load-state

Load skills: perlmutter, codex-cli, openhands, opencode, quicksilver, lulesh

Phase 1 framework integration works (all 4 frameworks launch and connect to API), but
deeper analysis shows no framework produced actual optimizations. There are 2 high-priority
tool execution bugs and 1 prompt issue to fix. Details in STATE.md "Agent Execution Quality"
and HANDOFF.md "Agent Execution Quality Issues".

GOALS (in priority order):

0. Create feature branch `fix-agent-execution` off `local`.

1. Fix Codex `qs_run` silent output (HIGH): Agent built successfully but all 6 qs_run
   calls returned empty output. Diagnose whether Codex exec swallows harness stdout.
   Start by reading the trajectory, then the harness script, then codex.py launcher.

2. Fix OpenCode environment access (HIGH): Agent got "invalid options in the ruleset
   configurations" on first qs_build call. Diagnose sandbox/PATH/config issues.
   Start by reading the trajectory, then opencode.py launcher and its config generation.

3. Fix OpenHands build breakage (MEDIUM): Agent deleted Makefiles and broke lulesh_build.
   Add prompt guardrails in base.py get_prompt() forbidding Makefile/build config deletion.

VALIDATION:
- Test each fix with interactive allocations (salloc -- CMD pattern, see HANDOFF.md)
- Codex: qs_run output appears in trajectory with performance numbers
- OpenCode: agent can at least call qs_build and qs_run successfully
- OpenHands: agent does not delete build config files
- Existing SWE-agent path still works unchanged

CONSTRAINTS:
- Use interactive SLURM allocations, not batch jobs.
- Commit working changes as checkpoints after each fix.
- If approaching context limits, commit all changes and run /save-state, then stop.

Start by reading the trajectories for the failed runs (paths in HANDOFF.md).
```
