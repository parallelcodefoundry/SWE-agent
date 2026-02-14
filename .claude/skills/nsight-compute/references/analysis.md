# Nsight Compute Analysis Reference

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

## Occupancy Calculator (12.9 only)

Available at `/opt/nvidia/hpc_sdk/Linux_x86_64/25.5/profilers/Nsight_Compute/extras/python/ncu_occupancy.py`.

Not available on cudatoolkit/12.4.

## ncu_report Path by CUDA Version

| | cudatoolkit/12.4 (default) | cudatoolkit/12.9 |
|---|---|---|
| **ncu_report.py** | `.../24.5/profilers/Nsight_Compute/extras/python/` | `.../25.5/.../extras/python/` |
| **ncu_occupancy.py** | Not available | `.../25.5/.../extras/python/` |

## Rule Results API (12.9+)

```python
for ai in range(r.num_actions()):
    action = r.action_by_idx(ai)
    for rule in action.rule_results():
        print(rule.name, rule.focus_metrics, rule.speedup_estimate)
```

Provides focus metrics and speedup estimates per rule, useful for automated bottleneck identification.
