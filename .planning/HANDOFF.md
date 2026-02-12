# HANDOFF.md — Session 11 Summary

Last updated: 2026-02-12 (session 11)

## What Was Done

Diagnosed and fixed the 3 agent execution bugs discovered in session 10 analysis. All fixes committed on branch `fix-agent-execution` (off `local`). Fixes not yet validated on compute nodes.

## Goal Progress

- [x] Goal 0: Create feature branch `fix-agent-execution` off `local`
- [x] Goal 1: Fix Codex `qs_run` silent output (HIGH) — Root cause: 10s exec timeout kills ~100s harness
- [x] Goal 2: Fix OpenCode environment access (HIGH) — Root cause: `Object.entries("allow")` splits string into character rules
- [x] Goal 3: Fix OpenHands build breakage (MEDIUM) — Added FORBIDDEN ACTIONS guardrails to all prompts
- [ ] Validate fixes on compute nodes (not yet done)
- [ ] Merge `fix-agent-execution` into `local`

## Files Modified This Session

| File | Change |
|------|--------|
| `batch/frameworks/prompt.py` | Added `CODEX_TIMEOUT_GUIDANCE` template (injected for Codex only). Added `FORBIDDEN ACTIONS` section to all 4 app SYSTEM_CONTEXT entries. |
| `batch/frameworks/codex.py` | Added timeout guidance to AGENTS.md written to workspace |
| `batch/frameworks/base.py` | Added `PYTHONUNBUFFERED=1` to env exports |
| `batch/frameworks/opencode.py` | Changed `"permission": "allow"` → `"permission": {"*": "allow"}` (both external and vLLM configs) |
| `tools/quicksilver_harness/bin/qs_run` | Added `sys.stdout.flush()` after header prints |
| `STATE.md` | Updated with session 11 results |
| `.planning/HANDOFF.md` | This file |

## Files to Read First Next Session

1. `STATE.md` — Full state overview
2. `.planning/HANDOFF.md` — This file
3. `batch/frameworks/prompt.py` — CODEX_TIMEOUT_GUIDANCE and FORBIDDEN ACTIONS (lines ~140-160 for timeout, lines 13-80 for app contexts)
4. `batch/frameworks/opencode.py:49-80` — Permission fix with detailed comment

## Root Cause Details

### Codex `qs_run` Silent Output

**Source**: `codex-rs/core/src/exec.rs:38` — `pub const DEFAULT_EXEC_COMMAND_TIMEOUT_MS: u64 = 10_000`

When the model calls a shell command, Codex waits 10 seconds then kills the process group (exit code 124). The trajectory showed `"aggregated_output":""` and `"exit_code":null` for all 6 `qs_run` calls — classic timeout signature.

**Why no CLI override**: The timeout can only be set per-command by the model via `LocalShellExecAction.timeout_ms`. No CLI flag, no config.toml field. Would need to rebuild from Rust source (no toolchain on Perlmutter).

**Fix approach**: Prompt-based — tell the model to always use `timeout_ms: 300000` for build/run commands. Also added `PYTHONUNBUFFERED=1` so partial output appears before timeout.

### OpenCode Permission Failure

**Source**: `opencode/packages/opencode/src/config/config.ts:179` — `result = mergeConfigConcatArrays(result, JSON.parse(Flag.OPENCODE_CONFIG_CONTENT))`

The `OPENCODE_CONFIG_CONTENT` is merged as raw JSON without running through the Zod schema. The Zod `Permission` schema has a `.transform(permissionTransform)` that converts `"allow"` → `{"*": "allow"}`, but this transform never runs for inline config.

In `agent.ts:74`: `const user = PermissionNext.fromConfig(cfg.permission ?? {})` receives the raw string `"allow"`. `Object.entries("allow")` → `[["0","a"],["1","l"],["2","l"],["3","o"],["4","w"]]`. Each becomes a rule with invalid action value.

**Evidence**: OpenCode log at `~/.local/share/opencode/log/2026-02-12T180103.log:96` shows the exact ruleset with character-split entries. OpenCode storage at `~/.local/share/opencode/storage/part/msg_c530387b.../prt_c5303d82...json` shows the Zod validation error.

**Fix**: Use `{"*": "allow"}` (object) instead of `"allow"` (string) in the config JSON. This is the post-transform form, so it works even without the Zod transform running.

**Additional finding**: `opencode run` (headless mode) auto-REJECTS all permission requests at `run.ts:512-523`. This means every tool permission MUST evaluate to "allow" in the ruleset — anything that evaluates to "ask" gets rejected.

### OpenHands Build Breakage

**Symptom**: +4837/-4966 line changes in Lulesh, agent deleted Makefiles and broke the build across 8 attempts.

**Fix**: Added `FORBIDDEN ACTIONS` section to all 4 app SYSTEM_CONTEXT entries in `prompt.py`:
- NEVER delete/rename/move Makefiles or build config
- NEVER delete/rewrite entire source files
- NEVER remove #include, class defs, or function signatures
- NEVER disable CUDA/GPU code paths
- Keep changes small and incremental

## Validation Plan (Not Yet Done)

### Codex Validation
```bash
salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m2404 -- \
  bash -c 'source ~/.openai_env && source ~/envs/sweagent/bin/activate && python batch/hpc_benchmark_runner.py --framework codex --base --quicksilver --model-name gpt-4o-mini'
```
Success criteria: trajectory shows `qs_run` with non-empty output and valid exit_code.

### OpenCode Validation
```bash
salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m2404 -- \
  bash -c 'source ~/.openai_env && source ~/envs/sweagent/bin/activate && python batch/hpc_benchmark_runner.py --framework opencode --base --quicksilver --model-name gpt-4o-mini'
```
Success criteria: trajectory shows tool calls succeeding (no Zod errors), agent can run qs_build/qs_run.

### OpenHands Validation
```bash
salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m2404 -- \
  bash -c 'source ~/.openai_env && source ~/envs/sweagent/bin/activate && python batch/hpc_benchmark_runner.py --framework openhands --base --lulesh --model-name gpt-4o-mini'
```
Success criteria: agent does NOT delete Makefiles, patch size is reasonable (<500 lines).

## Key Gotchas

1. **Branch is `fix-agent-execution`** off `local` — don't merge until validation passes
2. **OpenCode hangs on login nodes** — must test on compute nodes or with proper API setup (`source ~/.openai_env`)
3. **Codex timeout fix is prompt-based** — effectiveness depends on whether gpt-4o-mini follows the timeout_ms guidance
4. **OpenHands guardrails are prompt-based** — can't mechanically prevent Makefile deletion, relies on model compliance
5. **OpenCode JSONL trajectory only shows model text** — to see actual tool errors, read `~/.local/share/opencode/storage/part/` JSON files
6. **`source ~/.openai_env`** must be run before any external model testing (sets OPENAI_API_BASE and OPENAI_API_KEY)
