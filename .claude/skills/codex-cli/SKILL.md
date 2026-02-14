---
name: codex-cli
description: "OpenAI Codex CLI terminal agent. Use when user mentions 'codex', 'codex cli', Codex shell timeout, Codex provider config, or Codex benchmark runs. CRITICAL: Codex has a 10s default shell timeout bug."
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

## Shell Command Timeout (CRITICAL for HPC)

**Default timeout: 10 seconds** (`DEFAULT_EXEC_COMMAND_TIMEOUT_MS = 10_000` in `codex-rs/core/src/exec.rs:38`). This kills any command running longer than 10s. HPC harnesses need 60-120+ seconds.

**Symptoms**: `aggregated_output: ""` and `exit_code: null` in JSONL trajectory.

**No CLI override exists.** Timeout can ONLY be set per-command by the model via `LocalShellExecAction.timeout_ms`. Include explicit guidance in prompt and `AGENTS.md`:
```
CRITICAL: Set timeout_ms: 300000 (5 minutes) for all build/run harness commands.
```

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
4. **Harness commands return empty output**: 10s timeout killing the process
5. **`AGENTS.md` not `CLAUDE.md`**: Codex ignores CLAUDE.md
6. **Lustre + Landlock**: `--dangerously-bypass-approvals-and-sandbox` bypasses Landlock

For detailed reference, see references/ in this skill directory.
