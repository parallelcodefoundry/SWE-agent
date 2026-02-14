# Kripke Solver Internals

## CMake Options

| Flag | Default | Notes |
|------|---------|-------|
| `ENABLE_CUDA` | Off | NVIDIA GPU backend via RAJA |
| `ENABLE_OPENMP` | Off | CPU threading backend |
| `ENABLE_MPI` | Off | Distributed parallelism |
| `ENABLE_CHAI` | Off | Copy-hiding memory management (CHAI/Umpire) |
| `ENABLE_CALIPER` | Off | Performance profiling annotations |
| `CMAKE_CUDA_ARCHITECTURES` | -- | Must set to `80` for A100 |

## Submodule Dependencies

44+ nested submodules. Key deps: **RAJA** (v2025.03.2, loop abstraction), **BLT** (v0.7.0, CMake), **CHAI/Umpire** (optional, memory mgmt), **CUB** (CUDA primitives for RAJA). Build harness auto-runs `git submodule update --init --recursive` if missing.

## Run Parameters

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

## Additional Notes

- Don't add `-fno-exceptions`/`-fno-rtti`: Breaks RAJA/CAMP which uses RTTI internally.
- Upstream: https://github.com/LLNL/Kripke (branch: `develop`)
