#!/bin/bash
#SBATCH -A m2404
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 3:00:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
#SBATCH -J swe-batch
#SBATCH -o batch_results/slurm_%j.out
#SBATCH -e batch_results/slurm_%j.err

# HPC Batch Runner for SWE-Agent Experiments
# Starts vLLM server and runs batch experiments
#
# Usage:
#   sbatch batch/hpc_batch_runner.sh --all --both --runs 3
#   sbatch batch/hpc_batch_runner.sh --apps kripke,lulesh --no-profiling --runs 5
#
# All arguments after the script name are passed to hpc_runner.py

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SWEAGENT_ROOT="$(dirname "$SCRIPT_DIR")"
VLLM_HOST="127.0.0.1"
VLLM_PORT="8008"
VLLM_STARTUP_TIMEOUT=300

# Store arguments for hpc_runner.py
RUNNER_ARGS="$@"

echo "=================================================="
echo "HPC Batch Runner - SWE-Agent Experiments"
echo "=================================================="
echo "Job ID: ${SLURM_JOB_ID:-local}"
echo "Node: ${SLURM_NODELIST:-$(hostname)}"
echo "Start time: $(date)"
echo "SWE-Agent root: ${SWEAGENT_ROOT}"
echo "Runner arguments: ${RUNNER_ARGS}"
echo "=================================================="

# Phase 1: Environment Setup
echo ""
echo "[Phase 1] Setting up environment..."

# Load required modules
module load openmpi/5.0.7
module load cuda/12.4

# Setup spack for Python packages
if [ -f "/global/common/software/nersc9/spack/share/spack/setup-env.sh" ]; then
    source /global/common/software/nersc9/spack/share/spack/setup-env.sh
fi

# Setup HuggingFace cache
export HF_HOME="${HF_HOME:-$HOME/.cache/huggingface}"
export HF_HUB_ENABLE_HF_TRANSFER=1

# Setup environment for SWE-agent
export PYTHONPATH="${SWEAGENT_ROOT}:${PYTHONPATH}"
export PATH="${SWEAGENT_ROOT}/bin:${PATH}"

# Export SWE-agent virtual environment path for batch runner
export SWEAGENT_VENV="${SWEAGENT_VENV:-/global/u2/k/krydzy/envs/sweagent}"
echo "  SWEAGENT_VENV: ${SWEAGENT_VENV}"

# Ensure pip packages are available
pip install --quiet datasets huggingface_hub pyyaml 2>/dev/null || true

echo "  Modules loaded: openmpi/5.0.7, cuda/12.4"
echo "  HF_HOME: ${HF_HOME}"
echo "  PYTHONPATH includes: ${SWEAGENT_ROOT}"

# Phase 2: Start vLLM Server
echo ""
echo "[Phase 2] Starting vLLM server..."

# Export vLLM configuration
export VLLM_HOST VLLM_PORT

# Start vLLM in background
"${SCRIPT_DIR}/vllm_server.sh" &
VLLM_PID=$!

echo "  vLLM server started (PID: ${VLLM_PID})"
echo "  Waiting for server to be ready (timeout: ${VLLM_STARTUP_TIMEOUT}s)..."

# Phase 3: Wait for vLLM Health Check
wait_for_vllm() {
    local timeout=$1
    local start=$(date +%s)

    while true; do
        local now=$(date +%s)
        local elapsed=$((now - start))

        if [ $elapsed -ge $timeout ]; then
            echo "  ERROR: vLLM server not ready after ${timeout}s"
            return 1
        fi

        # Check if vLLM process is still running
        if ! kill -0 $VLLM_PID 2>/dev/null; then
            echo "  ERROR: vLLM server process died"
            return 1
        fi

        # Try health endpoint
        if curl -s "http://${VLLM_HOST}:${VLLM_PORT}/health" > /dev/null 2>&1; then
            echo "  vLLM server is ready! (took ${elapsed}s)"
            return 0
        fi

        sleep 5
    done
}

if ! wait_for_vllm $VLLM_STARTUP_TIMEOUT; then
    echo "FATAL: Failed to start vLLM server"
    kill $VLLM_PID 2>/dev/null || true
    exit 1
fi

# Phase 4: Execute Python Orchestrator
echo ""
echo "[Phase 3] Running batch experiments..."

cd "${SWEAGENT_ROOT}"

# Run the Python orchestrator with provided arguments
python3 batch/hpc_runner.py \
    --vllm-host "${VLLM_HOST}" \
    --vllm-port "${VLLM_PORT}" \
    --skip-vllm-check \
    ${RUNNER_ARGS}

RUNNER_EXIT_CODE=$?

# Phase 5: Cleanup
echo ""
echo "[Phase 4] Cleanup..."

# Stop vLLM server
echo "  Stopping vLLM server..."
kill $VLLM_PID 2>/dev/null || true
wait $VLLM_PID 2>/dev/null || true

echo ""
echo "=================================================="
echo "Batch run complete"
echo "Exit code: ${RUNNER_EXIT_CODE}"
echo "End time: $(date)"
echo "=================================================="

exit $RUNNER_EXIT_CODE
