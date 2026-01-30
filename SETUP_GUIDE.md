# HPC Proxy Application Setup Guide

Setup instructions for building the four LLNL/CEED proxy applications on NERSC Perlmutter with CUDA/GPU support.

---

## Quick Setup (Recommended)

From the SWE-agent root directory, run:

```bash
./scripts/setup_apps.sh
```

This single command will:
1. Load the required modules (`openmpi/5.0.7`, `cuda/12.4`)
2. Clone all 4 proxy apps from GitHub (correct branches and submodules)
3. Build each app with CUDA/GPU support
4. Create `_test/` working copies for agent experiments

Options:
```bash
./scripts/setup_apps.sh --kripke --lulesh   # Setup specific apps only
./scripts/setup_apps.sh --no-build          # Clone and copy without building
./scripts/setup_apps.sh --no-test           # Skip creating _test copies
./scripts/setup_apps.sh --prefix /scratch/apps  # Install apps to a custom directory
```

The `--prefix` flag clones and builds the apps in the specified directory instead of the SWE-agent root, then creates symlinks back so all harness scripts still work.

After running the script, set up the remaining tools:

```bash
# Spack + HPCToolkit (for profiling)
git clone -c feature.manyFiles=true https://github.com/spack/spack.git ~/spack
cd ~/spack && git checkout releases/v0.23
source ~/spack/share/spack/setup-env.sh
spack install hpctoolkit@2025.01.1

# Python environment (for SWE-agent)
python -m venv ~/envs/sweagent
source ~/envs/sweagent/bin/activate
cd /path/to/SWE-agent
pip install -e .

# Hatchet (performance analysis)
git clone https://github.com/LLNL/hatchet.git ~/hatchet
pip install -e ~/hatchet
```

To reset test repos between agent runs:
```bash
./scripts/reset_test_repos.sh
```

---

## Manual Setup

Step-by-step instructions for setting up each component individually.

### Prerequisites

```bash
module load openmpi/5.0.7
module load cuda/12.4
module load python
```

### 1. Kripke (3D Sn Deterministic Transport)

**Repository:**
```bash
git clone --recursive https://github.com/LLNL/Kripke.git
cd Kripke
git checkout develop
git submodule update --init --recursive
```

**Build (CUDA via RAJA):**
```bash
mkdir build && cd build
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DENABLE_CUDA=ON \
  -DENABLE_MPI=ON \
  -DCMAKE_CXX_COMPILER=mpicxx \
  -DCMAKE_C_COMPILER=mpicc \
  -DCMAKE_CUDA_ARCHITECTURES=80
make -j8
```

**Executable:** `build/bin/kripke.exe`

**Notes:**
- Uses RAJA portability layer; supports Sequential, OpenMP, CUDA, HIP backends
- Submodules include RAJA and BLT (build system)
- **Must use `develop` branch** — contains CUDA/RAJA support
- Version used: v1.2.7

**Create test copy:**
```bash
cd /path/to/SWE-agent
cp -r Kripke Kripke_test
```

---

### 2. Laghos (Lagrangian High-Order Solver)

**Repository:**
```bash
git clone https://github.com/CEED/Laghos.git
cd Laghos
```

**Build (CUDA with auto-built dependencies):**
```bash
# Downloads and builds MFEM, hypre (v2.11.2), and METIS (v4.0.3) automatically
make setup MFEM_BUILD=pcuda
make -j8
```

**Executable:** `laghos`

**Notes:**
- Dependencies (MFEM, hypre, METIS) are fetched and built automatically by `make setup`
- `pcuda` = parallel CUDA build (MPI + CUDA)
- `make setup` creates `mfem/`, `hypre/`, `metis-4.0/` as sibling directories
- Version used: v3.1 (master branch)
- MFEM is cloned from https://github.com/mfem/mfem.git

**Create test copy:**
```bash
cd /path/to/SWE-agent
cp -r Laghos Laghos_test
# Both copies share the sibling mfem/hypre/metis-4.0 directories
```

---

### 3. LULESH (Livermore Unstructured Lagrangian Explicit Shock Hydrodynamics)

**Repository:**
```bash
git clone https://github.com/LLNL/LULESH.git Lulesh
cd Lulesh
git checkout 2.0.2-dev
cd cuda
```

**Build (CUDA):**
```bash
make -j8
```

The Makefile uses `nvcc` with `-arch=sm_80` (A100). If targeting a different GPU, edit `CUDA_ARCH` in the Makefile.

**Executable:** `cuda/lulesh`

**Notes:**
- **Must use `2.0.2-dev` branch** — `master` does not contain the CUDA port
- The `2.0.2-dev` branch has multiple ports: `cuda/`, `openacc/`, `omp_4.0/`, `stdpar/`
- No external dependencies beyond CUDA toolkit

**Create test copy:**
```bash
cd /path/to/SWE-agent
cp -r Lulesh Lulesh_test
```

---

### 4. Quicksilver (Monte Carlo Particle Transport)

**Repository:**
```bash
git clone https://github.com/LLNL/Quicksilver.git
cd Quicksilver/src
```

**Build (CUDA + OpenMP):**
```bash
make -j8
```

The Makefile uses `nvcc` with `-arch=sm_80` and `-Xcompiler -fopenmp`. Edit the Makefile if targeting a different GPU architecture.

**Executable:** `src/qs`

**Notes:**
- No MPI in current build configuration
- Uses OpenMP for host-side threading alongside CUDA
- Version used: V1.0 (master branch)

**Create test copy:**
```bash
cd /path/to/SWE-agent
cp -r Quicksilver Quicksilver_test
```

---

### 5. Spack + HPCToolkit (Profiling)

```bash
git clone -c feature.manyFiles=true https://github.com/spack/spack.git ~/spack
cd ~/spack && git checkout releases/v0.23
source ~/spack/share/spack/setup-env.sh
spack install hpctoolkit@2025.01.1
```

### 6. Python Environment + SWE-agent

```bash
python -m venv ~/envs/sweagent
source ~/envs/sweagent/bin/activate
cd /path/to/SWE-agent
pip install -e .
```

### 7. Hatchet (Performance Analysis)

```bash
git clone https://github.com/LLNL/hatchet.git ~/hatchet
pip install -e ~/hatchet
```

---

## Directory Layout

After setup, the expected directory structure is:
```
SWE-agent/
├── Kripke/          # Pristine clone (baseline for comparisons)
├── Kripke_test/     # Working copy for agent experiments
├── Laghos/
├── Laghos_test/
├── Lulesh/
├── Lulesh_test/
├── Quicksilver/
├── Quicksilver_test/
├── mfem/            # Laghos dependency (shared by both copies)
├── hypre/           # Laghos dependency
├── metis-4.0/       # Laghos dependency
├── tools/           # Harness scripts for each app
├── config/          # SWE-agent YAML configs
├── batch/           # Batch automation scripts
├── dataset/         # Performance commit dataset
└── scripts/         # setup_apps.sh, reset_test_repos.sh
```

The `*_test/` directories are working copies that get reset between agent runs via `scripts/reset_test_repos.sh`.

## Resetting Test Repos

```bash
./scripts/reset_test_repos.sh              # Reset and rebuild all
./scripts/reset_test_repos.sh --lulesh     # Reset only Lulesh
./scripts/reset_test_repos.sh --no-build   # Reset without rebuilding
```

---

## Environment Variables

Scripts resolve paths automatically via relative paths from the SWE-agent directory structure. If your layout differs, the following environment variables are supported:

### General
| Variable | Purpose | Default |
|----------|---------|---------|
| `SWEAGENT_ROOT` | Root SWE-agent directory | Derived from script location |
| `SWEAGENT_VENV` | Path to sweagent Python venv | `~/envs/sweagent` |

### App root paths (for build/run harness scripts)
| Variable | Purpose | Expected path |
|----------|---------|---------------|
| `KRIPKE_ROOT` | Kripke working copy | `$SWEAGENT_ROOT/Kripke_test` |
| `LAGHOS_ROOT` | Laghos working copy | `$SWEAGENT_ROOT/Laghos_test` |
| `LULESH_ROOT` | Lulesh working copy (cuda subdir) | `$SWEAGENT_ROOT/Lulesh_test/cuda` |
| `QUICKSILVER_ROOT` | Quicksilver working copy | `$SWEAGENT_ROOT/Quicksilver_test` |

### Pristine (baseline) repo paths (for run/check_correct scripts)
| Variable | Purpose | Expected path |
|----------|---------|---------------|
| `PRISTINE_KRIPKE_ROOT` | Unmodified Kripke for baseline | `$SWEAGENT_ROOT/Kripke` |
| `PRISTINE_LAGHOS_ROOT` | Unmodified Laghos for baseline | `$SWEAGENT_ROOT/Laghos` |
| `PRISTINE_LULESH_ROOT` | Unmodified Lulesh for baseline | `$SWEAGENT_ROOT/Lulesh/cuda` |
| `PRISTINE_QS_ROOT` | Unmodified Quicksilver for baseline | `$SWEAGENT_ROOT/Quicksilver` |

If you keep the standard directory layout, none of these need to be set.
