# HANDOFF.md — Session 9 Summary

Last updated: 2026-02-12 (session 9)

## What Was Done

Retested and fixed Codex/Quicksilver and OpenHands/Lulesh on Perlmutter compute nodes. Found and fixed 5 new bugs (3 Codex, 2 OpenHands + 1 env ordering). Both frameworks now pass. Phase 1 framework integration is **COMPLETE**. Merged `framework-integration` into `local`. Updated skill files and MEMORY.md.

## Goal Progress

- [x] Create feature branch `framework-integration`
- [x] Install OpenCode, OpenHands, Codex CLI
- [x] Create batch/frameworks/ package (base + sweagent + all 3 new launchers)
- [x] Refactor hpc_benchmark_runner.py (--framework, launcher dispatch)
- [x] Refactor run_benchmark.sh (--framework, nvm setup, banner)
- [x] Per-framework config generation (YAML/JSON/TOML/-c flags)
- [x] Shared prompt templates with framework-specific adaptations
- [x] Unified result format (framework field in BenchmarkResult)
- [x] Update docs (architecture.md, experiment-workflow.md)
- [x] Fix import bugs (batch/__init__.py, sys.path)
- [x] Fix Codex --yolo → --dangerously-bypass-approvals-and-sandbox
- [x] Fix OpenHands --headless → SDK runner (openhands_runner.py)
- [x] Fix vLLM HF env vars in podman container
- [x] Live test: OpenCode/Quicksilver — **PASS**
- [x] Live test: SWE-agent/Lulesh — Agent worked (pre-existing path bug)
- [x] Fix Codex config: custom provider `ext`, bare model name, model_provider field
- [x] Fix OpenHands: module load ordering, -m invocation, env var cleanup
- [x] Live test: Codex/Quicksilver — **PASS** (job 48811735, 141s)
- [x] Live test: OpenHands/Lulesh — **PASS** (job 48812701, 151s)
- [x] Update skill files with correct CLI flags and Perlmutter fixes
- [x] Merge framework-integration into local
- [ ] Phase 2: GPA-Benchmark + SWE-fficiency integration
- [ ] Phase 3: Restructure repo with submodules
- [ ] Run full benchmark suite with all 4 frameworks on all 4 apps
- [ ] Fix SWE-agent Lulesh doubled path (pre-existing config issue)

## Commits on local (framework-integration merged)

- `65bd095e` — WIP: Fix Codex config and OpenHands tmux for framework validation
- `3ab892ff` — WIP: Fix framework launcher bugs found during live validation
- `14f75f1e` — Update docs for multi-framework benchmark support
- `38fdcaf3` — Add multi-framework support for HPC benchmark pipeline

Plus session 9 commit with all Codex/OpenHands fixes and skill file updates.

## Files Modified This Session (Session 9)

| File | Change |
|------|--------|
| `batch/frameworks/codex.py` | Custom provider `ext` (not `openai`), `model_provider` field, bare model name |
| `batch/frameworks/openhands.py` | Module loads before venv activation, `-m` runner invocation, spack/HPCToolkit setup |
| `batch/frameworks/openhands_runner.py` | sys.path cleanup, `_clean_env_for_tmux()` env var stripping |
| `.claude/skills/codex-cli/SKILL.md` | Updated `--yolo` → `--dangerously-bypass-approvals-and-sandbox`, external API config section, common issues 8-9 |
| `.claude/skills/openhands/SKILL.md` | Added Perlmutter-specific fixes section (issues 6-10) |
| `STATE.md` | Updated with session 9 results |
| `.planning/HANDOFF.md` | This file |

## Files to Read First Next Session

1. `STATE.md` — Full state overview
2. `.planning/HANDOFF.md` — This file
3. `agent_docs/architecture.md` — System design for Phase 2 planning
4. `agent_docs/experiment-workflow.md` — Benchmark workflow reference

## Key Bug Fixes (Session 9)

### Codex Built-in Provider Shadow

`config/mod.rs:1521` uses `or_insert` — user overrides for built-in provider names (like `openai`) are silently dropped. Must use custom provider name `ext`:

```bash
-c "model_provider=ext"
-c "model_providers.ext.name=ext"
-c "model_providers.ext.base_url=https://us.api.openai.com/v1"
-c "model_providers.ext.env_key=OPENAI_API_KEY"
-c "model_providers.ext.wire_api=responses"
-c "model=gpt-4o-mini"           # bare name, NOT ext/gpt-4o-mini
```

### OpenHands Module Load Ordering

`module load python` after venv activation overrides venv's Python in PATH. Fix: load modules BEFORE `source activate`.

### OpenHands tmux "command too long"

OpenHands SDK passes `os.environ` to `tmux new_session -e` flags. On compute nodes with 100+ SLURM/Cray vars, command exceeds limit. Fix: `_clean_env_for_tmux()` strips non-essential env vars before SDK init.

### OpenHands openhands.py Filename Shadow

`batch/frameworks/openhands.py` shadows pip `openhands` namespace package when script dir is on sys.path. Fix: invoke runner via `python -m batch.frameworks.openhands_runner` and strip script dir from sys.path in runner.

## Agent Execution Quality Issues (Discovered Session 10)

Phase 1 validated framework integration (plumbing), but deeper result analysis shows no agent produced real optimizations:

### Issue 1: Codex `qs_run` silent failure (HIGH PRIORITY)
- **Symptom**: Agent built CUDA exe successfully, but all 6 `qs_run` calls returned empty `aggregated_output`
- **Impact**: Agent got stuck waiting for results, never proceeded to code exploration
- **Likely cause**: Codex exec mode may swallow stdout/stderr from harness scripts
- **Where to look**: `batch/frameworks/codex.py` build_launch_command(), harness script `tools/quicksilver_harness/bin/qs_run`
- **Test**: Run `codex exec` with a simple script that prints to stdout — does output appear in trajectory?
- **Results dir**: `batch_results/benchmark_20260212_110537_48811735/run_1/quicksilver/`
- **Trajectory**: `trajectories/benchmark_20260212_110537_48811735/run_1/quicksilver/quicksilver__base.jsonl`

### Issue 2: OpenCode environment access failure (HIGH PRIORITY)
- **Symptom**: Agent hit "invalid options in the ruleset configurations" on first `qs_build` call, couldn't access filesystem
- **Impact**: Zero progress — couldn't build, run, or read any files
- **Likely cause**: OpenCode sandbox/ruleset config too restrictive, or PATH not set up for harness tools
- **Where to look**: `batch/frameworks/opencode.py` build_launch_command(), check how PATH/env vars are passed
- **Results dir**: `batch_results/benchmark_20260212_095958_48809130/run_1/quicksilver/`
- **Trajectory**: `trajectories/benchmark_20260212_095958_48809130/run_1/quicksilver/quicksilver__base.jsonl`

### Issue 3: OpenHands build breakage (MEDIUM)
- **Symptom**: Agent deleted old Makefiles, modified allocator.cu, then `lulesh_build` failed 8x with "No rule to make target"
- **Impact**: Never ran the app, no performance measurement
- **Likely cause**: Agent made changes outside safe areas; prompt may need guardrails against Makefile deletion
- **Where to look**: `batch/frameworks/base.py` get_prompt(), lulesh prompt template
- **Results dir**: `batch_results/benchmark_20260212_112244_48812701/run_1/lulesh/`

### Issue 4: SWE-agent whitespace patches (LOW)
- **Symptom**: 129K-line patch of mostly reformatting, 0.84% regression
- **Impact**: Full workflow completed but no meaningful optimization
- **Likely cause**: gpt-4o-mini not capable enough for GPU optimization; may improve with stronger model
- **Results dir**: `batch_results/benchmark_20260212_101846_48810087/run_1/lulesh/`

## Phase 2 Planning Notes

Next steps from STATE.md:

1. **Fix agent execution issues** (Issues 1-2 above, before full benchmark run)
2. **GPA-Benchmark**: `/pscratch/sd/k/krydzy/gpa-benchmark` — GPU anti-pattern benchmarks. Wire into pipeline as instance source.
3. **SWE-fficiency**: `/pscratch/sd/k/krydzy/swefficiency` — Real-world repo optimization dataset. Wire into pipeline.
4. **Full benchmark run**: All 4 frameworks × all 4 apps with external gpt-4o-mini.
5. **Repo restructure**: Move proxy apps to submodules.

## Key Gotchas

1. **Branch is now `local`** — `framework-integration` was merged via fast-forward
2. **tmux 3.5a at `~/local/bin/tmux`** — must persist (it's in $HOME)
3. **`salloc -- CMD` pattern** is the correct way to run interactive benchmarks
4. **SWE-agent Lulesh path bug** is pre-existing and NOT related to framework integration
5. **OpenHands pip v1.2.1 is SDK/TUI only** — use openhands_runner.py, not CLI headless mode
