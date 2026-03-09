# Handoff — Session 42 (continued) → Session 43

Last updated: 2026-03-09

## What We Were Implementing

Migrating all LLNL app harnesses from single-GPU (np=1) to multi-GPU defaults. User requirement: "we are optimizing all of parallel HPC code performance." Target runtime: ~1 minute per app on 4x A100.

## Goal Progress

- [x] Goal 0: Load state, analyze gptoss120b results
- [x] Goal 1: Fix GPA agent launch bug, LULESH_ROOT path fix
- [x] Goal 2: Results analysis guide, workspace cleanup, batch cleanup
- [x] Goal 3: Per-rank GPU isolation in QS, Laghos, Lulesh harnesses
- [x] Goal 4: Multi-GPU defaults — Laghos np=4, QS np=4 (weak-scaled), Lulesh np=8
- [x] Goal 5: QS nSteps 100→10 (349s was too slow)
- [x] Goal 6: Benchmark runner validation timeout increased (600→900 base)
- [x] Goal 7: Commit all multi-GPU changes
- [ ] Goal 8: **DEBUG Kripke np>1 MPI hang** — MUST run multi-GPU, not stay at np=1 (user requirement)
- [ ] Goal 9: Validate QS np=4 nSteps=10 timing (~35s estimated)
- [ ] Goal 10: Consider Laghos problem scaling (8.3s too short, target ~60s)
- [ ] Goal 11: Check Qwen job results when they complete
- [ ] Goal 12: Fix OpenHands+gptoss120b Pydantic crash
- [ ] Goal 13: Submit Claude Code runs (LLNL + GPA)

## CRITICAL: Kripke MPI Hang Must Be Fixed

User explicitly stated all apps should run on full node. Kripke np>1 hangs with OpenMPI 5.0.7 at transport sweep. This MUST be debugged, not worked around with np=1. Possible approaches:
- Try cray-mpich instead of openmpi/5.0.7
- Check RAJA CUDA+MPI interaction — Kripke uses RAJA for GPU kernels
- Try different `--procs` decomposition (e.g., `4,1,1` instead of `2,2,1`)
- Check if `--bind-to none` or `--oversubscribe` causes the hang
- Run with NCCL debug logging to identify where it stalls
- Test np=2 (minimum multi-rank) to narrow down

Currently `kripke_run` is at np=1 with a hang warning. Once fixed, change to np=4.

## Target Runtimes (~1 minute per app)

| App | Current | Target | Action Needed |
|-----|---------|--------|---------------|
| Kripke | 28.4s (np=1) | ~60s (np=4) | Debug MPI hang first |
| Laghos | 8.3s (np=4) | ~60s | Increase rs (1→2 or 3) or dim (2→3) |
| Lulesh | 82.0s (np=8) | ~60-90s | OK as-is |
| QS | ~35s (np=4, nSteps=10 est) | ~60s | Validate; maybe increase nSteps to 15-20 |

## Files Modified This Session

### Committed in `4ac2767e` (Multi-GPU defaults)
- `tools/laghos_harness/bin/laghos_run` — DEFAULT_NP 1→4, GPU isolation
- `tools/lulesh_harness/bin/lulesh_run` — DEFAULT_NP 1→8, GPU mapping formula
- `tools/quicksilver_harness/bin/qs_run` — Weak-scaled input, fallback, timeout, header
- `tools/kripke_harness/bin/kripke_run` — np=1 with hang warning (TEMPORARY)
- `tools/quicksilver_harness/inputs/Coral2_P2_4.inp` — 4-rank input (nSteps=10)
- `batch/hpc_benchmark_runner.py` — Validation timeout increase

### Earlier commits this session
- `9da240e6` — Per-rank GPU isolation
- `319c790d` — LULESH_ROOT path fix
- `d7b58711` — Results analysis guide, workspace cleanup

## Key Decisions and Gotchas

1. **Lulesh requires perfect cube ranks** — np=8 (2³) with 2 ranks per GPU. Formula: `CUDA_VISIBLE_DEVICES=$(($RANK * 4 / 8))`.
2. **QS Coral2_P2_4 with nSteps=100 takes 349s** — Reduced to nSteps=10.
3. **Laghos np=4 is only 8.3s** — Needs problem scaling (rs or dim increase).
4. **`--overlap` srun gives partial GPUs** — Use `--exclusive` for validation.
5. **QS input file in two locations** — `Quicksilver/Examples/...` (untracked) + `tools/quicksilver_harness/inputs/` (tracked). Harness checks both.

## Files to Read First Next Session

1. `STATE.md` — Full project state
2. `.planning/HANDOFF.md` — This file
3. `tools/kripke_harness/bin/kripke_run:148-160` — Current MPI launch code (where hang occurs)
4. `tools/quicksilver_harness/bin/qs_run:40-48,306-325` — QS weak-scaled input resolution
5. Check Qwen jobs: `sacct -u krydzy -j 49850096,49850097,49850098,49850099`

## Validation Commands (interactive)

```bash
salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m5083

# QS np=4 nSteps=10 (needs validation)
srun --exclusive --gpus=4 --ntasks=1 bash -lc '
  module load python openmpi/5.0.7
  cd /pscratch/sd/k/krydzy/SWE-agent
  export QUICKSILVER_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Quicksilver
  python3 tools/quicksilver_harness/bin/qs_run --np 4 --baseline-only --timing-runs 1
'

# Kripke np=4 debug (try different approaches)
srun --exclusive --gpus=4 --ntasks=1 bash -lc '
  module load python openmpi/5.0.7
  cd /pscratch/sd/k/krydzy/SWE-agent
  export KRIPKE_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Kripke
  timeout 120 python3 tools/kripke_harness/bin/kripke_run --arch CUDA --np 4 --baseline-only
'
```

## Pending SLURM Jobs
- Qwen LLNL: 49850096-99 (PENDING)
- Qwen GPA: 49850130-35 (PENDING)
