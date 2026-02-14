# HPCToolkit Output Format & Hatchet Integration

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

## Benchmark Config Integration

Enabled in benchmark configs via tool bundle:
```yaml
agent:
  tools:
    bundles:
      - path: tools/hpctoolkit    # hpc_profile
      - path: tools/hatchet       # hatchet_analyze (downstream analysis)
```

## Companion Tools

| Tool | Purpose |
|------|---------|
| `hatchet_analyze` | Parse HPCToolkit database into LLM-friendly analysis |
| `check_profiling_ready` | Pre-flight: checks GPU, profilers, DCGM, memory, disk |
| `profiler_info` | Lists available profiling tools |
| `compiler_analysis` | nvcc register/shared mem analysis |
| `benchmark_code` | Git-based baseline comparison with correctness check |

## Advanced Notes

- For large-scale runs use `srun -n 8 hpcprof-mpi` (needs `+mpi` spack variant).
- The v4 database format is binary (not the older XML experiment.xml format).
- `meta.db` contains the context tree and all metric definitions.
- `profile.db` uses a sparse format -- only non-zero values stored.
