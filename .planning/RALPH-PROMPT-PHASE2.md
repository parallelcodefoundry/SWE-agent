/ralph-loop

/load-state

Read the Phase 2 goals from .planning/PHASE2-GOALS.md. Then follow the Ralph loop protocol below.

CONTEXT: We need to integrate GPA-Benchmark (GPU anti-pattern kernels), SWE-fficiency (Python optimization tasks), and run the curated performance commits benchmark into our HPC agent benchmark pipeline.

Critical approach: GPA-Benchmark and SWE-fficiency are standalone projects with their own build/run/validate infrastructure. Reuse their existing drivers rather than building new harnesses from scratch. The curated commits benchmark uses our existing pipeline with --instance-id support.

GPA-Benchmark (/pscratch/sd/k/krydzy/GPA-Benchmark/): Has gpa_bench_driver Python package with run_driver() API. Handles build, run, validate, profile, and code swapping for 17 GPU kernel benchmarks. Agent gets a workspace with kernel file(s), edits them, we read the modified code and pass to run_driver(swaps_override=...). Read .claude/skills/gpa-benchmark/SKILL.md for full driver API details.

SWE-fficiency (/pscratch/sd/k/krydzy/swefficiency/): Has swefficiency eval CLI for evaluation and scripts/inference/custom.py inference harness with spec-driven YAML configs. Docker-based evaluation (podman-hpc on Perlmutter). Read .claude/skills/swefficiency/SKILL.md for reference. The inference harness README is at /pscratch/sd/k/krydzy/swefficiency/scripts/inference/README.md and the example spec is at scripts/inference/specs/cursor_cli.yaml.

Our pipeline entry point is batch/run_benchmark.sh -> batch/hpc_benchmark_runner.py. It already supports --framework {sweagent,opencode,openhands,codex} and --app {kripke,laghos,lulesh,quicksilver}. We need to add --app gpa and --app swefficiency.

Design decisions are at the top of .planning/PHASE2-GOALS.md. These are final — do not revisit them.

RALPH LOOP PROTOCOL:
1. Identify the NEXT uncompleted goal (first [ ] item in .planning/PHASE2-GOALS.md)
2. Work on that goal completely
3. When the goal is done: mark it [x] in PHASE2-GOALS.md, update STATE.md with what you did, commit working changes with a descriptive message, run /save-state
4. If blocked: document the blocker in STATE.md, mark goal [BLOCKED], move to next

RULES:
- ONE goal per iteration. Do not try to do everything at once.
- Always run /save-state before stopping. This is MANDATORY, even if you hit context limits or errors.
- Read skill files before working on unfamiliar benchmarks (.claude/skills/{gpa-benchmark,swefficiency}/SKILL.md)
- Read existing code before modifying. Understand batch/hpc_benchmark_runner.py and batch/run_benchmark.sh patterns first.
- Use compute nodes for GPU work (delegate to perlmutter-executor agent or use salloc)
- Commit after each goal. Checkpoint working changes before moving on.
- Reuse existing infrastructure. Call into GPA-Benchmark's run_driver() and SWE-fficiency's eval CLI and inference harness. Do NOT rebuild their functionality.
- If approaching context limits (>70%), immediately run /save-state and stop.

COMPLETION: Output <promise>PHASE COMPLETE</promise> ONLY when ALL goals in .planning/PHASE2-GOALS.md are marked [x].
