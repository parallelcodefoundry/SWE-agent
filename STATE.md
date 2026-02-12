# STATE.md — Current Project State

Last updated: 2026-02-12 (session 8)

## Active Experiments

None. All jobs cancelled for session save.

## Current Focus

Phase 1 framework integration — debugging and fixing the last 2 framework launchers (Codex, OpenHands). Both bugs are now fixed and ready for retest.

## Last Session (Session 8)

### Bugs Fixed

| Bug | Fix | Files |
|-----|-----|-------|
| Codex config missing `name` field | Added `model_providers.{provider_id}.name={provider_id}` to `-c` flags | `batch/frameworks/codex.py` |
| Codex `wire_api=chat` no longer supported | Changed to `wire_api=responses` everywhere (chat was removed from Codex CLI) | `batch/frameworks/codex.py` |
| OpenHands SDK tmux 3.1c lacks `-e` flag | Built tmux 3.5a from source at `~/local/bin/tmux`; launcher adds it to PATH | `batch/frameworks/openhands.py` |

### SWE-agent/Lulesh Result (Job 48810087)

- Agent ran 621s with gpt-4o-mini external model, generated 129K-line patch
- Failed at post-run: path doubled `cuda/cuda/src/lulesh.cu` (workspace is `*/cuda`, git diff says `cuda/src/...`)
- **Pre-existing SWE-agent config issue**, not framework integration bug
- Agent successfully ran and made code changes — backwards compat validated

### Codex Trajectory Analysis

- Error: `Error loading config.toml: missing field 'name' in model_providers.openai`
- Fix: Added `name` field + changed `wire_api` from `chat` to `responses` (chat removed in current Codex version)

### tmux Build

- System tmux 3.1c lacks `new-session -e` flag (added in 3.2) needed by libtmux 0.53.0
- Built tmux 3.5a from source at `/tmp/tmux-3.5a/`, installed to `~/local/bin/tmux`
- Verified: `new-session -e KEY=VALUE` works, all OpenHands SDK imports succeed with new tmux

### Key Findings

- **Codex CLI `wire_api=chat` is removed** — only `responses` is supported now (Codex JSON Schema confirms)
- **Codex config requires `name` field** in `model_providers.{id}` (the only required field per schema)
- **Full OpenHands framework** at `/pscratch/sd/k/krydzy/swefficiency/OpenHands/` needs `browsergym` which won't install (greenlet build fails). SDK approach is better.
- **CLIRuntime** exists in full OpenHands (no tmux), but browsergym import blocks all agent hub imports

## Recent Decisions

- 2026-02-12: Build tmux 3.5a from source for libtmux compatibility (simpler than patching or full framework)
- 2026-02-12: Keep SDK runner approach for OpenHands (full framework has browsergym dep issue)
- 2026-02-12: Use `wire_api=responses` always for Codex (chat was removed)

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| OpenCode/Quicksilver (ext model) | 48809130 | PASS — framework integration validated |
| SWE-agent/Lulesh (ext model) | 48810087 | Agent worked 621s, post-run path bug (pre-existing) |
| Codex/Quicksilver (ext model) | 48810088 | Failed: config.toml missing `name` field (NOW FIXED) |
| OpenHands/Lulesh (ext model) | 48809277 | Failed: tmux -e flag (NOW FIXED) |
| SWE-agent/Lulesh (vLLM) | 48809129 | vLLM model weights missing |
| GPT-4o-mini (all 4 apps) | 48730028 | Completed (agents fought builds) |
| vLLM gpt-oss-120b (3 apps) | 48730084 | Completed (agents fought builds) |

## Uncommitted Changes

Modified and ready to commit:
- `batch/frameworks/codex.py` — Added `name` field, changed `wire_api` from `chat` to `responses`, updated docstrings
- `batch/frameworks/openhands.py` — Added `~/local/bin` to PATH for tmux 3.5a

## Open Issues

- SWE-agent doubled path bug: workspace ends in `/cuda` + git diff gives `cuda/src/...` → `cuda/cuda/src/...` (pre-existing)
- vLLM model cache (`openai/gpt-oss-120b`) is incomplete — needs HF_TOKEN for full download
- Agent sometimes switches GPU builds to OpenMP (model behavior, no fix yet)
- Skill files still have wrong CLI flags (codex-cli/SKILL.md, openhands/SKILL.md)

## Next Steps

1. **Retest Codex + OpenHands on compute node** (get interactive allocation first)
   - Codex/Quicksilver: `salloc ... -- bash batch/run_benchmark.sh --base --quicksilver --framework codex --external-model --model-name gpt-4o-mini`
   - OpenHands/Lulesh: `salloc ... -- bash batch/run_benchmark.sh --base --lulesh --framework openhands --external-model --model-name gpt-4o-mini`
2. **Update skill files**: Fix incorrect CLI flags in codex-cli and openhands skills
3. **When all 4 frameworks pass**: Merge `framework-integration` into `local`
4. Phase 2: Integrate GPA-Benchmark + SWE-fficiency
5. Phase 3: Restructure repo with submodules
