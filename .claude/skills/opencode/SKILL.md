---
name: opencode
description: "Knowledge about the OpenCode terminal-based coding agent including configuration, benchmark automation, result collection, and differences from other frameworks. Load when creating or modifying OpenCode benchmarks."
---

# OpenCode

## Source Location

- **Local clone:** `/pscratch/sd/k/krydzy/opencode/`
- **Main repo:** https://github.com/opencode-ai/opencode (actual org: `anomalyco/opencode`)
- **Documentation:** https://opencode.ai/docs
- **npm package:** `opencode-ai`

## Architecture Overview

OpenCode is an open-source, provider-agnostic terminal-based AI coding agent built with **Bun + TypeScript** (monorepo with `turbo`). It uses a client/server architecture where a **Hono HTTP server** handles LLM interaction (via Vercel AI SDK `@ai-sdk/*` adapters), tool execution, and sessions backed by SQLite, while frontends (TUI, web, SDK) connect over HTTP/SSE. **No Docker sandbox** -- commands run directly on the host like SWE-agent local mode.

## Installation on Perlmutter

Node.js is available via nvm (no system module). npm global packages install to `$HOME/.nvm/`.

```bash
# nvm should already be sourced in ~/.bashrc
nvm use 22                         # or: nvm install 22
npm i -g opencode-ai@latest
opencode --version
```

If `nvm` is not found, source it: `source ~/.nvm/nvm.sh`

## Provider Configuration

Config file: `opencode.json` or `opencode.jsonc`. Schema: `https://opencode.ai/config.json`. Supports 20+ providers via `@ai-sdk/*` adapters (Anthropic, OpenAI, Google, Groq, etc.). For automation, use `OPENCODE_CONFIG_CONTENT` env var (inline JSON, highest priority).

**Local vLLM example** (our standard setup):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "local-vllm": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://127.0.0.1:8008/v1", "apiKey": "dummy" },
      "models": { "gpt-oss-120b": { "name": "GPT-OSS 120B" } }
    }
  },
  "model": "local-vllm/gpt-oss-120b"
}
```

For Ollama: change baseURL to `http://localhost:11434/v1`.

## Model Selection

Format: **`provider-id/model-id`** (e.g., `anthropic/claude-sonnet-4-5-20250929`, `local-vllm/gpt-oss-120b`).

- Config default: `"model": "provider/model"`
- CLI override: `opencode run --model provider/model "message"`

## Built-in Tools

| Tool | Description | SWE-agent Equivalent |
|------|-------------|---------------------|
| `bash` | Execute shell commands | `bash` |
| `read` | Read file contents | `open` / `scroll_down/up` |
| `edit` | Exact string replacement | `str_replace_editor` |
| `write` | Create/overwrite files | `create` |
| `glob` | Find files by pattern | `find_file` |
| `grep` | Regex content search | `search_dir` / `search_file` |
| `list` | List directory contents | `ls` |
| `webfetch` | Fetch web content | -- |
| `task` | Spawn subagent | -- |
| `question` | Ask user (disabled in `run` mode) | -- |

## Custom Tools

Place TypeScript/JS files in `.opencode/tools/*.{ts,js}` -- they are auto-loaded and the filename becomes the tool name. See OpenCode docs for the `tool()` API.

## Headless Mode (`opencode run`)

Runs a single prompt without the TUI -- primary mechanism for automation:

```bash
opencode run [message..] [flags]
```

**Key flags:**

| Flag | Description |
|------|-------------|
| `--model/-m provider/model` | Override model |
| `--agent name` | Use specific agent |
| `--format json` | JSON event stream output |
| `--continue/-c` | Continue last session |
| `--file/-f path` | Attach file(s) |
| `--title "text"` | Set session title |
| `--variant name` | Reasoning effort variant |

**Critical behavior:** In `run` mode, the `question` tool is **auto-denied** (no user interaction), `plan_enter`/`plan_exit` are auto-denied, and **all permission requests are auto-rejected** (`run.ts:512-523` publishes `permission.asked` events and auto-replies with `reply: "reject"`). Every tool permission MUST evaluate to "allow" in the ruleset — anything that evaluates to "ask" gets rejected.

**CRITICAL — Permission config format:** Use `"permission": {"*": "allow"}` (object form), NOT `"permission": "allow"` (string). The `OPENCODE_CONFIG_CONTENT` env var is merged via `JSON.parse()` without Zod schema validation (`config.ts:179`), so the `permissionTransform` that converts `"allow"` → `{"*": "allow"}` never runs. The raw string `"allow"` gets split by `Object.entries()` into per-character rules with invalid action values (`"a"`, `"l"`, `"l"`, `"o"`, `"w"`), causing all tools to fail with Zod validation errors.

## JSON Output (`--format json`)

Each line is a JSON event. Event types: `tool_use`, `text`, `step_start`, `step_finish`, `error`.

## Key Differences from SWE-agent

| Aspect | SWE-agent | OpenCode |
|--------|-----------|----------|
| **Language** | Python | TypeScript/Bun |
| **LLM interface** | `litellm` | Vercel AI SDK (`@ai-sdk/*`) |
| **Config format** | YAML (Jinja2 templates) | JSON/JSONC (static) |
| **Tool definition** | YAML bundles + shell scripts | TS files in `.opencode/tools/` or just bash |
| **Task input** | Template vars (`{{working_dir}}`) | Flat string prompt |
| **Prompt control** | Full template system | Agent `prompt` field only |
| **Sandbox** | Local or Docker | Host-only |
| **Headless mode** | `sweagent run --config ...` | `opencode run "message"` |
| **Output format** | Trajectory JSON + patches | JSONL events + git diff |
| **Cost control** | `per_instance_cost_limit` | `steps` limit only |
| **Custom tools** | Registered via YAML bundles | Bash calls anything in PATH |
| **Submit signal** | `submit` command | None -- agent stops when done or hits step limit |

**Key implications:** No tool bundles needed (bash calls harness scripts in PATH). No template variables (all context goes in prompt). No submit mechanism (use `steps` limit, check `git diff`). Model format: `provider-id/model-id` not litellm's `openai/openai/model`.

## Setting Up HPC Benchmarks

Use `opencode run` with inline config and harness scripts in PATH:

```bash
#!/bin/bash
# benchmark_opencode.sh -- single HPC optimization task
module load python cmake openmpi/5.0.7 cuda/12.4

APP_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Kripke_test
HARNESS_BIN=/pscratch/sd/k/krydzy/SWE-agent/tools/kripke_harness/bin
export PATH="$HARNESS_BIN:$PATH"
export KRIPKE_ROOT="$APP_ROOT"
export CUDA_VISIBLE_DEVICES="0,1,2,3"

cd /pscratch/sd/k/krydzy/SWE-agent && ./scripts/reset_test_repos.sh --kripke

export OPENCODE_CONFIG_CONTENT='{
  "provider": {
    "local-vllm": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://127.0.0.1:8008/v1", "apiKey": "dummy" },
      "models": { "gpt-oss-120b": { "name": "GPT-OSS 120B" } }
    }
  },
  "model": "local-vllm/gpt-oss-120b",
  "permission": {"*": "allow"}
}'

cd "$APP_ROOT"
opencode run --format json --model local-vllm/gpt-oss-120b --title "Kripke Opt" \
  "Optimize Kripke for NVIDIA A100 GPUs. Use --arch CUDA for all builds/runs.
Available tools: kripke_build --arch CUDA, kripke_run --arch CUDA.
Workflow: build baseline, run baseline, explore code, optimize, rebuild, test." \
  > output.jsonl 2>&1
```

For SDK-based or server-attach approaches, see full docs at https://opencode.ai/docs.

## Debugging Tool Errors

The JSONL trajectory from `--format json` only captures model text, NOT tool call results or errors. To see actual tool errors:

1. **Session storage**: `~/.local/share/opencode/storage/part/` — Full tool call details (input, output, error) stored per-part as JSON files. Look for `"status": "error"` entries.
2. **OpenCode logs**: `~/.local/share/opencode/log/` — Contains full permission ruleset and startup diagnostics.

## Common Issues

1. **Bun unavailable:** Use `module load nodejs` and install via npm.
2. **Permission string bug (all tools fail with Zod errors):** `"permission": "allow"` (string) causes `Object.entries("allow")` to split into per-character rules `{action:"a"}, {action:"l"}, ...` — invalid Zod enum values. Fix: use `"permission": {"*": "allow"}` (object form). See "Critical — Permission config format" above.
3. **Permission auto-reject in headless mode:** `opencode run` auto-rejects all `permission.asked` events at `run.ts:512-523`. ALL permissions must evaluate to "allow" in the ruleset, never "ask".
4. **No step template:** Agent sees raw tool output; make harness scripts output clear text.
5. **No submit command:** Use `steps` limit and check `git diff` for final state.
6. **Bash timeout:** Set `OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS` for long builds.
7. **Skill scanning:** OpenCode scans `EXTERNAL_DIRS = [".claude", ".agents"]` for `skills/**/SKILL.md`, adding `external_directory` permission rules per skill dir.
8. **JSONL trajectory incomplete:** Use `~/.local/share/opencode/storage/part/` to see actual tool call errors (see "Debugging Tool Errors" above).
