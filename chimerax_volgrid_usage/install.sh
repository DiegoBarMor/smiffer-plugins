#!/bin/bash

# ChimeraX Volgrid Usage Plugin Installer

set -e

echo "Installing ChimeraX Volgrid Usage Plugin..."

# Check if we're in the correct directory
if [ ! -f "bundle_info.xml" ]; then
    echo "Error: Must run from chimerax_volgrid_usage directory"
    exit 1
fi

# Ensure volgrids-main is present
if [ ! -d "volgrids-main" ]; then
    echo "Error: volgrids-main directory not found. This directory is required for the plugin to work."
    exit 1
fi

# Copy volgrids-main into src directory if not already there
if [ ! -d "src/volgrids-main" ]; then
    echo "Copying volgrids-main to src directory..."
    cp -r volgrids-main src/
fi

# Build and install the plugin
echo "Building plugin..."

path_dist=./dist/chimerax_smiffertool-1.0-py3-none-any.whl # hardcoded for now
chimerax --nogui --cmd "devel build .; toolshed install $path_dist; exit"

path_installed=$(chimerax -c "import chimerax.smiffertool as sm; from pathlib import Path; print(Path(sm.__file__).parent)")

echo "Plugin built successfully to $path_installed"
