---
name: opencode
description: "OpenCode terminal AI agent configuration and benchmarking. Use when user mentions 'opencode', OpenCode providers, Bun/TypeScript agent, or OpenCode benchmark automation."
---

# OpenCode

## Source Location

- **Local clone:** `/pscratch/sd/k/krydzy/opencode/`
- **Main repo:** https://github.com/opencode-ai/opencode
- **Documentation:** https://opencode.ai/docs

## Installation on Perlmutter

```bash
nvm use 22                         # or: nvm install 22
npm i -g opencode-ai@latest
opencode --version
```

If `nvm` is not found: `source ~/.nvm/nvm.sh`

## Provider Configuration

Config file: `opencode.json` or `opencode.jsonc`. For automation, use `OPENCODE_CONFIG_CONTENT` env var.

**Local vLLM example:**
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

## Headless Mode (`opencode run`)

```bash
opencode run [message..] [flags]
```

Key flags: `--model/-m provider/model`, `--format json`, `--continue/-c`, `--file/-f path`, `--title "text"`.

**CRITICAL -- Permission config format:** Use `"permission": {"*": "allow"}` (object form), NOT `"permission": "allow"` (string). The string form causes `Object.entries("allow")` to split into per-character rules, breaking all tools with Zod validation errors.

**CRITICAL -- Headless auto-reject:** `opencode run` auto-rejects all `permission.asked` events. ALL permissions must evaluate to "allow" in the ruleset, never "ask".

## HPC Benchmark Setup

```bash
module load python cmake openmpi/5.0.7 cuda/12.4
export PATH="/pscratch/sd/k/krydzy/SWE-agent/tools/kripke_harness/bin:$PATH"
export KRIPKE_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Kripke_test
export OPENCODE_CONFIG_CONTENT='{
  "provider": { "local-vllm": { ... } },
  "model": "local-vllm/gpt-oss-120b",
  "permission": {"*": "allow"}
}'

cd "$KRIPKE_ROOT"
opencode run --format json --model local-vllm/gpt-oss-120b --title "Kripke Opt" \
  "Optimize Kripke for A100. Use kripke_build/kripke_run --arch CUDA." \
  > output.jsonl 2>&1
```

## Debugging Tool Errors

JSONL trajectory only captures model text. For actual tool errors:
1. **Session storage**: `~/.local/share/opencode/storage/part/` -- full tool call details per-part as JSON
2. **OpenCode logs**: `~/.local/share/opencode/log/` -- permission ruleset and startup diagnostics

## Common Issues

1. **Permission string bug**: Use `{"*": "allow"}` not `"allow"`. See critical note above.
2. **Permission auto-reject in headless mode**: All permissions must be "allow", never "ask".
3. **No submit command**: Use `steps` limit and check `git diff` for final state.
4. **Bash timeout**: Set `OPENCODE_EXPERIMENTAL_BASH_DEFAULT_TIMEOUT_MS` for long builds.
5. **Skill scanning**: OpenCode scans `.claude` and `.agents` for `skills/**/SKILL.md`.

For detailed reference, see references/ in this skill directory.
