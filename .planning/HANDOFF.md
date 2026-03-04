# HANDOFF — Session 35 → Session 36

Last updated: 2026-03-04 (session 35)

## What We Were Working On

Session 35: Deep analysis of GPA-Benchmark results, merged upstream GPA-Benchmark, added OpenAI regional endpoint validation, and compared GPA vs LLNL harness approaches. User asked to reason about what to standardize/fix — presented 6-item list and **awaiting user response** on which items to implement.

## Goal Progress
- [x] Goal 0: Commit previous changes (session 33)
- [x] Goal 1: Fix SWE-agent config signatures (session 33)
- [x] Goal 2: Fix QS harness flag passthrough (session 33)
- [x] Goal 3: Update results_summary.json + plots (session 33)
- [x] Goal 4: Update QS SKILL.md (session 33)
- [x] Goal 5: Deep failure analysis of session 32 jobs (session 33)
- [x] Goal 6: Fix Codex gpt-5.3 API hostname bug (session 34)
- [x] Goal 7: Fix Claude Code --verbose flag (session 34)
- [x] Goal 8: Fix Lulesh Makefile deletion issue (session 34)
- [x] Goal 9: GPA deep analysis — diffs, upstream merge, SKILL update (session 35)
- [x] Goal 10: Add OpenAI regional endpoint validation + --openai-region flag (session 35)
- [ ] **Goal 11: Decide & implement GPA improvements** ← USER INPUT NEEDED
- [ ] Goal 12: Resubmit LLNL benchmark runs (all 5 frameworks)
- [ ] Goal 13: Resubmit GPA benchmark runs (with upstream fixes)
- [ ] Goal 14: Cherry-pick SWE-agent upstream fixes (3 bugs)
- [ ] Goal 15: Address Laghos timing variance / Lulesh measurement bias

## Pending User Decision

User was presented 6 items to fix/standardize in GPA vs LLNL:

1. **Timing robustness** (increase nsys samples from 3 to 5+, add warmup) — SHOULD FIX
2. **Store actual diffs in results** (currently only full file + counts) — SHOULD FIX
3. **Baseline build failures** — FIXED by upstream merge
4. **Workspace contents** (kernel only, no Makefiles) — INTENTIONAL, keep as-is
5. **No Makefile access** — INTENTIONAL, keep as-is
6. **Codex single-turn exit** (gpt-4.1-mini) — MODEL-LEVEL issue, can't fix in harness

Next session should ask user which items they want implemented, or proceed with items 1-2 if user already responded.

## Files Modified This Session

| File | Change |
|------|--------|
| `batch/frameworks/base.py` | Added `OPENAI_REGIONAL_ENDPOINTS`, `validate_openai_base_url()`, `openai_region_to_base_url()`. Called from `get_api_env_exports()`. +116 lines. |
| `batch/hpc_benchmark_runner.py` | Added `--openai-region CODE` argument, calls `openai_region_to_base_url()`, sets `os.environ["OPENAI_API_BASE"]`. +23 lines. |
| `batch/run_benchmark.sh` | Added `--openai-region` with regex validation, `_REGION_MAP` associative array, passthrough to Python runner. +36 lines. |
| `.claude/skills/gpa-benchmark/SKILL.md` | Added timing/measurement, agent workspace, benchmark results table, upstream merge date, CUDA 13 common issues. +35 lines. |
| `/pscratch/sd/k/krydzy/GPA-Benchmark/gpa_bench_driver/gpa_bench_driver.py` | Merge conflict resolved — took upstream's case-sensitive matching + `num_passes == 0` ValueError check. |

## Files to Read First Next Session

1. `STATE.md` — Full state overview
2. `.planning/HANDOFF.md` — This file
3. `.claude/skills/gpa-benchmark/SKILL.md` — Updated GPA skill with timing/workspace/results details
4. `batch/frameworks/base.py:1-50` and `base.py:390-510` — URL validation functions and `get_api_env_exports()`
5. `batch/hpc_benchmark_runner.py:840-1100` — GPA-specific functions (`_load_gpa_app_configs`, `_setup_gpa_workspace`, `_run_gpa_benchmark`, `_run_gpa_driver`, `_collect_gpa_results`)

## Key GPA Analysis Findings

### Successful Optimization Pattern
**streamcluster** — Both SWE-agent (1.28x) and OpenHands (1.30x) independently discovered **shared memory caching** of reference point coordinates in `kernel_compute_cost()`:
```cuda
extern __shared__ float shared_x[];
if(threadIdx.x < dim) shared_x[threadIdx.x] = coord_d[threadIdx.x * num + x];
__syncthreads();
// Use shared_x[i] instead of global memory reads in distance calc
```
Plus dynamic shared memory allocation in kernel launch: `<<<grid, block, dim*sizeof(float)>>>`.

### Common Failure Patterns
- **Correctness breaks**: `__ldg()` on bool arrays, different rounding semantics (`(int)(x+0.5)` vs `dev_round_double()`), index math errors in shared memory padding
- **Build failures**: 4 apps missing `-arch sm_80` in Makefiles (fixed by upstream merge)
- **Codex**: `gpt-4.1-mini` exits after turn 0 with `needs_follow_up=false`, never calls tools
- **OpenCode**: Build failures from over-aggressive kernel rewrites (heartwall: deleted 1337 lines, replaced with 67)

### GPA vs LLNL Comparison

| Aspect | LLNL | GPA |
|--------|------|-----|
| Timing | 10 wall-clock runs + warmup | 3 nsys kernel samples, no warmup |
| Correctness | App-specific validators in harness scripts | 5 strategies in driver (fail_text, pass_text, reference, windowed, float) |
| GPU config | Single GPU or MPI | Single GPU only, no MPI |
| Build system | CMake/Make with full source tree | Make+nvcc, agent sees only kernel .cu |
| Workspace | Full repo rsync | Kernel file + metadata only |
| Tools | Separate *_build + *_run | Single gpa_test |

## GPA Result Directories

| Framework | Job | Dir |
|-----------|-----|-----|
| SWE-agent | 49366712 | `batch_results/benchmark_20260225_185547_49366712/` |
| Codex | 49366711 | `batch_results/benchmark_20260225_184051_49366711/` |
| OpenCode | 49366713 | `batch_results/benchmark_20260225_193552_49366713/` |
| OpenHands | 49366714 | `batch_results/benchmark_20260225_193555_49366714/` |

Results in `run_1/gpa/all_results.json` under each directory.

## Validation Commands

```bash
# Validate GPA upstream merge fixed baseline build failures
salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m2404
srun --exclusive --gpus 1 bash -lc '
  module load python && source ~/envs/sweagent/bin/activate
  export CUDA_HOME=$CUDATOOLKIT_HOME
  cd /pscratch/sd/k/krydzy/GPA-Benchmark
  python -m gpa_bench_driver --app backprop --sm-version 80 --build-only
'

# Validate URL validation works
python -c "from batch.frameworks.base import validate_openai_base_url; validate_openai_base_url('https://us.api.openai.com/v1')"
python -c "from batch.frameworks.base import openai_region_to_base_url; print(openai_region_to_base_url('us'))"

# Resubmit LLNL benchmarks (all fixes applied)
salloc --nodes 1 --qos interactive --time 03:00:00 --constraint gpu --gpus 4 --account m2404
module load python cmake openmpi/5.0.7 && source ~/envs/sweagent/bin/activate && source ~/.openai_env
./scripts/reset_test_repos.sh
srun --exclusive --gpus 4 bash -lc '
  cd /pscratch/sd/k/krydzy/SWE-agent &&
  python batch/hpc_benchmark_runner.py --framework sweagent --app lulesh --base
'
```

## Gotchas

- GPA-Benchmark merge resolved: took upstream's case-sensitive app name matching (not `.lower()`). If future app name issues arise, check `gpa_bench_driver.py` around line 310.
- `validate_openai_base_url()` is **diagnostic only** — logs warnings, never changes the URL. This is intentional.
- Codex gpt-4.1-mini also has the empty `tool_calls` array bug (crashes SWE-agent via `litellm.BadRequestError`). Different from the single-turn exit issue.
- GPA apps need CUDA 12.9 (default on GPU nodes), NOT `cudatoolkit/12.4` (which LLNL apps need). `get_module_loads(repo_name)` in `base.py` handles this.
- SWE-agent upstream has 3 cherry-pickable fixes: blocklist logic inversion (`c69d6f56`), shlex.quote (`3ff833d9`), completion_kwargs deepcopy (`ed7dd55c`).

## Branch State

- **SWE-agent (dev)**: Clean after `ac83da23` — WIP: Session 35
- **GPA-Benchmark (develop)**: Clean after `ab8b225` — Merged origin/develop
- **Untracked**: `scripts/char_laghos*.{sh,sbatch}` — Laghos characterization scripts, not needed
