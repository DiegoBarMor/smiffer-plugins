#!/bin/bash

# ChimeraX SmifferTool Plugin Uninstaller

echo "Uninstalling ChimeraX SmifferTool Plugin..."

# Clean build artifacts
echo "Cleaning build artifacts..."
rm -rf build/ dist/ *.egg-info/
rm -rf src/*.egg-info/

chimerax --nogui --cmd "toolshed uninstall SmifferTool; exit"
