# STATE.md — Current Project State

Last updated: 2026-02-13 (session 14)

## Active Experiments

None. Codex timeout patch complete and validated.

## Current Focus

**Full benchmark suite** — All framework integrations (SWE-agent, Codex, OpenCode, OpenHands) are now functional. Next step is running the full benchmark suite across all 4 frameworks on all 4 apps.

## Last Session (Session 14)

### Codex CLI Shell Timeout Patch — COMPLETE

Patched the Codex CLI Rust binary to support `CODEX_DEFAULT_EXEC_TIMEOUT_MS` env var override. Changed hardcoded 10s default to 300s. Rebuilt from source, replaced npm binary, validated E2E.

| Phase | Status | Details |
|-------|--------|---------|
| Source patch | **DONE** | 4 touch points: `exec.rs` (constant→fn, 2 call sites), `mcp.rs` (1 call site) |
| Build | **DONE** | Installed Rust 1.93.1 via rustup, built release binary (68MB) on login node |
| Benchmark integration | **DONE** | `batch/frameworks/codex.py` exports `CODEX_DEFAULT_EXEC_TIMEOUT_MS=300000` |
| E2E validation | **DONE** | gpt-4o-mini completed full build-explore-edit-rebuild cycle (+7/-32 lines) |

### Validation Results

| Test | Job ID | Result | Details |
|------|--------|--------|---------|
| `sleep 15` through Codex | 48887761 | **PASS** | Would fail at 10s default; completed with 300s timeout |
| E2E Codex/QS base mode | 48887817 | **PASS** | qs_build exit 0, qs_run completed, agent made changes, 249.1s total |

### Build Environment Notes

| Item | Detail |
|------|--------|
| Rust toolchain | `~/.cargo/bin/` — rustc/cargo 1.93.1, installed via rustup |
| Build workarounds | `cc` symlink → `/opt/cray/pe/gcc-native/13/bin/gcc`, `ar` symlink → `/usr/bin/ar`, `pkg-config` symlink → `/usr/bin/pkg-config` in `~/.cargo/bin/` |
| Cargo config | `/pscratch/sd/k/krydzy/codex/codex-rs/.cargo/config.toml` — linker set to gcc-13 |
| Built binary | `/pscratch/sd/k/krydzy/codex/codex-rs/target/release/codex` (68MB) |
| Installed binary | `~/.nvm/versions/node/v22.19.0/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/codex/codex` |
| Original backup | Same path with `.bak` suffix (81MB) |

### Commits

- `7548b391` — Fix Codex 10s shell timeout: export CODEX_DEFAULT_EXEC_TIMEOUT_MS=300000
- `55df28a6` — WIP: Update skills, agents, and rules references
- Codex repo (`/pscratch/sd/k/krydzy/codex/`): `272184359` — Add CODEX_DEFAULT_EXEC_TIMEOUT_MS env var override

## Recent Decisions

- 2026-02-13 (s14): Default timeout changed from 10s to 300s (not just env var — the fallback itself is 300s)
- 2026-02-13 (s14): Env var name `CODEX_DEFAULT_EXEC_TIMEOUT_MS` (matches the internal constant name pattern)
- 2026-02-13 (s14): Build Codex on login node (gcc-13 available), not compute node — saves allocation time
- 2026-02-13 (s14): Rust toolchain installed at `~/.cargo/bin/` with symlinks for cc/ar/pkg-config
- 2026-02-13 (s14): Updated AGENTS.md guidance to reflect 300s default (agent no longer needs to set timeout_ms manually)
- 2026-02-12 (s13): Remove `HAVE_ASYNC_MPI` — OpenMPI 5 non-blocking collectives broken with QS
- 2026-02-12 (s13): Use temp input files for domain decomposition (QS input overrides CLI)
- 2026-02-12 (s13): Use `--oversubscribe` with mpirun (PRRTE sees only 1 slot from SLURM srun)
- 2026-02-12 (s13): Keep QS pristine on `master` (not `dev`)
- 2026-02-12 (s12): Merged `fix-agent-execution` into `local` after all 3 validations passed
- 2026-02-12 (s11): Use object form `{"*": "allow"}` for OpenCode permission
- 2026-02-12 (s11): Add CODEX_TIMEOUT_GUIDANCE to prompt (model sets timeout_ms: 300000)
- 2026-02-12 (s10): Use custom Codex provider name `ext` (not `openai`)

## Completed Experiments

| Name | Job ID | Result |
|------|--------|--------|
| **Codex timeout E2E (s14)** | 48887817 | **PASS** — gpt-4o-mini built+ran+edited QS, 249.1s |
| **Codex sleep 15 test (s14)** | 48887761 | **PASS** — 15s sleep survived (would die at 10s default) |
| QS multi-GPU validation (s13) | 48820324 | PASS — 4 GPUs, 4 ranks, 700 values correct |
| E2E Codex/QS pipeline (s13) | 48820324 | PASS (infra) — pipeline works, agent unproductive (timeout) |
| Codex/QS fix validation (s12) | 48817293 | PASS — 483.8s, timeout fix works |
| OpenCode/QS fix validation (s12) | 48817295 | PASS — Permission fix works |
| OpenHands/Lulesh fix validation (s12) | 48817669 | PASS — +1/-130 lines, guardrails work |
| Codex/Quicksilver (s9) | 48811735 | PASS — 141s, agent worked |
| OpenHands/Lulesh (s9) | 48812701 | PASS — 151s, agent worked |
| OpenCode/Quicksilver (ext model) | 48809130 | PASS — framework works |

## Uncommitted Changes

None. All changes committed on `local` branch.

## Open Issues

- ~~**Codex 10s shell timeout**~~ — **RESOLVED** (session 14)
- **OpenCode exits non-zero on normal completion** — benchmark runner marks as failed
- **OpenHands still deletes some non-essential Makefiles** — guardrails partial
- **SWE-agent whitespace patches** — agent reformats code instead of optimizing
- SWE-agent doubled path bug: workspace ends in `/cuda` + git diff gives `cuda/src/...`
- vLLM model cache incomplete — needs HF_TOKEN

## Next Steps

1. **Run full benchmark suite** with all 4 frameworks on all 4 apps (curated commits)
2. **Phase 2: GPA-Benchmark + SWE-fficiency integration**
3. **Phase 3: Restructure repo with submodules**
