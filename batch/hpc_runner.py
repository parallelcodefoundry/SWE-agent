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

        # Setup output directory
        job_id = os.environ.get("SLURM_JOB_ID", "local")
        self.output_dir = config.output_dir / f"{self.run_id}_{job_id}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir = self.output_dir / "runs"
        self.runs_dir.mkdir(exist_ok=True)

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

    def run_sweagent(self, app: str, profiling: str, run_num: int) -> RunResult:
        """Execute a single SWE-agent run"""
        config_path = self.get_config_path(app, profiling)
        run_name = f"{app}_{profiling}_run{run_num}"
        run_output_dir = self.runs_dir / run_name
        run_output_dir.mkdir(exist_ok=True)

        result = RunResult(
            app=app,
            config_type=profiling,
            run_number=run_num,
            success=False
        )

        if not config_path.exists():
            self.log(f"ERROR: Config not found: {config_path}")
            result.error_message = f"Config not found: {config_path}"
            return result

        self.log(f"Starting run: {run_name}")
        start_time = time.time()

        # Build shell script that replicates manual workflow:
        # 1. cd to SWE-agent directory
        # 2. Activate venv
        # 3. Run sweagent with config
        sweagent_venv = os.environ.get(
            "SWEAGENT_VENV",
            "/global/u2/k/krydzy/envs/sweagent"
        )

        # Use relative config path from SWE-agent root
        config_rel_path = config_path.relative_to(self.config.sweagent_root)

        shell_script = f"""
cd {self.config.sweagent_root}
source {sweagent_venv}/bin/activate
export OPENAI_API_KEY=dummy
export OPENAI_BASE_URL=http://{self.config.vllm_host}:{self.config.vllm_port}/v1
sweagent run --config {config_rel_path}
"""

        try:
            # Run SWE-agent through bash to properly activate venv
            proc = subprocess.run(
                ["bash", "-c", shell_script],
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout per run
            )

            result.duration_seconds = time.time() - start_time

            # Save stdout/stderr
            with open(run_output_dir / "stdout.txt", "w") as f:
                f.write(proc.stdout)
            with open(run_output_dir / "stderr.txt", "w") as f:
                f.write(proc.stderr)

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
            trajectory_file = self._find_latest_trajectory(app)
            if trajectory_file:
                result.trajectory_file = str(trajectory_file)
                # Copy trajectory to run output
                subprocess.run(
                    ["cp", str(trajectory_file), str(run_output_dir / "trajectory.json")],
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

    def _find_latest_trajectory(self, app: str) -> Optional[Path]:
        """Find the most recent trajectory file for an app"""
        # SWE-agent stores trajectories in trajectories/ directory
        traj_dir = self.config.sweagent_root / "trajectories"
        if not traj_dir.exists():
            return None

        # Find most recent .traj file
        traj_files = list(traj_dir.glob("**/*.traj"))
        if not traj_files:
            return None

        return max(traj_files, key=lambda p: p.stat().st_mtime)

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

    # Create configuration
    config = BatchConfig(
        apps=apps,
        runs=args.runs,
        profiling_configs=profiling_configs,
        output_dir=output_dir,
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

    # Generate reports
    from report_generator import generate_reports
    generate_reports(runner.output_dir, runner.results)


if __name__ == "__main__":
    main()
