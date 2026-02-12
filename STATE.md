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

## Open Issues

- SWE-agent doubled path bug: workspace ends in `/cuda` + git diff gives `cuda/src/...` → `cuda/cuda/src/...` (pre-existing)
- vLLM model cache (`openai/gpt-oss-120b`) is incomplete — needs HF_TOKEN for full download
- Agent sometimes switches GPU builds to OpenMP (model behavior, no fix yet)

## Next Steps

1. **Phase 2: GPA-Benchmark + SWE-fficiency integration**
   - GPA-Benchmark: `/pscratch/sd/k/krydzy/gpa-benchmark` — GPU anti-pattern benchmarks
   - SWE-fficiency: `/pscratch/sd/k/krydzy/swefficiency` — real-world repo optimization dataset
   - Wire these into the benchmark pipeline as additional instance sources
2. **Phase 3: Restructure repo with submodules**
   - Clean up the repo structure, move proxy apps to proper submodules
3. **Run full benchmark suite** with all 4 frameworks on all 4 apps
4. **Fix SWE-agent Lulesh doubled path** (pre-existing config issue)
