#!/usr/bin/env python3
"""
HuggingFace Dataset Upload for HPC Performance Commits

Uploads the scraped performance commits to HuggingFace Hub for use
with SWE-agent batch instances.

Usage:
    python3 dataset/upload_to_huggingface.py --input dataset/hpc_perf_commits.json
    python3 dataset/upload_to_huggingface.py --repo-id username/hpc-perf-commits --private
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def load_commits(input_file: Path) -> list[dict]:
    """Load commits from JSON file"""
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    with open(input_file) as f:
        return json.load(f)


def prepare_for_huggingface(commits: list[dict]) -> list[dict]:
    """Prepare commits for HuggingFace format"""
    # Select and rename fields for SWE-agent compatibility
    prepared = []
    for commit in commits:
        # Core SWE-agent fields
        prepared_commit = {
            "instance_id": commit["instance_id"],
            "repo_name": commit["repo_name"],
            "base_commit": commit["base_commit"],
            "problem_statement": commit["problem_statement"],

            # Commit metadata
            "commit_hash": commit["commit_hash"],
            "commit_message": commit["commit_message"],
            "commit_date": commit["commit_date"],
            "author_name": commit["author_name"],
            "files_changed": commit["files_changed"],
            "diff": commit["diff"],
            "insertions": commit["insertions"],
            "deletions": commit["deletions"],

            # Classification
            "perf_keywords": commit["perf_keywords"],
            "optimization_type": commit["optimization_type"],
            "confidence_score": commit["confidence_score"],
            "nearest_tag": commit.get("nearest_tag"),

            # Build verification
            "build_verified": commit.get("build_verified", False),
            "build_success": commit.get("build_success"),
        }
        prepared.append(prepared_commit)

    return prepared


def create_dataset_splits(
    commits: list[dict],
    train_ratio: float = 0.8,
    seed: int = 42
) -> tuple[list[dict], list[dict]]:
    """Split commits into train/test sets"""
    import random
    random.seed(seed)

    # Shuffle commits
    shuffled = commits.copy()
    random.shuffle(shuffled)

    # Split
    split_idx = int(len(shuffled) * train_ratio)
    train = shuffled[:split_idx]
    test = shuffled[split_idx:]

    return train, test


def upload_to_huggingface(
    commits: list[dict],
    repo_id: str,
    private: bool = False,
    train_ratio: float = 0.8
) -> None:
    """Upload dataset to HuggingFace Hub"""
    try:
        from datasets import Dataset, DatasetDict
        from huggingface_hub import HfApi
    except ImportError:
        print("Required packages not found. Install with:")
        print("  pip install datasets huggingface_hub")
        sys.exit(1)

    # Prepare data
    prepared = prepare_for_huggingface(commits)
    train, test = create_dataset_splits(prepared, train_ratio)

    print(f"Dataset splits: {len(train)} train, {len(test)} test")

    # Create HuggingFace datasets
    train_dataset = Dataset.from_list(train)
    test_dataset = Dataset.from_list(test)

    dataset_dict = DatasetDict({
        "train": train_dataset,
        "test": test_dataset
    })

    # Upload
    print(f"\nUploading to HuggingFace Hub: {repo_id}")
    dataset_dict.push_to_hub(repo_id, private=private)

    print(f"\nDataset uploaded successfully!")
    print(f"URL: https://huggingface.co/datasets/{repo_id}")

    # Print usage example
    print("\nTo use with SWE-agent, add to your config:")
    print(f"""
instances:
  type: huggingface
  dataset_name: "{repo_id}"
  split: train
""")


def create_local_dataset(
    commits: list[dict],
    output_dir: Path,
    train_ratio: float = 0.8
) -> None:
    """Create local dataset files without uploading"""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Prepare data
    prepared = prepare_for_huggingface(commits)
    train, test = create_dataset_splits(prepared, train_ratio)

    # Save splits
    train_file = output_dir / "train.json"
    test_file = output_dir / "test.json"
    full_file = output_dir / "full.json"

    with open(train_file, "w") as f:
        json.dump(train, f, indent=2)

    with open(test_file, "w") as f:
        json.dump(test, f, indent=2)

    with open(full_file, "w") as f:
        json.dump(prepared, f, indent=2)

    print(f"Local dataset created in {output_dir}/")
    print(f"  train.json: {len(train)} instances")
    print(f"  test.json: {len(test)} instances")
    print(f"  full.json: {len(prepared)} instances")


def print_statistics(commits: list[dict]) -> None:
    """Print dataset statistics"""
    print("\n" + "=" * 60)
    print("DATASET STATISTICS")
    print("=" * 60)

    print(f"Total commits: {len(commits)}")

    # By repository
    by_repo = {}
    for c in commits:
        by_repo[c["repo_name"]] = by_repo.get(c["repo_name"], 0) + 1

    print("\nBy Repository:")
    for repo, count in sorted(by_repo.items()):
        print(f"  {repo}: {count}")

    # By optimization type
    by_type = {}
    for c in commits:
        by_type[c["optimization_type"]] = by_type.get(c["optimization_type"], 0) + 1

    print("\nBy Optimization Type:")
    for opt_type, count in sorted(by_type.items()):
        print(f"  {opt_type}: {count}")

    # Build verification status
    verified = sum(1 for c in commits if c.get("build_verified"))
    successful = sum(1 for c in commits if c.get("build_success"))

    if verified > 0:
        print(f"\nBuild Verification:")
        print(f"  Verified: {verified}/{len(commits)}")
        print(f"  Successful: {successful}/{verified}")


def main():
    parser = argparse.ArgumentParser(
        description="Upload HPC performance commits to HuggingFace"
    )
    parser.add_argument(
        "--input", "-i",
        type=Path,
        default=Path("dataset/hpc_perf_commits.json"),
        help="Input JSON file"
    )
    parser.add_argument(
        "--repo-id",
        type=str,
        help="HuggingFace repo ID (e.g., username/hpc-perf-commits)"
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Make the dataset private"
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Create local dataset files without uploading"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("dataset/hf_dataset"),
        help="Output directory for local dataset"
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.8,
        help="Train/test split ratio (default: 0.8)"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only print statistics, don't upload"
    )

    args = parser.parse_args()

    # Load commits
    commits = load_commits(args.input)
    print(f"Loaded {len(commits)} commits from {args.input}")

    # Print statistics
    print_statistics(commits)

    if args.stats_only:
        return

    if args.local_only:
        create_local_dataset(commits, args.output_dir, args.train_ratio)
    elif args.repo_id:
        upload_to_huggingface(
            commits,
            args.repo_id,
            args.private,
            args.train_ratio
        )
    else:
        print("\nNo action taken. Use --repo-id to upload or --local-only for local files.")


if __name__ == "__main__":
    main()
