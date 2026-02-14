---
name: perlmutter
description: "NERSC Perlmutter GPU cluster reference. Use when user mentions 'perlmutter', 'salloc', 'sbatch', 'srun', 'module load', 'compute node', 'GPU allocation', SLURM errors, or NERSC-specific configuration."
user-invocable: false
---

# NERSC Perlmutter

For detailed reference, see references/ in this skill directory.

## SLURM Job Submission

Account: always `-A m2404`.

### QOS Limits (GPU)

| QOS | Max Nodes | Max Walltime | Notes |
|-----|-----------|-------------|-------|
| `regular` | Unlimited | 48 hrs | Standard production |
| `debug` | 8 | 30 min | Quick testing, max 2 running |
| `interactive` | 4 | 4 hrs | Interactive, max 2 running |
| `shared` | 0.5 (1-2 GPUs) | 48 hrs | Sub-node jobs |

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

## CUDA Environment

Always `sm_80` for A100:
```bash
-DCMAKE_CUDA_ARCHITECTURES=80       # CMake
-arch=sm_80                          # nvcc directly
```

### Host Compiler
- Default g++ works for most apps (Kripke, Laghos)
- **Lulesh and Quicksilver need `g++-12`** -- nvcc incompatible with g++ 13 for `-std=c++11`

## Common Issues

- **"No CUDA-capable device"**: Forgot `--gpus-per-node=4` or `--gpus-per-task=1` in SLURM.
- **"nvcc not found"**: Building on a login node. Get an interactive allocation first.
- **"Module not found"**: Use `module avail <name>`. Tested: `openmpi/5.0.7`, `cuda/12.4`, `cudatoolkit/12.4`.
- **Git hanging on Kripke**: 44+ submodules. Fix: `git config --local submodule.recurse false`.
- **SLURM job pending forever**: Check balance with `iris`. Try `debug` or `overrun`.

## Useful Commands

```bash
iris                                # check allocation balance
squeue -u $USER                     # job status (or sqs)
scancel <job_id>                    # cancel a job
nvidia-smi                          # GPU utilization (compute node only)
module list                         # currently loaded modules
module avail cuda                   # available versions
```
