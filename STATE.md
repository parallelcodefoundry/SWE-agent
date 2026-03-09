# STATE.md — Current Project State

Last updated: 2026-03-09 (session 42)

## Last Session (Session 42)

### gptoss120b LLNL Analysis (jobs 49641358-60)

Analyzed SWE-agent, OpenCode, and OpenHands results on gptoss120b model. **0 meaningful speedups across 24 runs.**

**SWE-agent (49641358):** Most active — 107-193 iterations per run. Laghos got 0.997x (pow→x*x, negligible). 3 runs killed by SLURM walltime. QS hit framework bugs (_state_anthropic timeout, FunctionCallingFormatError). Kripke with_profiling had 634K-line patch (build artifacts, not source).

**OpenCode (49641359):** Explored superficially, exited early. 1-12 steps per run. Model gathered info but never edited source code. gptoss120b appears unable to follow through on optimization.

**OpenHands (49641360):** All 8 runs crashed after exactly 1 agent action. Pydantic ValidationError in vLLM harmony_utils — rejects LiteLLM tool result content format. CRITICAL infrastructure bug blocking all OpenHands+gptoss120b.

### Infrastructure Fixes
- **GPA agent launch bug FIXED** — `hpc_benchmark_runner.py` now always runs agent after baseline verification (was skipping in base mode)
- **Workspace cleanup added** — Auto-delete workspace after patch saved. Cleaned 21GB → 181MB.
- **GPA-Benchmark updated** — Merged origin/develop (sanitizer support, linting, driver improvements). All 6 build failures already fixed upstream (CUDA 13 migration, lavaMD case fix, rodinia includes).
- **CLAUDE.md updated** — Documented `bash` vs `sbatch` for run_benchmark.sh
- **Results analysis guide** — `agent_docs/results-analysis.md` with framework-specific log format docs
- **Batch results cleaned** — Deleted Feb 25-26 failed runs, LLNL legacy, stale scripts, all workspaces

### Claude Code gptoss120b LLNL (job 49641364) — Analyzed session 41
| App | Mode | Speedup | Patch | Key Changes |
|-----|------|---------|-------|-------------|
| Kripke | no_profiling | **15.08x** | +40/-5 | `--use_fast_math`, GPU-ify `kConst`/`kCopy`, `RAJA_HOST_DEVICE` |
| Kripke | with_profiling | **11.18x** | +15/-4 | `--use_fast_math`, `--maxrregcount=64`, CHAI enabled |
| Laghos | no_profiling | 1.05x | +14/-41 | CG tol relaxed, remove epsilon zeroing, remove `DEVICE_SYNC` |
| Laghos | with_profiling | 1.07x | +23/-47 | Same + `cg_max_iter=9`, skip redundant `UpdateQuadratureData` |
| Lulesh | with_profiling | 0.95x | +53/-33 | Static allocation caching, MPI single-rank guard |
| Lulesh | no_profiling | N/A | killed | SLURM walltime kill after 161 turns |
| QS | no_profiling | timeout | +29/-26 | Full Makefile rewrite, `sincos()`, remove GPU printf |
| QS | with_profiling | unknown | +0/-0 | .gitignore only |

## Active Experiments

### Qwen LLNL (session 42, resubmitted correctly with `bash`)
| Job ID | Framework | Model | Nodes | Status |
|--------|-----------|-------|-------|--------|
| 49850096 | sweagent | Qwen/Qwen3-Coder-Next-FP8 | 5 | PENDING |
| 49850097 | codex | Qwen/Qwen3-Coder-Next-FP8 | 5 | PENDING |
| 49850098 | opencode | Qwen/Qwen3-Coder-Next-FP8 | 5 | PENDING |
| 49850099 | openhands | Qwen/Qwen3-Coder-Next-FP8 | 5 | PENDING |

### Qwen GPA (session 42)
| Job ID | Framework | Model | Nodes | Status |
|--------|-----------|-------|-------|--------|
| 49850130 | sweagent | Qwen/Qwen3-Coder-Next-FP8 | 2 | PENDING |
| 49850133 | codex | Qwen/Qwen3-Coder-Next-FP8 | 2 | PENDING |
| 49850134 | opencode | Qwen/Qwen3-Coder-Next-FP8 | 2 | PENDING |
| 49850135 | openhands | Qwen/Qwen3-Coder-Next-FP8 | 2 | PENDING |

### Previous Qwen (session 41) — FAILED
Jobs 49653981-84 all failed: `sbatch` bypassed self-submit → 1 node instead of 5.

### gptoss120b GPA (jobs 49641361-63) — NOT USEFUL
Agent never launched (GPA bug). All patches 0/0. 20/32 baseline builds passed, 12 failed. No signal — these predate the GPA fix.

## Branch State

- **Current branch**: `dev` (30 commits ahead of `origin/dev`)
- **Latest commit**: `d7b58711` — Add framework-specific log analysis guide, workspace cleanup

## Infrastructure Bugs Found (session 42)

| Bug | Framework | Severity | Status |
|-----|-----------|----------|--------|
| vLLM harmony_utils Pydantic content mismatch | OpenHands | CRITICAL | Open — blocks all OpenHands+gptoss120b |
| SWE-agent `_state_anthropic` 25s timeout | SWE-agent | HIGH | Open — kills QS runs |
| gptoss120b weak at function calling | SWE-agent | MEDIUM | Model limitation |
| Build artifacts in git patch (634K lines) | SWE-agent | MEDIUM | .gitignore not effective |
| nsys_profile argument parsing fragile | OpenCode | LOW | Open |
| .gitignore-only patch triggers false "success" | All | LOW | Open |

## Persistent Issues
- [ ] **Quicksilver consistent timeout** — All frameworks timeout on QS baseline
- [ ] **Lulesh intractable for agents** — Kernels already well-optimized
- [ ] **Codex gpt-4.1-mini single-turn exit** — Model exits with needs_follow_up=false
- [ ] **OpenHands+gptoss120b Pydantic crash** — vLLM harmony_utils content format bug

## Recent Decisions

- 2026-03-09 (s42): Always use `bash batch/run_benchmark.sh`, never `sbatch` directly
- 2026-03-09 (s42): Auto-cleanup workspaces after patch extraction to prevent GB-scale accumulation
- 2026-03-09 (s42): gptoss120b GPA results (49641361-63) discarded — predated GPA agent launch fix
- 2026-03-04 (s41): Switch SLURM account from m2404 to m5083
- 2026-03-04 (s41): Add profiling tool diversity tip to prompt

## Next Steps

1. **Check Qwen LLNL+GPA results** when 49850096-99, 49850130-35 complete
2. **Fix OpenHands+gptoss120b Pydantic crash** — vLLM harmony_utils content format
3. **Fix SWE-agent _state_anthropic timeout** for long-running apps
4. **Submit Claude Code runs** (LLNL + GPA) — uses Anthropic API, no vLLM needed
