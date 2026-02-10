---
name: laghos
description: "Knowledge about the Laghos high-order Lagrangian hydrodynamics proxy application including build configuration, run parameters, MFEM dependency, expected output, and correctness validation. Load when working on Laghos benchmarks or harnesses."
---

# Laghos

**LAGrangian High-Order Solver** -- compressible gas dynamics via high-order Lagrangian finite elements. MFEM-based, part of the CEED suite, proxy for LLNL's BLAST hydrocode.

## Source Location

- **Pristine clone**: `/pscratch/sd/k/krydzy/SWE-agent/Laghos/` (never modify)
- **Working copy**: `/pscratch/sd/k/krydzy/SWE-agent/Laghos_test/` (agent experiments)
- **Upstream**: https://github.com/CEED/Laghos (branch: `master`)
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

### CUDA Math Libraries
On Perlmutter, `cusparse`/`cublas`/`cusolver`/`curand` are in a separate path. The harness sets this automatically; for manual builds:
```bash
export LIBRARY_PATH=/opt/nvidia/hpc_sdk/Linux_x86_64/24.5/math_libs/12.4/lib64:$LIBRARY_PATH
```

### METIS Download Fallback
Upstream URL often fails. Mirrors tried by setup scripts:
1. `http://glaros.dtc.umn.edu/gkhome/fetch/sw/metis/OLD/metis-4.0.3.tar.gz`
2. `https://github.com/mfem/tpls/raw/gh-pages/metis-4.0.3.tar.gz`
3. `https://ftp.mcs.anl.gov/pub/petsc/externalpackages/metis-4.0.3.tar.gz`

## Run

### Via Harness (recommended)
```bash
python3 tools/laghos_harness/bin/laghos_run                          # default benchmark
python3 tools/laghos_harness/bin/laghos_run -p 1 --dim 2 --rs 3 --tf 0.8 -d cuda  # custom
```

The run harness: (1) builds pristine Laghos if needed, (2) runs pristine baseline, (3) runs modified version with same params, (4) compares final energy `|e|` for correctness (tolerance 1e-8), (5) reports speedup.

### Test Problems

| `-p` | Problem | Description | Notes |
|------|---------|-------------|-------|
| 0 | Taylor-Green vortex | Smooth flow | Tests all kernels except viscosity |
| 1 | Sedov blast | Shock wave | **Primary benchmark** |
| 2 | Sod shock tube | 1D shock | Not supported on GPU |
| 3 | Triple-point | Multi-material shock | Complex test |
| 4 | Gresho vortex | Smooth rotating flow | Tests all kernels except viscosity |
| 5 | Riemann config 12 | 2D Riemann problem | -- |
| 6 | Riemann config 6 | 2D Riemann problem | -- |
| 7 | Rayleigh-Taylor | Instability problem | -- |

### Key CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `-p <n>` | 1 | Problem type (see table above) |
| `-dim <d>` | 3 | Spatial dimension (1, 2, or 3) |
| `-rs <n>` | 0 | Serial mesh refinement levels |
| `-tf <t>` | 0.8 | Final simulation time |
| `-pa` | -- | Partial assembly (better GPU perf, use for high order) |
| `-d <dev>` | cpu | Device: `cpu`, `cuda`, `hip`, etc. |

## Key Files

### Core Source (optimization targets)

| File | Description |
|------|-------------|
| `laghos.cpp` | Main driver, time integration loop, CLI parsing |
| `laghos_solver.cpp` | `LagrangianHydroOperator::Mult()`, timing output |
| `laghos_assembly.cpp` | `ForcePAOperator`, `MassPAOperator` -- **main computational kernels** |

**Important**: Most GPU computation happens **inside MFEM**, not Laghos directly. Laghos calls MFEM operators that dispatch to CUDA kernels. For deeper GPU optimization, look into `../mfem/` source.

## Output

### Step-by-Step Progress
```
   step     68,	t = 0.5000,	dt = 0.002180,	|e| = 2.4958996352e+01
```

### Performance Timing (printed at end)
```
CG (H1) total time: 12.345
CG (H1) rate (megadofs x cg_iterations / second): 1234.56
Forces total time: 4.567
UpdateQuadData total time: 2.345
Major kernels total time (seconds): 19.257
Major kernels total rate (megadofs x time steps / second): 123.45
```

### Correctness Validation
**Primary metric**: final energy `|e|`. The harness compares `final_energy`, `final_step`, and `final_dt` between baseline and modified runs. Tolerance: 1e-8 relative error on energy.

## Common Issues

- **"MFEM library is not built"** -- Run `make setup MFEM_BUILD=pcuda` first, or use `laghos_build --setup`.
- **METIS download failure** -- Upstream URL unreliable; use `scripts/setup_apps.sh` which tries mirror URLs.
- **CUDA math linker errors (`-lcusparse`, `-lcublas`)** -- Set `LIBRARY_PATH` to include `math_libs/` path (see Build section).
- **Source files missing in `_test` after git ops** -- Harness auto-copies from pristine directory.
- **"1D test not supported on device"** -- Problem `-p 2` doesn't work with `-d cuda`; use `-d cpu`.
- **Wrong energy values** -- Verify `-pa` flag and that MFEM was built with CUDA (`pcuda`).
- **Very slow GPU runs** -- Ensure `-pa` is used; full assembly is much slower on GPU for high orders.
- **Shared deps** -- `../mfem`, `../hypre`, `../metis-4.0` are shared between pristine and test copies.
- **Each `laghos_run` takes 60-120s** -- Runs both baseline and modified end-to-end.

## SWE-agent Configuration

Config files:
- `config/hpc/laghos_no_profiling.yaml` -- Standard optimization run
- `config/hpc/laghos_with_profiling.yaml` -- With HPCToolkit/hatchet profiling

Key env vars: `CUDA_VISIBLE_DEVICES=0,1,2,3`, `OMP_NUM_THREADS=32`, `LAGHOS_ROOT=/pscratch/sd/k/krydzy/SWE-agent/Laghos_test`

Agent editable files: `laghos.cpp`, `laghos_solver.cpp`, `laghos_assembly.cpp`, `makefile`
