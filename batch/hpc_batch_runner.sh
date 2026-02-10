#!/bin/bash
#SBATCH -A m2404
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 4:00:00
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
#SBATCH -J swe-batch
#SBATCH -o /pscratch/sd/k/krydzy/SWE-agent/batch_results/slurm_%j.out
#SBATCH -e /pscratch/sd/k/krydzy/SWE-agent/batch_results/slurm_%j.err
# NOTE: -N (node count) is set dynamically via self-submit. Do NOT add #SBATCH -N here.

# HPC Batch Runner for SWE-Agent Experiments
# Starts vLLM server and runs batch experiments on existing test repositories
#
# Multi-node execution:
#   Automatically allocates N+1 nodes (1 for vLLM, 1 per app).
#   With --external-model, allocates N nodes (no vLLM node needed).
#   All SWE-agent instances run in parallel on dedicated nodes.
#
# Usage:
#   sbatch batch/hpc_batch_runner.sh --all --both --runs 3
#   sbatch batch/hpc_batch_runner.sh --apps kripke,lulesh --no-profiling --runs 5
#   sbatch batch/hpc_batch_runner.sh --skip-vllm --apps quicksilver --runs 1
#
# Shell-level options (handled before passing to hpc_runner.py):
#   --skip-vllm       Skip vLLM startup (use existing server)
#   --external-model  Use external model API (no vLLM node)
#   --keep-profiles   Don't delete HPCToolkit profiles after run
#   --no-cleanup      Skip all cleanup (repos and profiles)
#
# All other arguments are passed to hpc_runner.py

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
HATCHET_DIR="${HATCHET_DIR:-$HOME/hatchet}"

#===============================================================================
# Parse Shell-Level Arguments
#===============================================================================
SKIP_VLLM=false
EXTERNAL_MODEL=false
KEEP_PROFILES=false
NO_CLEANUP=false
HAS_ALL_FLAG=false
RUNNER_ARGS=()
APPS_FOR_CLEANUP=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-vllm)
            SKIP_VLLM=true
            shift
            ;;
        --external-model)
            EXTERNAL_MODEL=true
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
        --all)
            HAS_ALL_FLAG=true
            APPS_FOR_CLEANUP=("kripke" "laghos" "lulesh" "quicksilver")
            RUNNER_ARGS+=("$1")
            shift
            ;;
        --apps)
            # Capture apps for cleanup, also pass to runner
            RUNNER_ARGS+=("$1" "$2")
            # Parse comma-separated apps
            IFS=',' read -ra APPS_FOR_CLEANUP <<< "$2"
            shift 2
            ;;
        *)
            # Pass all other arguments to hpc_runner.py
            RUNNER_ARGS+=("$1")
            shift
            ;;
    esac
done

#===============================================================================
# Auto-calculate Node Count and Self-Submit
#===============================================================================

# Determine number of apps
if [[ ${#APPS_FOR_CLEANUP[@]} -eq 0 ]]; then
    # No apps specified and no --all flag — will fail validation later
    NUM_APPS=4  # Default assumption for node calculation
else
    NUM_APPS=${#APPS_FOR_CLEANUP[@]}
fi

# Validate --external-model environment variables
if [[ "$EXTERNAL_MODEL" == "true" ]]; then
    if [[ -z "${OPENAI_API_BASE:-}" ]]; then
        echo "ERROR: --external-model requires OPENAI_API_BASE environment variable"
        exit 1
    fi
    if [[ -z "${OPENAI_API_KEY:-}" ]]; then
        echo "ERROR: --external-model requires OPENAI_API_KEY environment variable"
        exit 1
    fi
fi

# Calculate required nodes
if [[ "$EXTERNAL_MODEL" == "true" ]] || [[ "$SKIP_VLLM" == "true" ]]; then
    REQUIRED_NODES=$NUM_APPS
else
    REQUIRED_NODES=$((NUM_APPS + 1))
fi

# Self-submit logic
if [[ -z "${SLURM_JOB_ID:-}" ]]; then
    echo "Not inside a SLURM job. Self-submitting with ${REQUIRED_NODES} nodes..."
    sbatch -N "${REQUIRED_NODES}" "$0" "$@"
    exit $?
fi

# Validate node count
if [[ "${SLURM_JOB_NUM_NODES:-1}" -lt "$REQUIRED_NODES" ]]; then
    echo "ERROR: Need ${REQUIRED_NODES} nodes but only have ${SLURM_JOB_NUM_NODES}"
    exit 1
fi

#===============================================================================
# Node Discovery and Role Assignment
#===============================================================================
mapfile -t ALL_NODES < <(scontrol show hostnames "$SLURM_NODELIST")

if [[ "$EXTERNAL_MODEL" == "true" ]] || [[ "$SKIP_VLLM" == "true" ]]; then
    VLLM_NODE=""
    AGENT_NODES=("${ALL_NODES[@]}")
else
    VLLM_NODE="${ALL_NODES[0]}"
    AGENT_NODES=("${ALL_NODES[@]:1}")
fi

# Map apps to agent nodes
declare -A APP_NODE_MAP
for i in "${!APPS_FOR_CLEANUP[@]}"; do
    APP_NODE_MAP["${APPS_FOR_CLEANUP[$i]}"]="${AGENT_NODES[$i]}"
done

#===============================================================================
# Setup Output Directory
#===============================================================================
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
JOB_ID="${SLURM_JOB_ID:-interactive}"
OUTPUT_DIR="${SWEAGENT_ROOT}/batch_results/batch_${TIMESTAMP}_${JOB_ID}"
TRAJ_DIR="${SWEAGENT_ROOT}/trajectories/batch_${TIMESTAMP}_${JOB_ID}"

mkdir -p "${OUTPUT_DIR}"
mkdir -p "${TRAJ_DIR}"
mkdir -p "${SWEAGENT_ROOT}/batch_results"

#===============================================================================
# Print Banner
#===============================================================================
echo "=================================================="
echo "HPC Batch Runner - SWE-Agent Experiments"
echo "=================================================="
echo "Job ID: ${JOB_ID}"
echo "Nodes: ${SLURM_NODELIST} (${SLURM_JOB_NUM_NODES} total)"
echo "Start time: $(date)"
echo ""
echo "Node Assignment:"
if [[ -n "$VLLM_NODE" ]]; then
    echo "  vLLM server:  ${VLLM_NODE}"
else
    echo "  vLLM server:  (none — external model or skip-vllm)"
fi
for app in "${APPS_FOR_CLEANUP[@]}"; do
    printf "  %-16s%s\n" "${app}:" "${APP_NODE_MAP[$app]}"
done
echo ""
echo "Configuration:"
echo "  SWE-Agent root: ${SWEAGENT_ROOT}"
echo "  Output: ${OUTPUT_DIR}"
echo "  Trajectories: ${TRAJ_DIR}"
echo "  Runner arguments: ${RUNNER_ARGS[*]}"
echo "  Apps: ${APPS_FOR_CLEANUP[*]}"
echo "  External model: ${EXTERNAL_MODEL}"
echo "  Skip vLLM: ${SKIP_VLLM}"
echo "  Keep profiles: ${KEEP_PROFILES}"
echo "  No cleanup: ${NO_CLEANUP}"
echo "=================================================="

#===============================================================================
# Cleanup Function (called on exit)
#===============================================================================
VLLM_PID=""
AGENT_PIDS=()

cleanup() {
    local exit_code=$?
    echo ""
    echo "[Cleanup] Starting cleanup..."

    # Kill any running agent processes first
    for pid in "${AGENT_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "  Stopping agent process (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
        fi
    done
    for pid in "${AGENT_PIDS[@]}"; do
        wait "$pid" 2>/dev/null || true
    done

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

    # Clean up workspace copies
    if [[ -d "${OUTPUT_DIR}/workspaces" ]]; then
        echo "  Cleaning up workspace copies..."
        rm -rf "${OUTPUT_DIR}/workspaces"
    fi

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

# Note: hatchet installation moved to after venv activation (Phase 4)

# Setup HuggingFace cache (use PSCRATCH for large model files)
: "${PSCRATCH:=${SCRATCH:-$HOME}}"
export HF_HOME="${HF_HOME:-$PSCRATCH/hf-cache}"
export HF_HUB_ENABLE_HF_TRANSFER=1
mkdir -p "$HF_HOME"
unset VLLM_ATTENTION_BACKEND

# Export paths for batch runner
export SWEAGENT_VENV
export SWEAGENT_ROOT
export VLLM_HOST
export VLLM_PORT

echo "  Modules loaded: openmpi/5.0.7, cudatoolkit/12.4"
echo "  HF_HOME: ${HF_HOME}"
echo "  SWEAGENT_VENV: ${SWEAGENT_VENV}"

#===============================================================================
# Phase 2: Start vLLM Server (unless --skip-vllm or --external-model)
#===============================================================================
if [[ "$EXTERNAL_MODEL" == "true" ]]; then
    echo ""
    echo "[Phase 2] Using external model API (--external-model)"
    echo "  OPENAI_API_BASE: ${OPENAI_API_BASE}"
    echo "  Skipping vLLM startup"
    VLLM_HOST="external"
    VLLM_PORT="0"
elif [[ "$SKIP_VLLM" == "true" ]]; then
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
    echo "[Phase 2] Starting vLLM server on node ${VLLM_NODE}..."
    echo "  Model: ${VLLM_MODEL}"
    echo "  Image: ${VLLM_IMAGE}"
    echo "  Tensor Parallel: ${TP_SIZE}"

    # Pull container image on vLLM node (if not cached)
    srun --nodes=1 --ntasks=1 --nodelist="${VLLM_NODE}" --exclusive --gpu-bind=none \
        podman-hpc pull "${VLLM_IMAGE}" 2>/dev/null || true

    # Start vLLM on dedicated node in background
    srun --nodes=1 --ntasks=1 --nodelist="${VLLM_NODE}" --exclusive --gpu-bind=none \
        podman-hpc run --rm --gpu --net host --ipc=host \
        -e HF_HOME \
        -e HF_HUB_ENABLE_HF_TRANSFER \
        -e VLLM_ATTENTION_BACKEND=TRITON_ATTN \
        -v "${HF_HOME}:${HF_HOME}" \
        "${VLLM_IMAGE}" \
        --model "${VLLM_MODEL}" \
        --host "0.0.0.0" \
        --port "${VLLM_PORT}" \
        --tensor-parallel-size "${TP_SIZE}" \
        --gpu-memory-utilization "${GPU_MEM_UTIL}" \
        --download-dir "${HF_HOME}" \
        --tool-call-parser openai \
        --enable-auto-tool-choice \
        --reasoning-parser openai_gptoss \
        > "${OUTPUT_DIR}/vllm.log" 2>&1 &

    VLLM_PID=$!
    VLLM_HOST="${VLLM_NODE}"
    echo "  vLLM server started on ${VLLM_NODE} (PID: ${VLLM_PID})"

    # Wait for vLLM to be ready
    echo ""
    echo "[Phase 3] Waiting for vLLM server at ${VLLM_HOST}:${VLLM_PORT} (timeout: ${VLLM_STARTUP_TIMEOUT}s)..."

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

export VLLM_HOST
export VLLM_PORT

#===============================================================================
# Phase 4: Run Batch Experiments — Parallel per-app execution
#===============================================================================
echo ""
echo "[Phase 4] Running batch experiments (parallel per-app)..."

cd "${SWEAGENT_ROOT}"
source "${SWEAGENT_VENV}/bin/activate"

# Install hatchet if needed (must be after venv activation)
# TODO: Change to 'pip install hatchet' once changes are upstreamed
if [[ -d "$HATCHET_DIR" ]]; then
    echo "  Installing hatchet from local fork..."
    pip install --use-pep517 "$HATCHET_DIR" -q 2>/dev/null || echo "  Warning: hatchet install failed"
fi

# Validate that required arguments are present
if [[ ! " ${RUNNER_ARGS[*]} " =~ " --apps " ]] && [[ ! " ${RUNNER_ARGS[*]} " =~ " --all " ]]; then
    echo "ERROR: Must specify either --apps or --all"
    echo "Usage: sbatch batch/hpc_batch_runner.sh --apps kripke,lulesh [OPTIONS]"
    echo "       sbatch batch/hpc_batch_runner.sh --all [OPTIONS]"
    exit 1
fi

# Determine API env vars
if [[ "$EXTERNAL_MODEL" == "true" ]]; then
    API_BASE_EXPORT="export OPENAI_API_BASE='${OPENAI_API_BASE}'; export OPENAI_API_KEY='${OPENAI_API_KEY}'"
else
    API_BASE_EXPORT="export OPENAI_API_BASE='http://${VLLM_HOST}:${VLLM_PORT}/v1'; export OPENAI_API_KEY='dummy-key-ok'"
fi

# Build per-app runner args (strip --apps/--all from RUNNER_ARGS since we pass --apps per-app)
FILTERED_RUNNER_ARGS=()
skip_next=false
for arg in "${RUNNER_ARGS[@]}"; do
    if [[ "$skip_next" == "true" ]]; then
        skip_next=false
        continue
    fi
    case "$arg" in
        --apps) skip_next=true ;;
        --all) ;; # skip
        *) FILTERED_RUNNER_ARGS+=("$arg") ;;
    esac
done

# Launch one agent per app, each on its dedicated node
AGENT_PIDS=()
declare -A BATCH_APP_PID_MAP

for app in "${APPS_FOR_CLEANUP[@]}"; do
    node="${APP_NODE_MAP[$app]}"
    APP_OUTPUT_DIR="${OUTPUT_DIR}/${app}"
    APP_TRAJ_DIR="${TRAJ_DIR}/${app}"
    mkdir -p "${APP_OUTPUT_DIR}"
    mkdir -p "${APP_TRAJ_DIR}"

    echo "  Launching ${app} on node ${node} -> ${APP_OUTPUT_DIR}"

    srun --nodes=1 --ntasks=1 --nodelist="${node}" --exclusive --gpu-bind=none \
        bash -c "
            # Pin child srun calls (e.g., Kripke MPI) to this node only
            export SLURM_NODELIST=\$(hostname)
            export SLURM_JOB_NUM_NODES=1

            # Setup environment
            module load openmpi/5.0.7 2>/dev/null || true
            module load cudatoolkit/12.4 2>/dev/null || true
            module load python 2>/dev/null || true

            # Setup spack/HPCToolkit
            if [ -f \"${HOME}/spack/share/spack/setup-env.sh\" ]; then
                source \"${HOME}/spack/share/spack/setup-env.sh\"
                spack load hpctoolkit 2>/dev/null || true
            fi

            cd ${SWEAGENT_ROOT}
            source ${SWEAGENT_VENV}/bin/activate

            # Install hatchet if needed
            if [[ -d '${HATCHET_DIR}' ]]; then
                pip install --use-pep517 '${HATCHET_DIR}' -q 2>/dev/null || true
            fi

            ${API_BASE_EXPORT}
            export VLLM_HOST='${VLLM_HOST}'
            export VLLM_PORT='${VLLM_PORT}'
            export SWEAGENT_VENV='${SWEAGENT_VENV}'
            export SWEAGENT_ROOT='${SWEAGENT_ROOT}'
            export HF_HOME='${HF_HOME}'

            python3 batch/hpc_runner.py \
                --apps ${app} \
                --vllm-host '${VLLM_HOST}' \
                --vllm-port '${VLLM_PORT}' \
                --output-dir '${APP_OUTPUT_DIR}' \
                --trajectory-dir '${APP_TRAJ_DIR}' \
                --skip-vllm-check \
                ${FILTERED_RUNNER_ARGS[*]}
        " > "${APP_OUTPUT_DIR}/agent.log" 2>&1 &

    local_pid=$!
    AGENT_PIDS+=("$local_pid")
    BATCH_APP_PID_MAP["$app"]="$local_pid"
    echo "    PID: ${local_pid}"
done

# Wait for all agents to finish
echo ""
echo "  Waiting for ${#AGENT_PIDS[@]} agents to complete..."
RUNNER_EXIT_CODE=0

for app in "${APPS_FOR_CLEANUP[@]}"; do
    pid="${BATCH_APP_PID_MAP[$app]}"
    if wait "$pid"; then
        echo "    ${app} (PID ${pid}): SUCCESS"
    else
        exit_code=$?
        echo "    ${app} (PID ${pid}): FAILED (exit code ${exit_code})"
        RUNNER_EXIT_CODE=1
    fi
done

#===============================================================================
# Phase 5: Summary
#===============================================================================
echo ""
echo "=================================================="
echo "Batch run complete"
echo "Exit code: ${RUNNER_EXIT_CODE}"
echo "Results: ${OUTPUT_DIR}"
echo "Trajectories: ${TRAJ_DIR}"
echo "End time: $(date)"
echo "=================================================="

exit $RUNNER_EXIT_CODE
