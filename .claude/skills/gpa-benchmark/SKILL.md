---
name: gpa-benchmark
description: "Knowledge about the GPA-Benchmark GPU performance anti-pattern suite including available benchmarks, build configuration, integration with our benchmark harness, and expected optimization targets. Load when working with GPA-Benchmark applications or creating benchmark instances from them."
---

# GPA-Benchmark (GPU Performance Advisor Benchmark)

Suite of GPU kernels with **known performance anti-patterns and expert-written fixes**, plus a Python driver (`gpa_bench_driver`) that automates build→run→validate→profile→swap. 20+ benchmarks from Rodinia, ExaTENSOR, LULESH, XSBench. Speedups 1.02x-3.86x on V100.

## Source & Layout

- **Local clone**: `/pscratch/sd/k/krydzy/GPA-Benchmark/`
- **App configs**: `driver_apps.yaml` — per-app build/run/validate/profile config
- **Driver source**: `gpa_bench_driver/` — Python package
- **Rodinia apps**: `rodinia/{app}/` (baseline), `rodinia/{app}-opt*/` (optimized variants)
- **Other apps**: `ExaTENSOR/`, `LULESH/`, `XSBench/`

## Driver CLI

```bash
cd /pscratch/sd/k/krydzy/GPA-Benchmark

python -m gpa_bench_driver --app gaussian                     # build + run + validate
python -m gpa_bench_driver --app gaussian --nsys              # + Nsight Systems profiling
python -m gpa_bench_driver --app gaussian --ncu               # + Nsight Compute profiling
python -m gpa_bench_driver --app gaussian --swaps /path/dir   # test optimized code variants
python -m gpa_bench_driver --app all                          # all apps
python -m gpa_bench_driver --app gaussian --build-only        # build only
python -m gpa_bench_driver --app gaussian --sm-version 80     # override SM (A100=80)
python -m gpa_bench_driver --app gaussian -n 5 -o results.json  # 5 samples, JSON output
```

## Python API

```python
from gpa_bench_driver.gpa_bench_driver import run_driver
results, operations, long_results = run_driver(app="gaussian", nsys=True, sm_version=80)

# Test agent-generated code via swaps_override
results, ops, lr = run_driver(app="gaussian", swaps_override={"// gaussian.cu\n": optimized_code})
```

## Driver Pass Flow

For each app: copy to temp dir → swap file in (if testing) → `make -j 8 SM_VERSION={sm}` → run → validate → profile → swap file out → report.

## Code Swap Format

- Swap file first line: comment with target filename (e.g., `// gaussian.cu`)
- Editable regions: `// >>> START EDITABLE REGION ID=0` ... `// <<< END EDITABLE REGION ID=0`
- Only region between markers is replaced when `--detect-regions` is used

## Validation Strategies

| Strategy | YAML Key | How |
|----------|----------|-----|
| Fail check | `fail_check_text` | FAIL if text in stdout |
| Pass check | `pass_check_text` | PASS if text in stdout |
| Reference output | `reference_output` + `test_output` | Exact diff |
| Float grep | `float_grep` + `float_tolerance` | Float within tolerance |
| Output window | `output_window` | Compare specific line range |

## Build on Perlmutter

```bash
salloc -A m2404 -C gpu -q interactive -t 01:00:00 -n 1 -c 32 --gpus-per-task=1
module load cuda/12.4
cd /pscratch/sd/k/krydzy/GPA-Benchmark
bash get_data.sh                    # one-time: download rodinia input data
export CUDA_HOME=$CUDATOOLKIT_HOME
python -m gpa_bench_driver --app gaussian --sm-version 80
```

## Configured Apps

See `driver_apps.yaml` for full list: exatensor, lulesh, xsbench, b+tree, backprop, bfs, gaussian, heartwall, hotspot, huffman, lavaMD, lud, nw, particlefilter, pathfinder, srad, streamcluster.

### Difficulty Grouping

- **Easy** (clear signal): hotspot, cfd, gaussian, particlefilter
- **Medium** (kernel logic): backprop, bfs, lud, streamcluster
- **Hard** (subtle): myocyte (20K lines), srad (1.03x), pathfinder (1.05x)

## Agent Integration

1. Agent receives baseline kernel source + profiling tools
2. Agent profiles with nsys/ncu, diagnoses bottleneck
3. Agent generates optimized code
4. Driver swaps in code, builds, runs, validates, profiles
5. Driver reports: correctness + timing comparison

The `run_driver()` API with `swaps_override` makes this straightforward — pass agent code as string, get structured results.

## Common Issues

- **`CUDA_HOME` not set**: `export CUDA_HOME=$CUDATOOLKIT_HOME`
- **SM mismatch**: Default 90 (H100). For A100: `--sm-version 80` or auto-detect
- **Missing rodinia data**: Run `bash get_data.sh`
- **V100 speedups ≠ A100**: README results are V100. Re-baseline on A100
- **Swap file format**: First line must be comment with target filename
- **Python deps**: Requires Python >=3.12.11, alive-progress, pandas, pysqlite3, pyyaml
