# HANDOFF — Session 39 → Session 40

Last updated: 2026-03-04 (session 39)

## What We Were Working On

Session 39: Fixed vLLM A100 compatibility (removed invalid bfloat16 KV cache, added --enforce-eager), implemented model-dependent container selection (v0.11.0 for gptoss, nightly for Qwen), validated both Qwen models on vLLM nightly, diagnosed session 36 node count failures, submitted 24 benchmark jobs.

## Goal Progress
- [x] Goal 0: Fix vLLM A100 compatibility — removed bfloat16, added --enforce-eager
- [x] Goal 1: Implement model-dependent container selection — v0.11.0 for gptoss, nightly for Qwen
- [x] Goal 2: Validate Qwen3.5-27B-FP8 on nightly — PASS (Qwen3_5ForConditionalGeneration resolved)
- [x] Goal 3: Validate Qwen3-Coder-Next-FP8 on nightly — PASS (tool calls working)
- [x] Goal 4: Diagnose session 36 failures — sbatch bypasses self-submit (missing -N)
- [x] Goal 5: Submit Qwen benchmark runs — 16 jobs (8 per model)
- [x] Goal 6: Re-submit gptoss120b benchmarks — 8 jobs (with correct node counts)
- [ ] Goal 7: Check session 39 benchmark results — 24 jobs all PENDING (Priority)
- [ ] Goal 8: Submit Codex gptoss120b external-model — needs OPENAI_API_BASE env var

## Key Commits (Session 39)

| Commit | Description |
|--------|-------------|
| `1a399bad` | Model-dependent vLLM container selection in registry |
| `b3736562` | Switch vLLM container from v0.11.0 to nightly for Qwen3.5 support |
| `0799c39a` | Fix vLLM A100 compatibility: remove bfloat16 KV cache, add enforce-eager |
| `e7f3b28b` | WIP: Save session 38 state — GPA analysis, upstream merge, URL validation |

## Active Benchmark Jobs (24 total, all PENDING)

**Qwen3-Coder-Next-FP8 (8 jobs):**
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

**Qwen3.5-27B-FP8 (8 jobs):**
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

**gptoss120b re-submission (8 jobs):**
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

## Files Modified This Session

| File | Change |
|------|--------|
| `batch/run_benchmark.sh` | Model-dependent container selection (5th field in MODEL_REGISTRY), removed bfloat16, added --enforce-eager, lowered Coder-Next gpu_mem_util to 0.70 |
| `batch/vllm_server.sh` | Added --enforce-eager, default image v0.11.0 (env var override) |
| `.claude/skills/nsight-compute/SKILL.md` | Updated with GPA test results from session 38 |
| `STATE.md` | Rewritten with session 39 progress |

## Files to Read First Next Session

1. `STATE.md` — Full state overview
2. `.planning/HANDOFF.md` — This file
3. Check benchmark queue: `squeue -u krydzy`
4. `batch/run_benchmark.sh` lines 58-110 — MODEL_REGISTRY and _lookup_model_settings

## Key Decisions (Session 39)

- **vLLM container per-model**: v0.11.0 for gptoss (stable), nightly for Qwen (needs qwen3_5 arch)
- **kv_cache_dtype=bfloat16 removed**: Only valid for FP8-default models (e.g. DeepSeek), not Qwen
- **--enforce-eager**: Added to all vLLM launches — prevents CUDA graph compilation timeout
- **Session 36 jobs failed**: sbatch bypasses self-submit (missing -N). Use `bash batch/run_benchmark.sh` from login node
- **vLLM nightly = 0.16.1rc1.dev206**: Supports qwen3_5 + qwen3_next. v0.16.0 (latest) does NOT support qwen3_5

## Monitoring Concerns

- **Empty tool_calls [] from Qwen**: Both models return `tool_calls: []` in responses. SWE-agent outbound filter (line 870 models.py: `and tool_calls` is falsy for []) should handle this, but monitor for crashes.
- **content: null with reasoning field**: Qwen models put text in `reasoning` field, not `content`. `--reasoning-parser qwen3` handles this.

## Verification Commands (Interactive)

```bash
# Check benchmark results
squeue -u krydzy  # Are jobs still queued?
sacct -u krydzy --starttime=2026-03-04 --format=JobID,JobName,State,ExitCode,Elapsed,NNodes -n | head -30

# Find completed job output
ls -lt batch_results/ | head -20

# Quick results check for a specific job
grep -r "CORRECTNESS" batch_results/benchmark_*_49641327/ 2>/dev/null
```

## Gotchas

- **sbatch vs bash for run_benchmark.sh**: MUST use `bash batch/run_benchmark.sh` from login node (triggers self-submit with -N). `sbatch batch/run_benchmark.sh` runs inside SLURM and gets 1 node.
- **VLLM_IMAGE env var overrides registry**: If set in environment, all models use that image regardless of registry setting.
- **Codex external-model needs env vars**: `source ~/.openai_env` sets OPENAI_API_BASE and OPENAI_API_KEY. Skipped in session 39.
- **Perlmutter QOS max 2 interactive jobs**: Cannot launch 3+ salloc subagents simultaneously.
- **srun "nodes are busy"**: If a previous srun step on an allocation is stale, new steps fail. Cancel+restart allocation.

## Branch State

- **SWE-agent (dev)**: Clean after `1a399bad`, 21 commits ahead of `origin/dev`
- **Untracked**: `scripts/char_laghos*.{sh,sbatch}`, `xyz.asc`, `output.{out,txt}`
