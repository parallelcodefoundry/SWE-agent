# HANDOFF.md — Session 8 Summary

Last updated: 2026-02-12 (session 8)

## What Was Done

Diagnosed and fixed the remaining 2 framework launcher bugs (Codex config + OpenHands tmux). Also checked SWE-agent/Lulesh result from job 48810087. All fixes are coded but not yet retested on compute nodes.

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
- [x] Fix Codex config: added `name` field, changed `wire_api` from `chat` to `responses`
- [x] Fix OpenHands tmux: built tmux 3.5a from source at ~/local/bin/tmux
- [x] Check SWE-agent/Lulesh external model result — agent worked, post-run path bug (pre-existing)
- [ ] Live test: Codex/Quicksilver — **READY TO RETEST** (config fix applied)
- [ ] Live test: OpenHands/Lulesh — **READY TO RETEST** (tmux fix applied)
- [ ] Update skill files with correct CLI flags
- [ ] Merge framework-integration into local
- [ ] Phase 2: GPA-Benchmark + SWE-fficiency
- [ ] Phase 3: Restructure repo with submodules

## Commits on framework-integration

- `3ab892ff` — WIP: Fix framework launcher bugs found during live validation
- `14f75f1e` — Update docs for multi-framework benchmark support
- `38fdcaf3` — Add multi-framework support for HPC benchmark pipeline

Plus uncommitted changes (session 8 fixes) ready to commit.

## Files Modified This Session

| File | Change |
|------|--------|
| `batch/frameworks/codex.py` | Added `name` field to `-c` config flags; changed `wire_api` from `chat` to `responses`; updated docstrings |
| `batch/frameworks/openhands.py` | Added `~/local/bin` to PATH for tmux 3.5a; updated docstrings |
| `STATE.md` | Updated with session 8 findings |
| `.planning/HANDOFF.md` | This file |

## Files to Read First Next Session

1. `STATE.md` — Full state overview
2. `.planning/HANDOFF.md` — This file
3. `batch/frameworks/codex.py` — Verify `-c` flags look correct (especially `name` field format)
4. `batch/frameworks/openhands_runner.py` — SDK runner (verify tools/imports)

## Infrastructure Installed This Session

- **tmux 3.5a**: Built from source at `/tmp/tmux-3.5a/`, binary at `~/local/bin/tmux`
  - Fixes libtmux 0.53.0 `new-session -e KEY=VALUE` flag (requires tmux >= 3.2)
  - System tmux is 3.1c (lacks `-e` for `new-session`)
  - The OpenHands launcher now prepends `~/local/bin` to PATH in its shell script

## Key Bug Fixes (This Session)

### Codex Config Fix

The Codex CLI `-c` config flags were missing the required `name` field:

Before:
```bash
-c "model_providers.openai.base_url=https://api.openai.com/v1"
-c "model_providers.openai.env_key=OPENAI_API_KEY"
-c "model_providers.openai.wire_api=responses"
```

After:
```bash
-c "model_providers.openai.name=openai"          # <-- ADDED (only required field)
-c "model_providers.openai.base_url=https://api.openai.com/v1"
-c "model_providers.openai.env_key=OPENAI_API_KEY"
-c "model_providers.openai.wire_api=responses"    # <-- was "chat" (removed from Codex)
```

Schema source: `/pscratch/sd/k/krydzy/codex/codex-rs/core/config.schema.json` lines 425-511

### OpenHands tmux Fix

System tmux 3.1c → built tmux 3.5a from source. Launcher adds to PATH:
```bash
export PATH="$HOME/local/bin:$PATH"
```

### SWE-agent Path Bug (Pre-existing)

SWE-agent/Lulesh post-run fails with doubled path:
- Workspace: `*/workspaces/lulesh__base/cuda`
- Git diff file: `cuda/src/lulesh.cu`
- Combined: `cuda/cuda/src/lulesh.cu` → FileNotFoundError

This is a SWE-agent config issue (workspace root vs repo root mismatch). Not related to framework integration.

## Debugging Notes

### Codex — What to Check if Retest Fails

The trajectory file is the key diagnostic (realtime log is empty because codex exec redirects):
```
trajectories/benchmark_*/run_1/quicksilver/quicksilver__base.jsonl
```

Previous error was clear: `Error loading config.toml: missing field 'name' in model_providers.openai`

If it fails again, check:
1. The exact `-c` flags generated (written to `*_codex_config.txt` in output dir)
2. Whether `codex exec` needs `CODEX_API_KEY` env var (set at line 140)
3. Whether `--skip-git-repo-check` is needed/valid

### OpenHands — What to Check if Retest Fails

Test tmux 3.5a is on PATH inside the shell script:
```bash
source ~/envs/sweagent/bin/activate
export PATH="$HOME/local/bin:$PATH"
tmux -V  # should show 3.5a
```

If SDK runner still fails, check:
1. Import errors in `openhands_runner.py` (run standalone with `--help`)
2. Tool names: must use lowercase `terminal`, `file_editor` (not class names)
3. tmux server conflicts: `tmux kill-server` before running

## Test Commands for Next Session

```bash
# Source credentials first
source ~/.openai_env

# Reset test repos
bash ./scripts/reset_test_repos.sh --quicksilver --lulesh

# Get interactive compute node
salloc -N 1 -q interactive -t 01:00:00 -C gpu --gpus-per-node=4 --gpu-bind=none --cpus-per-task=64 --ntasks-per-node=1 -A m2404

# Codex retest (from inside allocation):
bash batch/run_benchmark.sh --base --quicksilver --framework codex --external-model --model-name gpt-4o-mini

# OpenHands retest (from inside allocation):
bash batch/run_benchmark.sh --base --lulesh --framework openhands --external-model --model-name gpt-4o-mini

# Or use salloc -- pattern (auto-releases node):
salloc -N 1 -q interactive -t 01:00:00 -C gpu --gpus-per-node=4 --gpu-bind=none --cpus-per-task=64 --ntasks-per-node=1 -A m2404 -- bash batch/run_benchmark.sh --base --quicksilver --framework codex --external-model --model-name gpt-4o-mini
```

## Key Gotchas

1. **Test repos were already reset** at the end of session 8 — no need to reset again unless other experiments ran
2. **tmux 3.5a binary at `~/local/bin/tmux`** — this must survive across sessions (it's in $HOME, so it should)
3. **The `-c` flag values must not have quotes inside quotes** — Codex CLI parses as TOML, bare strings work
4. **OpenHands SDK `openhands` pip v1.2.1** — TUI+SDK only, no `openhands.core.main`. Full framework at `/pscratch/sd/k/krydzy/swefficiency/OpenHands/` has browsergym dep issue
5. **Interactive queue**: max 2 running, 4 nodes each. Use `salloc -q interactive` for fastest allocation
