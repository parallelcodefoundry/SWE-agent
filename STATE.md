# STATE.md — Current Project State

Last updated: 2026-03-09 (session 44)

## Last Session (Session 44)

Continued session 43's multi-GPU characterization work. Key accomplishments:

### Harness MPI Robustness (all 4 harnesses)
- Added `_find_mpirun()` — resolves mpirun to absolute path with Perlmutter fallback
- Added `_ensure_ld_library_path()` — ensures libfabric, CUDA, OpenMPI libs available for MPI-launched processes
- Fixed kripke_run default `--arch` from OpenMP to CUDA

### QS Recalibration
- nSteps=67 in Coral2_P2_4.inp (was 8) → 59.7s at np=4 (validated)
- Updated both `tools/quicksilver_harness/inputs/` and `Quicksilver/Examples/.../` copies

### GPA Benchmark Testing (via benchmark runner flow)
- Fixed `_run_gpa_driver()` — GPA driver API changed to require `DriverConfig` object, not kwargs
- Initialized GPA LULESH submodule (`git submodule update --init LULESH`)
- Tested all 16 GPA apps through benchmark runner's `_run_gpa_driver()`:

| App | Status | Notes |
|-----|--------|-------|
| exatensor | PASS | |
| xsbench | PASS | |
| bfs | PASS | |
| gaussian | PASS | |
| heartwall | PASS | |
| hotspot | PASS | |
| huffman | PASS | |
| lud | PASS | |
| nw | PASS | |
| particlefilter | PASS | |
| pathfinder | PASS | |
| srad | PASS | |
| streamcluster | PASS | |
| b+tree | BUILD FAIL | gcc 14 strict: implicit declarations, incompatible pointer types |
| backprop | BUILD FAIL | gcc 14 strict: K&R style C, implicit int/declarations |
| lavaMD | CONFIG ERROR | GPA driver bug: `run_all()` compares `app["name"].lower()` with `config.app` (not lowered) |

**GPA requirements**: Default CUDA 12.9 (NOT cudatoolkit/12.4). Driver auto-detects via `nvcc` in PATH.

### CLAUDE.md Updated
- Added Multi-GPU MPI Requirements section with timing table
- Fixed module name: `cuda/12.4` → `cudatoolkit/12.4`

### Nsys Profiles Completed (all 4 LLNL apps)
Profiles saved to `/tmp/nsys_{kripke,laghos,lulesh,qs}/` with summary.txt and cuda_kern_summary.txt.

## Validated LLNL App Timings (4x A100)

| App | np | Parameters | Time | Correctness |
|-----|-----|-----------|------|-------------|
| Kripke | 4 | zones=64³, groups=64, niter=60, quad=8 | 51-55s | PASSED |
| Laghos | 4 | p1, dim=2, rs=4, tf=0.8, -pa -d cuda | 67s | PASSED |
| Lulesh | 8 | s=150, i=5000 | 51-52s | PASSED |
| QS | 4 | Coral2_P2_4.inp, nSteps=67 | 60s | PASSED |

## Active Experiments

### Qwen LLNL (session 42, still pending)
| Job ID | Framework | Status |
|--------|-----------|--------|
| 49850098 | opencode | PENDING |
| 49850099 | openhands | PENDING |

### Qwen GPA (session 42, still pending)
| Job ID | Framework | Status |
|--------|-----------|--------|
| 49850130 | sweagent | PENDING |
| 49850133 | codex | PENDING |
| 49850134 | opencode | PENDING |
| 49850135 | openhands | PENDING |

## Branch State

- **Current branch**: `dev`
- **Latest commit**: `0608c8d7` — WIP: Session 43-44 harness MPI robustness, GPA driver fix, QS recalibration

## Infrastructure Bugs Found

| Bug | Severity | Status |
|-----|----------|--------|
| Kripke CHAI required for CUDA+MPI | CRITICAL | **FIXED** (session 43) |
| OMP_PROC_BIND=spread in harnesses | HIGH | **FIXED** (session 43) |
| GPA driver API: run_driver() takes DriverConfig | HIGH | **FIXED** (session 44) |
| Harness mpirun path resolution | HIGH | **FIXED** (session 44) |
| Harness LD_LIBRARY_PATH for MPI+CUDA | HIGH | **FIXED** (session 44) |
| QS nSteps recalibration | HIGH | **FIXED** (session 44) — nSteps=67 |
| GPA b+tree build fail (gcc14) | LOW | Open — upstream C code issue |
| GPA backprop build fail (gcc14) | LOW | Open — upstream C code issue |
| GPA lavaMD config error | LOW | Open — case sensitivity bug in GPA driver |
| vLLM harmony_utils Pydantic crash | CRITICAL | Open — blocks OpenHands+gptoss120b |
| SWE-agent `_state_anthropic` 25s timeout | HIGH | Open |

## Recent Decisions

- 2026-03-09 (s44): GPA driver `run_driver()` API changed — must use `DriverConfig` object
- 2026-03-09 (s44): GPA LULESH submodule initialized — builds/runs/validates OK
- 2026-03-09 (s44): GPA `no_sanitize=True` added — skip compute-sanitizer for faster runs
- 2026-03-09 (s44): b+tree/backprop failures are upstream gcc14 issues, not our problem
- 2026-03-09 (s44): lavaMD failure is GPA driver bug (case-insensitive compare), not our problem
- 2026-03-09 (s43): Kripke requires ENABLE_CHAI=ON for CUDA+MPI
- 2026-03-09 (s43): Remove OMP_PROC_BIND/PLACES from harnesses
- 2026-03-09 (s43): Laghos rs=4, tf=0.8 gives ~67s at np=4
- 2026-03-09 (s43): Kripke zones=64³, niter=60 gives ~55s at np=4

## Next Steps

1. **Check Qwen job results** (still PENDING from session 42)
2. **Submit Claude Code runs** (LLNL + GPA)
3. **Update setup_apps.sh** to build Kripke with CHAI
4. **Fix GPA broken apps** if needed — b+tree/backprop need gcc flags fix, lavaMD needs driver fix
5. **Design: agent access to OMP/env settings** — Direct mode or wrapper script approach
