#!/bin/bash

# ChimeraX SmifferTool Plugin Installer

set -e

echo "Installing ChimeraX SmifferTool Plugin..."

# Check if we're in the correct directory
if [ ! -f "bundle_info.xml" ]; then
    echo "Error: Must run from chimerax_volgrid_usage directory"
    exit 1
fi

# Downloads volgrids-main
echo "Fetching volgrids-main..."
git clone https://github.com/DiegoBarMor/volgrids.git
mv volgrids src/volgrids-main

# Build and install the plugin
echo "Building plugin..."

path_dist=./dist/chimerax_smiffertool-1.0-py3-none-any.whl # hardcoded for now
chimerax --nogui --cmd "devel build .; toolshed install $path_dist; exit"

path_installed=$(chimerax -c "import chimerax.smiffertool as sm; from pathlib import Path; print(Path(sm.__file__).parent)")

echo "Plugin built successfully to $path_installed"

rm -rf build/ dist/ ./*.egg-info/ src/volgrids-main/
