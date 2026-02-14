# Nsight Systems SQLite Export Reference

## Export Command

```bash
nsys export --type=sqlite --output=report.sqlite report.nsys-rep
```

## Key Tables

| Table | Key Columns |
|-------|-------------|
| `CUPTI_ACTIVITY_KIND_KERNEL_NAMED` | `start`, `end`, `name`, `deviceId`, `streamId`, grid/block dims, registers, shared mem |
| `CUPTI_ACTIVITY_KIND_MEMCPY` | `start`, `end`, `bytes`, `srcKind`, `dstKind` |
| `NVTX_EVENTS` | `start`, `end`, `textId`, `domainId` |
| `MPI_P2P_EVENTS` / `MPI_COLLECTIVES_EVENTS` | `start`, `end`, `textId`, `globalTid` |
| `StringIds` | `id`, `value` -- join with `textId`/`nameId` |

## Analysis Queries

**Top kernels by total time**:
```sql
SELECT name, count(*) AS launches, sum(end-start) AS total_ns, avg(end-start) AS avg_ns
FROM CUPTI_ACTIVITY_KIND_KERNEL_NAMED
GROUP BY name ORDER BY total_ns DESC LIMIT 10
```

**Memory transfer summary**:
```sql
SELECT srcKind, dstKind, count(*) AS transfers, sum(bytes) AS total_bytes, sum(end-start) AS total_ns
FROM CUPTI_ACTIVITY_KIND_MEMCPY
GROUP BY srcKind, dstKind ORDER BY total_ns DESC
```

**MPI collective overhead**:
```sql
SELECT s.value AS name, count(*) AS calls, sum(e.end-e.start) AS total_ns
FROM MPI_COLLECTIVES_EVENTS e JOIN StringIds s ON e.textId = s.id
GROUP BY s.value ORDER BY total_ns DESC
```

## Project Integration

- `tools/system_info/bin/check_profiling_ready` -- checks nsys on PATH
- **No dedicated nsys tool wrapper yet** -- `tools/nsight_systems/` needs to be created

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

## Features New in 12.9 (nsys 2025.3)

- **`--pytorch`** (2025.1) -- PyTorch module tracing, autograd NVTX markers
- **`--dask`** (2025.2) -- Dask distributed computing trace
- **Lustre metrics** (2024.7 GA) -- client-side Lustre I/O, relevant for `/global/`
- **Analysis recipes** (`nsys recipe`): `communications`, `nccl_identification`, `compute_overlap`, `heatmap_overview`, `gpu_metrics_per_range`
- **`cuda-hw` trace** (2025.2 Beta) -- hardware-based low-overhead, Blackwell only (not A100)

### Deprecated in 12.9

- Pascal/Volta dropped (A100 still supported)
- `text` export deprecated -- use `sqlite`
- `libnvToolsExt.so` not shipped -- use `nvtx3/nvtx3.hpp` or `pip install nvtx`

## Per-Rank Reports

Each MPI rank gets its own `.nsys-rep` file. Export each to SQLite for analysis, or use `nsys recipe` for cross-rank summaries.

**nsight-python** (`/pscratch/sd/k/krydzy/nsight-python/`) is **ncu-only** -- no nsys support.
