# STATE.md — Current Project State

Last updated: 2026-03-04 (session 36)

## Last Session (Session 36)

### GPA Improvements, NCU Tool, vLLM Model Registry, Benchmark Resubmission

1. **GPA timing robustness** — Increased nsys samples from 3→5 (`num_samples=5` in `_run_gpa_driver()`) and added warmup run before nsys profiling loop in `driver_profiling.py`. Warmup run discards result, warms CUDA context.
2. **GPA diff storage** — Replaced full-content `agent_patch` with unified diff format using `difflib.unified_diff()` with `fromfile`/`tofile` headers. Falls back to full content if no original to compare.
3. **vLLM model registry** — Added `MODEL_REGISTRY` associative array in `run_benchmark.sh` mapping model names to `tool_call_parser|reasoning_parser|kv_cache_dtype|gpu_mem_util`. Added `_lookup_model_settings()` function. Updated `vllm_server.sh` to use env var defaults.
4. **NCU profiling tool** — Created `tools/nsight_compute/{config.yaml,bin/ncu_profile}`. Tested on all 4 proxy apps (Lulesh, Kripke, Laghos, Quicksilver) in both basic and detailed modes. Fixed 7 bugs discovered during testing.
5. **Downloaded 3 Qwen FP8 models** — `Qwen3.5-27B-FP8` (~31GB), `Qwen3-Coder-Next-FP8` (~80GB), `Qwen3.5-122B-A10B-FP8` (~127GB). All at `/pscratch/sd/k/krydzy/hf-cache/hub/`.
6. **Fixed bf16→bfloat16** — vLLM v0.11.0 rejects `bf16`, requires `bfloat16`. Updated all Qwen entries in MODEL_REGISTRY.
7. **Submitted 9 benchmark jobs** — 4 LLNL + 4 GPA + 1 Codex-Lulesh. See Active Experiments table.

### Previous Session (Session 35)

8. **GPA upstream merge** — 29 commits from `origin/develop` fixing CUDA 13 baseline builds.
9. **OpenAI regional endpoint validation** — `validate_openai_base_url()`, `--openai-region` flag.
10. **GPA SKILL.md update** — Timing, workspace, results, common issues.

## Active Experiments

### Session 36 Benchmark Submissions (PENDING)

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

### GPA Benchmark Results (Session ~30, A100) — SUPERSEDED by new runs

| Job | Framework | Model | Build Fail | No Change | Correct Fail | Speedup | Best |
|-----|-----------|-------|------------|-----------|-------------|---------|------|
| 49366712 | SWE-agent | gpt-4o-mini | 4 | 3 | 8 | 1 | streamcluster 1.28x |
| 49366711 | Codex | gpt-4.1-mini | 4 | 10 | 2 | 0 | — |
| 49366713 | OpenCode | gpt-4o-mini | 5 | 5 | 3 | 3 | streamcluster 0.76x (regression) |
| 49366714 | OpenHands | gpt-4o-mini | 5 | 1 | 7 | 2 | streamcluster 1.30x |

### LLNL Benchmark Results (Sessions 29-32) — SUPERSEDED by new runs

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

- **Current branch**: `dev` (8 commits ahead of `origin/dev`)
- **Latest commit**: `f42541b8` — Fix vLLM kv-cache-dtype (bf16→bfloat16) and NCU profiling bugs
- **GPA-Benchmark**: warmup run added to `driver_profiling.py` (uncommitted in GPA repo)
- **Working tree**: HANDOFF.md modified (uncommitted)
- **Untracked**: Laghos characterization scripts, `xyz.asc`

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

## Open Issues / TODOs

### Actionable
- [ ] **Check session 36 benchmark results** — 9 jobs submitted, check `squeue -u krydzy` and `batch_results/`
- [ ] **Qwen3.5-27B-FP8 benchmark runs** — Model downloaded, `--kv-cache-dtype bfloat16` ready
- [ ] **Qwen3-Coder-Next-FP8 benchmark runs** — Model downloaded, `--kv-cache-dtype bfloat16` ready
- [ ] **Cherry-pick SWE-agent upstream fixes** — 3 bugs: blocklist inversion (`c69d6f56`), shlex.quote (`3ff833d9`), completion_kwargs deepcopy (`ed7dd55c`)

### Persistent Issues
- [ ] **Quicksilver consistent timeout** — All frameworks timeout on QS. May need smaller problem size.
- [ ] **Lulesh systematic bias** — N/C runs show ~0.94x consistently (ordering effect?)
- [ ] **Laghos timing variance** — N/C range 0.98x-1.23x too high for reliable speedup detection
- [ ] **Codex gpt-4.1-mini single-turn exit** — Model produces plan text then exits with `needs_follow_up=false`
- [ ] **Qwen3.5-122B-A10B-FP8** — BLOCKED: needs 8 GPUs or 4x80GB nodes (127GB model)

## Recent Decisions

- 2026-03-04 (s36): vLLM `--kv-cache-dtype bfloat16` NOT `bf16` — v0.11.0 rejects the abbreviation
- 2026-03-04 (s36): Per-model gpu_mem_util in MODEL_REGISTRY — 0.60 for 27B, 0.85 for Coder-Next, 0.92 for 122B
- 2026-03-04 (s36): NCU metric `dram__cycles_active` not `dram__throughput` — confirmed by testing
- 2026-03-04 (s36): Skip Codex with gptoss120b — confirmed broken (never makes code changes)
- 2026-03-04 (s35): GPA upstream merged — CUDA 13 migration fixes 4 always-failing apps
- 2026-03-04 (s35): GPA workspace intentionally minimal (kernel .cu only, no Makefiles)
- 2026-03-04 (s35): OpenAI regional endpoints — diagnostic only, never mutates URL
- 2026-03-02 (s34): Codex first-party models must pass OPENAI_API_BASE as model_providers.openai.base_url
- 2026-03-02 (s34): Claude Code CLI requires --verbose with --output-format stream-json (v2.1.59+)
- 2026-03-02 (s33): SWE-agent signature format must use `[<arg>]` not `[--flag]`

## Next Steps

1. **Check benchmark results** — `squeue -u krydzy` then analyze `batch_results/` for jobs 49639229-49639242
2. **Qwen benchmark runs** — Start with Qwen3.5-27B-FP8 (fits easily), then Qwen3-Coder-Next-FP8
3. **Cherry-pick SWE-agent upstream fixes** — 3 bugs identified
4. Address Laghos timing variance and Lulesh measurement bias
5. Investigate QS consistent timeout across all frameworks
