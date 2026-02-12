# STATE.md — Current Project State

Last updated: 2026-02-12 (session 9)

## Active Experiments

None. All validation runs completed successfully.

## Current Focus

Phase 1 framework integration is **COMPLETE**. All 4 frameworks (SWE-agent, OpenCode, Codex, OpenHands) validated on Perlmutter compute nodes with external gpt-4o-mini. Branch `framework-integration` merged into `local`. Ready for Phase 2.

## Last Session (Session 9)

### Bugs Fixed

| Bug | Fix | Files |
|-----|-----|-------|
| Codex built-in provider shadow | Use custom provider `ext` instead of `openai` (config/mod.rs `or_insert` silently drops overrides for built-ins) | `batch/frameworks/codex.py` |
| Codex model name sent with provider prefix | Set `model_provider=ext` separately, `model=gpt-4o-mini` bare | `batch/frameworks/codex.py` |
| OpenHands `module load python` shadows venv | Moved module loads BEFORE `source activate` in shell script | `batch/frameworks/openhands.py` |
| OpenHands `openhands.py` shadows pip package | Invoke runner via `python -m batch.frameworks.openhands_runner` | `batch/frameworks/openhands.py` |
| OpenHands tmux "command too long" | Strip bulky SLURM/Cray env vars before SDK init | `batch/frameworks/openhands_runner.py` |

### Validation Results

| Framework | App | Job ID | Duration | Result |
|-----------|-----|--------|----------|--------|
| Codex | Quicksilver | 48811735 | 141s | **PASS** — agent called qs_build/qs_run, 27-line trajectory |
| OpenHands | Lulesh | 48812701 | 151s | **PASS** — conversation created, agent executed |

### Key Findings

- **Codex config/mod.rs:1521** uses `or_insert` for merging user providers into built-ins — user overrides for `model_providers.openai.*` are silently dropped. Must use custom provider name.
- **Codex `model` and `model_provider` are separate config fields** — model name (sent in API request) must NOT include provider prefix.
- **OpenHands SDK passes `os.environ` to tmux `-e` flags** — on compute nodes with 100+ SLURM/Cray vars, the command exceeds tmux's limit.
- **`module load python` after venv activation** overrides venv's Python in PATH, breaking pip package resolution.
- **salloc -- CMD** pattern works for running run_benchmark.sh (sets SLURM env vars, script's internal srun dispatches to compute node).

## Recent Decisions

- 2026-02-12: Use custom Codex provider name `ext` (not `openai`) to bypass built-in provider shadow
- 2026-02-12: Set `model_provider` separately from `model` in Codex config (bare model name in API request)
- 2026-02-12: Clean env vars in OpenHands runner to fit within tmux command length limit
- 2026-02-12: Move module loads before venv activation in OpenHands shell script
- 2026-02-12: Invoke openhands_runner.py via `python -m` to prevent openhands.py filename shadow
- 2026-02-12: Merged framework-integration into local (Phase 1 complete)

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| Codex/Quicksilver (session 9, final) | 48811735 | **PASS** — 141s, agent worked |
| OpenHands/Lulesh (session 9, final) | 48812701 | **PASS** — 151s, agent worked |
| OpenCode/Quicksilver (ext model) | 48809130 | PASS — framework integration validated |
| SWE-agent/Lulesh (ext model) | 48810087 | Agent worked 621s, post-run path bug (pre-existing) |
| Codex/Quicksilver (session 8) | 48810088 | Failed: config.toml missing `name` field (fixed session 8) |
| OpenHands/Lulesh (session 8) | 48809277 | Failed: tmux -e flag (fixed session 8) |
| GPT-4o-mini (all 4 apps) | 48730028 | Completed (agents fought builds) |
| vLLM gpt-oss-120b (3 apps) | 48730084 | Completed (agents fought builds) |

## Uncommitted Changes

None. All changes committed on `local` branch.

## Agent Execution Quality (Session 10 Analysis)

Phase 1 validated that frameworks integrate (plumbing works), but deeper analysis of all 4 runs reveals no framework produced actual optimizations:

| Framework | App | Built? | Ran? | Code Changes? | Speedup |
|-----------|-----|--------|------|--------------|---------|
| **Codex** | Quicksilver | Yes | No (qs_run silent fail) | None | N/A |
| **OpenHands** | Lulesh | Failed 8x | No | Yes (broke build) | N/A |
| **OpenCode** | Quicksilver | No (env errors) | No | None | N/A |
| **SWE-agent** | Lulesh | Yes | Yes | Whitespace only | -0.84% (regression) |

### Issues Blocking Agent Effectiveness

1. **Codex `qs_run` silent failure**: Agent built CUDA exe successfully, but all 6 `qs_run` calls returned empty output. Agent got stuck waiting. Likely Codex exec mode swallows stdout/stderr from the harness script.
2. **OpenCode environment access failure**: Agent hit "invalid options in the ruleset configurations" immediately on `qs_build`. Could not access filesystem or run any tools. PATH/sandbox config issue.
3. **OpenHands build breakage**: Agent deleted old Makefiles and modified allocator.cu, then `lulesh_build` failed with "No rule to make target 'src/allocator.o'". Never recovered across 8 build attempts.
4. **SWE-agent whitespace-only changes**: 129K-line patch that's mostly reformatting. Baseline 4.159s → modified 4.194s (0.84% regression). Correctness passed but no real optimization.

## Open Issues

- **Codex `qs_run` output not captured** — harness stdout swallowed by Codex exec mode (HIGH PRIORITY)
- **OpenCode can't access harness tools** — sandbox/ruleset blocks `qs_build` (HIGH PRIORITY)
- **OpenHands no build recovery** — agent breaks build and doesn't recover (MEDIUM — prompt/harness issue)
- **SWE-agent whitespace patches** — agent reformats code instead of optimizing (LOW — model behavior)
- SWE-agent doubled path bug: workspace ends in `/cuda` + git diff gives `cuda/src/...` → `cuda/cuda/src/...` (pre-existing)
- vLLM model cache (`openai/gpt-oss-120b`) is incomplete — needs HF_TOKEN for full download
- Agent sometimes switches GPU builds to OpenMP (model behavior, no fix yet)

## Next Steps

1. **Fix agent execution issues** (before full benchmark run)
   - Debug Codex `qs_run` output capture (check harness stdout routing in exec mode)
   - Debug OpenCode tool access (check PATH setup, sandbox config in `batch/frameworks/opencode.py`)
   - Consider prompt improvements to prevent build breakage and whitespace-only changes
2. **Phase 2: GPA-Benchmark + SWE-fficiency integration**
   - GPA-Benchmark: `/pscratch/sd/k/krydzy/gpa-benchmark` — GPU anti-pattern benchmarks
   - SWE-fficiency: `/pscratch/sd/k/krydzy/swefficiency` — real-world repo optimization dataset
   - Wire these into the benchmark pipeline as additional instance sources
3. **Phase 3: Restructure repo with submodules**
   - Clean up the repo structure, move proxy apps to proper submodules
4. **Run full benchmark suite** with all 4 frameworks on all 4 apps
5. **Fix SWE-agent Lulesh doubled path** (pre-existing config issue)
