# HANDOFF.md — Session 14 Summary

Last updated: 2026-02-13 (session 14)

## What Was Done

Patched the Codex CLI Rust binary to add `CODEX_DEFAULT_EXEC_TIMEOUT_MS` env var override. Built from source on Perlmutter, replaced npm binary, integrated with benchmark runner, validated E2E with gpt-4o-mini on Quicksilver.

## Goal Progress

- [x] Goal 1: Patch exec.rs — replace constant with env-var-aware function (4 touch points)
- [x] Goal 2: Install Rust toolchain and build Codex binary on Perlmutter
- [x] Goal 3: Replace npm-installed binary with patched one
- [x] Goal 4: Update benchmark runner (codex.py) to export CODEX_DEFAULT_EXEC_TIMEOUT_MS
- [x] Goal 5: Update AGENTS.md guidance (300s default, no manual timeout_ms needed)
- [x] Goal 6: E2E validation — sleep 15 test + full Codex/QS benchmark
- [x] Goal 7: Commit and save state
- [ ] Goal 8: Run full benchmark suite with all 4 frameworks (**NEXT SESSION**)

## Files Modified This Session

| File | Repo | Change |
|------|------|--------|
| `codex-rs/core/src/exec.rs` | codex | Replaced `pub const DEFAULT_EXEC_COMMAND_TIMEOUT_MS: u64 = 10_000` with `pub fn default_exec_command_timeout_ms() -> u64` that checks env var, falls back to 300_000 |
| `codex-rs/exec-server/src/posix/mcp.rs` | codex | Updated reference from constant to function call (line 116) |
| `batch/frameworks/codex.py` | SWE-agent | Added `export CODEX_DEFAULT_EXEC_TIMEOUT_MS=300000`, updated AGENTS.md guidance |
| `.claude/` skills/agents/rules | SWE-agent | Reference file updates (cosmetic) |
| `STATE.md` | SWE-agent | Updated with session 14 results |
| `.planning/HANDOFF.md` | SWE-agent | This file |

## Files to Read First Next Session

1. `STATE.md` — Full state overview
2. `.planning/HANDOFF.md` — This file
3. `batch/run_benchmark.sh` — To understand how to launch full benchmark suite

## Key Context for Full Benchmark Suite

### What's Ready

All 4 frameworks have been individually validated:
- **SWE-agent** — Baseline framework, works but has whitespace patch issues
- **Codex CLI** — Timeout patched (session 14), E2E validated with gpt-4o-mini
- **OpenCode** — Permission fix works (session 12), but exits non-zero on normal completion
- **OpenHands** — Guardrails work (session 12), but still deletes some non-essential Makefiles

### Running Full Suite

```bash
# All 4 apps, all curated commits, with Codex framework:
sbatch batch/run_benchmark.sh --framework codex --external-model --model-name openai/gpt-4o-mini

# Single app:
sbatch batch/run_benchmark.sh --quicksilver --framework codex --external-model --model-name openai/gpt-4o-mini

# All 4 frameworks would need 4 separate runs (one per framework)
```

### Rust Toolchain on Perlmutter

Installed at `~/.cargo/bin/` with these symlinks for build tools:
- `cc` → `/opt/cray/pe/gcc-native/13/bin/gcc`
- `ar` → `/usr/bin/ar`
- `pkg-config` → `/usr/bin/pkg-config`

If Codex needs a rebuild: `CC=/opt/cray/pe/gcc-native/13/bin/gcc PATH="$HOME/.cargo/bin:$PATH" cargo build --release -p codex-cli --manifest-path /pscratch/sd/k/krydzy/codex/codex-rs/Cargo.toml`

## Gotchas for Next Session

1. **Codex version shows 0.0.0** — Expected; we built from source with workspace `version = "0.0.0"`. The npm package was 0.99.0. Functionally identical.
2. **Original binary backed up** — At the same install path with `.bak` suffix (81MB vs patched 68MB).
3. **Codex source is a separate git repo** — Changes committed at `/pscratch/sd/k/krydzy/codex/` (commit `272184359`), not in the SWE-agent repo.
4. **Login node has gcc-13 but not in default PATH for cargo** — The `~/.cargo/bin/cc` symlink handles this.
5. **OpenSSL available at `/usr`** — No special `OPENSSL_DIR` needed, just `pkg-config` in PATH.

## Branch State

- **Current branch**: `local`
- **Latest commit**: `55df28a6` — WIP: Update skills, agents, and rules references
- **Previous commit**: `7548b391` — Fix Codex 10s shell timeout
