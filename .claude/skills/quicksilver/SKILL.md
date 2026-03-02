---
name: quicksilver
description: "Build, run, and validate the Quicksilver Monte Carlo transport proxy app. Use when user mentions 'quicksilver', 'QS', 'Monte Carlo transport', MPI+CUDA builds, domain decomposition, or particle tracking."
---

# Quicksilver

Monte Carlo particle transport proxy app (LLNL). Simulates neutral particle transport through 3D Cartesian geometry with multi-group cross sections. CUDA GPU via UVM, OpenMP for host threading. ~8,000 lines C++/CUDA.

## Source Location

- **Pristine clone**: `/pscratch/sd/k/krydzy/SWE-agent/Quicksilver/` (never modify)
- **Working copy**: `/pscratch/sd/k/krydzy/SWE-agent/Quicksilver_test/` (agent experiments)
- **Executable**: `src/qs` (relative to repo root)

## Build (Perlmutter)

### Via Harness (recommended)
```bash
module load python cmake openmpi/5.0.7 cuda/12.4
export QUICKSILVER_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Quicksilver_test
python3 tools/quicksilver_harness/bin/qs_build
python3 tools/quicksilver_harness/bin/qs_build --clean   # clean rebuild
```

The build harness uses `nvcc` with `g++-12`. If the agent modifies the Makefile, the harness respects agent flags (only enforcing `CXX=nvcc`). Otherwise, uses safe defaults: `-DHAVE_CUDA`, `-DHAVE_OPENMP`, `-std=c++11`, `-O3`.

### g++-12 Requirement
**nvcc is incompatible with g++ 13+ when using `-std=c++11`.** Harness handles via `--compiler-bindir`.

## Run

### Via Harness (recommended)
```bash
python3 tools/quicksilver_harness/bin/qs_run              # benchmark + correctness
```

The harness: (1) builds pristine Quicksilver, (2) runs pristine with Coral2_P2_1 benchmark input as baseline, (3) runs modified version with same input, (4) compares per-cycle physics values for correctness (tolerance 1e-6), (5) reports speedup using "main" timer.

### Correctness Validation
The harness extracts per-cycle physics values (`absorb`, `scatter`, `fission`, `collisn`, `escape`, `census`, `scalar_flux`) from both runs. Relative error must be < 1e-6.

### Figure of Merit
`numSegments / (cycleTracking max_us * 1e-6)` -- segments per second.

## Common Issues

- **g++ 13 errors** -- Ensure `--compiler-bindir` points to `g++-12`; harness does this automatically.
- **"nvcc not found"** -- On a login node; CUDA builds require a compute node with GPUs.
- **Makefile changes are respected** -- If you modify the Makefile, the harness detects your changes and only enforces `CXX=nvcc`. If you don't modify the Makefile, the harness uses full default flags (`-O3`, `-std=c++11`, `sm_80`).
- **Linker errors with `-dc`** -- All `.cc` files compiled as CUDA with `-x cu -dc`; new files must be included.
- **Executable not found** -- Binary is at `src/qs`, not repo root.
- **Particle conservation warnings** -- Optimization broke physics; revert changes.

## SWE-agent Configuration

- `config/hpc/quicksilver_no_profiling.yaml` -- Standard optimization run
- `config/hpc/quicksilver_with_profiling.yaml` -- With profiling tools
- Key env vars: `CUDA_VISIBLE_DEVICES=0,1,2,3`, `OMP_NUM_THREADS=32`, `QUICKSILVER_ROOT`
- Agent editable files: `src/CycleTracking.cc`, `src/CollisionEvent.cc`, `src/main.cc`, `src/MCT.cc`

For detailed reference, see references/ in this skill directory.
