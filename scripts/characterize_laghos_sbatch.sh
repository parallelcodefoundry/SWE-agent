#!/bin/bash
#SBATCH -A m2404
#SBATCH -C gpu
#SBATCH -q regular
#SBATCH -t 02:00:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=64
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
#SBATCH -o /pscratch/sd/k/krydzy/SWE-agent/batch_results/laghos_characterization/slurm-%j.out
#SBATCH -e /pscratch/sd/k/krydzy/SWE-agent/batch_results/laghos_characterization/slurm-%j.err
#SBATCH -J laghos_char

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
echo "Job ID: $SLURM_JOB_ID"
echo "Executable: $LAGHOS_EXE"
echo "========================================"
echo ""

# Function to run a single config and capture time
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
        return 0
    else
        local exit_code=$?
        if [ $exit_code -eq 124 ]; then
            echo "  TIMEOUT (>120s)"
            echo "$label | TIMEOUT | - | -" >> "$RESULTS_FILE"
        else
            echo "  FAILED (exit code $exit_code)"
            # Print last few lines of output for debugging
            echo "$output" | tail -20
            echo "$label | FAILED($exit_code) | - | -" >> "$RESULTS_FILE"
        fi
        return 1
    fi
}

# Function to run config 3 times for variance measurement
run_variance() {
    local label="$1"
    shift
    local args=("$@")
    
    echo ""
    echo "=== Variance test: $label ==="
    local times=()
    for i in 1 2 3; do
        local start_time end_time elapsed
        start_time=$(date +%s%N)
        
        if timeout 120 mpirun -np 4 --bind-to none --oversubscribe "$LAGHOS_EXE" "${args[@]}" -d cuda -pa > /dev/null 2>&1; then
            end_time=$(date +%s%N)
            elapsed=$(echo "scale=3; ($end_time - $start_time) / 1000000000" | bc)
            times+=("$elapsed")
            echo "  Run $i: ${elapsed}s"
        else
            echo "  Run $i: FAILED/TIMEOUT"
            return 1
        fi
    done
    
    # Calculate mean and variance
    if [ ${#times[@]} -eq 3 ]; then
        local sum mean
        sum=$(echo "${times[0]} + ${times[1]} + ${times[2]}" | bc)
        mean=$(echo "scale=3; $sum / 3" | bc)
        
        # Calculate max deviation from mean as percentage
        local max_dev=0
        for t in "${times[@]}"; do
            local dev
            dev=$(echo "scale=6; (($t - $mean) / $mean) * 100" | bc)
            # Absolute value
            dev=${dev#-}
            local cmp
            cmp=$(echo "$dev > $max_dev" | bc)
            if [ "$cmp" -eq 1 ]; then
                max_dev=$dev
            fi
        done
        
        echo "  Mean: ${mean}s, Max deviation: ${max_dev}%"
        echo "VARIANCE: $label | ${times[0]} | ${times[1]} | ${times[2]} | mean=${mean} | maxdev=${max_dev}%" >> "$RESULTS_FILE"
    fi
}

# Initialize results file
echo "======================================" > "$RESULTS_FILE"
echo "Laghos Characterization Results" >> "$RESULTS_FILE"
echo "Date: $(date)" >> "$RESULTS_FILE"
echo "Job: $SLURM_JOB_ID" >> "$RESULTS_FILE"
echo "======================================" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "Config | Time(s) | Steps | Energy" >> "$RESULTS_FILE"
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

# Max steps limited
run_config "p1_dim2_rs3_ms50"  -p 1 -dim 2 -rs 3 -ms 50
run_config "p1_dim2_rs3_ms100" -p 1 -dim 2 -rs 3 -ms 100
run_config "p1_dim2_rs2_ms200" -p 1 -dim 2 -rs 2 -ms 200

# Additional configs to explore the space more
run_config "p0_dim2_rs3_tf0.1" -p 0 -dim 2 -rs 3 -tf 0.1
run_config "p0_dim2_rs4_tf0.1" -p 0 -dim 2 -rs 4 -tf 0.1
run_config "p1_dim2_rs3_tf0.1" -p 1 -dim 2 -rs 3 -tf 0.1
run_config "p1_dim2_rs3_tf0.2" -p 1 -dim 2 -rs 3 -tf 0.2
run_config "p1_dim2_rs4_tf0.1" -p 1 -dim 2 -rs 4 -tf 0.1
run_config "p0_dim3_rs2_tf0.1" -p 0 -dim 3 -rs 2 -tf 0.1

echo ""
echo "========================================" 
echo "Phase 1 Complete. Selecting candidates for variance testing."
echo "========================================"
echo ""

# Now read results and pick configs in 10-60s range for variance testing
echo "" >> "$RESULTS_FILE"
echo "======================================" >> "$RESULTS_FILE"
echo "Phase 2: Variance Testing (3 runs each)" >> "$RESULTS_FILE"
echo "======================================" >> "$RESULTS_FILE"

# We'll test variance for configs that looked promising
# Since we don't have dynamic logic here, let's just test a range of likely candidates

# Run variance tests for several configs - we'll pick the best from Phase 1 results
# These are configs likely to be in the 10-60s range based on typical Laghos scaling

run_variance "p0_dim2_rs2_tf0.1" -p 0 -dim 2 -rs 2 -tf 0.1
run_variance "p0_dim2_rs1_tf0.5" -p 0 -dim 2 -rs 1 -tf 0.5
run_variance "p0_dim3_rs1_tf0.1" -p 0 -dim 3 -rs 1 -tf 0.1
run_variance "p1_dim2_rs2_tf0.1" -p 1 -dim 2 -rs 2 -tf 0.1
run_variance "p1_dim2_rs2_tf0.4" -p 1 -dim 2 -rs 2 -tf 0.4
run_variance "p1_dim2_rs3_ms50"  -p 1 -dim 2 -rs 3 -ms 50
run_variance "p1_dim2_rs3_ms100" -p 1 -dim 2 -rs 3 -ms 100
run_variance "p1_dim2_rs3_tf0.1" -p 1 -dim 2 -rs 3 -tf 0.1
run_variance "p1_dim2_rs3_tf0.2" -p 1 -dim 2 -rs 3 -tf 0.2
run_variance "p0_dim2_rs3_tf0.1" -p 0 -dim 2 -rs 3 -tf 0.1

echo ""
echo "========================================"
echo "All phases complete."
echo "Results in: $RESULTS_FILE"
echo "========================================"
cat "$RESULTS_FILE"
