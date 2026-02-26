# STATE.md — Current Project State

Last updated: 2026-02-25 (session 26)

## Current Focus

**Session 26: Implemented prompt redesign, build mode flag, harness pivot, Kripke correctness strengthening, and scope refactoring.**

## Session 26 — Changes Implemented

### 1. Prompt Redesign (`batch/frameworks/prompt.py`) — COMPLETE
- **New structure**: Role + Autonomy → Build Target → Task → Workflow → Tools → Completion
- **Autonomy directive**: "NEVER ask for confirmation. Implement changes directly."
- **Non-interactive directive** (Codex, Claude): "You are in non-interactive mode. There is NO human to respond."
- **Per-app essential flags**: Explicit build requirements for Kripke, Laghos, Lulesh, Quicksilver
- **Removed**: "FORBIDDEN ACTIONS" block, "Do NOT edit Makefiles" restriction, "Thinking should be thorough"
- **Removed**: Optimization strategy suggestions (no longer telling agents what to optimize)
- **Added**: WHAT YOU CAN CHANGE / WHAT YOU MUST NOT CHANGE sections
- **Build mode support**: harness mode shows tools, direct mode shows build instructions

### 2. Build Mode Flag — COMPLETE
- `--build-mode {harness|direct}` added to:
  - `batch/hpc_benchmark_runner.py` (argparse + HPCBenchmarkRunner.__init__)
  - `batch/run_benchmark.sh` (passthrough to Python runner)
  - `batch/frameworks/__init__.py` (factory function)
  - `batch/frameworks/base.py` (FrameworkLauncher.__init__ + get_prompt)
- Harness mode (default): current behavior with relaxed restrictions
- Direct mode: agent gets build instructions in prompt, *_run still available

### 3. Harness Modifications — COMPLETE
- **kripke_build**: Checks if agent modified CMakeLists.txt; if so, preserves agent's CUDA flags while ensuring host compiler + architecture
- **qs_build**: Passes through agent's -O flags (was stripping them), warns if agent changed CXX

### 4. Kripke Correctness Check — COMPLETE
- `kripke_run:extract_scientific_values()` now parses:
  - Configuration params: iterations, zones, groups (exact match)
  - Physics values: total_unknowns, unknowns_per_direction, directions, phi (float with tolerance)
  - Timer counts: solve_count (verify algorithm ran)
- Tolerance changed from 1e-10 to 1e-6 (allows fast-math variance)

### 5. Framework Launcher Updates — COMPLETE
- **codex.py**: AGENTS.md includes anti-yielding directive at top
- **claude.py**: CLAUDE.md includes anti-yielding directive, removed "Do NOT modify build configuration" instruction

### 6. CLAUDE.md Scope Update — COMPLETE
- Updated project description (base mode as primary, no expert commits framing)
- Added build mode documentation
- Updated key commands to show base mode examples
- Removed SWE-fficiency references from main docs
- Preserved dataset/ for future use

### NOT Done (deferred)
- Branch cleanup (moving expert commit code to feature branch) — minimal impact, base mode already bypasses
- STATE.md / HANDOFF.md update for scope (doing now)
- Integration testing on compute node (requires interactive session)
- GPA prompt update (already has autonomy via shared directive, minor)

## Previous Sessions

- **Session 25** (2026-02-26): Analyzed benchmark results (6/9 jobs), fixed MPICH_DIR, Claude argparse, Laghos g++-12, OpenHands Lmod, Kripke GPU binding
- **Session 24** (2026-02-25): All infra fixes committed. 9 benchmark jobs submitted.
- **Session 23** (2026-02-25): Deep investigation of LLNL failures. Fixed kripke build, GPA CUDA, logging.
- **Session 22** (2026-02-25): Fixed logging, sbatch, vLLM, added Claude Code. First 5-fw benchmark (partial).

## Recent Decisions

- 2026-02-25 (s26): Base mode is primary benchmark mode (no expert comparison)
- 2026-02-25 (s26): Two build modes: harness (default) and direct (agent builds manually)
- 2026-02-25 (s26): Agents CAN now edit Makefiles and CMakeLists.txt
- 2026-02-25 (s26): Essential flags specified explicitly in prompt (not strategy suggestions)
- 2026-02-25 (s26): Anti-yielding language for Codex and Claude Code
- 2026-02-25 (s26): Expert commit comparison and SWE-fficiency deferred to feature branch

## Branch State

- **Current branch**: `dev`
- **Uncommitted changes**: 14 files (prompt redesign + build mode + harness + CLAUDE.md)

## Open Issues / TODOs

### Infrastructure — Still open
- [ ] **SWE-agent kripke git submodule** — `blt/../.git/modules/blt` broken in workspace copy
- [ ] **SWE-agent gpt-4.1-mini empty tool_calls** — API returns empty array, LiteLLM rejects it
- [ ] **GPA baseline build failures** — backprop/lavaMD missing C headers; exatensor/srad driver issue
- [ ] **GPA BFS/Gaussian correctness** — Float precision from `__ldg()` causes mismatches

### Validation Needed (s26 changes)
- [ ] **Prompt quality** — Run 1 agent on interactive node to verify new prompt produces better behavior
- [ ] **Harness mode** — Test kripke_build with modified CMakeLists.txt on compute node
- [ ] **Direct mode** — Test end-to-end on interactive node
- [ ] **Kripke correctness** — Verify strengthened check catches bad modifications
- [ ] **Full regression** — Run 1 framework on 4 LLNL apps to verify no breakage

### Longer-term
- [ ] **Merge dev into local/main** — Phase 2B + s25/s26 fixes ready
- [ ] **Full production benchmark** — 5 frameworks × 4 apps × {harness, direct} modes
- [ ] **Consider stronger model** — gpt-4.1-mini too weak; test gpt-4.1 or claude-sonnet
- [ ] **Expert commit comparison** — Move to feature/expert-commits-swefficiency branch

## Next Steps

1. **Commit s26 changes** — 14 files with prompt redesign, build mode, harness mods
2. **Interactive node validation** — Test one framework on one app with new prompts
3. **Verify Codex anti-yielding** — Critical: does Codex actually implement instead of asking?
4. **Test direct mode** — Single instance end-to-end
5. **Full benchmark rerun** — 5 frameworks × 4 LLNL apps with new prompts
