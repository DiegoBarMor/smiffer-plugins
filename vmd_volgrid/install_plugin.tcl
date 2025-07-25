#!/usr/bin/env tclsh
# VMD Smiffer Plugin Installation Script
# This script installs the Smiffer plugin for VMD

proc install_smiffer_plugin {} {
    set script_dir [file dirname [info script]]
    set plugin_files [list "vmd_smiffer.tcl" "pkgIndex.tcl"]
    
    # Get VMD plugin directory
    set vmd_plugin_dir ""
    
    # Try to find VMD plugin directory
    if {[info exists env(VMDDIR)]} {
        set vmd_plugin_dir [file join $env(VMDDIR) "plugins" "noarch" "tcl" "smiffer1.0"]
    } elseif {[file exists "/usr/local/lib/vmd/plugins/noarch/tcl"]} {
        set vmd_plugin_dir "/usr/local/lib/vmd/plugins/noarch/tcl/smiffer1.0"
    } elseif {[file exists "/opt/vmd/plugins/noarch/tcl"]} {
        set vmd_plugin_dir "/opt/vmd/plugins/noarch/tcl/smiffer1.0"
    } else {
        puts "VMD plugin directory not found. Please set VMDDIR environment variable or install manually."
        puts "Copy the following files to your VMD plugin directory:"
        foreach file $plugin_files {
            puts "  - $file"
        }
        return
    }
    
    # Create plugin directory if it doesn't exist
    if {![file exists $vmd_plugin_dir]} {
        if {[catch {file mkdir $vmd_plugin_dir} error]} {
            puts "Error creating plugin directory: $error"
            puts "Please create the directory manually: $vmd_plugin_dir"
            return
        }
    }
    
    # Copy plugin files
    foreach file $plugin_files {
        set src [file join $script_dir $file]
        set dst [file join $vmd_plugin_dir $file]
        
        if {[file exists $src]} {
            if {[catch {file copy -force $src $dst} error]} {
                puts "Error copying $file: $error"
                return
            }
            puts "Copied $file to $vmd_plugin_dir"
        } else {
            puts "Warning: $file not found in current directory"
        }
    }
    
    puts "Smiffer plugin installed successfully!"
    puts "Restart VMD and use 'vmd_smiffer_tk' command or Extensions->Smiffer Tool to open the GUI"
}

proc manual_install_instructions {} {
    puts "Manual Installation Instructions:"
    puts "================================"
    puts "1. Copy vmd_smiffer.tcl and pkgIndex.tcl to your VMD plugin directory"
    puts "2. The plugin directory is typically located at:"
    puts "   - Linux: \$VMDDIR/plugins/noarch/tcl/smiffer1.0/"
    puts "   - macOS: /Applications/VMD.app/Contents/vmd/plugins/noarch/tcl/smiffer1.0/"
    puts "   - Windows: C:\\Program Files\\VMD\\plugins\\noarch\\tcl\\smiffer1.0\\"
    puts "3. Create the smiffer1.0 directory if it doesn't exist"
    puts "4. Restart VMD"
    puts "5. Use 'vmd_smiffer_tk' command to open the GUI"
}

if {[info exists argv0] && [file tail $argv0] eq "install_plugin.tcl"} {
    if {[llength $argv] > 0 && [lindex $argv 0] eq "manual"} {
        manual_install_instructions
    } else {
        install_smiffer_plugin
    }
}