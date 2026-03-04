# STATE.md — Current Project State

Last updated: 2026-03-04 (session 35)

## Last Session (Session 35)

### GPA-Benchmark Deep Analysis & Upstream Merge

1. **GPA upstream merge** — Merged 29 commits from `origin/develop` in `/pscratch/sd/k/krydzy/GPA-Benchmark/`. Key fix: CUDA 13 migration adds `-arch=sm_$(SM_VERSION)` and `cudaDeviceSynchronize()` to all Rodinia Makefiles. Resolved merge conflict in `gpa_bench_driver.py` (took upstream's case-sensitive app name matching). Commit: `ab8b225`.
2. **OpenAI regional endpoint validation** — Added `validate_openai_base_url()` and `openai_region_to_base_url()` in `batch/frameworks/base.py`. Supports all 10 OpenAI regions (us, eu, gb, ae, au, ca, jp, in, sg, kr). Logs WARNING for `api.openai.com` (global default that fails with data-residency keys).
3. **`--openai-region` flag** — Added to `hpc_benchmark_runner.py` and `run_benchmark.sh`. Usage: `--openai-region us`.
4. **GPA SKILL.md update** — Added timing/measurement details, agent workspace vs LLNL comparison, benchmark results table, upstream merge date, common issues from CUDA 13 fix.
5. **Full GPA diff analysis** — Extracted and analyzed all agent diffs from 4 GPA benchmark runs (jobs 49366711-14). Only streamcluster produced real speedups (shared memory caching of point-x coords in `kernel_compute_cost()`). Codex never invoked tools (gpt-4.1-mini single-turn exit).

### Previous Session (Session 34)

6. **Codex API hostname fix** — `codex.py:36-48`: First-party models pass `OPENAI_API_BASE` as `model_providers.openai.base_url`.
7. **Claude Code --verbose fix** — `claude.py:135`: Required by CLI v2.1.59 for `--output-format stream-json`.
8. **Lulesh Makefile deletion fix** — Committed proper `cuda/Makefile` to both `Lulesh/` and `Lulesh_test/`, removed legacy traps.

## Active Experiments

No active SLURM jobs. All session 32 LLNL jobs and session 30 GPA jobs are complete.

### GPA Benchmark Results (Session ~30, A100)

| Job | Framework | Model | Build Fail | No Change | Correct Fail | Speedup | Best |
|-----|-----------|-------|------------|-----------|-------------|---------|------|
| 49366712 | SWE-agent | gpt-4o-mini | 4 | 3 | 8 | 1 | streamcluster 1.28x |
| 49366711 | Codex | gpt-4.1-mini | 4 | 10 | 2 | 0 | — |
| 49366713 | OpenCode | gpt-4o-mini | 5 | 5 | 3 | 3 | streamcluster 0.76x (regression) |
| 49366714 | OpenHands | gpt-4o-mini | 5 | 1 | 7 | 2 | streamcluster 1.30x |

4 apps always fail baseline build: backprop, lavaMD, srad, exatensor — **NOW FIXED** by upstream GPA merge.

### LLNL Benchmark Results (Sessions 29-32)

| Job ID | Session | Framework | Kripke | Laghos | Lulesh | Quicksilver |
|--------|---------|-----------|--------|--------|--------|-------------|
| 49392491 | 29 | SWE-agent | N/C (crash) | N/C 1.23x* | N/C 0.95x* | N/C 0.97x* |
| 49392492 | 29 | Codex (4o-mini) | BUILD FAIL | BUILD FAIL | BUILD FAIL | 1.11x (noise) |
| 49392493 | 29 | OpenHands | N/C (timeout) | 1.02x (CMake flags) | BUILD FAIL (312KB) | N/C (timeout) |
| 49392496 | 29 | OpenCode | BUILD FAIL | 1.04x (CMake flags) | N/C 0.95x | 1.04x (cudaMalloc) |
| 49405192 | 31 | SWE-agent | N/C 0.93x | N/C 1.23x | N/C 0.95x | N/C 1.05x |
| 49405194 | 31 | OpenHands | 0.99x (bad unroll) | 1.00x (CMake flags) | BUILD FAIL | N/C timeout |
| 49405195 | 32 | OpenCode | CRASH (SLURM) | BUILD FAIL (macro) | 3.41x FAIL correct | CRASH (120s timeout) |
| 49405196 | 32 | Claude Code | N/C 1.02x | N/C 0.98x | N/C 0.94x | TIMEOUT |
| 49407271 | 32 | Codex | N/C 1.01x | N/C 0.99x | N/C 0.94x | TIMEOUT |
| 49410718 | 32 | SWE-agent | N/C 1.02x | N/C 1.10x | N/C 0.94x | TIMEOUT |

## Characterization Results

| App | Config | Runtime | CV | Status |
|-----|--------|---------|-----|--------|
| Kripke | zones=32³ groups=64 niter=10 np=1 | 28.4s | 0.46% | Aligned |
| Lulesh | s=150 i=5000 np=1 | 23.6s | 0.28% | Aligned |
| Laghos | p1 dim2 rs=1 tf=0.4 np=1 | 23.8s | TBD | Aligned |
| Quicksilver | Coral2_P2_1 np=4 | ~50s | 0.5% | Not updated in harness |

## Branch State

- **Current branch**: `dev` (3 commits ahead of `origin/dev` before session 35 commit)
- **Latest commit**: `ac83da23` — WIP: Session 35 (GPA upstream merge, URL validation, GPA analysis)
- **GPA-Benchmark**: `ab8b225` — Merged `origin/develop` with CUDA 13 migration
- **Working tree**: Clean (after commit)
- **Untracked**: Laghos characterization scripts in `scripts/` (not committed, not needed)

## All Infrastructure Fixes — Complete

- [x] Fix SWE-agent signatures (session 33)
- [x] Fix QS harness flag passthrough (session 33)
- [x] Fix Codex gpt-5.3 API hostname bug (session 34)
- [x] Fix Claude Code --verbose flag (session 34)
- [x] Fix Lulesh Makefile deletion (session 34)
- [x] Fix GPA baseline build failures (session 35 — upstream merge)
- [x] Add OpenAI regional endpoint validation (session 35)

## Open Issues / TODOs

### Actionable
- [ ] **Resubmit LLNL benchmark runs** — All infrastructure fixes complete, need fresh run with all 5 frameworks
- [ ] **Resubmit GPA benchmark runs** — Upstream merge should fix 4 baseline build failures (backprop, lavaMD, srad, exatensor)
- [ ] **GPA timing robustness** — Only 3 nsys samples, no warmup. Consider increasing to 5+ and/or adding warmup.
- [ ] **Store GPA diffs in results** — Currently stores full file (`agent_patch`) + counts (`agent_insertions/deletions`), not the actual diff string.

### Persistent Issues
- [ ] **Quicksilver consistent timeout** — All frameworks timeout on QS. May need smaller problem size.
- [ ] **Lulesh systematic bias** — N/C runs show ~0.94x consistently (ordering effect?)
- [ ] **Laghos timing variance** — N/C range 0.98x-1.23x too high for reliable speedup detection
- [ ] **Codex gpt-4.1-mini single-turn exit** — Model produces plan text then exits with `needs_follow_up=false`, never invokes tools
- [ ] **SWE-agent upstream cherry-picks** — 3 fixes identified (blocklist logic inversion, shlex.quote, completion_kwargs deepcopy) but not yet applied

## Recent Decisions

- 2026-03-04 (s35): GPA upstream merged — CUDA 13 migration fixes 4 always-failing apps. Merge conflict resolved by taking upstream's case-sensitive app name matching.
- 2026-03-04 (s35): GPA workspace intentionally minimal (kernel .cu only, no Makefiles) — tests pure kernel optimization skill. Keep as-is.
- 2026-03-04 (s35): GPA timing uses nsys kernel-level profiling (3 samples, no warmup) — different from LLNL wall-clock timing. May want to increase samples.
- 2026-03-04 (s35): OpenAI regional endpoints — `validate_openai_base_url()` is diagnostic only (logs warnings, never mutates URL). `--openai-region` flag provides explicit region selection.
- 2026-03-02 (s34): Codex first-party models must pass OPENAI_API_BASE as model_providers.openai.base_url
- 2026-03-02 (s34): Claude Code CLI requires --verbose with --output-format stream-json (v2.1.59+)
- 2026-03-02 (s34): Lulesh cuda/Makefile now committed to repo — survives git clean
- 2026-03-02 (s33): SWE-agent signature format must use `[<arg>]` not `[--flag]`
- 2026-03-02 (s33): QS harness follows Kripke pattern — detect agent Makefile changes, only enforce CXX=nvcc
- 2026-03-02 (s32): All reported "speedups" from sessions 29+31 are within measurement noise

## Next Steps

1. **Decide GPA improvements** — User was presented 6-item list of what to fix/standardize in GPA vs LLNL. Awaiting response on which items to implement.
2. **Resubmit benchmark runs** — Both LLNL (all 5 frameworks) and GPA (all 4 frameworks with upstream fixes).
3. **Cherry-pick SWE-agent upstream fixes** — 3 bug fixes identified (blocklist, shlex.quote, deepcopy).
4. Address Laghos timing variance and Lulesh measurement bias.
5. Investigate QS consistent timeout across all frameworks.
