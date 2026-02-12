"""OpenHands framework launcher.

OpenHands (formerly OpenDevin) uses a CodeActAgent with local runtime on Perlmutter.
Config is TOML format. Headless mode via `openhands --headless -t "PROMPT"`.
"""

import os
from pathlib import Path
from typing import Optional

from batch.frameworks.base import FrameworkLauncher, SESSION_TIMEOUT


class OpenHandsLauncher(FrameworkLauncher):
    """Launcher for the OpenHands framework.

    Generates TOML config with local runtime (no Docker on Perlmutter),
    builds shell script that runs `openhands --headless`.
    """

    name = "openhands"

    def generate_config(
        self,
        repo_name: str,
        workspace: Path,
        instance_id: str,
        output_dir: Path,
    ) -> Path:
        """Generate OpenHands config.toml.

        Key settings:
        - runtime = "local" (no Docker/podman on Perlmutter compute nodes)
        - max_iterations = 50 (matches SWE-agent per_instance_call_limit)
        - Model in litellm format
        """
        if self.model_name:
            # External model (already in litellm format)
            model = self.model_name
            api_key = os.environ.get("OPENAI_API_KEY", "")
            base_url = os.environ.get("OPENAI_API_BASE", "")
        else:
            # Local vLLM — double openai prefix for litellm
            model = "openai/openai/gpt-oss-120b"
            api_key = "dummy-key-ok"
            base_url = f"http://{self.vllm_host}:{self.vllm_port}/v1"

        # Build TOML config
        config_lines = [
            "[core]",
            'default_agent = "CodeActAgent"',
            'runtime = "local"',
            f"max_iterations = 50",
            f'workspace_base = "{workspace}"',
            "",
            "[llm]",
            f'model = "{model}"',
            f'api_key = "{api_key}"',
            f'base_url = "{base_url}"',
            "max_input_tokens = 120000",
            "max_output_tokens = 120000",
            "native_tool_calling = true",
            "",
            "[agent]",
            "enable_browsing = false",
            "enable_jupyter = false",
            "enable_cmd = true",
            "enable_editor = true",
            "enable_think = true",
        ]

        config_content = "\n".join(config_lines) + "\n"

        config_path = output_dir / f"{instance_id}_openhands_config.toml"
        with open(config_path, "w") as f:
            f.write(config_content)

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
        """Build shell script to run OpenHands in headless mode."""
        sweagent_venv = os.environ.get(
            "SWEAGENT_VENV",
            os.path.join(os.environ.get("HOME", ""), "envs", "sweagent")
        )
        home_dir = os.environ.get("HOME", str(Path.home()))
        prompt = self.get_prompt(repo_name, workspace)
        traj_file = trajectory_dir / f"{instance_id}.jsonl"

        # Write prompt to temp file to avoid shell argument length limits
        prompt_file = output_dir / f"{instance_id}_prompt.txt"
        with open(prompt_file, "w") as f:
            f.write(prompt)

        shell_script = f"""\
# Activate Python venv (OpenHands is pip-installed here)
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

# OpenHands config
export OPENHANDS_CONFIG="{config_path}"

cd "{workspace}"

# Run OpenHands in headless mode
timeout {SESSION_TIMEOUT} openhands --headless \\
    -t "$(cat '{prompt_file}')" \\
    --json \\
    > "{traj_file}" 2>&1
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
