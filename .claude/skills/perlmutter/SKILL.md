---
name: perlmutter
description: "Knowledge about NERSC Perlmutter supercomputer including SLURM job submission, module loading, GPU node specifications, and compute allocation. Load this skill when building, running, or debugging anything on Perlmutter."
---

# NERSC Perlmutter

## Hardware

**GPU Nodes (1,792)**: AMD EPYC 7763 (64 cores), 256 GB DDR4, 4x NVIDIA A100 (40 GB or 80 GB HBM), NVLink 3.0, CUDA `sm_80`.
**Per-A100 Performance**: FP64 9.7 TFLOPS, FP32 19.5 TFLOPS.

## SLURM Job Submission

Account: always `-A m2404`.

### QOS Limits (GPU)

| QOS | Max Nodes | Max Walltime | Notes |
|-----|-----------|-------------|-------|
| `regular` | Unlimited | 48 hrs | Standard production |
| `debug` | 8 | 30 min | Quick testing, max 2 running |
| `interactive` | 4 | 4 hrs | Interactive, max 2 running |
| `shared` | 0.5 (1-2 GPUs) | 48 hrs | Sub-node jobs |
| `shared_interactive` | 0.5 | 4 hrs | Interactive sub-node, max 2 |
| `preempt` | 128 | 48 hrs | 0.25x charge, can be preempted |
| `overrun` | Unlimited | 48 hrs | Free, lowest priority |

### Interactive GPU Allocation

```bash
salloc --nodes 1 --qos interactive --time 03:00:00 --constraint gpu --gpus 4 --account m2404
```

### Standard Batch Header (Full Node)

```bash
#!/bin/bash
#SBATCH -A m2404
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 4:00:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
```

## Module Loading

### Build Modules (compiling on compute nodes)
```bash
module load python cmake openmpi/5.0.7 cuda/12.4
```

### Runtime Modules (batch jobs)
```bash
module load python openmpi/5.0.7 cudatoolkit/12.4
```

**Important**: Build uses `cuda/12.4`, runtime uses `cudatoolkit/12.4` -- different module names, both CUDA 12.4.

### HPCToolkit
```bash
source ~/spack/share/spack/setup-env.sh
spack load hpctoolkit
```

## Filesystems

| Path | Variable | Purge | Purpose |
|------|----------|-------|---------|
| `/global/homes/k/krydzy` (`/global/u2/k/krydzy`) | `$HOME` | No | Small configs, venvs, dotfiles |
| `/pscratch/sd/k/krydzy` | `$PSCRATCH` | Yes | **Primary workspace**: SWE-agent, proxy apps, all large repos |

`$PSCRATCH` is high-performance Lustre. SWE-agent and all proxy app repos live here to avoid $HOME quota limits. Git repos are backed by version control so purge risk is acceptable.

## CUDA Environment

### Architecture Flag
Always `sm_80` for A100:
```bash
-DCMAKE_CUDA_ARCHITECTURES=80       # CMake
-arch=sm_80                          # nvcc directly
```

### CUDA Math Libraries
Math libs (`cusparse`, `cublas`, etc.) are in a separate path on Perlmutter:
```bash
CUDA_MATH_LIBS="${CUDA_HOME/cuda/math_libs}/lib64"
export LD_LIBRARY_PATH="$CUDA_MATH_LIBS:$LD_LIBRARY_PATH"
export LIBRARY_PATH="$CUDA_MATH_LIBS:${LIBRARY_PATH:-}"
```

### Host Compiler
- Default g++ works for most apps (Kripke, Laghos)
- **Lulesh and Quicksilver need `g++-12`** -- nvcc incompatible with g++ 13 for `-std=c++11`

## Common Issues

- **"No CUDA-capable device"**: Forgot `--gpus-per-node=4` or `--gpus-per-task=1` in SLURM.
- **"nvcc not found"**: Building on a login node. Get an interactive allocation first.
- **"Module not found"**: Use `module avail <name>`. Tested versions: `openmpi/5.0.7`, `cuda/12.4`, `cudatoolkit/12.4`.
- **Git hanging on Kripke**: 44+ submodules. Fix: `git config --local submodule.recurse false` and `git remote remove origin`.
- **SLURM job pending forever**: Check balance with `iris`. Try `debug` (30 min) or `overrun` (free, low priority). Check queue: `sqs`.

## Useful Commands

```bash
iris                                # check allocation balance
squeue -u $USER                     # job status (or sqs)
scancel <job_id>                    # cancel a job
scontrol show node <nodename>       # node info
nvidia-smi                          # GPU utilization (compute node only)
sacct -j <job_id> --format=JobID,Elapsed,MaxRSS,State,ExitCode  # completed job details
module list                         # currently loaded modules
module avail cuda                   # available versions
module spider openmpi               # search for module
```
