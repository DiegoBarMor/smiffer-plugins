import os
import sys
import subprocess
import importlib.metadata
import platform


def __init_plugin__(app):
    """Initialize the PyMOL Volgrid plugin"""
    # Check and install dependencies
    install_dir = os.path.dirname(__file__)
    check_packages(install_dir)
    
    # Register the plugin in PyMOL menu
    from pymol.plugins import addmenuitemqt
    addmenuitemqt('Smiffer Tool', run_plugin_gui)


def install_package(package, main_folder_path):
    """Install a Python package if not already installed"""
    try:
        package_name = package.split('=')[0].split('<')[0].split('>')[0]
        __import__(package_name)
        print(f"{package_name} is already installed")
    except ImportError as e:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable.replace('pythonw', 'python'), "-m", "pip", "install", package])
            print(f"Successfully installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {package}: {e}")
            if package_name in ['MDAnalysis', 'h5py']:
                print(f"Warning: {package_name} is required for some functionality. Please install manually.")


def check_packages(install_dir):
    """Check and install required Python packages"""
    print('Checking python modules for PyMOL Volgrid plugin')
    packages = [
        'MDAnalysis', 
        'h5py', 
        'numpy', 
        'scipy', 
        'matplotlib'
    ]
    
    for package in packages:
        install_package(package, install_dir)
    
    print('Package check completed')


def run_plugin_gui():
    """Launch the Smiffer GUI"""
    try:
        # Import and run the plugin
        from . import pymol_smiffer_plugin
        
        # Initialize plugin instance if not already done
        if not hasattr(pymol_smiffer_plugin, 'plugin_instance') or pymol_smiffer_plugin.plugin_instance is None:
            pymol_smiffer_plugin.plugin_instance = pymol_smiffer_plugin.SmifferPyMOLPlugin()
        
        # Show the GUI
        pymol_smiffer_plugin.plugin_instance.show_gui()
        
    except Exception as e:
        print(f"Error launching Smiffer Tool: {e}")
        import traceback
        traceback.print_exc()