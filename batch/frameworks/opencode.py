"""OpenCode framework launcher.

OpenCode is a terminal-based coding agent that uses `opencode run` for headless mode.
Config is passed via OPENCODE_CONFIG_CONTENT env var (inline JSON).
Tools are bash commands in PATH — no tool bundle registration needed.
"""

import json
import os
from pathlib import Path
from typing import Optional

from batch.frameworks.base import FrameworkLauncher, SESSION_TIMEOUT


class OpenCodeLauncher(FrameworkLauncher):
    """Launcher for the OpenCode framework.

    Generates JSON config for provider/model, builds shell script that runs
    `opencode run --format json` with harness tools in PATH.
    """

    name = "opencode"

    def generate_config(
        self,
        repo_name: str,
        workspace: Path,
        instance_id: str,
        output_dir: Path,
    ) -> Path:
        """Generate OpenCode config JSON.

        Uses OPENCODE_CONFIG_CONTENT env var format with provider configuration
        for either local vLLM or external model API.
        """
        if self.model_name:
            # External model (e.g., "anthropic/claude-sonnet-4-5-20250929" or "openai/gpt-4o")
            # Parse provider/model from model_name
            if "/" in self.model_name:
                provider_id, model_id = self.model_name.split("/", 1)
            else:
                provider_id = "openai"
                model_id = self.model_name

            api_base = os.environ.get("OPENAI_API_BASE", "")
            api_key = os.environ.get("OPENAI_API_KEY", "")

            config = {
                "provider": {
                    provider_id: {
                        "npm": f"@ai-sdk/{provider_id}",
                        "options": {"baseURL": api_base, "apiKey": api_key},
                        "models": {model_id: {"name": model_id}},
                    }
                },
                "model": f"{provider_id}/{model_id}",
                # CRITICAL: Use object form {"*": "allow"}, NOT string "allow".
                # OpenCode's OPENCODE_CONFIG_CONTENT is merged via JSON.parse()
                # without Zod schema validation, so the permissionTransform that
                # converts "allow" → {"*": "allow"} never runs. The raw string
                # "allow" gets split by Object.entries() into per-character rules
                # with invalid action values ("a", "l", "l", "o", "w").
                "permission": {"*": "allow"},
            }
        else:
            # Local vLLM
            base_url = f"http://{self.vllm_host}:{self.vllm_port}/v1"
            config = {
                "provider": {
                    "local-vllm": {
                        "npm": "@ai-sdk/openai-compatible",
                        "options": {"baseURL": base_url, "apiKey": "dummy"},
                        "models": {"gpt-oss-120b": {"name": "GPT-OSS 120B"}},
                    }
                },
                "model": "local-vllm/gpt-oss-120b",
                # See comment above — must use object form, not string "allow"
                "permission": {"*": "allow"},
            }

        config_path = output_dir / f"{instance_id}_opencode_config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

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
        """Build shell script to run OpenCode in headless mode."""
        home_dir = os.environ.get("HOME", str(Path.home()))
        prompt = self.get_prompt(repo_name, workspace)
        traj_file = trajectory_dir / f"{instance_id}.jsonl"

        # Write prompt to temp file to avoid shell argument length limits
        prompt_file = output_dir / f"{instance_id}_prompt.txt"
        with open(prompt_file, "w") as f:
            f.write(prompt)

        shell_script = f"""\
set -o pipefail  # propagate agent exit code through tee pipe

# Setup Node.js via nvm
if [ -f "{home_dir}/.nvm/nvm.sh" ]; then
    source "{home_dir}/.nvm/nvm.sh"
    nvm use 22 2>/dev/null || {{ echo "ERROR: Node 22 not available"; exit 1; }}
else
    echo "ERROR: nvm not found at {home_dir}/.nvm/nvm.sh"
    exit 1
fi

# Load HPC modules
{self.get_module_loads(repo_name)}

# Setup spack/HPCToolkit for profiling
if [ -f "{home_dir}/spack/share/spack/setup-env.sh" ]; then
    source "{home_dir}/spack/share/spack/setup-env.sh"
    spack load hpctoolkit 2>/dev/null || true
fi

# Environment variables
{self.get_env_exports(repo_name, workspace)}
{self.get_api_env_exports()}

# OpenCode config via env var
export OPENCODE_CONFIG_CONTENT="$(cat '{config_path}')"

cd "{workspace}"

# Run OpenCode in headless mode with debug logging.
# --log-level DEBUG --print-logs sends debug traces to stderr,
# which subprocess.run merges into _agent_realtime.log via stderr=STDOUT.
# Use `tee` to split --format json output: one copy to trajectory JSONL file,
# the other to stdout (captured as _agent_realtime.log by the runner).
timeout {SESSION_TIMEOUT} opencode run \\
    --format json \\
    --log-level DEBUG \\
    --print-logs \\
    --title "{instance_id}" \\
    "$(cat '{prompt_file}')" \\
    2>&1 | tee "{traj_file}"
"""
        return shell_script

    def find_trajectory(
        self,
        output_dir: Path,
        trajectory_dir: Path,
        instance_id: str,
    ) -> Optional[str]:
        """Find OpenCode JSONL output file."""
        traj_file = trajectory_dir / f"{instance_id}.jsonl"
        if traj_file.exists():
            return str(traj_file)
        return None
