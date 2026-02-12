#!/bin/bash
#SBATCH -A m2404
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 4:00:00
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
#SBATCH -J swe-benchmark
#SBATCH -o /pscratch/sd/k/krydzy/SWE-agent/batch_results/benchmark_%j.out
#SBATCH -e /pscratch/sd/k/krydzy/SWE-agent/batch_results/benchmark_%j.err
# NOTE: -N (node count) is set dynamically via self-submit. Do NOT add #SBATCH -N here.

# HPC Benchmark Runner - Compares agent patches vs expert optimizations
#
# Usage:
#   sbatch batch/run_benchmark.sh [OPTIONS]
#   bash batch/run_benchmark.sh [OPTIONS]
#
# Two modes:
#   BENCHMARK MODE (default): Runs on curated commits, compares agent vs expert patches
#   BASE MODE (--base):       Runs on current test repo state, no expert comparison
#
# Multi-node execution:
#   Automatically allocates N+1 nodes (1 for vLLM, 1 per app).
#   With --external-model, allocates N nodes (no vLLM node needed).
#   All SWE-agent instances run in parallel on dedicated nodes.
#
# This script:
# 1. Auto-calculates required nodes and self-submits via sbatch (if not already in a job)
# 2. Starts vLLM server on dedicated node (unless --skip-vllm or --external-model)
# 3. Runs SWE-agent in parallel (one per app, each on its own node)
# 4. Compares agent patches vs expert patches (benchmark mode only)
# 5. Generates comparison report
# 6. Cleans up (workspaces, profiles unless --keep-profiles)

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
  --base                Run on current state of test repos (skip dataset/git checkout)
  --num-runs N          Number of complete benchmark runs (default: 1)
  --num-probs N         Max problems (commits) per application (default: all)
  --instance-id ID      Run only specific instance (can use multiple times)
  --profiling MODE      with_profiling or no_profiling (default: no_profiling)
  --both                Run both with_profiling and no_profiling (only with --base)

Server Options:
  --skip-vllm           Skip vLLM startup (use existing server on port $VLLM_PORT)
  --external-model      Use external model API (OpenAI, Anthropic, etc.)
                        Requires OPENAI_API_BASE and OPENAI_API_KEY env vars.
                        Skips vLLM entirely and reduces node count by 1.
  --model-name NAME     Override model name (e.g., openai/gpt-5.1).
                        Also enables \$1 cost limit per instance.

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
  OPENAI_API_BASE       External model API base URL (used with --external-model)
  OPENAI_API_KEY        External model API key (used with --external-model)

Examples:
  # Run all apps, all commits, once (benchmark mode) — auto-allocates 5 nodes
  bash run_benchmark.sh

  # Run quicksilver and lulesh — auto-allocates 3 nodes (2 apps + 1 vLLM)
  bash run_benchmark.sh --quicksilver --lulesh --num-probs 2 --num-runs 3

  # Single instance test with profiling
  bash run_benchmark.sh --instance-id quicksilver__67a13d0d --profiling with_profiling

  # BASE MODE: Run on current test repos (no git checkout)
  bash run_benchmark.sh --base --kripke --laghos --lulesh

  # BASE MODE with both profiling configs
  bash run_benchmark.sh --base --both --kripke --laghos --lulesh

  # Use external model (no vLLM node) — auto-allocates 2 nodes
  OPENAI_API_BASE="https://api.openai.com/v1" OPENAI_API_KEY="sk-..." \
    bash run_benchmark.sh --external-model --base --kripke --lulesh

  # Use existing vLLM server (single-node, legacy mode)
  bash run_benchmark.sh --skip-vllm --quicksilver
EOF
}

# Default values
SKIP_VLLM=false
EXTERNAL_MODEL=false
KEEP_PROFILES=false
NO_CLEANUP=false
BASE_MODE=false
BOTH_PROFILING=false
NUM_RUNS=1
NUM_PROBS=""
PROFILING="no_profiling"
MODEL_NAME=""
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
        --base)
            BASE_MODE=true
            shift
            ;;
        --both)
            BOTH_PROFILING=true
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
        --model-name)
            MODEL_NAME="$2"
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
# Auto-calculate Node Count and Self-Submit
#===============================================================================

# If no apps specified, default to all 4
if [[ ${#APPS[@]} -eq 0 ]]; then
    ALL_APPS_DEFAULT=true
    NUM_APPS=4
else
    ALL_APPS_DEFAULT=false
    NUM_APPS=${#APPS[@]}
fi

# Calculate required nodes: N apps + 1 vLLM (or 0 if external/skip)
if [[ "$EXTERNAL_MODEL" == "true" ]] || [[ "$SKIP_VLLM" == "true" ]]; then
    REQUIRED_NODES=$NUM_APPS
else
    REQUIRED_NODES=$((NUM_APPS + 1))
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

# Self-submit logic: if not inside a SLURM job, submit via sbatch
if [[ -z "${SLURM_JOB_ID:-}" ]]; then
    echo "Not inside a SLURM job. Self-submitting with ${REQUIRED_NODES} nodes..."
    sbatch -N "${REQUIRED_NODES}" "$0" "$@"
    exit $?
fi

# Already in a SLURM job — validate we have enough nodes
if [[ "${SLURM_JOB_NUM_NODES:-1}" -lt "$REQUIRED_NODES" ]]; then
    echo "ERROR: Need ${REQUIRED_NODES} nodes but only have ${SLURM_JOB_NUM_NODES}"
    echo "  Apps: ${NUM_APPS}, vLLM node: $([[ "$EXTERNAL_MODEL" == "true" ]] || [[ "$SKIP_VLLM" == "true" ]] && echo 0 || echo 1)"
    exit 1
fi

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

# Build the effective app list (used for node mapping and later phases)
if [[ "$ALL_APPS_DEFAULT" == "true" ]]; then
    APPS=("kripke" "laghos" "lulesh" "quicksilver")
fi

# Map apps to agent nodes
declare -A APP_NODE_MAP
for i in "${!APPS[@]}"; do
    APP_NODE_MAP["${APPS[$i]}"]="${AGENT_NODES[$i]}"
done

echo "=================================================="
echo "HPC Benchmark Runner - Agent vs Expert Comparison"
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
for app in "${APPS[@]}"; do
    echo "  ${app}:$(printf '%*s' $((16 - ${#app})) '')${APP_NODE_MAP[$app]}"
done
echo ""
echo "Configuration:"
echo "  SWE-Agent root: ${SWEAGENT_ROOT}"
if [[ "$BASE_MODE" == "true" ]]; then
    echo "  Mode: BASE (run on current test repos)"
else
    echo "  Mode: BENCHMARK (compare vs expert commits)"
    echo "  Dataset: ${DATASET}"
fi
echo "  Output: ${OUTPUT_DIR}"
echo "  Trajectories: ${TRAJ_DIR}"
if [[ "$BOTH_PROFILING" == "true" ]]; then
    echo "  Profiling: BOTH (with_profiling and no_profiling)"
else
    echo "  Profiling: ${PROFILING}"
fi
echo "  Num runs: ${NUM_RUNS}"
[[ -n "$NUM_PROBS" ]] && echo "  Max probs per app: ${NUM_PROBS}"
echo "  Apps: ${APPS[*]}"
[[ ${#INSTANCE_IDS[@]} -gt 0 ]] && echo "  Instance IDs: ${INSTANCE_IDS[*]}"
echo "  External model: ${EXTERNAL_MODEL}"
[[ -n "$MODEL_NAME" ]] && echo "  Model override: ${MODEL_NAME}"
echo "  Skip vLLM: ${SKIP_VLLM}"
echo "  Keep profiles: ${KEEP_PROFILES}"
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

# Export paths for benchmark runner
export SWEAGENT_VENV
export SWEAGENT_ROOT
export VLLM_HOST
export VLLM_PORT

echo "  Modules loaded: openmpi/5.0.7, cudatoolkit/12.4"
echo "  HF_HOME: ${HF_HOME}"
echo "  SWEAGENT_VENV: ${SWEAGENT_VENV}"

# Apply Kripke git config fixes (prevents git fetch/status from hanging on submodules)
# These settings are required because Kripke has 44+ nested submodules that cause
# git operations to timeout during SWE-agent's repo initialization
if [[ -d "${SWEAGENT_ROOT}/Kripke_test/.git" ]]; then
    echo "  Applying Kripke git config fixes..."
    git -C "${SWEAGENT_ROOT}/Kripke_test" config --local status.submodulesummary false
    git -C "${SWEAGENT_ROOT}/Kripke_test" config --local submodule.recurse false
    git -C "${SWEAGENT_ROOT}/Kripke_test" config --local diff.ignoreSubmodules all
    # Remove origin remote to prevent git fetch from trying to contact submodule remotes
    git -C "${SWEAGENT_ROOT}/Kripke_test" remote remove origin 2>/dev/null || true
fi

#===============================================================================
# Phase 2: Start vLLM Server (unless --skip-vllm or --external-model)
#===============================================================================
if [[ "$EXTERNAL_MODEL" == "true" ]]; then
    echo ""
    echo "[Phase 2] Using external model API (--external-model)"
    echo "  OPENAI_API_BASE: ${OPENAI_API_BASE}"
    echo "  Skipping vLLM startup"
    # Set VLLM_HOST/PORT to external values for downstream use
    # Parse host:port from OPENAI_API_BASE (e.g., "https://api.openai.com/v1" -> api.openai.com:443)
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
    # vLLM is now reachable at VLLM_NODE:VLLM_PORT from all nodes
    VLLM_HOST="${VLLM_NODE}"
    echo "  vLLM server started on ${VLLM_NODE} (PID: ${VLLM_PID})"

    # Wait for vLLM to be ready (check from head node via cross-node TCP)
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

# Export vLLM host/port for downstream use
export VLLM_HOST
export VLLM_PORT

#===============================================================================
# Phase 4: Run Benchmark(s) — Parallel per-app execution
#===============================================================================
echo ""
echo "[Phase 4] Running benchmark (parallel per-app)..."

cd "${SWEAGENT_ROOT}"
source "${SWEAGENT_VENV}/bin/activate"

# Install hatchet if needed (must be after venv activation)
# TODO: Change to 'pip install hatchet' once changes are upstreamed
if [[ -d "$HATCHET_DIR" ]]; then
    echo "  Installing hatchet from local fork..."
    pip install --use-pep517 "$HATCHET_DIR" -q 2>/dev/null || echo "  Warning: hatchet install failed"
fi

# Determine profiling configurations to run
if [[ "$BOTH_PROFILING" == "true" ]]; then
    PROFILING_CONFIGS=("with_profiling" "no_profiling")
else
    PROFILING_CONFIGS=("$PROFILING")
fi

# Build common runner arguments
build_runner_args() {
    local app="$1"
    local prof_config="$2"
    local run_num="$3"
    local run_output_dir="$4"
    local run_traj_dir="$5"

    local args=(
        "--output-dir" "${run_output_dir}"
        "--trajectory-dir" "${run_traj_dir}"
        "--profiling" "${prof_config}"
        "--run-number" "${run_num}"
        "--app" "${app}"
        "--vllm-host" "${VLLM_HOST}"
        "--vllm-port" "${VLLM_PORT}"
    )

    if [[ -n "$MODEL_NAME" ]]; then
        args+=("--model-name" "${MODEL_NAME}")
    fi

    if [[ "$BASE_MODE" == "true" ]]; then
        args+=("--base")
    else
        args+=("--dataset" "${DATASET}")
        # Add instance IDs if specified and matching this app
        for iid in "${INSTANCE_IDS[@]}"; do
            args+=("--instance-id" "$iid")
        done
        if [[ -n "$NUM_PROBS" ]]; then
            args+=("--num-probs" "$NUM_PROBS")
        fi
    fi

    echo "${args[@]}"
}

# Run benchmark(s)
TOTAL_SUCCESS=0
TOTAL_FAILED=0

for run_num in $(seq 1 $NUM_RUNS); do
    for prof_config in "${PROFILING_CONFIGS[@]}"; do
        echo ""
        echo "=========================================="
        echo "Run ${run_num}/${NUM_RUNS} - Profiling: ${prof_config}"
        echo "=========================================="

        # Check vLLM is still healthy (skip for external model)
        if [[ "$EXTERNAL_MODEL" != "true" ]]; then
            if ! curl -s "http://${VLLM_HOST}:${VLLM_PORT}/health" > /dev/null 2>&1; then
                echo "ERROR: vLLM server is not responding. Aborting."
                exit 1
            fi
        fi

        # Launch one agent per app, each on its dedicated node
        AGENT_PIDS=()
        declare -A APP_PID_MAP

        for app in "${APPS[@]}"; do
            node="${APP_NODE_MAP[$app]}"

            if [[ "$BOTH_PROFILING" == "true" ]]; then
                RUN_OUTPUT_DIR="${OUTPUT_DIR}/run_${run_num}_${prof_config}/${app}"
                RUN_TRAJ_DIR="${TRAJ_DIR}/run_${run_num}_${prof_config}/${app}"
            else
                RUN_OUTPUT_DIR="${OUTPUT_DIR}/run_${run_num}/${app}"
                RUN_TRAJ_DIR="${TRAJ_DIR}/run_${run_num}/${app}"
            fi
            mkdir -p "${RUN_OUTPUT_DIR}"
            mkdir -p "${RUN_TRAJ_DIR}"

            RUNNER_ARGS_STR=$(build_runner_args "$app" "$prof_config" "$run_num" "$RUN_OUTPUT_DIR" "$RUN_TRAJ_DIR")

            echo "  Launching ${app} on node ${node} -> ${RUN_OUTPUT_DIR}"

            # Determine API env vars
            if [[ "$EXTERNAL_MODEL" == "true" ]]; then
                API_BASE_EXPORT="export OPENAI_API_BASE='${OPENAI_API_BASE}'; export OPENAI_API_KEY='${OPENAI_API_KEY}'"
            else
                API_BASE_EXPORT="export OPENAI_API_BASE='http://${VLLM_HOST}:${VLLM_PORT}/v1'; export OPENAI_API_KEY='dummy-key-ok'"
            fi

            srun --nodes=1 --ntasks=1 --nodelist="${node}" --exclusive --gpu-bind=none \
                bash -c "
                    # Pin child srun calls (e.g., Kripke MPI) to this node only
                    export SLURM_NODELIST=\$(hostname)
                    export SLURM_JOB_NUM_NODES=1
                    # Signal to run scripts that we're inside a batch run
                    export INSIDE_BATCH_RUN=1

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

                    python3 batch/hpc_benchmark_runner.py ${RUNNER_ARGS_STR}
                " > "${RUN_OUTPUT_DIR}/agent.log" 2>&1 &

            local_pid=$!
            AGENT_PIDS+=("$local_pid")
            APP_PID_MAP["$app"]="$local_pid"
            echo "    PID: ${local_pid}"
        done

        # Wait for all agents to finish and collect exit codes
        echo ""
        echo "  Waiting for ${#AGENT_PIDS[@]} agents to complete..."
        RUN_SUCCESS=0
        RUN_FAILED=0

        for app in "${APPS[@]}"; do
            pid="${APP_PID_MAP[$app]}"
            if wait "$pid"; then
                echo "    ${app} (PID ${pid}): SUCCESS"
                RUN_SUCCESS=$((RUN_SUCCESS + 1))
            else
                echo "    ${app} (PID ${pid}): FAILED (exit code $?)"
                RUN_FAILED=$((RUN_FAILED + 1))
            fi
        done

        TOTAL_SUCCESS=$((TOTAL_SUCCESS + RUN_SUCCESS))
        TOTAL_FAILED=$((TOTAL_FAILED + RUN_FAILED))
        echo "  Run ${run_num} ${prof_config}: ${RUN_SUCCESS} succeeded, ${RUN_FAILED} failed"
    done
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

# Collect results from all runs (now in per-app subdirectories: run_*/app/)
for run_dir in sorted(output_dir.glob("run_*")):
    # Check for results directly in run_dir (legacy layout)
    results_file = run_dir / "benchmark_results.json"
    if results_file.exists():
        with open(results_file) as f:
            run_results = json.load(f)
            for r in run_results:
                r['run_number'] = int(run_dir.name.split('_')[1])
            all_results.extend(run_results)
    # Check for results in per-app subdirectories (new parallel layout)
    for app_dir in sorted(run_dir.iterdir()):
        if app_dir.is_dir():
            app_results_file = app_dir / "benchmark_results.json"
            if app_results_file.exists():
                with open(app_results_file) as f:
                    run_results = json.load(f)
                    for r in run_results:
                        r['run_number'] = int(run_dir.name.split('_')[1])
                        r['app_node'] = app_dir.name
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
