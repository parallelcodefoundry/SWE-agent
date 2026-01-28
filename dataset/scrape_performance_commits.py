#!/usr/bin/env python3
"""
Performance Commit Scraper for HPC Applications

Scrapes performance-related commits from HPC proxy application repositories
and creates a dataset compatible with SWE-agent and HuggingFace.

Usage:
    python3 dataset/scrape_performance_commits.py --all
    python3 dataset/scrape_performance_commits.py --repos kripke,laghos
    python3 dataset/scrape_performance_commits.py --output dataset/hpc_perf_commits.json
"""

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


# Keyword classification for performance commits
PRIMARY_KEYWORDS = {
    "optimize", "optimization", "performance", "speedup", "speed up",
    "faster", "efficient", "efficiency", "improve performance",
    "accelerate", "acceleration", "port to", "ported to"
}

SECONDARY_KEYWORDS = {
    # GPU/CUDA/HIP
    "cuda", "gpu", "kernel", "device", "nvcc", "hip", "rocm", "amd",
    "__shfl", "atomicadd", "warp", "block", "sm_", "compute_",
    # Threading/Parallelism
    "thread", "threading", "parallel", "omp", "openmp", "mpi",
    "concurrent", "simd", "vectorize", "vectorization", "stdpar",
    "offload", "offloading",
    # Memory
    "cache", "memory", "allocation", "buffer", "prefetch",
    "bandwidth", "coalesc", "allocate", "release",  # coalesced, coalescing
    # Algorithm/Loop
    "loop", "unroll", "tile", "tiling", "blocking", "fusion",
    "algorithm", "reduce overhead", "binary search", "lookup",
    # Timing/Benchmarking
    "latency", "throughput", "bottleneck", "timer", "benchmark",
    "fom", "figure of merit",
    # Architecture-specific
    "mi250", "a100", "v100", "ampere", "volta"
}

NEGATIVE_KEYWORDS = {
    "fix bug", "bugfix", "bug fix", "typo", "documentation", "readme",
    "license", "copyright", "comment only", "todo", "fixme",
    "revert", "formatting", "whitespace", "spelling", "ci testing",
    "add missing", "missing include"
}


@dataclass
class PerformanceCommit:
    """A performance-related commit from an HPC repository"""
    # SWE-agent compatible fields
    instance_id: str
    repo_name: str
    base_commit: str  # Parent commit (before state)
    problem_statement: str

    # Commit metadata
    commit_hash: str
    commit_message: str
    commit_date: str
    author_name: str
    files_changed: list[str]
    diff: str
    insertions: int
    deletions: int

    # Classification
    perf_keywords: list[str] = field(default_factory=list)
    optimization_type: str = "general"
    confidence_score: float = 0.0
    nearest_tag: Optional[str] = None

    # Build verification (optional)
    build_verified: bool = False
    build_success: Optional[bool] = None


class CommitScraper:
    """Scrapes performance commits from git repositories"""

    # Repository configurations
    REPOS = {
        "kripke": {
            "path": "/global/u2/k/krydzy/SWE-agent/Kripke",
            "github_url": "https://github.com/LLNL/Kripke",
            "file_patterns": ["*.cpp", "*.hpp", "*.cxx", "*.hxx", "*.cu", "*.h"],
        },
        "laghos": {
            "path": "/global/u2/k/krydzy/SWE-agent/Laghos",
            "github_url": "https://github.com/CEED/Laghos",
            "file_patterns": ["*.cpp", "*.hpp", "*.cxx", "*.cu", "*.h"],
        },
        "lulesh": {
            "path": "/global/u2/k/krydzy/SWE-agent/Lulesh",
            "github_url": "https://github.com/LLNL/LULESH",
            "file_patterns": ["*.cc", "*.cpp", "*.cu", "*.h", "*.hpp"],
        },
        "quicksilver": {
            "path": "/global/u2/k/krydzy/SWE-agent/Quicksilver",
            "github_url": "https://github.com/LLNL/Quicksilver",
            "file_patterns": ["*.cc", "*.cpp", "*.cu", "*.h", "*.hpp"],
        },
    }

    def __init__(self, output_file: Path):
        self.output_file = output_file
        self.commits: list[PerformanceCommit] = []

    def run_git(self, repo_path: Path, *args) -> str:
        """Run a git command and return output"""
        result = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()

    def get_all_commits(self, repo_path: Path) -> list[dict]:
        """Get all commits from a repository"""
        # Format: hash|parent|date|author|message
        log_format = "%H|%P|%aI|%an|%s"
        output = self.run_git(
            repo_path,
            "log", "--all", f"--format={log_format}"
        )

        commits = []
        for line in output.split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 4)
            if len(parts) >= 5:
                commits.append({
                    "hash": parts[0],
                    "parent": parts[1].split()[0] if parts[1] else None,
                    "date": parts[2],
                    "author": parts[3],
                    "message": parts[4],
                })
        return commits

    def get_commit_diff(self, repo_path: Path, commit_hash: str) -> tuple[str, list[str], int, int]:
        """Get diff and stats for a commit"""
        # Get diff
        try:
            diff = self.run_git(repo_path, "show", commit_hash, "--format=", "-p")
        except subprocess.CalledProcessError:
            diff = ""

        # Get file list
        try:
            files_output = self.run_git(
                repo_path, "show", commit_hash, "--format=", "--name-only"
            )
            files = [f for f in files_output.split("\n") if f.strip()]
        except subprocess.CalledProcessError:
            files = []

        # Get stats
        try:
            stats = self.run_git(
                repo_path, "show", commit_hash, "--format=", "--stat"
            )
            # Parse insertions/deletions from stats line
            match = re.search(r"(\d+) insertions?\(\+\)", stats)
            insertions = int(match.group(1)) if match else 0
            match = re.search(r"(\d+) deletions?\(-\)", stats)
            deletions = int(match.group(1)) if match else 0
        except subprocess.CalledProcessError:
            insertions, deletions = 0, 0

        return diff, files, insertions, deletions

    def get_nearest_tag(self, repo_path: Path, commit_hash: str) -> Optional[str]:
        """Get the nearest tag to a commit"""
        try:
            return self.run_git(
                repo_path, "describe", "--tags", "--abbrev=0", commit_hash
            )
        except subprocess.CalledProcessError:
            return None

    def classify_commit(self, message: str, diff: str) -> tuple[list[str], str, float]:
        """Classify a commit based on keywords"""
        text = (message + " " + diff).lower()
        found_keywords = []

        # Check for negative keywords first
        for keyword in NEGATIVE_KEYWORDS:
            if keyword in text:
                return [], "excluded", 0.0

        # Check primary keywords
        primary_found = []
        for keyword in PRIMARY_KEYWORDS:
            if keyword in text:
                primary_found.append(keyword)
                found_keywords.append(keyword)

        # Check secondary keywords
        secondary_found = []
        for keyword in SECONDARY_KEYWORDS:
            if keyword in text:
                secondary_found.append(keyword)
                found_keywords.append(keyword)

        # Calculate confidence score
        if primary_found:
            confidence = min(1.0, 0.5 + 0.1 * len(primary_found) + 0.05 * len(secondary_found))
        elif len(secondary_found) >= 2:
            confidence = min(0.7, 0.2 + 0.1 * len(secondary_found))
        else:
            confidence = 0.0

        # Determine optimization type
        opt_type = "general"
        if any(kw in text for kw in ["cuda", "gpu", "kernel", "device", "hip"]):
            opt_type = "gpu"
        elif any(kw in text for kw in ["thread", "omp", "openmp", "mpi", "parallel"]):
            opt_type = "threading"
        elif any(kw in text for kw in ["cache", "memory", "allocation", "buffer"]):
            opt_type = "memory"
        elif any(kw in text for kw in ["loop", "unroll", "tile", "algorithm"]):
            opt_type = "algorithm"

        return found_keywords, opt_type, confidence

    def generate_problem_statement(self, commit: PerformanceCommit) -> str:
        """Generate a problem statement for SWE-agent"""
        opt_type_desc = {
            "gpu": "GPU/CUDA optimization",
            "threading": "parallel processing optimization",
            "memory": "memory access optimization",
            "algorithm": "algorithmic optimization",
            "general": "performance optimization",
        }

        desc = opt_type_desc.get(commit.optimization_type, "performance optimization")

        # Extract key info from commit message
        msg = commit.commit_message

        statement = f"""Implement a {desc} for the {commit.repo_name} application.

The optimization should achieve the improvements described in the following commit message:

"{msg}"

Focus on the following files:
{chr(10).join(f"- {f}" for f in commit.files_changed[:10])}

The optimization should maintain correctness while improving performance.
Keywords related to this optimization: {', '.join(commit.perf_keywords[:5])}
"""
        return statement

    def scrape_repo(self, repo_name: str, min_confidence: float = 0.3) -> list[PerformanceCommit]:
        """Scrape performance commits from a repository"""
        config = self.REPOS.get(repo_name)
        if not config:
            print(f"Unknown repository: {repo_name}")
            return []

        repo_path = Path(config["path"])
        if not repo_path.exists():
            print(f"Repository not found: {repo_path}")
            return []

        print(f"\nScraping {repo_name} from {repo_path}...")

        all_commits = self.get_all_commits(repo_path)
        print(f"  Found {len(all_commits)} total commits")

        perf_commits = []
        for i, commit_data in enumerate(all_commits):
            if (i + 1) % 100 == 0:
                print(f"  Processing commit {i + 1}/{len(all_commits)}...")

            # Skip merge commits (multiple parents)
            if not commit_data["parent"]:
                continue

            # Quick classification on message only
            keywords, opt_type, confidence = self.classify_commit(
                commit_data["message"], ""
            )

            # Skip low-confidence commits
            if confidence < min_confidence:
                continue

            # Get full diff for confirmed candidates
            diff, files, insertions, deletions = self.get_commit_diff(
                repo_path, commit_data["hash"]
            )

            # Re-classify with full diff
            keywords, opt_type, confidence = self.classify_commit(
                commit_data["message"], diff
            )

            if confidence < min_confidence:
                continue

            # Filter to source files only
            source_files = [
                f for f in files
                if any(f.endswith(ext.replace("*", ""))
                       for ext in config["file_patterns"])
            ]

            if not source_files:
                continue

            # Get nearest tag
            tag = self.get_nearest_tag(repo_path, commit_data["hash"])

            # Create instance ID
            instance_id = f"{repo_name}__{commit_data['hash'][:8]}"

            commit = PerformanceCommit(
                instance_id=instance_id,
                repo_name=repo_name,
                base_commit=commit_data["parent"],
                problem_statement="",  # Generated later
                commit_hash=commit_data["hash"],
                commit_message=commit_data["message"],
                commit_date=commit_data["date"],
                author_name=commit_data["author"],
                files_changed=source_files,
                diff=diff[:50000],  # Limit diff size
                insertions=insertions,
                deletions=deletions,
                perf_keywords=keywords,
                optimization_type=opt_type,
                confidence_score=confidence,
                nearest_tag=tag,
            )

            # Generate problem statement
            commit.problem_statement = self.generate_problem_statement(commit)

            perf_commits.append(commit)

        print(f"  Found {len(perf_commits)} performance commits")
        return perf_commits

    def scrape_all(self, repos: list[str], min_confidence: float = 0.3) -> None:
        """Scrape all specified repositories"""
        for repo in repos:
            commits = self.scrape_repo(repo, min_confidence)
            self.commits.extend(commits)

        print(f"\nTotal performance commits: {len(self.commits)}")

    def save(self) -> None:
        """Save commits to JSON file"""
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

        data = [asdict(c) for c in self.commits]
        with open(self.output_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Saved {len(self.commits)} commits to {self.output_file}")

    def print_summary(self) -> None:
        """Print summary statistics"""
        print("\n" + "=" * 60)
        print("SCRAPING SUMMARY")
        print("=" * 60)

        by_repo = {}
        by_type = {}
        for c in self.commits:
            by_repo[c.repo_name] = by_repo.get(c.repo_name, 0) + 1
            by_type[c.optimization_type] = by_type.get(c.optimization_type, 0) + 1

        print("\nBy Repository:")
        for repo, count in sorted(by_repo.items()):
            print(f"  {repo}: {count}")

        print("\nBy Optimization Type:")
        for opt_type, count in sorted(by_type.items()):
            print(f"  {opt_type}: {count}")

        # Confidence distribution
        high_conf = sum(1 for c in self.commits if c.confidence_score >= 0.7)
        med_conf = sum(1 for c in self.commits if 0.5 <= c.confidence_score < 0.7)
        low_conf = sum(1 for c in self.commits if c.confidence_score < 0.5)

        print("\nBy Confidence:")
        print(f"  High (>=0.7): {high_conf}")
        print(f"  Medium (0.5-0.7): {med_conf}")
        print(f"  Low (<0.5): {low_conf}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape performance commits from HPC repositories"
    )

    repo_group = parser.add_mutually_exclusive_group(required=True)
    repo_group.add_argument(
        "--repos",
        type=str,
        help="Comma-separated list of repos: kripke,laghos,lulesh,quicksilver"
    )
    repo_group.add_argument(
        "--all",
        action="store_true",
        help="Scrape all repositories"
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("dataset/hpc_perf_commits.json"),
        help="Output JSON file"
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.3,
        help="Minimum confidence score (0.0-1.0, default: 0.3)"
    )

    args = parser.parse_args()

    if args.all:
        repos = list(CommitScraper.REPOS.keys())
    else:
        repos = [r.strip().lower() for r in args.repos.split(",")]

    scraper = CommitScraper(args.output)
    scraper.scrape_all(repos, args.min_confidence)
    scraper.save()
    scraper.print_summary()


if __name__ == "__main__":
    main()
