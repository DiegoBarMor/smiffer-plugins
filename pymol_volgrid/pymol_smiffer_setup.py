"""
Setup script for PyMOL Smiffer Plugin
"""

import os
import sys
import shutil
from pathlib import Path

def install_plugin():
    """Install the PyMOL Smiffer plugin"""
    
    # Get PyMOL plugin directory
    try:
        import pymol
        pymol_dir = Path(pymol.__file__).parent
        plugin_dir = pymol_dir / "pymol_path" / "plugins"
        
        # Alternative locations
        if not plugin_dir.exists():
            plugin_dir = Path.home() / ".pymol" / "plugins"
        
        # Create directory if it doesn't exist
        plugin_dir.mkdir(parents=True, exist_ok=True)
        
    except ImportError:
        print("PyMOL not found. Please install PyMOL first.")
        return False
    
    # Copy plugin file
    plugin_source = Path(__file__).parent / "pymol_smiffer_plugin.py"
    plugin_dest = plugin_dir / "pymol_smiffer_plugin.py"
    
    if not plugin_source.exists():
        print(f"Plugin source file not found: {plugin_source}")
        return False
    
    try:
        shutil.copy2(plugin_source, plugin_dest)
        print(f"Plugin installed to: {plugin_dest}")
        
        # Copy volgrids directory if it exists
        volgrids_source = Path(__file__).parent / "volgrids-main"
        if volgrids_source.exists():
            volgrids_dest = plugin_dir / "volgrids-main"
            if volgrids_dest.exists():
                shutil.rmtree(volgrids_dest)
            shutil.copytree(volgrids_source, volgrids_dest)
            print(f"Volgrids copied to: {volgrids_dest}")
        
        print("\nInstallation complete!")
        print("To use the plugin in PyMOL:")
        print("1. Start PyMOL")
        print("2. Go to Plugin menu > Smiffer Tool")
        print("3. Or type 'smiffer_gui' in the PyMOL command line")
        
        return True
        
    except Exception as e:
        print(f"Error installing plugin: {e}")
        return False

def create_pymol_init_file():
    """Create a PyMOL initialization file to auto-load the plugin"""
    
    pymol_config_dir = Path.home() / ".pymol"
    pymol_config_dir.mkdir(exist_ok=True)
    
    init_file = pymol_config_dir / "pymolrc.py"
    
    init_content = """
# PyMOL initialization file
# Auto-load Smiffer plugin

try:
    from pymol.plugins import addmenuitemqt
    import pymol_smiffer_plugin
    print("Smiffer plugin loaded successfully")
except ImportError as e:
    print(f"Failed to load Smiffer plugin: {e}")
"""
    
    try:
        with open(init_file, 'w') as f:
            f.write(init_content)
        print(f"Created PyMOL init file: {init_file}")
        return True
    except Exception as e:
        print(f"Error creating init file: {e}")
        return False

if __name__ == "__main__":
    print("PyMOL Smiffer Plugin Setup")
    print("=" * 40)
    
    success = install_plugin()
    
    if success:
        create_init = input("\nCreate PyMOL initialization file to auto-load plugin? (y/n): ")
        if create_init.lower() in ['y', 'yes']:
            create_pymol_init_file()
    
    print("\nSetup complete!")