# Laghos Dependencies and Internals

## CUDA Math Libraries

On Perlmutter, `cusparse`/`cublas`/`cusolver`/`curand` are in a separate path. The harness sets this automatically; for manual builds:
```bash
export LIBRARY_PATH=/opt/nvidia/hpc_sdk/Linux_x86_64/24.5/math_libs/12.4/lib64:$LIBRARY_PATH
```

## METIS Download Fallback

Upstream URL often fails. Mirrors tried by setup scripts:
1. `http://glaros.dtc.umn.edu/gkhome/fetch/sw/metis/OLD/metis-4.0.3.tar.gz`
2. `https://github.com/mfem/tpls/raw/gh-pages/metis-4.0.3.tar.gz`
3. `https://ftp.mcs.anl.gov/pub/petsc/externalpackages/metis-4.0.3.tar.gz`

## Dependency Paths

| Dependency | Path | Description |
|------------|------|-------------|
| MFEM | `/pscratch/sd/k/krydzy/SWE-agent/mfem/` | Finite element library |
| hypre | `/pscratch/sd/k/krydzy/SWE-agent/hypre/` -> `hypre-2.11.2/` | Parallel linear algebra |
| METIS | `/pscratch/sd/k/krydzy/SWE-agent/metis-4.0/` -> `metis-4.0.3/` | Domain decomposition |

Both `Laghos/` and `Laghos_test/` share these via relative paths (`../mfem`, etc.).

## Test Problems

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

## Key CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `-p <n>` | 1 | Problem type (see table above) |
| `-dim <d>` | 3 | Spatial dimension (1, 2, or 3) |
| `-rs <n>` | 0 | Serial mesh refinement levels |
| `-tf <t>` | 0.8 | Final simulation time |
| `-pa` | -- | Partial assembly (better GPU perf, use for high order) |
| `-d <dev>` | cpu | Device: `cpu`, `cuda`, `hip`, etc. |

## Key Source Files

### Core Source (optimization targets)

| File | Description |
|------|-------------|
| `laghos.cpp` | Main driver, time integration loop, CLI parsing |
| `laghos_solver.cpp` | `LagrangianHydroOperator::Mult()`, timing output |
| `laghos_assembly.cpp` | `ForcePAOperator`, `MassPAOperator` -- **main computational kernels** |

**Important**: Most GPU computation happens **inside MFEM**, not Laghos directly. Laghos calls MFEM operators that dispatch to CUDA kernels. For deeper GPU optimization, look into `../mfem/` source.

## Output Format

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

## Additional Notes

- Upstream: https://github.com/CEED/Laghos (branch: `master`)
- Source files missing in `_test` after git ops -- Harness auto-copies from pristine directory.
- Wrong energy values -- Verify `-pa` flag and that MFEM was built with CUDA (`pcuda`).
