---
description: Save current work state to STATE.md before ending a session or clearing context
---

Before saving, commit any uncommitted working changes to git as a checkpoint. Use a commit message like "WIP: [description of current progress]". This ensures code state survives across sessions.

Update STATE.md with:
1. What we accomplished this session (add under "## Last Session" at the top)
2. Any new decisions made (add to "## Recent Decisions" with today's date)
3. Current experiment/benchmark status (update "## Active Experiments" table)
4. Update "## Next Steps" based on where we are
5. Any context that would be lost — file paths we discussed, specific lines changed, errors encountered, SLURM job IDs

Always write a handoff file to .planning/HANDOFF.md containing:
- What we were implementing and why
- The approach/plan chosen (so the next session doesn't re-evaluate alternatives)
- A structured goal checklist showing completion status, like:
  ```
  ## Goal Progress
  - [x] Goal 0: Commit previous changes
  - [x] Goal 1: Add --framework flag to run_benchmark.sh
  - [ ] Goal 2: Refactor hpc_benchmark_runner.py dispatch (IN PROGRESS — FrameworkRunner base class done, OpenCode subclass started)
  - [ ] Goal 3: OpenCode integration
  - [ ] Goal 4: OpenHands integration
  ```
- Which files were modified and what changes were made
- Which files the next session should read first (with line ranges if relevant)
- Any gotchas, failed approaches, or decisions the next session needs to know
- Current validation status (which checks pass, which haven't been run yet)
- **For validation examples in HANDOFF.md, always show interactive salloc commands (not sbatch)**. Interactive sessions start immediately and allow real-time monitoring.

## Update Skills

After writing STATE.md and HANDOFF.md, check if any `.claude/skills/` files need updating based on what was learned or changed this session. Common triggers:
- A bug was fixed or a workaround discovered → update the relevant skill's "Common Issues" or main content
- A tool was patched or reconfigured → update the skill to reflect current state (not the old bug)
- New build/run procedures were established → add to the relevant skill's reference docs
- A skill's description mentions a bug that's been resolved → update the description

Only update skills that are directly affected by this session's work. Don't make speculative changes.
