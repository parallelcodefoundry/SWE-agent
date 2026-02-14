# Quicksilver MPI+CUDA Details

## Manual Build

```bash
cd Quicksilver_test/src
module load cuda/12.4 openmpi/5.0.7
nvcc --compiler-bindir=$(which g++-12) \
  -DHAVE_CUDA -std=c++11 -O3 -lineinfo \
  -gencode=arch=compute_80,code=sm_80 \
  -Xcompiler -fopenmp -x cu -dc -DHAVE_OPENMP \
  *.cc -o qs
```

The build harness **always overrides** Makefile `CXX`/`CXXFLAGS`/`CPPFLAGS`/`LDFLAGS`. It filters out flags that break CUDA (`-fno-exceptions`, `-fno-rtti`, `-fno-asynchronous-unwind-tables`).

## Benchmark Input

- Path: `Examples/CORAL2_Benchmark/Problem2/Coral2_P2_1.inp`
- 230 energy groups, nSteps=10, dt=1e-08, nBatches=10

## Run Parameters

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

## MPI+CUDA Execution

The `qs_build` harness detects MPI via `mpicxx --showme`, filters nvcc-incompatible flags (`-pthread`, `-Wl,X` -> `-Xlinker X`). `qs_run` uses `mpirun -np N --bind-to none --oversubscribe`, creates temp input files with correct `xDom/yDom/zDom` (QS input file overrides CLI `-I/-J/-K` flags). No `HAVE_ASYNC_MPI` -- OpenMPI 5 `MPI_Iallreduce` crashes with it.

## Timer Output Format

```
Timer                  HET  Calls        Micro Seconds                    Efficiency
                                    Min          Avg          Max
main                    No      1  1.23e+07     1.23e+07     1.23e+07       100.00
cycleTracking           No     10  1.00e+06     1.10e+06     1.20e+06        83.33
```

## Domain Decomposition

QS input file overrides CLI domain flags. `Parameters.cc:88` parses input file AFTER command line, so `-I/-J/-K` get overwritten. Must modify the input file directly for domain decomposition.

## Additional Notes

- Upstream: https://github.com/LLNL/Quicksilver (branch: `master`)
- Single public commit (f174550) on `master`.
- Benchmark input missing -- Needs `Examples/CORAL2_Benchmark/Problem2/Coral2_P2_1.inp` relative to root.
