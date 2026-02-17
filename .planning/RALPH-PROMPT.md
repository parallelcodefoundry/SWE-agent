# Ralph Loop Prompt — Phase Work

Run /load-state. Read the current phase checklist from .planning/HANDOFF.md.

## Your Task
1. Identify the NEXT uncompleted goal (first [ ] item)
2. Work on that goal completely
3. When the goal is done:
   - Mark it [x] in HANDOFF.md
   - Update STATE.md with what you did
   - Run /save-state
4. If blocked: document the blocker in STATE.md, mark goal BLOCKED, move to next

## Rules
- ONE goal per iteration — don't try to do everything at once
- Always run /save-state before trying to exit
- Read skill files before working on unfamiliar apps
- Use compute nodes for GPU work (salloc if needed)
- Commit working changes before moving to next goal

## Completion
Output <promise>PHASE COMPLETE</promise> ONLY when ALL goals in the current phase checklist are marked [x].
