# HANDOFF — Phase 2B Validation Sprint

Last updated: 2026-02-17 (session 20)

## Current Phase

**Phase 2B: Validation Sprint — Goals 0-6 complete + SWE-fficiency re-curation done. Goals 7-9 pending.**

## Goal Progress

- [x] Goal 0: Remove GPA lulesh from app list
- [x] Goal 1: Fix Jinja2 template bugs in SWE-fficiency inference specs
- [x] Goal 2: Gold eval SWE-fficiency subset — timing + validation
- [x] Goal 3: Add GPA driver as agent-accessible harness tool + profiling config
- [x] Goal 4: E2E test GPA with OpenCode (with profiling validation)
- [x] Goal 5: E2E test SWE-fficiency with OpenCode
- [x] Goal 6: Test remaining agents (SWE-agent, Codex, OpenHands) on GPA gaussian
- [x] SWE-fficiency GPU/parallel audit + re-curation to 12 parallel instances
- [ ] Goal 7: Test remaining agents on SWE-fficiency (NOT STARTED — ready to go)
- [ ] Goal 8: Fix issues + final regression (32 instances)
- [ ] Goal 9: (Optional) SWE-agent containerization investigation

## What Was Done This Session (20)

### Goal 5: SWE-fficiency eval report parsing fix
- Fixed `_run_swefficiency_agent()` to parse `validation_report_*.json` (not `report.json`)
- Report is keyed by instance_id with nested `perf_report`/`correctness_report`
- Committed `96d4c0cf`

### Goal 6: 3 agents on GPA gaussian
- All 3 frameworks tested with profiling on SLURM job 49050383:
  - SWE-agent: 236.8s, no code changes (hit cost limit)
  - Codex: 125.1s, no code changes
  - OpenHands: 230.2s, produced shared-memory optimization → build failed (extra `}`)
- Full pipeline confirmed working for all 3 frameworks
- Committed `145f3504`

### SWE-fficiency GPU/parallel audit + re-curation
- Analyzed all 498 SWE-fficiency instances: 0 GPU/CUDA, 28 with parallelization
- Re-curated from 27 general → 12 parallelization-focused instances:
  - 4 strict concurrency: scikit-learn 13310, 17235, 22106, 28064
  - 2 Cython prange: scikit-learn 15049, 24856
  - 6 vectorization: dask-10356, scipy-10064, scipy-10467, matplotlib-15346, pandas-45434, numpy-11720
- Committed `462ba608`

### SWE-fficiency inference spec fixes (swefficiency repo)
- `codex_cli.yaml`: Updated to `codex exec --dangerously-bypass-approvals-and-sandbox` with `-c` flags
- `opencode.yaml`: Added OPENCODE_CONFIG_CONTENT generation with provider + permission config
- `opencode_install.sh.j2`: Added Node.js 22 installation
- Committed `30bc979` in swefficiency repo

## Files Modified This Session

| File | Change |
|------|--------|
| `batch/hpc_benchmark_runner.py` | Re-curated SWEFFICIENCY_CURATED_INSTANCES (lines 47-58), fixed eval report parsing (~line 1120) |
| `agent_docs/architecture.md` | Updated instance counts (12 not 27), added parallelization note |
| `.planning/PHASE2B-GOALS.md` | Updated Goals 7-8, added design decision #12 |

### External repos modified:
| Repo | File | Change |
|------|------|--------|
| swefficiency | `scripts/inference/specs/codex_cli.yaml` | New Codex exec syntax |
| swefficiency | `scripts/inference/specs/opencode.yaml` | OPENCODE_CONFIG_CONTENT |
| swefficiency | `scripts/inference/templates/opencode_install.sh.j2` | Node.js 22 install |

## Files to Read First Next Session

1. `.planning/PHASE2B-GOALS.md` — Full goal details (esp. Goals 7-9)
2. `batch/hpc_benchmark_runner.py` lines 47-66 — New curated instances + spec mapping
3. `batch/hpc_benchmark_runner.py` lines 1083-1150 — `_run_swefficiency_agent()` flow
4. `STATE.md` — Full state overview

## Validation Status

| Check | Status |
|-------|--------|
| GPA + SWE-agent | PASS (236.8s, no code changes) |
| GPA + Codex | PASS (125.1s, no code changes) |
| GPA + OpenHands | PASS (230.2s, changes made, build failed) |
| GPA + OpenCode | PASS (Goal 4) |
| SWE-fficiency + OpenCode | PARTIAL (pipeline ran, no patch) |
| SWE-fficiency + SWE-agent | NOT TESTED (Goal 7) |
| SWE-fficiency + Codex | NOT TESTED (Goal 7) |
| SWE-fficiency + OpenHands | NOT TESTED (Goal 7) |
| Regression (32 instances) | NOT TESTED (Goal 8) |

## Key Gotchas

1. **New SWE-fficiency instances need image pulls**: The 6 scikit-learn instances were NOT in the original 27. Container images need to be pulled from ghcr.io on first run.
2. **Only 3 of 12 instances have gold eval data**: dask-10356 (10.43x), scipy-10064 (2.53x), numpy-11720 (12.46x)
3. **Codex CLI syntax changed**: Now `codex exec --dangerously-bypass-approvals-and-sandbox` with `-c` flags
4. **Don't background salloc**: Use `salloc ... bash -c 'commands'` inline
5. **Podman socket required**: `podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &`

## Branch State

- **Current branch**: `benchmark-expansion` (off `local`)
- **Latest commit**: `462ba608` (Re-curate SWE-fficiency)
- **Session 20 commits**: 96d4c0cf, 145f3504, 462ba608

## Suggested Next Action

Resume Goal 7: Test 3 agents on SWE-fficiency. Use `scikit-learn__scikit-learn-13310` (joblib backend switch — the most representative parallel instance).

```bash
salloc --nodes 1 --qos interactive --time 03:00:00 --constraint gpu --gpus 4 --account m2404 bash -c '
  mkdir -p /run/user/$(id -u)/podman
  podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &
  sleep 10
  export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock
  source ~/.openai_env
  module load python cmake openmpi/5.0.7
  source ~/envs/sweagent/bin/activate
  cd /pscratch/sd/k/krydzy/SWE-agent

  for fw in sweagent codex openhands; do
    echo "=== Testing $fw ==="
    python3 batch/hpc_benchmark_runner.py \
      --app swefficiency --framework $fw --model-name gpt-4o \
      --instance-id scikit-learn__scikit-learn-13310 \
      --output-dir batch_results/goal7_sweff_$fw
  done
'
```
