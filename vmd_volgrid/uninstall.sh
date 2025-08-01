#!/bin/bash
# VMD Volgrid Plugin Uninstallation Script for Linux/macOS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_NAME="smiffer1.0"

echo "VMD Volgrid Plugin Uninstaller"
echo "==============================="

# Function to find VMD plugin directory (same as install.sh)
find_vmd_plugin_dir() {
    local vmd_plugin_dir=""
    
    # Try different common locations
    if [[ -n "$VMDDIR" ]]; then
        vmd_plugin_dir="$VMDDIR/plugins/noarch/tcl"
    elif [[ -d "/usr/local/lib/vmd/plugins/noarch/tcl" ]]; then
        vmd_plugin_dir="/usr/local/lib/vmd/plugins/noarch/tcl"
    elif [[ -d "/opt/vmd/plugins/noarch/tcl" ]]; then
        vmd_plugin_dir="/opt/vmd/plugins/noarch/tcl"
    elif [[ -d "/Applications/VMD.app/Contents/vmd/plugins/noarch/tcl" ]]; then
        vmd_plugin_dir="/Applications/VMD.app/Contents/vmd/plugins/noarch/tcl"
    else
        # Check user plugins directory
        local user_vmd_plugins="$HOME/.vmd/plugins"
        if [[ -d "$user_vmd_plugins" ]]; then
            vmd_plugin_dir="$user_vmd_plugins"
        fi
    fi
    
    echo "$vmd_plugin_dir"
}

# Function to remove plugin files
remove_plugin() {
    local vmd_plugin_dir="$1"
    local plugin_dir="$vmd_plugin_dir/vmd_smiffer"
    
    if [[ -d "$plugin_dir" ]]; then
        echo "Removing plugin directory: $plugin_dir"
        rm -rf "$plugin_dir"
        echo "Plugin files removed successfully"
    else
        echo "Plugin directory not found: $plugin_dir"
        echo "Plugin may not be installed or already removed"
    fi
}

# Function to clean up VMD startup script
clean_vmdrc() {
    local vmd_rc="$HOME/.vmdrc"
    
    if [[ ! -f "$vmd_rc" ]]; then
        echo "No ~/.vmdrc file found - nothing to clean"
        return 0
    fi
    
    echo "Cleaning up VMD startup script: $vmd_rc"
    
    # Create a backup
    cp "$vmd_rc" "$vmd_rc.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Created backup: $vmd_rc.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Create temporary file for cleaned content
    local temp_file
    temp_file=$(mktemp)
    
    # Remove vmd_smiffer related lines
    grep -v "vmd_smiffer\|VMD Smiffer plugin" "$vmd_rc" > "$temp_file" || true
    
    # Check if the file was created by our installer (has auto-generated comment)
    if grep -q "Auto-generated by vmd_smiffer plugin installer" "$vmd_rc"; then
        echo "This .vmdrc was created by the installer - offering to remove it completely"
        read -p "Remove the entire .vmdrc file? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm "$vmd_rc"
            echo "Removed .vmdrc file completely"
        else
            # Keep the cleaned version
            mv "$temp_file" "$vmd_rc"
            echo "Removed vmd_smiffer entries from .vmdrc"
        fi
    else
        # Just remove vmd_smiffer lines from existing file
        mv "$temp_file" "$vmd_rc"
        echo "Removed vmd_smiffer entries from existing .vmdrc"
        
        # If the file is now empty or only has comments/whitespace, ask if user wants to remove it
        if ! grep -q "^[^#]" "$vmd_rc" 2>/dev/null || [[ ! -s "$vmd_rc" ]]; then
            read -p ".vmdrc appears to be empty now. Remove it? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm "$vmd_rc"
                echo "Removed empty .vmdrc file"
            fi
        fi
    fi
    
    # Clean up temp file if it still exists
    [[ -f "$temp_file" ]] && rm "$temp_file"
}

# Function to remove src/volgrids-main if it was copied by installer
remove_src_volgrids() {
    local src_volgrids="$SCRIPT_DIR/src/volgrids-main"
    
    if [[ -d "$src_volgrids" ]]; then
        echo "Found volgrids-main in src directory"
        
        # Check if the main volgrids-main exists and is identical
        if [[ -d "$SCRIPT_DIR/volgrids-main" ]]; then
            # Compare the directories
            if diff -r "$SCRIPT_DIR/volgrids-main" "$src_volgrids" &>/dev/null; then
                echo "Removing duplicate volgrids-main from src directory"
                rm -rf "$src_volgrids"
                echo "Removed src/volgrids-main (duplicate of main volgrids-main)"
            else
                echo "Warning: src/volgrids-main differs from main volgrids-main"
                echo "Keeping src/volgrids-main to avoid data loss"
            fi
        else
            read -p "Remove src/volgrids-main directory? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf "$src_volgrids"
                echo "Removed src/volgrids-main"
            else
                echo "Kept src/volgrids-main"
            fi
        fi
    fi
}

# Function to show what will be uninstalled
show_uninstall_preview() {
    echo "Uninstall Preview:"
    echo "=================="
    
    local vmd_plugin_dir
    vmd_plugin_dir=$(find_vmd_plugin_dir)
    local plugin_dir="$vmd_plugin_dir/vmd_smiffer"
    
    echo "Will attempt to remove:"
    echo "- Plugin directory: $plugin_dir"
    echo "- VMD startup script entries in: $HOME/.vmdrc"
    echo "- src/volgrids-main (if it's a copy)"
    echo ""
    
    if [[ -d "$plugin_dir" ]]; then
        echo "Plugin files found:"
        ls -la "$plugin_dir" 2>/dev/null || echo "  (cannot list contents)"
    else
        echo "Plugin directory not found - may already be uninstalled"
    fi
    
    if [[ -f "$HOME/.vmdrc" ]]; then
        echo ""
        echo "VMD startup script entries to be removed:"
        grep -n "vmd_smiffer\|VMD Smiffer plugin" "$HOME/.vmdrc" || echo "  (no vmd_smiffer entries found)"
    else
        echo ""
        echo "No ~/.vmdrc file found"
    fi
}

# Function to verify uninstallation
verify_uninstall() {
    echo ""
    echo "Verifying uninstallation..."
    
    local vmd_plugin_dir
    vmd_plugin_dir=$(find_vmd_plugin_dir)
    local plugin_dir="$vmd_plugin_dir/vmd_smiffer"
    
    local success=true
    
    # Check if plugin directory is removed
    if [[ -d "$plugin_dir" ]]; then
        echo "❌ Plugin directory still exists: $plugin_dir"
        success=false
    else
        echo "✅ Plugin directory removed"
    fi
    
    # Check if vmdrc is clean
    if [[ -f "$HOME/.vmdrc" ]]; then
        if grep -q "vmd_smiffer" "$HOME/.vmdrc"; then
            echo "❌ VMD startup script still contains vmd_smiffer references"
            success=false
        else
            echo "✅ VMD startup script cleaned"
        fi
    else
        echo "✅ No VMD startup script present"
    fi
    
    if [[ "$success" == true ]]; then
        echo ""
        echo "🎉 Uninstallation completed successfully!"
        echo "The VMD Smiffer plugin has been completely removed."
        echo "You may need to restart VMD for changes to take effect."
    else
        echo ""
        echo "⚠️  Uninstallation completed with warnings."
        echo "Some components may need manual removal."
    fi
}

# Main uninstallation logic
main() {
    case "${1:-uninstall}" in
        "uninstall")
            show_uninstall_preview
            echo ""
            read -p "Proceed with uninstallation? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                vmd_plugin_dir=$(find_vmd_plugin_dir)
                if [[ -z "$vmd_plugin_dir" ]]; then
                    echo "Error: Could not determine VMD plugin directory"
                    exit 1
                fi
                
                remove_plugin "$vmd_plugin_dir"
                clean_vmdrc
                remove_src_volgrids
                verify_uninstall
            else
                echo "Uninstallation cancelled"
            fi
            ;;
        "preview"|"dry-run")
            show_uninstall_preview
            ;;
        "force")
            echo "Force uninstalling without confirmation..."
            vmd_plugin_dir=$(find_vmd_plugin_dir)
            if [[ -z "$vmd_plugin_dir" ]]; then
                echo "Error: Could not determine VMD plugin directory"
                exit 1
            fi
            
            remove_plugin "$vmd_plugin_dir"
            clean_vmdrc
            remove_src_volgrids
            verify_uninstall
            ;;
        "help"|"-h"|"--help")
            echo "VMD Volgrid Plugin Uninstaller"
            echo ""
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  uninstall  - Interactive uninstallation (default)"
            echo "  preview    - Show what would be removed without doing it"
            echo "  dry-run    - Same as preview"
            echo "  force      - Uninstall without confirmation prompts"
            echo "  help       - Show this help message"
            echo ""
            echo "The uninstaller will:"
            echo "  - Remove the vmd_smiffer plugin directory"
            echo "  - Clean VMD startup script (~/.vmdrc)"
            echo "  - Remove src/volgrids-main if it's a copy"
            echo "  - Create backups of modified files"
            ;;
        *)
            echo "Unknown command: $1"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Check if we're in the right directory (helpful but not required)
if [[ -f "vmd_smiffer.tcl" ]]; then
    echo "Running from vmd_volgrid directory ✓"
else
    echo "Note: Not running from vmd_volgrid directory, but uninstall should work anyway"
fi

echo ""
main "$@"