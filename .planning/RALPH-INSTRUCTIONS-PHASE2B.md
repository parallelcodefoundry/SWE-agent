# Ralph Loop Instructions — Phase 2B: Validation Sprint

## First Steps

1. Run /load-state
2. Read .planning/PHASE2B-GOALS.md for the goal checklist and design decisions
3. Read the skill files listed in the goals before starting unfamiliar work

## Context

Phase 2 built GPA-Benchmark and SWE-fficiency integrations on the `benchmark-expansion` branch. All code is committed but UNTESTED with real agents. Phase 2B validates everything works end-to-end, including profiling tools on GPA benchmarks.

**GPA-Benchmark** at `/pscratch/sd/k/krydzy/GPA-Benchmark/` — 16 active CUDA kernel benchmarks (lulesh excluded). Driver API: `run_driver(app=X, swaps_override=..., sm_version=80, nsys=True)`. Read `.claude/skills/gpa-benchmark/SKILL.md` for details.

**SWE-fficiency** at `/pscratch/sd/k/krydzy/swefficiency/` — Python performance optimization benchmark. Eval via podman containers. Inference specs at `scripts/inference/specs/`. Read `.claude/skills/swefficiency/SKILL.md` for details.

**Inference harness** (`custom.py`) renders Jinja2 templates for each framework. CRITICAL: SWE-agent template variables (`{{observation}}`, `{{working_dir}}`, etc.) must be escaped with `{% raw %}...{% endraw %}` to prevent Jinja2 from consuming them.

**Profiling tools** (`tools/hpctoolkit/`, `tools/hatchet/`, `tools/profiling/`) are GENERIC — they work on any CUDA binary or .cu file, not just LLNL apps. `compiler_analysis` is the most useful for GPA (register count, occupancy). The GPA driver also has built-in nsys/ncu profiling exposed via `run_driver(nsys=True)`.

**Benchmark runner** at `batch/hpc_benchmark_runner.py` dispatches to GPA via `_run_gpa_benchmark()` and SWE-fficiency via `_run_swefficiency_benchmark()`.

## Ralph Loop Protocol

1. Identify the NEXT uncompleted goal — the first unchecked item in .planning/PHASE2B-GOALS.md
2. Work on that goal completely
3. When the goal is done: mark it done in PHASE2B-GOALS.md, update STATE.md with what you did, commit working changes with a descriptive message, run /save-state
4. If blocked: document the blocker in STATE.md, mark goal BLOCKED, move to next. If debugging is required, load relevant skills or web search the issue.

## Rules

- **ONE goal per iteration.** Do not try to do everything at once.
- **Always run /save-state before stopping.** This is MANDATORY, even if you hit context limits or errors.
- **Read skill files before working on unfamiliar benchmarks.** Load gpa-benchmark, swefficiency, opencode, swe-agent-framework, codex-cli, openhands skills as needed.
- **Read existing code before modifying.** Understand the pattern before changing it.
- **Use perlmutter-executor agent for compute-node work.** It handles allocation, module loading, and execution.
- **Chain env setup with &&.** Shell invocations don't share env vars: `source ~/.openai_env && python3 ...`
- **Podman socket for SWE-fficiency:** Start before any eval: `podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &` and `export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock`.
- **Commit after each goal.** Checkpoint working changes before moving on.
- **Reuse existing infrastructure.** Call GPA `run_driver()` and SWE-fficiency `swefficiency eval` CLI. Do NOT rebuild their functionality.
- **If approaching context limits above 70 percent, immediately run /save-state and stop.**
- **Record timing data.** Goal 2 specifically requires recording per-instance eval times to plan the full 27.
- **Test fixes before committing.** For code goals (0, 1, 3), verify the fix works before marking done.
- **Profiling tools are your friend.** For GPA, test `compiler_analysis` on kernel files and verify hpc_profile works on built executables. Document which tools are useful for which benchmark types.
