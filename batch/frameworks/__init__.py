"""Framework launcher factory for multi-framework HPC benchmarks."""

from pathlib import Path
from typing import Optional

from batch.frameworks.base import FrameworkLauncher


def get_launcher(
    framework: str,
    sweagent_root: Path,
    vllm_host: str = "127.0.0.1",
    vllm_port: int = 8008,
    model_name: Optional[str] = None,
    profiling: str = "no_profiling",
    build_mode: str = "harness",
) -> FrameworkLauncher:
    """Create a framework-specific launcher instance.

    Args:
        framework: One of "sweagent", "opencode", "openhands", "codex", "claude"
        sweagent_root: Root directory of the SWE-agent project
        vllm_host: vLLM server hostname
        vllm_port: vLLM server port
        model_name: Optional model name override (for external APIs)
        profiling: "no_profiling" or "with_profiling"
        build_mode: "harness" or "direct"

    Returns:
        FrameworkLauncher subclass instance
    """
    kwargs = dict(
        sweagent_root=sweagent_root,
        vllm_host=vllm_host,
        vllm_port=vllm_port,
        model_name=model_name,
        profiling=profiling,
        build_mode=build_mode,
    )

    if framework == "sweagent":
        from batch.frameworks.sweagent import SweAgentLauncher
        return SweAgentLauncher(**kwargs)
    elif framework == "opencode":
        from batch.frameworks.opencode import OpenCodeLauncher
        return OpenCodeLauncher(**kwargs)
    elif framework == "openhands":
        from batch.frameworks.openhands import OpenHandsLauncher
        return OpenHandsLauncher(**kwargs)
    elif framework == "codex":
        from batch.frameworks.codex import CodexLauncher
        return CodexLauncher(**kwargs)
    elif framework == "claude":
        from batch.frameworks.claude import ClaudeCodeLauncher
        return ClaudeCodeLauncher(**kwargs)
    else:
        raise ValueError(
            f"Unknown framework: {framework}. "
            f"Valid options: sweagent, opencode, openhands, codex, claude"
        )
