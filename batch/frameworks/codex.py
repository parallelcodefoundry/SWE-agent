"""Codex CLI framework launcher.

OpenAI Codex CLI uses `codex exec` for non-interactive mode.
CRITICAL: wire_api=chat is no longer supported; use wire_api=responses always.
Config via -c flags. Project context via AGENTS.md in workspace.
"""

import os
from pathlib import Path
from typing import Optional

from batch.frameworks.base import FrameworkLauncher, SESSION_TIMEOUT


class CodexLauncher(FrameworkLauncher):
    """Launcher for the Codex CLI framework.

    Generates AGENTS.md for project context, builds shell script that runs
    `codex exec --dangerously-bypass-approvals-and-sandbox` with config overrides via -c flags.
    """

    name = "codex"

    def generate_config(
        self,
        repo_name: str,
        workspace: Path,
        instance_id: str,
        output_dir: Path,
    ) -> Path:
        """Generate Codex CLI config: AGENTS.md in workspace + metadata file.

        Codex reads AGENTS.md from the working directory for project context.
        Runtime config is passed via -c flags in the launch command.
        """
        prompt = self.get_prompt(repo_name, workspace)

        # Write AGENTS.md to workspace for Codex to discover
        agents_md = workspace / "AGENTS.md"
        with open(agents_md, "w") as f:
            f.write(f"# HPC Optimization Task\n\n{prompt}\n")

        # Write a metadata file with the -c config flags for the launch command
        if self.model_name:
            # External model — use custom provider name to avoid collision
            # with Codex built-in "openai" provider (or_insert semantics
            # in config/mod.rs silently drops user overrides for built-ins).
            if "/" in self.model_name:
                _, model_id = self.model_name.split("/", 1)
            else:
                model_id = self.model_name
            provider_id = "ext"
            api_base = os.environ.get("OPENAI_API_BASE", "")
            wire_api = "responses"  # External OpenAI uses Responses API
        else:
            # Local vLLM
            provider_id = "local-vllm"
            model_id = "gpt-oss-120b"
            api_base = f"http://{self.vllm_host}:{self.vllm_port}/v1"
            wire_api = "responses"

        config_flags = [
            f"model_provider={provider_id}",
            f"model_providers.{provider_id}.name={provider_id}",
            f"model_providers.{provider_id}.base_url={api_base}",
            f"model_providers.{provider_id}.env_key=OPENAI_API_KEY",
            f"model_providers.{provider_id}.wire_api={wire_api}",
            f"model={model_id}",
            "web_search=disabled",
        ]

        # Write metadata for reference
        meta_path = output_dir / f"{instance_id}_codex_config.txt"
        with open(meta_path, "w") as f:
            for flag in config_flags:
                f.write(f"-c {flag}\n")

        return meta_path

    def build_launch_command(
        self,
        repo_name: str,
        workspace: Path,
        config_path: Path,
        output_dir: Path,
        trajectory_dir: Path,
        instance_id: str,
    ) -> str:
        """Build shell script to run Codex CLI in exec mode."""
        home_dir = os.environ.get("HOME", str(Path.home()))
        prompt = self.get_prompt(repo_name, workspace)
        traj_file = trajectory_dir / f"{instance_id}.jsonl"

        # Write prompt to temp file
        prompt_file = output_dir / f"{instance_id}_prompt.txt"
        with open(prompt_file, "w") as f:
            f.write(prompt)

        # Build -c config flags — use custom provider name "ext" for external
        # models to avoid Codex built-in "openai" provider shadow (or_insert).
        if self.model_name:
            if "/" in self.model_name:
                _, model_id = self.model_name.split("/", 1)
            else:
                model_id = self.model_name
            provider_id = "ext"
            api_base = os.environ.get("OPENAI_API_BASE", "")
            wire_api = "responses"
        else:
            provider_id = "local-vllm"
            model_id = "gpt-oss-120b"
            api_base = f"http://{self.vllm_host}:{self.vllm_port}/v1"
            wire_api = "responses"

        c_flags = (
            f'-c "model_provider={provider_id}" '
            f'-c "model_providers.{provider_id}.name={provider_id}" '
            f'-c "model_providers.{provider_id}.base_url={api_base}" '
            f'-c "model_providers.{provider_id}.env_key=OPENAI_API_KEY" '
            f'-c "model_providers.{provider_id}.wire_api={wire_api}" '
            f'-c "model={model_id}" '
            f'-c "web_search=disabled"'
        )

        shell_script = f"""\
# Setup Node.js via nvm
if [ -f "{home_dir}/.nvm/nvm.sh" ]; then
    source "{home_dir}/.nvm/nvm.sh"
    nvm use 22 2>/dev/null || {{ echo "ERROR: Node 22 not available"; exit 1; }}
else
    echo "ERROR: nvm not found at {home_dir}/.nvm/nvm.sh"
    exit 1
fi

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
export CODEX_API_KEY="${{OPENAI_API_KEY}}"

cd "{workspace}"

# Run Codex CLI in exec mode (no sandbox, no approvals)
timeout {SESSION_TIMEOUT} codex exec \\
    --dangerously-bypass-approvals-and-sandbox \\
    --skip-git-repo-check \\
    --json \\
    --ephemeral \\
    {c_flags} \\
    "$(cat '{prompt_file}')" \\
    > "{traj_file}" 2>&1
"""
        return shell_script

    def find_trajectory(
        self,
        output_dir: Path,
        trajectory_dir: Path,
        instance_id: str,
    ) -> Optional[str]:
        """Find Codex CLI JSONL output file."""
        traj_file = trajectory_dir / f"{instance_id}.jsonl"
        if traj_file.exists():
            return str(traj_file)
        return None
