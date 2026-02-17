---
name: gpa-benchmark
description: "GPA-Benchmark GPU performance anti-pattern suite. Use when user mentions 'gpa-benchmark', 'GPU anti-patterns', benchmark difficulty tiers, or integrating GPA apps into the harness."
user-invocable: false
---

# GPA-Benchmark (GPU Performance Advisor Benchmark)

Suite of GPU kernels with **known performance anti-patterns and expert-written fixes**, plus a Python driver (`gpa_bench_driver`) that automates build, run, validate, profile, and swap. 17 active benchmarks from Rodinia, ExaTENSOR, LULESH, XSBench. Speedups 1.02x-3.86x on V100.

## Source & Layout

- **Local clone**: `/pscratch/sd/k/krydzy/GPA-Benchmark/` (symlinked at `~/GPA-Benchmark`)
- **App configs**: `driver_apps.yaml` (17 apps)
- **Driver source**: `gpa_bench_driver/` (entry: `gpa_bench_driver.py`)
- **Driver modules**: `gpa_bench_driver/driver_src/` (operations, validation, profiling, file swapping, reporting)
- **App dirs**: `rodinia/`, `ExaTENSOR/`, `LULESH/`, `XSBench/`, `Castro/`, `darknet/`, `PeleC/`, `Quicksilver/`

## Active Apps (17)

**Rodinia (13):** b+tree, backprop, bfs, gaussian, heartwall, hotspot, huffman, lavaMD, lud, nw, particlefilter, pathfinder, srad, streamcluster
**Standalone (3):** exatensor, lulesh, xsbench
**Commented out:** quicksilver (validation needs CORAL2), myocyte

## Driver CLI

```bash
cd /pscratch/sd/k/krydzy/GPA-Benchmark

# Core operations
python -m gpa_bench_driver --app gaussian                     # build + run + validate
python -m gpa_bench_driver --app all                          # all 17 apps
python -m gpa_bench_driver --app gaussian --nsys              # + Nsight Systems profiling
python -m gpa_bench_driver --app gaussian --ncu               # + Nsight Compute profiling
python -m gpa_bench_driver --app gaussian --swaps /path/dir   # test optimized code variants

# Build/run controls
python -m gpa_bench_driver --app gaussian --sm-version 80     # override SM (A100=80, auto-detected by default)
python -m gpa_bench_driver --app gaussian --build-only        # build without running
python -m gpa_bench_driver --app gaussian --no-clean          # skip clean before rebuild
python -m gpa_bench_driver --app gaussian -n 5                # 5 profiling samples (default 3)

# Output/logging
python -m gpa_bench_driver --app gaussian -o results.json     # save results to file (default: driver_results.json)
python -m gpa_bench_driver --app gaussian -l DEBUG             # log level (DEBUG/INFO/WARNING/ERROR)
python -m gpa_bench_driver --app gaussian --no-progress        # hide progress bar

# Advanced
python -m gpa_bench_driver --app gaussian --detect-regions    # detect editable region markers in swap files
python -m gpa_bench_driver --app gaussian --postprocess-nsys  # only postprocess existing nsys-rep files
python -m gpa_bench_driver --config custom.yaml               # custom app config file
python -m gpa_bench_driver --app gaussian -t /tmp/mydir       # custom temp dir for builds
```

## Programmatic API

```python
from gpa_bench_driver import run_driver

results, operations, long_results = run_driver(
    app="xsbench",
    nsys=True,
    num_samples=5,
    output_file="results.json",
    swaps_override={"xsbench": {"target.cu": "optimized code string"}},
)
# results: Dict[str, AppResults] — per-app summary (baseline timing, swap timing, speedup)
# operations: List[Operation] — what was done (BUILD, RUN, VALIDATE, SWAP_*, etc.)
# long_results: Dict[str, List[DriverPassResult]] — detailed per-pass results with stdout/stderr
```

## Build on Perlmutter

```bash
salloc -A m2404 -C gpu -q interactive -t 01:00:00 -n 1 -c 32 --gpus-per-task=1
module load cuda/12.4
cd /pscratch/sd/k/krydzy/GPA-Benchmark
bash get_data.sh                    # one-time: download rodinia input data
export CUDA_HOME=$CUDATOOLKIT_HOME
python -m gpa_bench_driver --app gaussian --sm-version 80
```

## Agent Integration

1. Agent receives baseline kernel source + profiling tools
2. Agent profiles with nsys/ncu, diagnoses bottleneck
3. Agent generates optimized CUDA code
4. Driver swaps in code (`--swaps` or `swaps_override`), force-rebuilds (`make -B`), runs, validates, profiles
5. Driver reports: correctness + timing comparison (baseline vs swapped)

Swap file naming: `run_<num>_optimized_code_<num>.cu`

## Validation Strategies (in driver_apps.yaml)

- `fail_check_text` — fails if text found in output
- `pass_check_text` — passes only if text found
- `reference_output` — exact match or windowed/float comparison
- `float_grep` — extract and compare float within tolerance
- `output_window` — compare specific line range

## Difficulty Grouping

- **Easy** (clear signal): hotspot, cfd, gaussian, particlefilter
- **Medium** (kernel logic): backprop, bfs, lud, streamcluster
- **Hard** (subtle): myocyte (20K lines), srad (1.03x), pathfinder (1.05x)

## Batch Execution

`drive-gpa.sbatch` runs all 17 apps as a SLURM job array (1 GPU per app, H100/A100).

## Benchmark Runner Integration

```bash
# Via benchmark runner (from SWE-agent repo root)
python3 batch/hpc_benchmark_runner.py --base --app gpa          # base mode (all 17 apps)
python3 batch/hpc_benchmark_runner.py --app gpa --framework sweagent  # agent mode

# Via run_benchmark.sh
bash batch/run_benchmark.sh --gpa --base
```

The runner handles `sys.path` setup, `os.chdir()` to GPA root, workspace creation for agent mode, and result collection via `run_driver()` API.

## Validation Status (Perlmutter A100)

16/17 apps PASS in base mode. Only `lulesh` fails (empty `LULESH/` dir upstream — not our bug).

## Common Issues

- **`CUDA_HOME` not set**: `export CUDA_HOME=$CUDATOOLKIT_HOME`
- **SM mismatch**: Auto-detected from `nvidia-smi`. Override with `--sm-version 80` for A100
- **Missing rodinia data**: Run `bash get_data.sh`
- **V100 speedups != A100**: README results are V100. Re-baseline on A100
- **Force rebuild**: Driver uses `make -B` to always rebuild (prevents stale binaries)
- **lavaMD case sensitivity**: Fixed — driver lowercases app names but `driver_apps.yaml` has `name: lavaMD`. All comparisons now use `.lower()` (commit `ab21f6b` in GPA-Benchmark)
- **lulesh always fails**: Empty `LULESH/` directory in GPA-Benchmark repo — upstream issue, not our integration

For detailed reference, see references/ in this skill directory.
