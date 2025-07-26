#!/bin/bash

# ChimeraX SmifferTool Plugin Uninstaller

echo "Uninstalling ChimeraX SmifferTool Plugin..."

chimerax --nogui --cmd "toolshed uninstall SmifferTool; exit"
