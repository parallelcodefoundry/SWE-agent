---
name: codex-cli
description: "Knowledge about OpenAI Codex CLI terminal agent including installation, automated benchmark execution, result collection, and differences from other frameworks. Load when creating or modifying Codex CLI benchmarks."
---

# OpenAI Codex CLI

## Source & References

- **Local clone**: `/pscratch/sd/k/krydzy/codex/`
- **Config schema**: `/pscratch/sd/k/krydzy/codex/codex-rs/core/config.schema.json`
- **SDK README**: `/pscratch/sd/k/krydzy/codex/sdk/typescript/README.md`

## Architecture (Key Non-Obvious Facts)

1. **npm wrapper → Rust binary**: `codex-cli/bin/codex.js` spawns vendored Rust binary from `codex-rs/`
2. **Default: Responses API, NOT Chat Completions** — won't work with vLLM unless `wire_api = "chat"`
3. **Project docs**: `AGENTS.md` (NOT `CLAUDE.md`). Loaded from `~/.codex/`, repo root, cwd
4. **Agent tools**: `shell` (sandboxed bash), `apply_patch` (file editing), `web_search` (optional), MCP servers
5. **Built-in provider "openai" uses `or_insert`** — user `-c` overrides for `model_providers.openai.*` are silently ignored. Use a custom provider name (e.g., `ext`) to override base_url.
6. **`model` and `model_provider` are separate fields** — `model=gpt-4o-mini` (bare name sent in API request) + `model_provider=ext` (routes to provider config). Do NOT use `provider/model` format.

## Installation on Perlmutter

Node.js is available via nvm (no system module). npm global packages install to `$HOME/.nvm/`.

```bash
# nvm should already be sourced in ~/.bashrc
nvm use 22                         # or: nvm install 22
npm install -g @openai/codex
codex --version
```

If `nvm` is not found, source it: `source ~/.nvm/nvm.sh`

Or: download `codex-x86_64-unknown-linux-musl` from GitHub Releases, or `cargo build --release` in `codex-rs/`.

## Non-Interactive Mode (`codex exec`)

**Only mode relevant for benchmarks:**

```bash
codex exec \
  --dangerously-bypass-approvals-and-sandbox \  # No sandbox, no approvals (replaces --yolo)
  --skip-git-repo-check \         # Don't require git repo
  --json \                        # JSONL events to stdout
  --ephemeral \                   # Don't persist session
  -c "KEY=VALUE" \                # Config overrides (repeatable)
  -o result.txt \                 # Final message to file
  "PROMPT"
```

Other flags: `--model/-m`, `--sandbox/-s MODE`, `--cd/-C DIR`, `--add-dir DIR`, `--profile/-p NAME`, `--output-schema schema.json`. Run `codex exec --help` for full list.

## External OpenAI API Configuration (Critical for Perlmutter)

**IMPORTANT**: Must use a custom provider name (not `openai`) due to built-in provider shadow bug.

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

## vLLM Configuration

**#1 gotcha**: Codex defaults to Responses API. vLLM only speaks Chat Completions.

```bash
export OPENAI_API_KEY="dummy"
export CODEX_API_KEY="dummy"

codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check --json --ephemeral \
  -c "model_provider=local-vllm" \
  -c "model_providers.local-vllm.name=local-vllm" \
  -c "model_providers.local-vllm.base_url=http://127.0.0.1:8008/v1" \
  -c "model_providers.local-vllm.env_key=OPENAI_API_KEY" \
  -c "model_providers.local-vllm.wire_api=chat" \
  -c "model=gpt-oss-120b" \
  -c "web_search=disabled" \
  "Your prompt here"
```

Or in `~/.codex/config.toml`:
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

## Sandbox Modes

| Mode | Flag | Behavior |
|------|------|----------|
| read-only | `-s read-only` | Read only; writes need approval |
| workspace-write | `--full-auto` | Read/write in cwd; no network |
| danger-full-access | `--dangerously-bypass-approvals-and-sandbox` | Full access, no restrictions |

**For benchmarks**: Use `--dangerously-bypass-approvals-and-sandbox` — SLURM provides isolation. Landlock may conflict with Lustre.

## HPC Benchmark Setup

Harness scripts go in PATH — no tool registration needed (unlike SWE-agent YAML bundles):

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

For profiling tools, add to PATH: `tools/hpctoolkit/bin`, `tools/hatchet/bin`.

## Collecting Results

| Source | How |
|--------|-----|
| Trajectory | `--json` → JSONL file |
| Final message | `-o result.txt` or stdout |
| Patch | `git diff` after run |
| Structured | `--output-schema schema.json -o output.json` |
| Errors | Filter JSONL for `"type": "error"` |
| Logs | `~/.codex/log/` or `RUST_LOG=codex_core=info` |

## Key Differences from SWE-agent

- **No tool bundles** — shell calls any command in PATH
- **No Jinja2 templates** — all context in prompt or AGENTS.md
- **No submit command** — agent finishes when done
- **Must set `wire_api=chat`** for vLLM (SWE-agent uses litellm)
- **Sandboxed by default** — use `--dangerously-bypass-approvals-and-sandbox` for open mode

## Shell Command Timeout (Critical for HPC Benchmarks)

**Default timeout: 10 seconds** (`DEFAULT_EXEC_COMMAND_TIMEOUT_MS = 10_000` in `codex-rs/core/src/exec.rs:38`). This kills any command that runs longer than 10s. HPC benchmark harnesses (`qs_run`, `lulesh_run`, `kripke_run`, `laghos_run`) need 60-120+ seconds.

**Symptoms of timeout**: `aggregated_output: ""` and `exit_code: null` in the JSONL trajectory. The process is killed silently.

**No CLI override exists.** The timeout can ONLY be set per-command by the model via `LocalShellExecAction.timeout_ms`. There is no CLI flag or `config.toml` field. Rebuilding from Rust source is the only other option.

**Workaround**: Include explicit timeout guidance in the prompt and `AGENTS.md`:
```
CRITICAL: Set timeout_ms: 300000 (5 minutes) for all build/run harness commands.
If a command returns empty output with null exit code, it was killed by timeout.
```

Also set `PYTHONUNBUFFERED=1` in the environment so harness scripts flush output immediately, giving partial output even if timeout occurs.

## Common Issues

1. **API 404/unsupported**: Forgot `wire_api = "chat"` for vLLM
2. **"Not inside a trusted directory"**: Add `--skip-git-repo-check`
3. **Sandbox blocks GPU builds**: Use `--dangerously-bypass-approvals-and-sandbox` on Perlmutter
4. **Agent never finishes**: No submit gate. Add completion instructions in prompt
5. **Session disk bloat**: Use `--ephemeral`
6. **`AGENTS.md` not `CLAUDE.md`**: Codex ignores CLAUDE.md
7. **Lustre + Landlock**: `--dangerously-bypass-approvals-and-sandbox` bypasses Landlock
8. **Built-in provider shadow**: User overrides for `model_providers.openai.*` are silently ignored. Use a custom provider name like `ext`
9. **Regional API endpoint**: If your OpenAI key requires `us.api.openai.com`, you MUST use a custom provider with `base_url` set correctly
10. **Harness commands return empty output**: 10s default timeout is killing the process. See "Shell Command Timeout" section above
