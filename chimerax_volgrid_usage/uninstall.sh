#!/bin/bash

# ChimeraX SmifferTool Plugin Uninstaller

echo "Uninstalling ChimeraX SmifferTool Plugin..."

# Clean build artifacts
echo "Cleaning build artifacts..."
rm -rf build/ dist/ *.egg-info/
rm -rf src/*.egg-info/

echo "Build artifacts cleaned."
echo ""
echo "To completely remove from ChimeraX:"
echo "1. Open ChimeraX"
echo "2. Go to Tools > More Tools"
echo "3. Find 'SmifferTool' in the installed tools list"
echo "4. Click 'Uninstall'"
echo ""
echo "Or use the ChimeraX command line:"
echo "toolshed uninstall SmifferTool"
