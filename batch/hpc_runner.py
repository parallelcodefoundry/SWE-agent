#!/usr/bin/env python3
"""
HPC Batch Runner - Python orchestrator for SWE-agent experiments

Runs SWE-agent on multiple HPC proxy applications, collecting performance metrics
and generating structured results for analysis.

Usage:
    python3 batch/hpc_runner.py --apps kripke,laghos --runs 3 --both
    python3 batch/hpc_runner.py --all --no-profiling --runs 5
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class RunResult:
    """Result from a single SWE-agent run"""
    app: str
    config_type: str  # "with_profiling" or "no_profiling"
    run_number: int
    success: bool
    correctness: Optional[str] = None  # "PASSED", "FAILED", or None
    baseline_time: Optional[float] = None
    modified_time: Optional[float] = None
    speedup: Optional[float] = None
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    trajectory_file: Optional[str] = None
    # Full metrics (optional)
    token_count: Optional[int] = None
    api_calls: Optional[int] = None
    trajectory_steps: Optional[int] = None
    model_name: Optional[str] = None


@dataclass
class BatchConfig:
    """Configuration for a batch run"""
    apps: list[str]
    runs: int
    profiling_configs: list[str]  # ["with_profiling", "no_profiling"]
    output_dir: Path
    trajectory_dir: Path
    full_metrics: bool = False
    sweagent_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    vllm_host: str = "127.0.0.1"
    vllm_port: int = 8008


class HPCBatchRunner:
    """Orchestrates SWE-agent runs across HPC applications"""

    # Patterns to extract metrics from trajectory/output
    PATTERNS = {
        "correctness": re.compile(r"CORRECTNESS:\s*(PASSED|FAILED)", re.IGNORECASE),
        "baseline_time": re.compile(r"BASELINE TIME:\s*([\d.]+)\s*s", re.IGNORECASE),
        "modified_time": re.compile(r"MODIFIED TIME:\s*([\d.]+)\s*s", re.IGNORECASE),
        "speedup": re.compile(r"SPEEDUP:\s*([\d.]+)x", re.IGNORECASE),
    }

    # Test repo paths relative to SWE-agent root
    TEST_REPOS = {
        "kripke": "Kripke_test",
        "laghos": "Laghos_test",
        "lulesh": "Lulesh_test",
        "quicksilver": "Quicksilver_test",
    }

    def __init__(self, config: BatchConfig):
        self.config = config
        self.results: list[RunResult] = []
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Setup output directory (use as-is if provided, otherwise create timestamped subdir)
        # When called from hpc_batch_runner.sh, output_dir already includes timestamp/jobid
        if config.output_dir.name.startswith("batch_") or "batch_results" not in str(config.output_dir):
            # Already a specific output dir (from shell script) - use directly
            self.output_dir = config.output_dir
        else:
            # Default batch_results dir - create timestamped subdir
            job_id = os.environ.get("SLURM_JOB_ID", "local")
            self.output_dir = config.output_dir / f"{self.run_id}_{job_id}"

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir = self.output_dir / "runs"
        self.runs_dir.mkdir(exist_ok=True)

        # Setup trajectory directory
        self.trajectory_dir = config.trajectory_dir
        self.trajectory_dir.mkdir(parents=True, exist_ok=True)

        # Directory for modified configs
        self.configs_dir = self.output_dir / "configs"
        self.configs_dir.mkdir(exist_ok=True)

        # Setup logging
        self.log_file = self.output_dir / "batch.log"

    def log(self, message: str) -> None:
        """Log message to both console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        with open(self.log_file, "a") as f:
            f.write(log_line + "\n")

    def reset_test_repo(self, app: str) -> bool:
        """Reset a test repository to clean state"""
        repo_dir = self.config.sweagent_root / self.TEST_REPOS[app]

        if not repo_dir.exists():
            self.log(f"ERROR: Test repo not found: {repo_dir}")
            return False

        self.log(f"Resetting {app} test repo: {repo_dir}")

        try:
            # Git checkout and clean
            subprocess.run(
                ["git", "checkout", "."],
                cwd=repo_dir,
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "clean", "-fd"],
                cwd=repo_dir,
                check=True,
                capture_output=True
            )

            # Remove build directory if exists
            build_dir = repo_dir / "build"
            if build_dir.exists():
                subprocess.run(
                    ["rm", "-rf", str(build_dir)],
                    check=True,
                    capture_output=True
                )

            self.log(f"  Successfully reset {app} test repo")
            return True

        except subprocess.CalledProcessError as e:
            self.log(f"  ERROR resetting {app}: {e.stderr.decode() if e.stderr else str(e)}")
            return False

    def get_config_path(self, app: str, profiling: str) -> Path:
        """Get path to SWE-agent config for app/profiling combination"""
        config_name = f"{app}_{profiling}.yaml"
        return self.config.sweagent_root / "config" / "hpc" / config_name

    def create_run_config(self, app: str, profiling: str, run_num: int) -> Path:
        """Create a modified config file with run-specific trajectory directory"""
        base_config_path = self.get_config_path(app, profiling)
        run_name = f"{app}_{profiling}_run{run_num}"

        # Read base config
        with open(base_config_path) as f:
            config_content = f.read()

        # Create run-specific trajectory directory
        run_traj_dir = self.trajectory_dir / run_name
        run_traj_dir.mkdir(parents=True, exist_ok=True)

        # Replace trajectory output directory in config
        # Look for common patterns in SWE-agent configs
        # Pattern 1: trajectories/krydzy or similar
        config_content = re.sub(
            r'trajectories/[^"\'\s]+',
            str(run_traj_dir),
            config_content
        )

        # Pattern 2: output_dir or trajectory_dir settings
        config_content = re.sub(
            r'(output_dir:\s*)[^\n]+',
            f'\\1{run_traj_dir}',
            config_content
        )

        # Override api_base to point to the (possibly remote) vLLM server
        config_content = config_content.replace(
            'api_base: "http://127.0.0.1:8008/v1"',
            f'api_base: "http://{self.config.vllm_host}:{self.config.vllm_port}/v1"'
        )

        # Write modified config
        run_config_path = self.configs_dir / f"{run_name}_config.yaml"
        with open(run_config_path, "w") as f:
            f.write(config_content)

        return run_config_path

    def create_workspace_copy(self, app: str, run_name: str) -> Optional[Path]:
        """Create an isolated workspace copy from the test repo"""
        test_repo = self.config.sweagent_root / self.TEST_REPOS[app]
        if not test_repo.exists():
            self.log(f"  ERROR: Test repo not found: {test_repo}")
            return None

        workspace_dir = self.output_dir / "workspaces"
        workspace_dir.mkdir(exist_ok=True)
        workspace = workspace_dir / run_name

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
                return None
        except Exception as e:
            self.log(f"  ERROR copying test repo: {e}")
            return None

        # Apply Kripke git config fixes if needed
        if app == "kripke" and (workspace / ".git").exists():
            subprocess.run(["git", "config", "--local", "status.submodulesummary", "false"], cwd=workspace, capture_output=True)
            subprocess.run(["git", "config", "--local", "submodule.recurse", "false"], cwd=workspace, capture_output=True)
            subprocess.run(["git", "config", "--local", "diff.ignoreSubmodules", "all"], cwd=workspace, capture_output=True)

        return workspace

    def create_run_config_with_workspace(self, app: str, profiling: str, run_num: int, workspace: Path) -> Path:
        """Create a modified config file pointing to an isolated workspace"""
        run_name = f"{app}_{profiling}_run{run_num}"
        config_path = self.create_run_config(app, profiling, run_num)

        # Read the already-created config and substitute workspace paths
        with open(config_path) as f:
            config_content = f.read()

        original_path = str(self.config.sweagent_root / f"{app.capitalize()}_test")
        config_content = config_content.replace(original_path, str(workspace))

        root_var = f"{app.upper()}_ROOT"
        config_content = config_content.replace(
            f"{root_var}: {original_path}",
            f"{root_var}: {workspace}"
        )

        with open(config_path, "w") as f:
            f.write(config_content)

        return config_path

    def run_sweagent(self, app: str, profiling: str, run_num: int) -> RunResult:
        """Execute a single SWE-agent run"""
        run_name = f"{app}_{profiling}_run{run_num}"
        run_output_dir = self.runs_dir / run_name
        run_output_dir.mkdir(exist_ok=True)

        result = RunResult(
            app=app,
            config_type=profiling,
            run_number=run_num,
            success=False
        )

        # Create isolated workspace copy
        workspace = self.create_workspace_copy(app, run_name)
        if workspace is None:
            result.error_message = "Failed to create workspace copy"
            return result

        # Create run-specific config pointing to workspace
        config_path = self.create_run_config_with_workspace(app, profiling, run_num, workspace)
        self.log(f"Starting run: {run_name}")
        self.log(f"  Config: {config_path}")
        self.log(f"  Workspace: {workspace}")
        start_time = time.time()

        # Get environment settings
        sweagent_venv = os.environ.get(
            "SWEAGENT_VENV",
            os.path.join(os.environ.get("HOME", ""), "envs", "sweagent")
        )
        home_dir = os.environ.get("HOME", str(Path.home()))

        # Build shell script with full HPC environment setup (matching hpc_benchmark_runner.py)
        shell_script = f"""
cd {self.config.sweagent_root}
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

export OPENAI_API_BASE=http://{self.config.vllm_host}:{self.config.vllm_port}/v1
export OPENAI_API_KEY="dummy-key-ok"

sweagent run --config {config_path} \\
    --agent.model.max_input_tokens=120000 \\
    --agent.model.max_output_tokens=120000
"""

        # Save shell script for debugging
        script_path = run_output_dir / "run_script.sh"
        with open(script_path, "w") as f:
            f.write(shell_script)

        # Write real-time agent log
        agent_realtime_log = run_output_dir / "agent_realtime.log"

        try:
            # Run SWE-agent through bash — stream output to file in real-time
            with open(agent_realtime_log, "w") as log_fh:
                proc = subprocess.run(
                    ["bash", "-c", shell_script],
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=3600  # 1 hour timeout per run
                )

            result.duration_seconds = time.time() - start_time

            # Check for success (return code 0)
            if proc.returncode == 0:
                result.success = True
                self.log(f"  Run completed successfully in {result.duration_seconds:.1f}s")
            else:
                result.error_message = f"SWE-agent exited with code {proc.returncode}"
                self.log(f"  Run failed: {result.error_message}")

            # Parse metrics from output
            combined_output = proc.stdout + proc.stderr
            self._extract_metrics(result, combined_output)

            # Find and save trajectory file
            trajectory_file = self._find_latest_trajectory(run_name)
            if trajectory_file:
                result.trajectory_file = str(trajectory_file)
                # Copy trajectory to run output
                subprocess.run(
                    ["cp", str(trajectory_file), str(run_output_dir / "trajectory.traj")],
                    capture_output=True
                )

                # Extract additional metrics from trajectory if requested
                if self.config.full_metrics:
                    self._extract_trajectory_metrics(result, trajectory_file)

        except subprocess.TimeoutExpired:
            result.duration_seconds = time.time() - start_time
            result.error_message = "Run timed out after 1 hour"
            self.log(f"  Run timed out")

        except Exception as e:
            result.duration_seconds = time.time() - start_time
            result.error_message = str(e)
            self.log(f"  Run error: {e}")

        return result

    def _extract_metrics(self, result: RunResult, output: str) -> None:
        """Extract performance metrics from SWE-agent output"""
        for metric, pattern in self.PATTERNS.items():
            match = pattern.search(output)
            if match:
                value = match.group(1)
                if metric == "correctness":
                    result.correctness = value.upper()
                elif metric == "baseline_time":
                    result.baseline_time = float(value)
                elif metric == "modified_time":
                    result.modified_time = float(value)
                elif metric == "speedup":
                    result.speedup = float(value)

    def _find_latest_trajectory(self, run_name: str) -> Optional[Path]:
        """Find the most recent trajectory file for a run"""
        # First check run-specific trajectory directory
        run_traj_dir = self.trajectory_dir / run_name
        if run_traj_dir.exists():
            traj_files = list(run_traj_dir.glob("**/*.traj"))
            if traj_files:
                return max(traj_files, key=lambda p: p.stat().st_mtime)

        # Fallback to default SWE-agent trajectory directory
        default_traj_dir = self.config.sweagent_root / "trajectories"
        if default_traj_dir.exists():
            traj_files = list(default_traj_dir.glob("**/*.traj"))
            if traj_files:
                return max(traj_files, key=lambda p: p.stat().st_mtime)

        return None

    def _extract_trajectory_metrics(self, result: RunResult, traj_file: Path) -> None:
        """Extract additional metrics from trajectory file"""
        try:
            with open(traj_file) as f:
                # Trajectory files are typically JSONL
                lines = f.readlines()
                result.trajectory_steps = len(lines)

                # Try to extract model info and token counts from trajectory
                total_tokens = 0
                api_calls = 0
                for line in lines:
                    try:
                        entry = json.loads(line)
                        if "usage" in entry:
                            total_tokens += entry["usage"].get("total_tokens", 0)
                            api_calls += 1
                        if "model" in entry and not result.model_name:
                            result.model_name = entry["model"]
                    except json.JSONDecodeError:
                        continue

                result.token_count = total_tokens if total_tokens > 0 else None
                result.api_calls = api_calls if api_calls > 0 else None

        except Exception as e:
            self.log(f"  Warning: Could not extract trajectory metrics: {e}")

    def run_batch(self) -> None:
        """Execute the full batch of runs"""
        total_runs = len(self.config.apps) * len(self.config.profiling_configs) * self.config.runs
        current_run = 0

        self.log(f"Starting batch run: {total_runs} total runs")
        self.log(f"  Apps: {', '.join(self.config.apps)}")
        self.log(f"  Configs: {', '.join(self.config.profiling_configs)}")
        self.log(f"  Runs per config: {self.config.runs}")
        self.log(f"  Output directory: {self.output_dir}")
        self.log(f"  Trajectory directory: {self.trajectory_dir}")

        batch_start = time.time()

        for app in self.config.apps:
            for profiling in self.config.profiling_configs:
                for run_num in range(1, self.config.runs + 1):
                    current_run += 1
                    self.log(f"\n{'='*60}")
                    self.log(f"Run {current_run}/{total_runs}: {app} ({profiling}) - Run #{run_num}")
                    self.log(f"{'='*60}")

                    # Reset test repo before each run
                    if not self.reset_test_repo(app):
                        self.log("  Skipping run due to repo reset failure")
                        result = RunResult(
                            app=app,
                            config_type=profiling,
                            run_number=run_num,
                            success=False,
                            error_message="Failed to reset test repo"
                        )
                        self.results.append(result)
                        continue

                    # Execute the run
                    result = self.run_sweagent(app, profiling, run_num)
                    self.results.append(result)

                    # Save intermediate results
                    self._save_results()

        batch_duration = time.time() - batch_start
        self.log(f"\n{'='*60}")
        self.log(f"Batch complete in {batch_duration:.1f}s ({batch_duration/60:.1f} min)")
        self.log(f"Results saved to: {self.output_dir}")

        # Print summary
        self._print_summary()

    def _save_results(self) -> None:
        """Save current results to JSON"""
        results_file = self.output_dir / "results.json"
        with open(results_file, "w") as f:
            json.dump([asdict(r) for r in self.results], f, indent=2)

    def _print_summary(self) -> None:
        """Print a summary of results"""
        successful = sum(1 for r in self.results if r.success)
        passed = sum(1 for r in self.results if r.correctness == "PASSED")
        failed = sum(1 for r in self.results if r.correctness == "FAILED")

        self.log(f"\nSummary:")
        self.log(f"  Total runs: {len(self.results)}")
        self.log(f"  Successful: {successful}")
        self.log(f"  Correctness PASSED: {passed}")
        self.log(f"  Correctness FAILED: {failed}")

        # Average speedup for passed runs
        speedups = [r.speedup for r in self.results if r.speedup and r.correctness == "PASSED"]
        if speedups:
            avg_speedup = sum(speedups) / len(speedups)
            self.log(f"  Average speedup (passed runs): {avg_speedup:.2f}x")


def wait_for_vllm(host: str, port: int, timeout: int = 300) -> bool:
    """Wait for vLLM server to be ready"""
    import urllib.request
    import urllib.error

    url = f"http://{host}:{port}/health"
    start = time.time()

    print(f"Waiting for vLLM server at {host}:{port}...")

    while time.time() - start < timeout:
        try:
            req = urllib.request.urlopen(url, timeout=5)
            if req.status == 200:
                print("vLLM server is ready!")
                return True
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(5)

    print(f"ERROR: vLLM server not ready after {timeout}s")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="HPC Batch Runner for SWE-agent experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 batch/hpc_runner.py --all --both --runs 3
  python3 batch/hpc_runner.py --apps kripke,lulesh --no-profiling --runs 5
  python3 batch/hpc_runner.py --apps laghos --with-profiling --runs 1 --full-metrics
        """
    )

    # App selection
    app_group = parser.add_mutually_exclusive_group(required=True)
    app_group.add_argument(
        "--apps",
        type=str,
        help="Comma-separated list of apps: kripke,laghos,lulesh,quicksilver"
    )
    app_group.add_argument(
        "--all",
        action="store_true",
        help="Run all applications"
    )

    # Profiling configuration
    prof_group = parser.add_mutually_exclusive_group()
    prof_group.add_argument(
        "--profiling", "--with-profiling",
        action="store_true",
        help="Run only with profiling tools"
    )
    prof_group.add_argument(
        "--no-profiling",
        action="store_true",
        help="Run only without profiling tools"
    )
    prof_group.add_argument(
        "--both",
        action="store_true",
        default=True,
        help="Run both configurations (default)"
    )

    # Run configuration
    parser.add_argument(
        "--runs", "-n",
        type=int,
        default=1,
        help="Number of runs per configuration (default: 1)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Output directory for results"
    )
    parser.add_argument(
        "--trajectory-dir", "-t",
        type=str,
        default=None,
        help="Directory for trajectory files (enables real-time monitoring)"
    )
    parser.add_argument(
        "--full-metrics",
        action="store_true",
        help="Collect additional metrics (token counts, API calls)"
    )

    # vLLM configuration
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
        "--skip-vllm-check",
        action="store_true",
        help="Skip vLLM health check (assume server is ready)"
    )

    args = parser.parse_args()

    # Determine apps
    if args.all:
        apps = ["kripke", "laghos", "lulesh", "quicksilver"]
    else:
        apps = [a.strip().lower() for a in args.apps.split(",")]
        valid_apps = {"kripke", "laghos", "lulesh", "quicksilver"}
        invalid = set(apps) - valid_apps
        if invalid:
            parser.error(f"Invalid apps: {invalid}. Valid: {valid_apps}")

    # Determine profiling configs
    if args.profiling:
        profiling_configs = ["with_profiling"]
    elif args.no_profiling:
        profiling_configs = ["no_profiling"]
    else:
        profiling_configs = ["with_profiling", "no_profiling"]

    # Determine output directory
    sweagent_root = Path(__file__).parent.parent
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = sweagent_root / "batch_results"

    # Determine trajectory directory
    if args.trajectory_dir:
        trajectory_dir = Path(args.trajectory_dir)
    else:
        trajectory_dir = sweagent_root / "trajectories" / "batch_runs"

    # Create configuration
    config = BatchConfig(
        apps=apps,
        runs=args.runs,
        profiling_configs=profiling_configs,
        output_dir=output_dir,
        trajectory_dir=trajectory_dir,
        full_metrics=args.full_metrics,
        sweagent_root=sweagent_root,
        vllm_host=args.vllm_host,
        vllm_port=args.vllm_port,
    )

    # Wait for vLLM server
    if not args.skip_vllm_check:
        if not wait_for_vllm(args.vllm_host, args.vllm_port):
            print("ERROR: vLLM server not available. Use --skip-vllm-check to bypass.")
            sys.exit(1)

    # Run batch
    runner = HPCBatchRunner(config)
    runner.run_batch()

    # Generate reports (optional, don't fail if not available)
    try:
        from report_generator import generate_reports
        generate_reports(runner.output_dir, runner.results)
    except ImportError:
        print("Note: report_generator not available, skipping report generation")


if __name__ == "__main__":
    main()
