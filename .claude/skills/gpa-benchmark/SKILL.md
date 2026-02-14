---
name: gpa-benchmark
description: "GPA-Benchmark GPU performance anti-pattern suite. Use when user mentions 'gpa-benchmark', 'GPU anti-patterns', benchmark difficulty tiers, or integrating GPA apps into the harness."
user-invocable: false
---

# GPA-Benchmark (GPU Performance Advisor Benchmark)

Suite of GPU kernels with **known performance anti-patterns and expert-written fixes**, plus a Python driver (`gpa_bench_driver`) that automates build, run, validate, profile, and swap. 20+ benchmarks from Rodinia, ExaTENSOR, LULESH, XSBench. Speedups 1.02x-3.86x on V100.

## Source & Layout

- **Local clone**: `/pscratch/sd/k/krydzy/GPA-Benchmark/`
- **App configs**: `driver_apps.yaml`
- **Driver source**: `gpa_bench_driver/`

## Driver CLI

```bash
cd /pscratch/sd/k/krydzy/GPA-Benchmark

python -m gpa_bench_driver --app gaussian                     # build + run + validate
python -m gpa_bench_driver --app gaussian --nsys              # + Nsight Systems profiling
python -m gpa_bench_driver --app gaussian --ncu               # + Nsight Compute profiling
python -m gpa_bench_driver --app gaussian --swaps /path/dir   # test optimized code variants
python -m gpa_bench_driver --app all                          # all apps
python -m gpa_bench_driver --app gaussian --sm-version 80     # override SM (A100=80)
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
3. Agent generates optimized code
4. Driver swaps in code, builds, runs, validates, profiles
5. Driver reports: correctness + timing comparison

The `run_driver()` API with `swaps_override` makes this straightforward -- pass agent code as string, get structured results.

## Difficulty Grouping

- **Easy** (clear signal): hotspot, cfd, gaussian, particlefilter
- **Medium** (kernel logic): backprop, bfs, lud, streamcluster
- **Hard** (subtle): myocyte (20K lines), srad (1.03x), pathfinder (1.05x)

## Common Issues

- **`CUDA_HOME` not set**: `export CUDA_HOME=$CUDATOOLKIT_HOME`
- **SM mismatch**: Default 90 (H100). For A100: `--sm-version 80`
- **Missing rodinia data**: Run `bash get_data.sh`
- **V100 speedups != A100**: README results are V100. Re-baseline on A100

For detailed reference, see references/ in this skill directory.
