#!/bin/bash
#SBATCH -A m2404
#SBATCH -C gpu
#SBATCH -q debug
#SBATCH -t 00:30:00
#SBATCH -N 1
#SBATCH --ntasks-per-node=4
#SBATCH --cpus-per-task=16
#SBATCH --gpus-per-node=4
#SBATCH --gpu-bind=none
#SBATCH -o /pscratch/sd/k/krydzy/SWE-agent/batch_results/laghos_characterization/char-%j.out
#SBATCH -e /pscratch/sd/k/krydzy/SWE-agent/batch_results/laghos_characterization/char-%j.err
#SBATCH -J laghos_char

module load openmpi/5.0.7 cudatoolkit/12.4
export OMP_NUM_THREADS=1
LAGHOS=/pscratch/sd/k/krydzy/SWE-agent/Laghos/laghos
OUTDIR=/pscratch/sd/k/krydzy/SWE-agent/batch_results/laghos_characterization
RFILE=$OUTDIR/results.txt

echo "=== Laghos Characterization === $(date)" | tee $RFILE
echo "Job: $SLURM_JOB_ID  Node: $(hostname)" | tee -a $RFILE
echo "" | tee -a $RFILE

run_one() {
    local label="$1"; shift
    local start end elapsed
    start=$(date +%s%N)
    if timeout 120 mpirun -np 4 --bind-to none --oversubscribe $LAGHOS "$@" -d cuda -pa > /tmp/laghos_out_$$.txt 2>&1; then
        end=$(date +%s%N)
        elapsed=$(echo "scale=3; ($end - $start) / 1000000000" | bc)
        local energy=$(grep -oP "\|e\|\s*=\s*\K[\d.eE+-]+" /tmp/laghos_out_$$.txt | tail -1)
        local steps=$(grep -oP "step\s+\K\d+" /tmp/laghos_out_$$.txt | tail -1)
        printf "%-35s %8ss  steps=%-6s energy=%s\n" "$label" "$elapsed" "${steps:-?}" "${energy:-?}" | tee -a $RFILE
    else
        local rc=$?
        if [ $rc -eq 124 ]; then
            printf "%-35s TIMEOUT\n" "$label" | tee -a $RFILE
        else
            printf "%-35s FAILED(rc=$rc)\n" "$label" | tee -a $RFILE
            tail -5 /tmp/laghos_out_$$.txt 2>/dev/null | tee -a $RFILE
        fi
    fi
}

echo "=== Phase 1: Survey ===" | tee -a $RFILE

# Problem 0 (Taylor-Green)
run_one "p0 dim2 rs1 tf0.1"  -p 0 -dim 2 -rs 1 -tf 0.1
run_one "p0 dim2 rs2 tf0.1"  -p 0 -dim 2 -rs 2 -tf 0.1
run_one "p0 dim2 rs1 tf0.5"  -p 0 -dim 2 -rs 1 -tf 0.5
run_one "p0 dim3 rs1 tf0.1"  -p 0 -dim 3 -rs 1 -tf 0.1
run_one "p0 dim2 rs3 tf0.1"  -p 0 -dim 2 -rs 3 -tf 0.1
run_one "p0 dim2 rs4 tf0.1"  -p 0 -dim 2 -rs 4 -tf 0.1
run_one "p0 dim3 rs2 tf0.1"  -p 0 -dim 3 -rs 2 -tf 0.1

# Problem 1 (Sedov)
run_one "p1 dim2 rs1 tf0.1"  -p 1 -dim 2 -rs 1 -tf 0.1
run_one "p1 dim2 rs1 tf0.4"  -p 1 -dim 2 -rs 1 -tf 0.4
run_one "p1 dim2 rs2 tf0.1"  -p 1 -dim 2 -rs 2 -tf 0.1
run_one "p1 dim2 rs2 tf0.4"  -p 1 -dim 2 -rs 2 -tf 0.4
run_one "p1 dim2 rs3 tf0.1"  -p 1 -dim 2 -rs 3 -tf 0.1
run_one "p1 dim2 rs3 tf0.2"  -p 1 -dim 2 -rs 3 -tf 0.2
run_one "p1 dim2 rs4 tf0.1"  -p 1 -dim 2 -rs 4 -tf 0.1

# Problem 2 (Gresho)
run_one "p2 dim2 rs1 tf0.1"  -p 2 -dim 2 -rs 1 -tf 0.1
run_one "p2 dim2 rs2 tf0.1"  -p 2 -dim 2 -rs 2 -tf 0.1

# Problem 3 (Triple Point)
run_one "p3 dim2 rs1 tf0.1"  -p 3 -dim 2 -rs 1 -tf 0.1

# Max steps limited
run_one "p1 dim2 rs3 ms50"   -p 1 -dim 2 -rs 3 -ms 50
run_one "p1 dim2 rs3 ms100"  -p 1 -dim 2 -rs 3 -ms 100
run_one "p1 dim2 rs2 ms200"  -p 1 -dim 2 -rs 2 -ms 200

echo "" | tee -a $RFILE
echo "=== Phase 2: Variance testing (3 runs for 10-60s candidates) ===" | tee -a $RFILE

run_variance() {
    local label="$1"; shift
    local t1 t2 t3
    local run_args=("$@")
    
    for i in 1 2 3; do
        local start end
        start=$(date +%s%N)
        if timeout 120 mpirun -np 4 --bind-to none --oversubscribe $LAGHOS "${run_args[@]}" -d cuda -pa > /dev/null 2>&1; then
            end=$(date +%s%N)
            local t=$(echo "scale=3; ($end - $start) / 1000000000" | bc)
            eval "t$i=$t"
        else
            printf "%-35s Run%d FAILED\n" "$label" "$i" | tee -a $RFILE
            return 1
        fi
    done
    
    local sum mean max_dev
    sum=$(echo "$t1 + $t2 + $t3" | bc)
    mean=$(echo "scale=3; $sum / 3" | bc)
    
    # Compute max deviation %
    max_dev=0
    for t in $t1 $t2 $t3; do
        local dev=$(echo "scale=4; (($t - $mean) / $mean) * 100" | bc)
        dev=${dev#-}
        if [ "$(echo "$dev > $max_dev" | bc)" -eq 1 ]; then
            max_dev=$dev
        fi
    done
    
    printf "%-35s mean=%7ss  [%ss, %ss, %ss]  maxdev=%s%%\n" "$label" "$mean" "$t1" "$t2" "$t3" "$max_dev" | tee -a $RFILE
}

# Variance tests for configs likely in 10-60s range
run_variance "p0 dim2 rs2 tf0.1"  -p 0 -dim 2 -rs 2 -tf 0.1
run_variance "p0 dim2 rs3 tf0.1"  -p 0 -dim 2 -rs 3 -tf 0.1
run_variance "p0 dim2 rs4 tf0.1"  -p 0 -dim 2 -rs 4 -tf 0.1
run_variance "p0 dim2 rs1 tf0.5"  -p 0 -dim 2 -rs 1 -tf 0.5
run_variance "p0 dim3 rs1 tf0.1"  -p 0 -dim 3 -rs 1 -tf 0.1
run_variance "p0 dim3 rs2 tf0.1"  -p 0 -dim 3 -rs 2 -tf 0.1
run_variance "p1 dim2 rs1 tf0.4"  -p 1 -dim 2 -rs 1 -tf 0.4
run_variance "p1 dim2 rs2 tf0.1"  -p 1 -dim 2 -rs 2 -tf 0.1
run_variance "p1 dim2 rs2 tf0.4"  -p 1 -dim 2 -rs 2 -tf 0.4
run_variance "p1 dim2 rs3 tf0.1"  -p 1 -dim 2 -rs 3 -tf 0.1
run_variance "p1 dim2 rs3 tf0.2"  -p 1 -dim 2 -rs 3 -tf 0.2
run_variance "p1 dim2 rs3 ms50"   -p 1 -dim 2 -rs 3 -ms 50
run_variance "p1 dim2 rs3 ms100"  -p 1 -dim 2 -rs 3 -ms 100
run_variance "p1 dim2 rs2 ms200"  -p 1 -dim 2 -rs 2 -ms 200
run_variance "p1 dim2 rs4 tf0.1"  -p 1 -dim 2 -rs 4 -tf 0.1

echo "" | tee -a $RFILE
echo "=== DONE === $(date)" | tee -a $RFILE
