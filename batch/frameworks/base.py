"""Base class for framework-specific agent launchers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import json
import logging
import os
import subprocess
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# OpenAI regional API endpoints — keyed by ISO 3166-1 alpha-2 country code.
# Keys with data-residency-enabled projects MUST use the matching regional
# endpoint; the global api.openai.com returns 401 for such keys.
OPENAI_REGIONAL_ENDPOINTS = {
    "us": "us.api.openai.com",
    "eu": "eu.api.openai.com",
    "gb": "gb.api.openai.com",
    "ae": "ae.api.openai.com",
    "au": "au.api.openai.com",
    "ca": "ca.api.openai.com",
    "jp": "jp.api.openai.com",
    "in": "in.api.openai.com",
    "sg": "sg.api.openai.com",
    "kr": "kr.api.openai.com",
}

# The set of all recognized regional hostnames for quick membership checks.
_REGIONAL_HOSTNAMES = set(OPENAI_REGIONAL_ENDPOINTS.values())


def openai_region_to_base_url(region: str) -> str:
    """Convert a region code (e.g. 'us') to a full OPENAI_API_BASE URL.

    Args:
        region: Two-letter region code (case-insensitive).  Must be one of
            the keys in OPENAI_REGIONAL_ENDPOINTS.

    Returns:
        Full URL suitable for OPENAI_API_BASE, e.g. ``https://us.api.openai.com/v1``.

    Raises:
        ValueError: If the region code is not recognized.
    """
    region = region.lower().strip()
    if region not in OPENAI_REGIONAL_ENDPOINTS:
        valid = ", ".join(sorted(OPENAI_REGIONAL_ENDPOINTS))
        raise ValueError(
            f"Unknown OpenAI region '{region}'. Valid regions: {valid}"
        )
    return f"https://{OPENAI_REGIONAL_ENDPOINTS[region]}/v1"


def validate_openai_base_url(api_base: str) -> str:
    """Validate and warn about OpenAI API base URL configuration.

    Checks the provided ``OPENAI_API_BASE`` value and emits log warnings
    when the URL is the non-regional global endpoint, which will fail for
    API keys bound to a data-residency-enabled project.

    The function never mutates the URL — it only logs diagnostics.

    Args:
        api_base: Current value of the ``OPENAI_API_BASE`` environment variable.
            May be empty/unset (local vLLM setups), a local URL, or an
            OpenAI endpoint.

    Returns:
        The *unchanged* ``api_base`` string.
    """
    if not api_base:
        # Empty/unset — likely a local vLLM or skip-vllm setup. Nothing to check.
        return api_base

    try:
        parsed = urlparse(api_base)
        hostname = (parsed.hostname or "").lower()
    except Exception:
        logger.warning("OPENAI_API_BASE URL could not be parsed: %s", api_base)
        return api_base

    # Local / non-OpenAI URL — no validation needed.
    if not hostname.endswith("api.openai.com"):
        return api_base

    # Already a recognized regional endpoint — great, just confirm.
    if hostname in _REGIONAL_HOSTNAMES:
        region_code = hostname.split(".")[0]
        logger.info(
            "OPENAI_API_BASE is using regional endpoint '%s' (%s). Good.",
            region_code,
            api_base,
        )
        return api_base

    # Global (non-regional) endpoint: api.openai.com
    if hostname == "api.openai.com":
        logger.warning(
            "OPENAI_API_BASE is set to the global endpoint (%s). "
            "If your API key is bound to a data-residency-enabled project "
            "(e.g. US), this will return 401. Use --openai-region <code> or "
            "set OPENAI_API_BASE to a regional endpoint "
            "(e.g. https://us.api.openai.com/v1).",
            api_base,
        )
        return api_base

    # Some other *.api.openai.com subdomain we don't recognize.
    logger.warning(
        "OPENAI_API_BASE hostname '%s' looks like an OpenAI endpoint but is "
        "not a recognized regional endpoint. Proceeding as-is.",
        hostname,
    )
    return api_base


# Harness directory names per app
HARNESS_MAP = {
    "kripke": "kripke_harness",
    "laghos": "laghos_harness",
    "lulesh": "lulesh_harness",
    "quicksilver": "quicksilver_harness",
    "gpa": "gpa_harness",
}

# Profiling tool directories (added to PATH when profiling == "with_profiling")
PROFILING_TOOL_DIRS = [
    "tools/hpctoolkit/bin",
    "tools/hatchet/bin",
    "tools/profiling/bin",
    "tools/system_info/bin",
    "tools/nsight_compute/bin",
    "tools/nsight_systems/bin",
]

# Per-app environment variable name for the app root directory
APP_ROOT_VAR = {
    "kripke": "KRIPKE_ROOT",
    "laghos": "LAGHOS_ROOT",
    "lulesh": "LULESH_ROOT",
    "quicksilver": "QUICKSILVER_ROOT",
}

# Per-app execution timeouts (from SWE-agent configs)
APP_EXECUTION_TIMEOUT = {
    "kripke": 900,
    "laghos": 600,
    "lulesh": 300,
    "quicksilver": 600,
}

# Session timeout for all frameworks (seconds)
SESSION_TIMEOUT = 3600


class FrameworkLauncher(ABC):
    """Base class for framework-specific agent launch logic.

    Subclasses implement config generation, agent launch command building,
    and trajectory file discovery. Shared functionality (patch extraction,
    PATH building, env vars) lives here.
    """

    name: str  # "sweagent", "opencode", "openhands", "codex"

    def __init__(
        self,
        sweagent_root: Path,
        vllm_host: str = "127.0.0.1",
        vllm_port: int = 8008,
        model_name: Optional[str] = None,
        profiling: str = "no_profiling",
        build_mode: str = "harness",
    ):
        self.sweagent_root = sweagent_root
        self.vllm_host = vllm_host
        self.vllm_port = vllm_port
        self.model_name = model_name
        self.profiling = profiling
        self.build_mode = build_mode

    @abstractmethod
    def generate_config(
        self,
        repo_name: str,
        workspace: Path,
        instance_id: str,
        output_dir: Path,
    ) -> Path:
        """Generate framework-specific config file(s).

        Returns path to the primary config file.
        """
        ...

    @abstractmethod
    def build_launch_command(
        self,
        repo_name: str,
        workspace: Path,
        config_path: Path,
        output_dir: Path,
        trajectory_dir: Path,
        instance_id: str,
    ) -> str:
        """Return a shell script string that launches the agent.

        The script should:
        1. Set up the environment (modules, PATH, env vars)
        2. Launch the agent with the given config
        3. Direct output to trajectory_dir
        """
        ...

    @abstractmethod
    def find_trajectory(
        self,
        output_dir: Path,
        trajectory_dir: Path,
        instance_id: str,
    ) -> Optional[str]:
        """Find the trajectory/log file after a run completes.

        Returns absolute path to trajectory file, or None.
        """
        ...

    def extract_patch(self, workspace: Path) -> str:
        """Extract agent's patch from workspace via git diff. Framework-agnostic."""
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        return result.stdout

    def get_harness_bin_path(self, repo_name: str) -> Path:
        """Get absolute path to the harness bin directory for an app."""
        harness_name = HARNESS_MAP.get(repo_name)
        if not harness_name:
            return Path()  # GPA apps have no harness
        return self.sweagent_root / "tools" / harness_name / "bin"

    def get_path_dirs(self, repo_name: str) -> list[str]:
        """Get list of directories to add to PATH for this app and profiling config.

        In direct mode, only the *_run tool is needed (for validation/timing).
        The harness bin dir is still added since it contains the run tool,
        but *_build becomes a no-op that prints a message.
        """
        dirs = []
        if repo_name in HARNESS_MAP:
            if self.build_mode == "direct":
                # In direct mode, use a wrapper dir where *_build is a no-op
                # but the harness bin is still on PATH for the *_run tool
                dirs.append(str(self.get_harness_bin_path(repo_name)))
            else:
                dirs.append(str(self.get_harness_bin_path(repo_name)))
        if self.profiling == "with_profiling":
            for tool_dir in PROFILING_TOOL_DIRS:
                full_path = self.sweagent_root / tool_dir
                if full_path.exists():
                    dirs.append(str(full_path))
        return dirs

    def get_env_exports(self, repo_name: str, workspace: Path) -> str:
        """Generate shell export statements for common environment variables."""
        if repo_name == "gpa":
            path_dirs = self.get_path_dirs(repo_name)
            path_prefix = ":".join(path_dirs) if path_dirs else ""
            lines = []
            if path_prefix:
                lines.append(f'export PATH="{path_prefix}:$PATH"')
            lines.extend([
                f'export SWE_AGENT_ROOT="{self.sweagent_root}"',
                'export GPA_BENCHMARK_ROOT="/pscratch/sd/k/krydzy/GPA-Benchmark"',
                f'export PYTHONPATH="/pscratch/sd/k/krydzy/GPA-Benchmark:$PYTHONPATH"',
                'export CUDA_VISIBLE_DEVICES="0,1,2,3"',
                'export OMP_NUM_THREADS=32',
                'export PYTHONUNBUFFERED=1',
            ])
            return "\n".join(lines)

        root_var = APP_ROOT_VAR[repo_name]
        path_dirs = self.get_path_dirs(repo_name)
        path_prefix = ":".join(path_dirs)

        # Lulesh: LULESH_ROOT must point to cuda/ subdir where Makefile and source live
        app_root = workspace / "cuda" if repo_name == "lulesh" else workspace

        lines = [
            f'export PATH="{path_prefix}:$PATH"',
            f'export {root_var}="{app_root}"',
            f'export SWE_AGENT_ROOT="{self.sweagent_root}"',
            'export CUDA_VISIBLE_DEVICES="0,1,2,3"',
            'export OMP_NUM_THREADS=32',
            # Unbuffered Python output ensures harness scripts flush immediately,
            # critical for Codex which has a 10s per-command timeout.
            'export PYTHONUNBUFFERED=1',
        ]
        return "\n".join(lines)

    def get_api_env_exports(self) -> str:
        """Generate shell export statements for API credentials.

        When using an external model, also runs :func:`validate_openai_base_url`
        to emit diagnostic warnings about the configured endpoint.
        """
        if self.model_name:
            # External model: use env vars passed through from parent
            api_base = os.environ.get("OPENAI_API_BASE", "")
            api_key = os.environ.get("OPENAI_API_KEY", "")
            # Validate / warn about the OpenAI endpoint configuration.
            validate_openai_base_url(api_base)
            return (
                f'export OPENAI_API_BASE="{api_base}"\n'
                f'export OPENAI_API_KEY="{api_key}"'
            )
        else:
            # Local vLLM
            return (
                f'export OPENAI_API_BASE="http://{self.vllm_host}:{self.vllm_port}/v1"\n'
                f'export OPENAI_API_KEY="dummy-key-ok"'
            )

    def get_module_loads(self, repo_name: str = "") -> str:
        """Generate module load commands for HPC environment.

        GPA apps need default CUDA 12.9; LLNL proxy apps need cudatoolkit/12.4.
        """
        lines = ["module load openmpi/5.0.7 2>/dev/null || true"]
        if repo_name == "gpa":
            # GPA apps need default CUDA 12.9; ensure no earlier 12.4 override
            lines.append("module unload cudatoolkit 2>/dev/null || true")
        else:
            lines.append("module load cudatoolkit/12.4 2>/dev/null || true")
        lines.append("module load python 2>/dev/null || true")
        # openmpi module sets MPI_ROOT, but lulesh Makefile expects MPICH_DIR
        lines.append('export MPICH_DIR="${MPI_ROOT:-${OPENMPI_ROOT}}"')
        # nvcc requires g++ <= 13; system g++ is 14.3. Make mpicxx wrap g++-12.
        lines.append('export OMPI_CXX=g++-12')
        return "\n".join(lines)

    def get_spack_setup(self) -> str:
        """Generate shell snippet for spack/HPCToolkit profiling tools."""
        home_dir = os.environ.get("HOME", str(Path.home()))
        return (
            f'if [ -f "{home_dir}/spack/share/spack/setup-env.sh" ]; then\n'
            f'    source "{home_dir}/spack/share/spack/setup-env.sh"\n'
            f'    spack load hpctoolkit 2>/dev/null || true\n'
            f'fi'
        )

    def build_shell_preamble(
        self,
        repo_name: str,
        workspace: Path,
        include_api_exports: bool = True,
    ) -> str:
        """Build the common shell preamble for all framework launchers.

        Generates: module loads, spack setup, env exports, cd to workspace.
        Framework-specific setup (nvm, venv, custom PATH) should be added
        before or after this preamble by each subclass.
        """
        parts = [
            f"# HPC modules",
            self.get_module_loads(repo_name),
            "",
            f"# Spack/HPCToolkit",
            self.get_spack_setup(),
            "",
            f"# Environment variables",
            self.get_env_exports(repo_name, workspace),
        ]
        if include_api_exports:
            parts.append(self.get_api_env_exports())
        parts.extend([
            "",
            f'cd "{workspace}"',
        ])
        return "\n".join(parts)

    def get_prompt(self, repo_name: str, workspace: Path) -> str:
        """Get the task prompt for this framework and app.

        Uses the shared prompt builder with framework-specific adaptations.
        For GPA apps, reads metadata and kernel source from the workspace.
        """
        if repo_name == "gpa":
            from batch.frameworks.prompt import build_gpa_prompt
            metadata_path = workspace / "gpa_metadata.json"
            with open(metadata_path) as f:
                metadata = json.load(f)
            kernel_basename = Path(metadata["kernel_file"]).name
            kernel_source = (workspace / kernel_basename).read_text()
            return build_gpa_prompt(
                framework=self.name,
                workspace=str(workspace),
                gpa_app_name=metadata["gpa_app_name"],
                kernel_file=metadata["kernel_file"],
                kernel_name=metadata["kernel_name"],
                kernel_source=kernel_source,
                profiling=self.profiling,
                build_mode=self.build_mode,
            )

        from batch.frameworks.prompt import build_prompt
        return build_prompt(self.name, repo_name, str(workspace), self.profiling, self.build_mode)
