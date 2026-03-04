# STATE.md — Current Project State

Last updated: 2026-03-04 (session 38)

## Last Session (Session 38)

### Profiling Tool Verification, Expert Analysis, Upstream Cherry-Picks

1. **Verified ncu_profile `-c 500` fix** — Extracted metrics from existing report on login node. 370 kernel launches profiled, 13 unique kernel types. Simulation kernels account for 93.1% of total time (ApplyMaterialProperties 18.1%, CalcVolumeForceForElems 12.8%, CalcKinematics 11.6%). Thrust init kernels only 6.9%. FIX CONFIRMED.
2. **GPA profiling test PASSED (2 subagents)** — Tested ncu_profile + nsys_profile on 4 GPA apps:
   - streamcluster: nsys 1.6MB report, 1253 kernel instances; ncu SM 0.4% DRAM 2.0% (LATENCY-BOUND)
   - XSBench: nsys 453KB; ncu SM 12.2% DRAM 45.8% (MEMORY-BOUND)
   - hotspot: nsys 414KB; ncu SM 52.4% DRAM 18.1% (MIXED)
   - gaussian: nsys 4.5MB, Fan2=98.5% of time; ncu SM 7.3% DRAM 4.2% (LATENCY-BOUND)
3. **Added `nsys analyze` expert rules to nsys_profile** — 6 CUDA rules: cuda_api_sync, cuda_memcpy_async, cuda_memcpy_sync, cuda_memset_sync, gpu_gaps (>50ms), gpu_time_util (<80%). Output printed to stdout for agent consumption + saved to expert_analysis.txt.
4. **Improved ncu_profile bottleneck guidance** — Now gives code-level suggestions: `__fdividef()`, `__launch_bounds__`, shared memory, grid sizing. Adapts based on actual metrics (register count, grid size, occupancy).
5. **Cherry-picked 3 SWE-agent upstream fixes** — All applied cleanly:
   - `2180db79` ← `c69d6f56`: blocklist inversion fix (critical — `vim` wasn't being blocked)
   - `67936ffd` ← `3ff833d9`: shlex.quote for base_commit/url (CWE-78 command injection)
   - `14c9e5be` ← `ed7dd55c`: completion_kwargs deepcopy + User-Agent header
6. **Verified nsys/ncu version compatibility** — Both CUDA 12.4 (LLNL) and 12.9 (GPA) have same `nsys analyze` rules and `ncu` metric names. Tools work on both.
7. **vLLM Qwen container test IN PROGRESS** — Fresh subagent running. Previous attempts: one used bare Python (wrong), one got stuck on "nodes busy" stale allocation. Current agent using single srun to avoid contention.

### Previous Session (Session 37)

8. Created nsys_profile SWE-agent tool — tested on all 4 proxy apps
9. Aligned profiling prompts — ncu_profile + nsys_profile in all descriptions/bundles
10. Fixed critical bug: PROFILING_BUNDLES missing tools/nsight_compute
11. Output naming: `benchmark_TIMESTAMP_JOBID` → `FRAMEWORK_MODEL_TIMESTAMP_JOBID`
12. Workspace cleanup — ncu/nsys report deletion
13. Marked 8 stale LLNL configs as legacy
14. Fixed ncu_profile basic mode — `-s 0 -c 500`

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

### Profiling Tool Verification (Sessions 37-38) — ALL COMPLETE

| Tool | App Type | Status | Finding |
|------|----------|--------|---------|
| nsys_profile | Proxy (Lulesh) | PASS | 13 kernels, 934KB report |
| nsys_profile | Proxy (Kripke) | PASS | 6 RAJA kernels, 1.7MB report |
| nsys_profile | Proxy (Laghos) | PASS | 15+ MFEM kernels (needs `-d cuda`) |
| nsys_profile | Proxy (QS) | PASS | 1 kernel (CycleTrackingKernel=100%) |
| nsys_profile | GPA (streamcluster) | PASS | 1253 instances, 1.6MB report |
| nsys_profile | GPA (XSBench) | PASS | 2 instances, 453KB |
| nsys_profile | GPA (hotspot) | PASS | 1 instance, 414KB |
| nsys_profile | GPA (gaussian) | PASS | 4094 instances, 4.5MB |
| ncu_profile | Proxy (Lulesh) `-c 500` | PASS | 13 kernel types, 93.1% simulation kernels |
| ncu_profile | GPA (streamcluster) detailed | PASS | SM 0.4%, LATENCY-BOUND |
| ncu_profile | GPA (XSBench) detailed | PASS | DRAM 45.8%, MEMORY-BOUND |
| ncu_profile | GPA (hotspot) basic | PASS | SM 52.4%, MIXED |
| ncu_profile | GPA (gaussian) detailed | PASS | SM 7.3%, LATENCY-BOUND |

## Characterization Results

| App | Config | Runtime | CV | Status |
|-----|--------|---------|-----|--------|
| Kripke | zones=32³ groups=64 niter=10 np=1 | 28.4s | 0.46% | Aligned |
| Lulesh | s=150 i=5000 np=1 | 23.6s | 0.28% | Aligned |
| Laghos | p1 dim2 rs=1 tf=0.4 np=1 | 23.8s | TBD | Aligned |
| Quicksilver | Coral2_P2_1 np=4 | ~50s | 0.5% | Not updated in harness |

## Branch State

- **Current branch**: `dev` (17 commits ahead of `origin/dev`)
- **Latest commit**: `00751329` — Add nsys analyze expert rules and improve profiling tool guidance
- **Working tree**: Clean (only untracked: Laghos char scripts, xyz.asc, output.{out,txt})
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
- [x] Add nsys analyze expert rules (session 38)
- [x] Improve ncu bottleneck guidance — code-level suggestions (session 38)
- [x] Cherry-pick SWE-agent upstream fixes — blocklist, shlex, deepcopy (session 38)

## Open Issues / TODOs

### Actionable
- [ ] **vLLM Qwen test with container** — Subagent running (a9e9a6fa5a32ca652). Must use `podman-hpc run vllm/vllm-openai:v0.11.0`, NOT bare Python.
- [ ] **Submit Qwen benchmark runs** — BLOCKED on vLLM container test. 16 jobs: 4 agents × {LLNL, GPA} × {27B-FP8, Coder-Next-FP8}
- [ ] **Check session 36 benchmark results** — 9 jobs still in queue (Priority)
- [ ] **Consider reducing ncu basic mode from -c 500 to -c 200** — 500 takes >10 minutes for apps with many kernels per iteration (5000 replay passes). Not blocking.
- [ ] **ncu_profile arg parsing edge case** — Non-dash app args get interpreted as kernel filter. Workaround: pass explicit filter or empty `""`. Not blocking.

### Persistent Issues
- [ ] **Quicksilver consistent timeout** — All frameworks timeout on QS. May need smaller problem size.
- [ ] **Lulesh systematic bias** — N/C runs show ~0.94x consistently (ordering effect?)
- [ ] **Laghos timing variance** — N/C range 0.98x-1.23x too high for reliable speedup detection
- [ ] **Laghos needs `-d cuda` flag** — Without it, runs on CPU. Agents/harness must know this.
- [ ] **Codex gpt-4.1-mini single-turn exit** — Model produces plan text then exits with `needs_follow_up=false`
- [ ] **Qwen3.5-122B-A10B-FP8** — BLOCKED: needs 8 GPUs or 4x80GB nodes (127GB model)

## Recent Decisions

- 2026-03-04 (s38): nsys analyze expert rules: gpu_gaps threshold=50ms, gpu_time_util threshold=80%. Both 12.4 and 12.9 compatible.
- 2026-03-04 (s38): ncu_profile bottleneck guidance now code-level specific (fast math, launch_bounds, shared mem, grid sizing)
- 2026-03-04 (s38): Cherry-picked 3 upstream SWE-agent fixes (all clean, no conflicts)
- 2026-03-04 (s37): ncu_profile basic mode `-s 0 -c 500` — skip 0 + 500 captures to cover init and simulation phases
- 2026-03-04 (s37): vLLM must be tested via podman-hpc container (v0.11.0), not bare Python install (v0.16.0 on system)
- 2026-03-04 (s37): 8 stale LLNL YAML configs marked as legacy (not deleted) — kept for standalone SWE-agent testing reference
- 2026-03-04 (s37): Perlmutter QOS max 2 interactive jobs — serialize subagent testing, don't launch 3+ concurrent salloc

## Next Steps

1. **Check vLLM Qwen container test result** — subagent running (a9e9a6fa5a32ca652)
2. **Submit Qwen benchmark runs** — 16 jobs after vLLM verification
3. **Check session 36 benchmark results** — 9 gptoss120b jobs still queued
4. **Consider reducing ncu -c 500 to -c 200** — Performance optimization, not blocking
5. Address Laghos timing variance and Lulesh measurement bias
