# SMIFFer plugins

## TODO
### General
- document here the plugins setup, installation and usage

### ChimeraX
- clean the scripts
- I had an issue while trying to uninstall and reinstall the plugin for chimerax. After using "toolshed install", I would get the message "No change in list of installed bundles" despite the plugin not being currently installed.
    - Solution: go to location of the installed packages (in my case `~/.local/share/ChimeraX/1.10/lib/python3.11/site-packages`) and remove the `chimerax_smiffertool-1.0.dist-info/` folder. For some reason it sometimes remained there after uninstalling --> why?

### PyMOL
- default output for smiffer execution should be MRC (CMAP isn't supported)
- clean the scripts

### VMD
- default output for smiffer execution should be MRC (CMAP isn't supported)
- a "&1" file is being generated at vmd/plugins/noarch/tcl/vmd_smiffer/volgrids-main/run, is it intended?
- installation script sometimes hangs when checking the APBS installation
- clean the scripts
