"""Shared prompt templates for all frameworks.

Extracts the core task content from SWE-agent YAML configs into
framework-neutral templates, then applies per-framework adaptations
(tool names, completion signals, profiling tool descriptions).
"""

# =============================================================================
# Per-app system context (architecture/build requirements)
# =============================================================================

SYSTEM_CONTEXT = {
    "kripke": """\
CRITICAL ARCHITECTURE REQUIREMENT:
- You are optimizing for NVIDIA A100 GPUs
- The application is PRE-BUILT with CUDA for A100 GPUs. Run kripke_run --arch CUDA first to get a baseline measurement before making any changes.
- You MUST use --arch CUDA for ALL kripke_build and kripke_run commands
- Do NOT use --arch OpenMP or --arch Sequential - these are CPU backends and will not test GPU performance

CRITICAL BUILD REQUIREMENT:
- You MUST run kripke_build --arch CUDA after EVERY source code edit before testing
- Source changes have NO effect until you rebuild
- Do NOT skip rebuilding - your changes will not be applied otherwise
- Do NOT edit CMakeLists.txt or build configuration. The build harness handles all compiler flags and CUDA setup. Focus ONLY on optimizing source code (.cpp, .h files).
- If the build fails, call kripke_build --clean --arch CUDA for a clean rebuild. Do NOT try to fix build issues manually.

FORBIDDEN ACTIONS (will break the build permanently):
- NEVER delete, rename, or move any Makefile, CMakeLists.txt, or build configuration file
- NEVER delete or rewrite entire source files — make targeted edits only
- NEVER remove #include directives, class definitions, or function signatures that other files depend on
- NEVER disable or remove CUDA/GPU code paths
- Keep changes small and incremental. Test after EVERY edit.

OPTIMIZATION SCOPE:
- Explore the ENTIRE repository for optimization opportunities
- Consider algorithmic improvements, data structure changes, memory layouts, etc.
- Any valid performance optimization is welcome - not just GPU-specific changes
- The key requirement is that you TEST with --arch CUDA to measure GPU performance""",

    "laghos": """\
CRITICAL BUILD REQUIREMENT:
- The application is PRE-BUILT with CUDA for A100 GPUs. Run laghos_run first to get a baseline measurement before making any changes.
- You MUST run laghos_build after EVERY source code edit before testing
- Source changes have NO effect until you rebuild
- Do NOT skip rebuilding - your changes will not be applied otherwise
- If the build fails, call laghos_build --clean for a clean rebuild. Do NOT try to fix build issues manually.

FILE EDITING GUIDANCE:
- Primary focus: laghos.cpp, laghos_solver.cpp, laghos_assembly.cpp
- Do NOT edit Makefiles, CMakeLists.txt, or build configuration. The build harness handles all compiler flags and CUDA setup. Focus ONLY on optimizing source code (.cpp, .cu, .cc, .hh files).
- Do NOT disable CUDA/GPU support - the goal is GPU performance optimization

FORBIDDEN ACTIONS (will break the build permanently):
- NEVER delete, rename, or move any Makefile, CMakeLists.txt, or build configuration file
- NEVER delete or rewrite entire source files — make targeted edits only
- NEVER remove #include directives, class definitions, or function signatures that other files depend on
- NEVER disable or remove CUDA/GPU code paths
- Keep changes small and incremental. Test after EVERY edit.""",

    "lulesh": """\
CRITICAL BUILD REQUIREMENT:
- The application is PRE-BUILT with CUDA for A100 GPUs. Run lulesh_run first to get a baseline measurement before making any changes.
- You MUST run lulesh_build after EVERY source code edit before testing
- Source changes have NO effect until you rebuild
- Do NOT skip rebuilding - your changes will not be applied otherwise
- If the build fails, call lulesh_build --clean for a clean rebuild. Do NOT try to fix build issues manually.

FILE EDITING GUIDANCE:
- Primary focus: cuda/src/lulesh.cu, cuda/src/allocator.cu
- Do NOT edit Makefiles or build configuration. The build harness handles all compiler flags and CUDA setup. Focus ONLY on optimizing source code (.cu, .cpp files).
- Do NOT disable CUDA/GPU support - the goal is GPU performance optimization

FORBIDDEN ACTIONS (will break the build permanently):
- NEVER delete, rename, or move any Makefile, CMakeLists.txt, or build configuration file
- NEVER delete or rewrite entire source files — make targeted edits only
- NEVER remove #include directives, class definitions, or function signatures that other files depend on
- NEVER disable or remove CUDA/GPU code paths
- Keep changes small and incremental. Test after EVERY edit.""",

    "quicksilver": """\
CRITICAL BUILD REQUIREMENT:
- The application is PRE-BUILT with CUDA for A100 GPUs. Run qs_run first to get a baseline measurement before making any changes.
- You MUST run qs_build after EVERY source code edit before testing
- Source changes have NO effect until you rebuild
- Do NOT skip rebuilding - your changes will not be applied otherwise
- If the build fails, call qs_build --clean for a clean rebuild. Do NOT try to fix build issues manually.

FILE EDITING GUIDANCE:
- Primary focus: src/*.cc and src/*.hh source files
- Do NOT edit Makefiles or build configuration. The build harness always overrides CXX and CXXFLAGS. Makefile edits to compiler settings have no effect. Focus ONLY on optimizing source code (.cc, .hh files).
- Do NOT disable CUDA/GPU support - the goal is GPU performance optimization

FORBIDDEN ACTIONS (will break the build permanently):
- NEVER delete, rename, or move any Makefile, CMakeLists.txt, or build configuration file
- NEVER delete or rewrite entire source files — make targeted edits only
- NEVER remove #include directives, class definitions, or function signatures that other files depend on
- NEVER disable or remove CUDA/GPU code paths
- Keep changes small and incremental. Test after EVERY edit.""",
}

# =============================================================================
# Per-app task descriptions (the core optimization task)
# =============================================================================

APP_DESCRIPTIONS = {
    "kripke": "the Kripke 3D Sn deterministic transport application",
    "laghos": "the Laghos high-order Lagrangian hydrodynamics application",
    "lulesh": "the LULESH shock hydrodynamics proxy application",
    "quicksilver": "the Quicksilver Monte Carlo particle transport application",
}

# =============================================================================
# Per-app workflow steps (build/run tool names)
# =============================================================================

APP_TOOLS = {
    "kripke": {"build": "kripke_build --arch CUDA", "run": "kripke_run --arch CUDA"},
    "laghos": {"build": "laghos_build", "run": "laghos_run"},
    "lulesh": {"build": "lulesh_build", "run": "lulesh_run"},
    "quicksilver": {"build": "qs_build", "run": "qs_run"},
}

# =============================================================================
# Per-app additional notes
# =============================================================================

APP_NOTES = {
    "kripke": """\
NOTE: kripke_run automatically checks BOTH timing AND correctness - no separate correctness check needed!

OPTIMIZATION SCOPE:
- Explore the entire repository for optimization opportunities
- PRIORITIZE source code changes over compiler flags:
  * Algorithmic improvements (reduce computational complexity)
  * Data structure optimizations (memory layout, cache efficiency)
  * Loop transformations (blocking, tiling, fusion)
  * Parallelization improvements (better work distribution)
- Compiler flag changes are acceptable but should NOT be your only optimization
- Key files: src/Kripke/Kernel/*.cpp, src/Kripke/Arch/*.h, but any file is fair game

CRITICAL:
- Always use --arch CUDA (not OpenMP!) for builds and runs
- Always rebuild with kripke_build --arch CUDA after editing source files!
- If a build fails, carefully analyze the error before making changes
- Do NOT add flags like -fno-exceptions or -fno-rtti (breaks RAJA/CAMP)""",

    "laghos": """\
NOTE: laghos_run uses a Sedov blast benchmark for consistent results.
It automatically checks BOTH timing AND correctness - no separate check needed!
Each laghos_run takes ~60-120 seconds (runs baseline + modified version).

SCOPE: Focus on the specific areas mentioned. Do NOT modify unrelated code.

FILES TO EDIT: laghos.cpp, laghos_solver.cpp, laghos_assembly.cpp

CRITICAL: Always rebuild with laghos_build after editing source files!""",

    "lulesh": """\
NOTE: lulesh_run uses a standard benchmark for consistent results.
It automatically checks BOTH timing AND correctness - no separate check needed!
Each lulesh_run takes ~60 seconds (runs baseline + modified version).

SCOPE: Focus on the specific areas mentioned. Do NOT modify unrelated code.

FILES TO EDIT: cuda/src/lulesh.cu, cuda/src/allocator.cu

CRITICAL: Always rebuild with lulesh_build after editing source files!""",

    "quicksilver": """\
NOTE: qs_run uses a fixed benchmark (Coral2_P2_1) for consistent results.
It automatically checks BOTH timing AND correctness - no separate check needed!
Each qs_run takes ~100 seconds (runs baseline + modified version).

SCOPE: Focus on the specific areas mentioned. Do NOT modify unrelated code.

FILES TO EDIT: src/*.cc, src/*.hh

CRITICAL: Always rebuild with qs_build after editing source files!""",
}

# =============================================================================
# Profiling tool descriptions (appended when profiling == "with_profiling")
# =============================================================================

PROFILING_DESCRIPTION = """\
PROFILING TOOLS AVAILABLE (run as bash commands):
- hpc_profile: Run HPCToolkit profiling to collect GPU/CPU performance data
- hatchet_analyze: Analyze HPCToolkit profiles using Hatchet (call tree, hot paths)
- compiler_analysis: Static analysis of compiler optimization opportunities
- gpu_info: Show GPU hardware information (A100 specs, memory, compute capability)
- cpu_info: Show CPU hardware information

RECOMMENDED PROFILING WORKFLOW:
1. Build and run baseline first
2. Run hpc_profile to collect performance data
3. Run hatchet_analyze to identify hotspots
4. Use profiling insights to guide your optimizations"""

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
# Main prompt builder
# =============================================================================

def build_prompt(
    framework: str,
    repo_name: str,
    workspace: str,
    profiling: str = "no_profiling",
) -> str:
    """Build the complete optimization task prompt for any framework.

    Args:
        framework: "sweagent", "opencode", "openhands", or "codex"
        repo_name: "kripke", "laghos", "lulesh", or "quicksilver"
        workspace: Absolute path to the workspace directory
        profiling: "no_profiling" or "with_profiling"

    Returns:
        Complete prompt string ready for the framework's CLI.
    """
    tools = APP_TOOLS[repo_name]
    completion = COMPLETION_INSTRUCTIONS.get(framework, COMPLETION_INSTRUCTIONS["opencode"])

    # Build profiling section
    if profiling == "with_profiling":
        profiling_section = PROFILING_DESCRIPTION
        workflow_profiling_step = "3. Profile with hpc_profile / hatchet_analyze to identify hotspots\n"
        step_offset = 1
    else:
        profiling_section = NO_PROFILING_NOTE
        workflow_profiling_step = ""
        step_offset = 0

    # Build workflow steps with correct numbering
    step = 1
    workflow_lines = [f"{step}. {tools['build']} - Build the application"]
    step += 1
    workflow_lines.append(f"{step}. {tools['run']} - Run to measure current performance AND verify correctness")
    step += 1
    if workflow_profiling_step:
        workflow_lines.append(f"{step}. Profile with hpc_profile / hatchet_analyze to identify hotspots")
        step += 1
    workflow_lines.append(f"{step}. Explore the repository and identify optimization opportunities")
    step += 1
    workflow_lines.append(f"{step}. Edit source files to optimize performance")
    step += 1
    workflow_lines.append(f"{step}. {tools['build']} - REBUILD (required after every edit!)")
    step += 1
    workflow_lines.append(f"{step}. {tools['run']} - Measure improvement AND verify correctness")
    step += 1

    # Framework-specific final step
    if framework == "sweagent":
        workflow_lines.append(f"{step}. submit - When done with improvements")
    elif framework == "openhands":
        workflow_lines.append(f"{step}. finish - When done with improvements")
    # opencode/codex: no explicit final step — they just stop

    workflow = "\n".join(workflow_lines)

    # Codex-specific timeout guidance
    codex_section = ""
    if framework == "codex":
        codex_section = CODEX_TIMEOUT_GUIDANCE.format(
            run_cmd=tools["run"],
            build_cmd=tools["build"],
        )

    # Assemble the prompt
    prompt = f"""\
You are an autonomous agent tasked with optimizing HPC application performance.

{SYSTEM_CONTEXT[repo_name]}

{completion}

TASK: Optimize the runtime performance of {APP_DESCRIPTIONS[repo_name]}.

The application is in {workspace}.

IMPORTANT: You are optimizing for NVIDIA A100 GPUs.

WORKFLOW:
{workflow}

{profiling_section}

{APP_NOTES[repo_name]}

{codex_section}

Thinking should be thorough."""

    return prompt
