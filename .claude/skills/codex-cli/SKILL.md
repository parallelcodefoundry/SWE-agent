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

## Installation on Perlmutter

```bash
module load nodejs
npm install -g @openai/codex
codex --version
```

Or: download `codex-x86_64-unknown-linux-musl` from GitHub Releases, or `cargo build --release` in `codex-rs/`.

## Non-Interactive Mode (`codex exec`)

**Only mode relevant for benchmarks:**

```bash
codex exec \
  --yolo \                        # No sandbox, no approvals
  --skip-git-repo-check \         # Don't require git repo
  --json \                        # JSONL events to stdout
  --ephemeral \                   # Don't persist session
  -c "KEY=VALUE" \                # Config overrides (repeatable)
  -o result.txt \                 # Final message to file
  "PROMPT"
```

Other flags: `--model/-m`, `--sandbox/-s MODE`, `--cd/-C DIR`, `--add-dir DIR`, `--profile/-p NAME`, `--output-schema schema.json`. Run `codex exec --help` for full list.

## vLLM Configuration (Critical)

**#1 gotcha**: Codex defaults to Responses API. vLLM only speaks Chat Completions.

```bash
export OPENAI_API_KEY="dummy"
export CODEX_API_KEY="dummy"

codex exec --yolo --skip-git-repo-check --json --ephemeral \
  -c "model_providers.local-vllm.base_url=http://127.0.0.1:8008/v1" \
  -c "model_providers.local-vllm.env_key=OPENAI_API_KEY" \
  -c "model_providers.local-vllm.wire_api=chat" \
  -c "model=local-vllm/gpt-oss-120b" \
  -c "web_search=disabled" \
  "Your prompt here"
```

Or in `~/.codex/config.toml`:
```toml
model = "local-vllm/gpt-oss-120b"
web_search = "disabled"
[model_providers.local-vllm]
base_url = "http://127.0.0.1:8008/v1"
env_key = "OPENAI_API_KEY"
wire_api = "chat"
```

## Sandbox Modes

| Mode | Flag | Behavior |
|------|------|----------|
| read-only | `-s read-only` | Read only; writes need approval |
| workspace-write | `--full-auto` | Read/write in cwd; no network |
| danger-full-access | `--yolo` | Full access, no restrictions |

**For benchmarks**: Use `--yolo` — SLURM provides isolation. Landlock may conflict with Lustre.

## HPC Benchmark Setup

Harness scripts go in PATH — no tool registration needed (unlike SWE-agent YAML bundles):

```bash
export PATH="/pscratch/sd/k/krydzy/SWE-agent/tools/kripke_harness/bin:$PATH"
export KRIPKE_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Kripke_test

cd "$KRIPKE_ROOT"
codex exec --yolo --skip-git-repo-check --json --ephemeral \
  -c "model_providers.local-vllm.base_url=http://127.0.0.1:8008/v1" \
  -c "model_providers.local-vllm.env_key=OPENAI_API_KEY" \
  -c "model_providers.local-vllm.wire_api=chat" \
  -c "model=local-vllm/gpt-oss-120b" \
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
- **Sandboxed by default** — use `--yolo` for open mode

## Common Issues

1. **API 404/unsupported**: Forgot `wire_api = "chat"` for vLLM
2. **"Not inside a trusted directory"**: Add `--skip-git-repo-check`
3. **Sandbox blocks GPU builds**: Use `--yolo` on Perlmutter
4. **Agent never finishes**: No submit gate. Add completion instructions in prompt
5. **Session disk bloat**: Use `--ephemeral`
6. **`AGENTS.md` not `CLAUDE.md`**: Codex ignores CLAUDE.md
7. **Lustre + Landlock**: `--yolo` bypasses Landlock
