# Session Prompts

Three phases of work, each on its own feature branch off `local`.
Use the continuation prompt when a session runs long and needs to be restarted.

## Prerequisites

Session 3+4 changes already committed on `local` (commits 5ae747d7 and 75b25a11).
Framework installation happens as part of Phase 1 Goal 1.

---

## Continuation Prompt

Use this when starting a fresh session to continue interrupted work:

```
/load-state

Continue working on the current phase goals from HANDOFF.md. Resume from the first
unchecked goal. Read the files listed in HANDOFF.md, then continue implementing.
Do not re-evaluate the approach — the previous session already chose it.
```

---

## Phase 1: Integrate Other Agent Frameworks

```
/load-state

I need to integrate 3 additional LLM agent frameworks (OpenCode, OpenHands, Codex CLI)
into our existing HPC benchmark pipeline so we can run cross-framework comparisons on
the same 4 LLNL proxy app optimization tasks (Kripke, Laghos, Lulesh, Quicksilver).

CONTEXT: Our pipeline currently only supports SWE-agent. The entry point is
`batch/run_benchmark.sh` which calls `batch/hpc_benchmark_runner.py`. The runner creates
isolated workspaces, launches SWE-agent with per-app YAML configs from `config/hpc/`,
and collects results (speedup, correctness, agent patch). We need to generalize this to
support multiple frameworks while keeping the same harness tools and evaluation. This is
Phase 1 of 3.

Relevant skills: `.claude/skills/{swe-agent-framework,opencode,openhands,codex-cli}/SKILL.md`

GOALS (in priority order):

0. Create feature branch `framework-integration` off `local`.

1. Install the three frameworks on Perlmutter (see each skill file for commands):
   - OpenCode: `npm i -g opencode-ai@latest` (node via nvm)
   - OpenHands: `source ~/envs/sweagent/bin/activate && pip install openhands`
   - Codex CLI: `npm install -g @openai/codex`
   Verify each runs `--version` successfully.

2. Refactor `batch/run_benchmark.sh` to accept `--framework {sweagent,opencode,openhands,codex}`
   (default: sweagent for backwards compatibility).

3. Refactor `batch/hpc_benchmark_runner.py` to dispatch to framework-specific launch
   logic while sharing workspace setup, patch extraction, and result collection.

4. Integrate OpenCode first (closest to SWE-agent — bash/edit/read tools natively,
   `opencode run --format json` for headless mode, no Docker).

5. Integrate OpenHands second (podman-hpc on Perlmutter, headless API, CodeActAgent).

6. Integrate Codex CLI third (`codex exec` YOLO mode, vLLM `wire_api=chat`, AGENTS.md).

7. Per-framework config generation so each framework gets equivalent instructions and
   tool access as our SWE-agent YAML configs.

8. Unified result format — all frameworks output to `benchmark_results.json` with:
   instance_id, framework, success, agent_speedup, agent_correctness, file_overlap,
   patch_similarity, duration_seconds.

VALIDATION:
- `bash batch/run_benchmark.sh --help` shows --framework flag
- Dry-run each framework dispatch path to verify routing
- `batch/run_benchmark.sh --base --lulesh` (no --framework) still defaults to sweagent
- Update any affected skills in `.claude/skills/`

CONSTRAINTS:
- Patch extraction: `git diff` from workspace for all frameworks.
- External model support (`--external-model`) should work for all frameworks.
- Commit working changes as checkpoints after each major goal.
- Choose an approach and commit to it — don't revisit unless concretely blocked.
- If approaching context limits, commit all changes and run /save-state, then stop.

Start by reading `batch/hpc_benchmark_runner.py` and `batch/run_benchmark.sh`, then
enter plan mode to design the framework abstraction before implementing.
```

---

## Phase 2: Integrate Additional Benchmarks

```
/load-state

I need to integrate two additional benchmark suites into our HPC agent benchmark pipeline:
GPA-Benchmark (GPU anti-pattern kernels) and SWE-fficiency (Python optimization tasks).

CONTEXT: Our pipeline benchmarks agents on 4 LLNL proxy apps using harness tools in
`tools/*_harness/`. After Phase 1, we support multiple frameworks via `--framework`.
Now we need to expand task diversity. This is Phase 2 of 3.

Relevant skills: `.claude/skills/{gpa-benchmark,swefficiency,swe-agent-framework}/SKILL.md`

GOALS (in priority order):

0. Create feature branch `benchmark-expansion` off `local` (merge `framework-integration`
   first if Phase 1 is complete).

1. GPA-Benchmark first (native on Perlmutter, no Docker):
   a. Create `tools/gpa_harness/` following existing harness pattern
   b. Adapt code-swap format to work with git-diff patch extraction
   c. Add GPA to `batch/hpc_benchmark_runner.py` and `batch/run_benchmark.sh` (`--gpa`)
   d. Create `config/hpc/gpa_{no,with}_profiling.yaml`

2. SWE-fficiency second (needs podman-hpc for Docker containers):
   a. Create `tools/swefficiency_harness/` wrapping existing Python eval CLI
   b. Handle Docker to podman-hpc translation
   c. Add to benchmark runner dispatch
   d. Unified results combining HPC speedup with SWE-fficiency speedup ratio

VALIDATION:
- GPA: `gpa_build` + `gpa_run` on one easy kernel, verify CORRECTNESS + SPEEDUP output
- GPA: `batch/run_benchmark.sh --base --gpa` dispatches correctly
- SWE-fficiency: eval harness on one instance via podman-hpc
- Existing LLNL app benchmarks still work unchanged
- Update any affected skills in `.claude/skills/`

CONSTRAINTS:
- Commit working changes as checkpoints after each benchmark integration.
- Choose an approach and commit to it — don't revisit unless concretely blocked.
- If approaching context limits, commit all changes and run /save-state, then stop.

Start by reading an existing harness (e.g., `tools/kripke_harness/`), then enter plan
mode to design the GPA harness before implementing.
```

---

## Phase 3: Repo Restructuring

```
/load-state

I need to restructure this project from a monolithic SWE-agent fork into a clean
`agents-perf` repository where SWE-agent, other frameworks, and benchmark suites are
git submodules.

CONTEXT: The repo has SWE-agent code at root (main=upstream, local=ours), proxy app
repos as siblings, and custom infrastructure in tools/, config/, batch/, .claude/.
After Phases 1+2 we have multi-framework support and multiple benchmarks. Now we need
clean organization. This is Phase 3 of 3 — highest-risk change in the project.

GOALS:

0. Create feature branch `repo-restructure` off `local` (merge previous branches first).

1. Design new repo structure:
   - Root = `agents-perf` (batch/, tools/, config/, scripts/, dataset/)
   - `frameworks/{sweagent,openhands,opencode,codex}/` as submodules
   - `apps/{kripke,laghos,lulesh,quicksilver}/` as submodules
   - `benchmarks/{gpa-benchmark,swefficiency}/` as submodules
   - Shared deps (mfem, hypre, metis) stay as direct clones

2. Update all path references across batch scripts, harnesses, configs, skills, docs.

3. Ensure benchmark pipeline works with submodule paths.

4. Preserve git history — reorganization, not fresh start.

VALIDATION:
- `batch/run_benchmark.sh --base --lulesh` end-to-end on compute node
- `git submodule status` shows all submodules pinned correctly
- `scripts/setup_apps.sh` builds from submodule paths
- Grep all skills/agents/commands/docs for broken paths
- Update all skills, agents, commands, and docs with new paths

CONSTRAINTS:
- Submodules pin to specific commits, not branches.
- `_test/` working copies pattern must still work (rsync from submodule to workspace).
- Commit in small logical chunks — one per major move.
- If approaching context limits, commit all changes and run /save-state, then stop.

Enter plan mode first. Design the migration carefully before touching any files.
```
