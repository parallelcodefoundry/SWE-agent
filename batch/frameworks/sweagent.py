"""SWE-agent framework launcher.

Generates SWE-agent YAML configs by combining:
  - config/hpc/llnl_base.yaml  (SWE-agent plumbing: tools, model, env vars)
  - batch/frameworks/prompt.py  (shared prompts: system_template + instance_template)

This ensures all frameworks share a single prompt source of truth.
"""

import os
import re
from pathlib import Path
from typing import Optional


from batch.frameworks.base import (
    FrameworkLauncher, SESSION_TIMEOUT, APP_EXECUTION_TIMEOUT, APP_ROOT_VAR,
)


# Per-app harness tool bundle
APP_HARNESS_BUNDLE = {
    "kripke": "tools/kripke_harness",
    "laghos": "tools/laghos_harness",
    "lulesh": "tools/lulesh_harness",
    "quicksilver": "tools/quicksilver_harness",
}

# Profiling tool bundles (added when profiling == "with_profiling")
PROFILING_BUNDLES = [
    "tools/hpctoolkit",
    "tools/hatchet",
    "tools/system_info",
    "tools/profiling",
    "tools/nsight_compute",
    "tools/nsight_systems",
]

# Common tool bundles (always included)
COMMON_BUNDLES_BEFORE = [
    "tools/registry",
    "tools/edit_anthropic",
]
COMMON_BUNDLES_AFTER = [
    "tools/review_on_submit_m",
    "tools/forfeit",
]


class SweAgentLauncher(FrameworkLauncher):
    """Launcher for SWE-agent framework.

    LLNL apps: prompts generated from prompt.py, injected into llnl_base.yaml.
    GPA apps: prompts generated from prompt.py, injected into gpa_*.yaml.
    """

    name = "sweagent"

    def generate_config(
        self,
        repo_name: str,
        workspace: Path,
        instance_id: str,
        output_dir: Path,
    ) -> Path:
        """Generate SWE-agent YAML config for this instance.

        For LLNL apps: reads llnl_base.yaml template, generates prompts from
        prompt.py, and injects both into the YAML via placeholder replacement.
        """
        if repo_name == "gpa":
            return self._generate_gpa_config(workspace, instance_id, output_dir)

        from batch.frameworks.prompt import build_sweagent_prompts, APP_TOOLS

        # Generate prompts from shared prompt builder
        prompts = build_sweagent_prompts(repo_name, str(workspace), self.profiling)

        # Read base YAML template
        base_config_path = self.sweagent_root / "config/hpc/llnl_base.yaml"
        with open(base_config_path) as f:
            config_content = f.read()

        # Indent prompts for YAML (system_template and instance_template
        # are under "|-" blocks indented 6 spaces)
        sys_indented = _indent_yaml_block(prompts["system_template"], indent=6)
        inst_indented = _indent_yaml_block(prompts["instance_template"], indent=6)

        config_content = config_content.replace(
            "      __SYSTEM_PROMPT__", sys_indented
        )
        config_content = config_content.replace(
            "      __INSTANCE_PROMPT__", inst_indented
        )

        # Per-app settings
        tools = APP_TOOLS[repo_name]
        run_cmd = tools["run"].split()[0]  # e.g., "kripke_run"
        root_var = APP_ROOT_VAR[repo_name]
        timeout = APP_EXECUTION_TIMEOUT[repo_name]

        config_content = config_content.replace("__EXECUTION_TIMEOUT__", str(timeout))
        config_content = config_content.replace("__APP_ROOT_VAR__", root_var)
        config_content = config_content.replace("__APP_ROOT_PATH__", str(workspace))
        config_content = config_content.replace("__REPO_PATH__", str(workspace))
        config_content = config_content.replace("__RUN_CMD__", run_cmd)

        # Build tool bundle list
        bundles = self._build_bundle_list(repo_name)
        bundle_yaml = "\n".join(f"      - path: {b}" for b in bundles)
        config_content = config_content.replace("__BUNDLES__", bundle_yaml)

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
{self.get_spack_setup()}

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

    def _build_bundle_list(self, repo_name: str) -> list[str]:
        """Build the ordered list of SWE-agent tool bundles for an app."""
        bundles = list(COMMON_BUNDLES_BEFORE)
        if repo_name in APP_HARNESS_BUNDLE:
            bundles.append(APP_HARNESS_BUNDLE[repo_name])
        if self.profiling == "with_profiling":
            bundles.extend(PROFILING_BUNDLES)
        bundles.extend(COMMON_BUNDLES_AFTER)
        return bundles

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


def _indent_yaml_block(text: str, indent: int = 6) -> str:
    """Indent a multi-line string for YAML literal block scalar.

    The first line gets the full indent. Subsequent lines get the same indent.
    Empty lines are left empty (YAML literal block convention).
    """
    prefix = " " * indent
    lines = text.splitlines()
    result = []
    for line in lines:
        if line.strip():
            result.append(prefix + line)
        else:
            result.append("")
    return "\n".join(result)
