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
#SBATCH -o /pscratch/sd/k/krydzy/SWE-agent/batch_results/laghos_characterization/char2-%j.out
#SBATCH -e /pscratch/sd/k/krydzy/SWE-agent/batch_results/laghos_characterization/char2-%j.err
#SBATCH -J laghos_ch2

module load openmpi/5.0.7 cudatoolkit/12.4
export OMP_NUM_THREADS=1
LAGHOS=/pscratch/sd/k/krydzy/SWE-agent/Laghos/laghos
RFILE=/pscratch/sd/k/krydzy/SWE-agent/batch_results/laghos_characterization/results2.txt

echo "=== Laghos Characterization Phase 2 === $(date)" | tee $RFILE
echo "Job: $SLURM_JOB_ID  Node: $(hostname)" | tee -a $RFILE

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
        fi
    fi
}

echo "" | tee -a $RFILE
echo "=== Additional survey configs ===" | tee -a $RFILE

# More configs to fill in the 10-60s range
run_one "p0 dim2 rs4 tf0.5"  -p 0 -dim 2 -rs 4 -tf 0.5
run_one "p0 dim2 rs3 tf0.5"  -p 0 -dim 2 -rs 3 -tf 0.5
run_one "p1 dim2 rs1 tf0.8"  -p 1 -dim 2 -rs 1 -tf 0.8
run_one "p2 dim2 rs2 tf0.5"  -p 2 -dim 2 -rs 2 -tf 0.5
run_one "p2 dim2 rs3 tf0.1"  -p 2 -dim 2 -rs 3 -tf 0.1
run_one "p1 dim2 rs2 tf0.2"  -p 1 -dim 2 -rs 2 -tf 0.2

echo "" | tee -a $RFILE
echo "=== Remaining variance tests ===" | tee -a $RFILE

run_variance "p1 dim2 rs3 ms100" -p 1 -dim 2 -rs 3 -ms 100
run_variance "p2 dim2 rs2 tf0.1" -p 2 -dim 2 -rs 2 -tf 0.1
run_variance "p0 dim2 rs4 tf0.1" -p 0 -dim 2 -rs 4 -tf 0.1

# Run 5x variance for the best candidates 
echo "" | tee -a $RFILE
echo "=== 5-run variance for top candidates ===" | tee -a $RFILE

run_5x() {
    local label="$1"; shift
    local times=()
    local run_args=("$@")
    
    for i in 1 2 3 4 5; do
        local start end
        start=$(date +%s%N)
        if timeout 120 mpirun -np 4 --bind-to none --oversubscribe $LAGHOS "${run_args[@]}" -d cuda -pa > /dev/null 2>&1; then
            end=$(date +%s%N)
            local t=$(echo "scale=3; ($end - $start) / 1000000000" | bc)
            times+=("$t")
        else
            printf "%-35s Run%d FAILED\n" "$label" "$i" | tee -a $RFILE
            return 1
        fi
    done
    
    local sum=0
    for t in "${times[@]}"; do
        sum=$(echo "$sum + $t" | bc)
    done
    local mean=$(echo "scale=3; $sum / 5" | bc)
    
    local max_dev=0
    for t in "${times[@]}"; do
        local dev=$(echo "scale=4; (($t - $mean) / $mean) * 100" | bc)
        dev=${dev#-}
        if [ "$(echo "$dev > $max_dev" | bc)" -eq 1 ]; then
            max_dev=$dev
        fi
    done
    
    printf "%-35s mean=%7ss  [%s]  maxdev=%s%%\n" "$label" "$mean" "${times[*]}" "$max_dev" | tee -a $RFILE
}

run_5x "p1 dim2 rs1 tf0.4"  -p 1 -dim 2 -rs 1 -tf 0.4
run_5x "p1 dim2 rs2 tf0.1"  -p 1 -dim 2 -rs 2 -tf 0.1

echo "" | tee -a $RFILE
echo "=== DONE === $(date)" | tee -a $RFILE
