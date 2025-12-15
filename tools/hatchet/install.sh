#!/usr/bin/env bash

# Get the bundle directory
bundle_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Add lib directory to PYTHONPATH for importing hatchet_utils
export PYTHONPATH="$bundle_dir/lib":$PYTHONPATH

# Install Hatchet Python library
echo "Installing Hatchet Python library..."
pip install hatchet --quiet || {
    echo "Warning: Failed to install Hatchet via pip"
    echo "Hatchet must be installed manually for hatchet_analyze to work:"
    echo "  pip install hatchet"
}

# Verify installation
if python3 -c "import hatchet" 2>/dev/null; then
    echo "Hatchet installation verified successfully"
else
    echo "Warning: Hatchet not found. Install with: pip install hatchet"
fi
