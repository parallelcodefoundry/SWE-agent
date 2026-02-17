# Validation Sprint — Prompt for New Session

Copy-paste the entire block below as one message in a fresh Claude Code session:

```
/load-state

I want to set up a Ralph loop for validating our GPA-Benchmark and SWE-fficiency integrations with all 4 agent frameworks. Phase 2 (benchmark expansion) is complete on the benchmark-expansion branch — all integration code is committed but UNTESTED with real agents. The inference specs we wrote for SWE-fficiency are untested Jinja2 templates that may have bugs.

Before we start the loop, I want you to explore the codebase and plan this out. Read the existing Ralph loop resources (.planning/RALPH-INSTRUCTIONS.md, .planning/RALPH-PROMPT-PHASE2.md, .planning/PHASE2-GOALS.md) to understand the patterns that worked in Phase 2. Then read the current integration code (batch/hpc_benchmark_runner.py, the GPA and SWE-fficiency sections) and the relevant skill files (.claude/skills/gpa-benchmark/, .claude/skills/swefficiency/) to understand what we built and what needs testing.

Here is what I am thinking for goals, but I want your feedback after you explore. Adjust, reorder, split, or merge goals as you see fit based on what you find in the code:

Goal 0: Remove lulesh from GPA-Benchmark app list. Broken upstream (empty LULESH/ dir) and redundant with our LLNL Lulesh. Skip it in the runner, update counts from 17 to 16 in docs/comments/skills.

Goal 1: Gold eval all 27 SWE-fficiency curated instances. We only tested 1 (pandas) in Phase 2. Run the gold eval (expert patch, no agent) on all 27 across the 9 repos to validate container images, workloads, and correctness tests all work. Record which pass and fail.

Goal 2: Add GPA driver as an agent-accessible harness tool. Right now GPA agents edit kernel files but cannot test their changes during the session. Integrate run_driver() as a tool agents can call for fast build/correctness/timing feedback (~10-30s per call). Design within the existing tools/*_harness/ pattern. This only applies to GPA — SWE-fficiency eval takes 30-77 min per run so in-the-loop feedback is impractical there.

Goal 3: E2E test GPA with one agent (OpenCode). Run a single easy app (gaussian) twice — once without the GPA driver tool and once with it — to validate the flow and see if the tool helps. If it works try a few more apps.

Goal 4: E2E test SWE-fficiency with one agent (OpenCode). Run a single instance from the passing set in Goal 1 (prefer a fast repo like numpy or dask). Tests the full inference spec pipeline.

Goal 5: Test remaining agents (SWE-agent, Codex, OpenHands) on GPA, with and without the driver tool. GPA apps are fast so all runs can happen in one salloc session.

Goal 6: Test remaining agents on SWE-fficiency. One instance per agent.

Goal 7: Investigate SWE-agent containerization. Early commits on our branch may have hurt containerized capabilities in favor of running locally. Explore whether its Docker/sandbox mode still works. Document findings.

Goal 8: Fix issues and final regression.

Operational notes to keep in mind: source ~/.openai_env sets API keys but env vars dont persist across Claude shell invocations so chain with &&. Podman socket needed for SWE-fficiency: podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &. Max 2 concurrent salloc sessions. Use the perlmutter-executor subagent for GPU work. Load relevant skill files for whatever benchmark or framework you are debugging.

After exploring, create the goals file and Ralph loop instructions, then generate the ralph-loop command for me to approve before we start.
```
