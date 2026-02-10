---
name: kripke
description: "Knowledge about the Kripke deterministic transport proxy application including build configuration, run parameters, expected output format, and correctness validation. Load when working on Kripke benchmarks or harnesses."
---

# Kripke

3D Sn deterministic particle transport proxy app (LLNL). Solves Kobayashi benchmark via source iteration with parallel sweep. Uses RAJA for portability (Sequential/OpenMP/CUDA/HIP), BLT CMake build system. ~5,000 lines C++14, v1.2.5-dev.

## Source Location

- **Pristine clone**: `/pscratch/sd/k/krydzy/SWE-agent/Kripke/` (never modify)
- **Working copy**: `/pscratch/sd/k/krydzy/SWE-agent/Kripke_test/` (agent experiments)
- **Upstream**: https://github.com/LLNL/Kripke (branch: `develop`)
- **Executable**: `build/kripke.exe` (relative to repo root)

## Build (Perlmutter)

### Via Harness (recommended)
```bash
module load python cmake openmpi/5.0.7 cuda/12.4
export KRIPKE_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Kripke_test
python3 tools/kripke_harness/bin/kripke_build --arch CUDA
python3 tools/kripke_harness/bin/kripke_build --arch CUDA --clean  # clean rebuild
```

### Manual CMake
```bash
cd Kripke_test && mkdir -p build && cd build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_CUDA=ON \
  -DENABLE_MPI=ON \
  -DCMAKE_CXX_COMPILER=mpicxx \
  -DCMAKE_C_COMPILER=mpicc \
  -DCMAKE_CUDA_ARCHITECTURES=80 \
  -DCMAKE_CUDA_FLAGS="--extended-lambda --expt-relaxed-constexpr"
make -j8
```

### CMake Options
| Flag | Default | Notes |
|------|---------|-------|
| `ENABLE_CUDA` | Off | NVIDIA GPU backend via RAJA |
| `ENABLE_OPENMP` | Off | CPU threading backend |
| `ENABLE_MPI` | Off | Distributed parallelism |
| `ENABLE_CHAI` | Off | Copy-hiding memory management (CHAI/Umpire) |
| `ENABLE_CALIPER` | Off | Performance profiling annotations |
| `CMAKE_CUDA_ARCHITECTURES` | -- | Must set to `80` for A100 |

### Submodule Dependencies
44+ nested submodules. Key deps: **RAJA** (v2025.03.2, loop abstraction), **BLT** (v0.7.0, CMake), **CHAI/Umpire** (optional, memory mgmt), **CUB** (CUDA primitives for RAJA). Build harness auto-runs `git submodule update --init --recursive` if missing.

## Run

### Via Harness (recommended)
```bash
python3 tools/kripke_harness/bin/kripke_run --arch CUDA

python3 tools/kripke_harness/bin/kripke_run \
  --arch CUDA --layout DGZ --zones 32,32,32 --groups 32 --niter 10 --quad 8 --np 4 --omp-threads 8
```

### Default Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--arch` | Sequential* | Backend: Sequential, OpenMP, CUDA, HIP |
| `--layout` | DGZ | Data nesting order (Direction, Group, Zone) |
| `--zones` | 16,16,16 | Grid dimensions per MPI rank |
| `--groups` | 32 | Energy groups |
| `--legendre` | 4 | Scattering expansion order |
| `--quad` | 96 | Quadrature points (or polar:azimuthal) |
| `--niter` | 10 | Solver iterations |
| `--procs` | 1,1,1 | MPI rank decomposition (x,y,z) |
| `--dset` | 8 | Direction-sets (must factor 8, divide quad evenly) |
| `--gset` | 1 | Group-sets (must divide groups evenly) |
| `--zset` | 1,1,1 | Zone-sets per dimension |
| `--pmethod` | sweep | Solver: sweep (wavefront) or bj (Block Jacobi) |

*Default arch precedence: Sequential < OpenMP < CUDA. Harness overrides: `--arch OpenMP --layout DGZ --zones 32,32,32 --groups 32 --niter 10 --quad 8 --np 4 --omp-threads 8`. For CUDA benchmarking, always pass `--arch CUDA`.

## Key Files: Computational Kernels (hot path)

| File | Description | Timer Name |
|------|-------------|------------|
| `src/Kripke/Kernel/SweepSubdomain.cpp` | Transport sweep (dominates runtime) | `SweepSubdomain` |
| `src/Kripke/Kernel/LTimes.cpp` | Discrete-to-moments (phi = L * psi) | `LTimes` |
| `src/Kripke/Kernel/LPlusTimes.cpp` | Moments-to-discrete (rhs = L+ * phi_out) | `LPlusTimes` |
| `src/Kripke/Kernel/Scattering.cpp` | Scattering source term (phi_out = S * phi) | `Scattering` |
| `src/Kripke/Kernel/Source.cpp` | External source term | `Source` |
| `src/Kripke/Kernel/Population.cpp` | Particle population count (convergence) | `Population` |

## Solver Algorithm

Each source iteration: (1) `phi = LTimes(psi)` discrete-to-moments, (2) `phi_out = Scattering(phi)` scattering source, (3) `phi_out += Source()` external source, (4) `rhs = LPlusTimes(phi_out)` moments-to-discrete, (5) `psi = Sweep(rhs, psi)` transport sweep, (6) `population(psi)` convergence check. The sweep kernel (`SweepSubdomain`) typically dominates runtime.

## Output Format

### Timer Output (machine-readable)
```
TIMER_NAMES:Generate,LPlusTimes,LTimes,Population,Scattering,Solve,Source,SweepSolver,SweepSubdomain
TIMER_DATA:0.042820,0.229180,0.194920,0.007340,0.018230,21.809680,0.000430,21.353030,20.553820
```

### Correctness Validation
The harness runs pristine Kripke with identical parameters, compares iteration count, zone dimensions, and group count. Kripke is deterministic -- identical inputs must produce identical particle counts (tolerance 1e-10). Output:
```
CORRECTNESS:     PASSED (3 values match)
```

## Common Issues

- **"nvcc not found"**: You're on a login node; CUDA builds require a compute node.
- **"BLT/CAMP submodule not present"**: Run `git submodule update --init --recursive` (harness does this automatically).
- **"--extended-lambda" errors**: Pass `-DCMAKE_CUDA_FLAGS="--extended-lambda --expt-relaxed-constexpr"` (required for RAJA CUDA).
- **Don't add `-fno-exceptions`/`-fno-rtti`**: Breaks RAJA/CAMP which uses RTTI internally.
- **Agent switches CUDA to OpenMP**: Known issue -- agent reconfigures cmake without `ENABLE_CUDA=ON`. Verify build log shows "Architecture: CUDA".
- **Git operations hanging**: 44+ submodules. Fix: `git config --local submodule.recurse false && git config --local diff.ignoreSubmodules all && git remote remove origin`.
- **"executable not found"**: Can land in `build/kripke.exe` or `build/bin/kripke.exe`; harness checks both.

## SWE-agent Configuration

- `config/hpc/kripke_no_profiling.yaml` -- Standard optimization run
- `config/hpc/kripke_with_profiling.yaml` -- With HPCToolkit/hatchet profiling tools
- Key env vars: `CUDA_VISIBLE_DEVICES=0,1,2,3`, `OMP_NUM_THREADS=32`, `KRIPKE_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Kripke_test`
