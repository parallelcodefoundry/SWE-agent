# Handoff — Session 44

Last updated: 2026-03-09

## What We Were Implementing and Why

Multi-GPU characterization and validation of all LLNL proxy apps + GPA benchmark apps. Goal: calibrate ~60s runtimes for LLNL apps running on 4 GPUs with MPI, verify MPI parallelism, profile with nsight, and test all GPA app builds.

## Approach Chosen

- Run apps via harness scripts (same path as benchmark runner)
- Fix infrastructure bugs in harnesses (mpirun path, LD_LIBRARY_PATH, arch default)
- Test GPA apps via benchmark runner's `_run_gpa_driver()` (exactly how benchmarks invoke them)
- Document multi-GPU requirements in CLAUDE.md

## Goal Progress

- [x] Goal 0: Load state, verify compute node
- [x] Goal 1: Fix Kripke CUDA+MPI (CHAI rebuild) — np=4 works
- [x] Goal 2: Remove OMP_PROC_BIND/PLACES from harnesses
- [x] Goal 3: Tune Laghos to ~60s — rs=4, tf=0.8, np=4 → 67s
- [x] Goal 4: Verify Lulesh timing — np=8, s=150, i=5000 → 52s
- [x] Goal 5: Recalibrate QS to ~60s — nSteps=67, np=4 → 60s
- [x] Goal 6: Verify MPI parallelism — all 4 apps confirmed rank→GPU mapping
- [x] Goal 7: Run nsys profiles for all 4 LLNL apps — saved to /tmp/nsys_*/
- [x] Goal 8: Update CLAUDE.md with multi-GPU MPI requirement section
- [x] Goal 9: Fix harness mpirun path resolution (all 4 harnesses)
- [x] Goal 10: Fix harness LD_LIBRARY_PATH for MPI+CUDA (all 4 harnesses)
- [x] Goal 11: Fix GPA driver API call in benchmark runner (DriverConfig)
- [x] Goal 12: Test all 16 GPA apps — 13 pass, 3 fail (upstream issues)
- [x] Goal 13: Commit all changes
- [ ] Goal 14: Update setup_apps.sh with CHAI build for Kripke
- [ ] Goal 15: Check Qwen job results (PENDING from session 42)
- [ ] Goal 16: Submit Claude Code runs (LLNL + GPA)

## Files Modified This Session

- `tools/kripke_harness/bin/kripke_run` — _find_mpirun(), _ensure_ld_library_path(), default arch=CUDA
- `tools/laghos_harness/bin/laghos_run` — _find_mpirun(), _ensure_ld_library_path()
- `tools/lulesh_harness/bin/lulesh_run` — _find_mpirun(), _ensure_ld_library_path()
- `tools/quicksilver_harness/bin/qs_run` — _find_mpirun(), _ensure_ld_library_path()
- `tools/quicksilver_harness/inputs/Coral2_P2_4.inp` — nSteps=67 (was 8)
- `batch/hpc_benchmark_runner.py` — Fixed _run_gpa_driver() to use DriverConfig object
- `CLAUDE.md` — Added Multi-GPU MPI Requirements section, fixed module name

## Files to Read First Next Session

- `STATE.md` — Full project state
- `CLAUDE.md` — Updated with multi-GPU section
- `batch/hpc_benchmark_runner.py` (lines 1064-1080) — GPA driver invocation

## Gotchas and Decisions

- **GPA driver API changed**: `run_driver()` now takes `DriverConfig` object, not kwargs. Our `_run_gpa_driver()` was passing kwargs directly → `TypeError`. Fixed.
- **GPA lavaMD bug**: `run_all()` at line 537 does `app["name"].lower() != config.app` — lowercases YAML name but not config.app. So `"lavamd" != "lavaMD"` → skip → `AppNameNotFoundError`. Upstream bug, not our fix.
- **GPA b+tree/backprop**: C code uses K&R style (implicit int, implicit declarations) that gcc 14 treats as errors. Upstream code issue.
- **GPA LULESH submodule**: Was empty. Initialized with `git submodule update --init LULESH` in GPA-Benchmark. Now builds/runs/validates OK, but excluded from our benchmark runner (line 888: `if app["name"].lower() != "lulesh"`).
- **Module loading doesn't persist**: Each Bash tool call starts fresh. Must set PATH/LD_LIBRARY_PATH explicitly or use harness `_ensure_ld_library_path()`.
- **CUDA 12.4 path**: `/opt/nvidia/hpc_sdk/Linux_x86_64/24.5/cuda/12.4` (under `24.5`, not `25.5`)

## Validated Timings

| App | np | Time | Correctness | Status |
|-----|-----|------|-------------|--------|
| Kripke | 4 | 51-55s | PASSED | OK |
| Laghos | 4 | 67s | PASSED | OK |
| Lulesh | 8 | 51-52s | PASSED | OK |
| QS | 4 | 60s | PASSED | OK |

## GPA App Results (via benchmark runner)

| App | Status | App | Status |
|-----|--------|-----|--------|
| exatensor | PASS | lud | PASS |
| xsbench | PASS | nw | PASS |
| bfs | PASS | particlefilter | PASS |
| gaussian | PASS | pathfinder | PASS |
| heartwall | PASS | srad | PASS |
| hotspot | PASS | streamcluster | PASS |
| huffman | PASS | b+tree | BUILD FAIL |
| backprop | BUILD FAIL | lavaMD | CONFIG ERROR |

## Interactive Validation Commands

```bash
salloc --nodes 1 --qos interactive --time 03:00:00 --constraint gpu --gpus 4 --account m5083

source /opt/cray/pe/lmod/lmod/init/bash && module load python cmake && module swap cray-mpich openmpi/5.0.7 && module load cudatoolkit/12.4
source ~/envs/sweagent/bin/activate

# LLNL apps
export KRIPKE_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Kripke
python3 tools/kripke_harness/bin/kripke_run --np 4 --baseline-only --timing-runs 1

export LAGHOS_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Laghos
python3 tools/laghos_harness/bin/laghos_run --np 4 --baseline-only --timing-runs 1

export LULESH_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Lulesh/cuda
python3 tools/lulesh_harness/bin/lulesh_run --np 8 --baseline-only --timing-runs 1

export QUICKSILVER_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Quicksilver
python3 tools/quicksilver_harness/bin/qs_run --np 4 --baseline-only --timing-runs 1

# GPA apps (use default CUDA 12.9, NOT cudatoolkit/12.4)
cd /pscratch/sd/k/krydzy/GPA-Benchmark
python3 -m gpa_bench_driver --app bfs --sm-version 80 --no-sanitize --no-progress -l INFO
```
