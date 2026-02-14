---
name: hatchet
description: "Hatchet performance analysis: tree data structures, profile loading, filtering, and metrics. Use when user mentions 'hatchet', 'GraphFrame', 'call tree', 'profile analysis', or needs to parse HPCToolkit/caliper output."
user-invocable: false
---

# Hatchet Performance Analysis Library

Python library (LLNL) for analyzing hierarchical performance profiles as tree data structures paired with pandas DataFrames.

For detailed reference, see references/ in this skill directory.

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

- `gf.graph` -- tree of `Node` objects, each with a `frame` dict (`name`, `file`, `line`, `type`)
- `gf.dataframe` -- multi-indexed DataFrame (index levels: `node`, optionally `rank`, `thread`)
- `gf.exc_metrics` / `gf.inc_metrics` -- exclusive/inclusive metric column names
- `gf.default_metric` -- default metric for operations

## Key Operations

```python
# Filter: remove nodes not matching predicate
filtered_gf = gf.filter(lambda row: row["time"] > 0.01, squash=True)

# Hot path: list of Nodes from root to hottest leaf
nodes = gf.hot_path(metric="time (inc)", threshold=0.5)

# Tree rendering (NOTE: param is depth=, NOT max_depth=)
tree_str = gf.tree(metric_column="time (inc)", depth=10)

# Load imbalance (MPI)
imb_gf = gf.load_imbalance(metric_column="time (inc)")

# Drop index levels
gf.drop_index_levels(function=np.mean)
```

## Our Tool Wrapper

**Path**: `tools/hatchet/bin/hatchet_analyze` (Python CLI)
**Utilities**: `tools/hatchet/lib/hatchet_utils.py`

Usage: `hatchet_analyze <database_dir> [<metric>]`

Pass the `database/` subdirectory, NOT the parent: `hatchet_analyze ./profile_output/database`

The tool auto-detects the best metric (priority: `GKER (sec)` > `time` > `cycles` > first numeric) and generates a structured report with: profile overview, hot path, top 20 functions, source locations, load imbalance, and call tree summary.

## Common Issues

- **"meta.db not found"**: you passed the parent dir instead of the `database/` subdirectory.
- **hot_path() returns a list**, not a GraphFrame; don't call `.tree()` on the result.
- **tree() depth parameter**: use `depth=`, not `max_depth=`.
- **Multi-rank metric access**: `gf.dataframe.loc[node, metric]` may return a Series; use `.mean()`.
