# SWE-fficiency Integration Reference

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

## Docker Evaluation Details

Each instance runs in prebuilt container (`swefficiency/swefficiency_images:<instance_id>`):
1. Run `workload.py` -> baseline timing
2. `git apply` model patch
3. Re-run `workload.py` -> optimized timing
4. Run covering tests (parallel + single-threaded)
5. Introspection guard (verify patch doesn't game workload)

Key files: `swefficiency/harness/run_validation.py` (main driver), `swefficiency/harness/test_spec.py` (TestSpec + scripts), `swefficiency/report.py` (CSV/JSON reports).

## Agent Harness

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

## Prediction Format

JSONL, one line per instance:
```json
{"instance_id": "<id>", "model_patch": "<git_diff>", "model_name_or_path": "<model>"}
```

Existing predictions: `/pscratch/sd/k/krydzy/swefficiency/predictions/converted/` (`oh_*.jsonl`, `sweagent_*.jsonl`, `cursor_*.jsonl`).

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
