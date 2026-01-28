#!/bin/bash
#SBATCH -A m2404
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 4:00:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
#SBATCH -J swe-benchmark
#SBATCH -o batch_results/benchmark_%j.out
#SBATCH -e batch_results/benchmark_%j.err

# HPC Benchmark Runner - Compares agent patches vs expert optimizations
#
# Usage:
#   sbatch batch/run_benchmark.sh [OPTIONS]
#   bash batch/run_benchmark.sh [OPTIONS]
#
# This script:
# 1. Starts vLLM server with gpt-oss-120b model (unless --skip-vllm)
# 2. Runs SWE-agent on curated performance commits
# 3. Compares agent patches vs expert patches
# 4. Generates comparison report
# 5. Cleans up (reset repos, delete profiles unless --keep-profiles)

set -e

#===============================================================================
# Configuration (can be overridden via environment variables)
#===============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SWEAGENT_ROOT="$(dirname "$SCRIPT_DIR")"

# vLLM settings
VLLM_HOST="${VLLM_HOST:-127.0.0.1}"
VLLM_PORT="${VLLM_PORT:-8008}"
VLLM_MODEL="${VLLM_MODEL:-openai/gpt-oss-120b}"
VLLM_IMAGE="${VLLM_IMAGE:-docker.io/vllm/vllm-openai:v0.11.0}"
VLLM_STARTUP_TIMEOUT="${VLLM_STARTUP_TIMEOUT:-600}"
TP_SIZE="${TP_SIZE:-4}"
GPU_MEM_UTIL="${GPU_MEM_UTIL:-0.60}"

# Paths
SWEAGENT_VENV="${SWEAGENT_VENV:-$HOME/envs/sweagent}"
HATCHET_DIR="${HATCHET_DIR:-$HOME/hatchet}"  # TODO: change to pip install once upstreamed
DATASET="${SWEAGENT_ROOT}/dataset/curated_perf_commits.json"

#===============================================================================
# Parse Arguments
#===============================================================================
show_help() {
    cat << EOF
HPC Benchmark Runner - Compare SWE-agent patches vs expert optimizations

Usage: $(basename "$0") [OPTIONS]

Application Filters (combine multiple to run subset):
  --quicksilver         Include Quicksilver instances
  --lulesh              Include LULESH instances
  --kripke              Include Kripke instances
  --laghos              Include Laghos instances
  (If none specified, all applications are included)

Run Configuration:
  --num-runs N          Number of complete benchmark runs (default: 1)
  --num-probs N         Max problems (commits) per application (default: all)
  --instance-id ID      Run only specific instance (can use multiple times)
  --profiling MODE      with_profiling or no_profiling (default: no_profiling)

Server Options:
  --skip-vllm           Skip vLLM startup (use existing server on port $VLLM_PORT)

Cleanup Options:
  --keep-profiles       Don't delete HPCToolkit profiles after benchmark
  --no-cleanup          Skip all cleanup (repos and profiles)

Other:
  --help, -h            Show this help message

Environment Variables:
  VLLM_HOST             vLLM server host (default: 127.0.0.1)
  VLLM_PORT             vLLM server port (default: 8008)
  VLLM_MODEL            Model to use (default: openai/gpt-oss-120b)
  SWEAGENT_VENV         Path to sweagent virtualenv

Examples:
  # Run all apps, all commits, once
  bash run_benchmark.sh

  # Run quicksilver and lulesh, max 2 commits each, 3 runs
  bash run_benchmark.sh --quicksilver --lulesh --num-probs 2 --num-runs 3

  # Single instance test with profiling
  bash run_benchmark.sh --instance-id quicksilver__67a13d0d --profiling with_profiling

  # Use existing vLLM server
  bash run_benchmark.sh --skip-vllm --quicksilver
EOF
}

# Default values
SKIP_VLLM=false
KEEP_PROFILES=false
NO_CLEANUP=false
NUM_RUNS=1
NUM_PROBS=""
PROFILING="no_profiling"
APPS=()
INSTANCE_IDS=()

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --skip-vllm)
            SKIP_VLLM=true
            shift
            ;;
        --keep-profiles)
            KEEP_PROFILES=true
            shift
            ;;
        --no-cleanup)
            NO_CLEANUP=true
            shift
            ;;
        --num-runs)
            NUM_RUNS="$2"
            shift 2
            ;;
        --num-probs)
            NUM_PROBS="$2"
            shift 2
            ;;
        --profiling)
            PROFILING="$2"
            shift 2
            ;;
        --instance-id)
            INSTANCE_IDS+=("$2")
            shift 2
            ;;
        --quicksilver)
            APPS+=("quicksilver")
            shift
            ;;
        --lulesh)
            APPS+=("lulesh")
            shift
            ;;
        --kripke)
            APPS+=("kripke")
            shift
            ;;
        --laghos)
            APPS+=("laghos")
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

#===============================================================================
# Setup Output Directory
#===============================================================================
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
JOB_ID="${SLURM_JOB_ID:-interactive}"
OUTPUT_DIR="${SWEAGENT_ROOT}/batch_results/benchmark_${TIMESTAMP}_${JOB_ID}"
TRAJ_DIR="${SWEAGENT_ROOT}/trajectories/benchmark_${TIMESTAMP}_${JOB_ID}"

mkdir -p "${OUTPUT_DIR}"
mkdir -p "${TRAJ_DIR}"
mkdir -p "${SWEAGENT_ROOT}/batch_results"

#===============================================================================
# Print Banner
#===============================================================================
echo "=================================================="
echo "HPC Benchmark Runner - Agent vs Expert Comparison"
echo "=================================================="
echo "Job ID: ${JOB_ID}"
echo "Node: ${SLURM_NODELIST:-$(hostname)}"
echo "Start time: $(date)"
echo ""
echo "Configuration:"
echo "  SWE-Agent root: ${SWEAGENT_ROOT}"
echo "  Dataset: ${DATASET}"
echo "  Output: ${OUTPUT_DIR}"
echo "  Trajectories: ${TRAJ_DIR}"
echo "  Profiling: ${PROFILING}"
echo "  Num runs: ${NUM_RUNS}"
[[ -n "$NUM_PROBS" ]] && echo "  Max probs per app: ${NUM_PROBS}"
[[ ${#APPS[@]} -gt 0 ]] && echo "  Apps filter: ${APPS[*]}"
[[ ${#INSTANCE_IDS[@]} -gt 0 ]] && echo "  Instance IDs: ${INSTANCE_IDS[*]}"
echo "  Skip vLLM: ${SKIP_VLLM}"
echo "  Keep profiles: ${KEEP_PROFILES}"
echo "=================================================="

#===============================================================================
# Cleanup Function (called on exit)
#===============================================================================
VLLM_PID=""

cleanup() {
    local exit_code=$?
    echo ""
    echo "[Cleanup] Starting cleanup..."

    # Stop vLLM if we started it
    if [[ -n "$VLLM_PID" ]] && kill -0 "$VLLM_PID" 2>/dev/null; then
        echo "  Stopping vLLM server (PID: $VLLM_PID)..."
        kill "$VLLM_PID" 2>/dev/null || true
        wait "$VLLM_PID" 2>/dev/null || true
    fi

    # Skip cleanup if requested
    if [[ "$NO_CLEANUP" == "true" ]]; then
        echo "  Skipping cleanup (--no-cleanup specified)"
        return $exit_code
    fi

    # Reset test repos
    echo "  Resetting test repositories..."
    "${SWEAGENT_ROOT}/scripts/reset_test_repos.sh" 2>/dev/null || echo "    Warning: repo reset failed"

    # Delete HPCToolkit profiles unless --keep-profiles
    if [[ "$KEEP_PROFILES" != "true" ]]; then
        echo "  Cleaning up HPCToolkit profiles..."
        find "${OUTPUT_DIR}" -type d -name "hpc_profile*" -exec rm -rf {} + 2>/dev/null || true
        find "${OUTPUT_DIR}" -type d -name "measurements" -exec rm -rf {} + 2>/dev/null || true
        find "${OUTPUT_DIR}" -type d -name "database" -exec rm -rf {} + 2>/dev/null || true
    fi

    echo "[Cleanup] Done"
    return $exit_code
}

trap cleanup EXIT

#===============================================================================
# Phase 1: Environment Setup
#===============================================================================
echo ""
echo "[Phase 1] Setting up environment..."

# Load required modules
module load openmpi/5.0.7 2>/dev/null || true
module load cudatoolkit/12.4 2>/dev/null || true
module load python 2>/dev/null || true

# Setup spack and HPCToolkit for profiling tools
if [ -f "$HOME/spack/share/spack/setup-env.sh" ]; then
    source "$HOME/spack/share/spack/setup-env.sh"
    spack load hpctoolkit 2>/dev/null && echo "  HPCToolkit loaded via spack" || echo "  Warning: HPCToolkit not available"
fi

# Install hatchet if needed
# TODO: Change to 'pip install hatchet' once changes are upstreamed
if [[ -d "$HATCHET_DIR" ]]; then
    echo "  Installing hatchet from local fork..."
    pip install --use-pep517 "$HATCHET_DIR" -q 2>/dev/null || echo "  Warning: hatchet install failed"
fi

# Setup HuggingFace cache (use PSCRATCH for large model files)
: "${PSCRATCH:=${SCRATCH:-$HOME}}"
export HF_HOME="${HF_HOME:-$PSCRATCH/hf-cache}"
export HF_HUB_ENABLE_HF_TRANSFER=1
mkdir -p "$HF_HOME"
unset VLLM_ATTENTION_BACKEND

# Export paths for benchmark runner
export SWEAGENT_VENV
export SWEAGENT_ROOT
export VLLM_HOST
export VLLM_PORT

echo "  Modules loaded: openmpi/5.0.7, cudatoolkit/12.4"
echo "  HF_HOME: ${HF_HOME}"
echo "  SWEAGENT_VENV: ${SWEAGENT_VENV}"

#===============================================================================
# Phase 2: Start vLLM Server (unless --skip-vllm)
#===============================================================================
if [[ "$SKIP_VLLM" == "true" ]]; then
    echo ""
    echo "[Phase 2] Skipping vLLM startup (--skip-vllm)"
    echo "  Checking existing server at ${VLLM_HOST}:${VLLM_PORT}..."
    if ! curl -s "http://${VLLM_HOST}:${VLLM_PORT}/health" > /dev/null 2>&1; then
        echo "  ERROR: No vLLM server responding at ${VLLM_HOST}:${VLLM_PORT}"
        exit 1
    fi
    echo "  vLLM server is available"
else
    echo ""
    echo "[Phase 2] Starting vLLM server..."
    echo "  Model: ${VLLM_MODEL}"
    echo "  Image: ${VLLM_IMAGE}"
    echo "  Tensor Parallel: ${TP_SIZE}"

    # Pull container image (if not cached)
    podman-hpc pull "${VLLM_IMAGE}" 2>/dev/null || true

    # Start vLLM in background with podman-hpc
    podman-hpc run --rm --gpu --net host --ipc=host \
        -e HF_HOME \
        -e HF_HUB_ENABLE_HF_TRANSFER \
        -e VLLM_ATTENTION_BACKEND=TRITON_ATTN \
        -v "${HF_HOME}:${HF_HOME}" \
        "${VLLM_IMAGE}" \
        --model "${VLLM_MODEL}" \
        --host "${VLLM_HOST}" \
        --port "${VLLM_PORT}" \
        --tensor-parallel-size "${TP_SIZE}" \
        --gpu-memory-utilization "${GPU_MEM_UTIL}" \
        --download-dir "${HF_HOME}" \
        --tool-call-parser openai \
        --enable-auto-tool-choice \
        --reasoning-parser openai_gptoss \
        > "${OUTPUT_DIR}/vllm.log" 2>&1 &

    VLLM_PID=$!
    echo "  vLLM server started (PID: ${VLLM_PID})"

    # Wait for vLLM to be ready
    echo ""
    echo "[Phase 3] Waiting for vLLM server (timeout: ${VLLM_STARTUP_TIMEOUT}s)..."

    start_time=$(date +%s)
    while true; do
        now=$(date +%s)
        elapsed=$((now - start_time))

        if [ $elapsed -ge $VLLM_STARTUP_TIMEOUT ]; then
            echo "  ERROR: vLLM server not ready after ${VLLM_STARTUP_TIMEOUT}s"
            tail -50 "${OUTPUT_DIR}/vllm.log"
            exit 1
        fi

        if ! kill -0 $VLLM_PID 2>/dev/null; then
            echo "  ERROR: vLLM server process died"
            tail -50 "${OUTPUT_DIR}/vllm.log"
            exit 1
        fi

        if curl -s "http://${VLLM_HOST}:${VLLM_PORT}/health" > /dev/null 2>&1; then
            echo "  vLLM server is ready! (took ${elapsed}s)"
            break
        fi

        echo "    Waiting... (${elapsed}s elapsed)"
        sleep 10
    done
fi

#===============================================================================
# Phase 4: Run Benchmark(s)
#===============================================================================
echo ""
echo "[Phase 4] Running benchmark..."

cd "${SWEAGENT_ROOT}"
source "${SWEAGENT_VENV}/bin/activate"

# Build runner arguments
RUNNER_ARGS=(
    "--dataset" "${DATASET}"
    "--output-dir" "${OUTPUT_DIR}"
    "--trajectory-dir" "${TRAJ_DIR}"
    "--profiling" "${PROFILING}"
)

# Add app filters
for app in "${APPS[@]}"; do
    RUNNER_ARGS+=("--app" "$app")
done

# Add instance IDs
for iid in "${INSTANCE_IDS[@]}"; do
    RUNNER_ARGS+=("--instance-id" "$iid")
done

# Add num-probs if specified
[[ -n "$NUM_PROBS" ]] && RUNNER_ARGS+=("--num-probs" "$NUM_PROBS")

# Run benchmark(s)
TOTAL_SUCCESS=0
TOTAL_FAILED=0

for run_num in $(seq 1 $NUM_RUNS); do
    echo ""
    echo "=========================================="
    echo "Run ${run_num}/${NUM_RUNS}"
    echo "=========================================="

    RUN_OUTPUT_DIR="${OUTPUT_DIR}/run_${run_num}"
    RUN_TRAJ_DIR="${TRAJ_DIR}/run_${run_num}"
    mkdir -p "${RUN_OUTPUT_DIR}"
    mkdir -p "${RUN_TRAJ_DIR}"

    # Check vLLM is still healthy
    if ! curl -s "http://${VLLM_HOST}:${VLLM_PORT}/health" > /dev/null 2>&1; then
        echo "ERROR: vLLM server is not responding. Aborting."
        exit 1
    fi

    # Run the benchmark runner for this run
    python3 batch/hpc_benchmark_runner.py \
        "${RUNNER_ARGS[@]}" \
        --output-dir "${RUN_OUTPUT_DIR}" \
        --trajectory-dir "${RUN_TRAJ_DIR}" \
        --run-number "${run_num}" \
        && TOTAL_SUCCESS=$((TOTAL_SUCCESS + 1)) \
        || TOTAL_FAILED=$((TOTAL_FAILED + 1))
done

#===============================================================================
# Phase 5: Generate Summary
#===============================================================================
echo ""
echo "[Phase 5] Generating summary..."

# Create aggregate summary
python3 << EOF
import json
import os
from pathlib import Path

output_dir = Path("${OUTPUT_DIR}")
all_results = []

# Collect results from all runs
for run_dir in sorted(output_dir.glob("run_*")):
    results_file = run_dir / "benchmark_results.json"
    if results_file.exists():
        with open(results_file) as f:
            run_results = json.load(f)
            for r in run_results:
                r['run_number'] = int(run_dir.name.split('_')[1])
            all_results.extend(run_results)

# Save aggregate results
if all_results:
    with open(output_dir / "all_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    # Print summary
    successful = [r for r in all_results if r.get('success', False)]
    print(f"Total runs completed: ${NUM_RUNS}")
    print(f"Total instances processed: {len(all_results)}")
    print(f"Successful: {len(successful)}")

    if successful:
        avg_overlap = sum(r.get('file_overlap', 0) for r in successful) / len(successful)
        avg_sim = sum(r.get('patch_similarity', 0) for r in successful) / len(successful)
        print(f"Avg file overlap: {avg_overlap*100:.1f}%")
        print(f"Avg patch similarity: {avg_sim*100:.1f}%")
EOF

echo ""
echo "=================================================="
echo "Benchmark complete"
echo "Total runs: ${NUM_RUNS} (Success: ${TOTAL_SUCCESS}, Failed: ${TOTAL_FAILED})"
echo "Results: ${OUTPUT_DIR}"
echo "Trajectories: ${TRAJ_DIR}"
echo "End time: $(date)"
echo "=================================================="

exit 0
