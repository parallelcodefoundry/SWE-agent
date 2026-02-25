#!/bin/bash
# Full 5×4 matrix: 5 frameworks × 4 LLNL apps (base mode)
# Run inside salloc or as standalone script. Requires 4+ nodes.
#
# Usage:
#   # LLNL only (default)
#   salloc --nodes 4 --qos interactive --time 06:00:00 --constraint gpu --gpus-per-node 4 --account m2404
#   bash batch/run_full_matrix.sh
#
#   # LLNL + GPA
#   bash batch/run_full_matrix.sh --gpa
#
#   # Specific frameworks only
#   bash batch/run_full_matrix.sh --frameworks "codex openhands claude"
#
#   # Custom model
#   bash batch/run_full_matrix.sh --model openai/gpt-4.1-mini

set -o pipefail
LOGFILE="/pscratch/sd/k/krydzy/SWE-agent/batch_results/full_matrix_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOGFILE") 2>&1

# Defaults
MODEL="openai/gpt-4.1-mini"
FRAMEWORKS=("codex" "sweagent" "opencode" "openhands" "claude")
RUN_GPA=false
APP_FLAGS=""  # empty = all LLNL apps

# Parse args
while [[ $# -gt 0 ]]; do
    case $1 in
        --gpa) RUN_GPA=true; shift ;;
        --model) MODEL="$2"; shift 2 ;;
        --frameworks) IFS=' ' read -ra FRAMEWORKS <<< "$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

echo "============================================"
echo "Full Matrix Benchmark"
echo "Started: $(date)"
echo "SLURM_JOB_ID: ${SLURM_JOB_ID:-not_in_job}"
echo "SLURM_NODELIST: ${SLURM_NODELIST:-none}"
echo "SLURM_JOB_NUM_NODES: ${SLURM_JOB_NUM_NODES:-0}"
echo "Model: $MODEL"
echo "Frameworks: ${FRAMEWORKS[*]}"
echo "GPA: $RUN_GPA"
echo "Log: $LOGFILE"
echo "============================================"

cd /pscratch/sd/k/krydzy/SWE-agent
source ~/.openai_env 2>/dev/null || true

RESULTS=()

run_framework() {
    local fw="$1"
    local extra_flags="$2"

    echo ""
    echo "######################################################"
    echo "# FRAMEWORK: $fw ${extra_flags}"
    echo "# Started: $(date)"
    echo "######################################################"

    local START_TIME=$(date +%s)

    if [[ "$fw" == "claude" ]]; then
        # Claude Code uses Anthropic API directly — no --external-model needed
        bash batch/run_benchmark.sh --base --framework claude ${extra_flags}
    else
        bash batch/run_benchmark.sh --base --framework "$fw" --external-model --model-name "$MODEL" ${extra_flags}
    fi
    local EXIT_CODE=$?

    local END_TIME=$(date +%s)
    local ELAPSED=$(( END_TIME - START_TIME ))

    echo ""
    echo ">>> $fw ${extra_flags} completed with exit code $EXIT_CODE in ${ELAPSED}s"
    RESULTS+=("${fw}${extra_flags:+ ($extra_flags)}:exit=${EXIT_CODE}:time=${ELAPSED}s")

    sleep 5
}

# Run LLNL apps (all 4: kripke, laghos, lulesh, quicksilver)
for fw in "${FRAMEWORKS[@]}"; do
    run_framework "$fw" ""
done

# Run GPA apps if requested
if [[ "$RUN_GPA" == "true" ]]; then
    echo ""
    echo "============================================"
    echo "Starting GPA benchmark runs"
    echo "============================================"
    for fw in "${FRAMEWORKS[@]}"; do
        run_framework "$fw" "--gpa"
    done
fi

echo ""
echo "============================================"
echo "Full Matrix Complete: $(date)"
echo "============================================"
for r in "${RESULTS[@]}"; do
    echo "  $r"
done
echo "============================================"
