"""Shared prompt templates for all frameworks.

Extracts the core task content from SWE-agent YAML configs into
framework-neutral templates, then applies per-framework adaptations
(tool names, completion signals, profiling tool descriptions).

Prompt structure (for LLNL proxy apps):
  1. ROLE + AUTONOMY DIRECTIVE
  2. BUILD TARGET (essential flags per app)
  3. TASK + WORKSPACE
  4. WORKFLOW
  5. TOOLS (harness mode) or BUILD INSTRUCTIONS (direct mode)
  6. COMPLETION
"""

# =============================================================================
# Per-app task descriptions
# =============================================================================

APP_DESCRIPTIONS = {
    "kripke": "the Kripke 3D Sn deterministic transport application",
    "laghos": "the Laghos high-order Lagrangian hydrodynamics application",
    "lulesh": "the LULESH shock hydrodynamics proxy application",
    "quicksilver": "the Quicksilver Monte Carlo particle transport application",
}

# =============================================================================
# Per-app tool names (harness mode)
# =============================================================================

APP_TOOLS = {
    "kripke": {"build": "kripke_build --arch CUDA", "run": "kripke_run --arch CUDA"},
    "laghos": {"build": "laghos_build", "run": "laghos_run"},
    "lulesh": {"build": "lulesh_build", "run": "lulesh_run"},
    "quicksilver": {"build": "qs_build", "run": "qs_run"},
}

# =============================================================================
# Per-app essential build requirements
# =============================================================================

ESSENTIAL_FLAGS = {
    "kripke": """\
ESSENTIAL BUILD REQUIREMENTS (do NOT remove these):
- CUDA enabled: -DENABLE_CUDA=ON
- MPI enabled: -DENABLE_MPI=ON
- GPU architecture: -DCMAKE_CUDA_ARCHITECTURES=80 (A100)
- Host compiler: g++-12 (nvcc requires GCC <= 13)
- CUDA flags must include: --extended-lambda --expt-relaxed-constexpr (required by RAJA)
- Do NOT add -fno-exceptions or -fno-rtti (breaks RAJA/CAMP)""",

    "laghos": """\
ESSENTIAL BUILD REQUIREMENTS (do NOT remove these):
- Build target: MFEM with CUDA (pcuda)
- Host compiler: OMPI_CXX=g++-12
- Dependencies: mfem, hypre, metis must remain linked
- Do NOT disable CUDA/GPU support""",

    "lulesh": """\
ESSENTIAL BUILD REQUIREMENTS (do NOT remove these):
- CUDA architecture: sm_80 (A100)
- Host compiler: g++-12 via --compiler-bindir
- MPI: USE_MPI=1 with MPICH_DIR set
- Standard: -std=c++11
- Do NOT disable CUDA/GPU support""",

    "quicksilver": """\
ESSENTIAL BUILD REQUIREMENTS (do NOT remove these):
- CXX must be nvcc (CUDA compiler)
- GPU target: -gencode=arch=compute_80,code=sm_80
- Host compiler: g++-12 via --compiler-bindir
- MPI: link against MPI libraries
- Standard: -std=c++11
- HAVE_CUDA must be defined
- Do NOT disable CUDA/GPU support""",
}

# =============================================================================
# Role + autonomy directive (top of every prompt)
# =============================================================================

AUTONOMY_DIRECTIVE = """\
You are an autonomous HPC performance engineer. Your goal is to optimize \
application runtime on NVIDIA A100 GPUs.

CRITICAL RULES:
- NEVER ask for confirmation or clarification. Implement changes directly.
- You MUST produce code changes. Analysis alone is FAILURE.
- Make changes, rebuild, measure. Repeat until you have a measurable improvement.
- If an approach doesn't work, revert it and try something different."""

# Anti-yielding directive for non-interactive agents (Codex, Claude Code)
NON_INTERACTIVE_DIRECTIVE = """\
CRITICAL: You are in non-interactive mode. There is NO human to respond.
NEVER output "Would you like..." or "Shall I..." — just DO IT.
You MUST edit source files before stopping. Analysis alone means FAILURE."""

# =============================================================================
# Build target (hardware + compiler environment)
# =============================================================================

BUILD_TARGET = """\
BUILD ENVIRONMENT:
- GPU: NVIDIA A100 (sm_80), CUDA 12.4
- MPI: OpenMPI 5.0.7
- Host compiler: g++-12 (required — nvcc incompatible with GCC >= 13)
- OS: SUSE Linux on Perlmutter (NERSC)"""

# =============================================================================
# What agents CAN and MUST NOT change
# =============================================================================

CHANGE_RULES = """\
WHAT YOU CAN CHANGE:
- Source code (.cpp, .cu, .cc, .hh, .h files)
- Compiler optimization flags (e.g., -O3, -funroll-loops, -use_fast_math)
- CMakeLists.txt and Makefiles (to add flags, change options)
- Data structures, memory layouts, algorithms
- CUDA kernel launch configurations (block size, grid size)
- Any valid code-level or build-level optimization

WHAT YOU MUST NOT CHANGE:
- GPU architecture target (must remain sm_80 / A100)
- MPI support (must stay enabled)
- Host compiler version (must remain g++-12)
- Do NOT delete entire source files or remove critical #include directives
- Do NOT disable CUDA/GPU code paths"""

MPI_RUNTIME_GUIDANCE = """\
CRITICAL MPI CONSTRAINT:
- All apps run on MULTIPLE GPUs via MPI (Kripke/Laghos/QS: 4 ranks, Lulesh: 8 ranks)
- The validation harness uses mpirun — disabling MPI causes SEGFAULTS
- DO NOT set USE_MPI=0, remove -DENABLE_MPI=ON, or disable MPI/CHAI in any way
- DO NOT remove or modify MPI-related code paths, headers, or link flags
- Keep all MPI collective operations (MPI_Allreduce, MPI_Barrier, etc.) intact"""

# =============================================================================
# Profiling tool descriptions
# =============================================================================

PROFILING_DESCRIPTION = """\
PROFILING TOOLS AVAILABLE (run as bash commands):
- nsys_profile: System-wide GPU timeline profiling with Nsight Systems (identifies hotspot kernels, memory transfers, MPI overhead)
  Usage: nsys_profile <executable> <output_dir> [<app_args>...]
  Use this FIRST to find which kernels take the most time.
- ncu_profile: Per-kernel GPU profiling with Nsight Compute (SM%, DRAM%, occupancy, registers)
  Usage: ncu_profile <executable> <output_dir> [<kernel_filter>] [<app_args>...]
  Use this AFTER nsys_profile to deep-dive into the top hotspot kernel(s).
- hpc_profile: Run HPCToolkit profiling to collect GPU/CPU performance data
- hatchet_analyze: Analyze HPCToolkit profiles using Hatchet (call tree, hot paths)
  Use hpc_profile + hatchet_analyze for hierarchical call-tree analysis — especially useful when nsys/ncu flat summaries don't reveal the bottleneck.
- compiler_analysis: Static analysis of compiler optimization opportunities
- gpu_info: Show GPU hardware information (A100 specs, memory, compute capability)
- cpu_info: Show CPU hardware information

TIP: If one profiling approach isn't yielding actionable insights, try a different tool. Each tool provides a different view of performance."""

NO_PROFILING_NOTE = """\
NOTE: You do NOT have profiling tools available. Optimize based on code analysis and HPC best practices."""

# =============================================================================
# Framework-specific completion instructions
# =============================================================================

COMPLETION_INSTRUCTIONS = {
    "sweagent": "When you have made improvements and verified correctness, call the submit command.",
    "opencode": "When you have made improvements and verified correctness, stop working. Ensure all file changes are saved.",
    "openhands": "When you have made improvements and verified correctness, call the finish command to signal completion.",
    "codex": "When you have made improvements and verified correctness, stop working. Ensure all file changes are saved.",
    "claude": "When you have made improvements and verified correctness, stop working. Ensure all file changes are saved.",
}

# =============================================================================
# Codex-specific shell timeout guidance
# =============================================================================

CODEX_TIMEOUT_GUIDANCE = """\
CRITICAL - SHELL COMMAND TIMEOUT:
The default shell command timeout is 10 seconds. The benchmark commands ({run_cmd}, {build_cmd})
take 60-120 seconds to complete. You MUST set timeout_ms to 300000 (5 minutes) when executing
these commands to prevent premature timeout. Example:
  Set timeout_ms: 300000 in your shell tool call for {run_cmd} and {build_cmd}.
If a command returns with no output and null exit code, it was killed by timeout.
Retry with timeout_ms: 300000."""

# =============================================================================
# Per-app direct mode build instructions
# =============================================================================

DIRECT_BUILD_INSTRUCTIONS = {
    "kripke": """\
BUILD INSTRUCTIONS (you must build manually — no build harness):
  mkdir -p build && cd build
  cmake .. -DCMAKE_BUILD_TYPE=Release \\
    -DENABLE_CUDA=ON -DENABLE_MPI=ON \\
    -DCMAKE_CUDA_ARCHITECTURES=80 \\
    -DCMAKE_CUDA_FLAGS="--extended-lambda --expt-relaxed-constexpr" \\
    -DCMAKE_CUDA_HOST_COMPILER=g++-12 \\
    -DCMAKE_CXX_COMPILER=mpicxx -DCMAKE_C_COMPILER=mpicc
  make -j8
The executable will be at build/bin/kripke.exe or build/kripke.exe.
Use kripke_run --arch CUDA for validation and timing only.""",

    "laghos": """\
BUILD INSTRUCTIONS (you must build manually — no build harness):
  export OMPI_CXX=g++-12
  make pcuda -j8
This builds with MFEM+CUDA. Dependencies (mfem, hypre, metis) are in sibling directories.
Use laghos_run for validation and timing only.""",

    "lulesh": """\
BUILD INSTRUCTIONS (you must build manually — no build harness):
  cd cuda/
  make -j8
The active Makefile is cuda/Makefile (NOT cuda/build/Makefile.CRAY, which is legacy).
It uses nvcc with --compiler-bindir=g++-12 and sm_80. Source files are in cuda/src/.
Use lulesh_run for validation and timing only.""",

    "quicksilver": """\
BUILD INSTRUCTIONS (you must build manually — no build harness):
  cd src/
  make -j8 CXX=nvcc \\
    CXXFLAGS="-DHAVE_CUDA -std=c++11 -O3 -gencode=arch=compute_80,code=sm_80 --compiler-bindir=g++-12 -Xcompiler -fopenmp" \\
    CPPFLAGS="-x cu -dc -DHAVE_OPENMP -DHAVE_MPI $(mpicxx --showme:compile)" \\
    LDFLAGS="-lcudart -lcuda -lgomp $(mpicxx --showme:link)"
The executable will be at src/qs.
Use qs_run for validation and timing only.""",
}


# =============================================================================
# Main prompt builder (LLNL proxy apps)
# =============================================================================

def build_prompt(
    framework: str,
    repo_name: str,
    workspace: str,
    profiling: str = "no_profiling",
    build_mode: str = "harness",
) -> str:
    """Build the complete optimization task prompt for any framework.

    Args:
        framework: "sweagent", "opencode", "openhands", "codex", or "claude"
        repo_name: "kripke", "laghos", "lulesh", or "quicksilver"
        workspace: Absolute path to the workspace directory
        profiling: "no_profiling" or "with_profiling"
        build_mode: "harness" (tools handle build) or "direct" (agent builds manually)

    Returns:
        Complete prompt string ready for the framework's CLI.
    """
    tools = APP_TOOLS[repo_name]
    completion = COMPLETION_INSTRUCTIONS.get(framework, COMPLETION_INSTRUCTIONS["opencode"])

    # --- 1. ROLE + AUTONOMY DIRECTIVE ---
    role_section = AUTONOMY_DIRECTIVE
    if framework in ("codex", "claude"):
        role_section += "\n\n" + NON_INTERACTIVE_DIRECTIVE

    # --- 2. BUILD TARGET + ESSENTIAL FLAGS + MPI CONSTRAINT ---
    build_section = f"""{BUILD_TARGET}

{ESSENTIAL_FLAGS[repo_name]}

{MPI_RUNTIME_GUIDANCE}

{CHANGE_RULES}"""

    # --- 3. TASK + WORKSPACE ---
    task_section = f"""\
TASK: Optimize the runtime performance of {APP_DESCRIPTIONS[repo_name]}.
The application source code is in {workspace}."""

    # --- 4. WORKFLOW ---
    workflow_lines = []
    step = 1

    # First: build and get baseline
    if build_mode == "harness":
        workflow_lines.append(f"{step}. Run {tools['run']} --baseline-only to get a baseline measurement BEFORE making any changes")
    else:
        workflow_lines.append(f"{step}. Build the application (see BUILD INSTRUCTIONS below) and run {tools['run']} --baseline-only for baseline")
    step += 1

    # Profiling step (if available)
    if profiling == "with_profiling":
        workflow_lines.append(f"{step}. Profile with nsys_profile / ncu_profile / hpc_profile to identify hotspots")
        step += 1

    workflow_lines.append(f"{step}. Explore the code and identify optimization opportunities")
    step += 1
    workflow_lines.append(f"{step}. Edit source files (and/or build config) to optimize performance")
    step += 1

    if build_mode == "harness":
        workflow_lines.append(f"{step}. {tools['build']} — REBUILD after every edit (changes have NO effect until rebuilt)")
    else:
        workflow_lines.append(f"{step}. Rebuild (changes have NO effect until rebuilt)")
    step += 1

    workflow_lines.append(f"{step}. {tools['run']} — measure improvement AND verify correctness")
    step += 1
    workflow_lines.append(f"{step}. If no improvement, revert and try a different approach")
    step += 1

    # Framework-specific final step
    if framework == "sweagent":
        workflow_lines.append(f"{step}. submit — when done with improvements")
    elif framework == "openhands":
        workflow_lines.append(f"{step}. finish — when done with improvements")

    workflow = "\n".join(workflow_lines)

    # --- 5. TOOLS (harness) or BUILD INSTRUCTIONS (direct) ---
    if build_mode == "harness":
        tools_section = f"""\
TOOLS (already in PATH):
- {tools['build']} — build the application (rebuilds after source changes)
- {tools['run']} — run benchmark, check correctness, and report speedup vs baseline
- If build fails: {tools['build'].split()[0]} --clean {'--arch CUDA ' if repo_name == 'kripke' else ''}for a clean rebuild"""
    else:
        tools_section = f"""\
{DIRECT_BUILD_INSTRUCTIONS[repo_name]}

VALIDATION TOOL (in PATH):
- {tools['run']} — run benchmark, check correctness, and report speedup vs baseline"""

    # Profiling tools
    if profiling == "with_profiling":
        tools_section += "\n\n" + PROFILING_DESCRIPTION
    else:
        tools_section += "\n\n" + NO_PROFILING_NOTE

    # --- 6. COMPLETION ---
    # Already captured in `completion`

    # --- Codex-specific timeout guidance ---
    codex_section = ""
    if framework == "codex":
        codex_section = "\n\n" + CODEX_TIMEOUT_GUIDANCE.format(
            run_cmd=tools["run"],
            build_cmd=tools["build"],
        )

    # --- Assemble prompt ---
    prompt = f"""\
{role_section}

{build_section}

{task_section}

WORKFLOW:
{workflow}

{tools_section}

{completion}{codex_section}"""

    return prompt


# =============================================================================
# SWE-agent prompt builder (system + instance templates)
# =============================================================================

# Per-app key source files for SWE-agent instance_template
APP_KEY_FILES = {
    "kripke": "src/Kripke/Kernel/*.cpp, src/Kripke/Arch/*.h, but any file is fair game",
    "laghos": "laghos.cpp, laghos_solver.cpp, laghos_assembly.cpp",
    "lulesh": "cuda/src/lulesh.cu, cuda/src/allocator.cu",
    "quicksilver": "src/*.cc, src/*.hh",
}

# Per-app file editing guidance for SWE-agent system_template
APP_EDITING_GUIDANCE = {
    "kripke": (
        "- The baseline already builds with -O3 (CMAKE_BUILD_TYPE=Release). "
        "You CAN modify CMakeLists.txt and source code."
    ),
    "laghos": (
        "- The baseline already builds with -O3 via MFEM's config. "
        "You CAN modify the Makefile, CMakeLists.txt, and source code."
    ),
    "lulesh": (
        "- The baseline already builds with -O3 -arch=sm_80. "
        "You CAN modify the Makefile and source code.\n"
        "- NOTE: The active Makefile is cuda/Makefile (NOT cuda/build/Makefile.CRAY, which is legacy and unused)."
    ),
    "quicksilver": (
        "- NOTE: The Makefile's CXXFLAGS are for an AMD HIP target and are NOT used by the build harness. "
        "The harness already builds with -O3 -arch=sm_80. Do NOT waste time changing -g to -O3 — it has no effect. "
        "You CAN modify the Makefile and source code."
    ),
}

# Per-app primary focus files for system_template
APP_PRIMARY_FOCUS = {
    "kripke": None,  # Kripke uses a broader scope message instead
    "laghos": "laghos.cpp, laghos_solver.cpp, laghos_assembly.cpp",
    "lulesh": "cuda/src/lulesh.cu, cuda/src/allocator.cu",
    "quicksilver": "src/*.cc and src/*.hh source files",
}


def build_sweagent_prompts(
    repo_name: str,
    workspace: str,
    profiling: str = "no_profiling",
    build_mode: str = "harness",
) -> dict:
    """Build SWE-agent system_template and instance_template from shared constants.

    Args:
        repo_name: "kripke", "laghos", "lulesh", or "quicksilver"
        workspace: Absolute path (will use {{working_dir}} Jinja2 variable)
        profiling: "no_profiling" or "with_profiling"
        build_mode: "harness" (tools handle build) or "direct" (agent builds manually)

    Returns:
        Dict with "system_template" and "instance_template" strings.
    """
    tools = APP_TOOLS[repo_name]
    build_cmd = tools["build"]
    run_cmd = tools["run"]
    build_base = build_cmd.split()[0]  # e.g., "kripke_build"

    # ── system_template ──────────────────────────────────────────────
    # SWE-agent's system_template is the agent's persistent identity.
    # Keep it focused on rules, not task details.

    arch_section = ""
    if repo_name == "kripke":
        arch_section = """
CRITICAL ARCHITECTURE REQUIREMENT:
- You are optimizing for NVIDIA A100 GPUs
- The application is PRE-BUILT with CUDA for A100 GPUs. Run {run_cmd} --baseline-only first to get a baseline measurement before making any changes.
- You MUST use --arch CUDA for ALL {build_base} and {run_base} commands
- Do NOT use --arch OpenMP or --arch Sequential - these are CPU backends and will not test GPU performance
""".format(run_cmd=run_cmd, build_base=build_cmd.split()[0],
           run_base=run_cmd.split()[0])
    else:
        arch_section = f"""
CRITICAL BUILD REQUIREMENT:
- The application is PRE-BUILT with CUDA for A100 GPUs. Run {run_cmd} --baseline-only first to get a baseline measurement before making any changes."""

    # Build requirement section (depends on build mode)
    if build_mode == "direct":
        build_req = f"""
- You MUST rebuild after EVERY source code edit before testing
- Source changes have NO effect until you rebuild
- Do NOT skip rebuilding - your changes will not be applied otherwise
- See BUILD INSTRUCTIONS below for how to compile"""
    else:
        build_req = f"""
- You MUST run {build_cmd} after EVERY source code edit before testing
- Source changes have NO effect until you rebuild
- Do NOT skip rebuilding - your changes will not be applied otherwise
- If the build fails, call {build_base} --clean{' --arch CUDA' if repo_name == 'kripke' else ''} for a clean rebuild. Do NOT try to fix build issues manually."""

    # File editing guidance
    primary_focus = APP_PRIMARY_FOCUS[repo_name]
    if primary_focus:
        editing = f"""
FILE EDITING GUIDANCE:
- Primary focus: {primary_focus}
{APP_EDITING_GUIDANCE[repo_name]}
- Do NOT disable CUDA/GPU support - the goal is GPU performance optimization"""
    else:
        # Kripke uses broader "optimization scope" instead
        editing = f"""
{APP_EDITING_GUIDANCE[repo_name]}

OPTIMIZATION SCOPE:
- Explore the ENTIRE repository for optimization opportunities
- Consider algorithmic improvements, data structure changes, memory layouts, etc.
- Any valid performance optimization is welcome - not just GPU-specific changes
- The key requirement is that you TEST with --arch CUDA to measure GPU performance"""

    system_template = f"""\
You are an autonomous agent that can interact with a computer to solve performance optimization tasks.
{arch_section}{build_req}

{MPI_RUNTIME_GUIDANCE}
{editing}

SUBMISSION:
When you have made improvements and verified correctness, call the submit command.
Reasoning: high"""

    # ── instance_template ────────────────────────────────────────────
    # SWE-agent's instance_template is the per-task prompt with {{working_dir}}.

    # Workflow steps
    workflow_lines = []
    step = 1
    if build_mode == "direct":
        workflow_lines.append(f"{step}. Build the application (see BUILD INSTRUCTIONS below) and run {run_cmd} --baseline-only for baseline")
    else:
        workflow_lines.append(f"{step}. {run_cmd} --baseline-only - Get baseline timing BEFORE making any changes")
    step += 1
    if profiling == "with_profiling":
        workflow_lines.append(f"{step}. nsys_profile / ncu_profile / hpc_profile - Profile to identify hotspots")
        step += 1
    if repo_name == "kripke":
        workflow_lines.append(f"{step}. Explore the repository to understand the codebase and identify optimization opportunities")
    else:
        workflow_lines.append(f"{step}. Analyze source code for bottlenecks ({APP_KEY_FILES[repo_name].split(', but')[0]})")
    step += 1
    workflow_lines.append(f"{step}. Edit source files to optimize")
    step += 1
    if build_mode == "direct":
        workflow_lines.append(f"{step}. Rebuild (changes have NO effect until rebuilt)")
    else:
        workflow_lines.append(f"{step}. {build_cmd} - REBUILD (required after every edit!)")
    step += 1
    workflow_lines.append(f"{step}. {run_cmd} - Measure improvement AND verify correctness")
    step += 1
    workflow_lines.append(f"{step}. submit - When done with improvements")
    workflow = "\n".join(workflow_lines)

    # Notes
    notes = [
        f"NOTE: {run_cmd.split()[0]} automatically checks BOTH timing AND correctness - no separate correctness check needed!",
    ]
    if profiling == "with_profiling":
        profiling_tools = "nsys_profile, ncu_profile, hpc_profile, hatchet_analyze, compiler_analysis, gpu_info, cpu_info"
        notes.append(f"\nPROFILING TOOLS AVAILABLE: {profiling_tools}")
    else:
        notes.append(f"\n{NO_PROFILING_NOTE}")

    # Optimization scope for instance
    if repo_name == "kripke":
        scope = f"""
OPTIMIZATION SCOPE:
- Explore the entire repository for optimization opportunities
- PRIORITIZE source code changes over compiler flags:
  * Algorithmic improvements (reduce computational complexity)
  * Data structure optimizations (memory layout, cache efficiency)
  * Loop transformations (blocking, tiling, fusion)
  * Parallelization improvements (better work distribution)
- Compiler flag changes are acceptable but should NOT be your only optimization
- Key files: {APP_KEY_FILES[repo_name]}"""
    else:
        scope = f"""
SCOPE: Focus on the specific areas mentioned. Do NOT modify unrelated code.

FILES TO EDIT: {APP_KEY_FILES[repo_name]}"""

    # Kripke-specific critical note
    if repo_name == "kripke":
        if build_mode == "direct":
            critical = """
CRITICAL:
- Always use --arch CUDA (not OpenMP!) for runs
- Always rebuild after editing source files!
- If a build fails, carefully analyze the error before making changes
- Do NOT add flags like -fno-exceptions or -fno-rtti (breaks RAJA/CAMP)"""
        else:
            critical = """
CRITICAL:
- Always use --arch CUDA (not OpenMP!) for builds and runs
- Always rebuild with kripke_build --arch CUDA after editing source files!
- If a build fails, carefully analyze the error before making changes
- Do NOT add flags like -fno-exceptions or -fno-rtti (breaks RAJA/CAMP)"""
    else:
        if build_mode == "direct":
            critical = "\nCRITICAL: Always rebuild after editing source files!"
        else:
            critical = f"\nCRITICAL: Always rebuild with {build_cmd} after editing source files!"

    # Build instructions section for direct mode
    build_instructions = ""
    if build_mode == "direct" and repo_name in DIRECT_BUILD_INSTRUCTIONS:
        build_instructions = f"\n\n{DIRECT_BUILD_INSTRUCTIONS[repo_name]}"

    instance_template = f"""\
<uploaded_files>
{{{{working_dir}}}}
</uploaded_files>

TASK: Optimize the runtime performance of {APP_DESCRIPTIONS[repo_name]}.

The application is in {{{{working_dir}}}}.
{"" if repo_name != "kripke" else '''
IMPORTANT: You are optimizing for NVIDIA A100 GPUs.
You MUST use --arch CUDA for all builds and runs. Do NOT use OpenMP or Sequential.
'''}
WORKFLOW:
{workflow}

{"".join(notes)}
{scope}
{critical}{build_instructions}

Thinking should be thorough."""

    return {
        "system_template": system_template,
        "instance_template": instance_template,
    }


# =============================================================================
# GPA prompt builder (CUDA kernel optimization)
# =============================================================================

def build_gpa_prompt(
    framework: str,
    workspace: str,
    gpa_app_name: str,
    kernel_file: str,
    kernel_name: str,
    kernel_source: str,
    profiling: str = "no_profiling",
    build_mode: str = "harness",
) -> str:
    """Build prompt for GPA benchmark CUDA kernel optimization.

    Args:
        framework: "sweagent", "opencode", "openhands", "codex", or "claude"
        workspace: Absolute path to the workspace directory
        gpa_app_name: Name of the GPA app (e.g., "gaussian")
        kernel_file: Relative path to kernel file (e.g., "rodinia/gaussian/gaussian.cu")
        kernel_name: Name of the target kernel function (e.g., "Fan2")
        kernel_source: The actual kernel source code
        profiling: "no_profiling" or "with_profiling"
        build_mode: "harness" or "direct" (GPA always uses gpa_test for build+validation)

    Returns:
        Complete prompt string.
    """
    from pathlib import Path
    kernel_basename = Path(kernel_file).name
    completion = COMPLETION_INSTRUCTIONS.get(framework, COMPLETION_INSTRUCTIONS["opencode"])

    # Role + autonomy directive
    role_section = AUTONOMY_DIRECTIVE
    if framework in ("codex", "claude"):
        role_section += "\n\n" + NON_INTERACTIVE_DIRECTIVE

    # Build tool description based on profiling config
    if profiling == "with_profiling":
        tools_section = f"""\
TOOLS AVAILABLE (run as bash commands):
- gpa_test: Build, run, validate, and time your optimization. Reports speedup vs baseline.
  Usage: gpa_test (auto-detects app from metadata)
- ncu_profile: Per-kernel GPU profiling with Nsight Compute (SM%, DRAM%, occupancy, registers)
  Usage: ncu_profile <executable> <output_dir> [<kernel_filter>]
- nsys_profile: System-wide GPU timeline profiling with Nsight Systems
  Usage: nsys_profile <executable> <output_dir> [<app_args>...]
- compiler_analysis: Analyze register usage, shared memory, occupancy of your .cu file.
  Usage: compiler_analysis {kernel_basename}
- microbench_code: Compile and time a standalone .cu file in isolation.

WORKFLOW:
1. Read the kernel code and understand it
2. Run compiler_analysis on the kernel to check register count and occupancy
3. Optionally use ncu_profile on the built executable to see SM/DRAM utilization and bottleneck type
4. Identify performance bottlenecks
5. Edit the kernel file to optimize it
6. Run gpa_test to verify correctness and measure speedup
7. Iterate if needed"""
    else:
        tools_section = f"""\
TOOLS AVAILABLE (run as bash commands):
- gpa_test: Build, run, validate, and time your optimization. Reports speedup vs baseline.
  Usage: gpa_test (auto-detects app from metadata)

WORKFLOW:
1. Read the kernel code and understand it
2. Identify performance bottlenecks
3. Edit the kernel file to optimize it
4. Run gpa_test to verify correctness and measure speedup
5. Iterate if needed"""

    # Codex-specific timeout guidance
    codex_section = ""
    if framework == "codex":
        codex_section = """\

CRITICAL - SHELL COMMAND TIMEOUT:
gpa_test takes 30-120 seconds. Set timeout_ms to 300000 (5 minutes) for this command."""

    prompt = f"""\
{role_section}

TASK: Optimize the CUDA kernel in {kernel_basename} for better GPU performance on NVIDIA A100 GPUs.

The kernel to optimize is `{kernel_name}`.

The workspace is at {workspace}. Your kernel file is at {workspace}/{kernel_basename}.

KERNEL SOURCE CODE:
```cuda
{kernel_source}
```

{tools_section}

CONSTRAINTS:
- The optimized kernel MUST produce correct results (same output as the original)
- Do not change the kernel function signature
- Do not modify host code (main function, I/O, etc.) unless necessary for the optimization
- Keep all #include directives and external dependencies unchanged

{completion}{codex_section}"""

    return prompt
