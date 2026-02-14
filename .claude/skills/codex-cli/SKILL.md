---
name: codex-cli
description: "OpenAI Codex CLI terminal agent. Use when user mentions 'codex', 'codex cli', Codex shell timeout, Codex provider config, or Codex benchmark runs."
---

# OpenAI Codex CLI

## Source & References

- **Local clone**: `/pscratch/sd/k/krydzy/codex/`
- **Config schema**: `/pscratch/sd/k/krydzy/codex/codex-rs/core/config.schema.json`

## Installation on Perlmutter

```bash
nvm use 22
npm install -g @openai/codex
codex --version
```

**Note**: The npm-installed binary has been replaced with a patched build (see Shell Timeout section). Original backed up at the same path with `.bak` suffix.

## Non-Interactive Mode (`codex exec`)

```bash
codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  --json --ephemeral \
  -c "model_provider=ext" \
  -c "model_providers.ext.name=ext" \
  -c "model_providers.ext.base_url=https://us.api.openai.com/v1" \
  -c "model_providers.ext.env_key=OPENAI_API_KEY" \
  -c "model=gpt-4o-mini" \
  "Your prompt here"
```

**IMPORTANT**: Must use a custom provider name (not `openai`) -- built-in provider uses `or_insert`, silently ignoring user overrides for `model_providers.openai.*`.

## Shell Command Timeout (PATCHED)

**Status: RESOLVED** (session 14, 2026-02-13)

The binary has been patched to support `CODEX_DEFAULT_EXEC_TIMEOUT_MS` env var with a 300s fallback default (was hardcoded 10s).

| Item | Detail |
|------|--------|
| Env var | `CODEX_DEFAULT_EXEC_TIMEOUT_MS` (milliseconds) |
| Default | 300,000 (5 minutes) — was 10,000 (10 seconds) |
| Source | `codex-rs/core/src/exec.rs:40` — `pub fn default_exec_command_timeout_ms()` |
| Integration | `batch/frameworks/codex.py` exports `CODEX_DEFAULT_EXEC_TIMEOUT_MS=300000` |

The benchmark runner handles this automatically. For manual Codex runs, export the env var:
```bash
export CODEX_DEFAULT_EXEC_TIMEOUT_MS=300000
```

**If the binary gets overwritten** (e.g., `npm update`), rebuild from patched source — see `references/internals.md` for build instructions.

## vLLM Configuration

Must set `wire_api=chat` -- Codex defaults to Responses API, vLLM only speaks Chat Completions.

```bash
codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check --json --ephemeral \
  -c "model_provider=local-vllm" \
  -c "model_providers.local-vllm.name=local-vllm" \
  -c "model_providers.local-vllm.base_url=http://127.0.0.1:8008/v1" \
  -c "model_providers.local-vllm.env_key=OPENAI_API_KEY" \
  -c "model_providers.local-vllm.wire_api=chat" \
  -c "model=gpt-oss-120b" \
  "Your prompt here"
```

## Key Architecture Facts

1. **npm wrapper -> Rust binary**: `codex-cli/bin/codex.js` spawns vendored Rust binary from `codex-rs/`
2. **Default: Responses API, NOT Chat Completions** -- won't work with vLLM unless `wire_api = "chat"`
3. **Project docs**: `AGENTS.md` (NOT `CLAUDE.md`)
4. **`model` and `model_provider` are separate fields** -- bare model name + provider routes to config

## Common Issues

1. **API 404/unsupported**: Forgot `wire_api = "chat"` for vLLM
2. **Built-in provider shadow**: Use custom provider name (not `openai`)
3. **Sandbox blocks GPU builds**: Use `--dangerously-bypass-approvals-and-sandbox`
4. **`AGENTS.md` not `CLAUDE.md`**: Codex ignores CLAUDE.md
5. **Lustre + Landlock**: `--dangerously-bypass-approvals-and-sandbox` bypasses Landlock

For detailed reference, see references/ in this skill directory.
