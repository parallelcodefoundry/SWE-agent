---
name: kripke
description: "Build, run, and validate the Kripke transport proxy app on Perlmutter. Use when user mentions 'kripke', 'transport sweep', 'RAJA', or needs to debug Kripke CMake builds, harness issues, or correctness validation."
---

# Kripke

3D Sn deterministic particle transport proxy app (LLNL). Solves Kobayashi benchmark via source iteration with parallel sweep. Uses RAJA for portability (Sequential/OpenMP/CUDA/HIP), BLT CMake build system. ~5,000 lines C++14, v1.2.5-dev.

## Source Location

- **Pristine clone**: `/pscratch/sd/k/krydzy/SWE-agent/Kripke/` (never modify)
- **Working copy**: `/pscratch/sd/k/krydzy/SWE-agent/Kripke_test/` (agent experiments)
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
  -DENABLE_CUDA=ON -DENABLE_MPI=ON \
  -DCMAKE_CXX_COMPILER=mpicxx -DCMAKE_C_COMPILER=mpicc \
  -DCMAKE_CUDA_ARCHITECTURES=80 \
  -DCMAKE_CUDA_FLAGS="--extended-lambda --expt-relaxed-constexpr"
make -j8
```

## Run

### Via Harness (recommended)
```bash
python3 tools/kripke_harness/bin/kripke_run --arch CUDA
python3 tools/kripke_harness/bin/kripke_run \
  --arch CUDA --layout DGZ --zones 32,32,32 --groups 32 --niter 10 --quad 8 --np 4
```

### Correctness Validation
The harness runs pristine Kripke with identical parameters, compares iteration count, zone dimensions, and group count. Kripke is deterministic -- identical inputs produce identical particle counts (tolerance 1e-10).

## Common Issues

- **MPI hang at np>1 (OPEN BUG)**: `mpirun -np 4` with OpenMPI 5.0.7 hangs at the transport sweep phase. Confirmed on 4x A100 (session 42). Kripke temporarily defaults to np=1. Must be debugged — all apps should run multi-GPU. Possible causes: RAJA+CUDA+MPI interaction, OpenMPI 5 incompatibility. Try: cray-mpich, different `--procs` decomposition, np=2 to narrow down.
- **"nvcc not found"**: On a login node; CUDA builds require a compute node.
- **"BLT/CAMP submodule not present"**: Run `git submodule update --init --recursive` (harness does this automatically).
- **"--extended-lambda" errors**: Pass `-DCMAKE_CUDA_FLAGS="--extended-lambda --expt-relaxed-constexpr"`.
- **Git operations hanging**: 44+ submodules. Fix: `git config --local submodule.recurse false && git config --local diff.ignoreSubmodules all && git remote remove origin`.
- **Agent switches CUDA to OpenMP**: Verify build log shows "Architecture: CUDA".
- **"executable not found"**: Can land in `build/kripke.exe` or `build/bin/kripke.exe`; harness checks both.

## SWE-agent Configuration

- `config/hpc/kripke_no_profiling.yaml` -- Standard optimization run
- `config/hpc/kripke_with_profiling.yaml` -- With HPCToolkit/hatchet profiling tools
- Key env vars: `CUDA_VISIBLE_DEVICES=0,1,2,3`, `OMP_NUM_THREADS=32`, `KRIPKE_ROOT`

For detailed reference, see references/ in this skill directory.
