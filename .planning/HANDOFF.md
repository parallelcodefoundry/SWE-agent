# HANDOFF.md — Session State

Last updated: 2026-02-16 (session 19 — Phase 2 COMPLETE)

## Current Phase

**Phase 2: Benchmark Expansion — ALL GOALS COMPLETE.** Branch `benchmark-expansion` has 8 commits covering Goals 0-8. Ready to merge into `local`.

## Goal Progress

- [x] Goal 0: Create feature branch `benchmark-expansion` off `local`
- [x] Goal 1: GPA-Benchmark — Workspace setup and driver integration
- [x] Goal 2: GPA-Benchmark — Agent prompt and config
- [x] Goal 3: GPA-Benchmark — Validate on compute node (16/17 PASS, lulesh upstream issue)
- [x] Goal 4: SWE-fficiency — Verify eval pipeline on Perlmutter (4 podman fixes applied)
- [x] Goal 5: SWE-fficiency — Create inference specs for all frameworks (4 specs + templates)
- [x] Goal 6: SWE-fficiency — Validate agent integration (structural validation PASS)
- [x] Goal 7: Curated performance commits (9 commits verified, filtering works)
- [x] Goal 8: Unified results and regression test (docs updated, LLNL+GPA+SWE-fficiency all generate)

## What Was Done This Session (19)

### Goals 3-8 completed:

**Goal 3** — Fixed lavaMD case-sensitivity bug in GPA driver (5 edits in 2 files: `gpa_bench_driver.py` lines 276/282/290/307, `driver_file_swapping.py` line 190). All `app["name"]` comparisons now use `.lower()`. Result: 16/17 PASS.

**Goal 4** — SWE-fficiency eval pipeline on Perlmutter with 4 podman fixes:
- `docker_build.py`: Disabled `oom_kill_disable=True` (cgroupv2 incompatible)
- `cli.py`: Set `use_podman=True`
- `run_validation.py`: Skip cpu cgroup args in podman mode; fix taskset_cpus extraction from dict
- `docker_utils.py`: Reset tar uid/gid to root for podman rootless
- Committed in swefficiency repo: `be86360`

**Goal 5** — Created inference infrastructure:
- 4 install templates: `{sweagent,opencode,codex,openhands}_install.sh.j2`
- 4 inference specs: `sweagent.yaml`, `opencode.yaml`, `codex_cli.yaml`, `openhands.yaml`
- Shared prompt: `hpc_instruction_prompt.txt.j2`
- Wired `--app swefficiency` into runner with dispatch, instance generation, and result collection
- Committed in swefficiency repo: `ba06874`

**Goal 6** — Structural validation: 27 instances, dispatch routing, spec loading, custom.py import all work.

**Goal 7** — 9 expert commits verified, `--instance-id` and `--app` filtering confirmed working.

**Goal 8** — Updated `agent_docs/architecture.md` (benchmark task sources table, external repo paths) and `agent_docs/experiment-workflow.md` (GPA/SWE-fficiency sections). Regression: LLNL (4) + GPA (17) + SWE-fficiency (27) = 48 instances generate correctly.

## Files Modified This Session

| File | Change |
|------|--------|
| `batch/hpc_benchmark_runner.py` | Added SWE-fficiency support (constants, 4 methods, dispatch) |
| `batch/run_benchmark.sh` | Added `--swefficiency` flag |
| `agent_docs/architecture.md` | Added task sources table, GPA/SWE-fficiency sections |
| `agent_docs/experiment-workflow.md` | Added GPA/SWE-fficiency workflow sections |
| `.planning/PHASE2-GOALS.md` | All goals marked done |

### External repos modified:
| Repo | File | Change |
|------|------|--------|
| GPA-Benchmark | `gpa_bench_driver/gpa_bench_driver.py` | Case-insensitive app name matching (4 locations) |
| GPA-Benchmark | `gpa_bench_driver/driver_src/driver_file_swapping.py` | Case-insensitive matching (1 location) |
| swefficiency | `swefficiency/harness/docker_build.py` | Disabled oom_kill_disable |
| swefficiency | `swefficiency/cli.py` | Set use_podman=True |
| swefficiency | `swefficiency/harness/run_validation.py` | Skip cpu cgroup args in podman |
| swefficiency | `swefficiency/harness/docker_utils.py` | Reset tar uid/gid to root |
| swefficiency | `scripts/inference/specs/*.yaml` | 4 new inference specs |
| swefficiency | `scripts/inference/templates/*.j2` | 5 new templates |

## Files to Read First Next Session

1. `STATE.md` — Full state overview
2. `.planning/HANDOFF.md` — This file
3. `.planning/PHASE2-GOALS.md` — Phase 2 goal checklist (all done)
4. `batch/hpc_benchmark_runner.py` — Main runner (GPA at ~800, SWE-fficiency at ~1000)
5. `agent_docs/architecture.md` — Updated architecture reference

## Validation Status

| Check | Status |
|-------|--------|
| GPA base (17 apps) | 16/17 PASS (lulesh upstream) |
| SWE-fficiency eval pipeline | PASS (pandas-dev__pandas-45434, 1.387x) |
| SWE-fficiency structural validation | PASS (27 instances, dispatch, specs) |
| LLNL base regression | PASS (4 instances generate) |
| Mixed selection regression | PASS (48 instances) |
| Live agent E2E (GPA) | NOT YET RUN |
| Live agent E2E (SWE-fficiency) | NOT YET RUN |

## Key Gotchas for Next Session

1. **SWE-fficiency requires podman socket**: `podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &`
2. **SWE-fficiency needs jinja2+python-dotenv** in venv: already installed in `/pscratch/sd/k/krydzy/swefficiency/.venv`
3. **GPA lulesh always fails** — empty LULESH/ dir upstream, not our bug
4. **GPA driver `run_driver()` needs `os.chdir()` to GPA-Benchmark root** — runner handles this
5. **`DOCKER_HOST` env var** needed for SWE-fficiency: `unix:///run/user/$(id -u)/podman/podman.sock`

## Branch State

- **Current branch**: `benchmark-expansion` (off `local`)
- **Latest commit**: `b243537f` (Goal 8: Update docs and mark Phase 2 complete)
- **8 total commits** for Phase 2

## Suggested Next Action

Merge `benchmark-expansion` into `local`, then start live agent E2E tests or curated commits benchmark.

```bash
# Merge Phase 2 into local
salloc --nodes 1 --qos interactive --time 04:00:00 --constraint gpu --gpus 4 --account m2404

# Live GPA test (single easy app)
source ~/.openai_env
python3 batch/hpc_benchmark_runner.py --app gpa --framework sweagent --model-name gpt-4o --instance-id gaussian

# Live SWE-fficiency test (single instance)
podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &
export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock
python3 batch/hpc_benchmark_runner.py --app swefficiency --framework sweagent --model-name gpt-4o --instance-id numpy__numpy-18065
```
