#!/bin/bash
# Reset test repos to clean state and rebuild
#
# Usage: ./scripts/reset_test_repos.sh [OPTIONS]
#
# Options:
#   --kripke       Reset Kripke_test only
#   --quicksilver  Reset Quicksilver_test only
#   --laghos       Reset Laghos_test only
#   --lulesh       Reset Lulesh_test only
#   --no-build     Skip rebuilding (just git reset)
#   (If no app flags specified, all apps are reset)
#
# This script resets test repos to clean state and optionally rebuilds them.

set -e  # Exit on error

SWEAGENT_ROOT="${SWEAGENT_ROOT:-/pscratch/sd/k/krydzy/SWE-agent}"

# Parse arguments
RESET_KRIPKE=false
RESET_QUICKSILVER=false
RESET_LAGHOS=false
RESET_LULESH=false
DO_BUILD=true
ANY_APP_SPECIFIED=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --kripke)
            RESET_KRIPKE=true
            ANY_APP_SPECIFIED=true
            shift
            ;;
        --quicksilver)
            RESET_QUICKSILVER=true
            ANY_APP_SPECIFIED=true
            shift
            ;;
        --laghos)
            RESET_LAGHOS=true
            ANY_APP_SPECIFIED=true
            shift
            ;;
        --lulesh)
            RESET_LULESH=true
            ANY_APP_SPECIFIED=true
            shift
            ;;
        --no-build)
            DO_BUILD=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# If no app specified, reset all
if [[ "$ANY_APP_SPECIFIED" == "false" ]]; then
    RESET_KRIPKE=true
    RESET_QUICKSILVER=true
    RESET_LAGHOS=true
    RESET_LULESH=true
fi

# Load required modules
echo "Loading modules..."
module load python 2>/dev/null || true
module load cmake 2>/dev/null || true  # Kripke requires cmake 3.23+
module load openmpi/5.0.7 2>/dev/null || true
module load cuda/12.4 2>/dev/null || true

#===============================================================================
# Kripke
#===============================================================================
if [[ "$RESET_KRIPKE" == "true" ]]; then
    echo ""
    echo "========================================="
    echo "Resetting Kripke_test..."
    echo "========================================="

    if [[ -d "$SWEAGENT_ROOT/Kripke_test" ]]; then
        cd "$SWEAGENT_ROOT/Kripke_test"

        echo "Reverting any uncommitted changes..."
        git checkout . 2>/dev/null || true

        echo "Removing untracked files..."
        git clean -fd 2>/dev/null || true

        echo "Removing build directory..."
        rm -rf build

        # Apply git config fixes to prevent submodule recursion issues
        # Kripke has 44+ nested submodules that cause git operations to hang
        echo "Applying git config fixes for submodule recursion..."
        git config --local status.submodulesummary false
        git config --local submodule.recurse false
        git config --local diff.ignoreSubmodules all
        # Remove origin remote to prevent git fetch from trying to contact submodule remotes
        git remote remove origin 2>/dev/null || true

        if [[ "$DO_BUILD" == "true" ]]; then
            echo "Rebuilding Kripke_test..."
            export KRIPKE_ROOT="$SWEAGENT_ROOT/Kripke_test"
            "$SWEAGENT_ROOT/tools/kripke_harness/bin/kripke_build" --arch CUDA || echo "  Warning: Kripke build failed"
        fi

        echo "Kripke_test reset complete!"
    else
        echo "  Warning: Kripke_test directory not found"
    fi
fi

#===============================================================================
# Quicksilver
#===============================================================================
if [[ "$RESET_QUICKSILVER" == "true" ]]; then
    echo ""
    echo "========================================="
    echo "Resetting Quicksilver_test..."
    echo "========================================="

    if [[ -d "$SWEAGENT_ROOT/Quicksilver_test" ]]; then
        cd "$SWEAGENT_ROOT/Quicksilver_test"

        echo "Reverting any uncommitted changes..."
        git checkout . 2>/dev/null || true

        echo "Removing untracked files..."
        git clean -fd 2>/dev/null || true

        if [[ "$DO_BUILD" == "true" ]]; then
            echo "Rebuilding Quicksilver_test..."
            export QUICKSILVER_ROOT="$SWEAGENT_ROOT/Quicksilver_test"
            "$SWEAGENT_ROOT/tools/quicksilver_harness/bin/qs_build" || echo "  Warning: Quicksilver build failed"
        fi

        echo "Quicksilver_test reset complete!"
    else
        echo "  Warning: Quicksilver_test directory not found"
    fi
fi

#===============================================================================
# Laghos
#===============================================================================
if [[ "$RESET_LAGHOS" == "true" ]]; then
    echo ""
    echo "========================================="
    echo "Resetting Laghos_test..."
    echo "========================================="

    if [[ -d "$SWEAGENT_ROOT/Laghos_test" ]]; then
        cd "$SWEAGENT_ROOT/Laghos_test"

        echo "Reverting any uncommitted changes..."
        git checkout . 2>/dev/null || true

        echo "Removing untracked files..."
        git clean -fd 2>/dev/null || true

        echo "Removing build artifacts..."
        rm -f laghos 2>/dev/null || true

        if [[ "$DO_BUILD" == "true" ]]; then
            echo "Rebuilding Laghos_test..."
            export LAGHOS_ROOT="$SWEAGENT_ROOT/Laghos_test"
            "$SWEAGENT_ROOT/tools/laghos_harness/bin/laghos_build" || echo "  Warning: Laghos build failed"
        fi

        echo "Laghos_test reset complete!"
    else
        echo "  Warning: Laghos_test directory not found"
    fi
fi

#===============================================================================
# Lulesh
#===============================================================================
if [[ "$RESET_LULESH" == "true" ]]; then
    echo ""
    echo "========================================="
    echo "Resetting Lulesh_test..."
    echo "========================================="

    if [[ -d "$SWEAGENT_ROOT/Lulesh_test" ]]; then
        cd "$SWEAGENT_ROOT/Lulesh_test"

        echo "Reverting any uncommitted changes..."
        git checkout . 2>/dev/null || true

        echo "Removing untracked files..."
        git clean -fd 2>/dev/null || true

        # Lulesh has cuda subdirectory
        if [[ -d "cuda" ]]; then
            cd cuda
            echo "Removing CUDA build artifacts..."
            rm -f lulesh 2>/dev/null || true
            make clean 2>/dev/null || true
        fi

        if [[ "$DO_BUILD" == "true" ]]; then
            echo "Rebuilding Lulesh_test..."
            export LULESH_ROOT="$SWEAGENT_ROOT/Lulesh_test/cuda"
            "$SWEAGENT_ROOT/tools/lulesh_harness/bin/lulesh_build" || echo "  Warning: Lulesh build failed"
        fi

        echo "Lulesh_test reset complete!"
    else
        echo "  Warning: Lulesh_test directory not found"
    fi
fi

echo ""
echo "========================================="
echo "Test repos reset complete!"
echo "========================================="
