"""SWE-agent framework launcher.

Extracts SWE-agent-specific config generation and launch logic from
HPCBenchmarkRunner, preserving the existing behavior exactly.
"""

import os
import re
from pathlib import Path
from typing import Optional


from batch.frameworks.base import FrameworkLauncher, SESSION_TIMEOUT


class SweAgentLauncher(FrameworkLauncher):
    """Launcher for SWE-agent framework.

    Uses YAML config files from config/hpc/ and runs via `sweagent run --config`.
    This is the original framework — logic extracted from HPCBenchmarkRunner.
    """

    name = "sweagent"

    # Repo config templates (same as HPCBenchmarkRunner.REPO_CONFIG_TEMPLATES)
    REPO_CONFIG_TEMPLATES = {
        "kripke": {
            "pristine_subdir": "Kripke",
            "test_subdir": "Kripke_test",
            "config_template": "config/hpc/kripke_{profiling}.yaml",
        },
        "laghos": {
            "pristine_subdir": "Laghos",
            "test_subdir": "Laghos_test",
            "config_template": "config/hpc/laghos_{profiling}.yaml",
        },
        "lulesh": {
            "pristine_subdir": "Lulesh",
            "test_subdir": "Lulesh_test",
            "config_template": "config/hpc/lulesh_{profiling}.yaml",
        },
        "quicksilver": {
            "pristine_subdir": "Quicksilver",
            "test_subdir": "Quicksilver_test",
            "config_template": "config/hpc/quicksilver_{profiling}.yaml",
        },
    }

    def generate_config(
        self,
        repo_name: str,
        workspace: Path,
        instance_id: str,
        output_dir: Path,
    ) -> Path:
        """Generate SWE-agent YAML config for this instance.

        Reads the base config template, substitutes workspace paths,
        injects SWE_AGENT_ROOT, and overrides model/API settings.
        """
        if repo_name == "gpa":
            return self._generate_gpa_config(workspace, instance_id, output_dir)

        tmpl = self.REPO_CONFIG_TEMPLATES[repo_name]
        base_config_rel = tmpl["config_template"].format(profiling=self.profiling)
        base_config_path = self.sweagent_root / base_config_rel

        with open(base_config_path) as f:
            config_content = f.read()

        # Replace repo path with workspace
        original_path = str(self.sweagent_root / tmpl["test_subdir"])
        config_content = config_content.replace(original_path, str(workspace))

        # Update ROOT env var
        root_var = f"{repo_name.upper()}_ROOT"
        config_content = config_content.replace(
            f"{root_var}: {original_path}",
            f"{root_var}: {workspace}"
        )

        # Inject SWE_AGENT_ROOT env var
        config_content = self._inject_sweagent_root(config_content)

        # Override api_base for (possibly remote) vLLM server
        config_content = config_content.replace(
            'api_base: "http://127.0.0.1:8008/v1"',
            f'api_base: "http://{self.vllm_host}:{self.vllm_port}/v1"'
        )

        # Override model name and cost limit for external APIs
        config_content = self._apply_model_overrides(config_content)

        # Write modified config
        instance_config = output_dir / f"{instance_id}_config.yaml"
        with open(instance_config, "w") as f:
            f.write(config_content)

        return instance_config

    def build_launch_command(
        self,
        repo_name: str,
        workspace: Path,
        config_path: Path,
        output_dir: Path,
        trajectory_dir: Path,
        instance_id: str,
    ) -> str:
        """Build shell script to run SWE-agent.

        This is the exact logic previously in HPCBenchmarkRunner.run_agent().
        """
        sweagent_venv = os.environ.get(
            "SWEAGENT_VENV",
            os.path.join(os.environ.get("HOME", ""), "envs", "sweagent")
        )
        home_dir = os.environ.get("HOME", str(Path.home()))

        shell_script = f"""
cd {self.sweagent_root}
source {sweagent_venv}/bin/activate

# Load modules for HPC environment
{self.get_module_loads(repo_name)}

# Setup spack and HPCToolkit for profiling tools
if [ -f "{home_dir}/spack/share/spack/setup-env.sh" ]; then
    source "{home_dir}/spack/share/spack/setup-env.sh"
    spack load hpctoolkit 2>/dev/null || true
fi

# Setup podman wrapper to use podman-hpc
unalias podman 2>/dev/null || true
hash -r
mkdir -p "{home_dir}/bin"
cat > "{home_dir}/bin/podman" <<'SH'
#!/usr/bin/env bash
real=/usr/bin/podman
hpc=/usr/bin/podman-hpc
case "$1" in
  -h|--help|help|version|--version) exec "$real" "$@";;
  *) if command -v "$hpc" >/dev/null 2>&1; then exec "$hpc" "$@"; else exec "$real" "$@"; fi ;;
esac
SH
chmod +x "{home_dir}/bin/podman"
export PATH="{home_dir}/bin:$PATH"
hash -r

# API credentials
{self.get_api_env_exports()}

# SWE_AGENT_ROOT for harness scripts
export SWE_AGENT_ROOT="{self.sweagent_root}"

timeout {SESSION_TIMEOUT} sweagent run --config {config_path} \\
    --agent.model.max_input_tokens=120000 \\
    --agent.model.max_output_tokens=120000 \\
    --output_dir {trajectory_dir / instance_id}
"""
        return shell_script

    def find_trajectory(
        self,
        output_dir: Path,
        trajectory_dir: Path,
        instance_id: str,
    ) -> Optional[str]:
        """Find SWE-agent .traj trajectory file."""
        traj_instance_dir = trajectory_dir / instance_id
        traj_files = (
            list(traj_instance_dir.glob("**/*.traj"))
            if traj_instance_dir.exists()
            else []
        )

        # Fallback to default location
        if not traj_files:
            traj_dir = self.sweagent_root / "trajectories"
            traj_files = list(traj_dir.glob("**/*.traj"))

        if traj_files:
            return str(max(traj_files, key=lambda p: p.stat().st_mtime))
        return None

    def _generate_gpa_config(
        self,
        workspace: Path,
        instance_id: str,
        output_dir: Path,
    ) -> Path:
        """Generate SWE-agent YAML config for a GPA benchmark instance.

        GPA apps use a dynamically generated config since the prompt includes
        the kernel source code, which varies per app.
        """
        base_config_path = self.sweagent_root / f"config/hpc/gpa_{self.profiling}.yaml"
        with open(base_config_path) as f:
            config_content = f.read()

        # Replace workspace placeholder
        config_content = config_content.replace("__GPA_WORKSPACE__", str(workspace))

        # Generate and inject the GPA prompt
        prompt = self.get_prompt("gpa", workspace)
        # Indent prompt for YAML (instance_template is indented 6 spaces)
        indented_prompt = "\n".join(
            f"      {line}" if line.strip() else "" for line in prompt.splitlines()
        )
        config_content = config_content.replace(
            "      __GPA_INSTANCE_PROMPT__", indented_prompt
        )

        # Inject SWE_AGENT_ROOT
        config_content = self._inject_sweagent_root(config_content)

        # Apply model overrides (api_base, model name, cost limit)
        config_content = config_content.replace(
            'api_base: "http://127.0.0.1:8008/v1"',
            f'api_base: "http://{self.vllm_host}:{self.vllm_port}/v1"',
        )
        config_content = self._apply_model_overrides(config_content)

        # Write config
        instance_config = output_dir / f"{instance_id}_config.yaml"
        with open(instance_config, "w") as f:
            f.write(config_content)

        return instance_config

    def _apply_model_overrides(self, config_content: str) -> str:
        """Override model name and cost limit when using an external model."""
        if self.model_name:
            config_content = config_content.replace(
                'name: openai/openai/gpt-oss-120b',
                f'name: {self.model_name}'
            )
            config_content = config_content.replace(
                'per_instance_cost_limit: 0',
                'per_instance_cost_limit: 1.0'
            )
            # Remove api_base and api_key so LiteLLM uses env vars
            config_content = re.sub(
                r'^\s*api_base:.*$\n?', '', config_content, flags=re.MULTILINE
            )
            config_content = re.sub(
                r'^\s*api_key:.*$\n?', '', config_content, flags=re.MULTILINE
            )
        return config_content

    def _inject_sweagent_root(self, config_content: str) -> str:
        """Inject SWE_AGENT_ROOT into config env_variables."""
        sweagent_root_line = f"      SWE_AGENT_ROOT: {self.sweagent_root}"
        config_content = re.sub(
            r'(env_variables:\n)',
            f'\\1{sweagent_root_line}\n',
            config_content,
            count=1
        )
        return config_content
