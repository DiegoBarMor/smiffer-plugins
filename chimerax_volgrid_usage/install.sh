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
python setup.py bdist_wheel

echo "Plugin built successfully!"
echo "To install the plugin, use the following command in the ChimeraX command line:"
echo
echo "cd $(pwd)/dist; toolshed install $(ls dist)"
echo
