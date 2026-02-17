# Ralph Loop Instructions — Phase 2: Benchmark Expansion

## First Steps

1. Run /load-state
2. Read .planning/PHASE2-GOALS.md for the goal checklist and design decisions
3. Read the skill files listed in the goals before starting unfamiliar work

## Context

We need to integrate GPA-Benchmark, SWE-fficiency, and the curated performance commits benchmark into our HPC agent benchmark pipeline.

GPA-Benchmark at /pscratch/sd/k/krydzy/GPA-Benchmark/ has a gpa_bench_driver Python package with a run_driver API. It handles build, run, validate, profile, and code swapping for 17 GPU kernel benchmarks. The agent gets a workspace with kernel files, edits them, and we read the modified code and pass it to run_driver with swaps_override. Read .claude/skills/gpa-benchmark/SKILL.md for full driver API details.

SWE-fficiency at /pscratch/sd/k/krydzy/swefficiency/ has a swefficiency eval CLI for evaluation and a scripts/inference/custom.py inference harness with spec-driven YAML configs. Docker-based evaluation uses podman-hpc on Perlmutter. Read .claude/skills/swefficiency/SKILL.md for reference. The inference harness README is at /pscratch/sd/k/krydzy/swefficiency/scripts/inference/README.md and the example spec is at scripts/inference/specs/cursor_cli.yaml.

Our pipeline entry point is batch/run_benchmark.sh calling batch/hpc_benchmark_runner.py. It already supports --framework sweagent/opencode/openhands/codex and --app kripke/laghos/lulesh/quicksilver. We need to add --app gpa and --app swefficiency.

The design decisions at the top of PHASE2-GOALS.md are final. Do not revisit them.

## Ralph Loop Protocol

1. Identify the NEXT uncompleted goal -- the first unchecked item in .planning/PHASE2-GOALS.md
2. Work on that goal completely
3. When the goal is done: mark it done in PHASE2-GOALS.md, update STATE.md with what you did, commit working changes with a descriptive message, run /save-state
4. If blocked: document the blocker in STATE.md, mark goal BLOCKED, move to next. If debugging is required to move on, load any necessary skills or web search the issue to try and get past the obstacle.

## Rules

- ONE goal per iteration. Do not try to do everything at once.
- Always run /save-state before stopping. This is MANDATORY, even if you hit context limits or errors.
- Read skill files before working on unfamiliar benchmarks.
- Read existing code before modifying. Understand batch/hpc_benchmark_runner.py and batch/run_benchmark.sh patterns first.
- Use compute nodes for GPU work -- delegate to perlmutter-executor agent or use salloc.
- Commit after each goal. Checkpoint working changes before moving on.
- Reuse existing infrastructure. Call into GPA-Benchmark run_driver and SWE-fficiency eval CLI and inference harness. Do NOT rebuild their functionality.
- If approaching context limits above 70 percent, immediately run /save-state and stop.
