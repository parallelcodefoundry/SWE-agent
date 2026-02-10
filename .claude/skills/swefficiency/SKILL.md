---
name: swefficiency
description: "Knowledge about the SWE-fficiency benchmark dataset and harness for evaluating LLM optimization of real-world repositories. Load when working with SWE-fficiency benchmarks or integrating them into our benchmark suite."
---

# SWE-fficiency

Repository-level benchmark for **performance optimization** (not bug fixing). 498 tasks across 9 Python repos. Each ships a codebase, a performance workload, and correctness tests. Measures whether agents can find bottlenecks, propose safe optimizations, and prove correctness.

- **Paper**: arXiv:2511.06090
- **Dataset**: `swefficiency/swefficiency` on HuggingFace
- **Repos**: numpy, scipy, pandas, scikit-learn, matplotlib, xarray, sympy, dask, astropy
- **Local clone**: `/pscratch/sd/k/krydzy/swefficiency/`

## Core Metric: Speedup Ratio (SR)

```
Expert speedup = T_pre / T_post_gold
Model speedup  = T_pre / T_post_lm
SR = Model speedup / Expert speedup    (harmonic mean across tasks)
```

SR > 1.0 = agent beat the human expert. Failed correctness → SR = 1/expert_speedup.

## Key Dataset Fields

| Field | Description |
|-------|-------------|
| `instance_id` | e.g., `pandas-dev__pandas-28447` |
| `repo`, `base_commit` | GitHub repo + pinned SHA |
| `patch` | Expert optimization diff |
| `workload` | Python script measuring the bottleneck |
| `covering_tests` | Tests covering the expert diff |
| `PASS_TO_PASS` | Tests that must stay green |
| `image_name` | Prebuilt Docker image |
| `rebuild_cmd` | pip install after edits |

## CLI

```bash
cd /pscratch/sd/k/krydzy/swefficiency
uv venv --python 3.12 && source .venv/bin/activate && uv sync

# Step 1: Gold baseline (expert patches)
swefficiency eval --run_id my_eval --num_workers 12

# Step 2: Model predictions
swefficiency eval --run_id my_eval --num_workers 12 --prediction_path predictions.jsonl

# Step 3: Report
swefficiency report --gold_run logs/run_evaluation/my_eval/gold \
                    --pred_run logs/run_evaluation/my_eval/<model_name>
```

Key flags: `--instances_regex "pandas.*"`, `--force_rerun`, `--num_workers N` (default 4, paper uses 12).

## Prediction Format

JSONL, one line per instance:
```json
{"instance_id": "<id>", "model_patch": "<git_diff>", "model_name_or_path": "<model>"}
```

Existing predictions: `/pscratch/sd/k/krydzy/swefficiency/predictions/converted/` (`oh_*.jsonl`, `sweagent_*.jsonl`, `cursor_*.jsonl`).

## Evaluation Pipeline

Docker-based. Each instance runs in prebuilt container (`swefficiency/swefficiency_images:<instance_id>`):
1. Run `workload.py` → baseline timing
2. `git apply` model patch
3. Re-run `workload.py` → optimized timing
4. Run covering tests (parallel + single-threaded)
5. Introspection guard (verify patch doesn't game workload)

Key files: `swefficiency/harness/run_validation.py` (main driver), `swefficiency/harness/test_spec.py` (TestSpec + scripts), `swefficiency/report.py` (CSV/JSON reports).

## Agent Integration

### Generic Inference Harness

`scripts/inference/custom.py` runs any agent inside SWE-fficiency containers using YAML specs:

```bash
python scripts/inference/custom.py --spec specs/<agent>.yaml --run-id <id>
```

See `scripts/inference/specs/cursor_cli.yaml` for example. YAML defines: Docker config, prework, inference command, patch extraction, artifacts.

### Adding a New Agent

1. Create `scripts/inference/specs/<agent>.yaml`
2. Create Jinja2 templates in `scripts/inference/templates/`
3. Run inference: `python scripts/inference/custom.py --spec specs/<agent>.yaml --run-id <id>`
4. Convert patches: write `predictions/converted/<agent>_conversion.py`
5. Evaluate: `swefficiency eval --prediction_path predictions/converted/<agent>.jsonl`

## Reproducibility

- **CPU pinning**: 4 vCPUs, 16 GB RAM per worker (see `scripts/vm/setup_docker.sh`)
- **Recommended**: GCP `n2-standard-64` with 12 workers
- **Agent limits**: 3 hours wall-clock, 100 max actions per instance
- **Docker images**: prebuilt on Docker Hub

## Key File Reference

| File | Purpose |
|------|---------|
| `swefficiency/cli.py` | CLI entry (`eval`, `report`) |
| `swefficiency/harness/run_validation.py` | Main eval driver |
| `swefficiency/harness/test_spec.py` | TestSpec, script generation |
| `swefficiency/harness/constants.py` | Instance TypedDict, repo specs |
| `swefficiency/report.py` | Report generation |
| `scripts/inference/custom.py` | Generic inference harness |
| `scripts/inference/specs/cursor_cli.yaml` | Example agent spec |
| `predictions/converted/` | Conversion scripts per agent |
