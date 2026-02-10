---
name: nsight-compute
description: "Knowledge about NVIDIA Nsight Compute for GPU kernel profiling including ncu CLI usage, key performance metrics, output parsing via nsight-python and CSV, and integration with our tool-calling format. Load when implementing or debugging Nsight Compute-based profiling tools."
---

# NVIDIA Nsight Compute (ncu) — Perlmutter Reference

## Perlmutter Paths

| | cudatoolkit/12.4 (default) | cudatoolkit/12.9 |
|---|---|---|
| **ncu version** | 2024.1.1.0 | 2025.2.0.0 |
| **ncu binary** | `/opt/nvidia/hpc_sdk/Linux_x86_64/24.5/profilers/Nsight_Compute/ncu` | `/opt/nvidia/hpc_sdk/Linux_x86_64/25.5/profilers/Nsight_Compute/ncu` |
| **ncu_report.py** | `.../24.5/profilers/Nsight_Compute/extras/python/` | `.../25.5/.../extras/python/` |
| **ncu_occupancy.py** | Not available | `.../25.5/.../extras/python/` (12.9 only) |

**NVTX breaking change on 12.9**: `libnvToolsExt.so` is gone. Use `nvtx3/nvtx3.hpp` for C++ or `pip install nvtx` for Python.

## Project Integration

- `tools/system_info/bin/check_profiling_ready` — checks ncu on PATH
- `tools/system_info/bin/profiler_info` — lists ncu/nsys presence
- **No dedicated ncu tool wrapper yet** — `tools/nsight_compute/` needs to be created

### Planned SWE-Agent Tool: `tools/nsight_compute/config.yaml`

```yaml
tools:
  ncu_profile:
    signature: "ncu_profile <executable> <output_dir> [<kernel_filter>] [<app_args>...]"
    docstring: |
      Profile GPU kernels with Nsight Compute.
      Validates ncu + GPU access, pauses DCGM, runs ncu --set basic (or --set detailed with kernel_filter).
      Returns: CSV metrics for top kernels + bottleneck summary.
```

## nsight-python Library

Local clone: `/pscratch/sd/k/krydzy/nsight-python/`. High-level Python API wrapping ncu.

```bash
pip install -e /pscratch/sd/k/krydzy/nsight-python/
```

```python
import nsight

@nsight.analyze.kernel(metrics=["gpu__time_duration.sum"], configs=[(1024,)], runs=10)
def my_benchmark(n: int) -> None:
    with nsight.annotate("my_kernel"):
        result = my_operation(a, b)

result = my_benchmark()
df = result.to_dataframe()  # AvgValue, StdDev, CI95, RelativeStdDevPct
```

Key modules: `nsight.analyze.kernel` (decorator), `nsight.annotate` (NVTX), `nsight.collection.ncu.NCUCollector`, `nsight.extraction.extract_df_from_report()`.

## ncu_report Module (Low-Level)

Bundled at `<NCU_DIR>/extras/python/` or `pip install ncu-report`.

```python
import ncu_report
report = ncu_report.load_report("report.ncu-rep")
r = report.range_by_idx(0)
for ai in range(r.num_actions()):
    action = r.action_by_idx(ai)
    print(action.name(), action["gpu__time_duration.sum"].value())
```

Derive path dynamically:
```python
import os, sys
sdk_base = os.path.dirname(os.path.dirname(os.environ["CUDATOOLKIT_HOME"]))
sys.path.insert(0, os.path.join(sdk_base, "profilers", "Nsight_Compute", "extras", "python"))
```

## Features New in 12.9 (ncu 2025.2)

- **Roofline in `--set full`** — no separate roofline pass needed
- **Occupancy calculator** (`ncu_occupancy.py`) — programmatic occupancy analysis
- **Rule results API** — `action.rule_results()` for focus metrics + speedup estimates
- **New metrics**: `sass__inst_executed_per_opcode_category`, `sass__inst_executed_register_spilling`, `launch__stack_size`
- **MPS profiling**, **range replay source metrics**, **Python call stack collection**

## Common Issues

- **DCGM conflicts**: Always `dcgmi profile --pause` before ncu, `--resume` after
- **Must run on compute nodes**: `salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 1 --account m2404`
- **ncu_report not found**: `pip install ncu-report` or add bundled path to `sys.path`
- **NVTX errors on 12.9**: `pip install nvtx` for Python; use `nvtx3/nvtx3.hpp` for C++
- **Clock control**: ncu defaults to `--clock-control base` (locked). nsight-python defaults to `none`. Use `base` for reproducible benchmarks
- **Large reports**: `--set full` can produce 100s of MB. Limit with `-c 1 -s 5` or use `--set basic`
- **Don't run ncu + nsys simultaneously** — both instrument CUDA
