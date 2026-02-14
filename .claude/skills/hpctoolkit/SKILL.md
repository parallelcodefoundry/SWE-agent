---
name: hpctoolkit
description: "HPCToolkit performance profiling: hpcrun, hpcstruct, hpcprof pipeline. Use when user mentions 'hpctoolkit', 'hpcrun', 'hpcstruct', 'hpcprof', or needs to instrument, profile, or analyze GPU application performance."
user-invocable: false
---

# HPCToolkit Profiling

HPCToolkit is a sampling-based performance profiling toolkit for HPC applications.

For detailed reference, see references/ in this skill directory.

## Installation (Perlmutter)

```bash
source ~/spack/share/spack/setup-env.sh
spack load hpctoolkit
```

The `hpc_profile` tool auto-discovers HPCToolkit via `PATH`, then `spack load`, then known Perlmutter paths.

## 3-Stage Pipeline

### 1. hpcrun (Measurement)

```bash
hpcrun -e gpu=nvidia -tt -o <measurements_dir> <executable> [app_args...]
```

Key flags: `-e gpu=nvidia` (NVIDIA GPU profiling), `-tt` (boosted tracing with CPU calling contexts), `-o <dir>` (output dir), `-e CYCLES@4000000` (CPU cycle sampling), `--disable-auditor` (LD_AUDIT compat). GPU count is controlled by the application, NOT by hpcrun.

### 2. hpcstruct (Structure Recovery)

```bash
hpcstruct <measurements_dir>
```

Recovers procedure/file/line mappings. Skip slow binaries with `-x libmpi.so.12.5.0`. Use `-j <N>` for parallel jobs or `HPCTOOLKIT_HPCSTRUCT_CACHE` for persistent caching.

### 3. hpcprof (Attribution)

```bash
hpcprof -o <database_dir> <measurements_dir>
```

Produces the final HPCToolkit v4 database. For large-scale: `srun -n 8 hpcprof-mpi <measurements_dir>`.

## Our Tool Wrapper

**Path**: `tools/hpctoolkit/bin/hpc_profile` (config: `tools/hpctoolkit/config.yaml`)

```
hpc_profile <executable> <output_dir> [<app_args>...]
```

The tool: validates inputs, pauses DCGM, runs hpcrun/hpcstruct/hpcprof, resumes DCGM. Output lands in `<output_dir>/measurements/` and `<output_dir>/database/`.

Prerequisites: `module load cuda/12.4 openmpi/5.0.7` and `spack load hpctoolkit`.

## Common Issues

- **"HPCToolkit not found"**: `source ~/spack/share/spack/setup-env.sh && spack load hpctoolkit`.
- **hpcstruct takes forever**: Skip large binaries with `-x`; use `HPCTOOLKIT_HPCSTRUCT_CACHE`.
- **DCGM conflicts**: `hpc_profile` auto-pauses/resumes; manually: `dcgmi profile --pause` / `--resume`.
- **GPU count wrong**: Control via app args or `CUDA_VISIBLE_DEVICES`, not hpcrun flags.
- **Static binaries**: HPCToolkit requires dynamically-linked executables.
