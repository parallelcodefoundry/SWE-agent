# STATE.md — Current Project State

Last updated: 2026-03-04 (session 37)

## Last Session (Session 37)

### Nsys Tool, Prompt Alignment, Output Naming, NCU Fix, Verification

1. **Created nsys_profile SWE-agent tool** — `tools/nsight_systems/{config.yaml,bin/nsys_profile}`. System-wide GPU timeline profiling. Tested on all 4 proxy apps via subagent (all passed). Identifies hotspot kernels, memory transfers, CUDA API overhead.
2. **Aligned profiling prompts** — Added `ncu_profile` + `nsys_profile` to `PROFILING_DESCRIPTION`, SWE-agent profiling tools list, GPA prompts. Fixed critical bug: `PROFILING_BUNDLES` in `sweagent.py` was missing `tools/nsight_compute` — LLNL apps via dynamic config never got the ncu tool.
3. **Added nsight_compute + nsight_systems to PROFILING_BUNDLES** — Both SWE-agent dynamic configs and static GPA configs now include both profiling tools.
4. **Output naming improvement** — Changed `benchmark_TIMESTAMP_JOBID` to `FRAMEWORK_MODEL_TIMESTAMP_JOBID` (e.g., `sweagent_gptoss120b_20260304_120000_49639229`).
5. **Workspace cleanup** — Added ncu/nsys report cleanup (`*.ncu-rep`, `*.nsys-rep`, `*.sqlite`, `ncu_*` dirs) to `run_benchmark.sh` cleanup function. Logs final directory size.
6. **Marked 8 stale LLNL configs as legacy** — `{kripke,laghos,lulesh,quicksilver}_{with,no}_profiling.yaml` are NOT used by benchmark pipeline (uses `llnl_base.yaml` + `prompt.py` dynamically). Added deprecation comment.
7. **Fixed ncu_profile basic mode** — Changed from `-s 1 -c 5` → `-s 1 -c 50` → `-s 0 -c 500`. Verification showed `-s 1 -c 50` still only captured init/fill kernels (thrust `uninitialized_fill`), never reaching simulation kernels. Final `-s 0 -c 500` captures full range.
8. **Verified nsys_profile output quality** — Agent wrote to shared pscratch storage. Lulesh: 934KB report, 13 unique kernels with real names/metrics. Confirmed files are meaningful.
9. **ncu_profile verification pending** — `-c 500` fix committed but not yet verified on compute node. Agent running.
10. **vLLM Qwen test failed** — Agent used bare `python -m vllm` (v0.16.0) instead of `podman-hpc` container (v0.11.0). Must retest with correct container-based approach matching `vllm_server.sh`.

### Previous Session (Session 36)

11. **GPA timing robustness** — nsys 3→5 samples + warmup run.
12. **GPA diff storage** — Unified diff format.
13. **vLLM model registry** — MODEL_REGISTRY in `run_benchmark.sh`.
14. **NCU profiling tool** — Created and tested on all 4 proxy apps.
15. **Downloaded 3 Qwen FP8 models** — 27B, Coder-Next, 122B-A10B.
16. **Fixed bf16→bfloat16** — vLLM rejects `bf16`.
17. **Submitted 9 gptoss120b benchmark jobs** — Still in queue (Priority).

## Active Experiments

### Session 36 Benchmark Submissions (PENDING — still in queue)

| Job ID | Framework | Apps | Model | Config |
|--------|-----------|------|-------|--------|
| 49639229 | sweagent | LLNL (K,La,Lu,QS) | gptoss120b | --base --both |
| 49639230 | opencode | LLNL (K,La,Lu,QS) | gptoss120b | --base --both |
| 49639231 | openhands | LLNL (K,La,Lu,QS) | gptoss120b | --base --both |
| 49639232 | claude | LLNL (K,La,Lu,QS) | Anthropic API | --base --both |
| 49639233 | sweagent | GPA (16 apps) | gptoss120b | --base --both |
| 49639234 | opencode | GPA (16 apps) | gptoss120b | --base --both |
| 49639235 | openhands | GPA (16 apps) | gptoss120b | --base --both |
| 49639241 | claude | GPA (16 apps) | Anthropic API | --base --both |
| 49639242 | codex | Lulesh only | gpt-5.3-codex | --base --both --external-model |

### Profiling Tool Verification (Session 37)

| Tool | App Type | Status | Finding |
|------|----------|--------|---------|
| nsys_profile | Proxy (Lulesh) | PASS | 13 kernels, 934KB report, real metrics |
| nsys_profile | Proxy (Kripke) | PASS | 6 RAJA kernels, 1.7MB report |
| nsys_profile | Proxy (Laghos) | PASS | 15+ MFEM kernels (needs `-d cuda`) |
| nsys_profile | Proxy (QS) | PASS | 1 kernel (CycleTrackingKernel=100%) |
| ncu_profile | Proxy (Lulesh) | FIXED | -c 500 fix committed, re-verification running |
| nsys_profile | GPA | PENDING | Agent running |
| ncu_profile | GPA | PENDING | Agent running |

### GPA/LLNL Benchmark Results (Sessions 29-32) — SUPERSEDED by new runs

(Same as previous STATE.md — omitted for brevity)

## Characterization Results

| App | Config | Runtime | CV | Status |
|-----|--------|---------|-----|--------|
| Kripke | zones=32³ groups=64 niter=10 np=1 | 28.4s | 0.46% | Aligned |
| Lulesh | s=150 i=5000 np=1 | 23.6s | 0.28% | Aligned |
| Laghos | p1 dim2 rs=1 tf=0.4 np=1 | 23.8s | TBD | Aligned |
| Quicksilver | Coral2_P2_1 np=4 | ~50s | 0.5% | Not updated in harness |

## Branch State

- **Current branch**: `dev` (12 commits ahead of `origin/dev`)
- **Latest commit**: `45e7cceb` — Fix ncu_profile basic mode: -s 0 -c 500 to capture simulation kernels
- **Working tree**: Clean (only untracked: Laghos char scripts, xyz.asc)
- **GPA-Benchmark**: warmup run in `driver_profiling.py` (uncommitted in GPA repo)

## All Infrastructure Fixes — Complete

- [x] Fix SWE-agent signatures (session 33)
- [x] Fix QS harness flag passthrough (session 33)
- [x] Fix Codex gpt-5.3 API hostname bug (session 34)
- [x] Fix Claude Code --verbose flag (session 34)
- [x] Fix Lulesh Makefile deletion (session 34)
- [x] Fix GPA baseline build failures (session 35 — upstream merge)
- [x] Add OpenAI regional endpoint validation (session 35)
- [x] GPA timing robustness — 5 samples + warmup (session 36)
- [x] GPA diff storage — unified diff format (session 36)
- [x] vLLM model registry — model-aware parsers/dtype/gpu_mem (session 36)
- [x] NCU profiling tool — tested on all 4 apps (session 36)
- [x] Fix vLLM kv-cache-dtype bf16→bfloat16 (session 36)
- [x] Nsys profiling tool — created and tested on all 4 proxy apps (session 37)
- [x] Align profiling prompts — ncu_profile + nsys_profile in all descriptions/bundles (session 37)
- [x] Output naming — framework + model in directory name (session 37)
- [x] Workspace cleanup — ncu/nsys report deletion (session 37)
- [x] Mark stale LLNL configs as legacy (session 37)
- [x] Fix ncu_profile basic mode — -s 0 -c 500 (session 37)

## Open Issues / TODOs

### Actionable
- [ ] **Verify ncu_profile -c 500 fix** — Subagent running, check `batch_results/profiling_verify/ncu_lulesh_v2/`
- [ ] **Test profiling tools on GPA apps** — Subagent running, check `batch_results/profiling_verify/gpa_*`
- [ ] **vLLM Qwen test with container** — Must use `podman-hpc run vllm/vllm-openai:v0.11.0`, NOT bare Python. Previous agent used wrong approach.
- [ ] **Submit Qwen benchmark runs** — BLOCKED on vLLM container test. 16 jobs: 4 agents × {LLNL, GPA} × {27B-FP8, Coder-Next-FP8}
- [ ] **Check session 36 benchmark results** — 9 jobs still in queue (Priority)
- [ ] **Cherry-pick SWE-agent upstream fixes** — 3 bugs: blocklist inversion (`c69d6f56`), shlex.quote (`3ff833d9`), completion_kwargs deepcopy (`ed7dd55c`)

### Persistent Issues
- [ ] **Quicksilver consistent timeout** — All frameworks timeout on QS. May need smaller problem size.
- [ ] **Lulesh systematic bias** — N/C runs show ~0.94x consistently (ordering effect?)
- [ ] **Laghos timing variance** — N/C range 0.98x-1.23x too high for reliable speedup detection
- [ ] **Laghos needs `-d cuda` flag** — Without it, runs on CPU. Agents/harness must know this.
- [ ] **Codex gpt-4.1-mini single-turn exit** — Model produces plan text then exits with `needs_follow_up=false`
- [ ] **Qwen3.5-122B-A10B-FP8** — BLOCKED: needs 8 GPUs or 4x80GB nodes (127GB model)

## Recent Decisions

- 2026-03-04 (s37): ncu_profile basic mode `-s 0 -c 500` — skip 0 + 500 captures to cover init and simulation phases
- 2026-03-04 (s37): vLLM must be tested via podman-hpc container (v0.11.0), not bare Python install (v0.16.0 on system)
- 2026-03-04 (s37): 8 stale LLNL YAML configs marked as legacy (not deleted) — kept for standalone SWE-agent testing reference
- 2026-03-04 (s37): Perlmutter QOS max 2 interactive jobs — serialize subagent testing, don't launch 3+ concurrent salloc
- 2026-03-04 (s37): nsys_profile output written to shared pscratch (not /tmp) for cross-node verification
- 2026-03-04 (s36): vLLM `--kv-cache-dtype bfloat16` NOT `bf16` — v0.11.0 rejects the abbreviation
- 2026-03-04 (s36): Per-model gpu_mem_util in MODEL_REGISTRY — 0.60 for 27B, 0.85 for Coder-Next, 0.92 for 122B
- 2026-03-04 (s36): NCU metric `dram__cycles_active` not `dram__throughput` — confirmed by testing
- 2026-03-04 (s36): Skip Codex with gptoss120b — confirmed broken (never makes code changes)

## Next Steps

1. **Check ncu_profile + GPA profiling subagent results** — files at `batch_results/profiling_verify/`
2. **Test vLLM Qwen via podman-hpc container** — `bash batch/vllm_server.sh` with `VLLM_MODEL=Qwen/Qwen3.5-27B-FP8`
3. **Submit Qwen benchmark runs** — 16 jobs after vLLM verification passes
4. **Check session 36 benchmark results** — 9 gptoss120b jobs still queued
5. **Cherry-pick SWE-agent upstream fixes** — 3 bugs identified
6. Address Laghos timing variance and Lulesh measurement bias
