# STATE.md — Current Project State

Last updated: 2026-03-04 (session 41)

## Last Session (Session 41)

### Claude Code Results Analysis

Deep-dived into Claude Code benchmark results from jobs 49641364 (LLNL) and 49641366 (GPA).

**LLNL Results (job 49641364):**

| App | with_profiling | no_profiling |
|-----|---------------|-------------|
| **Kripke** | 11.18x (+15/-4) | 15.08x (+40/-5) |
| **Laghos** | 1.07x (+23/-47) | 1.05x (+14/-41) |
| **Lulesh** | 0.95x (+53/-33) | **killed** (context exhaustion) |
| **Quicksilver** | .gitignore only (+0/-0) | timeout (+29/-26) |

Key findings:
- **Kripke no_profiling (15.08x) beat with_profiling (11.18x)** — `--maxrregcount=64` in profiling run likely hurt. Without profiling, Claude made bolder changes (GPU-ifying host-only functions)
- **Laghos patches nearly identical** between modes — core insight (remove epsilon zeroing, remove device sync) found without profiling
- **Lulesh with_profiling**: 9 real profiling calls (4 nsys + 4 ncu + 1 other), all succeeded. Claude did thorough per-kernel analysis but kernels were already well-optimized (252 regs, 9.6% occupancy). Optimization rabbit hole with reverts.
- **Lulesh no_profiling**: Killed after 161 turns, autocompact at 162K tokens, mid-`lulesh_run` call. Exit code 6 from srun step.
- **Claude never used hpc_profile or hatchet_analyze** — exclusively nsys/ncu across all 8 runs

**GPA Results (job 49641366): BROKEN — Agent never launched**
- Benchmark runner only ran baseline verification (build+run+validate), never invoked Claude Code
- 10/16 apps built and validated successfully, but all show +0/-0 (no agent optimization)
- 6 apps failed baseline: exatensor, xsbench, b+tree, backprop, srad (build failures), lavaMD (config case sensitivity)
- Total GPA run took <2 minutes (just sequential baseline checks)
- **Root cause**: Bug in GPA benchmark flow — runs "base mode verify baselines" but never launches agent

### Infrastructure Changes
- **SLURM account switch**: `m2404` → `m5083` across 10 files (batch scripts, configs, docs, rules, agents, skills)
- **Prompt improvement**: Added tip in `PROFILING_DESCRIPTION` encouraging tool diversity when one profiling approach isn't yielding insights
- **Qwen re-submission**: 4 jobs submitted (49653981-84) with fixed code on m5083
- **Results summary updated**: Added gptoss120b entries (jobs 49641358-60, 49641364) to `batch_results/results_summary.json`
- **Heatmaps regenerated**: `analysis/plot_results.py` — new `speedup_heatmap_s41.png` + updated `speedup_heatmap_all.png`

## Active Experiments

### Claude Code gptoss120b LLNL Results (job 49641364) — ANALYZED
| App | Mode | Speedup | Patch | Key Changes |
|-----|------|---------|-------|-------------|
| Kripke | no_profiling | **15.08x** | +40/-5 | `--use_fast_math`, GPU-ify `kConst`/`kCopy` with `cuda_exec<256>`, `RAJA_HOST_DEVICE` |
| Kripke | with_profiling | **11.18x** | +15/-4 | `--use_fast_math`, `--maxrregcount=64`, CHAI enabled |
| Laghos | no_profiling | 1.05x | +14/-41 | CG tol relaxed, remove epsilon zeroing, remove `DEVICE_SYNC` |
| Laghos | with_profiling | 1.07x | +23/-47 | Same + `cg_max_iter=9`, skip redundant `UpdateQuadratureData` |
| Lulesh | with_profiling | 0.95x | +53/-33 | Static allocation caching, MPI single-rank guard |
| Lulesh | no_profiling | N/A | killed | Context exhaustion after 161 turns |
| QS | no_profiling | timeout | +29/-26 | Full Makefile rewrite, `sincos()`, remove GPU printf |
| QS | with_profiling | unknown | +0/-0 | .gitignore only |

### Claude Code GPA Results (job 49641366) — BROKEN
- Agent never launched. Baseline verification only. Need to fix GPA agent launch flow.

### Other gptoss120b Results
| Job ID | Framework | Apps | Status |
|--------|-----------|------|--------|
| 49641358 | sweagent | LLNL | Real changes (Laghos pow→mul, 0.997x) |
| 49641359 | opencode | LLNL | Connected, no source changes |
| 49641360 | openhands | LLNL | Pydantic crash mid-session |
| 49641361-63 | sweagent/opencode/openhands | GPA | Not yet analyzed |

### Qwen Re-submission (session 41, m5083 account)
| Job ID | Framework | Model | Status |
|--------|-----------|-------|--------|
| 49653981 | sweagent | Qwen/Qwen3-Coder-Next-FP8 | PENDING |
| 49653982 | codex | Qwen/Qwen3-Coder-Next-FP8 | PENDING |
| 49653983 | opencode | Qwen/Qwen3-Coder-Next-FP8 | PENDING |
| 49653984 | openhands | Qwen/Qwen3-Coder-Next-FP8 | PENDING |

### Deleted (Session 40 Cleanup)
- 49641327, 49641343 — SWE-agent setup failures
- 49641328-30, 49641344-46 — Duplicate gptoss120b runs (intended Qwen)

## Branch State

- **Current branch**: `dev` (26 commits ahead of `origin/dev`)
- **Latest commit**: `7b5836de` — Save session 41 state

## All Infrastructure Fixes — Complete

- [x] All previous fixes (sessions 33-40)
- [x] SLURM account m2404 → m5083 (session 41)
- [x] Profiling prompt tip for tool diversity (session 41)

## Open Issues / TODOs

### Actionable (Priority Order)
1. **GPA agent launch bug** — Claude Code GPA run never invoked the agent. Need to debug `hpc_benchmark_runner.py` GPA flow to find why agent isn't launched after baseline verification.
2. **Check Qwen job results** — Jobs 49653981-84 (submitted this session)
3. **Analyze remaining gptoss120b GPA results** — Jobs 49641361-63 (sweagent/opencode/openhands on GPA)
4. **Submit Codex gptoss120b external-model** — Needs OPENAI_API_BASE/KEY
5. **GPA baseline build failures** — 6/16 apps fail to build (exatensor, xsbench, b+tree, backprop, srad, lavaMD)

### Persistent Issues
- [ ] **Quicksilver consistent timeout** — All frameworks timeout on QS
- [ ] **Lulesh intractable for agents** — Kernels already well-optimized (252 regs, compute-bound), bottleneck is MPI/CUDA runtime overhead
- [ ] **Laghos timing variance** — N/C range 0.98x-1.23x too high
- [ ] **Codex gpt-4.1-mini single-turn exit** — Model exits with needs_follow_up=false
- [ ] **Claude Code context exhaustion** — Lulesh no_profiling killed at 162K tokens after 161 turns
- [ ] **Claude never uses HPCToolkit/Hatchet** — Only nsys/ncu despite prompt listing hpc_profile+hatchet_analyze

## Recent Decisions

- 2026-03-04 (s41): Switch SLURM account from m2404 to m5083 for all jobs
- 2026-03-04 (s41): Add profiling tool diversity tip to prompt — encourage trying hpc_profile+hatchet when nsys/ncu don't yield insights
- 2026-03-04 (s40): All 4 framework launchers need `openai/` prefix for LiteLLM routing of external models
- 2026-03-04 (s40): Codex uses full `self.model_name` (e.g. `Qwen/Qwen3-Coder-Next-FP8`) because `model_provider=ext` is set separately
- 2026-03-04 (s40): OpenCode always uses `@ai-sdk/openai` npm package
- 2026-03-04 (s40): .gitignore committed in workspace to prevent patch contamination
- 2026-03-04 (s40): validation-runs default 10→3 to fix QS timeout

## Next Steps

1. **Debug GPA agent launch bug** — Why does `hpc_benchmark_runner.py` skip agent invocation for GPA base mode?
2. **Check Qwen job results** when 49653981-84 complete
3. **Analyze gptoss120b GPA results** for sweagent/opencode/openhands (49641361-63)
4. **Fix GPA baseline build failures** — 6 apps fail, may be CUDA version or path issue
