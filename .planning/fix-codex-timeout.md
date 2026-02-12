# Patch Codex CLI Default Shell Timeout (10s → 300s)

```
/load-state

Load skills: perlmutter, codex-cli

CONTEXT: Codex CLI has a hardcoded 10s default shell timeout that kills qs_build (~2min)
and qs_run (~4min). The model can set timeout_ms per-command but gpt-4o-mini does so
unreliably (~50%). We need to patch the default to 300s. See GitHub issues #7353, #7084.

The constant: DEFAULT_EXEC_COMMAND_TIMEOUT_MS = 10_000 in codex-rs/core/src/exec.rs:38
Installed: codex-cli 0.99.0 via npm at ~/.nvm/versions/node/v22.19.0/bin/codex

PHASE 1 — Investigate override options:

1. Check if Codex 0.99.0 has a config key or env var for shell timeout (check schema,
   docs, recent commits). If a non-source fix exists, use it instead of rebuilding.

PHASE 2 — Patch and rebuild (if no config override):

2. Clone openai/codex repo, checkout tag matching v0.99.0.
3. Check Rust toolchain availability on Perlmutter (cargo, rustc). Install if needed.
4. Change DEFAULT_EXEC_COMMAND_TIMEOUT_MS from 10_000 to 300_000 in exec.rs.
5. Build the Rust crate (codex-rs/core or the full CLI binary).
6. Replace the binary in the npm installation path.

PHASE 3 — Validate:

7. Run `codex --version` to confirm patched binary works.
8. Run a quick E2E Codex/QS benchmark to verify long commands survive.

AFTER ALL PASS: commit, /save-state
```
