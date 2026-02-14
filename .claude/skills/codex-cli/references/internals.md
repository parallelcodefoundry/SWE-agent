# Codex CLI Internals Reference

## Rust Architecture

The Codex CLI is a Rust binary (`codex-rs/`) wrapped by an npm package (`codex-cli/bin/codex.js`). The npm wrapper spawns the vendored Rust binary.

Key source files:
- `codex-rs/core/src/exec.rs` -- Shell command execution, contains `DEFAULT_EXEC_COMMAND_TIMEOUT_MS = 10_000`
- `codex-rs/core/config.schema.json` -- Full config schema
- `codex-rs/core/src/config/mod.rs` -- Config loading, built-in provider `or_insert` at line ~1521

## API Format

- **Default**: Responses API (OpenAI native)
- **Chat Completions**: Set `wire_api = "chat"` for vLLM or other OpenAI-compatible servers
- Agent tools: `shell` (sandboxed bash), `apply_patch` (file editing), `web_search` (optional), MCP servers

## Sandbox Modes

| Mode | Flag | Behavior |
|------|------|----------|
| read-only | `-s read-only` | Read only; writes need approval |
| workspace-write | `--full-auto` | Read/write in cwd; no network |
| danger-full-access | `--dangerously-bypass-approvals-and-sandbox` | Full access, no restrictions |

**For benchmarks**: Use `--dangerously-bypass-approvals-and-sandbox` -- SLURM provides isolation. Landlock may conflict with Lustre.

## Full `codex exec` Flags

```bash
codex exec \
  --dangerously-bypass-approvals-and-sandbox \  # No sandbox, no approvals
  --skip-git-repo-check \         # Don't require git repo
  --json \                        # JSONL events to stdout
  --ephemeral \                   # Don't persist session
  -c "KEY=VALUE" \                # Config overrides (repeatable)
  -o result.txt \                 # Final message to file
  "PROMPT"
```

Other flags: `--model/-m`, `--sandbox/-s MODE`, `--cd/-C DIR`, `--add-dir DIR`, `--profile/-p NAME`, `--output-schema schema.json`.

## External OpenAI API Configuration

```bash
export OPENAI_API_KEY="sk-proj-..."
export CODEX_API_KEY="${OPENAI_API_KEY}"

codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check --json --ephemeral \
  -c "model_provider=ext" \
  -c "model_providers.ext.name=ext" \
  -c "model_providers.ext.base_url=https://us.api.openai.com/v1" \
  -c "model_providers.ext.env_key=OPENAI_API_KEY" \
  -c "model_providers.ext.wire_api=responses" \
  -c "model=gpt-4o-mini" \
  -c "web_search=disabled" \
  "Your prompt here"
```

## Config File (`~/.codex/config.toml`)

```toml
model = "gpt-oss-120b"
model_provider = "local-vllm"
web_search = "disabled"
[model_providers.local-vllm]
name = "local-vllm"
base_url = "http://127.0.0.1:8008/v1"
env_key = "OPENAI_API_KEY"
wire_api = "chat"
```

## HPC Benchmark Setup (Full Example)

```bash
export PATH="/pscratch/sd/k/krydzy/SWE-agent/tools/kripke_harness/bin:$PATH"
export KRIPKE_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Kripke_test

cd "$KRIPKE_ROOT"
codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check --json --ephemeral \
  -c "model_provider=local-vllm" \
  -c "model_providers.local-vllm.name=local-vllm" \
  -c "model_providers.local-vllm.base_url=http://127.0.0.1:8008/v1" \
  -c "model_providers.local-vllm.env_key=OPENAI_API_KEY" \
  -c "model_providers.local-vllm.wire_api=chat" \
  -c "model=gpt-oss-120b" \
  -c "web_search=disabled" \
  "Optimize Kripke for A100. Use kripke_build --arch CUDA, kripke_run --arch CUDA" \
  > output.jsonl 2> stderr.log

git diff > agent_patch.diff
```

## Collecting Results

| Source | How |
|--------|-----|
| Trajectory | `--json` -> JSONL file |
| Final message | `-o result.txt` or stdout |
| Patch | `git diff` after run |
| Structured | `--output-schema schema.json -o output.json` |
| Errors | Filter JSONL for `"type": "error"` |
| Logs | `~/.codex/log/` or `RUST_LOG=codex_core=info` |

## Key Differences from SWE-agent

- **No tool bundles** -- shell calls any command in PATH
- **No Jinja2 templates** -- all context in prompt or AGENTS.md
- **No submit command** -- agent finishes when done
- **Must set `wire_api=chat`** for vLLM (SWE-agent uses litellm)
- **Sandboxed by default** -- use `--dangerously-bypass-approvals-and-sandbox` for open mode

## Full Known Issues

1. **API 404/unsupported**: Forgot `wire_api = "chat"` for vLLM
2. **"Not inside a trusted directory"**: Add `--skip-git-repo-check`
3. **Sandbox blocks GPU builds**: Use `--dangerously-bypass-approvals-and-sandbox` on Perlmutter
4. **Agent never finishes**: No submit gate. Add completion instructions in prompt
5. **Session disk bloat**: Use `--ephemeral`
6. **`AGENTS.md` not `CLAUDE.md`**: Codex ignores CLAUDE.md
7. **Lustre + Landlock**: `--dangerously-bypass-approvals-and-sandbox` bypasses Landlock
8. **Built-in provider shadow**: User overrides for `model_providers.openai.*` are silently ignored. Use a custom provider name like `ext`
9. **Regional API endpoint**: If your OpenAI key requires `us.api.openai.com`, you MUST use a custom provider with `base_url` set correctly
10. **Harness commands return empty output**: 10s default timeout is killing the process. See Shell Command Timeout section
