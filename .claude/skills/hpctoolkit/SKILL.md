---
name: hpctoolkit
description: "Knowledge about HPCToolkit performance profiling including hpcrun instrumentation, hpcstruct analysis, hpcprof database generation, and output parsing. Load when implementing or debugging HPCToolkit-based profiling tools."
---

# HPCToolkit Profiling

HPCToolkit is a sampling-based performance profiling toolkit for HPC applications.

## Installation (Perlmutter)

```bash
source ~/spack/share/spack/setup-env.sh
spack load hpctoolkit
```

The `hpc_profile` tool auto-discovers HPCToolkit via `PATH`, then `spack load`, then known Perlmutter paths.

## 3-Stage Pipeline

All three stages are automated by `hpc_profile`, but can be run manually:

### 1. hpcrun (Measurement)

```bash
hpcrun -e gpu=nvidia -tt -o <measurements_dir> <executable> [app_args...]
```

Key flags: `-e gpu=nvidia` (NVIDIA GPU profiling), `-tt` (boosted tracing with CPU calling contexts), `-o <dir>` (output dir), `-e CYCLES@4000000` (CPU cycle sampling), `--disable-auditor` (LD_AUDIT compat). Defaults to `CPUTIME` if no `-e` given. GPU count is controlled by the application (args, `CUDA_VISIBLE_DEVICES`, MPI ranks), NOT by hpcrun.

### 2. hpcstruct (Structure Recovery)

```bash
hpcstruct <measurements_dir>
```

Recovers procedure/file/line mappings into `.hpcstruct` XML files. Skip slow binaries with `-x libmpi.so.12.5.0`. Use `-j <N>` for parallel jobs or `HPCTOOLKIT_HPCSTRUCT_CACHE` for persistent caching.

### 3. hpcprof (Attribution)

```bash
hpcprof -o <database_dir> <measurements_dir>
```

Produces the final HPCToolkit v4 database (binary format). For large-scale runs: `srun -n 8 hpcprof-mpi <measurements_dir>`.

## Our Tool Wrapper

**Path**: `tools/hpctoolkit/bin/hpc_profile` (config: `tools/hpctoolkit/config.yaml`)

```
hpc_profile <executable> <output_dir> [<app_args>...]
```

The tool: validates inputs, pauses DCGM, runs hpcrun/hpcstruct/hpcprof, resumes DCGM. Output lands in `<output_dir>/measurements/` and `<output_dir>/database/`.

Enabled in benchmark configs via tool bundle:
```yaml
agent:
  tools:
    bundles:
      - path: tools/hpctoolkit    # hpc_profile
      - path: tools/hatchet       # hatchet_analyze (downstream analysis)
```

Prerequisites: `module load cuda/12.4 openmpi/5.0.7` and `spack load hpctoolkit`.

## Output Structure

```
<output_dir>/
  measurements/            # Raw hpcrun data (.hpcrun, .hpctrace, .log files)
    structs/               # hpcstruct XML output (.hpcstruct per binary)
    gpubins/               # Extracted GPU binaries
  database/                # HPCToolkit v4 database
    meta.db                # Metrics, context tree, function/file/module mappings
    profile.db             # Per-thread performance data (sparse)
    cct.db                 # Per-context performance data (sparse)
    trace.db               # Timestamped trace samples
    metrics/               # Metric taxonomy YAML files
```

The `.hpcstruct` XML uses `<F n="file">`, `<P n="func" l="line">`, `<S l="line">` elements. Parsed by `hatchet_utils.parse_hpcstruct_line_ranges()` to map functions to `(filename, start_line, end_line)`.

## Integration with Hatchet

Pass the **database** subdirectory to hatchet for analysis:

```bash
hpc_profile ./build/kripke.exe ./profiling_results --arch CUDA --layout DGZ --zones 32,32,32
hatchet_analyze ./profiling_results/database
```

## Companion Tools

| Tool | Purpose |
|------|---------|
| `hatchet_analyze` | Parse HPCToolkit database into LLM-friendly analysis |
| `check_profiling_ready` | Pre-flight: checks GPU, profilers, DCGM, memory, disk |
| `profiler_info` | Lists available profiling tools |
| `compiler_analysis` | nvcc register/shared mem analysis |
| `benchmark_code` | Git-based baseline comparison with correctness check |

## Common Issues

- **"HPCToolkit not found"**: `source ~/spack/share/spack/setup-env.sh && spack load hpctoolkit` (not a system module).
- **hpcstruct takes forever**: Skip large binaries with `-x libmpi.so.12.5.0`; use `HPCTOOLKIT_HPCSTRUCT_CACHE` for caching.
- **DCGM conflicts**: `hpc_profile` auto-pauses/resumes; manually: `dcgmi profile --pause` / `--resume`.
- **GPU count wrong**: Control via app args or `CUDA_VISIBLE_DEVICES`, not hpcrun flags.
- **Static binaries**: HPCToolkit requires dynamically-linked executables.
- **Large-scale hpcprof slow**: Use `srun -n 8 hpcprof-mpi` (needs `+mpi` spack variant).
