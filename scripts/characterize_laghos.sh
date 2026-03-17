#!/bin/bash
# Laghos Characterization Script
# Runs various parameter configurations to find optimal benchmark settings.
# Target: 10-60 seconds runtime with <2% variance.

set -euo pipefail

LAGHOS_EXE="/pscratch/sd/k/krydzy/SWE-agent/Laghos/laghos"
RESULTS_DIR="/pscratch/sd/k/krydzy/SWE-agent/batch_results/laghos_characterization"
mkdir -p "$RESULTS_DIR"

RESULTS_FILE="$RESULTS_DIR/characterization_results.txt"

# Load modules
module load openmpi/5.0.7 cudatoolkit/12.4

export OMP_NUM_THREADS=1

echo "========================================"
echo "Laghos Characterization - $(date)"
echo "Node: $(hostname)"
echo "Executable: $LAGHOS_EXE"
echo "========================================"
echo ""

# Function to run a single configuration and capture time
run_config() {
    local label="$1"
    shift
    local args=("$@")
    
    echo "--- Config: $label ---"
    echo "  Args: ${args[*]}"
    
    local start_time end_time elapsed
    start_time=$(date +%s%N)
    
    # Run with timeout of 120s
    local output
    if output=$(timeout 120 mpirun -np 4 --bind-to none --oversubscribe "$LAGHOS_EXE" "${args[@]}" -d cuda -pa 2>&1); then
        end_time=$(date +%s%N)
        elapsed=$(echo "scale=3; ($end_time - $start_time) / 1000000000" | bc)
        
        # Extract final energy from output
        local final_energy
        final_energy=$(echo "$output" | grep -oP '\|e\|\s*=\s*\K[\d.eE+-]+' | tail -1)
        local final_step
        final_step=$(echo "$output" | grep -oP 'step\s+\K\d+' | tail -1)
        
        echo "  Time: ${elapsed}s, Steps: ${final_step:-?}, Energy: ${final_energy:-?}"
        echo "$label | ${elapsed} | ${final_step:-?} | ${final_energy:-?}" >> "$RESULTS_FILE"
        echo "$elapsed"
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            echo "  TIMEOUT (>120s)"
            echo "$label | TIMEOUT | - | -" >> "$RESULTS_FILE"
        else
            echo "  FAILED (exit code $exit_code)"
            echo "$label | FAILED($exit_code) | - | -" >> "$RESULTS_FILE"
        fi
        echo "SKIP"
    fi
}

# Initialize results file
echo "Config | Time(s) | Steps | Energy" > "$RESULTS_FILE"
echo "------|---------|-------|-------" >> "$RESULTS_FILE"

echo ""
echo "========================================" 
echo "Phase 1: Survey all configurations (single run each)"
echo "========================================"
echo ""

# Problem 0 (Taylor-Green)
run_config "p0_dim2_rs1_tf0.1" -p 0 -dim 2 -rs 1 -tf 0.1
run_config "p0_dim2_rs2_tf0.1" -p 0 -dim 2 -rs 2 -tf 0.1
run_config "p0_dim2_rs1_tf0.5" -p 0 -dim 2 -rs 1 -tf 0.5
run_config "p0_dim3_rs1_tf0.1" -p 0 -dim 3 -rs 1 -tf 0.1

# Problem 1 (Sedov)
run_config "p1_dim2_rs1_tf0.1" -p 1 -dim 2 -rs 1 -tf 0.1
run_config "p1_dim2_rs1_tf0.4" -p 1 -dim 2 -rs 1 -tf 0.4
run_config "p1_dim2_rs2_tf0.1" -p 1 -dim 2 -rs 2 -tf 0.1
run_config "p1_dim2_rs2_tf0.4" -p 1 -dim 2 -rs 2 -tf 0.4

# Problem 2 (Gresho)
run_config "p2_dim2_rs1_tf0.1" -p 2 -dim 2 -rs 1 -tf 0.1
run_config "p2_dim2_rs2_tf0.1" -p 2 -dim 2 -rs 2 -tf 0.1

# Problem 3 (Triple Point)
run_config "p3_dim2_rs1_tf0.1" -p 3 -dim 2 -rs 1 -tf 0.1

# Max steps limited (default problem but capped)
run_config "p1_dim2_rs3_ms50"  -p 1 -dim 2 -rs 3 -ms 50
run_config "p1_dim2_rs3_ms100" -p 1 -dim 2 -rs 3 -ms 100
run_config "p1_dim2_rs2_ms200" -p 1 -dim 2 -rs 2 -ms 200

echo ""
echo "========================================"
echo "Phase 1 complete. Results in $RESULTS_FILE"
echo "========================================"
cat "$RESULTS_FILE"
