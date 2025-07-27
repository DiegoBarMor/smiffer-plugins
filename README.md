# SMIFFer plugins

## Installation
### ChimeraX
```
cd chimerax_volgrid_usage
./install.sh
# ./uninstall.sh
```

### PyMOL
```
cd pymol_volgrid
./install.sh
# ./uninstall.sh
```

### VMD
```
cd vmd_volgrid
./install.sh
# ./uninstall.sh
```


## Usage
...


## TODO
### General
- test if the plugins are really handling correctly cases where the smiffer backend crashes
- document here the plugins setup, installation and usage

### ChimeraX
- fix loading of outputs (and other issues)
- clean the scripts

### PyMOL
- fix loading of outputs
- clean the scripts

### VMD
- `invalid command name "voltool"` when clicking on `Isovalue Controls`
- a "&1" file is being generated at vmd/plugins/noarch/tcl/vmd_smiffer/volgrids-main/run, is it intended?
- clean the scripts
