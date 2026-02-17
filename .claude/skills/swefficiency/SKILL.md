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
- **Local clone**: `/pscratch/sd/k/krydzy/swefficiency/` (symlinked at `~/swefficiency`)

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

Existing predictions: `/pscratch/sd/k/krydzy/swefficiency/predictions/converted/` (20+ models including OpenHands, SWE-agent, Cursor runs with various LLMs).

## Inference Harness (`scripts/inference/custom.py`)

Self-contained harness for running agents inside SWE-fficiency containers:
- **Spec-driven**: YAML configs define pre-work, inference command, patch extraction
- **Templating**: Jinja2 rendering of env vars, instance metadata, API keys
- **Parallel**: `--num_workers N` for concurrent instances
- **Output**: `logs/run_inference/<run_id>/<spec_name>/<instance_id>/patch.diff`

Example spec at `scripts/inference/specs/cursor_cli.yaml`.

## Evaluation Pipeline

Docker-based (podman-hpc on Perlmutter). Three-layer image build:
1. **Base image** — Ubuntu + language runtime
2. **Env image** — repo + dependency installation
3. **Instance image** — at `base_commit`, ready for patch

Per-instance evaluation:
1. Run `workload.py` -> baseline timing
2. `git apply` model patch
3. Re-run `workload.py` -> optimized timing
4. Run covering tests (PASS_TO_PASS correctness)
5. Introspection guard (verify patch doesn't game workload)

Prebuilt images: `ghcr.io/swefficiency/swefficiency-images:<instance_id>`

## Report Output

```bash
swefficiency report --gold_run ... --pred_run ... --report_output eval_reports/
```

Produces:
- `eval_report_<model>.csv` — per-instance results (instance_id, SR, correctness, timing)
- `eval_report_<model>.json` — summary: `overall_score` (harmonic mean SR), `proportion_incorrect`, `proportion_correct_but_no_speedup`, `proportion_human_speedup_or_better`

## Common Issues

- **Docker images**: Prebuilt at `ghcr.io/swefficiency/swefficiency-images:<instance_id>`
- **podman-hpc on Perlmutter**: Use `podman-hpc` instead of `docker`
- **CPU pinning**: 4 vCPUs, 16 GB RAM per worker recommended
- **Agent limits**: 3 hours wall-clock, 100 max actions per instance
- **Timeout**: Default 2 hours per instance; configurable in eval

For detailed reference, see references/ in this skill directory.
