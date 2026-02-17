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

Inference specs for all 4 frameworks: `scripts/inference/specs/{sweagent,opencode,codex_cli,openhands}.yaml`. Each spec has install templates in `scripts/inference/templates/`.

```bash
# Via benchmark runner (from SWE-agent repo root)
python3 batch/hpc_benchmark_runner.py --base --app swefficiency          # base mode
python3 batch/hpc_benchmark_runner.py --app swefficiency --framework sweagent  # agent mode

# Via run_benchmark.sh
bash batch/run_benchmark.sh --swefficiency --base
```

Curated subset: 12 parallelization-focused instances (4 strict concurrency, 2 Cython prange, 6 vectorization). Re-curated from original 27 general instances after audit confirmed 0 GPU/CUDA instances in the full 498-task dataset. Each instance takes ~77 min.

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

## Perlmutter Setup

Requires podman socket running (Docker SDK connects via it):
```bash
podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &
export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock
```

Venv: `/pscratch/sd/k/krydzy/swefficiency/.venv` (needs jinja2 + python-dotenv installed).

4 podman compatibility fixes applied (commit `be86360` in swefficiency repo):
- `docker_build.py`: Disabled `oom_kill_disable=True` (cgroupv2 incompatible)
- `cli.py`: Set `use_podman=True`
- `run_validation.py`: Skip cpu cgroup args in podman mode; fix taskset_cpus extraction
- `docker_utils.py`: Reset tar uid/gid to root for podman rootless

## Common Issues

- **Docker images**: Prebuilt at `ghcr.io/swefficiency/swefficiency-images:<instance_id>`
- **podman-hpc on Perlmutter**: Must start socket manually (see setup above)
- **`oom_kill_disable` error**: cgroupv2 incompatible — disabled in `docker_build.py`
- **cpu/cpuset cgroup error**: Not delegated on Perlmutter — `cpu_groups=None` when using podman
- **`lchown` tar error**: Reset uid/gid to 0 in `docker_utils.py` for podman rootless
- **Spec `name` field must match runner path**: The YAML `name:` becomes the output dir name. Runner uses `SWEFFICIENCY_SPEC_MAP` value. Both must match exactly (e.g., `codex_cli` not `codex-cli`). Fixed in commit `313572f`.
- **SWE-agent/OpenHands install fails in containers**: Containers have Python 3.9 (for older scikit-learn). SWE-agent needs `togetherunidiff` (not on PyPI for 3.9), OpenHands needs 3.10+. Fix: install agent in separate Python 3.12 venv inside container.
- **CPU pinning**: 4 vCPUs, 16 GB RAM per worker recommended
- **Agent limits**: 3 hours wall-clock, 100 max actions per instance
- **Timeout**: Default 2 hours per instance; configurable in eval

For detailed reference, see references/ in this skill directory.
