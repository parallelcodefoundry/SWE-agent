# HPCToolkit Profiling Tool

This SWE-agent tool provides a simple interface to run the complete HPCToolkit profiling workflow on GPU-accelerated applications.

## What It Does

The `hpc_profile` tool automates the three-step HPCToolkit profiling process:

1. **hpcrun**: Profiles the application with GPU tracing enabled (`-e gpu=nvidia -tt`)
2. **hpcstruct**: Recovers program structure from measurements
3. **hpcprof**: Attributes measurements to source code, creating a database

## Usage

```bash
hpc_profile <executable> <output_dir> [app_args...]
```

### Arguments

- **executable** (required): Path to the executable to profile
- **output_dir** (required): Directory to store profiling results
- **app_args** (optional): Arguments to pass to your application

### Examples

```bash
# Profile a single-GPU application
hpc_profile /path/to/myapp ./profiling_results

# Profile CHAMPS+ with 4 GPUs
hpc_profile ./bin/champs+ ./results -dev num-avail=4

# Profile with application-specific arguments
hpc_profile ./myapp ./results --input data.txt --config setup.cfg

# Profile with MPI (use srun/mpirun)
srun -n 4 hpc_profile ./myapp ./results
```

## GPU Control

**Important**: The number of GPUs used by your application is controlled by:
1. **Application arguments** (like `-dev num-avail=4` for CHAMPS+)
2. **Environment variables** (like `CUDA_VISIBLE_DEVICES`)
3. **MPI rank distribution**

HPCToolkit automatically profiles ALL GPUs used by your application. It does not have a separate GPU count parameter.

## Prerequisites

HPCToolkit must be loaded before using this tool:

```bash
source ~/spack/share/spack/setup-env.sh
spack load hpctoolkit
```

## Output

The tool creates two directories:

- **measurements/**: Raw profiling data from hpcrun
- **database/**: Processed database for viewing/analysis

## Next Steps

After profiling completes, you can:

1. **Analyze with Hatchet** (recommended for LLM analysis):
   ```bash
   hatchet_analyze <output_dir>/database
   ```

2. **View with hpcviewer** (graphical interface):
   ```bash
   hpcviewer <output_dir>/database
   ```

## Features

- Automatically pauses/resumes DCGM for accurate profiling
- Validates executable and HPCToolkit availability
- Provides clear error messages
- Works with MPI applications via srun/mpirun
- Compatible with NERSC Perlmutter GPU nodes

## Technical Details

The tool uses these HPCToolkit commands:

```bash
# Step 1: Profile with GPU tracing and boosted resolution
hpcrun -e gpu=nvidia -tt -o measurements executable [app_args...]

# Step 2: Recover program structure
hpcstruct measurements

# Step 3: Attribute measurements to source
hpcprof -o database measurements
```

### What is `-tt`?

The `-tt` flag enables "boosted resolution tracing" which records CPU calling contexts when launching GPU operations. This provides more detailed analysis of GPU-accelerated applications.

## Verified Against HPCToolkit Repository

This tool has been verified against the official HPCToolkit repository:
- Repository: `/global/homes/k/krydzy/hpctoolkit`
- Documentation reviewed: quickstart, hpcrun, gpu profiling guides
- All command sequences verified for correctness

## Notes

- For large-scale experiments (thousands of threads/GPU streams), consider using `hpcprof-mpi` instead of regular `hpcprof`
- DCGM (NVIDIA Data Center GPU Manager) is paused during profiling if available
- The tool uses standard HPCToolkit options optimized for GPU profiling
- Works with dynamically-linked executables (statically-linked not supported by HPCToolkit)
