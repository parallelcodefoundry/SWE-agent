#!/bin/bash
# Setup proxy applications for HPC SWE-Agent experiments
#
# Clones all 4 proxy apps, builds them, and creates test copies.
# Run from the SWE-agent root directory.
#
# Usage:
#   ./scripts/setup_apps.sh                # Setup all apps
#   ./scripts/setup_apps.sh --kripke       # Setup only Kripke
#   ./scripts/setup_apps.sh --no-build     # Clone/copy without building
#   ./scripts/setup_apps.sh --no-test      # Skip creating test copies
#   ./scripts/setup_apps.sh --prefix /path  # Install apps to a custom directory
#   ./scripts/setup_apps.sh --help         # Show help

set -e

# Track failures but don't exit on them
FAILED_APPS=""
app_failed() {
    FAILED_APPS="${FAILED_APPS} $1"
    echo "  ERROR: $1 build failed"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SWEAGENT_ROOT="$(dirname "$SCRIPT_DIR")"

# Parse arguments
SETUP_KRIPKE=false
SETUP_LAGHOS=false
SETUP_LULESH=false
SETUP_QUICKSILVER=false
DO_BUILD=true
DO_TEST=true
ANY_APP_SPECIFIED=false
APP_PREFIX=""

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Clone, build, and create test copies of HPC proxy applications."
    echo "Run from the SWE-agent root directory."
    echo ""
    echo "Options:"
    echo "  --kripke       Setup Kripke only"
    echo "  --laghos       Setup Laghos only"
    echo "  --lulesh       Setup Lulesh only"
    echo "  --quicksilver  Setup Quicksilver only"
    echo "  --no-build     Skip building (just clone and copy)"
    echo "  --no-test      Skip creating *_test copies"
    echo "  --prefix DIR   Install apps into DIR instead of SWE-agent root"
    echo "  --help         Show this help message"
    echo ""
    echo "If no app flags are specified, all apps are set up."
    echo ""
    echo "Prerequisites (loaded automatically by the script):"
    echo "  module load python"
    echo "  module load cmake"
    echo "  module load openmpi/5.0.7"
    echo "  module load cuda/12.4"
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --kripke)
            SETUP_KRIPKE=true
            ANY_APP_SPECIFIED=true
            shift
            ;;
        --laghos)
            SETUP_LAGHOS=true
            ANY_APP_SPECIFIED=true
            shift
            ;;
        --lulesh)
            SETUP_LULESH=true
            ANY_APP_SPECIFIED=true
            shift
            ;;
        --quicksilver)
            SETUP_QUICKSILVER=true
            ANY_APP_SPECIFIED=true
            shift
            ;;
        --no-build)
            DO_BUILD=false
            shift
            ;;
        --no-test)
            DO_TEST=false
            shift
            ;;
        --prefix)
            APP_PREFIX="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run with --help for usage."
            exit 1
            ;;
    esac
done

if [[ "$ANY_APP_SPECIFIED" == "false" ]]; then
    SETUP_KRIPKE=true
    SETUP_LAGHOS=true
    SETUP_LULESH=true
    SETUP_QUICKSILVER=true
fi

# Load modules
echo "Loading modules..."
module load python 2>/dev/null || true
module load cmake 2>/dev/null || true
module load openmpi/5.0.7 2>/dev/null || true
module load cuda/12.4 2>/dev/null || true

# Ensure CUDA environment is set (fallback if module load didn't work)
if [[ -z "$CUDA_HOME" ]]; then
    for cuda_candidate in /opt/nvidia/hpc_sdk/Linux_x86_64/24.5/cuda/12.4 /usr/local/cuda; do
        if [[ -d "$cuda_candidate" ]]; then
            export CUDA_HOME="$cuda_candidate"
            export CUDATOOLKIT_HOME="$cuda_candidate"
            break
        fi
    done
fi
if [[ -n "$CUDA_HOME" ]]; then
    export PATH="$CUDA_HOME/bin:$PATH"
    export LD_LIBRARY_PATH="$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}"
    # CUDA math libraries (cusparse, cublas, cusolver, curand) are in a separate path on Perlmutter
    CUDA_MATH_LIBS="${CUDA_HOME/cuda/math_libs}/lib64"
    if [[ -d "$CUDA_MATH_LIBS" ]]; then
        export LD_LIBRARY_PATH="$CUDA_MATH_LIBS:$LD_LIBRARY_PATH"
        export LIBRARY_PATH="$CUDA_MATH_LIBS:${LIBRARY_PATH:-}"
    fi
fi

echo "  CUDA_HOME=$CUDA_HOME"
echo "  cmake: $(cmake --version 2>/dev/null | head -1 || echo 'not found')"

# Determine where to install apps
if [[ -n "$APP_PREFIX" ]]; then
    APP_DIR="$(mkdir -p "$APP_PREFIX" && cd "$APP_PREFIX" && pwd)"
    echo "Installing apps to custom prefix: $APP_DIR"
    echo "Symlinks will be created in $SWEAGENT_ROOT so harness scripts can find the apps."
else
    APP_DIR="$SWEAGENT_ROOT"
fi

cd "$APP_DIR"
echo "Working directory: $APP_DIR"
echo ""

# Create a symlink in SWEAGENT_ROOT pointing to the app in APP_DIR
create_symlink() {
    local name="$1"
    if [[ "$APP_DIR" != "$SWEAGENT_ROOT" ]]; then
        if [[ -L "$SWEAGENT_ROOT/$name" ]]; then
            rm "$SWEAGENT_ROOT/$name"
        fi
        if [[ ! -e "$SWEAGENT_ROOT/$name" ]]; then
            ln -s "$APP_DIR/$name" "$SWEAGENT_ROOT/$name"
            echo "  Symlinked $SWEAGENT_ROOT/$name -> $APP_DIR/$name"
        else
            echo "  Warning: $SWEAGENT_ROOT/$name already exists, skipping symlink"
        fi
    fi
}

#===============================================================================
# Kripke
#===============================================================================
if [[ "$SETUP_KRIPKE" == "true" ]]; then
    echo "========================================="
    echo "Setting up Kripke"
    echo "========================================="

    if [[ -d "Kripke" ]]; then
        echo "  Kripke/ already exists, skipping clone"
    else
        echo "  Cloning Kripke..."
        git clone --recursive https://github.com/LLNL/Kripke.git
        cd Kripke
        git checkout develop
        git submodule update --init --recursive
        cd "$APP_DIR"
    fi

    if [[ "$DO_BUILD" == "true" ]]; then
        echo "  Building Kripke (CUDA via RAJA)..."
        (
            export KRIPKE_ROOT="$APP_DIR/Kripke"
            "$SWEAGENT_ROOT/tools/kripke_harness/bin/kripke_build" --arch CUDA
        ) || app_failed "Kripke"
    fi

    if [[ "$DO_TEST" == "true" ]]; then
        if [[ -d "Kripke_test" ]]; then
            echo "  Kripke_test/ already exists, skipping copy"
        else
            echo "  Creating Kripke_test/ copy..."
            cp -r Kripke Kripke_test
        fi

        if [[ "$DO_BUILD" == "true" ]]; then
            echo "  Building Kripke_test..."
            (
                export KRIPKE_ROOT="$APP_DIR/Kripke_test"
                "$SWEAGENT_ROOT/tools/kripke_harness/bin/kripke_build" --clean --arch CUDA
            ) || app_failed "Kripke_test"
        fi
    fi

    create_symlink "Kripke"
    [[ "$DO_TEST" == "true" ]] && create_symlink "Kripke_test"

    echo "  Kripke setup complete!"
    echo ""
fi

#===============================================================================
# Laghos
#===============================================================================
if [[ "$SETUP_LAGHOS" == "true" ]]; then
    echo "========================================="
    echo "Setting up Laghos"
    echo "========================================="

    if [[ -d "Laghos" ]]; then
        echo "  Laghos/ already exists, skipping clone"
    else
        echo "  Cloning Laghos..."
        git clone https://github.com/CEED/Laghos.git
    fi

    if [[ "$DO_BUILD" == "true" ]]; then
        echo "  Building Laghos dependencies (MFEM, hypre, METIS) and Laghos..."
        echo "  This may take a while..."
        (
            # Pre-download METIS if the upstream URL is broken
            if [[ ! -d "$APP_DIR/metis-4.0" ]]; then
                echo "  Pre-downloading METIS tarball..."
                cd "$APP_DIR"
                if ! wget -q -O metis-4.0.3.tar.gz "http://glaros.dtc.umn.edu/gkhome/fetch/sw/metis/OLD/metis-4.0.3.tar.gz" 2>/dev/null; then
                    echo "  Original METIS URL failed, trying GitHub mirror..."
                    wget -q -O metis-4.0.3.tar.gz "https://github.com/mfem/tpls/raw/gh-pages/metis-4.0.3.tar.gz" 2>/dev/null || \
                    wget -q -O metis-4.0.3.tar.gz "https://ftp.mcs.anl.gov/pub/petsc/externalpackages/metis-4.0.3.tar.gz" 2>/dev/null || true
                fi
                if [[ -f metis-4.0.3.tar.gz ]]; then
                    tar -xzf metis-4.0.3.tar.gz
                    mv metis-4.0.3 metis-4.0
                    cd metis-4.0
                    make OPTFLAGS="-O2" -j8
                    cd "$APP_DIR"
                    rm -f metis-4.0.3.tar.gz
                fi
            fi
            export LAGHOS_ROOT="$APP_DIR/Laghos"
            "$SWEAGENT_ROOT/tools/laghos_harness/bin/laghos_build" --setup
        ) || app_failed "Laghos"
    fi

    if [[ "$DO_TEST" == "true" ]]; then
        if [[ -d "Laghos_test" ]]; then
            echo "  Laghos_test/ already exists, skipping copy"
        else
            echo "  Creating Laghos_test/ copy..."
            cp -r Laghos Laghos_test
            # Both Laghos/ and Laghos_test/ share ../mfem, ../hypre, ../metis-4.0
            # since their Makefiles reference these via relative paths to parent dir
        fi

        if [[ "$DO_BUILD" == "true" ]]; then
            echo "  Building Laghos_test..."
            (
                export LAGHOS_ROOT="$APP_DIR/Laghos_test"
                "$SWEAGENT_ROOT/tools/laghos_harness/bin/laghos_build"
            ) || app_failed "Laghos_test"
        fi
    fi

    create_symlink "Laghos"
    [[ "$DO_TEST" == "true" ]] && create_symlink "Laghos_test"
    # Also symlink shared dependencies if they were built
    for dep in mfem hypre metis-4.0; do
        [[ -d "$APP_DIR/$dep" ]] && create_symlink "$dep"
    done

    echo "  Laghos setup complete!"
    echo ""
fi

#===============================================================================
# Lulesh
#===============================================================================
if [[ "$SETUP_LULESH" == "true" ]]; then
    echo "========================================="
    echo "Setting up Lulesh"
    echo "========================================="

    if [[ -d "Lulesh" ]]; then
        echo "  Lulesh/ already exists, skipping clone"
    else
        echo "  Cloning Lulesh..."
        git clone https://github.com/LLNL/LULESH.git Lulesh
        cd Lulesh
        git checkout 2.0.2-dev
        cd "$APP_DIR"
    fi

    if [[ "$DO_BUILD" == "true" ]]; then
        echo "  Building Lulesh (CUDA+MPI, sm_80)..."
        (
            export LULESH_ROOT="$APP_DIR/Lulesh/cuda"
            "$SWEAGENT_ROOT/tools/lulesh_harness/bin/lulesh_build" --use-mpi
        ) || app_failed "Lulesh"
    fi

    if [[ "$DO_TEST" == "true" ]]; then
        if [[ -d "Lulesh_test" ]]; then
            echo "  Lulesh_test/ already exists, skipping copy"
        else
            echo "  Creating Lulesh_test/ copy..."
            cp -r Lulesh Lulesh_test
        fi

        if [[ "$DO_BUILD" == "true" ]]; then
            echo "  Building Lulesh_test (CUDA+MPI)..."
            (
                export LULESH_ROOT="$APP_DIR/Lulesh_test/cuda"
                "$SWEAGENT_ROOT/tools/lulesh_harness/bin/lulesh_build" --use-mpi
            ) || app_failed "Lulesh_test"
        fi
    fi

    create_symlink "Lulesh"
    [[ "$DO_TEST" == "true" ]] && create_symlink "Lulesh_test"

    echo "  Lulesh setup complete!"
    echo ""
fi

#===============================================================================
# Quicksilver
#===============================================================================
if [[ "$SETUP_QUICKSILVER" == "true" ]]; then
    echo "========================================="
    echo "Setting up Quicksilver"
    echo "========================================="

    if [[ -d "Quicksilver" ]]; then
        echo "  Quicksilver/ already exists, skipping clone"
    else
        echo "  Cloning Quicksilver..."
        git clone https://github.com/LLNL/Quicksilver.git
    fi

    if [[ "$DO_BUILD" == "true" ]]; then
        echo "  Building Quicksilver (CUDA + OpenMP, sm_80)..."
        (
            export QUICKSILVER_ROOT="$APP_DIR/Quicksilver"
            "$SWEAGENT_ROOT/tools/quicksilver_harness/bin/qs_build"
        ) || app_failed "Quicksilver"
    fi

    if [[ "$DO_TEST" == "true" ]]; then
        if [[ -d "Quicksilver_test" ]]; then
            echo "  Quicksilver_test/ already exists, skipping copy"
        else
            echo "  Creating Quicksilver_test/ copy..."
            cp -r Quicksilver Quicksilver_test
        fi

        if [[ "$DO_BUILD" == "true" ]]; then
            echo "  Building Quicksilver_test..."
            (
                export QUICKSILVER_ROOT="$APP_DIR/Quicksilver_test"
                "$SWEAGENT_ROOT/tools/quicksilver_harness/bin/qs_build"
            ) || app_failed "Quicksilver_test"
        fi
    fi

    create_symlink "Quicksilver"
    [[ "$DO_TEST" == "true" ]] && create_symlink "Quicksilver_test"

    echo "  Quicksilver setup complete!"
    echo ""
fi

echo "========================================="
echo "Setup complete!"
echo "========================================="
echo ""
echo "Directory layout:"
ls -d */ 2>/dev/null | grep -E '(Kripke|Laghos|Lulesh|Quicksilver)' | sed 's/^/  /'
echo ""
if [[ -n "$FAILED_APPS" ]]; then
    echo "WARNING: The following builds FAILED:$FAILED_APPS"
    echo ""
fi
echo "To reset test repos between agent runs:"
echo "  ./scripts/reset_test_repos.sh"
