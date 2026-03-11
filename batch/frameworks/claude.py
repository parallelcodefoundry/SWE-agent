"""Claude Code framework launcher.

Claude Code uses `claude -p` for non-interactive mode with --dangerously-skip-permissions
for auto-approval of all tool calls. Uses Anthropic's API via Max subscription (OAuth auth
stored in ~/.claude/). Project context via CLAUDE.md in workspace.
"""

import os
import subprocess
from pathlib import Path
from typing import Optional

from batch.frameworks.base import FrameworkLauncher, SESSION_TIMEOUT


class ClaudeCodeLauncher(FrameworkLauncher):
    """Launcher for the Claude Code framework.

    Generates CLAUDE.md for project context, builds shell script that runs
    `claude -p` with --dangerously-skip-permissions for autonomous execution.
    Uses Anthropic API via subscription auth (no API key needed).
    """

    name = "claude"

    def generate_config(
        self,
        repo_name: str,
        workspace: Path,
        instance_id: str,
        output_dir: Path,
    ) -> Path:
        """Generate Claude Code config: CLAUDE.md in workspace + metadata file.

        Claude Code auto-reads CLAUDE.md from the working directory for project
        context. The task prompt is passed via -p flag; CLAUDE.md provides
        persistent instructions about the harness tools and environment.
        """
        prompt = self.get_prompt(repo_name, workspace)

        # Write CLAUDE.md to workspace for Claude Code to discover
        claude_md = workspace / "CLAUDE.md"
        with open(claude_md, "w") as f:
            f.write("# HPC Optimization Task\n\n")
            f.write(
                "You are in non-interactive mode. There is NO human to respond.\n"
                "NEVER ask for confirmation. Implement changes directly.\n"
                "You MUST edit source files before stopping. Analysis alone means FAILURE.\n\n"
            )
            f.write(prompt)
            f.write("\n\n")
            f.write(
                "## Important Notes\n\n"
                "- Build and run commands take 60-240 seconds. This is normal — do not interrupt them.\n"
                "- Test after every edit by rebuilding and running.\n"
                "- Keep changes small and incremental.\n"
                "- If a change doesn't improve performance, revert it and try something different.\n"
            )

        # Record version for reproducibility
        version_result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
        )
        claude_version = (
            version_result.stdout.strip()
            if version_result.returncode == 0
            else "unknown"
        )

        # Determine model
        model = self.model_name if self.model_name else "claude-opus-4-6"

        # Write metadata file for reference/reproducibility
        meta_path = output_dir / f"{instance_id}_claude_config.txt"
        with open(meta_path, "w") as f:
            f.write(f"framework: claude-code\n")
            f.write(f"version: {claude_version}\n")
            f.write(f"model: {model}\n")
            f.write(f"auth: subscription\n")
            f.write(f"permissions: --dangerously-skip-permissions\n")
            f.write(f"workspace: {workspace}\n")
            f.write(f"instance_id: {instance_id}\n")

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
        """Build shell script to run Claude Code in non-interactive mode."""
        home_dir = os.environ.get("HOME", str(Path.home()))
        prompt = self.get_prompt(repo_name, workspace)
        traj_file = trajectory_dir / f"{instance_id}.jsonl"

        # Write prompt to temp file (avoid shell argument length limits)
        prompt_file = output_dir / f"{instance_id}_prompt.txt"
        with open(prompt_file, "w") as f:
            f.write(prompt)

        # Determine model
        model = self.model_name if self.model_name else "claude-opus-4-6"

        shell_script = f"""\
set -o pipefail  # propagate agent exit code through tee pipe

# Ensure claude CLI is in PATH
export PATH="{home_dir}/.local/bin:$PATH"

{self.build_shell_preamble(repo_name, workspace, include_api_exports=False)}

# Claude Code uses Anthropic API via subscription auth (~/.claude/).
# No OPENAI_API_BASE/KEY needed. If ANTHROPIC_API_KEY is set, Claude Code
# will use it automatically.

# Unset CLAUDECODE to prevent "nested session" error when benchmark runner
# itself is launched from within Claude Code.
unset CLAUDECODE 2>/dev/null || true

# Run Claude Code in non-interactive mode
# -p: pass prompt directly (non-interactive)
# --dangerously-skip-permissions: auto-approve all tool calls (bash, write, edit, etc.)
# --output-format stream-json: structured JSONL output for trajectory logging
# --model: explicit model selection for reproducibility
# --max-turns: allow enough iterations for build/run/optimize cycles
timeout {SESSION_TIMEOUT} claude -p "$(cat '{prompt_file}')" \\
    --dangerously-skip-permissions \\
    --output-format stream-json \\
    --verbose \\
    --model {model} \\
    --max-turns 300 \\
    2>&1 | tee "{traj_file}"
"""
        return shell_script

    def find_trajectory(
        self,
        output_dir: Path,
        trajectory_dir: Path,
        instance_id: str,
    ) -> Optional[str]:
        """Find Claude Code JSONL output file."""
        traj_file = trajectory_dir / f"{instance_id}.jsonl"
        if traj_file.exists():
            return str(traj_file)
        return None
