#!/bin/bash
# Full 4×4 matrix validation: 4 frameworks × 4 apps (base mode)
# Run inside salloc with 4 nodes, external model (gpt-4o-mini)

set -o pipefail
LOGFILE="/pscratch/sd/k/krydzy/SWE-agent/batch_results/full_matrix_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOGFILE") 2>&1

echo "============================================"
echo "Full 4×4 Matrix Validation"
echo "Started: $(date)"
echo "SLURM_JOB_ID: ${SLURM_JOB_ID:-not_in_job}"
echo "SLURM_NODELIST: ${SLURM_NODELIST:-none}"
echo "SLURM_JOB_NUM_NODES: ${SLURM_JOB_NUM_NODES:-0}"
echo "Log: $LOGFILE"
echo "============================================"

cd /pscratch/sd/k/krydzy/SWE-agent
source ~/.openai_env

FRAMEWORKS=("codex" "sweagent" "opencode" "openhands")
RESULTS=()

for fw in "${FRAMEWORKS[@]}"; do
    echo ""
    echo "######################################################"
    echo "# FRAMEWORK: $fw"
    echo "# Started: $(date)"
    echo "######################################################"

    START_TIME=$(date +%s)

    bash batch/run_benchmark.sh --base --framework "$fw" --external-model --model-name openai/gpt-4o-mini
    EXIT_CODE=$?

    END_TIME=$(date +%s)
    ELAPSED=$(( END_TIME - START_TIME ))

    echo ""
    echo ">>> $fw completed with exit code $EXIT_CODE in ${ELAPSED}s"
    RESULTS+=("${fw}:exit=${EXIT_CODE}:time=${ELAPSED}s")

    # Brief pause between frameworks
    sleep 5
done

echo ""
echo "============================================"
echo "Full Matrix Complete: $(date)"
echo "============================================"
for r in "${RESULTS[@]}"; do
    echo "  $r"
done
echo "============================================"
