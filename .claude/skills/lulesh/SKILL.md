---
name: lulesh
description: "Build, run, and validate the LULESH shock hydrodynamics proxy app. Use when user mentions 'lulesh', 'shock hydro', g++-12 build issues, CUDA kernel optimization, or LULESH correctness."
---

# LULESH

Livermore Unstructured Lagrangian Explicit Shock Hydrodynamics 2.0 -- Sedov blast wave on hex mesh, CUDA GPU, ~4800 lines C++.

## Source Location

- **Pristine**: `/pscratch/sd/k/krydzy/SWE-agent/Lulesh/cuda/` (never modify)
- **Working copy**: `/pscratch/sd/k/krydzy/SWE-agent/Lulesh_test/cuda/`
- **Executable**: `cuda/lulesh`

## Build

### g++-12 Requirement

**nvcc is incompatible with g++ 13+ when using `-std=c++11`.** Perlmutter defaults to g++ 13. The Makefile auto-detects g++-12:
```makefile
HOST_CXX ?= $(shell which g++-12 2>/dev/null || which g++-11 2>/dev/null || echo g++)
```

### Via Harness (recommended)
```bash
module load python cmake openmpi/5.0.7 cuda/12.4
export LULESH_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Lulesh_test/cuda
python3 tools/lulesh_harness/bin/lulesh_build          # standard build
python3 tools/lulesh_harness/bin/lulesh_build --clean   # clean rebuild
python3 tools/lulesh_harness/bin/lulesh_build --use-mpi # with MPI
```

The Makefile (`cuda/Makefile`) is committed to the repo with correct Perlmutter settings (sm_80, g++-12). The harness also has an embedded template that regenerates it if missing or corrupted.

## Run

### Benchmark Parameters
- **np=8** (2³ cube decomposition, 2 ranks/GPU on 4x A100)
- **s=150** (mesh size per edge)
- **i=2000** (iterations) — calibrated for ~63s wall time with real MPI
- GPU mapping: `CUDA_VISIBLE_DEVICES=$(($OMPI_COMM_WORLD_LOCAL_RANK * 4 / 8))`
- `OMPI_MCA_btl=^smcuda` required to prevent MPI finalization segfault

### Via Harness (recommended)
```bash
python3 tools/lulesh_harness/bin/lulesh_run               # benchmark + correctness
python3 tools/lulesh_harness/bin/lulesh_run -s 30 -i 100  # custom parameters
```

The harness: (1) builds pristine LULESH, (2) runs pristine as baseline, (3) runs modified version, (4) compares Final Origin Energy (tolerance 1e-8), (5) reports speedup.

### Correctness Validation
The harness extracts `Final Origin Energy` from both pristine and modified runs. Relative error must be < 1e-8. Regex: `Final Origin Energy\s*=\s*([\d.eE+-]+)`.

## Common Issues

- **g++ 13 errors** -- Ensure `HOST_CXX` points to `g++-12`; embedded Makefile does this automatically.
- **"nvcc not found"** -- On a login node; CUDA builds require a compute node with GPUs.
- **Makefile missing** -- Run `lulesh_build`; it generates from embedded template. The proper `cuda/Makefile` is also committed to the repo.
- **Legacy Makefiles removed** -- `cuda/build/Makefile.CRAY`, `openacc/build/Makefile`, `stdpar/build/Makefile` were removed (wrong arch/compiler targets). Do not recreate them.
- **CUDA sources missing after checkout** -- Older commits predate the CUDA port; skip them.
- **"Num processors must be a cube"** -- MPI builds need cube-number ranks (1, 8, 27, 64).
- **Volume/Q errors** -- Optimization broke the physics; revert. Error codes: VolumeError=-1, QStopError=-2.
- **MPI finalization segfault** -- OpenMPI 5.0.7 + CUDA causes SIGSEGV in `cuEventDestroy` during `MPI_Finalize`. Fix: `OMPI_MCA_btl=^smcuda` (already in harness since s50).
- **MPICH_DIR must be set for MPI build** -- Perlmutter uses OpenMPI (`OPENMPI_ROOT`), but Lulesh Makefile expects `MPICH_DIR`. Harness bridges: `MPICH_DIR=${OPENMPI_ROOT}`. Pristine binary rebuilt with MPI in session 50.

## SWE-agent Configuration

- `config/hpc/lulesh_no_profiling.yaml` -- standard run
- `config/hpc/lulesh_with_profiling.yaml` -- with profiling tools
- Key env vars: `CUDA_VISIBLE_DEVICES=0,1,2,3`, `OMP_NUM_THREADS=32`, `LULESH_ROOT`

For detailed reference, see references/ in this skill directory.
