# GPA-Benchmark App Catalog

## Configured Apps

Full list from `driver_apps.yaml`: exatensor, lulesh, xsbench, b+tree, backprop, bfs, gaussian, heartwall, hotspot, huffman, lavaMD, lud, nw, particlefilter, pathfinder, srad, streamcluster.

### App Sources

- **Rodinia apps**: `rodinia/{app}/` (baseline), `rodinia/{app}-opt*/` (optimized variants)
- **Other apps**: `ExaTENSOR/`, `LULESH/`, `XSBench/`

### Difficulty Grouping

- **Easy** (clear signal): hotspot, cfd, gaussian, particlefilter
- **Medium** (kernel logic): backprop, bfs, lud, streamcluster
- **Hard** (subtle): myocyte (20K lines), srad (1.03x), pathfinder (1.05x)

## Python API

```python
from gpa_bench_driver.gpa_bench_driver import run_driver
results, operations, long_results = run_driver(app="gaussian", nsys=True, sm_version=80)

# Test agent-generated code via swaps_override
results, ops, lr = run_driver(app="gaussian", swaps_override={"// gaussian.cu\n": optimized_code})
```

## Driver Pass Flow

For each app: copy to temp dir -> swap file in (if testing) -> `make -j 8 SM_VERSION={sm}` -> run -> validate -> profile -> swap file out -> report.

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

## Integration Pattern

To integrate a GPA-Benchmark app into the HPC agent harness:

1. Create a harness tool pair (`{app}_build`, `{app}_run`) in `tools/{app}_harness/`
2. The build tool should call `python -m gpa_bench_driver --app {app} --build-only --sm-version 80`
3. The run tool should call `python -m gpa_bench_driver --app {app} --sm-version 80 -n 3 -o results.json`
4. For agent optimization testing, use `run_driver()` with `swaps_override` parameter
5. Add a config YAML in `config/hpc/` following the existing pattern
6. Add dataset entries to `dataset/curated_perf_commits.json`

## Additional CLI Options

```bash
python -m gpa_bench_driver --app gaussian --build-only        # build only
python -m gpa_bench_driver --app gaussian -n 5 -o results.json  # 5 samples, JSON output
```

## Dependencies

- Python >=3.12.11, alive-progress, pandas, pysqlite3, pyyaml
