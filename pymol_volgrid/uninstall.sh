#!/bin/bash

# PyMOL Volgrid Plugin Uninstaller

echo "Uninstalling PyMOL Volgrid Plugin..."

# Find PyMOL startup directory
PYMOL_STARTUP_DIR=""
PLUGIN_DIR=""

# Try to find PyMOL installation path
echo "Searching for PyMOL startup directory..."

# Method 1: Use python to find pymol installation
PYMOL_PATH=$(python -c "import pymol; import os; print(os.path.dirname(pymol.__file__))" 2>/dev/null || echo "")

if [ ! -z "$PYMOL_PATH" ]; then
    # Look for pmg_tk/startup directory
    POSSIBLE_STARTUP_DIRS=(
        "$PYMOL_PATH/../pmg_tk/startup"
        "$PYMOL_PATH/pmg_tk/startup" 
        "$(dirname "$PYMOL_PATH")/pmg_tk/startup"
    )
    
    for dir in "${POSSIBLE_STARTUP_DIRS[@]}"; do
        if [ -d "$dir/pymol_volgrid" ]; then
            PYMOL_STARTUP_DIR="$dir"
            PLUGIN_DIR="$dir/pymol_volgrid"
            break
        fi
    done
fi

# Method 2: Search common conda/system locations if Method 1 failed
if [ -z "$PLUGIN_DIR" ]; then
    SEARCH_PATHS=(
        "/media/*/conda_envs/*/lib/python*/site-packages/pmg_tk/startup/pymol_volgrid"
        "$HOME/anaconda*/lib/python*/site-packages/pmg_tk/startup/pymol_volgrid"
        "$HOME/miniconda*/lib/python*/site-packages/pmg_tk/startup/pymol_volgrid"
        "/opt/conda/lib/python*/site-packages/pmg_tk/startup/pymol_volgrid"
        "/usr/lib/python*/site-packages/pmg_tk/startup/pymol_volgrid"
        "/usr/local/lib/python*/site-packages/pmg_tk/startup/pymol_volgrid"
    )
    
    for pattern in "${SEARCH_PATHS[@]}"; do
        for dir in $pattern; do
            if [ -d "$dir" ]; then
                PLUGIN_DIR="$dir"
                break 2
            fi
        done
    done
fi

# Method 3: Try to find using locate command
if [ -z "$PLUGIN_DIR" ] && command -v locate >/dev/null 2>&1; then
    FOUND_DIR=$(locate pmg_tk/startup/pymol_volgrid 2>/dev/null | head -1)
    if [ -d "$FOUND_DIR" ]; then
        PLUGIN_DIR="$FOUND_DIR"
    fi
fi

# Also check legacy .pymol/plugins location
LEGACY_DIRS=(
    "$HOME/.pymol/plugins"
    "$HOME/.PyMOL/plugins"
)

LEGACY_PLUGIN_DIR=""
for dir in "${LEGACY_DIRS[@]}"; do
    if [ -d "$dir" ] && [ -f "$dir/pymol_smiffer_plugin.py" ]; then
        LEGACY_PLUGIN_DIR="$dir"
        break
    fi
done

if [ -z "$PLUGIN_DIR" ] && [ -z "$LEGACY_PLUGIN_DIR" ]; then
    echo "Plugin installation not found."
    echo "Please manually remove:"
    echo "- pymol_volgrid directory (containing pymol_smiffer_plugin.py, __init__.py, and volgrids-main)"
    echo "from your PyMOL startup directory (pmg_tk/startup/) or plugins directory"
    exit 1
fi

# Remove from startup directory (new location)
if [ ! -z "$PLUGIN_DIR" ]; then
    echo "Removing plugin from: $PLUGIN_DIR"
    rm -rf "$PLUGIN_DIR"
    echo "Removed from startup directory"
fi

# Remove from legacy plugins directory
if [ ! -z "$LEGACY_PLUGIN_DIR" ]; then
    echo "Removing legacy files from: $LEGACY_PLUGIN_DIR"
    rm -f "$LEGACY_PLUGIN_DIR/pymol_smiffer_plugin.py"
    rm -f "$LEGACY_PLUGIN_DIR/smiffer.pym"
    rm -rf "$LEGACY_PLUGIN_DIR/volgrids-main"
    rm -f "$LEGACY_PLUGIN_DIR/__init__.py"
    echo "Removed legacy plugin files"
fi

# Clean local build artifacts
rm -rf build/ dist/ *.egg-info/

echo "Plugin uninstalled successfully!"
echo "Restart PyMOL to complete the removal."