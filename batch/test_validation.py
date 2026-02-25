#!/usr/bin/env python3
"""
Test the post-agent validation path in hpc_benchmark_runner.py.

This script directly invokes _validate_agent_changes() with a BenchmarkResult
that has agent_insertions=1, forcing the build+run validation path (instead of
the skip path that fires when insertions+deletions == 0).

Must be run on a compute node with GPUs (needs nvcc, MPI, CUDA).
"""

import sys
from pathlib import Path

# Ensure SWE-agent root is importable
SWEAGENT_ROOT = Path("/pscratch/sd/k/krydzy/SWE-agent")
sys.path.insert(0, str(SWEAGENT_ROOT))

from batch.hpc_benchmark_runner import HPCBenchmarkRunner, BenchmarkResult

def main():
    # Output dirs (temporary, just need to satisfy __init__)
    output_dir = SWEAGENT_ROOT / "batch_results" / "test_validation_output"
    trajectory_dir = output_dir / "trajectories"

    print("=" * 60)
    print("TEST: _validate_agent_changes() with agent_insertions=1")
    print("=" * 60)

    # 1. Create runner instance
    print("\n[1] Creating HPCBenchmarkRunner...")
    runner = HPCBenchmarkRunner(
        output_dir=output_dir,
        trajectory_dir=trajectory_dir,
        profiling="no_profiling",
        run_number=1,
        base_mode=True,
        vllm_host="127.0.0.1",
        vllm_port=8008,
        model_name=None,
        framework="codex",
    )
    print("    Runner created OK")

    # 2. Create a fake BenchmarkResult with agent_insertions=1
    print("\n[2] Creating BenchmarkResult with agent_insertions=1...")
    result = BenchmarkResult(
        instance_id="quicksilver__validation_test",
        repo_name="quicksilver",
        optimization_type="test",
        framework="codex",
        run_number=1,
        success=True,
        agent_insertions=1,  # <-- triggers validation (not skipped)
        agent_deletions=0,
    )
    print(f"    agent_insertions={result.agent_insertions}, agent_deletions={result.agent_deletions}")
    print(f"    agent_builds={result.agent_builds} (should be None before validation)")
    print(f"    agent_correctness={result.agent_correctness} (should be None before validation)")
    print(f"    agent_speedup={result.agent_speedup} (should be None before validation)")

    # 3. Use Quicksilver_test as the workspace
    workspace = SWEAGENT_ROOT / "Quicksilver_test"
    print(f"\n[3] Using workspace: {workspace}")
    print(f"    Workspace exists: {workspace.exists()}")
    print(f"    Exe exists: {(workspace / 'src' / 'qs').exists()}")

    # 4. Call _validate_agent_changes directly
    print("\n[4] Calling runner._validate_agent_changes('quicksilver', workspace, result)...")
    print("    This will: build (qs_build --clean) then run (qs_run)")
    print("-" * 60)
    sys.stdout.flush()

    try:
        runner._validate_agent_changes("quicksilver", workspace, result)
    except Exception as e:
        print(f"\n    EXCEPTION: {type(e).__name__}: {e}")

    # 5. Print results
    print("\n" + "=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)
    print(f"  agent_builds:      {result.agent_builds}")
    print(f"  agent_correctness: {result.agent_correctness}")
    print(f"  agent_speedup:     {result.agent_speedup}")
    print("=" * 60)

    # Summary
    if result.agent_builds is True and result.agent_correctness == "passed":
        print("\nSUCCESS: Validation path works end-to-end.")
    elif result.agent_builds is False:
        print("\nFAILED: Build step failed.")
    elif result.agent_builds is True and result.agent_correctness != "passed":
        print(f"\nPARTIAL: Built OK but correctness={result.agent_correctness}")
    else:
        print("\nUNEXPECTED: Check output above for details.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
