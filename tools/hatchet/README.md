# Hatchet Analysis Tool

This SWE-agent tool provides automated analysis of HPCToolkit profiling data using Hatchet, generating LLM-friendly text output for performance analysis.

## What It Does

The `hatchet_analyze` tool reads HPCToolkit profiling databases and generates comprehensive performance reports including:

1. **Hot Path Analysis**: Identifies the most time-consuming execution paths
2. **Function Ranking**: Lists top 20 functions by time/metric with percentages
3. **Load Imbalance Analysis**: Shows performance distribution across MPI ranks
4. **Call Tree Summary**: Displays hierarchical calling context with metrics

## Usage

```bash
hatchet_analyze <database_dir> [metric]
```

### Arguments

- **database_dir** (required): Path to HPCToolkit database directory (created by `hpcprof` or `hpc_profile`)
- **metric** (optional): Metric to analyze (default: "time"). Common options include:
  - `time` - Wall-clock time (default)
  - `cycles` - CPU cycles
  - `instructions` - Instruction count
  - Other metrics available in the profiling data

### Examples

```bash
# Basic analysis with default metric (time)
hatchet_analyze ./profiling_results/database

# Analyze with specific metric
hatchet_analyze ./profiling_results/database cycles

# Analyze after running hpc_profile
hpc_profile ./myapp ./results
hatchet_analyze ./results/database
```

## Prerequisites

Hatchet must be installed. The tool will attempt to install it via `pip` during bundle initialization, or you can install manually:

```bash
pip install hatchet
```

## Output Format

The tool generates structured text output with the following sections:

```
================================================================================
HPCToolkit Performance Analysis (via Hatchet)
================================================================================

## Profile Overview
Metric: time
Number of ranks: 4
Available metrics: time, cycles, instructions

## Hot Path Analysis
Critical execution path (most time-consuming):
[Hot path tree visualization]

## Top 20 Functions by Time
 1. function_name_1                                             45.23% (12.345s)
 2. function_name_2                                             23.45% (6.789s)
...

## Load Imbalance Analysis
Number of MPI ranks: 4
Load imbalance metrics:
[Imbalance statistics]

## Call Tree Summary
Hierarchical calling context (metric: time, max depth: 10):
[Full call tree with metrics]

================================================================================
End of Analysis
================================================================================
```

## Features

- **LLM-Friendly Output**: Structured text format optimized for AI interpretation
- **Comprehensive Analysis**: Multiple analysis perspectives in one command
- **Multi-Rank Support**: Analyzes load imbalance for MPI applications
- **Flexible Metrics**: Supports any metric in the profiling database
- **Error Handling**: Clear error messages for missing dependencies or invalid data

## Integration with HPCToolkit Tool

These tools work together seamlessly:

```bash
# Step 1: Profile your application
hpc_profile /path/to/executable ./profiling_results 4

# Step 2: Analyze the results
hatchet_analyze ./profiling_results/database
```

## Analyzing Results

The output helps identify:

- **Bottlenecks**: Functions consuming the most time
- **Critical Paths**: Sequences of calls that dominate execution
- **Load Imbalance**: Uneven work distribution across processes
- **Call Structure**: How functions relate in the calling hierarchy

Use this information to:
- Target optimization efforts effectively
- Understand application behavior
- Compare performance across different runs
- Identify parallelization opportunities

## About Hatchet

Hatchet is a Python library developed by the Performance and Systems Software Group (PSSG) for analyzing hierarchical performance data. It uses pandas DataFrames to provide powerful analysis capabilities for profiling data from HPCToolkit, Caliper, TAU, and other tools.

- **GitHub**: https://github.com/hatchet/hatchet
- **Documentation**: https://hatchet.readthedocs.io/

## Troubleshooting

### "Hatchet is not installed"

Install Hatchet manually:
```bash
pip install hatchet
```

### "Failed to load HPCToolkit database"

Ensure the path points to a valid HPCToolkit database directory created by `hpcprof` or `hpc_profile`. The directory should contain:
- `experiment.xml` or similar HPCToolkit database files
- Profiling measurement data

### "Metric 'X' not found"

Use the "Available metrics" line in the output to see which metrics are available in your profiling data, then specify the correct metric name.

## Notes

- Analysis time depends on the size of the profiling database
- For very large databases, consider filtering data before analysis
- The tool outputs analysis to stdout and status messages to stderr
- Multi-rank analysis requires profiling data from MPI applications
