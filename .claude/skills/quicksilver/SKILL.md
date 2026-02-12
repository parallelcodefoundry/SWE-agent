---
name: quicksilver
description: "Knowledge about the Quicksilver Monte Carlo particle transport proxy application including build configuration with g++-12, run parameters, expected output format, and correctness validation. Load when working on Quicksilver benchmarks or harnesses."
---

# Quicksilver

Monte Carlo particle transport proxy app (LLNL). Simulates neutral particle transport through 3D Cartesian geometry with multi-group cross sections. CUDA GPU via UVM, OpenMP for host threading. ~8,000 lines C++/CUDA. Single public commit (f174550) on `master`.

## Source Location

- **Pristine clone**: `/pscratch/sd/k/krydzy/SWE-agent/Quicksilver/` (never modify)
- **Working copy**: `/pscratch/sd/k/krydzy/SWE-agent/Quicksilver_test/` (agent experiments)
- **Upstream**: https://github.com/LLNL/Quicksilver (branch: `master`)
- **Executable**: `src/qs` (relative to repo root)

## Build (Perlmutter)

### g++-12 Requirement

**nvcc is incompatible with g++ 13+ when using `-std=c++11`.** Perlmutter defaults to g++ 13. The build harness handles this automatically via `--compiler-bindir`.

### Via Harness (recommended)
```bash
module load python cmake openmpi/5.0.7 cuda/12.4
export QUICKSILVER_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Quicksilver_test
python3 tools/quicksilver_harness/bin/qs_build
python3 tools/quicksilver_harness/bin/qs_build --clean   # clean rebuild
```

The build harness **always overrides** Makefile `CXX`/`CXXFLAGS`/`CPPFLAGS`/`LDFLAGS`. It uses `nvcc` with `g++-12`, passes recognized user flags through `-Xcompiler`, and filters out flags that break CUDA (`-fno-exceptions`, `-fno-rtti`, `-fno-asynchronous-unwind-tables`). Always enables: `-DHAVE_CUDA`, `-DHAVE_OPENMP`, `-std=c++11`, `-O3`.

### Manual Build
```bash
cd Quicksilver_test/src
module load cuda/12.4 openmpi/5.0.7
nvcc --compiler-bindir=$(which g++-12) \
  -DHAVE_CUDA -std=c++11 -O3 -lineinfo \
  -gencode=arch=compute_80,code=sm_80 \
  -Xcompiler -fopenmp -x cu -dc -DHAVE_OPENMP \
  *.cc -o qs
```

## Run

### Via Harness (recommended)
```bash
python3 tools/quicksilver_harness/bin/qs_run              # benchmark + correctness
```

The harness: (1) builds pristine Quicksilver if needed, (2) runs pristine with Coral2_P2_1 benchmark input as baseline, (3) runs modified version with same input, (4) compares per-cycle physics values for correctness (tolerance 1e-6), (5) compares wall-clock time using "main" timer for speedup, (6) outputs CORRECTNESS and SPEEDUP summary.

### Benchmark Input
- Path: `Examples/CORAL2_Benchmark/Problem2/Coral2_P2_1.inp`
- 230 energy groups, nSteps=10, dt=1e-08, nBatches=10

### Default Parameters (qs_run)
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--lx/ly/lz` | 10 | Domain dimensions (cm) |
| `--nx/ny/nz` | 10 | Mesh cells per dimension |
| `--nParticles` | 10000 | Number of particles |
| `--nSteps` | 5 | Number of time steps |

## Key Source Files

### Hot Path (optimization targets)
| File | Description |
|------|-------------|
| `src/CycleTracking.cc` | `CycleTrackingGuts()` and `CycleTrackingFunction()` -- particle tracking through mesh segments |
| `src/CollisionEvent.cc` | Collision processing: isotope selection, reaction sampling, tallying |
| `src/main.cc` | Main entry, `CycleTrackingKernel` CUDA kernel, `cycleTracking()` host dispatch |
| `src/MCT.cc` | Monte Carlo transport utilities |

### Supporting Files
| File | Description |
|------|-------------|
| `src/cudaFunctions.hh` | Thread layout (128 threads/block, max 65535 blocks) |
| `src/cudaUtils.hh` | `VAR_MEM` (UVM when HAVE_CUDA), `ExecutionPolicy` enum |
| `src/AtomicMacro.hh` | `ATOMIC_ADD`/`ATOMIC_UPDATE` -- CUDA atomicAdd on device, OpenMP on host |
| `src/ParticleVault.hh` | Particle container, manages batches |
| `src/MC_Fast_Timer.hh` | 6 timers: main, cycleInit, cycleTracking, cycleTracking_Segment, cycleTracking_Test_Done, cycleFinalize |

## Output and Validation

### Timer Output
```
Timer                  HET  Calls        Micro Seconds                    Efficiency
                                    Min          Avg          Max
main                    No      1  1.23e+07     1.23e+07     1.23e+07       100.00
cycleTracking           No     10  1.00e+06     1.10e+06     1.20e+06        83.33
```

### Correctness
The harness extracts per-cycle physics values (`absorb`, `scatter`, `fission`, `collisn`, `escape`, `census`, `scalar_flux`) from both runs. Relative error must be < 1e-6 for all values.

### Figure of Merit
`numSegments / (cycleTracking max_us * 1e-6)` -- segments per second.

## Common Issues

- **g++ 13 errors** -- Ensure `--compiler-bindir` points to `g++-12`; harness does this automatically.
- **"nvcc not found"** -- You are on a login node; CUDA builds require a compute node with GPUs.
- **Harness overrides Makefile flags** -- Edits to `CXX`/`CXXFLAGS` have no direct effect; harness always overrides.
- **Linker errors with `-dc`** -- All `.cc` files compiled as CUDA with `-x cu -dc`; new files must be included.
- **Executable not found** -- Binary is at `src/qs`, not repo root. Check `QUICKSILVER_ROOT`.
- **Benchmark input missing** -- Needs `Examples/CORAL2_Benchmark/Problem2/Coral2_P2_1.inp` relative to root.
- **Particle conservation warnings** -- Optimization broke physics; revert changes.

## SWE-agent Configuration

Config files:
- `config/hpc/quicksilver_no_profiling.yaml` -- Standard optimization run
- `config/hpc/quicksilver_with_profiling.yaml` -- With profiling tools

Key env vars: `CUDA_VISIBLE_DEVICES=0,1,2,3`, `OMP_NUM_THREADS=32`, `QUICKSILVER_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Quicksilver_test`

Agent editable files: `src/CycleTracking.cc`, `src/CollisionEvent.cc`, `src/main.cc`, `src/MCT.cc` (NOT Makefile — build harness overrides CXX/CXXFLAGS)
