---
description: Rules for running work on Perlmutter compute nodes
globs:
  - "batch/**"
  - "tools/**"
  - "scripts/**"
---

## Always Prefer Interactive Sessions for Validation

When running benchmarks, validation tests, E2E tests, or any compute-node work:

1. **Use `salloc` (interactive)** — NOT `sbatch` (batch). Interactive sessions start immediately and allow real-time monitoring, early cancellation, and faster iteration.
2. **Only use `sbatch`** for: runs >4 hours, multi-node (>4 nodes), or intentionally unattended overnight jobs.
3. **Delegate to perlmutter-executor agent** for any compute-node work — it handles allocation, module loading, and execution automatically.

```bash
# GOOD — interactive, immediate start
salloc --nodes 1 --qos interactive --time 01:00:00 --constraint gpu --gpus 4 --account m2404
srun --exclusive --gpus 4 ... bash -lc "..."

# AVOID for validation — sits in queue
sbatch batch/run_benchmark.sh ...
```
