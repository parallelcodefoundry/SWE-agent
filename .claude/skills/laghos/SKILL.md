---
name: laghos
description: "Build, run, and validate the Laghos Lagrangian hydrodynamics proxy app. Use when user mentions 'laghos', 'MFEM', 'hypre', 'metis', shared dependencies, or Laghos build/run issues."
---

# Laghos

**LAGrangian High-Order Solver** -- compressible gas dynamics via high-order Lagrangian finite elements. MFEM-based, part of the CEED suite, proxy for LLNL's BLAST hydrocode.

## Source Location

- **Pristine clone**: `/pscratch/sd/k/krydzy/SWE-agent/Laghos/` (never modify)
- **Working copy**: `/pscratch/sd/k/krydzy/SWE-agent/Laghos_test/` (agent experiments)
- **Executable**: `laghos` (in repo root)

### Shared Dependencies (sibling directories)

Both `Laghos/` and `Laghos_test/` share these via relative paths (`../mfem`, etc.):
- `/pscratch/sd/k/krydzy/SWE-agent/mfem/` -- MFEM finite element library
- `/pscratch/sd/k/krydzy/SWE-agent/hypre/` -> `hypre-2.11.2/` -- parallel linear algebra
- `/pscratch/sd/k/krydzy/SWE-agent/metis-4.0/` -> `metis-4.0.3/` -- domain decomposition

## Build (Perlmutter)

### Via Harness (recommended)
```bash
module load python cmake openmpi/5.0.7 cuda/12.4
export LAGHOS_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Laghos_test
python3 tools/laghos_harness/bin/laghos_build           # standard build
python3 tools/laghos_harness/bin/laghos_build --setup    # first-time (builds deps)
python3 tools/laghos_harness/bin/laghos_build --clean    # clean rebuild
```

### Manual Build
```bash
cd Laghos_test
make setup MFEM_BUILD=pcuda   # builds hypre, METIS, MFEM with CUDA
make -j8                       # builds Laghos
```

## Run

### Via Harness (recommended)
```bash
python3 tools/laghos_harness/bin/laghos_run                          # default benchmark
python3 tools/laghos_harness/bin/laghos_run -p 1 --dim 2 --rs 3 --tf 0.8 -d cuda  # custom
```

The run harness: (1) builds pristine Laghos if needed, (2) runs pristine baseline, (3) runs modified version with same params, (4) compares final energy `|e|` for correctness (tolerance 1e-8), (5) reports speedup.

### Correctness Validation
**Primary metric**: final energy `|e|`. The harness compares `final_energy`, `final_step`, and `final_dt` between baseline and modified runs. Tolerance: 1e-8 relative error on energy.

## Common Issues

- **"MFEM library is not built"** -- Run `make setup MFEM_BUILD=pcuda` first, or use `laghos_build --setup`.
- **METIS download failure** -- Upstream URL unreliable; use `scripts/setup_apps.sh` which tries mirror URLs.
- **CUDA math linker errors (`-lcusparse`, `-lcublas`)** -- Set `LIBRARY_PATH` to include `math_libs/` path.
- **"1D test not supported on device"** -- Problem `-p 2` doesn't work with `-d cuda`; use `-d cpu`.
- **Very slow GPU runs** -- Ensure `-pa` is used; full assembly is much slower on GPU for high orders.
- **Shared deps** -- `../mfem`, `../hypre`, `../metis-4.0` are shared between pristine and test copies.
- **Each `laghos_run` takes 60-120s** -- Runs both baseline and modified end-to-end.

## SWE-agent Configuration

- `config/hpc/laghos_no_profiling.yaml` -- Standard optimization run
- `config/hpc/laghos_with_profiling.yaml` -- With HPCToolkit/hatchet profiling
- Key env vars: `CUDA_VISIBLE_DEVICES=0,1,2,3`, `OMP_NUM_THREADS=32`, `LAGHOS_ROOT`
- Agent editable files: `laghos.cpp`, `laghos_solver.cpp`, `laghos_assembly.cpp` (NOT makefile)

For detailed reference, see references/ in this skill directory.
