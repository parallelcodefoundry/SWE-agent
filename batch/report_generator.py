#!/usr/bin/env python3
"""
Report Generator for HPC Batch Runner

Generates summary reports and statistics from batch run results.
Can be used standalone or called from hpc_runner.py.

Usage:
    python3 batch/report_generator.py /path/to/batch_results/timestamp_jobid/
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any


def load_results(results_dir: Path) -> list[dict]:
    """Load results from a batch run directory"""
    results_file = results_dir / "results.json"
    if not results_file.exists():
        raise FileNotFoundError(f"Results file not found: {results_file}")

    with open(results_file) as f:
        return json.load(f)


def calculate_statistics(values: list[float]) -> dict[str, float]:
    """Calculate basic statistics for a list of values"""
    if not values:
        return {"count": 0, "mean": None, "min": None, "max": None, "std": None}

    n = len(values)
    mean = sum(values) / n

    if n > 1:
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        std = variance ** 0.5
    else:
        std = 0.0

    return {
        "count": n,
        "mean": round(mean, 4),
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "std": round(std, 4),
    }


def generate_summary(results: list[dict]) -> dict[str, Any]:
    """Generate aggregated summary by app and config type"""
    summary = {
        "total_runs": len(results),
        "successful_runs": sum(1 for r in results if r.get("success")),
        "correctness_passed": sum(1 for r in results if r.get("correctness") == "PASSED"),
        "correctness_failed": sum(1 for r in results if r.get("correctness") == "FAILED"),
        "by_app": {},
        "by_config": {},
        "by_app_config": {},
    }

    # Group by app
    by_app = defaultdict(list)
    for r in results:
        by_app[r["app"]].append(r)

    for app, app_results in by_app.items():
        speedups = [r["speedup"] for r in app_results if r.get("speedup") and r.get("correctness") == "PASSED"]
        durations = [r["duration_seconds"] for r in app_results if r.get("duration_seconds")]

        summary["by_app"][app] = {
            "runs": len(app_results),
            "successful": sum(1 for r in app_results if r.get("success")),
            "passed": sum(1 for r in app_results if r.get("correctness") == "PASSED"),
            "failed": sum(1 for r in app_results if r.get("correctness") == "FAILED"),
            "speedup_stats": calculate_statistics(speedups),
            "duration_stats": calculate_statistics(durations),
        }

    # Group by config type
    by_config = defaultdict(list)
    for r in results:
        by_config[r["config_type"]].append(r)

    for config, config_results in by_config.items():
        speedups = [r["speedup"] for r in config_results if r.get("speedup") and r.get("correctness") == "PASSED"]

        summary["by_config"][config] = {
            "runs": len(config_results),
            "successful": sum(1 for r in config_results if r.get("success")),
            "passed": sum(1 for r in config_results if r.get("correctness") == "PASSED"),
            "failed": sum(1 for r in config_results if r.get("correctness") == "FAILED"),
            "speedup_stats": calculate_statistics(speedups),
        }

    # Group by app + config combination
    by_app_config = defaultdict(list)
    for r in results:
        key = f"{r['app']}_{r['config_type']}"
        by_app_config[key].append(r)

    for key, combo_results in by_app_config.items():
        speedups = [r["speedup"] for r in combo_results if r.get("speedup") and r.get("correctness") == "PASSED"]
        baseline_times = [r["baseline_time"] for r in combo_results if r.get("baseline_time")]
        modified_times = [r["modified_time"] for r in combo_results if r.get("modified_time")]

        summary["by_app_config"][key] = {
            "runs": len(combo_results),
            "successful": sum(1 for r in combo_results if r.get("success")),
            "passed": sum(1 for r in combo_results if r.get("correctness") == "PASSED"),
            "failed": sum(1 for r in combo_results if r.get("correctness") == "FAILED"),
            "speedup_stats": calculate_statistics(speedups),
            "baseline_time_stats": calculate_statistics(baseline_times),
            "modified_time_stats": calculate_statistics(modified_times),
        }

    return summary


def results_to_csv(results: list[dict], output_file: Path) -> None:
    """Write results to CSV format"""
    if not results:
        return

    # Define column order
    columns = [
        "app", "config_type", "run_number", "success", "correctness",
        "baseline_time", "modified_time", "speedup", "duration_seconds",
        "error_message", "trajectory_file", "token_count", "api_calls",
        "trajectory_steps", "model_name"
    ]

    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for result in results:
            writer.writerow(result)


def summary_to_csv(summary: dict, output_file: Path) -> None:
    """Write summary to CSV format"""
    rows = []

    for key, stats in summary.get("by_app_config", {}).items():
        app, config = key.rsplit("_", 1) if "_" in key else (key, "")
        if config in ("profiling", "no"):
            # Handle with_profiling and no_profiling
            parts = key.split("_")
            app = parts[0]
            config = "_".join(parts[1:])

        row = {
            "app": app,
            "config_type": config,
            "runs": stats["runs"],
            "successful": stats["successful"],
            "passed": stats["passed"],
            "failed": stats["failed"],
            "speedup_mean": stats["speedup_stats"]["mean"],
            "speedup_std": stats["speedup_stats"]["std"],
            "speedup_min": stats["speedup_stats"]["min"],
            "speedup_max": stats["speedup_stats"]["max"],
            "baseline_time_mean": stats["baseline_time_stats"]["mean"],
            "modified_time_mean": stats["modified_time_stats"]["mean"],
        }
        rows.append(row)

    if rows:
        columns = list(rows[0].keys())
        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)


def generate_reports(results_dir: Path, results: list = None) -> None:
    """Generate all report formats"""
    results_dir = Path(results_dir)

    # Load results if not provided
    if results is None:
        results = load_results(results_dir)
    else:
        # Convert dataclass instances to dicts if needed
        if results and hasattr(results[0], "__dataclass_fields__"):
            results = [asdict(r) for r in results]

    print(f"Generating reports for {len(results)} results in {results_dir}")

    # Generate summary
    summary = generate_summary(results)

    # Save JSON files
    summary_file = results_dir / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Created: {summary_file}")

    # Save CSV files
    results_csv = results_dir / "results.csv"
    results_to_csv(results, results_csv)
    print(f"  Created: {results_csv}")

    summary_csv = results_dir / "summary.csv"
    summary_to_csv(summary, summary_csv)
    print(f"  Created: {summary_csv}")

    # Print summary to console
    print("\n" + "=" * 60)
    print("BATCH RUN SUMMARY")
    print("=" * 60)
    print(f"Total runs: {summary['total_runs']}")
    print(f"Successful: {summary['successful_runs']}")
    print(f"Correctness PASSED: {summary['correctness_passed']}")
    print(f"Correctness FAILED: {summary['correctness_failed']}")

    print("\nBy Application:")
    for app, stats in summary["by_app"].items():
        speedup = stats["speedup_stats"]["mean"]
        speedup_str = f"{speedup:.2f}x" if speedup else "N/A"
        print(f"  {app}: {stats['passed']}/{stats['runs']} passed, avg speedup: {speedup_str}")

    print("\nBy Configuration:")
    for config, stats in summary["by_config"].items():
        speedup = stats["speedup_stats"]["mean"]
        speedup_str = f"{speedup:.2f}x" if speedup else "N/A"
        print(f"  {config}: {stats['passed']}/{stats['runs']} passed, avg speedup: {speedup_str}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate reports from HPC batch run results"
    )
    parser.add_argument(
        "results_dir",
        type=Path,
        help="Path to batch results directory (containing results.json)"
    )

    args = parser.parse_args()

    if not args.results_dir.exists():
        print(f"ERROR: Results directory not found: {args.results_dir}")
        sys.exit(1)

    generate_reports(args.results_dir)


if __name__ == "__main__":
    main()
