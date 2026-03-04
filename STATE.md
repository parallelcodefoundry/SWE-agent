# STATE.md — Current Project State

Last updated: 2026-03-04 (session 39)

## Last Session (Session 39)

### vLLM Container Fixes, Qwen Model Validation, Benchmark Submissions

1. **Fixed vLLM A100 compatibility** — Removed `kv_cache_dtype=bfloat16` from model registry (not a valid general option; only for models defaulting to FP8 KV cache like DeepSeek). Added `--enforce-eager` to prevent CUDA graph compilation timeout on first run.
2. **Implemented model-dependent container selection** — `openai/gpt-oss-120b` uses v0.11.0 (stable), all Qwen models use nightly (needs `qwen3_5` arch). `VLLM_IMAGE` env var overrides for manual control.
3. **Validated vLLM nightly (0.16.1rc1.dev206)** — Both Qwen3.5-27B-FP8 and Qwen3-Coder-Next-FP8 load and serve correctly. Chat completions and tool calls pass.
4. **Diagnosed session 36 benchmark failures** — All 9 gptoss120b jobs failed with "Need 5 nodes but only have 1". Root cause: `sbatch batch/run_benchmark.sh` bypasses self-submit logic (which adds `-N`). Fix: use `bash batch/run_benchmark.sh` from login node.
5. **Submitted 24 benchmark jobs** — 16 Qwen + 8 gptoss120b re-submissions. All with correct node counts.

### Previous Session (Session 38)

6. Verified ncu_profile `-c 500` fix — 370 launches, 13 kernel types, 93.1% simulation
7. GPA profiling test PASSED — nsys+ncu on 4 GPA apps
8. Added `nsys analyze` expert rules to nsys_profile
9. Improved ncu_profile bottleneck guidance — code-level suggestions
10. Cherry-picked 3 SWE-agent upstream fixes (blocklist, shlex, deepcopy)

## Active Experiments

### Session 39 Benchmark Submissions

**Qwen3-Coder-Next-FP8:**
| Job ID | Framework | Apps | Nodes |
|--------|-----------|------|-------|
| 49641327 | sweagent | LLNL (K,La,Lu,QS) | 5 |
| 49641328 | opencode | LLNL (K,La,Lu,QS) | 5 |
| 49641329 | openhands | LLNL (K,La,Lu,QS) | 5 |
| 49641330 | codex | LLNL (K,La,Lu,QS) | 5 |
| 49641339 | sweagent | GPA | 2 |
| 49641340 | opencode | GPA | 2 |
| 49641341 | openhands | GPA | 2 |
| 49641342 | codex | GPA | 2 |

**Qwen3.5-27B-FP8:**
| Job ID | Framework | Apps | Nodes |
|--------|-----------|------|-------|
| 49641343 | sweagent | LLNL (K,La,Lu,QS) | 5 |
| 49641344 | opencode | LLNL (K,La,Lu,QS) | 5 |
| 49641345 | openhands | LLNL (K,La,Lu,QS) | 5 |
| 49641346 | codex | LLNL (K,La,Lu,QS) | 5 |
| 49641353 | sweagent | GPA | 2 |
| 49641355 | opencode | GPA | 2 |
| 49641356 | openhands | GPA | 2 |
| 49641357 | codex | GPA | 2 |

**gptoss120b (re-submission):**
| Job ID | Framework | Apps | Nodes |
|--------|-----------|------|-------|
| 49641358 | sweagent | LLNL (K,La,Lu,QS) | 5 |
| 49641359 | opencode | LLNL (K,La,Lu,QS) | 5 |
| 49641360 | openhands | LLNL (K,La,Lu,QS) | 5 |
| 49641361 | sweagent | GPA | 2 |
| 49641362 | opencode | GPA | 2 |
| 49641363 | openhands | GPA | 2 |
| 49641364 | claude | LLNL (K,La,Lu,QS) | 4 |
| 49641366 | claude | GPA | 1 |

## Branch State

- **Current branch**: `dev` (21 commits ahead of `origin/dev`)
- **Latest commit**: `1a399bad` — Model-dependent vLLM container selection in registry
- **Working tree**: Clean (only untracked: Laghos char scripts, xyz.asc, output.{out,txt})

## All Infrastructure Fixes — Complete

- [x] All previous fixes (sessions 33-38)
- [x] Fix vLLM kv_cache_dtype — bfloat16 is not valid for non-FP8-default models (session 39)
- [x] Add --enforce-eager to vLLM launch (session 39)
- [x] Model-dependent container selection — v0.11.0 for gptoss, nightly for Qwen (session 39)
- [x] Diagnosed session 36 node count failure — sbatch bypasses self-submit (session 39)

## Open Issues / TODOs

### Actionable
- [ ] **Check session 39 benchmark results** — 24 jobs submitted, all pending
- [ ] **Empty tool_calls [] from Qwen models** — Both Qwen models return `tool_calls: []` in responses. SWE-agent outbound filter (line 870 models.py) should handle this, but monitor for crashes.
- [ ] **Codex gptoss120b external-model submission** — Needs `OPENAI_API_BASE` and `OPENAI_API_KEY` env vars. Skipped in session 39.
- [ ] **Consider reducing ncu basic mode from -c 500 to -c 200** — Performance optimization, not blocking.

### Persistent Issues
- [ ] **Quicksilver consistent timeout** — All frameworks timeout on QS
- [ ] **Lulesh systematic bias** — N/C runs show ~0.94x consistently
- [ ] **Laghos timing variance** — N/C range 0.98x-1.23x too high
- [ ] **Codex gpt-4.1-mini single-turn exit** — Model exits with `needs_follow_up=false`
- [ ] **Qwen3.5-122B-A10B-FP8** — BLOCKED: needs 8 GPUs or 4x80GB nodes

## Recent Decisions

- 2026-03-04 (s39): vLLM container per-model: v0.11.0 for gptoss (stable), nightly for Qwen (needs qwen3_5 arch)
- 2026-03-04 (s39): kv_cache_dtype=bfloat16 removed — only valid for FP8-default models (e.g. DeepSeek), not Qwen
- 2026-03-04 (s39): --enforce-eager added to all vLLM launches — prevents CUDA graph timeout on first run
- 2026-03-04 (s39): Session 36 jobs failed due to sbatch bypassing self-submit (missing -N). Use `bash batch/run_benchmark.sh` not `sbatch batch/run_benchmark.sh`
- 2026-03-04 (s39): vLLM nightly = 0.16.1rc1.dev206, supports qwen3_5 + qwen3_next. Latest = v0.16.0, does NOT support qwen3_5.

## Next Steps

1. **Check session 39 benchmark results** — 24 jobs queued
2. **Monitor for empty tool_calls crash** — If Qwen jobs fail, need litellm/SWE-agent patch
3. **Submit Codex gptoss120b external-model** — Need to source API keys first
4. **Address Laghos timing variance and Lulesh measurement bias**
