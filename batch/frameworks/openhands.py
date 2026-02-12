"""OpenHands framework launcher.

OpenHands (formerly OpenDevin) uses a CodeActAgent with SDK-based headless mode.
The openhands CLI is a TUI; for batch execution we use the SDK via openhands_runner.py.
"""

import os
from pathlib import Path
from typing import Optional

from batch.frameworks.base import FrameworkLauncher, SESSION_TIMEOUT


class OpenHandsLauncher(FrameworkLauncher):
    """Launcher for the OpenHands framework.

    Uses the OpenHands SDK (LocalConversation + Agent) for headless execution.
    The openhands CLI only supports interactive TUI mode.
    """

    name = "openhands"

    def generate_config(
        self,
        repo_name: str,
        workspace: Path,
        instance_id: str,
        output_dir: Path,
    ) -> Path:
        """Generate OpenHands config metadata.

        Unlike SWE-agent YAML, OpenHands SDK config is passed as CLI args
        to openhands_runner.py. This generates a metadata file for reference.
        """
        if self.model_name:
            model = self.model_name
            api_key = os.environ.get("OPENAI_API_KEY", "")
            base_url = os.environ.get("OPENAI_API_BASE", "")
        else:
            # Local vLLM — double openai prefix for litellm
            model = "openai/openai/gpt-oss-120b"
            api_key = "dummy-key-ok"
            base_url = f"http://{self.vllm_host}:{self.vllm_port}/v1"

        # Write config metadata for reference
        config_lines = [
            f"model = {model}",
            f"api_base = {base_url}",
            f"max_iterations = 50",
            f"workspace = {workspace}",
            f"tools = terminal, file_editor",
        ]

        config_path = output_dir / f"{instance_id}_openhands_config.toml"
        with open(config_path, "w") as f:
            f.write("\n".join(config_lines) + "\n")

        return config_path

    def build_launch_command(
        self,
        repo_name: str,
        workspace: Path,
        config_path: Path,
        output_dir: Path,
        trajectory_dir: Path,
        instance_id: str,
    ) -> str:
        """Build shell script to run OpenHands via SDK runner."""
        sweagent_venv = os.environ.get(
            "SWEAGENT_VENV",
            os.path.join(os.environ.get("HOME", ""), "envs", "sweagent")
        )
        sweagent_root = os.environ.get(
            "SWEAGENT_ROOT",
            str(self.sweagent_root)
        )
        home_dir = os.environ.get("HOME", str(Path.home()))
        prompt = self.get_prompt(repo_name, workspace)
        traj_file = trajectory_dir / f"{instance_id}.jsonl"

        # Write prompt to temp file to avoid shell argument length limits
        prompt_file = output_dir / f"{instance_id}_prompt.txt"
        with open(prompt_file, "w") as f:
            f.write(prompt)

        # Determine model for SDK runner
        if self.model_name:
            model = self.model_name
        else:
            model = "openai/openai/gpt-oss-120b"

        runner_script = f"{sweagent_root}/batch/frameworks/openhands_runner.py"

        shell_script = f"""\
# Activate Python venv (OpenHands SDK is pip-installed here)
source "{sweagent_venv}/bin/activate"

# Load HPC modules
{self.get_module_loads()}

# Setup spack/HPCToolkit for profiling
if [ -f "{home_dir}/spack/share/spack/setup-env.sh" ]; then
    source "{home_dir}/spack/share/spack/setup-env.sh"
    spack load hpctoolkit 2>/dev/null || true
fi

# Environment variables
{self.get_env_exports(repo_name, workspace)}
{self.get_api_env_exports()}

cd "{workspace}"

# Run OpenHands via SDK runner (headless mode)
timeout {SESSION_TIMEOUT} python3 "{runner_script}" \\
    --model "{model}" \\
    --workspace "{workspace}" \\
    --prompt-file "{prompt_file}" \\
    --trajectory-file "{traj_file}" \\
    --max-iterations 50
"""
        return shell_script

    def find_trajectory(
        self,
        output_dir: Path,
        trajectory_dir: Path,
        instance_id: str,
    ) -> Optional[str]:
        """Find OpenHands JSONL output file."""
        traj_file = trajectory_dir / f"{instance_id}.jsonl"
        if traj_file.exists():
            return str(traj_file)

        # Also check for OpenHands' save_trajectory_path output
        for jsonl in trajectory_dir.glob(f"**/{instance_id}*.jsonl"):
            return str(jsonl)

        return None
