# Perlmutter Hardware & Environment Reference

## Hardware Specs

**GPU Nodes (1,792)**: AMD EPYC 7763 (64 cores), 256 GB DDR4, 4x NVIDIA A100 (40 GB or 80 GB HBM), NVLink 3.0, CUDA `sm_80`.
**Per-A100 Performance**: FP64 9.7 TFLOPS, FP32 19.5 TFLOPS.

## Filesystems

| Path | Variable | Purge | Purpose |
|------|----------|-------|---------|
| `/global/homes/k/krydzy` (`/global/u2/k/krydzy`) | `$HOME` | No | Small configs, venvs, dotfiles |
| `/pscratch/sd/k/krydzy` | `$PSCRATCH` | Yes | **Primary workspace**: SWE-agent, proxy apps, all large repos |

`$PSCRATCH` is high-performance Lustre. SWE-agent and all proxy app repos live here to avoid $HOME quota limits. Git repos are backed by version control so purge risk is acceptable.

## CUDA Math Libraries

Math libs (`cusparse`, `cublas`, etc.) are in a separate path on Perlmutter:
```bash
CUDA_MATH_LIBS="${CUDA_HOME/cuda/math_libs}/lib64"
export LD_LIBRARY_PATH="$CUDA_MATH_LIBS:$LD_LIBRARY_PATH"
export LIBRARY_PATH="$CUDA_MATH_LIBS:${LIBRARY_PATH:-}"
```

## HPCToolkit (via Spack)

```bash
source ~/spack/share/spack/setup-env.sh
spack load hpctoolkit
```

## Full QOS Table (GPU)

| QOS | Max Nodes | Max Walltime | Notes |
|-----|-----------|-------------|-------|
| `regular` | Unlimited | 48 hrs | Standard production |
| `debug` | 8 | 30 min | Quick testing, max 2 running |
| `interactive` | 4 | 4 hrs | Interactive, max 2 running |
| `shared` | 0.5 (1-2 GPUs) | 48 hrs | Sub-node jobs |
| `shared_interactive` | 0.5 | 4 hrs | Interactive sub-node, max 2 |
| `preempt` | 128 | 48 hrs | 0.25x charge, can be preempted |
| `overrun` | Unlimited | 48 hrs | Free, lowest priority |

## Additional Useful Commands

```bash
scontrol show node <nodename>       # node info
sacct -j <job_id> --format=JobID,Elapsed,MaxRSS,State,ExitCode  # completed job details
module spider openmpi               # search for module
```
