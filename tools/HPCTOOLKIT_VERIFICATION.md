# HPCToolkit Tool Verification Report

## Overview

This document details the verification of the HPCToolkit SWE-agent tool against the official HPCToolkit repository at `/pscratch/sd/k/krydzy/hpctoolkit`.

**Repository Information:**
- Location: `/pscratch/sd/k/krydzy/hpctoolkit`
- Documentation: `doc/src/users/`
- Key docs reviewed:
  - `quickstart.md` - Overall workflow
  - `hpcrun/hpcrun.md` - hpcrun details
  - `gpu/gpu.md` - GPU profiling specifics
  - `environment-vars.md` - Environment variables

## HPCToolkit Workflow (Verified)

The official HPCToolkit workflow consists of 4 steps:

1. **Compilation** - With `-g` for line info
2. **Measurement** (`hpcrun`) - Profile/trace application execution
3. **Structure Recovery** (`hpcstruct`) - Analyze binaries
4. **Attribution** (`hpcprof` or `hpcprof-mpi`) - Correlate metrics with source
5. **Presentation** (`hpcviewer`) - Interactive visualization

## Command Verification

### 1. hpcrun - Measurement

**Official Usage:**
```bash
[<mpi-launcher>] hpcrun [hpcrun-options] app [app-arguments]
```

**Key Options (from `doc/src/users/hpcrun/hpcrun.md`):**

| Option | Description | Example |
|--------|-------------|---------|
| `-e/--event <event@period>` | Specify sample source | `-e CYCLES@4000000` |
| `-t/--trace` | Enable tracing | `-t` |
| `-tt` | Boosted resolution tracing (records CPU context when launching GPU ops) | `-tt` |
| `-o/--output <dir>` | Output directory | `-o measurements` |
| `--disable-auditor` | Disable LD_AUDIT (for compatibility) | |
| `-h/--help` | Show help | |

**GPU Profiling (from `doc/src/users/gpu/gpu.md`):**
- NVIDIA: `-e gpu=nvidia`
- AMD: `-e gpu=amd`
- Intel Level Zero: `-e gpu=level0`
- OpenCL: `-e gpu=opencl`

**Default Behavior:**
- If no events specified, uses `CPUTIME` (CPU timer sampling)
- Output directory: `hpctoolkit-<app>-measurements[-<jobid>]`
- `-tt` is recommended for GPU tracing to get CPU calling contexts

### 2. hpcstruct - Structure Analysis

**Official Usage:**
```bash
hpcstruct [options] <measurements-directory>
# OR for single binary
hpcstruct [options] <binary>
```

**Key Options (from `doc/src/users/quickstart.md`):**

| Option | Description | Example |
|--------|-------------|---------|
| `-j/--jobs <N>` | Number of parallel jobs (default: half of hardware threads) | `-j 16` |
| `-x/--exclude <file>` | Exclude problematic binary from analysis | `-x libmpi.so.12.5.0` |
| `-i/--include <file>` | Include binary that would otherwise be skipped | `-i mybinary.so` |
| `--show-files` | List all binaries in measurements directory | |
| `-c/--cache <dir>` | Structure cache directory | `-c /path/to/cache` |
| `HPCTOOLKIT_HPCSTRUCT_CACHE` | Environment variable for cache directory | |

**Important Notes:**
- Analyzes multiple binaries concurrently
- Can take 30-40 minutes for large binaries like libmpi.so
- Use `-x` to skip problematic binaries
- Caching recommended for repeated profiling

### 3. hpcprof - Attribution

**Official Usage:**
```bash
hpcprof [options] <measurements-directory>
```

**Key Options (from `doc/src/users/quickstart.md`):**

| Option | Description | Example |
|--------|-------------|---------|
| `-o/--output <dir>` | Output database directory | `-o database` |
| `-j/--jobs <N>` | Number of threads (default: all available) | `-j 8` |
| `-R/--replace-path <old=new>` | Replace source path prefixes | `-R /old/path=/new/path` |

**Default Behavior:**
- Output: `hpctoolkit-<app>-database` (with random suffix if exists)
- Uses all available threads by default
- Copies source files into database if accessible

### 4. hpcprof-mpi - Large-Scale Attribution

**Official Usage:**
```bash
<mpi-launcher> -n <ranks> hpcprof-mpi [options] <measurements-directory>
```

**When to Use:**
- Applications with thousands of threads
- Applications with thousands of GPU streams
- Faster analysis using multiple compute nodes
- Recommended: 8-10 compute nodes

**Example:**
```bash
srun -n 8 hpcprof-mpi hpctoolkit-app-measurements
```

## Critical Bug Found in Our Implementation

### ❌ BUG: Line 58 in hpc_profile

**Current (INCORRECT) code:**
```bash
hpcrun -e gpu=nvidia -tt -o "$measurements_dir" "$executable" -dev num-avail="$num_gpus"
```

**Problem:**
The `-dev num-avail=$num_gpus` is passed to the **executable**, NOT to hpcrun!

**Why this is wrong:**
- `hpcrun` syntax: `hpcrun [hpcrun-options] app [app-arguments]`
- Everything after `$executable` is passed to the application as arguments
- We're inadvertently passing `-dev num-avail=4` to the user's application
- This doesn't actually control GPU count for profiling

**Correct approach:**
HPCToolkit profiles ALL GPUs used by the application automatically. The number of GPUs is determined by:
1. The application's own arguments/configuration
2. MPI rank distribution
3. CUDA_VISIBLE_DEVICES or similar environment variables

**Fix:**
Remove `-dev num-avail=$num_gpus` from hpcrun command line, or pass it correctly to the executable if that's what the user's application expects.

## Additional Tools Identified

### hpcprof-mpi
- **Purpose**: MPI-parallel version of hpcprof for large experiments
- **Location**: Built with `+mpi` Spack variant
- **Usage**: `mpirun -n 8 hpcprof-mpi measurements`
- **Recommendation**: Worth creating separate SWE-agent tool for this

### hpctracedump
- **Purpose**: Dump trace data from measurements
- **Location**: `src/hpctracedump/`
- **Usage**: TBD (need to investigate further)

### hpctoolkit utilities
- **hpcrun**: Measurement (already covered)
- **hpcstruct**: Structure analysis (already covered)
- **hpcprof**: Attribution (already covered)
- **hpcprof-mpi**: MPI attribution
- **hpcviewer**: GUI viewer (separate tool, not for SWE-agent)

## Recommendations for Tool Enhancement

### Priority 1: Critical Fixes
1. ✅ **Fix `-dev num-avail` bug** - Remove or clarify usage
2. ✅ **Document correct GPU control** - Via app args, not hpcrun

### Priority 2: Important Enhancements
3. **Add hpcstruct options**:
   - `-j` for parallel job control
   - Cache support for repeated profiling
   - Exclude/include problematic binaries

4. **Add hpcprof options**:
   - `-j` for thread control
   - `-R` for path replacement

### Priority 3: Additional Tools
5. **Create hpcprof-mpi tool** - For large-scale experiments
6. **Add trace enable/disable option** - Currently hardcoded to `-tt`
7. **Add custom event support** - Allow CPU sampling events

### Priority 4: Nice to Have
8. **Add DCGM check** - Verify DCGM is installed before using
9. **Add environment variable support** - For advanced users
10. **Add dry-run mode** - Show commands without executing

## Verified Command Sequences

### Correct Workflow for GPU Profiling

**Single GPU:**
```bash
# Measurement
hpcrun -e gpu=nvidia -tt -o measurements ./myapp [app-args]

# Structure
hpcstruct measurements

# Attribution
hpcprof -o database measurements
```

**Multi-GPU (MPI):**
```bash
# Measurement (4 GPUs, 4 ranks)
srun -n 4 hpcrun -e gpu=nvidia -tt -o measurements ./myapp [app-args]

# Structure
hpcstruct -j 16 measurements

# Attribution (use hpcprof-mpi for very large runs)
hpcprof-mpi -o database measurements
# OR regular hpcprof for smaller runs
hpcprof -j 32 -o database measurements
```

**With caching:**
```bash
export HPCTOOLKIT_HPCSTRUCT_CACHE=/path/to/cache
hpcstruct measurements
```

**Excluding problematic binaries:**
```bash
hpcstruct -x libmpi.so.12.5.0 measurements
```

## Environment Variables (from doc/src/users/environment-vars.md)

| Variable | Purpose | Set by |
|----------|---------|--------|
| `HPCRUN_EVENT_LIST` | Event list for sampling | `hpcrun -e` |
| `HPCRUN_TRACE` | Enable tracing | `hpcrun -t/-tt` |
| `HPCRUN_OUT_PATH` | Output directory | `hpcrun -o` |
| `HPCTOOLKIT_HPCSTRUCT_CACHE` | Structure cache | User/script |

## Testing Checklist

- [ ] Test with actual CHAMPS+ executable
- [ ] Verify GPU profiling works correctly
- [ ] Test with MPI (multiple ranks)
- [ ] Verify measurements directory creation
- [ ] Verify database directory creation
- [ ] Test with Hatchet analysis
- [ ] Verify DCGM pause/resume
- [ ] Test error handling

## References

**Documentation Files Reviewed:**
- `/pscratch/sd/k/krydzy/hpctoolkit/README.md`
- `/pscratch/sd/k/krydzy/hpctoolkit/doc/src/users/quickstart.md`
- `/pscratch/sd/k/krydzy/hpctoolkit/doc/src/users/hpcrun/hpcrun.md`
- `/pscratch/sd/k/krydzy/hpctoolkit/doc/src/users/gpu/gpu.md`
- `/pscratch/sd/k/krydzy/hpctoolkit/doc/src/users/environment-vars.md`

**Online Documentation:**
- https://hpctoolkit.gitlab.io/hpctoolkit/

**Source Code:**
- `/pscratch/sd/k/krydzy/hpctoolkit/src/hpcrun/`
- `/pscratch/sd/k/krydzy/hpctoolkit/src/hpcstruct/`
- `/pscratch/sd/k/krydzy/hpctoolkit/src/hpcprof/`
