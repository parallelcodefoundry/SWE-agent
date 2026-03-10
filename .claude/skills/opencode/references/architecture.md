# OpenCode Architecture Reference

## Architecture Overview

OpenCode is an open-source, provider-agnostic terminal-based AI coding agent built with **Bun + TypeScript** (monorepo with `turbo`). It uses a client/server architecture where a **Hono HTTP server** handles LLM interaction (via Vercel AI SDK `@ai-sdk/*` adapters), tool execution, and sessions backed by SQLite, while frontends (TUI, web, SDK) connect over HTTP/SSE. **No Docker sandbox** -- commands run directly on the host like SWE-agent local mode.

## Provider Details

Config file: `opencode.json` or `opencode.jsonc`. Schema: `https://opencode.ai/config.json`. Supports 20+ providers via `@ai-sdk/*` adapters (Anthropic, OpenAI, Google, Groq, etc.). For automation, use `OPENCODE_CONFIG_CONTENT` env var (inline JSON, highest priority).

Model format: **`provider-id/model-id`** (e.g., `anthropic/claude-sonnet-4-5-20250929`, `local-vllm/gpt-oss-120b`).

- Config default: `"model": "provider/model"`
- CLI override: `opencode run --model provider/model "message"`

For Ollama: change baseURL to `http://localhost:11434/v1`.

## Built-in Tool System

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

### Custom Tools

Place TypeScript/JS files in `.opencode/tools/*.{ts,js}` -- auto-loaded, filename becomes tool name. See OpenCode docs for the `tool()` API.

## Headless Mode Details (`opencode run`)

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

**Critical behavior:** In `run` mode, the `question` tool is **auto-denied** (no user interaction), `plan_enter`/`plan_exit` are auto-denied, and **all permission requests are auto-rejected** (`run.ts:512-523` publishes `permission.asked` events and auto-replies with `reply: "reject"`). Every tool permission MUST evaluate to "allow" in the ruleset.

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

## Title Generation / Small Model

OpenCode calls a "small model" for session title generation after the first agent step. By default this is `gpt-5-nano` (hardcoded). When serving a different model via vLLM, this 404s and crashes the session.

**Fix:** Set `"small_model": "provider/model-id"` in the config JSON to redirect title gen to the same model being served. The benchmark launcher now adds this automatically.

Source: `packages/opencode/src/provider/provider.ts:1150-1210` (`getSmallModel()`), `packages/opencode/src/session/summary.ts:134-166` (`summarizeMessage()`).

**Caveats:** GitHub issues #2640 and #8609 report `small_model` config doesn't always work reliably. If it fails, alternatives:
1. Set up a model alias on vLLM that maps `gpt-5-nano` to the served model
2. Patch OpenCode source to skip title gen
3. Use `@ai-sdk/openai-compatible` provider

## Session Storage

Session data stored in `~/.local/share/opencode/storage/`. Full tool call details (input, output, error) stored per-part as JSON files. Invaluable for debugging since the JSONL trajectory only captures model text.
