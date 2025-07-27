#!/bin/bash

# PyMOL Volgrid Plugin Installer

set -e

echo "Installing PyMOL Volgrid Plugin..."

# Check if we're in the correct directory
if [ ! -f "pymol_smiffer_plugin.py" ]; then
    echo "Error: Must run from pymol_volgrid directory"
    exit 1
fi

# Find PyMOL startup directory
PYMOL_STARTUP_DIR=""

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
        if [ -d "$dir" ]; then
            PYMOL_STARTUP_DIR="$dir"
            break
        fi
    done
fi

# Method 2: Search common conda/system locations if Method 1 failed
if [ -z "$PYMOL_STARTUP_DIR" ]; then
    SEARCH_PATHS=(
        "/media/*/conda_envs/*/lib/python*/site-packages/pmg_tk/startup"
        "$HOME/anaconda*/lib/python*/site-packages/pmg_tk/startup"
        "$HOME/miniconda*/lib/python*/site-packages/pmg_tk/startup"
        "/opt/conda/lib/python*/site-packages/pmg_tk/startup"
        "/usr/lib/python*/site-packages/pmg_tk/startup"
        "/usr/local/lib/python*/site-packages/pmg_tk/startup"
    )

    for pattern in "${SEARCH_PATHS[@]}"; do
        for dir in $pattern; do
            if [ -d "$dir" ]; then
                PYMOL_STARTUP_DIR="$dir"
                break 2
            fi
        done
    done
fi

# Method 3: Try to find using locate command
if [ -z "$PYMOL_STARTUP_DIR" ] && command -v locate >/dev/null 2>&1; then
    STARTUP_DIR=$(locate pmg_tk/startup 2>/dev/null | head -1)
    if [ -d "$STARTUP_DIR" ]; then
        PYMOL_STARTUP_DIR="$STARTUP_DIR"
    fi
fi

if [ -z "$PYMOL_STARTUP_DIR" ]; then
    echo "Error: Could not find PyMOL startup directory (pmg_tk/startup)"
    echo "Please manually specify the path or ensure PyMOL is properly installed"
    exit 1
fi

# Create plugin directory
PLUGIN_DIR="$PYMOL_STARTUP_DIR/pymol_volgrid"
mkdir -p "$PLUGIN_DIR"

echo "Installing to: $PLUGIN_DIR"

# Copy plugin files
cp pymol_smiffer_plugin.py "$PLUGIN_DIR/"
rm -rf volgrids
git clone https://github.com/DiegoBarMor/volgrids.git
mv volgrids "$PLUGIN_DIR/volgrids-main"
cp __init__.py "$PLUGIN_DIR/"
{ echo "[VOLGRIDS]"; echo "OUTPUT_FORMAT=vg.GridFormat.MRC"; } > "$PLUGIN_DIR/default_config.ini"

echo "Plugin installed successfully!"
echo ""
echo "Plugin installed to: $PLUGIN_DIR"
echo ""
echo "To use the plugin in PyMOL:"
echo "1. Start PyMOL"
echo "2. The plugin should automatically load and appear in the Plugin menu as 'Smiffer Tool'"
echo "3. If it doesn't appear, restart PyMOL"
echo ""
echo "Alternative activation methods:"
echo "- Type 'smiffer_gui' in PyMOL command line"
echo "- Or manually install via Plugin > Plugin Manager and select: $PLUGIN_DIR/pymol_smiffer_plugin.py"
