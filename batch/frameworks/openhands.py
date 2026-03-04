"""OpenHands framework launcher.

OpenHands (formerly OpenDevin) uses the SDK for headless batch execution.
The openhands CLI is a TUI; for batch execution we use the SDK via openhands_runner.py.
Requires tmux >= 3.2 (installed at ~/local/bin/tmux for Perlmutter compatibility).
"""

import os
from pathlib import Path
from typing import Optional

from batch.frameworks.base import FrameworkLauncher, SESSION_TIMEOUT


class OpenHandsLauncher(FrameworkLauncher):
    """Launcher for the OpenHands framework.

    Uses the OpenHands SDK (LocalConversation + Agent) for headless execution.
    Requires custom tmux 3.5a at ~/local/bin/ since Perlmutter system tmux 3.1c
    doesn't support the -e flag needed by libtmux.
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
            f"max_iterations = 200",
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
            model = f"openai/{self.model_name}"
        else:
            model = "openai/openai/gpt-oss-120b"

        runner_script = f"{sweagent_root}/batch/frameworks/openhands_runner.py"

        shell_script = f"""\
# Load HPC modules BEFORE venv activation so module load python doesn't shadow venv
{self.get_module_loads(repo_name)}

# Activate Python venv (OpenHands SDK is pip-installed here)
# Must come AFTER module loads so venv's Python takes precedence over module's
source "{sweagent_venv}/bin/activate"

# Add custom tmux 3.5a to PATH (system tmux 3.1c lacks -e flag needed by libtmux)
export PATH="{home_dir}/local/bin:$PATH"

# Setup spack/HPCToolkit for profiling
{self.get_spack_setup()}

# Environment variables
{self.get_env_exports(repo_name, workspace)}
{self.get_api_env_exports()}

cd "{workspace}"

# Run OpenHands via SDK runner (headless mode)
# Use PYTHONPATH + -m to avoid openhands.py shadowing the pip openhands package
# (running as a script adds batch/frameworks/ to sys.path, shadowing the namespace pkg)
PYTHONPATH="{sweagent_root}:${{PYTHONPATH:-}}" timeout {SESSION_TIMEOUT} python3 -m batch.frameworks.openhands_runner \\
    --model "{model}" \\
    --workspace "{workspace}" \\
    --prompt-file "{prompt_file}" \\
    --trajectory-file "{traj_file}" \\
    --max-iterations 200
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
