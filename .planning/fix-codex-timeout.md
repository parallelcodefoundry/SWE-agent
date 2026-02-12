# Patch Codex CLI Shell Timeout — Env Var Override + New Default

```
/load-state

Load skills: perlmutter, codex-cli

CONTEXT: Codex CLI has a hardcoded 10s default shell timeout that kills qs_build (~2min)
and qs_run (~4min). The model can set timeout_ms per-command but gpt-4o-mini does so
unreliably. No config key or env var override exists in Codex 0.99.0. We investigated
the source — the fix is minimal.

Local Codex source: /pscratch/sd/k/krydzy/codex/
Binary installed at: ~/.nvm/versions/node/v22.19.0/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex/codex
Binary type: ELF 64-bit, dynamically linked Rust, 81 MB

THE FIX — 3 touch points in codex-rs/core/src/exec.rs:

1. Replace the constant (line 38):
   FROM: pub const DEFAULT_EXEC_COMMAND_TIMEOUT_MS: u64 = 10_000;
   TO:   a function that checks env var CODEX_DEFAULT_EXEC_TIMEOUT_MS,
         falls back to 300_000 (our new default, was 10_000)

2. Update ExecExpiration::wait() (line 101) and timeout_ms() (line 113):
   Replace DEFAULT_EXEC_COMMAND_TIMEOUT_MS references with the new function call.

3. Also check codex-rs/exec-server/src/posix/mcp.rs:116 — references the constant.

PHASE 1 — Patch source:

1. Modify exec.rs: replace constant with env-var-aware function, change default to 300_000.
2. Update any other files referencing DEFAULT_EXEC_COMMAND_TIMEOUT_MS.

PHASE 2 — Build:

3. Check Rust toolchain on Perlmutter (cargo, rustc). Install via rustup if needed.
4. Build the codex binary (likely `cargo build --release` from codex-rs/).
5. Replace the npm-installed binary with the new one.

PHASE 3 — Integrate with benchmark runner:

6. Update batch/frameworks/codex.py (or the shell script it generates) to export
   CODEX_DEFAULT_EXEC_TIMEOUT_MS=300000 before launching codex.
7. This lets us set custom timeout values per-run without rebuilding.

PHASE 4 — Validate:

8. Run `codex --version` to confirm patched binary works.
9. Run E2E Codex/QS benchmark — verify qs_build and qs_run survive (no exit code 124).

AFTER ALL PASS: commit, /save-state
```
