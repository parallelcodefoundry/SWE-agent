---
description: Load project state at the start of a new session
---

Read STATE.md to understand current research state.
Read .planning/HANDOFF.md if it exists (this means we were mid-task last session).

Check if any SLURM jobs are running: squeue -u krydzy
Cross-reference running/completed jobs with the Active Experiments table in STATE.md.

If there are completed jobs, check batch_results/ for new output files since the last session.

Check recent git log (git log --oneline -10) to see what was committed, especially any WIP commits from the previous session.

Check git status for any uncommitted changes from the previous session.

Report:
1. What we were working on last session
2. Goal progress checklist from HANDOFF.md (which goals are done, which is in progress, which are pending)
3. Any running/completed SLURM jobs and their status
4. Recent commits and any uncommitted changes
5. Suggested next action (resume the in-progress goal, or start the next pending goal)

Do NOT read any source files yet — wait for my instructions on what to work on.
