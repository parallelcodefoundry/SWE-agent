#!/usr/bin/env python3
"""
HPC Benchmark Runner - Compares agent patches vs expert patches

Runs SWE-agent on pre-optimization commits from the curated dataset,
then compares the agent's solution with the expert's actual optimization.

Usage:
    python3 batch/hpc_benchmark_runner.py --dataset dataset/curated_perf_commits.json
    python3 batch/hpc_benchmark_runner.py --app quicksilver --num-probs 2
    python3 batch/hpc_benchmark_runner.py --instance-id kripke__07b2b60d
"""

import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class BenchmarkResult:
    """Result from a single benchmark run comparing agent vs expert"""
    instance_id: str
    repo_name: str
    optimization_type: str
    run_number: int = 1

    # Run status
    success: bool = False
    error_message: Optional[str] = None
    duration_seconds: float = 0.0

    # Expert patch info
    expert_commit: str = ""
    expert_message: str = ""
    expert_files_changed: list = field(default_factory=list)
    expert_insertions: int = 0
    expert_deletions: int = 0

    # Agent patch info
    agent_patch: str = ""
    agent_files_changed: list = field(default_factory=list)
    agent_insertions: int = 0
    agent_deletions: int = 0

    # Comparison metrics
    file_overlap: float = 0.0  # % of files both touched
    patch_similarity: float = 0.0  # Sequence similarity of diffs

    # Performance (if measurable)
    agent_builds: Optional[bool] = None
    agent_correctness: Optional[str] = None
    agent_speedup: Optional[float] = None

    trajectory_file: Optional[str] = None


class HPCBenchmarkRunner:
    """Runs benchmark comparisons between agent and expert patches"""

    # Repository configurations (pristine paths derived from sweagent_root in __init__)
    REPO_CONFIG_TEMPLATES = {
        "kripke": {
            "pristine_subdir": "Kripke",
            "config_template": "config/hpc/kripke_{profiling}.yaml",
            "build_tool": "kripke_build",
        },
        "laghos": {
            "pristine_subdir": "Laghos",
            "config_template": "config/hpc/laghos_{profiling}.yaml",
            "build_tool": "laghos_build",
        },
        "lulesh": {
            "pristine_subdir": "Lulesh",
            "config_template": "config/hpc/lulesh_{profiling}.yaml",
            "build_tool": "lulesh_build",
        },
        "quicksilver": {
            "pristine_subdir": "Quicksilver",
            "config_template": "config/hpc/quicksilver_{profiling}.yaml",
            "build_tool": "qs_build",
        },
    }

    def __init__(
        self,
        output_dir: Path,
        trajectory_dir: Path,
        profiling: str = "no_profiling",
        run_number: int = 1
    ):
        self.output_dir = output_dir
        self.trajectory_dir = trajectory_dir
        self.profiling = profiling
        self.run_number = run_number
        self.sweagent_root = Path(__file__).parent.parent
        self.results: list[BenchmarkResult] = []

        # Build repo configs with absolute pristine paths
        self.repo_configs = {}
        for name, tmpl in self.REPO_CONFIG_TEMPLATES.items():
            self.repo_configs[name] = {
                "pristine": str(self.sweagent_root / tmpl["pristine_subdir"]),
                "config_template": tmpl["config_template"],
                "build_tool": tmpl["build_tool"],
            }

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.trajectory_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir = self.output_dir / "workspaces"
        self.work_dir.mkdir(exist_ok=True)

        # Setup logging
        self.log_file = self.output_dir / "benchmark.log"

    def log(self, message: str) -> None:
        """Log message to both console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")

    def setup_workspace(self, instance: dict) -> Optional[Path]:
        """Create a workspace with repo checked out to base_commit"""
        repo_name = instance["repo_name"]
        base_commit = instance["base_commit"]
        instance_id = instance["instance_id"]

        config = self.repo_configs.get(repo_name)
        if not config:
            self.log(f"  ERROR: Unknown repo {repo_name}")
            return None

        pristine_path = Path(config["pristine"])
        if not pristine_path.exists():
            self.log(f"  ERROR: Pristine repo not found: {pristine_path}")
            return None

        # Create workspace directory
        workspace = self.work_dir / instance_id
        if workspace.exists():
            shutil.rmtree(workspace)

        self.log(f"  Creating workspace at {workspace}")

        try:
            # Clone the repo locally (shallow if possible)
            subprocess.run(
                ["git", "clone", "--no-checkout", str(pristine_path), str(workspace)],
                check=True,
                capture_output=True
            )

            # Checkout the base commit (pre-optimization state)
            subprocess.run(
                ["git", "checkout", base_commit],
                cwd=workspace,
                check=True,
                capture_output=True
            )

            self.log(f"  Checked out base commit: {base_commit[:8]}")
            return workspace

        except subprocess.CalledProcessError as e:
            self.log(f"  ERROR setting up workspace: {e.stderr.decode() if e.stderr else str(e)}")
            return None

    def create_instance_config(self, instance: dict, workspace: Path) -> Path:
        """Create a temporary config file for this specific instance"""
        repo_name = instance["repo_name"]
        instance_id = instance["instance_id"]
        base_config = self.repo_configs[repo_name]["config_template"].format(
            profiling=self.profiling
        )

        # Read base config
        base_config_path = self.sweagent_root / base_config
        with open(base_config_path) as f:
            config_content = f.read()

        # Modify to use the workspace
        # Replace the repo path with workspace
        original_path = f"/global/u2/k/krydzy/SWE-agent/{repo_name.capitalize()}_test"
        config_content = config_content.replace(original_path, str(workspace))

        # Also update ROOT environment variable
        root_var = f"{repo_name.upper()}_ROOT"
        config_content = config_content.replace(
            f"{root_var}: {original_path}",
            f"{root_var}: {workspace}"
        )

        # Handle special case for lulesh (cuda subdirectory)
        if repo_name == "lulesh":
            config_content = config_content.replace(
                f"{workspace}/cuda",
                f"{workspace}/cuda"  # Keep cuda subdirectory
            )

        # Update trajectory output directory
        # Find and replace output_dir in config if present
        traj_instance_dir = self.trajectory_dir / instance_id
        config_content = config_content.replace(
            "trajectories/krydzy",
            str(traj_instance_dir)
        )

        # Write modified config
        instance_config = self.output_dir / f"{instance_id}_config.yaml"
        with open(instance_config, "w") as f:
            f.write(config_content)

        return instance_config

    def run_agent(self, instance: dict, workspace: Path, config_path: Path) -> tuple[bool, str, Optional[str]]:
        """Run SWE-agent on the workspace and capture the patch"""
        instance_id = instance["instance_id"]
        sweagent_venv = os.environ.get(
            "SWEAGENT_VENV",
            "/global/u2/k/krydzy/envs/sweagent"
        )
        vllm_host = os.environ.get("VLLM_HOST", "127.0.0.1")
        vllm_port = os.environ.get("VLLM_PORT", "8008")
        home_dir = os.environ.get("HOME", str(Path.home()))

        # Build shell script with podman wrapper setup and HPCToolkit
        shell_script = f"""
cd {self.sweagent_root}
source {sweagent_venv}/bin/activate

# Load modules for HPC environment
module load openmpi/5.0.7 2>/dev/null || true
module load cudatoolkit/12.4 2>/dev/null || true
module load python 2>/dev/null || true

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

export OPENAI_API_BASE=http://{vllm_host}:{vllm_port}/v1
export OPENAI_API_KEY="dummy-key-ok"
sweagent run --config {config_path} \\
    --agent.model.per_instance_cost_limit=0 \\
    --agent.model.max_input_tokens=120000 \\
    --agent.model.max_output_tokens=120000
"""

        try:
            proc = subprocess.run(
                ["bash", "-c", shell_script],
                capture_output=True,
                text=True,
                timeout=3600
            )

            success = proc.returncode == 0

            # Get the agent's patch (diff from base_commit)
            patch_result = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=workspace,
                capture_output=True,
                text=True
            )
            agent_patch = patch_result.stdout

            # Find trajectory file in our custom trajectory directory
            traj_instance_dir = self.trajectory_dir / instance_id
            traj_files = list(traj_instance_dir.glob("**/*.traj")) if traj_instance_dir.exists() else []

            # Fallback to default location
            if not traj_files:
                traj_dir = self.sweagent_root / "trajectories"
                traj_files = list(traj_dir.glob("**/*.traj"))

            traj_file = str(max(traj_files, key=lambda p: p.stat().st_mtime)) if traj_files else None

            return success, agent_patch, traj_file

        except subprocess.TimeoutExpired:
            return False, "", None
        except Exception as e:
            self.log(f"    ERROR running agent: {e}")
            return False, "", None

    def compare_patches(self, expert_diff: str, agent_diff: str) -> tuple[float, list, list]:
        """Compare expert and agent patches"""
        # Parse files from diffs
        def extract_files(diff: str) -> set:
            files = set()
            for line in diff.split("\n"):
                if line.startswith("+++ b/") or line.startswith("--- a/"):
                    path = line.split("/", 1)[1] if "/" in line else ""
                    if path and path != "/dev/null":
                        files.add(path)
            return files

        expert_files = extract_files(expert_diff)
        agent_files = extract_files(agent_diff)

        # Calculate file overlap
        if expert_files or agent_files:
            overlap = len(expert_files & agent_files) / len(expert_files | agent_files)
        else:
            overlap = 0.0

        # Calculate patch similarity using sequence matcher
        if expert_diff and agent_diff:
            similarity = difflib.SequenceMatcher(None, expert_diff, agent_diff).ratio()
        else:
            similarity = 0.0

        return overlap, list(expert_files), list(agent_files)

    def run_benchmark(self, instance: dict) -> BenchmarkResult:
        """Run a single benchmark instance"""
        instance_id = instance["instance_id"]
        self.log(f"\n{'='*60}")
        self.log(f"Benchmark: {instance_id}")
        self.log(f"{'='*60}")
        self.log(f"  Expert commit: {instance['commit_hash'][:8]}")
        self.log(f"  Message: {instance['commit_message'][:60]}...")
        self.log(f"  Type: {instance['optimization_type']}")

        result = BenchmarkResult(
            instance_id=instance_id,
            repo_name=instance["repo_name"],
            optimization_type=instance["optimization_type"],
            run_number=self.run_number,
            success=False,
            expert_commit=instance["commit_hash"],
            expert_message=instance["commit_message"],
            expert_files_changed=instance["files_changed"],
            expert_insertions=instance["insertions"],
            expert_deletions=instance["deletions"],
        )

        start_time = time.time()

        # Setup workspace
        workspace = self.setup_workspace(instance)
        if not workspace:
            result.error_message = "Failed to setup workspace"
            result.duration_seconds = time.time() - start_time
            return result

        # Create instance-specific config
        config_path = self.create_instance_config(instance, workspace)
        self.log(f"  Created config: {config_path}")

        # Run agent
        self.log(f"  Running SWE-agent...")
        success, agent_patch, traj_file = self.run_agent(instance, workspace, config_path)

        result.duration_seconds = time.time() - start_time
        result.success = success
        result.agent_patch = agent_patch
        result.trajectory_file = traj_file

        if success:
            self.log(f"  Agent completed successfully in {result.duration_seconds:.1f}s")
        else:
            self.log(f"  Agent failed or timed out")
            result.error_message = "Agent run failed"

        # Compare patches
        expert_diff = instance.get("diff", "")
        overlap, expert_files, agent_files = self.compare_patches(expert_diff, agent_patch)

        result.file_overlap = overlap
        result.agent_files_changed = agent_files

        # Count agent insertions/deletions
        for line in agent_patch.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                result.agent_insertions += 1
            elif line.startswith("-") and not line.startswith("---"):
                result.agent_deletions += 1

        # Calculate patch similarity
        if expert_diff and agent_patch:
            result.patch_similarity = difflib.SequenceMatcher(
                None, expert_diff, agent_patch
            ).ratio()

        self.log(f"  Comparison:")
        self.log(f"    File overlap: {overlap*100:.1f}%")
        self.log(f"    Patch similarity: {result.patch_similarity*100:.1f}%")
        self.log(f"    Expert: +{result.expert_insertions}/-{result.expert_deletions} in {len(expert_files)} files")
        self.log(f"    Agent:  +{result.agent_insertions}/-{result.agent_deletions} in {len(agent_files)} files")

        # Save agent patch
        patch_file = self.output_dir / f"{instance_id}_agent.patch"
        with open(patch_file, "w") as f:
            f.write(agent_patch)

        return result

    def run_all(
        self,
        instances: list[dict],
        instance_ids: Optional[list[str]] = None,
        apps: Optional[list[str]] = None,
        num_probs: Optional[int] = None
    ) -> None:
        """Run benchmarks for all instances with filtering"""

        # Filter by instance_ids if specified
        if instance_ids:
            instances = [i for i in instances if i["instance_id"] in instance_ids]

        # Filter by app names if specified
        if apps:
            instances = [i for i in instances if i["repo_name"] in apps]

        # Limit number of problems per app if specified
        if num_probs is not None:
            # Group by repo_name and take first num_probs from each
            by_repo = defaultdict(list)
            for inst in instances:
                by_repo[inst["repo_name"]].append(inst)

            limited_instances = []
            for repo_name, repo_instances in by_repo.items():
                limited_instances.extend(repo_instances[:num_probs])
            instances = limited_instances

        self.log(f"Starting benchmark run {self.run_number}: {len(instances)} instances")

        for i, instance in enumerate(instances):
            self.log(f"\nProgress: {i+1}/{len(instances)}")
            result = self.run_benchmark(instance)
            self.results.append(result)
            self._save_results()

        self._print_summary()

    def _save_results(self) -> None:
        """Save results to JSON"""
        results_file = self.output_dir / "benchmark_results.json"
        with open(results_file, "w") as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)

    def _print_summary(self) -> None:
        """Print summary statistics"""
        self.log(f"\n{'='*60}")
        self.log("BENCHMARK SUMMARY")
        self.log(f"{'='*60}")

        successful = [r for r in self.results if r.success]

        self.log(f"Run number: {self.run_number}")
        self.log(f"Total instances: {len(self.results)}")
        self.log(f"Successful runs: {len(successful)}")

        if successful:
            avg_overlap = sum(r.file_overlap for r in successful) / len(successful)
            avg_similarity = sum(r.patch_similarity for r in successful) / len(successful)

            self.log(f"\nComparison Metrics (successful runs):")
            self.log(f"  Average file overlap: {avg_overlap*100:.1f}%")
            self.log(f"  Average patch similarity: {avg_similarity*100:.1f}%")

            # By optimization type
            self.log(f"\nBy Optimization Type:")
            by_type = {}
            for r in successful:
                if r.optimization_type not in by_type:
                    by_type[r.optimization_type] = []
                by_type[r.optimization_type].append(r)

            for opt_type, type_results in by_type.items():
                avg_sim = sum(r.patch_similarity for r in type_results) / len(type_results)
                self.log(f"  {opt_type}: {len(type_results)} runs, avg similarity: {avg_sim*100:.1f}%")


def main():
    parser = argparse.ArgumentParser(
        description="Run HPC benchmark comparing agent vs expert patches"
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("dataset/curated_perf_commits.json"),
        help="Path to curated dataset JSON"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=None,
        help="Output directory for results"
    )
    parser.add_argument(
        "--trajectory-dir",
        type=Path,
        default=None,
        help="Directory for trajectory outputs"
    )
    parser.add_argument(
        "--instance-id",
        type=str,
        action="append",
        help="Run specific instance(s) by ID (can specify multiple)"
    )
    parser.add_argument(
        "--app",
        type=str,
        action="append",
        choices=["quicksilver", "lulesh", "kripke", "laghos"],
        help="Filter by application (can specify multiple)"
    )
    parser.add_argument(
        "--num-probs",
        type=int,
        default=None,
        help="Maximum number of problems (commits) per application"
    )
    parser.add_argument(
        "--profiling",
        choices=["with_profiling", "no_profiling"],
        default="no_profiling",
        help="Profiling configuration to use"
    )
    parser.add_argument(
        "--run-number",
        type=int,
        default=1,
        help="Run number (for multiple runs)"
    )

    args = parser.parse_args()

    # Load dataset
    if not args.dataset.exists():
        print(f"ERROR: Dataset not found: {args.dataset}")
        sys.exit(1)

    with open(args.dataset) as f:
        instances = json.load(f)

    print(f"Loaded {len(instances)} instances from {args.dataset}")

    # Setup output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"batch_results/benchmark_{timestamp}")

    # Setup trajectory directory
    if args.trajectory_dir:
        trajectory_dir = args.trajectory_dir
    else:
        trajectory_dir = Path(f"trajectories/benchmark_{output_dir.name}")

    # Run benchmarks
    runner = HPCBenchmarkRunner(
        output_dir,
        trajectory_dir,
        args.profiling,
        args.run_number
    )
    runner.run_all(
        instances,
        instance_ids=args.instance_id,
        apps=args.app,
        num_probs=args.num_probs
    )

    print(f"\nResults saved to: {output_dir}")


if __name__ == "__main__":
    main()
