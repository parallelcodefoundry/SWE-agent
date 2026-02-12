# STATE.md — Current Project State

Last updated: 2026-02-12 (session 11)

## Active Experiments

None. Fixes committed but not yet validated on compute nodes.

## Current Focus

**Fix agent execution quality** — Session 10 analysis found no framework produced real optimizations due to 3 bugs. Session 11 diagnosed root causes and implemented fixes on branch `fix-agent-execution`. Fixes need validation on compute nodes before merging to `local`.

## Last Session (Session 11)

### Bugs Fixed

| Bug | Root Cause | Fix | Files |
|-----|-----------|-----|-------|
| Codex `qs_run` silent output | `DEFAULT_EXEC_COMMAND_TIMEOUT_MS = 10_000` in `codex-rs/core/src/exec.rs:38` — 10s default kills `qs_run` (~100s) before it produces output. `exit_code: null` = killed by timeout. | Added `CODEX_TIMEOUT_GUIDANCE` to prompt telling model to set `timeout_ms: 300000`. Added `PYTHONUNBUFFERED=1` to env. Added `sys.stdout.flush()` to qs_run header. | `batch/frameworks/prompt.py`, `batch/frameworks/codex.py`, `batch/frameworks/base.py`, `tools/quicksilver_harness/bin/qs_run` |
| OpenCode all tools fail | `OPENCODE_CONFIG_CONTENT` merged via `JSON.parse()` without Zod `permissionTransform`. String `"allow"` passed to `PermissionNext.fromConfig()` which called `Object.entries("allow")`, splitting into per-character rules `{action:"a"}, {action:"l"}, ...` — invalid Zod enum values. | Use object form `{"*": "allow"}` instead of string `"allow"` in config JSON. | `batch/frameworks/opencode.py` |
| OpenHands deletes Makefiles | Existing "Do NOT edit Makefiles" guidance too weak — agent ignored it and made +4837/-4966 line changes. | Added explicit `FORBIDDEN ACTIONS` section to all 4 app prompts: NEVER delete/rename/move Makefiles, NEVER rewrite entire source files, keep changes small. | `batch/frameworks/prompt.py` |

### Key Diagnostic Findings

- **OpenCode session data at `~/.local/share/opencode/storage/part/`** — Full tool call details (input, output, error) stored per-part as JSON. The JSONL trajectory only captures model text, not tool errors. This was essential for diagnosing the permission bug.
- **OpenCode log at `~/.local/share/opencode/log/`** — Contains the full permission ruleset showing the character-split rules at indices 13-17.
- **Codex has NO CLI flag or config.toml option to override the exec timeout** — Only the model can set `timeout_ms` per-command via `LocalShellExecAction`. No Rust toolchain on Perlmutter to rebuild from source.
- **OpenCode `opencode run` auto-rejects all permission requests** — `run.ts:512-523` publishes `permission.asked` events and auto-replies with `reply: "reject"`. So ALL permissions must evaluate to "allow" in the ruleset, never "ask".

### Commits on `fix-agent-execution`

- `88b0a398` — Add FORBIDDEN ACTIONS guardrails to all app prompts
- `2d20e83a` — Fix Codex timeout and OpenCode permission bugs

## Recent Decisions

- 2026-02-12 (s11): Use object form `{"*": "allow"}` for OpenCode permission (not string shorthand)
- 2026-02-12 (s11): Add CODEX_TIMEOUT_GUIDANCE to prompt (model sets timeout_ms: 300000 per-command)
- 2026-02-12 (s11): Add FORBIDDEN ACTIONS section to all 4 app prompts to prevent build destruction
- 2026-02-12 (s10): Use custom Codex provider name `ext` (not `openai`) to bypass built-in provider shadow
- 2026-02-12 (s10): Merged framework-integration into local (Phase 1 complete)

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| Codex/Quicksilver (session 9, final) | 48811735 | **PASS** — 141s, agent worked (but qs_run timeout bug) |
| OpenHands/Lulesh (session 9, final) | 48812701 | **PASS** — 151s, agent worked (but deleted Makefiles) |
| OpenCode/Quicksilver (ext model) | 48809130 | PASS — framework works (but permission bug blocked tools) |
| SWE-agent/Lulesh (ext model) | 48810087 | Agent worked 621s, whitespace-only changes |

## Uncommitted Changes

None. All changes committed on `fix-agent-execution` branch.

## Open Issues

- **Validate fixes on compute nodes** — Codex timeout fix, OpenCode permission fix, prompt guardrails need live testing
- **SWE-agent whitespace patches** — agent reformats code instead of optimizing (LOW — model behavior)
- SWE-agent doubled path bug: workspace ends in `/cuda` + git diff gives `cuda/src/...` → `cuda/cuda/src/...` (pre-existing)
- vLLM model cache (`openai/gpt-oss-120b`) is incomplete — needs HF_TOKEN for full download

## Next Steps

1. **Validate fixes** on compute nodes via `salloc -- CMD` pattern:
   - Codex/Quicksilver: verify qs_run produces output (non-empty `aggregated_output`, valid `exit_code`)
   - OpenCode/Quicksilver: verify bash tool works (no Zod validation errors)
   - OpenHands/Lulesh: harder to test guardrails (model-dependent), visual check of trajectory
2. **Merge `fix-agent-execution` into `local`** after validation
3. **Run full benchmark suite** with all 4 frameworks on all 4 apps
4. **Phase 2: GPA-Benchmark + SWE-fficiency integration**
5. **Phase 3: Restructure repo with submodules**
