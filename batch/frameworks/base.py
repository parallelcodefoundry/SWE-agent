"""Base class for framework-specific agent launchers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import json
import os
import subprocess


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
    ):
        self.sweagent_root = sweagent_root
        self.vllm_host = vllm_host
        self.vllm_port = vllm_port
        self.model_name = model_name
        self.profiling = profiling

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
        """Get list of directories to add to PATH for this app and profiling config."""
        dirs = []
        if repo_name in HARNESS_MAP:
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
            return (
                f'export SWE_AGENT_ROOT="{self.sweagent_root}"\n'
                'export GPA_BENCHMARK_ROOT="/pscratch/sd/k/krydzy/GPA-Benchmark"\n'
                'export CUDA_VISIBLE_DEVICES="0,1,2,3"\n'
                'export OMP_NUM_THREADS=32\n'
                'export PYTHONUNBUFFERED=1'
            )

        root_var = APP_ROOT_VAR[repo_name]
        path_dirs = self.get_path_dirs(repo_name)
        path_prefix = ":".join(path_dirs)

        lines = [
            f'export PATH="{path_prefix}:$PATH"',
            f'export {root_var}="{workspace}"',
            f'export SWE_AGENT_ROOT="{self.sweagent_root}"',
            'export CUDA_VISIBLE_DEVICES="0,1,2,3"',
            'export OMP_NUM_THREADS=32',
            # Unbuffered Python output ensures harness scripts flush immediately,
            # critical for Codex which has a 10s per-command timeout.
            'export PYTHONUNBUFFERED=1',
        ]
        return "\n".join(lines)

    def get_api_env_exports(self) -> str:
        """Generate shell export statements for API credentials."""
        if self.model_name:
            # External model: use env vars passed through from parent
            api_base = os.environ.get("OPENAI_API_BASE", "")
            api_key = os.environ.get("OPENAI_API_KEY", "")
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

    def get_module_loads(self) -> str:
        """Generate module load commands for HPC environment."""
        return (
            "module load openmpi/5.0.7 2>/dev/null || true\n"
            "module load cudatoolkit/12.4 2>/dev/null || true\n"
            "module load python 2>/dev/null || true"
        )

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
            )

        from batch.frameworks.prompt import build_prompt
        return build_prompt(self.name, repo_name, str(workspace), self.profiling)
