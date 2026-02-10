#!/bin/bash
# setup_baselines.sh - Generate baseline timing data for Quicksilver and Kripke
#
# This script builds and runs both applications with proper MPI configuration
# (4 MPI ranks, 1 per GPU, with OpenMP threading) to establish baseline
# performance metrics for comparison.
#
# Prerequisites:
#   module load cuda/12.4 openmpi/5.0.7
#
# Usage:
#   ./scripts/setup_baselines.sh
#
# Note: This generates pre-computed baseline data for the problem statement.
# The actual comparison during optimization happens via the harness tools
# (qs_run, kripke_run) or the benchmark_code tool (git-based comparison).

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SWE_AGENT_ROOT="$(dirname "$SCRIPT_DIR")"
BASELINES_DIR="$SWE_AGENT_ROOT/baselines"

# MPI/OpenMP configuration: 4 MPI ranks, 1 per GPU, 8 OpenMP threads per rank
NUM_RANKS=4
OMP_THREADS=8

echo "=== SWE-Agent Baseline Setup ==="
echo "SWE-Agent root: $SWE_AGENT_ROOT"
echo "Baselines dir: $BASELINES_DIR"
echo "MPI ranks: $NUM_RANKS"
echo "OpenMP threads per rank: $OMP_THREADS"
echo ""

# Check for required modules
if ! command -v nvcc &> /dev/null; then
    echo "ERROR: CUDA not found. Run: module load cuda/12.4"
    exit 1
fi

if ! command -v mpicxx &> /dev/null; then
    echo "ERROR: MPI not found. Run: module load openmpi/5.0.7"
    exit 1
fi

if ! command -v mpirun &> /dev/null; then
    echo "ERROR: mpirun not found. Run: module load openmpi/5.0.7"
    exit 1
fi

# Load cmake module for Kripke (needs 3.23+)
if module load cmake 2>/dev/null; then
    echo "Loaded cmake module"
else
    CMAKE_VERSION=$(cmake --version 2>/dev/null | head -1 | awk '{print $3}' | cut -d. -f1,2)
    if [ -z "$CMAKE_VERSION" ]; then
        echo "WARNING: cmake not found. Kripke build may fail."
    elif (( $(echo "$CMAKE_VERSION < 3.23" | bc -l) )); then
        echo "WARNING: cmake $CMAKE_VERSION found but Kripke needs 3.23+. Try: module load cmake"
    fi
fi

echo "CUDA version: $(nvcc --version | grep release | awk '{print $6}')"
echo "MPI: $(mpicxx --version | head -1)"
echo ""

# Set OpenMP environment
export OMP_NUM_THREADS=$OMP_THREADS
export OMP_PROC_BIND=spread
export OMP_PLACES=threads

# =============================================================================
# Quicksilver Baseline
# =============================================================================
echo "=== Building Quicksilver Baseline ==="
QS_DIR="$SWE_AGENT_ROOT/Quicksilver"
QS_BASELINE_DIR="$BASELINES_DIR/quicksilver"

if [ ! -d "$QS_DIR" ]; then
    echo "ERROR: Quicksilver directory not found at $QS_DIR"
    exit 1
fi

mkdir -p "$QS_BASELINE_DIR"
cd "$QS_DIR/src"

# Clean and build with MPI and OpenMP support
echo "Building Quicksilver with MPI and OpenMP..."
make clean 2>/dev/null || true
make -j8 CXX=mpicxx CXXFLAGS="-O3 -std=c++11 -fopenmp" CPPFLAGS="-DHAVE_MPI -DHAVE_OPENMP" LDFLAGS=

if [ ! -f "qs" ]; then
    echo "ERROR: Quicksilver build failed - executable not found"
    exit 1
fi

echo "Running Quicksilver baseline with $NUM_RANKS MPI ranks..."
# Run with srun: 1 node, 4 tasks (1 per GPU)
srun -N 1 --ntasks-per-node=$NUM_RANKS --gpus-per-task=1 --gpu-bind=none \
    ./qs --lx 20 --ly 20 --lz 20 \
         --nx 20 --ny 20 --nz 20 \
         --nParticles 100000 \
         --nSteps 10 \
    > "$QS_BASELINE_DIR/baseline_output.txt" 2>&1

# Parse timing from output
echo "Parsing Quicksilver timing..."
python3 - "$QS_BASELINE_DIR" << 'EOF'
import json
import re
import sys

baseline_dir = sys.argv[1]
try:
    with open(f"{baseline_dir}/baseline_output.txt", "r") as f:
        output = f.read()
except FileNotFoundError:
    print("ERROR: No output file found")
    sys.exit(1)

timers = {}

# Parse Quicksilver timer table format:
# Name                            number    microSecs    microSecs    microSecs    microSecs   Efficiency
#                               of calls          min          avg          max       stddev       Rating
# main                                 1    1.048e+07    1.054e+07    1.060e+07    4.017e+04        99.46
# cycleTracking                       10    9.315e+06    9.381e+06    9.407e+06    3.820e+04        99.72
timer_pattern = re.compile(
    r'^(\w+)\s+(\d+)\s+([\d.e+\-]+)\s+([\d.e+\-]+)\s+([\d.e+\-]+)\s+([\d.e+\-]+)\s+([\d.]+)\s*$',
    re.MULTILINE
)
for match in timer_pattern.finditer(output):
    name = match.group(1)
    avg_microsecs = float(match.group(4))  # avg column
    max_microsecs = float(match.group(5))  # max column
    # Convert microseconds to seconds
    timers[f"{name}_avg_s"] = avg_microsecs / 1e6
    timers[f"{name}_max_s"] = max_microsecs / 1e6

# Extract Figure of Merit
fom_match = re.search(r'Figure Of Merit\s+([\d.e+\-]+)', output)
if fom_match:
    timers["figure_of_merit"] = float(fom_match.group(1))

# Also capture key timers in simple form for comparison
if "cycleTracking_max_s" in timers:
    timers["cycleTracking_seconds"] = timers["cycleTracking_max_s"]
if "main_max_s" in timers:
    timers["total_seconds"] = timers["main_max_s"]

# If no structured timers found
if not timers:
    timers["note"] = "No structured timing found - check baseline_output.txt manually"
    timers["baseline_generated"] = True

with open(f"{baseline_dir}/baseline_timing.json", "w") as f:
    json.dump(timers, f, indent=2)

print(f"Quicksilver baseline timing: {json.dumps(timers, indent=2)}")
EOF

echo "Quicksilver baseline complete!"
echo ""

# =============================================================================
# Kripke Baseline
# =============================================================================
echo "=== Building Kripke Baseline ==="
KRIPKE_DIR="$SWE_AGENT_ROOT/Kripke"
KRIPKE_BASELINE_DIR="$BASELINES_DIR/kripke"

if [ ! -d "$KRIPKE_DIR" ]; then
    echo "ERROR: Kripke directory not found at $KRIPKE_DIR"
    exit 1
fi

mkdir -p "$KRIPKE_BASELINE_DIR"
cd "$KRIPKE_DIR"

# Initialize submodules if needed
if [ ! -f "tpl/raja/CMakeLists.txt" ]; then
    echo "Initializing Kripke submodules..."
    git submodule update --init --recursive
fi

# Build with MPI and OpenMP
echo "Building Kripke with MPI and OpenMP..."
mkdir -p build
cd build
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DENABLE_OPENMP=ON \
    -DENABLE_MPI=ON \
    -DCMAKE_CXX_COMPILER=mpicxx \
    -DCMAKE_C_COMPILER=mpicc

make -j8

if [ ! -f "kripke.exe" ]; then
    echo "ERROR: Kripke build failed - executable not found"
    exit 1
fi

echo "Running Kripke baseline with $NUM_RANKS MPI ranks..."
# Run with srun: 1 node, 4 tasks (CPU-only OpenMP build, no GPU options needed)
# Use --procs to specify MPI decomposition (2x2x1 = 4 ranks)
srun -N 1 --ntasks-per-node=$NUM_RANKS \
    ./kripke.exe --arch OpenMP --layout DGZ \
                     --niter 10 --zones 32,32,32 --groups 32 \
                     --procs 2,2,1 \
    > "$KRIPKE_BASELINE_DIR/baseline_output.txt" 2>&1

# Parse timing from output
echo "Parsing Kripke timing..."
python3 - "$KRIPKE_BASELINE_DIR" << 'KRIPKE_EOF'
import json
import re
import sys

baseline_dir = sys.argv[1]
try:
    with open(f"{baseline_dir}/baseline_output.txt", "r") as f:
        output = f.read()
except FileNotFoundError:
    print("ERROR: No output file found")
    sys.exit(1)

timers = {}

# Kripke prints timing in a structured format
# Look for lines like: "Timer: LTimes = 1.234 s"
for line in output.split('\n'):
    match = re.search(r'Timer:\s*(\w+)\s*=\s*([\d.]+)\s*s', line)
    if match:
        timers[match.group(1)] = float(match.group(2))

# Also look for TIMER_DATA format
timer_names_match = re.search(r'TIMER_NAMES:\s*(.+)', output)
timer_data_match = re.search(r'TIMER_DATA:\s*(.+)', output)
if timer_names_match and timer_data_match:
    names = timer_names_match.group(1).strip().split(',')
    values = timer_data_match.group(1).strip().split(',')
    for name, value in zip(names, values):
        try:
            timers[name.strip()] = float(value.strip())
        except ValueError:
            pass

# Look for "Solve took X.XXX seconds"
match = re.search(r'Solve\s+took\s+([\d.]+)\s*(?:seconds|s)', output, re.IGNORECASE)
if match:
    timers["total"] = float(match.group(1))

# If no structured timers found
if not timers:
    timers["note"] = "No structured timing found - check baseline_output.txt manually"
    timers["baseline_generated"] = True

with open(f"{baseline_dir}/baseline_timing.json", "w") as f:
    json.dump(timers, f, indent=2)

print(f"Kripke baseline timing: {json.dumps(timers, indent=2)}")
KRIPKE_EOF

echo "Kripke baseline complete!"
echo ""

# =============================================================================
# Summary
# =============================================================================
echo "=== Baseline Setup Complete ==="
echo ""
echo "Configuration used:"
echo "  - MPI ranks: $NUM_RANKS"
echo "  - OpenMP threads per rank: $OMP_THREADS"
echo ""
echo "Quicksilver baseline:"
echo "  - Output: $QS_BASELINE_DIR/baseline_output.txt"
echo "  - Timing: $QS_BASELINE_DIR/baseline_timing.json"
cat "$QS_BASELINE_DIR/baseline_timing.json" 2>/dev/null || echo "  (no timing data)"
echo ""
echo "Kripke baseline:"
echo "  - Output: $KRIPKE_BASELINE_DIR/baseline_output.txt"
echo "  - Timing: $KRIPKE_BASELINE_DIR/baseline_timing.json"
cat "$KRIPKE_BASELINE_DIR/baseline_timing.json" 2>/dev/null || echo "  (no timing data)"
echo ""
echo "NOTE: These baselines are informational for the problem statement."
echo "The actual comparison during optimization happens through:"
echo "  - Harness tools (qs_run, kripke_run) for runtime comparison"
echo "  - benchmark_code for git-based A/B comparison against baseline branch"
