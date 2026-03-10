# Codex CLI Internals Reference

## Rust Architecture

The Codex CLI is a Rust binary (`codex-rs/`) wrapped by an npm package (`codex-cli/bin/codex.js`). The npm wrapper spawns the vendored Rust binary.

Key source files:
- `codex-rs/core/src/exec.rs` -- Shell command execution, `default_exec_command_timeout_ms()` function (was constant)
- `codex-rs/exec-server/src/posix/mcp.rs` -- MCP exec server, references the timeout function
- `codex-rs/core/config.schema.json` -- Full config schema
- `codex-rs/core/src/config/mod.rs` -- Config loading, built-in provider `or_insert` at line ~1521

## Shell Timeout Patch Details

**Patched in session 14 (2026-02-13).** The constant `DEFAULT_EXEC_COMMAND_TIMEOUT_MS = 10_000` was replaced with a function:

```rust
pub fn default_exec_command_timeout_ms() -> u64 {
    std::env::var("CODEX_DEFAULT_EXEC_TIMEOUT_MS")
        .ok()
        .and_then(|v| v.parse::<u64>().ok())
        .unwrap_or(300_000)
}
```

4 touch points:
1. `exec.rs:40` -- Function definition (was constant)
2. `exec.rs:108` -- `ExecExpiration::wait()` DefaultTimeout arm
3. `exec.rs:117` -- `ExecExpiration::timeout_ms()` DefaultTimeout arm
4. `mcp.rs:116` -- MCP exec server fallback timeout

## Binary Locations

| Binary | Path |
|--------|------|
| Installed (patched) | `~/.nvm/versions/node/v22.19.0/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex/codex` |
| Original backup | Same path with `.bak` suffix |
| Built release | `/pscratch/sd/k/krydzy/codex/codex-rs/target/release/codex` |

## Rebuilding on Perlmutter

Rust toolchain installed at `~/.cargo/bin/` (rustc/cargo 1.93.1). Symlinks for build tools are already in place.

```bash
# Build (can run on login node — gcc-13 available)
CC=/opt/cray/pe/gcc-native/13/bin/gcc \
PATH="$HOME/.cargo/bin:$PATH" \
cargo build --release -p codex-cli \
  --manifest-path /pscratch/sd/k/krydzy/codex/codex-rs/Cargo.toml

# Replace npm binary
CODEX_BIN="$HOME/.nvm/versions/node/v22.19.0/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex/codex"
cp /pscratch/sd/k/krydzy/codex/codex-rs/target/release/codex "$CODEX_BIN"
```

Build prerequisites (already set up in `~/.cargo/bin/`):
- `cc` symlink -> `/opt/cray/pe/gcc-native/13/bin/gcc`
- `ar` symlink -> `/usr/bin/ar`
- `pkg-config` symlink -> `/usr/bin/pkg-config`
- Cargo config at `codex-rs/.cargo/config.toml` sets linker to gcc-13

## API Format

- **Default**: Responses API (OpenAI native)
- **Chat Completions**: `wire_api = "chat"` is **permanently removed** — `WireApi` enum only has `Responses` variant. Attempting `wire_api=chat` throws `CHAT_WIRE_API_REMOVED_ERROR` at deserialization.
- Agent tools: `shell` (sandboxed bash), `apply_patch` (file editing), `web_search` (optional), MCP servers

### Codex + Qwen/vLLM Incompatibility

**Codex + Qwen via vLLM is permanently broken.** Codex requires `wire_api=responses` (only option). vLLM's `qwen3_coder` tool call parser only works on `/v1/chat/completions`, not `/v1/responses`. Qwen's XML tool calls (`<function=name>`) pass through as plain text on the Responses endpoint — Codex sees no tools and exits after 1 turn.

**Use first-party OpenAI models only with Codex** (gpt-5.3-codex, gpt-5.2-codex, o3, o4-mini). These use the built-in `openai` provider with native Responses API support.

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
export CODEX_DEFAULT_EXEC_TIMEOUT_MS=300000

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

1. **wire_api=chat removed**: `chat` wire API is permanently gone. Only `responses` works. Use first-party OpenAI models, not vLLM
2. **"Not inside a trusted directory"**: Add `--skip-git-repo-check`
3. **Sandbox blocks GPU builds**: Use `--dangerously-bypass-approvals-and-sandbox` on Perlmutter
4. **Agent never finishes**: No submit gate. Add completion instructions in prompt
5. **Session disk bloat**: Use `--ephemeral`
6. **`AGENTS.md` not `CLAUDE.md`**: Codex ignores CLAUDE.md
7. **Lustre + Landlock**: `--dangerously-bypass-approvals-and-sandbox` bypasses Landlock
8. **Built-in provider shadow**: User overrides for `model_providers.openai.*` are silently ignored. Use a custom provider name like `ext`
9. **Regional API endpoint**: If your OpenAI key requires `us.api.openai.com`, you MUST use a custom provider with `base_url` set correctly
10. **npm update overwrites binary**: After `npm update`, re-run the rebuild steps above
