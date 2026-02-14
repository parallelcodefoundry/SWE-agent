# Hatchet Advanced Reference

## Metric Types

- **Exclusive** (`time`, `GKER (sec)`): time spent in the function itself, excluding callees.
- **Inclusive** (`time (inc)`, `GKER (sec) (inc)`): time in the function plus all its callees.

The v4 reader auto-renames `"CPUTIME (sec)"` to `"time"`. GPU profiling produces `GKER (sec)` as the primary metric.

## Hot Path Pattern (used in hatchet_analyze)

```python
nodes = gf.hot_path(metric="time (inc)", threshold=0.5)
for node in nodes:
    name = node.frame.get('name', '<unknown>')
    val = gf.dataframe.loc[node, "time (inc)"]
    if hasattr(val, 'mean'):  # multi-rank returns Series
        val = val.mean()
```

## QueryMatcher

Pattern-based filtering:

```python
from hatchet import QueryMatcher
query = QueryMatcher().match("*", lambda row: row["time"] > 0.01)
filtered_gf = gf.filter(query)
```

## Squash

Rewrites the graph in-place to remove nodes not present in the DataFrame, reconnecting children to nearest surviving ancestor.

```python
gf.squash()
```

## Load Imbalance Details

```python
imb_gf = gf.load_imbalance(metric_column="time (inc)")
# Adds columns: "{metric}.imbalance", "{metric}.mean", "{metric}.max"
```

Column name is `"{metric}.imbalance"`, not `"imbalance"`.

## Known Issues and Artifacts

- **"(0)" metric values** can confuse the agent into thinking a function is free; these are rounding artifacts on small values.
- **Large profiles are slow** to parse; multi-rank profiles with millions of nodes can take minutes.
- **load_imbalance() column name** is `"{metric}.imbalance"`, not `"imbalance"`.
- **Metric name mismatch**: user passes `"time"` but only `"time (inc)"` exists; use `get_metric_column()` helper to resolve.
- **Multi-rank metric access**: `gf.dataframe.loc[node, metric]` may return a Series (one per rank); use `.mean()` to aggregate.
