#!/usr/bin/env python3
"""
Build Verification for Performance Commit Dataset

Verifies that commits in the dataset can be built successfully using
the existing harness tools.

Usage:
    python3 dataset/verify_builds.py --input dataset/hpc_perf_commits.json
    python3 dataset/verify_builds.py --repos kripke,laghos --recent-only
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class BuildVerifier:
    """Verifies builds for commits in the dataset"""

    # Build tool mappings
    BUILD_TOOLS = {
        "kripke": "kripke_build",
        "laghos": "laghos_build",
        "lulesh": "lulesh_build",
        "quicksilver": "qs_build",
    }

    # Test repository paths
    TEST_REPOS = {
        "kripke": "/pscratch/sd/k/krydzy/SWE-agent/Kripke_test",
        "laghos": "/pscratch/sd/k/krydzy/SWE-agent/Laghos_test",
        "lulesh": "/pscratch/sd/k/krydzy/SWE-agent/Lulesh_test",
        "quicksilver": "/pscratch/sd/k/krydzy/SWE-agent/Quicksilver_test",
    }

    # Pristine repository paths
    PRISTINE_REPOS = {
        "kripke": "/pscratch/sd/k/krydzy/SWE-agent/Kripke",
        "laghos": "/pscratch/sd/k/krydzy/SWE-agent/Laghos",
        "lulesh": "/pscratch/sd/k/krydzy/SWE-agent/Lulesh",
        "quicksilver": "/pscratch/sd/k/krydzy/SWE-agent/Quicksilver",
    }

    def __init__(self, sweagent_root: Path):
        self.sweagent_root = sweagent_root
        self.tools_dir = sweagent_root / "tools"

    def get_build_tool_path(self, repo_name: str) -> Optional[Path]:
        """Get path to build tool for a repository"""
        tool_name = self.BUILD_TOOLS.get(repo_name)
        if not tool_name:
            return None

        # Check harness directory
        harness_dir = self.tools_dir / f"{repo_name}_harness" / "bin"
        tool_path = harness_dir / tool_name

        if tool_path.exists():
            return tool_path
        return None

    def reset_test_repo(self, repo_name: str, commit_hash: str) -> bool:
        """Reset test repo to a specific commit"""
        test_repo = Path(self.TEST_REPOS.get(repo_name, ""))
        pristine_repo = Path(self.PRISTINE_REPOS.get(repo_name, ""))

        if not test_repo.exists() or not pristine_repo.exists():
            print(f"    Repository paths not found for {repo_name}")
            return False

        try:
            # First, reset test repo to pristine state
            subprocess.run(
                ["git", "checkout", "."],
                cwd=test_repo,
                check=True,
                capture_output=True
            )
            subprocess.run(
                ["git", "clean", "-fd"],
                cwd=test_repo,
                check=True,
                capture_output=True
            )

            # Remove build directory
            build_dir = test_repo / "build"
            if build_dir.exists():
                subprocess.run(["rm", "-rf", str(build_dir)], check=True)

            # Now checkout the specific commit in pristine repo
            # and copy changes to test repo
            subprocess.run(
                ["git", "checkout", commit_hash],
                cwd=pristine_repo,
                check=True,
                capture_output=True
            )

            # Copy source files from pristine to test
            subprocess.run(
                ["rsync", "-a", "--exclude=.git", "--exclude=build",
                 f"{pristine_repo}/", f"{test_repo}/"],
                check=True,
                capture_output=True
            )

            return True

        except subprocess.CalledProcessError as e:
            print(f"    Failed to reset repo: {e}")
            return False

    def verify_build(self, repo_name: str, commit_hash: str) -> tuple[bool, str]:
        """Verify that a commit builds successfully"""
        build_tool = self.get_build_tool_path(repo_name)
        if not build_tool:
            return False, f"Build tool not found for {repo_name}"

        # Set up environment
        env = os.environ.copy()
        env[f"{repo_name.upper()}_ROOT"] = self.TEST_REPOS[repo_name]
        env["CUDA_VISIBLE_DEVICES"] = "0"
        env["OMP_NUM_THREADS"] = "8"

        try:
            result = subprocess.run(
                [str(build_tool)],
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            # Check for success in output
            if result.returncode == 0:
                # Try to parse JSON output
                try:
                    output = json.loads(result.stdout)
                    if output.get("success"):
                        return True, "Build successful"
                    else:
                        return False, output.get("error", "Build failed")
                except json.JSONDecodeError:
                    # If not JSON, check for success indicators
                    if "success" in result.stdout.lower():
                        return True, "Build successful"
            return False, f"Build failed with code {result.returncode}"

        except subprocess.TimeoutExpired:
            return False, "Build timed out"
        except Exception as e:
            return False, str(e)

    def verify_commits(
        self,
        commits: list[dict],
        repos: Optional[list[str]] = None,
        recent_only: bool = False,
        max_commits: int = 100
    ) -> list[dict]:
        """Verify builds for a list of commits"""
        # Filter by repo if specified
        if repos:
            commits = [c for c in commits if c["repo_name"] in repos]

        # Filter to recent commits if specified
        if recent_only:
            cutoff = datetime.now() - timedelta(days=730)  # 2 years
            commits = [
                c for c in commits
                if datetime.fromisoformat(c["commit_date"].replace("Z", "+00:00")) > cutoff
            ]

        # Limit number of commits
        commits = commits[:max_commits]

        print(f"Verifying {len(commits)} commits...")
        verified = 0
        failed = 0

        for i, commit in enumerate(commits):
            print(f"\n[{i+1}/{len(commits)}] {commit['instance_id']}")
            print(f"  Commit: {commit['commit_hash'][:8]}")
            print(f"  Date: {commit['commit_date'][:10]}")

            # Reset test repo to this commit
            if not self.reset_test_repo(commit["repo_name"], commit["commit_hash"]):
                commit["build_verified"] = True
                commit["build_success"] = False
                failed += 1
                continue

            # Verify build
            success, message = self.verify_build(
                commit["repo_name"],
                commit["commit_hash"]
            )

            commit["build_verified"] = True
            commit["build_success"] = success

            if success:
                print(f"  Result: SUCCESS")
                verified += 1
            else:
                print(f"  Result: FAILED - {message}")
                failed += 1

        print(f"\nVerification complete: {verified} passed, {failed} failed")
        return commits


def main():
    parser = argparse.ArgumentParser(
        description="Verify builds for performance commit dataset"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=Path("dataset/hpc_perf_commits.json"),
        help="Input JSON file with commits"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output JSON file (default: overwrite input)"
    )
    parser.add_argument(
        "--repos",
        type=str,
        help="Comma-separated list of repos to verify"
    )
    parser.add_argument(
        "--recent-only",
        action="store_true",
        help="Only verify commits from last 2 years"
    )
    parser.add_argument(
        "--max-commits",
        type=int,
        default=100,
        help="Maximum commits to verify (default: 100)"
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Input file not found: {args.input}")
        sys.exit(1)

    with open(args.input) as f:
        commits = json.load(f)

    repos = None
    if args.repos:
        repos = [r.strip().lower() for r in args.repos.split(",")]

    sweagent_root = Path(__file__).parent.parent
    verifier = BuildVerifier(sweagent_root)

    verified_commits = verifier.verify_commits(
        commits,
        repos=repos,
        recent_only=args.recent_only,
        max_commits=args.max_commits
    )

    output_path = args.output or args.input
    with open(output_path, "w") as f:
        json.dump(verified_commits, f, indent=2)

    print(f"\nSaved verified commits to {output_path}")


if __name__ == "__main__":
    main()
