---
name: nsight-systems
description: "Knowledge about NVIDIA Nsight Systems for system-wide GPU timeline profiling including nsys CLI usage, trace collection, SQLite export, nsight-python API for analysis, MPI+CUDA profiling, and integration with our tool-calling format. Load when implementing or debugging Nsight Systems-based profiling tools."
---

# NVIDIA Nsight Systems (nsys) — Perlmutter Reference

**nsys vs ncu**: nsys = system-wide timeline ("where is time spent?"). ncu = per-kernel deep-dive ("why is this kernel slow?"). Start with nsys to find hotspots, then ncu on top 1-3 kernels.

## Perlmutter Paths

| | cudatoolkit/12.4 (default) | cudatoolkit/12.9 |
|---|---|---|
| **nsys version** | 2024.1.1.59 | 2025.3.1.90 |
| **nsys binary** | `/opt/nvidia/hpc_sdk/Linux_x86_64/24.5/profilers/Nsight_Systems/bin/nsys` | `.../25.5/.../bin/nsys` |

**nsight-python** (`/pscratch/sd/k/krydzy/nsight-python/`) is **ncu-only** — no nsys support.

## Project Integration

- `tools/system_info/bin/check_profiling_ready` — checks nsys on PATH
- **No dedicated nsys tool wrapper yet** — `tools/nsight_systems/` needs to be created

### Planned SWE-Agent Tool

```yaml
tools:
  nsys_profile:
    signature: "nsys_profile <executable> <output_dir> [<trace_types>] [<app_args>...]"
    docstring: "Profile GPU app with Nsight Systems. Default traces: cuda,nvtx,osrt. Add 'mpi' for MPI apps."
  nsys_stats:
    signature: "nsys_stats <report_file> [<report_type>]"
    docstring: "Extract stats from .nsys-rep. Types: cuda_gpu_kern_sum (default), cuda_api_sum, mpi_event_sum, nvtx_sum, osrt_sum."
```

### Recommended Agent Workflow

1. `check_profiling_ready` → verify GPU and tools
2. `nsys_profile ./executable ./output cuda,nvtx,osrt,mpi` → timeline
3. `nsys_stats ./output/report.nsys-rep cuda_gpu_kern_sum` → hot kernels
4. `nsys_stats ./output/report.nsys-rep mpi_event_sum` → MPI overhead
5. If kernel dominates → `ncu_profile ./executable ./ncu_output --kernel-filter "hotKernel"`

## MPI Profiling on Perlmutter

```bash
nsys profile --trace=cuda,nvtx,osrt,mpi --mpi-impl=openmpi \
    -o report_%h_%p -f true \
    srun -n <N> ./executable [args...]
```

- Perlmutter uses **OpenMPI** (`module load openmpi/5.0.7`), so `--mpi-impl=openmpi`
- Use **`srun`** (not `mpirun`) on Perlmutter
- Each rank gets its own `.nsys-rep` (use `%h_%p` in output name)

## SQLite Export & Analysis

```bash
nsys export --type=sqlite --output=report.sqlite report.nsys-rep
```

**Key tables**:

| Table | Key Columns |
|-------|-------------|
| `CUPTI_ACTIVITY_KIND_KERNEL_NAMED` | `start`, `end`, `name`, `deviceId`, `streamId`, grid/block dims, registers, shared mem |
| `CUPTI_ACTIVITY_KIND_MEMCPY` | `start`, `end`, `bytes`, `srcKind`, `dstKind` |
| `NVTX_EVENTS` | `start`, `end`, `textId`, `domainId` |
| `MPI_P2P_EVENTS` / `MPI_COLLECTIVES_EVENTS` | `start`, `end`, `textId`, `globalTid` |
| `StringIds` | `id`, `value` — join with `textId`/`nameId` |

**Top kernels query**:
```sql
SELECT name, count(*) AS launches, sum(end-start) AS total_ns, avg(end-start) AS avg_ns
FROM CUPTI_ACTIVITY_KIND_KERNEL_NAMED
GROUP BY name ORDER BY total_ns DESC LIMIT 10
```

## Features New in 12.9 (nsys 2025.3)

- **`--pytorch`** (2025.1) — PyTorch module tracing, autograd NVTX markers
- **`--dask`** (2025.2) — Dask distributed computing trace
- **Lustre metrics** (2024.7 GA) — client-side Lustre I/O, relevant for `/global/`
- **Analysis recipes** (`nsys recipe`): `communications`, `nccl_identification`, `compute_overlap`, `heatmap_overview`, `gpu_metrics_per_range`
- **`cuda-hw` trace** (2025.2 Beta) — hardware-based low-overhead, Blackwell only (not A100)

### Deprecated in 12.9

- Pascal/Volta dropped (A100 still supported)
- `text` export deprecated → use `sqlite`
- `libnvToolsExt.so` not shipped → use `nvtx3/nvtx3.hpp` or `pip install nvtx`

## Common Issues

- **Must run on compute nodes**: `salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 1 --account m2404`
- **DCGM conflicts**: `dcgmi profile --pause` before profiling
- **"No CUDA events collected"**: Verify app uses CUDA, `--trace=cuda` is set, and on compute node
- **Large reports**: Use `--duration=30`, `--delay=10`, or `--capture-range=nvtx` to limit
- **MPI per-rank reports**: Each rank gets own `.nsys-rep`. Export each to SQLite, or use `nsys recipe`
- **"table not found" in nsys stats**: Trace didn't capture that type (e.g., `mpi_event_sum` needs `--trace=mpi`)
- **Don't run nsys + ncu simultaneously** — both instrument CUDA
