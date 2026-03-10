# Optimization Insights — Session 48 Log Analysis

## Session 46 Kripke (Claude Code, Job 49878379)

### Agent Optimization Progression
Log: `batch_results/claude_openai-gpt-oss-120b_20260310_032230_49878379/run_1/kripke/kripke__base_agent_realtime.log`

| Attempt | Speedup (Solve/Sweep/LTimes/LPlus) | Correctness | Strategy |
|---------|-------------------------------------|-------------|----------|
| 1 | timeout (>159s) | N/A | Compiler flags (`--use_fast_math`, `-funroll-loops`, `-dlcm=ca`) |
| 2 | timeout (>254s) | N/A | More flags — fast_math caused solver divergence |
| 3 | 1.40x / 0.80x / 1.63x / 1.04x | PASSED | CHAI + `-O3 -funroll-loops -Xptxas -O3` (compiler flags only) |
| 4 | 1.16x / 0.98x / 1.25x / 1.11x | PASSED | Same approach, noisy baseline (64-86s) |
| 5 | timeout (>255s) | N/A | New approach failed |
| **6** | **10.71x / 1.89x / 20.93x / 2.60x** | **PASSED (3 values)** | **Fused init ALL 3 kernels (LTimes + LPlusTimes + Scattering) — BUT wrong physics** |
| Final | 2.03x | PASSED | Fused init LTimes + LPlusTimes only (safe) |

### The 20.93x Optimization and Why It Failed

**What the agent did:**
- Kripke calls `kConst(array, 0.0)` to zero 3 large arrays (phi, rhs, phi_out) before each iteration
- `kConst()` uses `RAJA::seq_exec` (CPU sequential) — triggers expensive CHAI-managed GPU→CPU→GPU data transfers for multi-GB arrays
- Agent fused the zeroing INTO the kernel loops: `if(first_index == 0) array = val; else array += val;`
- Eliminated 3 `kConst()` calls from `SteadyStateSolver.cpp` (lines ~58, ~67, ~78)
- This worked for LTimes (phi) and LPlusTimes (rhs) — 20.93x LTimes speedup

**Why it produced wrong physics:**
- Scattering kernel has complex loop with mixed materials and group-to-group scattering
- Agent modified Scattering.cpp for fused init but the logic was buggy
- Agent reverted Scattering.cpp back to original (uses `phi_out += ...`)
- BUT forgot to restore `kConst(phi_out, 0.0)` in SteadyStateSolver.cpp
- Result: `phi_out` accumulated stale values from previous iteration
- Particle count converged to 7.65e7 instead of correct 1.41e8

**Agent self-detection (line 273 of realtime log):**
> "Fused initialization correctness bug: Removing all 3 kConst calls and modifying LTimes, LPlusTimes, and Scattering gave 10.71x speedup but wrong physics (particle count 7.65e7 vs expected 1.41e8). Scattering.cpp was reverted but kConst(phi_out, 0.0) was NOT restored in SteadyStateSolver.cpp - this is the current bug."

**Key insight for future runs:** The `kConst()` elimination IS the right optimization (20x+ potential), but the Scattering kernel's fused init needs careful handling of the mixed-material loop structure. A future agent with this knowledge could potentially achieve 10x+ correctly.

### Files Modified (Final 2.03x Patch)
- `src/Kripke/Kernel/LTimes.cpp` — Fused init: `if(*d == 0) phi = val; else phi += val;`
- `src/Kripke/Kernel/LPlusTimes.cpp` — Fused init: `if(*nm == 0) rhs = val; else rhs += val;`
- `src/Kripke/Kernel/Scattering.cpp` — Whitespace only (reverted)
- `src/Kripke/SteadyStateSolver.cpp` — Removed 2 kConst calls (phi, rhs), kept kConst(phi_out)

### Harness Weakness
- `kripke_run:check_correctness()` only checks 3 output values (line 305)
- Did NOT catch particle count divergence (7.65e7 vs 1.41e8)
- Need to add iteration-by-iteration particle count comparison

---

## Session 46 Quicksilver (Claude Code, Job 49878379)

### Agent Optimization Progression
Log: `batch_results/claude_openai-gpt-oss-120b_20260310_032230_49878379/run_1/quicksilver/quicksilver__base_agent_realtime.log`

Started at 1.02x, built up incrementally:
1. **sincos()**: Replaced separate `sin(phi)` + `cos(phi)` with `sincos(phi, &sinPhi, &cosPhi)` in `CollisionEvent.cc`
2. **Batched atomics**: Local counters per particle, single `atomicAdd()` at end of tracking loop in `CycleTracking.cc` (8 separate atomic ops → 1 batch)
3. **MCT inline optimization**: Eliminated `distance_to_facet[24]` array (576 bytes GPU stack per thread), cached base pointers, inlined min-finding in `MCT.cc`
4. **GPU printf removal**: Removed `printf` in `MC_Segment_Outcome.cc` (causes warp stall)
5. **UVM optimization**: `cudaMemset` for cross-section cache clear in `MC_Domain.cc`
6. **nBatches 10→1**: Reduced simulation batches in `Parameters.hh`

**Final: 1.70x (123 insertions, 50 deletions across 7 files)**

---

## Session 41 Kripke (Claude Code, Job 49641364)

### Why 15.08x (likely inflated)
- Used np=1 (pre-multi-GPU calibration), baseline 29.2s
- Aggressive compiler flags: `--use_fast_math`, `-funroll-loops`, `-dlcm=ca`, `-Xptxas -O3`
- RAJA `cuda_exec<256>` kernel specialization in `Kernel.h`
- `RAJA_HOST_DEVICE` lambda annotations

### Session 41 QS: Lost 1.29x
- Achieved 1.29x with device LTO (`-dlto`) but validation timed out
- Final reported as null/timeout despite real optimization

### Session 41 Laghos: Measurement Noise
- Intermediate 1.10x (cg_max_iter=10), 1.07x (cg_max_iter=9)
- Final: 1.0664x — lower due to measurement variance

---

## Actionable Insights for Future Agents

1. **Kripke `kConst()` is the main bottleneck** — RAJA::seq_exec on CPU with CHAI GPU↔CPU transfer for multi-GB arrays. Fusing into kernels gives 10-20x but Scattering kernel is tricky.
2. **Quicksilver atomic contention** — Per-event atomicAdd in tight particle tracking loop. Batching to per-particle gives 1.7x.
3. **Laghos CG tuning** — Reducing cg_max_iter and relaxing tolerance gives ~1.1-1.3x but is numerically sensitive.
4. **Device LTO (`-dlto`)** — Promising for QS (1.29x in s41) but needs longer validation timeout.
5. **`--use_fast_math` dangerous for iterative solvers** — Caused timeout (non-convergence) in Kripke.
