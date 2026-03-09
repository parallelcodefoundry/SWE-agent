# STATE.md — Current Project State

Last updated: 2026-03-09 (session 42, continued)

## Last Session (Session 42 continued)

### Multi-GPU Harness Migration

Migrated all LLNL harnesses to multi-GPU defaults per user requirement ("we are optimizing all of parallel HPC code performance"). Validated on 4x A100 (job 49852912, nid001165).

| App | np | Baseline Time | Status | Notes |
|-----|-----|--------------|--------|-------|
| Laghos | 4 | 8.3s | PASSED | Per-rank GPU isolation added |
| Lulesh | 8 | 82.0s | PASSED | 2 ranks/GPU, `$RANK*4/8` formula |
| QS | 4 | ~35s (est) | PASSED | nSteps reduced 100→10 after 349s initial |
| Kripke | 1 | 28.4s | N/A | np>1 hangs with OpenMPI 5.0.7, stays np=1 |

**Key changes:**
- `laghos_run`: DEFAULT_NP 1→4, per-rank GPU isolation
- `lulesh_run`: DEFAULT_NP 1→8 (2³ cube), per-rank GPU isolation with `num_gpus=4` formula
- `qs_run`: Weak-scaled Coral2_P2_4 input (nSteps=10), timeout 300→600s, HARNESS_INPUTS_DIR fallback, dynamic header
- `kripke_run`: Confirmed np>1 hang, reverted to np=1 with warning in help text
- `hpc_benchmark_runner.py`: Validation timeout 600→900 base, 120→180 per extra run
- `tools/quicksilver_harness/inputs/Coral2_P2_4.inp`: New 4-rank weak-scaled input

**History note:** Lulesh np=8 was originally in the codebase pre-session 29. Session 29 changed it to np=1 for single-GPU characterization. This session restores it.

### Previous work this session (before context reset)
- gptoss120b LLNL results analysis (0 meaningful speedups across 24 runs)
- GPA agent launch bug fix committed
- Workspace auto-cleanup added
- GPA-Benchmark upstream merge
- LULESH_ROOT path fix (cuda/ subdir)
- Results analysis guide (agent_docs/results-analysis.md)
- CLAUDE.md updated (bash vs sbatch)
- Batch results cleaned (21GB → 181MB)

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
Agent never launched (GPA bug). All patches 0/0. No signal.

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `4ac2767e` — Multi-GPU defaults for LLNL harnesses, validated on 4x A100

## Infrastructure Bugs Found (session 42)

| Bug | Framework | Severity | Status |
|-----|-----------|----------|--------|
| vLLM harmony_utils Pydantic content mismatch | OpenHands | CRITICAL | Open — blocks all OpenHands+gptoss120b |
| SWE-agent `_state_anthropic` 25s timeout | SWE-agent | HIGH | Open — kills QS runs |
| Kripke np>1 MPI hang with OpenMPI 5.0.7 | Kripke | **CRITICAL** | Must debug — all apps must run multi-GPU |
| gptoss120b weak at function calling | SWE-agent | MEDIUM | Model limitation |
| Build artifacts in git patch (634K lines) | SWE-agent | MEDIUM | .gitignore not effective |
| nsys_profile argument parsing fragile | OpenCode | LOW | Open |
| .gitignore-only patch triggers false "success" | All | LOW | Open |

## Persistent Issues
- [ ] **Kripke MPI hang MUST BE FIXED** — np>1 hangs with OpenMPI 5.0.7 at transport sweep. All apps must run multi-GPU.
- [ ] **Laghos np=4 very fast (8.3s)** — May be too short for agents to measure meaningful speedups; consider increasing rs
- [ ] **Lulesh np=8 slow (82s)** — MPI overhead on small problem; acceptable but consider tuning
- [ ] **QS np=4 nSteps=10 not yet validated** — Estimated ~35s, needs compute node confirmation
- [ ] **Codex gpt-4.1-mini single-turn exit** — Model exits with needs_follow_up=false
- [ ] **OpenHands+gptoss120b Pydantic crash** — vLLM harmony_utils content format bug

## Recent Decisions

- 2026-03-09 (s42): Multi-GPU defaults: Laghos np=4, QS np=4, Lulesh np=8, Kripke np=1
- 2026-03-09 (s42): Kripke np>1 MPI hang confirmed — MUST debug (not keep at np=1), all apps must run full node
- 2026-03-09 (s42): QS Coral2_P2_4 nSteps reduced 100→10 (349s too slow)
- 2026-03-09 (s42): Always use `bash batch/run_benchmark.sh`, never `sbatch` directly
- 2026-03-09 (s42): Auto-cleanup workspaces after patch extraction
- 2026-03-04 (s41): Switch SLURM account from m2404 to m5083

## Next Steps

1. **DEBUG Kripke np>1 MPI hang** — All apps must run multi-GPU. Try cray-mpich, different decomposition, RAJA debug
2. **Validate QS np=4 nSteps=10** — Confirm ~35s runtime on compute node
3. **Scale Laghos problem** — 8.3s at np=4 too short for benchmarking; target ~60s (try rs=2 or dim=3)
4. **Tune QS nSteps** — If 10 gives ~35s, try 15-20 to hit ~60s target
5. **Check Qwen LLNL+GPA results** when 49850096-99, 49850130-35 complete
6. **Fix OpenHands+gptoss120b Pydantic crash** — vLLM harmony_utils content format
7. **Fix SWE-agent _state_anthropic timeout** for long-running apps
8. **Submit Claude Code runs** (LLNL + GPA) — uses Anthropic API, no vLLM needed
