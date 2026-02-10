---
description: Check results of a SLURM job or benchmark run
---

Check the experiment or benchmark specified: $ARGUMENTS

1. Find the output in batch_results/ (match by job ID or experiment name)
2. Read both the .out and .err files
3. Parse for: final metrics, any errors/warnings, timing information
4. Summarize: did it succeed? Key results? Any issues?
5. Update STATE.md Active Experiments table with findings
