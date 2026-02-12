# Session Prompts

Three phases of work, each designed as an independent session prompt.
Use the continuation prompt when a session runs long and needs to be restarted.

## Prerequisites

Before starting Phase 1, verify:
- [ ] Session 3+4 changes committed on `local` branch (or leave for Phase 1 Goal 0)
- [ ] OpenCode installed on Perlmutter (`npm install -g @anthropics/opencode` or similar)
- [ ] OpenHands available via podman-hpc (pull container image)
- [ ] Codex CLI installed (`npm install -g @openai/codex`)
- [ ] Test repos in clean state: `./scripts/reset_test_repos.sh`

Note: Phase 1 can write dispatch logic without frameworks installed. Install them
before running validation steps.

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
Phase 1 of 3 — cross-framework comparison on existing tasks comes first, then new
benchmarks, then repo restructuring.

The relevant skills are already documented:
- `.claude/skills/swe-agent-framework/SKILL.md` — current pipeline reference
- `.claude/skills/opencode/SKILL.md` — OpenCode framework details
- `.claude/skills/openhands/SKILL.md` — OpenHands framework details
- `.claude/skills/codex-cli/SKILL.md` — Codex CLI framework details

Use the `framework-expert` agent for framework-specific questions and the
`proxy-app-expert` agent for harness integration questions.

GOALS (in priority order):

0. Commit all uncommitted session 3+4 changes on the `local` branch before starting
   new work. These are the build infrastructure fixes from the previous session.

1. Refactor `batch/run_benchmark.sh` to accept `--framework {sweagent,opencode,openhands,codex}`
   (default: sweagent for backwards compatibility).

2. Refactor `batch/hpc_benchmark_runner.py` to dispatch to framework-specific launch
   logic while sharing workspace setup, patch extraction, and result collection.

3. Integrate OpenCode first (closest to SWE-agent — has bash/edit/read tools natively,
   `opencode run --format json` for headless mode, no Docker dependency).

4. Integrate OpenHands second (needs podman-hpc wrapping on Perlmutter, headless API,
   CodeActAgent with tool bundles).

5. Integrate Codex CLI third (needs `codex exec` YOLO mode, vLLM `wire_api=chat`
   configuration, AGENTS.md instead of YAML config).

6. Create per-framework config generation so each framework gets equivalent instructions
   and tool access as our SWE-agent YAML configs provide.

7. Unified result format — all frameworks output to the same `benchmark_results.json`
   schema with: instance_id, framework, success, agent_speedup, agent_correctness,
   file_overlap, patch_similarity, duration_seconds.

VALIDATION (do these before finishing):
- Run `bash batch/run_benchmark.sh --help` and verify --framework flag appears
- Dry-run each framework dispatch path with a print/log statement to verify routing
  (no GPU needed — just confirm the launch command is constructed correctly)
- Verify `batch/run_benchmark.sh --base --lulesh --framework opencode` generates a
  valid launch command (even if OpenCode isn't installed yet, the command should be correct)
- Verify backwards compatibility: `batch/run_benchmark.sh --base --lulesh` (no
  --framework flag) still defaults to sweagent and produces the same behavior as before

CONSTRAINTS:
- The harness tools (kripke_run, laghos_run, etc.) are framework-agnostic — any agent
  that can call bash gets them. Don't duplicate harness logic per framework.
- Patch extraction should use `git diff` from the workspace for all frameworks.
- External model support (`--external-model --model-name gpt-4o`) should work for all
  frameworks, not just SWE-agent.
- Commit working changes as checkpoints after each major goal before moving to the next.
- Choose an approach and commit to it. Don't revisit decisions unless you hit a concrete
  blocker.

SESSION CONTINUITY:
Your context will auto-compact if this session runs long. Before that happens:
1. Commit all working changes to git (even WIP commits are fine)
2. Run /save-state to write structured progress to STATE.md and HANDOFF.md
3. Stop working — a fresh session with /load-state will pick up cleanly

If this IS a continuation session (you see goal progress in HANDOFF.md), resume from
the first unchecked goal. Read the files listed in HANDOFF.md before continuing. Do not
re-evaluate the approach — the previous session already chose it.

Start by reading the existing `batch/hpc_benchmark_runner.py` and `batch/run_benchmark.sh`
to understand the current dispatch flow, then enter plan mode to design the framework
abstraction before implementing.
```

---

## Phase 2: Integrate Additional Benchmarks

```
/load-state

I need to integrate two additional benchmark suites into our HPC agent benchmark pipeline:
GPA-Benchmark (GPU anti-pattern kernels) and SWE-fficiency (Python optimization tasks).

CONTEXT: Our pipeline currently benchmarks agents on 4 LLNL proxy apps (Kripke, Laghos,
Lulesh, Quicksilver) using harness tools in `tools/*_harness/`. After Phase 1, we support
multiple agent frameworks via `--framework`. Now we need to expand the task diversity.
This is Phase 2 of 3.

The relevant skills are documented:
- `.claude/skills/gpa-benchmark/SKILL.md` — GPA-Benchmark details (20+ GPU kernels,
  Python driver, code-swap format)
- `.claude/skills/swefficiency/SKILL.md` — SWE-fficiency details (498 Python tasks,
  Docker eval, speedup ratio metric)
- `.claude/skills/swe-agent-framework/SKILL.md` — current pipeline reference

Use the `proxy-app-expert` agent for harness design and the `framework-expert` agent for
how benchmarks integrate with the multi-framework dispatch.

GOALS (in priority order):

1. GPA-Benchmark first (runs natively on Perlmutter, no Docker, simpler integration):
   a. Create `tools/gpa_harness/` following the existing harness pattern (bin/gpa_build,
      bin/gpa_run, config.yaml)
   b. Adapt the code-swap format to work with git-diff-based patch extraction
   c. Add GPA entries to `batch/hpc_benchmark_runner.py` dispatch
   d. Add `--gpa` flag to `batch/run_benchmark.sh`
   e. Create `config/hpc/gpa_{no,with}_profiling.yaml` configs

2. SWE-fficiency second (needs podman-hpc wrapping, larger integration effort):
   a. Create `tools/swefficiency_harness/` that wraps the existing Python eval CLI
   b. Handle Docker to podman-hpc translation for eval containers
   c. Add to benchmark runner dispatch
   d. Create unified results that combine HPC speedup with SWE-fficiency speedup ratio

VALIDATION:
- GPA: Run `gpa_build` and `gpa_run` on a single easy-difficulty kernel on a compute
  node. Verify CORRECTNESS + SPEEDUP output matches the existing harness format.
- GPA: Run `bash batch/run_benchmark.sh --base --gpa` and verify it dispatches correctly.
- SWE-fficiency: Run the eval harness on one instance with podman-hpc and verify the
  speedup ratio is captured in results.
- Backwards compatibility: Verify existing LLNL app benchmarks still work unchanged.

CONSTRAINTS:
- Follow the existing harness pattern: every *_run produces CORRECTNESS + SPEEDUP in one
  call with automatic pristine baseline comparison.
- GPA code-swap format (editable regions with START/END markers) differs from git diff.
  The harness needs to bridge this gap.
- SWE-fficiency uses Docker images per instance — on Perlmutter this must use podman-hpc.
- Results should merge into the same `benchmark_results.json` schema.
- Commit working changes as checkpoints after completing each benchmark integration.

SESSION CONTINUITY:
Your context will auto-compact if this session runs long. Before that happens:
1. Commit all working changes to git (even WIP commits are fine)
2. Run /save-state to write structured progress to STATE.md and HANDOFF.md
3. Stop working — a fresh session with /load-state will pick up cleanly

If this IS a continuation session (you see goal progress in HANDOFF.md), resume from
the first unchecked goal. Read the files listed in HANDOFF.md before continuing. Do not
re-evaluate the approach — the previous session already chose it.

Start by reading an existing harness (e.g., `tools/kripke_harness/`) to understand the
pattern, then enter plan mode to design the GPA harness before implementing.
```

---

## Phase 3: Repo Restructuring

```
/load-state

I need to restructure this project from a monolithic SWE-agent fork into a clean
`agents-perf` repository where SWE-agent, other frameworks, and benchmark suites are
git submodules.

CONTEXT: The repo currently has SWE-agent code at the root (main tracks upstream, local
is our branch), with proxy app repos cloned as siblings, and all our custom infrastructure
in tools/, config/, batch/, .claude/. After Phases 1 and 2, we have multi-framework
support and multiple benchmark suites. Now we need clean organization. This is Phase 3
of 3 — the highest-risk change in the project.

GOALS:

1. Design a new repo structure where:
   - Root is `agents-perf` (our code: batch/, tools/, config/, scripts/, dataset/)
   - `frameworks/sweagent/` is a submodule tracking upstream SWE-agent
   - `frameworks/openhands/`, `frameworks/opencode/`, `frameworks/codex/` are submodules
   - `apps/{kripke,laghos,lulesh,quicksilver}/` are submodules of pristine app repos
   - `benchmarks/gpa-benchmark/` and `benchmarks/swefficiency/` are submodules
   - Shared deps (mfem, hypre, metis) stay as direct clones (not submodules)

2. Update all path references across: batch scripts, harnesses, configs, skills,
   agent docs, and CLAUDE.md to use the new structure.

3. Ensure `batch/run_benchmark.sh` and `hpc_benchmark_runner.py` work with submodule
   paths.

4. Preserve git history — this should be a reorganization, not a fresh start.

VALIDATION:
- After restructuring, run `bash batch/run_benchmark.sh --base --lulesh` end-to-end
  on a compute node. This exercises workspace creation, harness dispatch, pristine
  baseline, and result collection.
- Verify all 15 skills, 4 agents, 4 commands load correctly (grep for broken paths).
- Verify `git submodule status` shows all submodules pinned to correct commits.
- Verify `scripts/setup_apps.sh` builds all apps from submodule paths.

CONSTRAINTS:
- Every path change must be tested — a single broken path breaks the whole pipeline.
- Submodules should pin to specific commits, not track branches.
- The `_test/` working copies pattern must still work (rsync from submodule to workspace).
- All 15 skills, 4 agents, 4 commands, and 3 agent_docs need path updates.
- Commit in small, logical chunks — one commit per major move, not one giant commit.

SESSION CONTINUITY:
Your context will auto-compact if this session runs long. Before that happens:
1. Commit all working changes to git (even WIP commits are fine)
2. Run /save-state to write structured progress to STATE.md and HANDOFF.md
3. Stop working — a fresh session with /load-state will pick up cleanly

If this IS a continuation session (you see goal progress in HANDOFF.md), resume from
the first unchecked goal. Read the files listed in HANDOFF.md before continuing. Do not
re-evaluate the approach — the previous session already chose it.

Enter plan mode first. Design the migration carefully before touching any files.
```
