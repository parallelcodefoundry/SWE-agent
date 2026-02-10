---
description: Save current work state to STATE.md before ending a session or clearing context
---

Update STATE.md with:
1. What we accomplished this session (add under "## Last Session" at the top)
2. Any new decisions made (add to "## Recent Decisions" with today's date)
3. Current experiment/benchmark status (update "## Active Experiments" table)
4. Update "## Next Steps" based on where we are
5. Any context that would be lost — file paths we discussed, specific lines changed, errors encountered, SLURM job IDs

If we were working on a specific implementation task, also write a handoff file to .planning/HANDOFF.md containing:
- What we were implementing and why
- Which files were being modified and what changes were made
- What's left to do
- Any files the next session should read (with line ranges if relevant)
- Any gotchas or decisions the next session needs to know
