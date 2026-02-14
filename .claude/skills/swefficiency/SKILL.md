---
name: swefficiency
description: "SWE-fficiency benchmark for LLM code optimization. Use when user mentions 'swe-fficiency', 'swefficiency', Python optimization tasks, speedup ratios, or the 498-task dataset."
user-invocable: false
---

# SWE-fficiency

Repository-level benchmark for **performance optimization** (not bug fixing). 498 tasks across 9 Python repos. Each ships a codebase, a performance workload, and correctness tests.

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

SR > 1.0 = agent beat the human expert. Failed correctness -> SR = 1/expert_speedup.

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

Key flags: `--instances_regex "pandas.*"`, `--force_rerun`, `--num_workers N`.

## Prediction Format

JSONL, one line per instance:
```json
{"instance_id": "<id>", "model_patch": "<git_diff>", "model_name_or_path": "<model>"}
```

Existing predictions: `/pscratch/sd/k/krydzy/swefficiency/predictions/converted/`.

## Evaluation Pipeline

Docker-based. Each instance runs in prebuilt container:
1. Run `workload.py` -> baseline timing
2. `git apply` model patch
3. Re-run `workload.py` -> optimized timing
4. Run covering tests
5. Introspection guard (verify patch doesn't game workload)

## Common Issues

- **Docker images**: Prebuilt on Docker Hub (`swefficiency/swefficiency_images:<instance_id>`)
- **CPU pinning**: 4 vCPUs, 16 GB RAM per worker recommended
- **Agent limits**: 3 hours wall-clock, 100 max actions per instance

For detailed reference, see references/ in this skill directory.
