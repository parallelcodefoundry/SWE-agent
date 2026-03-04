---
name: nsight-compute
description: "NVIDIA Nsight Compute GPU kernel profiling: ncu CLI, occupancy metrics, roofline analysis. Use when user mentions 'nsight compute', 'ncu', 'kernel profiling', 'occupancy', or GPU kernel performance analysis."
user-invocable: false
---

# NVIDIA Nsight Compute (ncu) -- Perlmutter Reference

For detailed reference, see references/ in this skill directory.

## Perlmutter Paths

| | cudatoolkit/12.4 (default) | cudatoolkit/12.9 |
|---|---|---|
| **ncu version** | 2024.1.1.0 | 2025.2.0.0 |
| **ncu binary** | `/opt/nvidia/hpc_sdk/Linux_x86_64/24.5/profilers/Nsight_Compute/ncu` | `.../25.5/.../ncu` |

**NVTX breaking change on 12.9**: `libnvToolsExt.so` is gone. Use `nvtx3/nvtx3.hpp` for C++ or `pip install nvtx` for Python.

## Project Integration

- `tools/nsight_compute/config.yaml` -- SWE-agent tool definition
- `tools/nsight_compute/bin/ncu_profile` -- Profiling script (tested on all 4 proxy apps)
- `tools/system_info/bin/check_profiling_ready` -- checks ncu on PATH
- `tools/system_info/bin/profiler_info` -- lists ncu/nsys presence
- All `config/hpc/*_with_profiling.yaml` configs include `tools/nsight_compute` in bundles
- `batch/frameworks/base.py` PROFILING_TOOL_DIRS includes `tools/nsight_compute/bin`

### SWE-Agent Tool Usage

```
ncu_profile <executable> <output_dir> [<kernel_filter>] [<app_args>...]
```

- **Basic mode** (no filter): `--set basic -s 0 -c 500` — profiles up to 500 kernel launches (covers init + simulation phases)
- **Detailed mode** (with filter): `--set detailed --kernel-name regex:<filter> -c 3` — full metrics for matching kernels
- Outputs: `report.ncu-rep` (binary), `metrics_summary.csv`, `summary.txt` (bottleneck analysis)
- Auto-pauses/resumes DCGM on managed clusters

### Key Metrics Extracted

- `gpu__time_duration.sum` — kernel execution time
- `sm__throughput.avg.pct_of_peak_sustained_elapsed` — SM utilization
- `dram__cycles_active.avg.pct_of_peak_sustained_elapsed` — DRAM utilization (NOT `dram__throughput`)
- `l1tex__throughput.avg.pct_of_peak_sustained_active` — L1 throughput (detailed only, uses `_active` NOT `_elapsed`)
- `sm__warps_active.avg.pct_of_peak_sustained_active` — warp occupancy
- `launch__registers_per_thread`, `launch__shared_mem_per_block_allocated`, `launch__grid_size`, `launch__block_size`

### Test Results (session 36, all proxy apps)

| App | Mode | Wall Time | Finding |
|-----|------|-----------|---------|
| Lulesh | Basic | 8s | LATENCY-BOUND (SM 1.6%) |
| Kripke | Basic | 15s | LATENCY-BOUND (SM 10.6%) |
| Laghos | Basic | 16s | LATENCY-BOUND (tiny kernels) |
| Quicksilver | Basic | 32s | LATENCY-BOUND (116 regs, SM 26.8%) |
| Lulesh | Detailed (CalcVolume) | 9s | MIXED (252 regs!) |

## Features New in 12.9 (ncu 2025.2)

- **Roofline in `--set full`** -- no separate roofline pass needed
- **Occupancy calculator** (`ncu_occupancy.py`) -- programmatic occupancy analysis
- **Rule results API** -- `action.rule_results()` for focus metrics + speedup estimates
- **New metrics**: `sass__inst_executed_per_opcode_category`, `sass__inst_executed_register_spilling`, `launch__stack_size`
- **MPS profiling**, **range replay source metrics**, **Python call stack collection**

## Common Issues

- **DCGM conflicts**: Always `dcgmi profile --pause` before ncu, `--resume` after
- **Must run on compute nodes**: `salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 1 --account m2404`
- **ncu_report not found**: `pip install ncu-report` or add bundled path to `sys.path`
- **NVTX errors on 12.9**: `pip install nvtx` for Python; use `nvtx3/nvtx3.hpp` for C++
- **Clock control**: ncu defaults to `--clock-control base` (locked). Use `base` for reproducible benchmarks
- **Large reports**: `--set full` can produce 100s of MB. Limit with `-c 1 -s 5` or use `--set basic`
- **Don't run ncu + nsys simultaneously** -- both instrument CUDA
