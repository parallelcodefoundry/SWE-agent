#!/usr/bin/env python3
"""
HPC Benchmark Runner - Compares agent patches vs expert patches

Runs an agent framework (SWE-agent, OpenCode, OpenHands, or Codex CLI) on
pre-optimization commits from the curated dataset, then compares the agent's
solution with the expert's actual optimization.

Usage:
    python3 batch/hpc_benchmark_runner.py --dataset dataset/curated_perf_commits.json
    python3 batch/hpc_benchmark_runner.py --app quicksilver --num-probs 2
    python3 batch/hpc_benchmark_runner.py --instance-id kripke__07b2b60d
    python3 batch/hpc_benchmark_runner.py --base --lulesh --framework opencode
"""

import argparse
import difflib
import json
import os
import re
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

# Ensure SWE-agent root is on sys.path so 'from batch.frameworks import ...' works
# even when invoked as 'python3 batch/hpc_benchmark_runner.py'
_sweagent_root = str(Path(__file__).resolve().parent.parent)
if _sweagent_root not in sys.path:
    sys.path.insert(0, _sweagent_root)


# Post-agent validation commands per app
VALIDATION_BUILD_CMD = {
    "quicksilver": "qs_build --clean",
    "lulesh": "lulesh_build --clean",
    "kripke": "kripke_build --clean --arch CUDA",
    "laghos": "laghos_build --clean",
}
VALIDATION_RUN_CMD = {
    "quicksilver": "qs_run",
    "lulesh": "lulesh_run",
    "kripke": "kripke_run --arch CUDA",
    "laghos": "laghos_run",
}


@dataclass
class BenchmarkResult:
    """Result from a single benchmark run comparing agent vs expert"""
    instance_id: str
    repo_name: str
    optimization_type: str
    framework: str = "sweagent"
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
            "test_subdir": "Kripke_test",
            "config_template": "config/hpc/kripke_{profiling}.yaml",
            "build_tool": "kripke_build",
        },
        "laghos": {
            "pristine_subdir": "Laghos",
            "test_subdir": "Laghos_test",
            "config_template": "config/hpc/laghos_{profiling}.yaml",
            "build_tool": "laghos_build",
        },
        "lulesh": {
            "pristine_subdir": "Lulesh",
            "test_subdir": "Lulesh_test",
            "config_template": "config/hpc/lulesh_{profiling}.yaml",
            "build_tool": "lulesh_build",
        },
        "quicksilver": {
            "pristine_subdir": "Quicksilver",
            "test_subdir": "Quicksilver_test",
            "config_template": "config/hpc/quicksilver_{profiling}.yaml",
            "build_tool": "qs_build",
        },
    }

    def __init__(
        self,
        output_dir: Path,
        trajectory_dir: Path,
        profiling: str = "no_profiling",
        run_number: int = 1,
        base_mode: bool = False,
        vllm_host: str = "127.0.0.1",
        vllm_port: int = 8008,
        model_name: Optional[str] = None,
        framework: str = "sweagent",
    ):
        self.output_dir = output_dir
        self.trajectory_dir = trajectory_dir
        self.profiling = profiling
        self.run_number = run_number
        self.base_mode = base_mode
        self.vllm_host = vllm_host
        self.vllm_port = vllm_port
        self.model_name = model_name
        self.framework = framework
        self.sweagent_root = Path(__file__).parent.parent
        self.results: list[BenchmarkResult] = []

        # Create framework launcher
        from batch.frameworks import get_launcher
        self.launcher = get_launcher(
            framework=framework,
            sweagent_root=self.sweagent_root,
            vllm_host=vllm_host,
            vllm_port=vllm_port,
            model_name=model_name,
            profiling=profiling,
        )

        # Build repo configs with absolute pristine and test paths
        self.repo_configs = {}
        for name, tmpl in self.REPO_CONFIG_TEMPLATES.items():
            self.repo_configs[name] = {
                "pristine": str(self.sweagent_root / tmpl["pristine_subdir"]),
                "test": str(self.sweagent_root / tmpl["test_subdir"]),
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

    def verify_pristine_builds(self, apps: list[str]) -> None:
        """Verify all required pristine executables exist before launching agents."""
        checks = {
            'kripke': 'Kripke/build/kripke.exe',
            'laghos': 'Laghos/laghos',
            'lulesh': 'Lulesh/cuda/lulesh',
            'quicksilver': 'Quicksilver/src/qs',
        }
        missing = []
        for app, rel_path in checks.items():
            if app in apps:
                exe = self.sweagent_root / rel_path
                if not exe.exists():
                    missing.append(f"  {app}: {exe}")
        if missing:
            raise RuntimeError(
                "Pristine executables missing (run setup_apps.sh first):\n"
                + "\n".join(missing)
            )

    def _symlink_laghos_deps(self, workspace: Path) -> None:
        """Create symlinks for Laghos shared dependencies (mfem, hypre, metis).

        Laghos's makefile uses relative paths like ../mfem/libmfem.a, so these
        deps must be siblings of the workspace directory.
        """
        workspace_parent = workspace.parent
        for dep in ['mfem', 'hypre', 'hypre-2.11.2', 'metis-4.0', 'metis-4.0.3', 'metis']:
            dep_source = self.sweagent_root / dep
            dep_link = workspace_parent / dep
            if dep_source.exists() and not dep_link.exists():
                try:
                    dep_link.symlink_to(dep_source)
                    self.log(f"  Symlinked {dep} -> {dep_source}")
                except OSError as e:
                    self.log(f"  Warning: Could not symlink {dep}: {e}")

    def generate_base_instances(self, apps: Optional[list[str]] = None) -> list[dict]:
        """Generate instances for base mode (current state of test repos)"""
        instances = []
        repo_names = apps if apps else list(self.REPO_CONFIG_TEMPLATES.keys())

        for repo_name in repo_names:
            if repo_name not in self.repo_configs:
                continue

            test_path = Path(self.repo_configs[repo_name]["test"])
            if not test_path.exists():
                self.log(f"  Warning: Test repo not found: {test_path}")
                continue

            instances.append({
                "instance_id": f"{repo_name}__base",
                "repo_name": repo_name,
                "optimization_type": "base_run",
                "commit_hash": "current",
                "commit_message": "Run on current state of test repo",
                "base_commit": "HEAD",
                "files_changed": [],
                "insertions": 0,
                "deletions": 0,
                "diff": "",
            })

        return instances

    def reset_test_repo(self, repo_name: str) -> bool:
        """Reset a test repository to clean state"""
        test_path = Path(self.repo_configs[repo_name]["test"])

        if not test_path.exists():
            self.log(f"  ERROR: Test repo not found: {test_path}")
            return False

        self.log(f"  Resetting test repo: {test_path}")

        try:
            subprocess.run(
                ["git", "checkout", "."],
                cwd=test_path,
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "clean", "-fd"],
                cwd=test_path,
                check=True,
                capture_output=True
            )

            # Remove build directory if exists
            build_dir = test_path / "build"
            if build_dir.exists():
                shutil.rmtree(build_dir)

            return True

        except subprocess.CalledProcessError as e:
            self.log(f"  ERROR resetting repo: {e.stderr.decode() if e.stderr else str(e)}")
            return False

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

            # Symlink Laghos shared dependencies into workspace parent
            if repo_name == "laghos":
                self._symlink_laghos_deps(workspace)

            return workspace

        except subprocess.CalledProcessError as e:
            self.log(f"  ERROR setting up workspace: {e.stderr.decode() if e.stderr else str(e)}")
            return None

    def create_instance_config(self, instance: dict, workspace: Path) -> Path:
        """Create framework-specific config for a benchmark instance.

        Delegates to the framework launcher's generate_config().
        """
        return self.launcher.generate_config(
            repo_name=instance["repo_name"],
            workspace=workspace,
            instance_id=instance["instance_id"],
            output_dir=self.output_dir,
        )

    def run_agent(self, instance: dict, workspace: Path, config_path: Path) -> tuple[bool, str, Optional[str]]:
        """Run the agent framework on the workspace and capture the patch.

        Delegates to the framework launcher's build_launch_command(),
        extract_patch(), and find_trajectory().
        """
        instance_id = instance["instance_id"]

        shell_script = self.launcher.build_launch_command(
            repo_name=instance["repo_name"],
            workspace=workspace,
            config_path=config_path,
            output_dir=self.output_dir,
            trajectory_dir=self.trajectory_dir,
            instance_id=instance_id,
        )

        # Write real-time agent log alongside benchmark.log
        agent_realtime_log = self.output_dir / f"{instance_id}_agent_realtime.log"
        self.log(f"  Agent real-time log: {agent_realtime_log}")

        try:
            with open(agent_realtime_log, "w") as log_fh:
                proc = subprocess.run(
                    ["bash", "-c", shell_script],
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=3900  # slightly beyond SESSION_TIMEOUT to allow cleanup
                )

            success = proc.returncode == 0
            agent_patch = self.launcher.extract_patch(workspace)
            traj_file = self.launcher.find_trajectory(
                self.output_dir, self.trajectory_dir, instance_id
            )

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
        repo_name = instance["repo_name"]

        self.log(f"\n{'='*60}")
        self.log(f"{'BASE RUN' if self.base_mode else 'Benchmark'}: {instance_id}")
        self.log(f"{'='*60}")

        if self.base_mode:
            self.log(f"  Mode: Base (current test repo state)")
            self.log(f"  Profiling: {self.profiling}")
        else:
            self.log(f"  Expert commit: {instance['commit_hash'][:8]}")
            self.log(f"  Message: {instance['commit_message'][:60]}...")
            self.log(f"  Type: {instance['optimization_type']}")

        result = BenchmarkResult(
            instance_id=instance_id,
            repo_name=repo_name,
            optimization_type=instance["optimization_type"],
            framework=self.framework,
            run_number=self.run_number,
            success=False,
            expert_commit=instance.get("commit_hash", ""),
            expert_message=instance.get("commit_message", ""),
            expert_files_changed=instance.get("files_changed", []),
            expert_insertions=instance.get("insertions", 0),
            expert_deletions=instance.get("deletions", 0),
        )

        start_time = time.time()

        if self.base_mode:
            # Base mode: create isolated workspace copy from test repo
            test_repo = Path(self.repo_configs[repo_name]["test"])
            if not test_repo.exists():
                result.error_message = f"Test repo not found: {test_repo}"
                result.duration_seconds = time.time() - start_time
                return result

            workspace = self.work_dir / instance_id
            if workspace.exists():
                shutil.rmtree(workspace)

            self.log(f"  Creating isolated workspace: {workspace}")
            try:
                # Use rsync instead of shutil.copytree to skip heavy git internals
                # .git/modules contains submodule git databases (massive for Kripke's 44+ submodules)
                # build/ contains stale build artifacts (agent will rebuild)
                rsync_cmd = [
                    "rsync", "-a", "--delete",
                    "--exclude=.git/modules",
                    "--exclude=build",
                    f"{test_repo}/", f"{workspace}/"
                ]
                rsync_result = subprocess.run(rsync_cmd, capture_output=True, text=True, timeout=120)
                if rsync_result.returncode != 0:
                    self.log(f"  ERROR: rsync failed: {rsync_result.stderr}")
                    result.error_message = f"rsync failed: {rsync_result.stderr}"
                    result.duration_seconds = time.time() - start_time
                    return result
            except Exception as e:
                result.error_message = f"Failed to copy test repo: {e}"
                result.duration_seconds = time.time() - start_time
                return result

            # Symlink Laghos shared dependencies into workspace parent
            if repo_name == "laghos":
                self._symlink_laghos_deps(workspace)

            # Apply Kripke git config fixes if needed
            if repo_name == "kripke" and (workspace / ".git").exists():
                subprocess.run(["git", "config", "--local", "status.submodulesummary", "false"], cwd=workspace, capture_output=True)
                subprocess.run(["git", "config", "--local", "submodule.recurse", "false"], cwd=workspace, capture_output=True)
                subprocess.run(["git", "config", "--local", "diff.ignoreSubmodules", "all"], cwd=workspace, capture_output=True)

            # Create config pointing to the isolated workspace
            config_path = self.create_base_config(repo_name, instance_id, workspace=workspace)
        else:
            # Benchmark mode: setup workspace with specific commit
            workspace = self.setup_workspace(instance)
            if not workspace:
                result.error_message = "Failed to setup workspace"
                result.duration_seconds = time.time() - start_time
                return result

            config_path = self.create_instance_config(instance, workspace)

        self.log(f"  Created config: {config_path}")
        self.log(f"  Workspace: {workspace}")

        # Run agent
        self.log(f"  Running {self.framework} agent...")
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

        # Count agent insertions/deletions
        for line in agent_patch.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                result.agent_insertions += 1
            elif line.startswith("-") and not line.startswith("---"):
                result.agent_deletions += 1

        # Post-agent validation: rebuild + run to measure actual performance
        try:
            self._validate_agent_changes(repo_name, workspace, result)
        except Exception as e:
            self.log(f"  [Validation] Error: {e}")

        if not self.base_mode:
            # Compare patches (only in benchmark mode)
            expert_diff = instance.get("diff", "")
            overlap, expert_files, agent_files = self.compare_patches(expert_diff, agent_patch)

            result.file_overlap = overlap
            result.agent_files_changed = agent_files

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
        else:
            self.log(f"  Agent changes: +{result.agent_insertions}/-{result.agent_deletions} lines")

        # Save agent patch
        patch_file = self.output_dir / f"{instance_id}_agent.patch"
        with open(patch_file, "w") as f:
            f.write(agent_patch)

        return result

    def _validate_agent_changes(self, repo_name: str, workspace: Path, result: BenchmarkResult) -> None:
        """Rebuild and run the app after agent modifications to measure performance."""
        if result.agent_insertions == 0 and result.agent_deletions == 0:
            self.log("  [Validation] Skipping (no code changes)")
            return

        # Shell preamble: modules + env vars (PATH, APP_ROOT, SWE_AGENT_ROOT, etc.)
        preamble = self.launcher.get_module_loads() + "\n" + self.launcher.get_env_exports(repo_name, workspace)

        # Lulesh: LULESH_ROOT must point to cuda/ subdir where Makefile lives
        if repo_name == "lulesh":
            preamble += f'\nexport LULESH_ROOT="{workspace / "cuda"}"'

        # --- Build ---
        self.log(f"  [Validation] Building {repo_name}...")
        try:
            build_proc = subprocess.run(
                ["bash", "-c", f"{preamble}\n{VALIDATION_BUILD_CMD[repo_name]}"],
                capture_output=True, text=True, timeout=600
            )
        except subprocess.TimeoutExpired:
            result.agent_builds = False
            self.log("  [Validation] Build TIMED OUT")
            return

        if build_proc.returncode != 0:
            result.agent_builds = False
            self.log(f"  [Validation] Build FAILED (exit {build_proc.returncode})")
            if build_proc.stderr:
                self.log(f"  [Validation] stderr tail: {build_proc.stderr[-500:]}")
            return

        result.agent_builds = True
        self.log("  [Validation] Build OK")

        # --- Run ---
        self.log(f"  [Validation] Running {repo_name}...")
        try:
            run_proc = subprocess.run(
                ["bash", "-c", f"{preamble}\n{VALIDATION_RUN_CMD[repo_name]}"],
                capture_output=True, text=True, timeout=600
            )
        except subprocess.TimeoutExpired:
            result.agent_correctness = "timeout"
            self.log("  [Validation] Run TIMED OUT")
            return

        output = (run_proc.stdout or "") + "\n" + (run_proc.stderr or "")

        # --- Parse correctness (all 4 apps print CORRECTNESS: PASSED/FAILED) ---
        if re.search(r"CORRECTNESS:\s+PASSED", output):
            result.agent_correctness = "passed"
        elif re.search(r"CORRECTNESS:\s+FAILED", output):
            result.agent_correctness = "failed"
        else:
            result.agent_correctness = "unknown"

        # --- Parse speedup ---
        if repo_name == "kripke":
            # Kripke: JSON to stdout with speedup.solve_speedup
            try:
                kripke_json = json.loads(run_proc.stdout)
                result.agent_speedup = round(kripke_json["speedup"]["solve_speedup"], 4)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        else:
            # QS/Lulesh/Laghos: parse BASELINE TIME + MODIFIED TIME from stdout
            bm = re.search(r"BASELINE TIME:\s+([\d.]+)", output)
            mm = re.search(r"MODIFIED TIME:\s+([\d.]+)", output)
            if bm and mm:
                bt, mt = float(bm.group(1)), float(mm.group(1))
                if mt > 0:
                    result.agent_speedup = round(bt / mt, 4)

        self.log(f"  [Validation] Correctness: {result.agent_correctness}")
        if result.agent_speedup is not None:
            self.log(f"  [Validation] Speedup: {result.agent_speedup:.2f}x")
        else:
            self.log("  [Validation] Speedup: N/A")

    def create_base_config(self, repo_name: str, instance_id: str, workspace: Optional[Path] = None) -> Path:
        """Create framework-specific config for base mode.

        Delegates to the framework launcher's generate_config().
        """
        ws = workspace or Path(self.repo_configs[repo_name]["test"])
        return self.launcher.generate_config(
            repo_name=repo_name,
            workspace=ws,
            instance_id=instance_id,
            output_dir=self.output_dir,
        )

    def run_all(
        self,
        instances: list[dict],
        instance_ids: Optional[list[str]] = None,
        apps: Optional[list[str]] = None,
        num_probs: Optional[int] = None
    ) -> None:
        """Run benchmarks for all instances with filtering"""

        # Pre-flight check: verify pristine executables exist
        check_apps = apps if apps else list(self.REPO_CONFIG_TEMPLATES.keys())
        self.verify_pristine_builds(check_apps)

        # In base mode, generate instances if none provided
        if self.base_mode and not instances:
            instances = self.generate_base_instances(apps)

        # Filter by instance_ids if specified (not applicable in base mode)
        if instance_ids and not self.base_mode:
            instances = [i for i in instances if i["instance_id"] in instance_ids]

        # Filter by app names if specified
        if apps:
            instances = [i for i in instances if i["repo_name"] in apps]

        # Limit number of problems per app if specified (not applicable in base mode)
        if num_probs is not None and not self.base_mode:
            # Group by repo_name and take first num_probs from each
            by_repo = defaultdict(list)
            for inst in instances:
                by_repo[inst["repo_name"]].append(inst)

            limited_instances = []
            for repo_name, repo_instances in by_repo.items():
                limited_instances.extend(repo_instances[:num_probs])
            instances = limited_instances

        mode_str = "base run" if self.base_mode else "benchmark run"
        self.log(f"Starting {mode_str} {self.run_number}: {len(instances)} instances")
        self.log(f"  Framework: {self.framework}")
        self.log(f"  Profiling: {self.profiling}")

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
        "--base",
        action="store_true",
        help="Run on current state of test repos (skip dataset/git checkout)"
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
    parser.add_argument(
        "--vllm-host",
        type=str,
        default="127.0.0.1",
        help="vLLM server host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--vllm-port",
        type=int,
        default=8008,
        help="vLLM server port (default: 8008)"
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=None,
        help="Override model name (e.g., openai/gpt-5.1). Also enables $1 cost limit."
    )
    parser.add_argument(
        "--framework",
        type=str,
        choices=["sweagent", "opencode", "openhands", "codex"],
        default="sweagent",
        help="Agent framework to use (default: sweagent)"
    )

    args = parser.parse_args()

    # Load dataset (unless in base mode)
    instances = []
    if args.base:
        print("Running in BASE mode (current state of test repos)")
    else:
        if not args.dataset.exists():
            print(f"ERROR: Dataset not found: {args.dataset}")
            sys.exit(1)

        with open(args.dataset) as f:
            instances = json.load(f)

        print(f"Loaded {len(instances)} instances from {args.dataset}")

    # Setup output directory (must be absolute — shell scripts cd to workspace)
    if args.output_dir:
        output_dir = args.output_dir.resolve()
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"batch_results/benchmark_{timestamp}").resolve()

    # Setup trajectory directory (must be absolute)
    if args.trajectory_dir:
        trajectory_dir = args.trajectory_dir.resolve()
    else:
        trajectory_dir = Path(f"trajectories/{output_dir.name}").resolve()

    # Run benchmarks
    runner = HPCBenchmarkRunner(
        output_dir,
        trajectory_dir,
        args.profiling,
        args.run_number,
        base_mode=args.base,
        vllm_host=args.vllm_host,
        vllm_port=args.vllm_port,
        model_name=args.model_name,
        framework=args.framework,
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
