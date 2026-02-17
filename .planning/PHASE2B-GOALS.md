# Phase 2B: Validation Sprint — Goal Checklist

## Design Decisions (already made — do not revisit)

1. **GPA agent workspace model**: Agent gets a workspace directory with kernel `.cu` file(s) and a prompt. Agent edits files in place. Runner reads modified files and passes to `run_driver(swaps_override=...)`. Same as Phase 2.
2. **GPA lulesh is excluded**: Empty `LULESH/` dir upstream. 16 active apps, not 17.
3. **SWE-fficiency eval pipeline works on Perlmutter**: 4 podman fixes applied in Phase 2 (commit `be86360`). Requires podman socket + `DOCKER_HOST` env var.
4. **SWE-fficiency inference specs are Jinja2 templates**: `custom.py` renders them via `Template(text).render()`. Nested template variables (e.g., SWE-agent's `{{observation}}`) must be escaped with `{% raw %}...{% endraw %}`.
5. **OpenCode is the first test agent**: Simplest setup, no container/sandbox layer, direct CLI.
6. **GPA driver tool follows existing harness pattern**: `tools/gpa_harness/` with `config.yaml` + `bin/` scripts, same as `tools/quicksilver_harness/`.
7. **SWE-fficiency gold eval can run without GPU**: It's CPU-bound Python workloads inside containers. Only needs podman socket.
8. **Profiling tools are generic**: `hpc_profile`, `hatchet_analyze`, `compiler_analysis`, `microbench_code` all work on arbitrary CUDA code — not hardcoded to LLNL apps. They should work on GPA kernels.
9. **Two profiling ecosystems for GPA**: Our HPCToolkit/hatchet wrappers AND the GPA driver's built-in nsys/ncu profiling (via `run_driver(nsys=True)`). Both should be available to agents.
10. **Phase 2B, not Phase 3**: Phase 3 is reserved for repo restructuring (`agents-perf` repo with submodules).
12. **SWE-fficiency re-curated for parallelism**: Audit of all 498 SWE-fficiency instances found 28 with parallel/concurrency characteristics (0 GPU). Re-curated from 27 general instances to 12 parallelization-focused instances (4 strict concurrency, 2 Cython prange, 6 vectorization). Suite now tests 3 optimization dimensions: GPA (GPU kernel), LLNL (HPC proxy app), SWE-fficiency (Python parallelization).
11. **GPA profiling: explore driver-integrated vs standalone tools**: The GPA driver already knows how to nsys/ncu profile each app (build paths, kernel names, validation). It may be simpler to expose this through `gpa_test --profile nsys` than to have agents run `hpc_profile` on executables they didn't build. Test both approaches in Goals 3-4 and go with what works better. This is an explicit exploration — not a premade decision.

## Operational Notes

- `source ~/.openai_env` — sets `OPENAI_API_BASE` and `OPENAI_API_KEY`. Env vars don't persist across Claude shell invocations — always chain with `&&`.
- Podman socket: `podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &`
- `export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock`
- Max 2 concurrent `salloc` interactive jobs.
- Use perlmutter-executor subagent for GPU/compute work.
- Load skill files before working on unfamiliar benchmarks/frameworks.

## Goals

- [x] Goal 0: Remove GPA lulesh from app list
  - Skip `lulesh` in `_generate_gpa_base_instances()` and `_load_gpa_app_configs()` in `batch/hpc_benchmark_runner.py`
  - Update counts from 17 to 16 in: `batch/hpc_benchmark_runner.py` comments, `agent_docs/architecture.md`, `.claude/skills/gpa-benchmark/SKILL.md`
  - Update PHASE2-GOALS.md references if any mention 17
  - Update total instance count: LLNL (4) + GPA (16) + SWE-fficiency (12) = 32
  - Commit with descriptive message

- [x] Goal 1: Fix Jinja2 template bugs in SWE-fficiency inference specs
  - CRITICAL: `sweagent.yaml` has un-escaped SWE-agent template variables (`{{observation}}`, `{{working_dir}}`, `{{open_file}}`, `{{diff}}`) inside the inline config heredoc. Jinja2 renders these to empty strings, breaking the SWE-agent config.
  - Fix: wrap SWE-agent template sections in `{% raw %}...{% endraw %}` blocks
  - Audit all 4 specs (sweagent, opencode, codex_cli, openhands) for similar issues
  - Dry-run render: load each spec with `custom.py`'s `load_spec()` and `render_inline()` on the inference command to verify correct output
  - Commit fixes

- [x] Goal 2: Gold eval SWE-fficiency subset — timing discovery + validation
  - Run gold eval on 5 instances (1 per fast-likely repo): numpy, scipy, dask, sympy, astropy
  - Use `swefficiency eval` CLI directly (not through runner) with `--num_workers 3` for parallelism
  - Record per-instance timing to calibrate expectations (pandas was ~77 min; others may be 15-30 min)
  - Verify: container pulls, workload execution, correctness tests, speedup reporting
  - Also run 1 instance through our `_run_swefficiency_base()` to validate runner integration
  - Based on timing data: decide whether remaining 22 instances can fit in a single salloc or need sbatch
  - Record which instances pass and fail

- [x] Goal 3: Add GPA driver as agent-accessible harness tool + profiling config
  - **GPA harness tool** — Create `tools/gpa_harness/config.yaml` defining `gpa_test` tool (build + run + validate + timing):
    - Create `tools/gpa_harness/bin/gpa_test` Python script that:
      - Reads the modified kernel file from the workspace (CWD)
      - Calls `run_driver(app=X, swaps_override={...}, sm_version=80, nsys=True)` for timing
      - Reports: build status, correctness (validate), baseline time, optimized time, speedup
      - Accepts `--app` argument (auto-reads from `gpa_metadata.json` in workspace if not provided)
    - Create a CLI wrapper script agents can call via bash (for OpenCode/Codex/OpenHands)
  - **GPA profiling config** — Create `config/hpc/gpa_with_profiling.yaml`:
    - Same as `gpa_no_profiling.yaml` but add tool bundles: `tools/hpctoolkit`, `tools/hatchet`, `tools/profiling`
    - This gives agents access to: `hpc_profile`, `hatchet_analyze`, `compiler_analysis`, `microbench_code`
    - These are GENERIC tools that work on any CUDA code — should work on GPA kernels
    - `compiler_analysis` is the most directly useful (register count, occupancy estimate on .cu files)
    - `hpc_profile` needs the built executable path — GPA builds happen inside run_driver(), so document that the agent can use `compiler_analysis` on their .cu file, or use `gpa_test` (which runs nsys internally)
  - Update `gpa_no_profiling.yaml` to include the gpa_harness tool bundle
  - **Explore combining GPA driver profiling with our tools**: The GPA driver has built-in nsys/ncu profiling (`run_driver(nsys=True, ncu=True)`) that already knows how to build, profile, and parse results for each app. If wrapping `run_driver()` into `gpa_test` with profiling output proves simpler and more informative than having agents run `hpc_profile`/`compiler_analysis` separately, lean into that approach. The driver knows the executable paths, build flags, kernel names, and validation — it may be more practical to expose its profiling data through `gpa_test` (e.g., `gpa_test --profile nsys` or `gpa_test --profile ncu`) rather than asking agents to wrangle HPCToolkit on GPA executables they didn't build. Evaluate during testing and document which approach works better.
  - Test: `gpa_test` manually on gaussian with a trivially modified kernel, and `compiler_analysis` on a GPA .cu file
  - Commit

- [x] Goal 4: E2E test GPA with OpenCode (with profiling tool validation)
  - Run gaussian twice: once WITHOUT profiling tools, once WITH them
  - Without profiling: `source ~/.openai_env && python3 batch/hpc_benchmark_runner.py --app gpa --framework opencode --model-name gpt-4o --instance-id gaussian`
  - With profiling: same but with `--profiling with_profiling` (needs gpa_with_profiling.yaml from Goal 3)
  - Verify: workspace setup, prompt generation, agent launch, code collection, driver timing, result reporting
  - Verify profiling tools work on GPA: does the agent successfully use `compiler_analysis` on the kernel? Can it interpret the register/occupancy output?
  - If the GPA driver's profiling-through-`gpa_test` approach from Goal 3 looks promising, test that path too — compare agent experience using `compiler_analysis` standalone vs `gpa_test --profile nsys` (or however it was implemented)
  - If gaussian works, try 1-2 more apps (hotspot, xsbench)
  - Record results and any issues — especially which profiling approach agents find more actionable

- [x] Goal 5: E2E test SWE-fficiency with OpenCode
  - Pick 1 fast-passing instance from Goal 2 results (prefer numpy or dask)
  - Run: `source ~/.openai_env && python3 batch/hpc_benchmark_runner.py --app swefficiency --framework opencode --model-name gpt-4o --instance-id <instance>`
  - Verify: inference spec rendering, custom.py container launch, agent execution, patch extraction, eval pipeline, speedup reporting
  - This validates the FULL pipeline: runner -> custom.py -> container -> agent -> patch -> eval -> result
  - Record results and any issues

- [x] Goal 6: Test remaining agents (SWE-agent, Codex, OpenHands) on GPA
  - Run gaussian with each framework (with GPA driver tool + profiling):
    - `--framework sweagent --model-name gpt-4o`
    - `--framework codex --model-name gpt-4o`
    - `--framework openhands --model-name gpt-4o`
  - GPA apps are fast (~30-60s per driver run) so all 3 can happen in one salloc session
  - Record: which frameworks succeed, quality of optimizations, profiling tool usage, any framework-specific issues
  - Debug and fix any framework-specific launch/config issues

- [x] Goal 7: Test remaining agents on SWE-fficiency + GPU/parallel instance audit
  - **GPU/Parallel Instance Check** (COMPLETED — see findings below):
    - Analyzed all 27 curated SWE-fficiency instances for GPU/CUDA and parallelization characteristics
    - **Result: 0/27 GPU instances, 1/27 parallelization instance (scikit-learn-13310)**
    - SWE-fficiency is fundamentally a Python library optimization benchmark (numpy, scipy, pandas, etc.)
    - The full 498-instance dataset draws from the same Python ecosystem — no GPU instances exist
    - **Decision needed**: SWE-fficiency targets a DIFFERENT optimization dimension than GPA/LLNL:
      - GPA: GPU kernel optimization (CUDA anti-patterns)
      - LLNL: HPC proxy app optimization (MPI+CUDA scientific codes)
      - SWE-fficiency: Python library performance optimization (algorithmic, caching, vectorization)
    - **DONE**: Re-curated from 27 general instances to 12 parallelization-focused instances:
      - 4 strict concurrency (joblib, concurrent.futures, threadpool)
      - 2 Cython prange/OpenMP
      - 6 high-impact vectorization (NumPy/PyArrow/BLAS implicit parallelism)
    - Updated SWEFFICIENCY_CURATED_INSTANCES in hpc_benchmark_runner.py
  - **Agent tests on scikit-learn__scikit-learn-13310** (SLURM job 49055388):
    - SWE-agent: Install FAILED — `togetherunidiff` not found, Python version mismatch in container
    - Codex CLI: **PRODUCED PATCH** — rewrote pairwise.py with threading backend. Patch was missed by runner due to `codex-cli` vs `codex_cli` name mismatch (fixed in swefficiency repo `313572f`)
    - OpenHands: Install FAILED — `openhands-ai` dependency conflicts in Ubuntu 22.04 container
  - **Bug found and fixed**: `codex_cli.yaml` had `name: codex-cli` (hyphen) but runner constructs path with `codex_cli` (underscore). Fixed in swefficiency repo.
  - **Known issue**: SWE-agent and OpenHands install templates need updating for SWE-fficiency containers (Python 3.9/Ubuntu 22.04). The agent frameworks require newer Python (3.10+). This is a template issue, not a pipeline bug.

- [ ] Goal 8: Fix issues and final regression
  - Fix any bugs discovered in Goals 4-7
  - Launch full 27-instance gold eval in background (if not already done in Goal 2)
  - **Instance classification validation**: Verify benchmark suite covers 3 optimization dimensions:
    - GPU kernel optimization (GPA): 16 CUDA anti-pattern instances
    - HPC proxy app optimization (LLNL): 4 MPI+CUDA proxy apps (Kripke, Laghos, Lulesh, Quicksilver)
    - Python parallelization optimization (SWE-fficiency): 12 parallel-focused Python instances
    - Document in architecture.md that SWE-fficiency is intentionally CPU-Python (no GPU/CUDA)
    - Total: 32 instances across 3 dimensions
  - Run regression: LLNL (4) + GPA (16) + SWE-fficiency (12) = 32 instances all generate correctly
  - Update STATE.md, architecture.md, experiment-workflow.md with validation results
  - Commit all fixes

- [ ] Goal 9: (Optional) Investigate SWE-agent containerization
  - Only if SWE-agent failed in Goals 6-7 due to sandbox/container issues
  - Check if early local-mode commits on our branch broke Docker/sandbox mode
  - Document findings and fix if feasible

## Profiling Tools Reference

**Our tools (generic, HPCToolkit-based):**
| Tool | What it does | Works on GPA? | Config location |
|------|-------------|---------------|-----------------|
| `hpc_profile` | Full HPCToolkit profiling (hpcrun/hpcstruct/hpcprof) | Yes (any CUDA binary) | `tools/hpctoolkit/` |
| `hatchet_analyze` | Analyze HPCToolkit DB (hot path, function ranking) | Yes (any HPCToolkit DB) | `tools/hatchet/` |
| `compiler_analysis` | nvcc -ptxas analysis (registers, occupancy, spills) | **Yes (best for GPA)** | `tools/profiling/` |
| `microbench_code` | Compile + time a standalone .cu file | Yes (any CUDA code) | `tools/profiling/` |
| `benchmark_code` | Git-based comparison workflow | **No (quicksilver/kripke only)** | `tools/profiling/` |

**GPA driver's built-in profiling (exposed via `gpa_test` tool):**
| Feature | What it does | How accessed |
|---------|-------------|-------------|
| `run_driver(nsys=True)` | Nsight Systems timing | Via `gpa_test` tool output (baseline vs optimized time) |
| `run_driver(ncu=True)` | Nsight Compute metrics | Could be exposed in `gpa_test` with `--ncu` flag |

**How agents get profiling tools:**
- SWE-agent: `*_with_profiling.yaml` includes tool bundles
- OpenCode/Codex/OpenHands: `base.py` adds `PROFILING_TOOL_DIRS` to PATH when `profiling == "with_profiling"`
- All 4 frameworks use the same mechanism from `batch/frameworks/base.py` lines 19-25

## Key Integration Points

**GPA driver tool pattern (Goal 3):**
```bash
# Agent calls from workspace:
gpa_test              # auto-detects app from gpa_metadata.json
gpa_test --app gaussian  # explicit app name

# Output:
# BUILD: PASSED
# CORRECTNESS: PASSED (4/4 validation checks)
# BASELINE TIME: 0.00234s (mean of 3 samples)
# OPTIMIZED TIME: 0.00187s (mean of 3 samples)
# SPEEDUP: 1.25x
```

**Agent profiling on GPA kernels (Goal 4):**
```bash
# Agent can use compiler_analysis directly on the kernel file:
compiler_analysis gaussian.cu

# Output:
# registers: 24
# smem_bytes: 4096
# spill_loads: 0
# occupancy_estimate: 75%
```

**SWE-fficiency gold eval (Goal 2):**
```bash
cd /pscratch/sd/k/krydzy/swefficiency
source .venv/bin/activate
podman-hpc system service --time=0 unix:///run/user/$(id -u)/podman/podman.sock &
export DOCKER_HOST=unix:///run/user/$(id -u)/podman/podman.sock

swefficiency eval --run_id gold_phase2b \
  --instances_regex "numpy__numpy-11720|scipy__scipy-10064|dask__dask-10356|sympy__sympy-10621|astropy__astropy-10814" \
  --num_workers 3
```
