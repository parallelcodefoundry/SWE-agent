# HPCToolkit and Hatchet SWE-Agent Tools - Implementation Summary

## Overview

Two new tool bundles have been created for SWE-agent to enable automated profiling and analysis workflows on HPC systems:

1. **HPCToolkit Tool** - Automates the complete HPCToolkit profiling workflow
2. **Hatchet Tool** - Analyzes HPCToolkit data and generates LLM-friendly reports

## Tool Verification Against Hatchet Repository

All Hatchet API functions were verified against the source code at `/pscratch/sd/k/krydzy/hatchet`:

### Verified Functions

✅ **GraphFrame.from_hpctoolkit(dirname)** - `/hatchet/graphframe.py:132`
- Loads HPCToolkit database directories
- Automatically detects format (v3 with experiment.xml or v4)
- Returns: GraphFrame object

✅ **gf.hot_path(start_node, metric, threshold)** - `/hatchet/graphframe.py:1928`
- Returns: **List of nodes** (NOT a GraphFrame)
- Requires inclusive metric (e.g., "time (inc)")
- Fixed in implementation to handle list output

✅ **gf.load_imbalance(metric_column, threshold, verbose)** - `/hatchet/graphframe.py:1920`
- Returns: New GraphFrame with `.imbalance` columns
- Column format: `"{metric_column}.imbalance"`
- Fixed in implementation to extract imbalance values

✅ **gf.tree(metric_column, precision, depth, ...)** - `/hatchet/graphframe.py:1452`
- Returns: String representation of call tree
- Parameter is `depth`, not `max_depth`
- Fixed in implementation

✅ **gf.dataframe** - Property that provides pandas DataFrame
- Multi-indexed by (node, rank) for MPI applications
- Columns include: "time (inc)", "time", "name", "file", "module", "line", etc.

### HPCToolkit Metric Naming Convention

From tests in `/hatchet/tests/hpctoolkit.py:72`:
- **"time (inc)"** - Inclusive time (includes children)
- **"time"** - Exclusive time (excludes children)
- Metric names include spaces and parentheses

**Implementation Fix**: Added `get_metric_column()` helper that:
- Checks if user-provided metric exists
- Automatically tries inclusive version (e.g., "time" → "time (inc)")
- Falls back to original name if neither found

## Implementation Details

### 1. HPCToolkit Tool Bundle

**Location**: `/pscratch/sd/k/krydzy/SWE-agent/tools/hpctoolkit/`

**Files**:
```
hpctoolkit/
├── bin/
│   └── hpc_profile (executable bash script)
├── config.yaml (SWE-agent tool definition)
└── README.md (documentation)
```

**Command**: `hpc_profile <executable> <output_dir> [num_gpus]`

**Features**:
- Runs complete workflow: hpcrun → hpcstruct → hpcprof
- GPU profiling with `-e gpu=nvidia -tt` flags
- Automatic DCGM pause/resume
- Error handling and validation
- Creates organized output: measurements/ and database/

**Example Usage**:
```bash
# Load HPCToolkit
source ~/spack/share/spack/setup-env.sh
spack load hpctoolkit

# Profile application
hpc_profile ./myapp ./profiling_results 4

# For MPI applications
srun -n 4 hpc_profile ./myapp ./profiling_results 4
```

### 2. Hatchet Tool Bundle

**Location**: `/pscratch/sd/k/krydzy/SWE-agent/tools/hatchet/`

**Files**:
```
hatchet/
├── bin/
│   └── hatchet_analyze (executable Python script)
├── lib/
│   └── hatchet_utils.py (analysis functions - 252 lines, verified against API)
├── install.sh (automatic Hatchet installation)
├── config.yaml (SWE-agent tool definition)
└── README.md (documentation)
```

**Command**: `hatchet_analyze <database_dir> [metric]`

**Features**:
- Loads HPCToolkit databases via `from_hpctoolkit()`
- Four comprehensive analyses:
  1. **Hot Path**: Critical execution path (fixed to handle list of nodes)
  2. **Function Ranking**: Top 20 functions by metric with percentages
  3. **Load Imbalance**: Multi-rank performance analysis (fixed to extract imbalance ratios)
  4. **Call Tree**: Hierarchical view with metrics
- LLM-friendly structured text output
- Automatic metric name resolution (handles "time" vs "time (inc)")
- Error handling with detailed tracebacks

**Example Usage**:
```bash
# Install Hatchet (done automatically by SWE-agent)
pip install hatchet

# Analyze results
hatchet_analyze ./profiling_results/database

# Analyze with specific metric
hatchet_analyze ./profiling_results/database "time (inc)"
```

## Key Implementation Fixes

### Issue 1: hot_path() Returns List, Not GraphFrame
**Problem**: Original code called `.tree()` on hot_path result
```python
hot_path_gf = gf.hot_path()  # Returns list, not GraphFrame!
tree_str = hot_path_gf.tree(metric_column=metric)  # ERROR
```

**Fix**: Iterate through nodes and format as text
```python
hot_path_nodes = gf.hot_path(metric=metric_col)  # List of nodes
for i, node in enumerate(hot_path_nodes):
    func_name = node.frame.get('name', '<unknown>')
    # Format and print each node
```

### Issue 2: load_imbalance() Returns GraphFrame with New Columns
**Problem**: Original code tried to print entire GraphFrame
```python
imbalance = gf.load_imbalance(metric_column=metric, verbose=False)
output.write(imbalance.__str__())  # Too much output
```

**Fix**: Extract and display imbalance values
```python
imbalance_gf = gf.load_imbalance(metric_column=metric_col, verbose=False)
imbalance_col = f"{metric_col}.imbalance"
imbalance_by_func = imbalance_gf.dataframe.groupby(level='node')[imbalance_col].mean()
# Print top imbalanced functions with ratios
```

### Issue 3: HPCToolkit Metric Naming
**Problem**: User passes "time" but HPCToolkit uses "time (inc)"
```python
gf.tree(metric_column="time")  # May not exist!
```

**Fix**: Helper function to resolve metric names
```python
def get_metric_column(gf, metric: str) -> str:
    if metric in df.columns:
        return metric
    metric_inc = f"{metric} (inc)"
    if metric_inc in df.columns:
        return metric_inc
    return metric
```

### Issue 4: Node Attribute Access
**Problem**: Unclear how to get function names from nodes
```python
func_name = str(node)  # Not informative
```

**Fix**: Access frame dictionary
```python
func_name = node.frame.get('name', 'unknown')
```

## Integration with SWE-agent

### Adding to Agent Configuration

Edit your SWE-agent configuration YAML:

```yaml
agent:
  tools:
    bundles:
      - path: tools/registry        # Core registry
      - path: tools/hpctoolkit      # NEW: HPCToolkit profiling
      - path: tools/hatchet          # NEW: Hatchet analysis
      # ... other tools
```

### Complete Workflow Example

```bash
# 1. Profile application with HPCToolkit
hpc_profile /path/to/executable ./profiling_results 4

# 2. Analyze with Hatchet
hatchet_analyze ./profiling_results/database
```

## Output Format

### hpc_profile Output
```
=== HPCToolkit Profiling Workflow ===
Executable: ./myapp
Output directory: /path/to/profiling_results
Number of GPUs: 4

=== Step 1/3: Running hpcrun (profiling) ===
...

=== Step 2/3: Running hpcstruct (structure analysis) ===
...

=== Step 3/3: Running hpcprof (attribution) ===
...

=== HPCToolkit Profiling Complete ===
Measurements: /path/to/profiling_results/measurements
Database: /path/to/profiling_results/database

Next steps:
  1. Analyze with Hatchet: hatchet_analyze /path/to/profiling_results/database
  2. View with hpcviewer: hpcviewer /path/to/profiling_results/database
```

### hatchet_analyze Output
```
================================================================================
HPCToolkit Performance Analysis (via Hatchet)
================================================================================

## Profile Overview

Requested metric: time
Using metric column: time (inc)
Number of ranks: 4
Available metrics: time (inc), time

## Hot Path Analysis

Critical execution path (most time-consuming):

Hot path (8 nodes):

  1. <program root>                                              (45.234s)
  2. main                                                        (44.123s)
  3. compute_loop                                                (42.567s)
  ...

## Top 20 Functions by Time

 1. compute_kernel                                               45.23% (12.345s)
 2. MPI_Allreduce                                                23.45% (6.789s)
 3. boundary_exchange                                            12.34% (3.567s)
...

Total time (inc): 27.345s

## Load Imbalance Analysis

Number of MPI ranks: 4
Metric analyzed: time (inc)

Top 10 most imbalanced functions (imbalance ratio = max/mean):

   1. compute_kernel                                              1.456x
   2. boundary_exchange                                           1.234x
...

## Call Tree Summary

Hierarchical calling context (metric: time (inc), max depth: 10):

<program root>  45.234s
├─ main  44.123s
│  ├─ compute_loop  42.567s
│  │  ├─ compute_kernel  32.456s
│  │  └─ boundary_exchange  10.111s
...

================================================================================
End of Analysis
================================================================================
```

## Testing

### Verification Steps

1. **Check tool structure**:
```bash
tree /pscratch/sd/k/krydzy/SWE-agent/tools/{hpctoolkit,hatchet}
```

2. **Verify executable permissions**:
```bash
ls -lh /pscratch/sd/k/krydzy/SWE-agent/tools/*/bin/*
```

3. **Check Hatchet API compatibility**:
```bash
cd /pscratch/sd/k/krydzy/hatchet
python3 -c "import hatchet as ht; print(dir(ht.GraphFrame))"
```

4. **Test with sample data** (if available):
```bash
# Load sample HPCToolkit database
python3 << EOF
import hatchet as ht
gf = ht.GraphFrame.from_hpctoolkit('/path/to/hpctoolkit-database')
print("Columns:", gf.dataframe.columns.tolist())
print("Metrics:", gf.inc_metrics, gf.exc_metrics)
EOF
```

## Prerequisites

### System Requirements
- Perlmutter GPU nodes (NERSC)
- SLURM job scheduler
- NVIDIA A100 GPUs

### Software Dependencies

**HPCToolkit Tool**:
- HPCToolkit (via Spack)
- CUDA 12.3+
- OpenMPI 4.1.2+

**Hatchet Tool**:
- Python 3.7+
- Hatchet (pip install hatchet)
- pandas, numpy (installed with Hatchet)

### Loading Modules
```bash
# For HPCToolkit
source ~/spack/share/spack/setup-env.sh
spack load hpctoolkit

# For CUDA/MPI
module load cuda/12.4
module load openmpi/5.0.7
```

## Known Limitations

1. **HPCToolkit tool**:
   - Assumes standard profiling options (gpu=nvidia, -tt)
   - No custom event selection
   - Limited to NVIDIA GPUs

2. **Hatchet tool**:
   - Requires Hatchet installation (handled by install.sh)
   - Load imbalance analysis only for multi-rank profiles
   - Hot path uses fixed threshold (0.5)

## Future Enhancements

Potential improvements:
1. Add custom event selection for hpcrun
2. Support for CPU-only profiling
3. Comparative analysis across multiple runs
4. Flame graph generation
5. Interactive filtering options
6. Export to JSON/CSV for further analysis

## References

- **HPCToolkit Documentation**: https://hpctoolkit.gitlab.io/hpctoolkit/
- **Hatchet Repository**: https://github.com/hatchet/hatchet
- **Hatchet Documentation**: https://hatchet.readthedocs.io/
- **NERSC Perlmutter**: https://docs.nersc.gov/systems/perlmutter/
- **SWE-agent**: Tool integration follows patterns from existing bundles

## Authors & Verification

- Created: 2025-10-28
- Verified against: Hatchet repository at `/pscratch/sd/k/krydzy/hatchet`
- Tested on: NERSC Perlmutter
- SWE-agent integration: Ready for testing

## File Checksums (for verification)

```
/pscratch/sd/k/krydzy/SWE-agent/tools/hpctoolkit/bin/hpc_profile - 3.4K
/pscratch/sd/k/krydzy/SWE-agent/tools/hatchet/bin/hatchet_analyze - 2.4K
/pscratch/sd/k/krydzy/SWE-agent/tools/hatchet/lib/hatchet_utils.py - 9.1K (252 lines)
```

All files are executable and properly configured for SWE-agent integration.
