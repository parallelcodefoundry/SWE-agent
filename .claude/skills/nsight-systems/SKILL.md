---
name: nsight-systems
description: "NVIDIA Nsight Systems GPU timeline profiling: nsys CLI, trace collection, SQLite export. Use when user mentions 'nsight systems', 'nsys', 'timeline profiling', 'GPU trace', or MPI+CUDA system-wide profiling."
user-invocable: false
---

# NVIDIA Nsight Systems (nsys) -- Perlmutter Reference

**nsys vs ncu**: nsys = system-wide timeline ("where is time spent?"). ncu = per-kernel deep-dive ("why is this kernel slow?"). Start with nsys to find hotspots, then ncu on top 1-3 kernels.

For detailed reference, see references/ in this skill directory.

## Perlmutter Paths

| | cudatoolkit/12.4 (default) | cudatoolkit/12.9 |
|---|---|---|
| **nsys version** | 2024.1.1.59 | 2025.3.1.90 |
| **nsys binary** | `/opt/nvidia/hpc_sdk/Linux_x86_64/24.5/profilers/Nsight_Systems/bin/nsys` | `.../25.5/.../bin/nsys` |

## MPI Profiling on Perlmutter

```bash
nsys profile --trace=cuda,nvtx,osrt,mpi --mpi-impl=openmpi \
    -o report_%h_%p -f true \
    srun -n <N> ./executable [args...]
```

- Perlmutter uses **OpenMPI** (`module load openmpi/5.0.7`), so `--mpi-impl=openmpi`
- Use **`srun`** (not `mpirun`) on Perlmutter
- Each rank gets its own `.nsys-rep` (use `%h_%p` in output name)

## Recommended Agent Workflow

1. `check_profiling_ready` -- verify GPU and tools
2. `nsys profile --trace=cuda,nvtx,osrt,mpi -o report ./executable` -- timeline
3. `nsys stats report.nsys-rep --report cuda_gpu_kern_sum` -- hot kernels
4. `nsys stats report.nsys-rep --report mpi_event_sum` -- MPI overhead
5. If kernel dominates -- use ncu on the hot kernel

## SQLite Export (Quick Reference)

```bash
nsys export --type=sqlite --output=report.sqlite report.nsys-rep
```

Top kernels query:
```sql
SELECT name, count(*) AS launches, sum(end-start) AS total_ns, avg(end-start) AS avg_ns
FROM CUPTI_ACTIVITY_KIND_KERNEL_NAMED
GROUP BY name ORDER BY total_ns DESC LIMIT 10
```

## Project Integration

- `tools/nsight_systems/config.yaml` -- SWE-agent tool definition
- `tools/nsight_systems/bin/nsys_profile` -- Profiling script
- `tools/system_info/bin/check_profiling_ready` -- checks nsys on PATH
- `tools/system_info/bin/profiler_info` -- lists nsys/ncu presence
- All `config/hpc/*_with_profiling.yaml` configs include `tools/nsight_systems` in bundles
- `batch/frameworks/base.py` PROFILING_TOOL_DIRS includes `tools/nsight_systems/bin`

### SWE-Agent Tool Usage

```
nsys_profile <executable> <output_dir> [<app_args>...]
```

- Runs `nsys profile --trace=cuda,nvtx,osrt --cuda-memory-usage=true`
- Extracts top kernels via `nsys stats --report=cuda_gpu_kern_sum`
- Extracts CUDA API via `nsys stats --report=cuda_api_sum`
- Runs `nsys analyze` with 6 expert rules (sync issues, pageable memory, GPU gaps, utilization)
- Outputs: `report.nsys-rep` (binary), `cuda_kern_summary.txt`, `cuda_api_summary.txt`, `expert_analysis.txt`, `summary.txt`
- All analysis is printed to stdout (agent sees it inline) + saved to files
- Auto-pauses/resumes DCGM on managed clusters

### When to Use nsys vs ncu

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `nsys_profile` | System-wide timeline | **First** — find which kernels are hotspots |
| `ncu_profile` | Per-kernel deep-dive | **Second** — analyze why top kernel(s) are slow |

## Common Issues

- **Must run on compute nodes**: `salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 1 --account m5083`
- **DCGM conflicts**: `dcgmi profile --pause` before profiling
- **"No CUDA events collected"**: Verify app uses CUDA, `--trace=cuda` is set, and on compute node
- **Large reports**: Use `--duration=30`, `--delay=10`, or `--capture-range=nvtx` to limit
- **"table not found" in nsys stats**: Trace didn't capture that type (e.g., needs `--trace=mpi`)
- **Don't run nsys + ncu simultaneously** -- both instrument CUDA
