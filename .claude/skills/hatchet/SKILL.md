---
name: hatchet
description: "Knowledge about the hatchet performance analysis library including tree data structures, profile loading from HPCToolkit/caliper formats, filtering, aggregation, and metric extraction. Load when implementing profile analysis tools."
---

# Hatchet Performance Analysis Library

Python library (LLNL) for analyzing hierarchical performance profiles as tree data structures paired with pandas DataFrames.

## Installation

Local fork at `/pscratch/sd/k/krydzy/hatchet` (branch `develop`, v1.4.1) includes the HPCToolkit v4 binary reader.

```bash
cd /pscratch/sd/k/krydzy/hatchet && pip install --use-pep517 .
```

## Loading Profiles

```python
import hatchet as ht
gf = ht.GraphFrame.from_hpctoolkit(database_dir)  # auto-detects v3 (XML) vs v4 (meta.db)
```

Also supports Caliper (`from_caliper`), TAU (`from_tau`), Score-P (`from_scorep`), and others.

## GraphFrame Basics

A GraphFrame combines a call tree (`graph`) with a pandas DataFrame of metrics.

Key attributes:
- `gf.graph` — tree of `Node` objects, each with a `frame` dict (`name`, `file`, `line`, `type`)
- `gf.dataframe` — multi-indexed DataFrame (index levels: `node`, optionally `rank`, `thread`)
- `gf.exc_metrics` — exclusive metric column names (self time only)
- `gf.inc_metrics` — inclusive metric column names (self + children)
- `gf.default_metric` — default metric for operations

## Metric Types

- **Exclusive** (`time`, `GKER (sec)`): time spent in the function itself, excluding callees.
- **Inclusive** (`time (inc)`, `GKER (sec) (inc)`): time in the function plus all its callees.

The v4 reader auto-renames `"CPUTIME (sec)"` to `"time"`. GPU profiling produces `GKER (sec)` as the primary metric.

## Key Operations

### Filter

Remove nodes that don't match a predicate; `squash=True` (default) rewrites the tree to stay consistent.

```python
filtered_gf = gf.filter(lambda row: row["time"] > 0.01, squash=True)
```

### Squash

Rewrites the graph in-place to remove nodes not present in the DataFrame, reconnecting children to nearest surviving ancestor.

```python
gf.squash()
```

### Query

Pattern-based filtering using `QueryMatcher`.

```python
from hatchet import QueryMatcher
query = QueryMatcher().match("*", lambda row: row["time"] > 0.01)
filtered_gf = gf.filter(query)
```

### Hot Path

Returns a **list of Node objects** (NOT a GraphFrame) tracing root to hottest leaf.

```python
nodes = gf.hot_path(metric="time (inc)", threshold=0.5)
for node in nodes:
    name = node.frame.get('name', '<unknown>')
    val = gf.dataframe.loc[node, "time (inc)"]
    if hasattr(val, 'mean'):  # multi-rank returns Series
        val = val.mean()
```

This is the pattern used in our `hatchet_analyze` tool for hot-path extraction.

### Tree Rendering

```python
tree_str = gf.tree(metric_column="time (inc)", depth=10)  # NOTE: param is depth=, NOT max_depth=
```

### Load Imbalance (MPI only)

```python
imb_gf = gf.load_imbalance(metric_column="time (inc)")
# Adds columns: "{metric}.imbalance", "{metric}.mean", "{metric}.max"
```

### Drop Index Levels

```python
gf.drop_index_levels(function=np.mean)  # Collapse rank/thread dims
```

## Our Tool Wrapper

**Path**: `tools/hatchet/bin/hatchet_analyze` (Python CLI)
**Utilities**: `tools/hatchet/lib/hatchet_utils.py`
**Config**: `tools/hatchet/config.yaml`

Usage: `hatchet_analyze <database_dir> [<metric>]`

Pass the `database/` subdirectory, NOT the parent: `hatchet_analyze ./profile_output/database`

The tool auto-detects the best metric (priority: `GKER (sec)` > `time` > `cycles` > first numeric column) and generates a structured report with: profile overview, hot path, top 20 functions, source locations, load imbalance, and call tree summary.

## Known Issues

- **"(0)" metric values** can confuse the agent into thinking a function is free; these are rounding artifacts on small values.
- **Large profiles are slow** to parse; multi-rank profiles with millions of nodes can take minutes.
- **"meta.db not found"**: you passed the parent dir instead of the `database/` subdirectory.
- **hot_path() returns a list**, not a GraphFrame; don't call `.tree()` on the result.
- **load_imbalance() column name** is `"{metric}.imbalance"`, not `"imbalance"`.
- **Metric name mismatch**: user passes `"time"` but only `"time (inc)"` exists; use `get_metric_column()` helper to resolve.
- **Multi-rank metric access**: `gf.dataframe.loc[node, metric]` may return a Series (one per rank); use `.mean()` to aggregate.
- **tree() depth parameter**: use `depth=`, not `max_depth=`.
