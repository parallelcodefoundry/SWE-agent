# Claude Code Usage Guide for HPC Agent Benchmark Suite

A human-readable guide to the Claude Code infrastructure we built for this project: what exists, how to use it, and what to do next.

## What We Built

We added three layers of Claude Code infrastructure on top of the benchmark codebase:

### 1. Skills (`.claude/skills/`) — Domain Knowledge

Skills are markdown files containing detailed reference material. Claude loads them **automatically** when the conversation topic matches the skill's description. You don't need to ask for them — if you mention "Kripke build" or "Nsight Compute profiling", the relevant skill gets pulled into context.

| Skill | What It Knows | Loaded When You... |
|-------|---------------|-------------------|
| `perlmutter` | SLURM, modules, hardware specs, filesystems, common errors | Talk about jobs, allocations, modules, compute nodes |
| `kripke` | Build flags, CMake config, run params, output parsing, correctness checks | Work on Kripke harness or benchmarks |
| `laghos` | MFEM/hypre/metis deps, build steps, run params, correctness tolerances | Work on Laghos harness or benchmarks |
| `lulesh` | g++-12 requirement, embedded Makefile, run params, correctness checks | Work on Lulesh harness or benchmarks |
| `quicksilver` | g++-12 requirement, build with make, run params, correctness checks | Work on Quicksilver harness or benchmarks |
| `hpctoolkit` | hpcrun/hpcstruct/hpcprof commands, spack loading, output format | Implement or debug HPCToolkit profiling |
| `hatchet` | Tree structures, profile loading, hot-path analysis, metric extraction | Work on profile analysis tools |
| `nsight-compute` | ncu CLI, key GPU metrics, CSV/nsight-python parsing | Implement Nsight Compute profiling |
| `nsight-systems` | nsys CLI, trace collection, SQLite export, timeline analysis | Implement Nsight Systems profiling |
| `swe-agent-framework` | Config YAML structure, CLI, tool bundles, sandbox, model routing, dataset format | Configure SWE-agent runs or modify the framework |
| `openhands` | Sandbox setup, benchmark instances, evaluation, result collection | Integrate Openhands framework |
| `codex-cli` | Installation, automated execution, result collection | Integrate Codex CLI framework |
| `opencode` | Configuration, benchmark automation, result collection | Integrate OpenCode framework |
| `gpa-benchmark` | 20+ GPU anti-pattern benchmarks, build config, optimization targets | Add GPA-Benchmark apps to the suite |
| `swefficiency` | 498-task dataset, harness design, evaluation metrics | Add SWE-fficiency tasks to the suite |

**You can also manually trigger a skill** by mentioning its name or topic. If Claude doesn't auto-load one you need, just say "load the hpctoolkit skill" or reference the topic directly.

### 2. Agents (`.claude/agents/`) — Specialized Workers

Agents are specialized Claude instances that can be delegated to for specific work. Claude Code spawns them as subprocesses with their own tool access. They're used automatically when you ask for something that matches an agent's domain, or you can request one explicitly.

| Agent | Role | Tools | When To Use |
|-------|------|-------|-------------|
| `proxy-app-expert` | App harnesses, builds, correctness, GPA/SWE-fficiency | Read, Grep, Glob, Bash, Write | "Fix the Lulesh harness", "Add a new app harness", "Why is correctness failing?" |
| `framework-expert` | SWE-agent/Openhands/Codex/OpenCode config and integration | Read, Grep, Glob, Bash, Write | "Set up an Openhands benchmark", "Design the unified format", "Fix the SWE-agent config" |
| `perlmutter-executor` | GPU builds, compute node runs, salloc, module loading | Bash, Read | "Build Quicksilver on a compute node", "Run the benchmark", "Check why the build failed" |
| `profiling-expert` | HPCToolkit, Nsight, hatchet wrappers and analysis | Read, Grep, Glob, Bash, Write | "Implement the Nsight Compute wrapper", "Debug hatchet output", "Parse this profile" |

**The agents don't overlap.** proxy-app-expert knows *what* to build, perlmutter-executor knows *how* to build it on Perlmutter. profiling-expert knows profiling tools, framework-expert knows how frameworks invoke those tools.

### 3. Slash Commands (`.claude/commands/`) — Session Workflows

Slash commands are shortcuts you type in the Claude Code prompt. They expand into structured instructions.

| Command | What It Does | When To Use |
|---------|-------------|-------------|
| `/load-state` | Reads STATE.md, checks for HANDOFF.md, checks running SLURM jobs, reports what happened last session | **Start of every session** |
| `/save-state` | Updates STATE.md with session accomplishments, decisions, experiment status, and writes HANDOFF.md if mid-task | **End of every session** (or before clearing context) |
| `/check-experiment <id>` | Finds output in `batch_results/`, reads .out/.err, parses metrics, summarizes success/failure | After a benchmark job completes |
| `/write-plan` | Writes a detailed implementation plan to `.planning/PLAN-current.md` with bootstrap files, steps, gotchas, verification | Before starting a complex implementation task |

### 4. Agent Docs (`agent_docs/`) — Architecture Reference

These are longer reference documents that skills and agents point to:

| Document | Contents |
|----------|----------|
| `architecture.md` | Research goals (3 phases), why harnesses exist, project layout, data flow diagram, expansion plan |
| `experiment-workflow.md` | How to run benchmarks, benchmark vs base mode, what `run_benchmark.sh` orchestrates, result format, adding new apps/frameworks |

## How It All Fits Together

### Typical Session Flow

```
1. Start session
   └── /load-state
       ├── Reads STATE.md → what we were doing
       ├── Checks SLURM queue → any jobs running/completed
       └── Reports status and suggests next action

2. Work on tasks
   ├── Claude auto-loads relevant skills as topics come up
   ├── Delegates to agents when specialized work is needed
   └── You can explicitly request: "use the perlmutter-executor to build this"

3. End session
   └── /save-state
       ├── Updates STATE.md with what we accomplished
       ├── Writes HANDOFF.md if mid-task
       └── Next session picks up where we left off
```

### What You Need to Reference in Prompts

**You usually don't need to reference anything explicitly.** The system is designed to be automatic:

- **Skills** load based on topic detection from the skill description field. Mention "Kripke", "HPCToolkit", "Perlmutter", etc. and the relevant knowledge appears.
- **Agents** are selected based on the task. Ask to build something on GPU → perlmutter-executor. Ask about a harness → proxy-app-expert.
- **CLAUDE.md** is always loaded into every session automatically. It contains the project structure, key commands, and critical rules.

**When to be explicit:**
- If Claude doesn't seem to know something covered by a skill, say: *"Check the lulesh skill"* or *"Load the nsight-compute skill"*
- If you want a specific agent, say: *"Use the profiling-expert agent for this"*
- For complex multi-step work, start with `/write-plan` so the plan is written to a file that survives context compaction

### What Gets Loaded Automatically vs What Doesn't

| Resource | Loaded Automatically? | How? |
|----------|----------------------|------|
| `CLAUDE.md` | Always | Injected into system prompt at session start |
| `STATE.md` | No | Loaded by `/load-state` command |
| Skills | Yes, on topic match | Claude detects relevant topics and loads the skill |
| Agents | Yes, on task match | Claude delegates when the task fits an agent's description |
| `agent_docs/` | No | Referenced by skills and agents when needed; read on demand |
| `.planning/HANDOFF.md` | No | Read by `/load-state` if it exists |

## Current State of the Project

### What's Working End-to-End

- **SWE-agent pipeline**: `run_benchmark.sh` orchestrates vLLM server startup, benchmark execution across 4 proxy apps, agent-vs-expert comparison, and cleanup
- **4 proxy app harnesses**: Kripke, Laghos, Lulesh, Quicksilver — each with build/run/correctness tools
- **Profiling tool wrappers**: HPCToolkit (`hpc_profile`), Hatchet (`hatchet_analyze`), compiler analysis, microbenchmarking
- **Dataset**: 9 curated expert optimization commits across 4 apps
- **Two benchmark modes**: benchmark mode (agent vs expert) and base mode (agent on current code)
- **With/without profiling comparison**: same evaluation, different tool access

### What Has Skill Files But No Pipeline Integration

| Component | Skill Exists? | Harness Exists? | In Pipeline? | What's Missing |
|-----------|:---:|:---:|:---:|---|
| Openhands | Yes | No | No | Launch mechanism, tool integration, patch extraction |
| Codex CLI | Yes | No | No | Launch mechanism, tool integration, patch extraction |
| OpenCode | Yes | No | No | Launch mechanism, tool integration, patch extraction |
| GPA-Benchmark | Yes | No | No | Harnesses for 20+ benchmarks, dataset entries |
| SWE-fficiency | Yes | No | No | Harness adapter, dataset conversion |

### What Doesn't Exist Yet

- `--framework` flag in `run_benchmark.sh` (needed to run non-SWE-agent frameworks)
- Unified result format across frameworks (each framework collects results differently)
- Cross-framework comparison tooling
- Nsight Compute/Systems tool bundles for SWE-agent (skill files describe them, but no `config.yaml` in `tools/`)

## Next Steps — Recommended Sequence

The research goal (from `architecture.md`) has three phases:
1. Run all frameworks without profiling → find which framework optimizes best
2. Add profiling tools to the winning framework → run again
3. Compare with/without profiling → measure the effect of tool augmentation

### Immediate (Get Baseline Results)

**1. Run SWE-agent baseline experiments.**
This is the lowest-hanging fruit — the pipeline works, just run it:
```bash
# All apps, no profiling, 3 runs for statistical significance
sbatch batch/run_benchmark.sh --num-runs 3

# Or start with one app to validate
sbatch batch/run_benchmark.sh --lulesh --num-runs 3
```
Then `/check-experiment <jobid>` to see results.

**2. Run SWE-agent with profiling.**
Same dataset, same model, add profiling tools:
```bash
sbatch batch/run_benchmark.sh --profiling with_profiling --num-runs 3
```
This gives you the SWE-agent with/without profiling comparison immediately.

### Short-Term (Add Frameworks)

**3. Integrate the next framework (pick one).**

The `framework-expert` agent and framework skills have the knowledge to do this. The work for each framework:

a. **Create a launcher** — how to invoke the framework (e.g., `openhands --headless`, `codex --auto`)
b. **Wire harness tools** — each framework has a different tool-discovery mechanism (SWE-agent uses `config.yaml` bundles, Openhands uses Docker, Codex reads filesystem)
c. **Extract patches** — capture the agent's final diff in the same format as SWE-agent
d. **Add `--framework` flag** to `run_benchmark.sh`

Recommended order: Openhands first (most mature, best documented in skill file), then Codex CLI (simplest tool model), then OpenCode.

**4. Run cross-framework comparison.**
Once 2+ frameworks are wired in, run them on the same dataset and compare speedups, correctness rates, and patch quality.

### Medium-Term (Expand Applications)

**5. Add GPA-Benchmark applications.**
20+ GPU anti-pattern benchmarks. Each one needs a harness (build/run/correctness). The `gpa-benchmark` skill has the benchmark list and expected optimization targets. The `proxy-app-expert` agent can help create harnesses.

**6. Add SWE-fficiency tasks.**
498 Python optimization tasks. Needs a different harness pattern (Python, not compiled GPU code). The `swefficiency` skill has the dataset structure.

### Long-Term

**7. Nsight Compute/Systems as agent tools.**
The skill files describe how these work, but there are no SWE-agent tool bundles yet (`tools/nsight_compute/config.yaml` etc.). The `profiling-expert` agent can implement these.

**8. Unified reporting.**
Once multiple frameworks are producing results, build comparison dashboards. The `experiment-workflow.md` doc describes the result format that all frameworks should target.

## Tips for Effective Prompting

- **Be specific about the app**: "Fix the Kripke harness" loads the right skill. "Fix the harness" might not.
- **Name the framework**: "Configure this for Openhands" triggers the right skill. "Configure the benchmark" is ambiguous.
- **Use slash commands**: `/load-state` at session start saves you from re-explaining context. `/save-state` before ending means tomorrow's session picks up cleanly.
- **For compute work, say so**: "Build this on a compute node" or "Run this on GPU" triggers the perlmutter-executor agent, which handles salloc/modules/srun.
- **For planning, use `/write-plan`**: Complex multi-step tasks benefit from a written plan that survives context compaction. The plan goes to `.planning/PLAN-current.md` where it can be read by the next session.
- **Reference agent_docs for architecture questions**: If you need to understand how the benchmark pipeline works end-to-end, point Claude to `agent_docs/architecture.md` or `agent_docs/experiment-workflow.md`.
