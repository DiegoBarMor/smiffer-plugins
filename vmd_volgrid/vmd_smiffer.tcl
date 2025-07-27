#!/usr/bin/env tclsh
# VMD Smiffer Plugin
# Author: Converted from ChimeraX plugin
# Version: 1.0
# Description: VMD plugin for running Smiffer calculations with GUI interface

package provide vmd_smiffer 1.0

# Global variables for plugin state
namespace eval ::smiffer:: {
    # Plugin state variables
    variable w
    variable smiffer_path ""
    variable current_process ""
    variable log_text ""

    # Configuration variables
    variable input_file ""
    variable output_dir ""
    variable trajectory_file ""
    variable apbs_file ""
    variable chem_table ""
    variable config_file ""
    variable mode "prot"
    variable run_apbs 1
    variable pocket_sphere 0
    variable sphere_radius 10.0
    variable sphere_x 0.0
    variable sphere_y 0.0
    variable sphere_z 0.0

    # Process management
    variable process_pid ""
    variable process_running 0

    # Auto-load results setting
    variable auto_load_results 0

    # File tracking for results comparison
    variable pre_calc_files [list]

    # Isovalue control window
    variable isovalue_window ""
    variable loaded_volumes [list]
    variable volume_isovalues
    array set volume_isovalues {}

    # Initialize smiffer path
    set script_dir [file dirname [info script]]
    set smiffer_path [file join $script_dir "volgrids-main" "run" "smiffer.py"]
}

# Check if required packages are available
proc ::smiffer::check_packages {} {
    set missing_packages {}

    # Check for ttk (should be available in modern Tk)
    if {[catch {package require Tk}]} {
        lappend missing_packages "Tk"
    }

    # Try to load ttk if available
    if {[catch {package require ttk}]} {
        # ttk not available as separate package, might be built into Tk 8.5+
        if {![info exists ::ttk::style] && ![namespace exists ::ttk]} {
            # Create fallback namespace if ttk is not available
            namespace eval ::ttk {}
            # Define fallback procedures for ttk widgets - use global namespace to avoid recursion
            proc ::ttk::notebook {args} { return [eval ::notebook $args] }
            proc ::ttk::frame {args} { return [eval ::frame $args] }
            proc ::ttk::label {args} { return [eval ::label $args] }
            proc ::ttk::entry {args} { return [eval ::entry $args] }
            proc ::ttk::button {args} { return [eval ::button $args] }
            proc ::ttk::checkbutton {args} { return [eval ::checkbutton $args] }
            proc ::ttk::combobox {args} { return [eval ::entry $args] }
            proc ::ttk::labelframe {args} { return [eval ::labelframe $args] }
            proc ::ttk::progressbar {args} { return [eval ::frame $args] }
            proc ::ttk::scrollbar {args} { return [eval ::scrollbar $args] }
        }
    }

    return $missing_packages
}

# Main function to create and show the GUI
proc ::smiffer::show_gui {} {
    variable w

    # Check if Tk is available
    if {[catch {package present Tk}]} {
        puts "Error: Tk package not available. Cannot create GUI."
        return
    }

    # Check required packages
    set missing [check_packages]
    if {[llength $missing] > 0} {
        puts "Warning: Missing packages: $missing"
        puts "Some GUI elements may not display correctly"
    }

    # Destroy existing window if it exists
    if {[winfo exists .smiffer]} {
        destroy .smiffer
    }

    # Create main window with error handling
    if {[catch {
        set w [toplevel .smiffer]
        wm title $w "VMD Smiffer Tool"
        wm geometry $w 800x900
        wm resizable $w 1 1

        # Create main frame with notebook for tabs
        create_main_interface $w

        # Create control buttons frame
        frame $w.controls
        pack $w.controls -fill x -padx 10 -pady 5

        # Create control buttons
        create_control_buttons $w.controls

        # Create progress bar (with fallback)
        create_progress_bar $w

        # Create log area
        create_log_area $w

        # Initialize values
        initialize_values

        puts "VMD Smiffer GUI loaded successfully"

    } error]} {
        puts "Error creating GUI: $error"
        if {[info exists w] && [winfo exists $w]} {
            destroy $w
        }
        catch {tk_messageBox -title "Error" -message "Failed to create GUI: $error" -type ok}
        return
    }
}

# Create main interface with tabs
proc ::smiffer::create_main_interface {w} {
    # Try to create notebook widget, fall back to frame if not available
    if {[catch {
        ttk::notebook $w.nb
        pack $w.nb -fill both -expand true -padx 10 -pady 10

        # Create basic settings tab
        create_basic_tab $w.nb

        # Create advanced settings tab
        create_advanced_tab $w.nb

    } error]} {
        puts "Notebook widget not available, using simple frame layout"

        # Create a simple frame-based layout instead
        frame $w.main
        pack $w.main -fill both -expand true -padx 10 -pady 10

        # Create basic settings in main frame
        create_basic_settings_simple $w.main

        # Create advanced settings in main frame
        create_advanced_settings_simple $w.main
    }
}

# Create progress bar with fallback
proc ::smiffer::create_progress_bar {w} {
    if {[catch {
        ttk::progressbar $w.progress -mode indeterminate
        pack $w.progress -fill x -padx 10 -pady 2
    } error]} {
        # Fallback to simple frame
        frame $w.progress -height 10 -bg gray
        pack $w.progress -fill x -padx 10 -pady 2
    }
}

# Create basic settings tab
proc ::smiffer::create_basic_tab {parent} {
    variable mode
    variable input_file
    variable output_dir

    # Create basic tab frame
    set basic_frame [ttk::frame $parent.basic]
    $parent add $basic_frame -text "Basic Settings"

    # Input structure section
    ttk::labelframe $basic_frame.input -text "Input Structure" -padding 10
    pack $basic_frame.input -fill x -pady 5

    # Structure file selection
    ttk::label $basic_frame.input.struct_lbl -text "Structure File:"
    ttk::entry $basic_frame.input.struct_entry -textvariable ::smiffer::input_file -width 50
    ttk::button $basic_frame.input.struct_browse -text "Browse" -command ::smiffer::browse_input_file
    ttk::button $basic_frame.input.struct_current -text "Load Current Structure" -command ::smiffer::load_current_structure

    grid $basic_frame.input.struct_lbl -row 0 -column 0 -sticky w -padx 5
    grid $basic_frame.input.struct_entry -row 0 -column 1 -sticky ew -padx 5
    grid $basic_frame.input.struct_browse -row 0 -column 2 -padx 5
    grid $basic_frame.input.struct_current -row 0 -column 3 -padx 5

    # Mode selection
    ttk::label $basic_frame.input.mode_lbl -text "Mode:"
    ttk::combobox $basic_frame.input.mode_combo -textvariable ::smiffer::mode -values {"prot" "rna"} -state readonly

    grid $basic_frame.input.mode_lbl -row 1 -column 0 -sticky w -padx 5 -pady 5
    grid $basic_frame.input.mode_combo -row 1 -column 1 -sticky w -padx 5 -pady 5

    # Output directory selection
    ttk::label $basic_frame.input.output_lbl -text "Output Directory:"
    ttk::entry $basic_frame.input.output_entry -textvariable ::smiffer::output_dir -width 50
    ttk::button $basic_frame.input.output_browse -text "Browse" -command ::smiffer::browse_output_dir

    grid $basic_frame.input.output_lbl -row 2 -column 0 -sticky w -padx 5 -pady 5
    grid $basic_frame.input.output_entry -row 2 -column 1 -sticky ew -padx 5 -pady 5
    grid $basic_frame.input.output_browse -row 2 -column 2 -padx 5 -pady 5

    # Configure grid weights
    grid columnconfigure $basic_frame.input 1 -weight 1
}

# Create advanced settings tab
proc ::smiffer::create_advanced_tab {parent} {
    variable trajectory_file
    variable apbs_file
    variable run_apbs
    variable pocket_sphere
    variable sphere_radius
    variable sphere_x
    variable sphere_y
    variable sphere_z
    variable chem_table
    variable config_file

    # Create advanced tab frame
    set advanced_frame [ttk::frame $parent.advanced]
    $parent add $advanced_frame -text "Advanced Settings"

    # Create scrollable frame for advanced options
    canvas $advanced_frame.canvas -yscrollcommand "$advanced_frame.scroll set"
    ttk::scrollbar $advanced_frame.scroll -orient vertical -command "$advanced_frame.canvas yview"
    frame $advanced_frame.scrollframe

    pack $advanced_frame.scroll -side right -fill y
    pack $advanced_frame.canvas -side left -fill both -expand true

    $advanced_frame.canvas create window 0 0 -anchor nw -window $advanced_frame.scrollframe

    # Trajectory options
    ttk::labelframe $advanced_frame.scrollframe.traj -text "Trajectory Options" -padding 10
    pack $advanced_frame.scrollframe.traj -fill x -pady 5

    ttk::label $advanced_frame.scrollframe.traj.traj_lbl -text "Trajectory File:"
    ttk::entry $advanced_frame.scrollframe.traj.traj_entry -textvariable ::smiffer::trajectory_file -width 40
    ttk::button $advanced_frame.scrollframe.traj.traj_browse -text "Browse" -command ::smiffer::browse_trajectory

    grid $advanced_frame.scrollframe.traj.traj_lbl -row 0 -column 0 -sticky w -padx 5
    grid $advanced_frame.scrollframe.traj.traj_entry -row 0 -column 1 -sticky ew -padx 5
    grid $advanced_frame.scrollframe.traj.traj_browse -row 0 -column 2 -padx 5

    # APBS options
    ttk::labelframe $advanced_frame.scrollframe.apbs -text "APBS Options" -padding 10
    pack $advanced_frame.scrollframe.apbs -fill x -pady 5

    ttk::label $advanced_frame.scrollframe.apbs.apbs_lbl -text "APBS File (.dx):"
    ttk::entry $advanced_frame.scrollframe.apbs.apbs_entry -textvariable ::smiffer::apbs_file -width 40
    ttk::button $advanced_frame.scrollframe.apbs.apbs_browse -text "Browse" -command ::smiffer::browse_apbs_file

    grid $advanced_frame.scrollframe.apbs.apbs_lbl -row 0 -column 0 -sticky w -padx 5
    grid $advanced_frame.scrollframe.apbs.apbs_entry -row 0 -column 1 -sticky ew -padx 5
    grid $advanced_frame.scrollframe.apbs.apbs_browse -row 0 -column 2 -padx 5

    ttk::checkbutton $advanced_frame.scrollframe.apbs.auto_apbs -text "Run APBS automatically" -variable ::smiffer::run_apbs
    grid $advanced_frame.scrollframe.apbs.auto_apbs -row 1 -column 0 -columnspan 3 -sticky w -padx 5 -pady 5

    # Pocket sphere options
    ttk::labelframe $advanced_frame.scrollframe.pocket -text "Pocket Sphere Mode" -padding 10
    pack $advanced_frame.scrollframe.pocket -fill x -pady 5

    ttk::checkbutton $advanced_frame.scrollframe.pocket.enable -text "Enable Pocket Sphere Mode" -variable ::smiffer::pocket_sphere -command ::smiffer::toggle_pocket_sphere
    grid $advanced_frame.scrollframe.pocket.enable -row 0 -column 0 -columnspan 4 -sticky w -padx 5

    ttk::label $advanced_frame.scrollframe.pocket.radius_lbl -text "Radius (Å):"
    spinbox $advanced_frame.scrollframe.pocket.radius_spin -from 0.1 -to 100.0 -increment 0.1 -textvariable ::smiffer::sphere_radius -width 10

    grid $advanced_frame.scrollframe.pocket.radius_lbl -row 1 -column 0 -sticky w -padx 5 -pady 5
    grid $advanced_frame.scrollframe.pocket.radius_spin -row 1 -column 1 -sticky w -padx 5 -pady 5

    ttk::label $advanced_frame.scrollframe.pocket.x_lbl -text "X:"
    spinbox $advanced_frame.scrollframe.pocket.x_spin -from -999.0 -to 999.0 -increment 0.1 -textvariable ::smiffer::sphere_x -width 10
    ttk::label $advanced_frame.scrollframe.pocket.y_lbl -text "Y:"
    spinbox $advanced_frame.scrollframe.pocket.y_spin -from -999.0 -to 999.0 -increment 0.1 -textvariable ::smiffer::sphere_y -width 10
    ttk::label $advanced_frame.scrollframe.pocket.z_lbl -text "Z:"
    spinbox $advanced_frame.scrollframe.pocket.z_spin -from -999.0 -to 999.0 -increment 0.1 -textvariable ::smiffer::sphere_z -width 10

    grid $advanced_frame.scrollframe.pocket.x_lbl -row 2 -column 0 -sticky w -padx 5
    grid $advanced_frame.scrollframe.pocket.x_spin -row 2 -column 1 -sticky w -padx 5
    grid $advanced_frame.scrollframe.pocket.y_lbl -row 2 -column 2 -sticky w -padx 5
    grid $advanced_frame.scrollframe.pocket.y_spin -row 2 -column 3 -sticky w -padx 5
    grid $advanced_frame.scrollframe.pocket.z_lbl -row 3 -column 0 -sticky w -padx 5
    grid $advanced_frame.scrollframe.pocket.z_spin -row 3 -column 1 -sticky w -padx 5

    # Chemical table options
    ttk::labelframe $advanced_frame.scrollframe.chem -text "Chemical Table" -padding 10
    pack $advanced_frame.scrollframe.chem -fill x -pady 5

    ttk::label $advanced_frame.scrollframe.chem.chem_lbl -text "Table File (.chem):"
    ttk::entry $advanced_frame.scrollframe.chem.chem_entry -textvariable ::smiffer::chem_table -width 40
    ttk::button $advanced_frame.scrollframe.chem.chem_browse -text "Browse" -command ::smiffer::browse_chem_table

    grid $advanced_frame.scrollframe.chem.chem_lbl -row 0 -column 0 -sticky w -padx 5
    grid $advanced_frame.scrollframe.chem.chem_entry -row 0 -column 1 -sticky ew -padx 5
    grid $advanced_frame.scrollframe.chem.chem_browse -row 0 -column 2 -padx 5

    # Configuration options
    ttk::labelframe $advanced_frame.scrollframe.config -text "Configuration" -padding 10
    pack $advanced_frame.scrollframe.config -fill x -pady 5

    ttk::label $advanced_frame.scrollframe.config.config_lbl -text "Config File (.ini):"
    ttk::entry $advanced_frame.scrollframe.config.config_entry -textvariable ::smiffer::config_file -width 40
    ttk::button $advanced_frame.scrollframe.config.config_browse -text "Browse" -command ::smiffer::browse_config_file

    grid $advanced_frame.scrollframe.config.config_lbl -row 0 -column 0 -sticky w -padx 5
    grid $advanced_frame.scrollframe.config.config_entry -row 0 -column 1 -sticky ew -padx 5
    grid $advanced_frame.scrollframe.config.config_browse -row 0 -column 2 -padx 5

    # Configure grid weights
    grid columnconfigure $advanced_frame.scrollframe.traj 1 -weight 1
    grid columnconfigure $advanced_frame.scrollframe.apbs 1 -weight 1
    grid columnconfigure $advanced_frame.scrollframe.chem 1 -weight 1
    grid columnconfigure $advanced_frame.scrollframe.config 1 -weight 1

    # Configure scrollable area
    bind $advanced_frame.scrollframe <Configure> "::smiffer::configure_scroll $advanced_frame.canvas $advanced_frame.scrollframe"

    # Initially disable pocket sphere controls
    toggle_pocket_sphere
}

# Create simplified basic settings (fallback for older Tk)
proc ::smiffer::create_basic_settings_simple {parent} {
    variable mode
    variable input_file
    variable output_dir

    # Input structure section
    labelframe $parent.input -text "Input Structure" -padx 10 -pady 10
    pack $parent.input -fill x -pady 5

    # Structure file selection
    label $parent.input.struct_lbl -text "Structure File:"
    entry $parent.input.struct_entry -textvariable ::smiffer::input_file -width 50
    button $parent.input.struct_browse -text "Browse" -command ::smiffer::browse_input_file
    button $parent.input.struct_current -text "Load Current" -command ::smiffer::load_current_structure

    grid $parent.input.struct_lbl -row 0 -column 0 -sticky w -padx 5
    grid $parent.input.struct_entry -row 0 -column 1 -sticky ew -padx 5
    grid $parent.input.struct_browse -row 0 -column 2 -padx 5
    grid $parent.input.struct_current -row 0 -column 3 -padx 5

    # Mode selection
    label $parent.input.mode_lbl -text "Mode:"
    frame $parent.input.mode_frame
    radiobutton $parent.input.mode_frame.prot -text "Protein" -variable ::smiffer::mode -value "prot"
    radiobutton $parent.input.mode_frame.rna -text "RNA" -variable ::smiffer::mode -value "rna"
    pack $parent.input.mode_frame.prot $parent.input.mode_frame.rna -side left

    grid $parent.input.mode_lbl -row 1 -column 0 -sticky w -padx 5 -pady 5
    grid $parent.input.mode_frame -row 1 -column 1 -sticky w -padx 5 -pady 5

    # Output directory selection
    label $parent.input.output_lbl -text "Output Directory:"
    entry $parent.input.output_entry -textvariable ::smiffer::output_dir -width 50
    button $parent.input.output_browse -text "Browse" -command ::smiffer::browse_output_dir

    grid $parent.input.output_lbl -row 2 -column 0 -sticky w -padx 5 -pady 5
    grid $parent.input.output_entry -row 2 -column 1 -sticky ew -padx 5 -pady 5
    grid $parent.input.output_browse -row 2 -column 2 -padx 5 -pady 5

    # Configure grid weights
    grid columnconfigure $parent.input 1 -weight 1
}

# Create simplified advanced settings (fallback for older Tk)
proc ::smiffer::create_advanced_settings_simple {parent} {
    variable trajectory_file
    variable apbs_file
    variable run_apbs
    variable pocket_sphere
    variable sphere_radius
    variable sphere_x
    variable sphere_y
    variable sphere_z
    variable chem_table
    variable config_file

    # Advanced options frame
    labelframe $parent.advanced -text "Advanced Options" -padx 10 -pady 10
    pack $parent.advanced -fill x -pady 5

    # Trajectory file
    label $parent.advanced.traj_lbl -text "Trajectory File:"
    entry $parent.advanced.traj_entry -textvariable ::smiffer::trajectory_file -width 40
    button $parent.advanced.traj_browse -text "Browse" -command ::smiffer::browse_trajectory

    grid $parent.advanced.traj_lbl -row 0 -column 0 -sticky w -padx 5 -pady 2
    grid $parent.advanced.traj_entry -row 0 -column 1 -sticky ew -padx 5 -pady 2
    grid $parent.advanced.traj_browse -row 0 -column 2 -padx 5 -pady 2

    # APBS options
    checkbutton $parent.advanced.auto_apbs -text "Run APBS automatically" -variable ::smiffer::run_apbs
    grid $parent.advanced.auto_apbs -row 1 -column 0 -columnspan 3 -sticky w -padx 5 -pady 2

    label $parent.advanced.apbs_lbl -text "APBS File (.dx):"
    entry $parent.advanced.apbs_entry -textvariable ::smiffer::apbs_file -width 40
    button $parent.advanced.apbs_browse -text "Browse" -command ::smiffer::browse_apbs_file

    grid $parent.advanced.apbs_lbl -row 2 -column 0 -sticky w -padx 5 -pady 2
    grid $parent.advanced.apbs_entry -row 2 -column 1 -sticky ew -padx 5 -pady 2
    grid $parent.advanced.apbs_browse -row 2 -column 2 -padx 5 -pady 2

    # Pocket sphere options
    checkbutton $parent.advanced.pocket_enable -text "Enable Pocket Sphere Mode" -variable ::smiffer::pocket_sphere -command ::smiffer::toggle_pocket_sphere_simple
    grid $parent.advanced.pocket_enable -row 3 -column 0 -columnspan 3 -sticky w -padx 5 -pady 2

    label $parent.advanced.radius_lbl -text "Radius:"
    entry $parent.advanced.radius_entry -textvariable ::smiffer::sphere_radius -width 10
    grid $parent.advanced.radius_lbl -row 4 -column 0 -sticky w -padx 5 -pady 2
    grid $parent.advanced.radius_entry -row 4 -column 1 -sticky w -padx 5 -pady 2

    label $parent.advanced.coords_lbl -text "Center (X,Y,Z):"
    frame $parent.advanced.coords_frame
    entry $parent.advanced.coords_frame.x -textvariable ::smiffer::sphere_x -width 8
    entry $parent.advanced.coords_frame.y -textvariable ::smiffer::sphere_y -width 8
    entry $parent.advanced.coords_frame.z -textvariable ::smiffer::sphere_z -width 8
    pack $parent.advanced.coords_frame.x $parent.advanced.coords_frame.y $parent.advanced.coords_frame.z -side left -padx 2

    grid $parent.advanced.coords_lbl -row 5 -column 0 -sticky w -padx 5 -pady 2
    grid $parent.advanced.coords_frame -row 5 -column 1 -sticky w -padx 5 -pady 2

    # Configure grid weights
    grid columnconfigure $parent.advanced 1 -weight 1
}

# Create control buttons
proc ::smiffer::create_control_buttons {parent} {
    variable process_running

    # Run button (with fallback)
    if {[catch {
        ttk::button $parent.run -text "Run Smiffer" -command ::smiffer::run_smiffer
    }]} {
        button $parent.run -text "Run Smiffer" -command ::smiffer::run_smiffer -bg green -fg white
    }
    pack $parent.run -side left -padx 5

    # Stop button (with fallback)
    if {[catch {
        ttk::button $parent.stop -text "Stop" -command ::smiffer::stop_smiffer -state disabled
    }]} {
        button $parent.stop -text "Stop" -command ::smiffer::stop_smiffer -state disabled -bg red -fg white
    }
    pack $parent.stop -side left -padx 5

    # Auto-load results checkbox (with fallback)
    if {[catch {
        ttk::checkbutton $parent.autoload -text "Auto-load Results" -variable ::smiffer::auto_load_results
    }]} {
        checkbutton $parent.autoload -text "Auto-load Results" -variable ::smiffer::auto_load_results
    }
    pack $parent.autoload -side left -padx 5

    # Load results button (with fallback)
    if {[catch {
        ttk::button $parent.load -text "Load Results" -command ::smiffer::load_results
    }]} {
        button $parent.load -text "Load Results" -command ::smiffer::load_results -bg blue -fg white
    }
    pack $parent.load -side left -padx 5

    # Clear log button (with fallback)
    if {[catch {
        ttk::button $parent.clear -text "Clear Log" -command ::smiffer::clear_log
    }]} {
        button $parent.clear -text "Clear Log" -command ::smiffer::clear_log
    }
    pack $parent.clear -side left -padx 5

    # Help button (with fallback)
    if {[catch {
        ttk::button $parent.help -text "Help" -command ::smiffer::show_help
    }]} {
        button $parent.help -text "Help" -command ::smiffer::show_help
    }
    pack $parent.help -side right -padx 5

    # Isovalue control button (with fallback)
    if {[catch {
        ttk::button $parent.isovalue -text "Isovalue Controls" -command ::smiffer::show_isovalue_controls
    }]} {
        button $parent.isovalue -text "Isovalue Controls" -command ::smiffer::show_isovalue_controls -bg lightblue
    }
    pack $parent.isovalue -side right -padx 5
}

# Create log area
proc ::smiffer::create_log_area {parent} {
    variable log_text

    # Create log frame with fallback
    if {[catch {
        ttk::labelframe $parent.log -text "Progress Log" -padding 10
    }]} {
        labelframe $parent.log -text "Progress Log" -padx 10 -pady 10
    }
    pack $parent.log -fill both -expand true -padx 10 -pady 5

    # Create text widget with scrollbar
    text $parent.log.text -yscrollcommand "$parent.log.scroll set" -height 10 -wrap word -font {Courier 9}

    if {[catch {
        ttk::scrollbar $parent.log.scroll -orient vertical -command "$parent.log.text yview"
    }]} {
        scrollbar $parent.log.scroll -orient vertical -command "$parent.log.text yview"
    }

    pack $parent.log.scroll -side right -fill y
    pack $parent.log.text -side left -fill both -expand true

    # Configure text widget
    $parent.log.text configure -state disabled
    set log_text $parent.log.text
}

# Initialize default values
proc ::smiffer::initialize_values {} {
    variable mode
    variable sphere_radius
    variable run_apbs
    variable pocket_sphere

    set mode "prot"
    set sphere_radius 10.0
    set run_apbs 1
    set pocket_sphere 0
}

# Configure scrollable area
proc ::smiffer::configure_scroll {canvas scrollframe} {
    $canvas configure -scrollregion [$canvas bbox all]
}

# Browse for input file
proc ::smiffer::browse_input_file {} {
    variable input_file
    variable output_dir

    set file [tk_getOpenFile -title "Select Structure File" -filetypes {
        {"Structure Files" {.pdb .cif .mmcif}}
        {"All Files" *}
    }]

    if {$file ne ""} {
        set input_file [file normalize $file]
        # Auto-set output directory if not set
        if {$output_dir eq ""} {
            set output_dir [file normalize [file dirname $file]]
        }
        log_message "Selected input file: $input_file"
    }
}

# Load current structure from VMD
proc ::smiffer::load_current_structure {} {
    variable input_file
    variable output_dir

    set molids [molinfo list]
    if {[llength $molids] == 0} {
        tk_messageBox -title "Info" -message "No molecules loaded in VMD" -type ok
        return
    }

    # Get the top molecule
    set top_mol [molinfo top]
    set filename [molinfo $top_mol get filename]

    if {$filename ne ""} {
        set input_file [file normalize $filename]
        set output_dir [file normalize [file dirname $filename]]
        log_message "Loaded current structure: $input_file"
    } else {
        tk_messageBox -title "Warning" -message "Current molecule has no associated filename" -type ok
    }
}

# Browse for output directory
proc ::smiffer::browse_output_dir {} {
    variable output_dir

    set dir [tk_chooseDirectory -title "Select Output Directory"]
    if {$dir ne ""} {
        set output_dir [file normalize $dir]
        log_message "Selected output directory: $output_dir"
    }
}

# Browse for trajectory file
proc ::smiffer::browse_trajectory {} {
    variable trajectory_file

    set file [tk_getOpenFile -title "Select Trajectory File" -filetypes {
        {"Trajectory Files" {.xtc .trr .dcd}}
        {"All Files" *}
    }]

    if {$file ne ""} {
        set trajectory_file [file normalize $file]
        log_message "Selected trajectory file: $trajectory_file"
    }
}

# Browse for APBS file
proc ::smiffer::browse_apbs_file {} {
    variable apbs_file

    set file [tk_getOpenFile -title "Select APBS File" -filetypes {
        {"APBS Files" {.dx}}
        {"All Files" *}
    }]

    if {$file ne ""} {
        set apbs_file [file normalize $file]
        log_message "Selected APBS file: $apbs_file"
    }
}

# Browse for chemical table
proc ::smiffer::browse_chem_table {} {
    variable chem_table

    set file [tk_getOpenFile -title "Select Chemical Table File" -filetypes {
        {"Chemical Table Files" {.chem}}
        {"All Files" *}
    }]

    if {$file ne ""} {
        set chem_table [file normalize $file]
        log_message "Selected chemical table: $chem_table"
    }
}

# Browse for config file
proc ::smiffer::browse_config_file {} {
    variable config_file

    set file [tk_getOpenFile -title "Select Configuration File" -filetypes {
        {"Configuration Files" {.ini}}
        {"All Files" *}
    }]

    if {$file ne ""} {
        set config_file [file normalize $file]
        log_message "Selected config file: $config_file"
    }
}

# Toggle pocket sphere controls
proc ::smiffer::toggle_pocket_sphere {} {
    variable w
    variable pocket_sphere

    set state [expr {$pocket_sphere ? "normal" : "disabled"}]

    # Enable/disable pocket sphere controls
    if {[winfo exists $w.nb.advanced.scrollframe.pocket.radius_spin]} {
        $w.nb.advanced.scrollframe.pocket.radius_spin configure -state $state
        $w.nb.advanced.scrollframe.pocket.x_spin configure -state $state
        $w.nb.advanced.scrollframe.pocket.y_spin configure -state $state
        $w.nb.advanced.scrollframe.pocket.z_spin configure -state $state
    }
}

# Toggle pocket sphere controls for simplified interface
proc ::smiffer::toggle_pocket_sphere_simple {} {
    variable w
    variable pocket_sphere

    set state [expr {$pocket_sphere ? "normal" : "disabled"}]

    # Enable/disable pocket sphere controls in simplified interface
    if {[winfo exists $w.main.advanced.radius_entry]} {
        $w.main.advanced.radius_entry configure -state $state
        $w.main.advanced.coords_frame.x configure -state $state
        $w.main.advanced.coords_frame.y configure -state $state
        $w.main.advanced.coords_frame.z configure -state $state
    }
}

# Build smiffer command
proc ::smiffer::build_smiffer_command {} {
    variable script_dir
    variable smiffer_path
    variable input_file
    variable output_dir
    variable trajectory_file
    variable apbs_file
    variable chem_table
    variable config_file
    variable mode
    variable pocket_sphere
    variable sphere_radius
    variable sphere_x
    variable sphere_y
    variable sphere_z

    if {$input_file eq ""} {
        error "Please select an input structure file"
    }

    # Build command list
    set cmd [list python3 [file normalize $smiffer_path]]

    # Add mode
    lappend cmd $mode

    # Add input file (ensure full path)
    lappend cmd [file normalize $input_file]

    # Add output directory (ensure full path)
    if {$output_dir ne ""} {
        lappend cmd "-o" [file normalize $output_dir]
    }

    # Add trajectory (ensure full path)
    if {$trajectory_file ne ""} {
        lappend cmd "-t" [file normalize $trajectory_file]
    }

    # Add APBS file (ensure full path)
    if {$apbs_file ne ""} {
        lappend cmd "-a" [file normalize $apbs_file]
    }

    # Add pocket sphere
    if {$pocket_sphere} {
        lappend cmd "-ps" $sphere_radius $sphere_x $sphere_y $sphere_z
    }

    # Add chemical table (ensure full path)
    if {$chem_table ne ""} {
        lappend cmd "-b" [file normalize $chem_table]
    }

    # Add config file (ensure full path)
    if {$config_file ne ""} {
        lappend cmd "-c" [file normalize $config_file]
    } else {
        # Default config file if not specified
        lappend cmd "-c" [file normalize [file join $script_dir "default_config.ini"]]
    }

    return $cmd
}

# Run APBS preparation
proc ::smiffer::run_apbs_preparation {structure_file} {
    variable output_dir

    set base_name [file rootname [file tail $structure_file]]
    set work_dir [file normalize [expr {$output_dir ne "" ? $output_dir : [file dirname $structure_file]}]]

    set pqr_file [file normalize [file join $work_dir "${base_name}.pqr"]]
    set input_file [file normalize [file join $work_dir "INPUT.in"]]

    # Build pdb2pqr command
    set pdb2pqr_cmd [list pdb2pqr --ff=PARSE --titration-state-method=propka --with-ph=7 --apbs-input=$input_file --drop-water [file normalize $structure_file] $pqr_file]

    log_message "Running pdb2pqr: [join $pdb2pqr_cmd]"

    # Execute pdb2pqr
    if {[catch {exec {*}$pdb2pqr_cmd} result]} {
        log_message "pdb2pqr failed: $result"
        return ""
    }

    log_message "pdb2pqr completed successfully"

    # Run APBS
    set apbs_cmd [list apbs $input_file]
    log_message "Running APBS: [join $apbs_cmd]"

    if {[catch {exec {*}$apbs_cmd} result]} {
        log_message "APBS failed: $result"
        return ""
    }

    log_message "APBS completed successfully"

    # Find the .dx file
    set dx_files [glob -nocomplain [file join $work_dir "*.dx"]]
    if {[llength $dx_files] > 0} {
        return [lindex $dx_files 0]
    }

    return ""
}

# Capture files in results directory before calculation
proc ::smiffer::capture_pre_calc_files {} {
    variable output_dir
    variable input_file
    variable pre_calc_files

    set work_dir [file normalize [expr {$output_dir ne "" ? $output_dir : [file dirname $input_file]}]]

    if {$work_dir eq "" || ![file exists $work_dir]} {
        set pre_calc_files [list]
        return
    }

    # Find all potential result files
    set result_files {}
    set extensions {.cmap .h5 .dx .ccp4 .mrc}

    foreach ext $extensions {
        set files [glob -nocomplain [file join $work_dir "*$ext"]]
        set result_files [concat $result_files $files]
    }

    set pre_calc_files $result_files
    log_message "Captured [llength $pre_calc_files] pre-existing files in results directory"
}

# Run smiffer calculation
proc ::smiffer::run_smiffer {} {
    variable w
    variable input_file
    variable output_dir
    variable apbs_file
    variable run_apbs
    variable smiffer_path
    variable process_pid
    variable process_running

    # Validate inputs
    if {$input_file eq ""} {
        tk_messageBox -title "Error" -message "Please select an input structure file" -type ok
        return
    }

    if {![file exists $input_file]} {
        tk_messageBox -title "Error" -message "Input structure file does not exist" -type ok
        return
    }

    if {![file exists $smiffer_path]} {
        tk_messageBox -title "Error" -message "Smiffer executable not found at: $smiffer_path" -type ok
        return
    }

    # Run APBS preparation if needed
    if {$run_apbs && $apbs_file eq ""} {
        log_message "Running APBS preparation..."
        set dx_file [run_apbs_preparation $input_file]
        if {$dx_file ne ""} {
            set apbs_file $dx_file
            log_message "APBS preparation completed: $dx_file"
        } else {
            log_message "APBS preparation failed, continuing without APBS"
        }
    }

    # Capture existing files in results directory before calculation
    capture_pre_calc_files

    # Build command
    if {[catch {set cmd [build_smiffer_command]} error]} {
        tk_messageBox -title "Error" -message $error -type ok
        return
    }

    # Set working directory
    set working_dir [file normalize [file dirname $smiffer_path]]

    log_message "Running command: [join $cmd]"
    log_message "Working directory: $working_dir"

    # Update UI
    $w.controls.run configure -state disabled
    $w.controls.stop configure -state normal
    if {[winfo exists $w.progress]} {
        $w.progress start
    }

    set process_running 1

    # Start process in background
    start_smiffer_process $cmd $working_dir
}

# Start smiffer process
proc ::smiffer::start_smiffer_process {cmd working_dir} {
    variable process_pid
    variable process_running

    # Change to working directory and run command
    set original_dir [pwd]
    cd $working_dir

    # Start process with output capture
    if {[catch {
        set process_pid [exec {*}$cmd 2>&1 &]
        monitor_process $process_pid
    } error]} {
        log_message "Error starting process: $error"
        on_smiffer_error $error
        cd $original_dir
        return
    }

    cd $original_dir
    log_message "Started Smiffer process with PID: $process_pid"
}

# Monitor process execution
proc ::smiffer::monitor_process {pid} {
    variable process_running

    if {!$process_running} {
        return
    }

    # Check if process is still running
    if {[catch {exec ps -p $pid} result]} {
        # Process finished
        on_smiffer_finished
        return
    }

    # Schedule next check
    after 1000 [list ::smiffer::monitor_process $pid]
}

# Stop smiffer process
proc ::smiffer::stop_smiffer {} {
    variable process_pid
    variable process_running

    if {$process_running && $process_pid ne ""} {
        log_message "Stopping Smiffer process (PID: $process_pid)..."

        # Try to terminate process gracefully
        if {[catch {exec kill $process_pid} error]} {
            log_message "Error stopping process: $error"
        }

        set process_running 0
        on_smiffer_finished
    }
}

# Handle smiffer completion
proc ::smiffer::on_smiffer_finished {} {
    variable w
    variable process_running
    variable process_pid
    variable auto_load_results

    set process_running 0
    set process_pid ""

    # Update UI
    $w.controls.run configure -state normal
    $w.controls.stop configure -state disabled
    if {[winfo exists $w.progress]} {
        $w.progress stop
    }

    log_message "Smiffer process finished"

    # Auto-load results if enabled
    if {$auto_load_results} {
        log_message "Auto-loading new results..."
        load_results
    }
}

# Handle smiffer error
proc ::smiffer::on_smiffer_error {error_msg} {
    variable w
    variable process_running

    set process_running 0

    # Update UI
    $w.controls.run configure -state normal
    $w.controls.stop configure -state disabled
    if {[winfo exists $w.progress]} {
        $w.progress stop
    }

    log_message "Smiffer error: $error_msg"
    tk_messageBox -title "Smiffer Error" -message $error_msg -type ok
}

# Load results into VMD
proc ::smiffer::load_results {} {
    variable output_dir
    variable input_file
    variable pre_calc_files

    set work_dir [file normalize [expr {$output_dir ne "" ? $output_dir : [file dirname $input_file]}]]

    if {$work_dir eq "" || ![file exists $work_dir]} {
        tk_messageBox -title "Error" -message "Output directory not found" -type ok
        return
    }

    # Find all current result files
    set current_files {}
    set extensions {.cmap .h5 .dx .ccp4 .mrc}

    foreach ext $extensions {
        set files [glob -nocomplain [file join $work_dir "*$ext"]]
        set current_files [concat $current_files $files]
    }

    # Determine new files by comparing with pre-calculation list
    set new_files [list]
    foreach file_path $current_files {
        if {[lsearch -exact $pre_calc_files $file_path] == -1} {
            lappend new_files $file_path
        }
    }

    if {[llength $new_files] == 0} {
        set message "No new result files found"
        if {[llength $current_files] > 0} {
            append message " ([llength $current_files] files already existed)"
        }
        tk_messageBox -title "Info" -message $message -type ok
        log_message $message
        return
    }

    log_message "Found [llength $new_files] new result files (out of [llength $current_files] total files)"

    # Load only the new files into VMD
    set loaded_count 0

    foreach file_path $new_files {
        if {[catch {
            log_message "Loading new file: $file_path"
            set molid [mol new $file_path]
            incr loaded_count

            # Track loaded volumes for isovalue control
            lappend ::smiffer::loaded_volumes $molid
        } error]} {
            log_message "Failed to load $file_path: $error"
        }
    }

    log_message "Loaded $loaded_count new result files"

    # Auto-color the loaded volumes
    color_loaded_volumes

    # Initialize volume rendering and default isovalues
    initialize_volume_rendering

    tk_messageBox -title "Success" -message "Loaded $loaded_count new result files" -type ok
}

# Auto-color loaded volumes
proc ::smiffer::color_loaded_volumes {} {
    # Color mapping for different field types
    array set color_map {
        hydrophobic #FFFF00
        hydrophilic #4DD9FF
        hbacceptors #B300FF
        hbdonors #FF8000
        stacking #00FF00
        apbs #0000FF
    }
    # For backup reasons
    set rgb_values [colorinfo rgb 32]
    set colored_count 0
    # Get all loaded molecules
    set molids [molinfo list]

    foreach molid $molids {
        set filename [molinfo $molid get filename]
        set base_name [file rootname [file tail $filename]]

        # Check for field type in filename
        foreach {field_type hex_color} [array get color_map] {
            if {[string match "*$field_type*" [string tolower $base_name]]} {
                # Convert colors to RGB values supported by VMD

                set r [expr "0x[string range $hex_color 1 2]" / 255.0]
                set g [expr "0x[string range $hex_color 3 4]" / 255.0]
                set b [expr "0x[string range $hex_color 5 6]" / 255.0]

                # Apply color to the molecule
                #mol modcolor 0 $molid ColorID [colorinfo num]
                #set color_name "custom_${field_type}_${molid}"
                #color add item $color_name
                #always edit 32 color
                color change rgb 32 $r $g $b
                update

                mol modcolor 0 $molid ColorID 32
                #set colorinfo_var [colorinfo num]
                update
                #log_message "Colored $filename as $field_type: $hex_color $r $g $b"
                log_message "color change rgb 32 $r $g $b"
                log_message "mol modcolor 0 $molid ColorID 32"
                incr colored_count
                break
            }
        }
    }
    # get back 32 to it's original orange color

    set r [lindex $rgb_values 0]
    set g [lindex $rgb_values 1]
    set b [lindex $rgb_values 2]
    color change rgb 32 $r $g $b

    if {$colored_count > 0} {
        log_message "Auto-colored $colored_count volumes"
    }
}

# Initialize volume rendering with default isovalues
proc ::smiffer::initialize_volume_rendering {} {
    variable loaded_volumes
    variable volume_isovalues

    foreach molid $loaded_volumes {
        if {[catch {
            set filename [molinfo $molid get filename]
            set base_name [file rootname [file tail $filename]]

            # Set default representation to isosurface
            mol modstyle 0 $molid Isosurface

            # Set default isovalue based on file type
            set default_isovalue 0.1
            if {[string match "*hydrophobic*" [string tolower $base_name]]} {
                set default_isovalue 0.05
            } elseif {[string match "*hydrophilic*" [string tolower $base_name]]} {
                set default_isovalue 0.08
            } elseif {[string match "*hbacceptors*" [string tolower $base_name]]} {
                set default_isovalue 0.15
            } elseif {[string match "*hbdonors*" [string tolower $base_name]]} {
                set default_isovalue 0.15
            } elseif {[string match "*stacking*" [string tolower $base_name]]} {
                set default_isovalue 0.12
            } elseif {[string match "*apbs*" [string tolower $base_name]]} {
                set default_isovalue 0.5
            }

            # Apply the isovalue
            mol modstyle 0 $molid "Isosurface $default_isovalue 0 0 0 1 1"

            # Store the current isovalue
            set volume_isovalues($molid) $default_isovalue

            log_message "Initialized volume rendering for $base_name with isovalue $default_isovalue"

        } error]} {
            log_message "Failed to initialize volume rendering for molecule $molid: $error"
        }
    }
}

# Show isovalue control window
proc ::smiffer::show_isovalue_controls {} {
    variable isovalue_window
    variable loaded_volumes

    # Check if volumes are loaded
    if {[llength $loaded_volumes] == 0} {
        tk_messageBox -title "Info" -message "No volumes loaded. Please load results first." -type ok
        return
    }

    # Destroy existing window if it exists
    if {[winfo exists .isovalue_controls]} {
        destroy .isovalue_controls
    }

    # Create isovalue control window
    set isovalue_window [toplevel .isovalue_controls]
    wm title $isovalue_window "Isovalue Controls"
    wm geometry $isovalue_window 500x600
    wm resizable $isovalue_window 1 1

    # Create main frame
    frame $isovalue_window.main
    pack $isovalue_window.main -fill both -expand true -padx 10 -pady 10

    # Create title label
    label $isovalue_window.main.title -text "Volume Isovalue Controls" -font {Arial 14 bold}
    pack $isovalue_window.main.title -pady 10

    # Create scrollable frame for volume controls
    canvas $isovalue_window.main.canvas -yscrollcommand "$isovalue_window.main.scroll set"
    scrollbar $isovalue_window.main.scroll -orient vertical -command "$isovalue_window.main.canvas yview"
    frame $isovalue_window.main.scrollframe

    pack $isovalue_window.main.scroll -side right -fill y
    pack $isovalue_window.main.canvas -side left -fill both -expand true

    $isovalue_window.main.canvas create window 0 0 -anchor nw -window $isovalue_window.main.scrollframe

    # Create controls for each loaded volume
    create_volume_controls $isovalue_window.main.scrollframe

    # Configure scrollable area
    bind $isovalue_window.main.scrollframe <Configure> "configure_isovalue_scroll $isovalue_window.main.canvas $isovalue_window.main.scrollframe"

    # Create control buttons
    frame $isovalue_window.controls
    pack $isovalue_window.controls -fill x -padx 10 -pady 5

    button $isovalue_window.controls.refresh -text "Refresh" -command ::smiffer::refresh_isovalue_controls
    button $isovalue_window.controls.reset -text "Reset to Defaults" -command ::smiffer::reset_isovalues
    button $isovalue_window.controls.close -text "Close" -command "destroy $isovalue_window"

    pack $isovalue_window.controls.refresh -side left -padx 5
    pack $isovalue_window.controls.reset -side left -padx 5
    pack $isovalue_window.controls.close -side right -padx 5
}

# Create controls for each volume
proc ::smiffer::create_volume_controls {parent} {
    variable loaded_volumes
    variable volume_isovalues

    set row 0

    foreach molid $loaded_volumes {
        # Check if molecule still exists
        if {[catch {molinfo $molid get filename} filename]} {
            continue
        }

        set base_name [file rootname [file tail $filename]]

        # Create frame for this volume
        labelframe $parent.vol_$molid -text "$base_name (ID: $molid)" -padx 5 -pady 5
        grid $parent.vol_$molid -row $row -column 0 -sticky ew -padx 5 -pady 2

        # Current isovalue display
        label $parent.vol_$molid.current_lbl -text "Current Isovalue:"
        label $parent.vol_$molid.current_val -text [format "%.3f" $volume_isovalues($molid)] -font {Courier 10}

        grid $parent.vol_$molid.current_lbl -row 0 -column 0 -sticky w -padx 5
        grid $parent.vol_$molid.current_val -row 0 -column 1 -sticky w -padx 5

        # Isovalue scale
        set minmax_values [voltool info minmax -mol $molid]
        set min_val [lindex $minmax_values 0]
        set max_val [lindex $minmax_values 1]

        scale $parent.vol_$molid.scale -from $min_val -to $max_val -resolution 0.001 -orient horizontal \
            -variable ::smiffer::volume_isovalues($molid) \
            -command "::smiffer::update_isovalue $molid" \
            -length 300

        grid $parent.vol_$molid.scale -row 1 -column 0 -columnspan 4 -sticky ew -padx 5 -pady 5

        # Quick preset buttons
        button $parent.vol_$molid.low -text "Low (0.01)" -command "::smiffer::set_isovalue $molid 0.01"
        button $parent.vol_$molid.med -text "Medium (0.1)" -command "::smiffer::set_isovalue $molid 0.1"
        button $parent.vol_$molid.high -text "High (0.5)" -command "::smiffer::set_isovalue $molid 0.5"

        grid $parent.vol_$molid.low -row 2 -column 0 -sticky w -padx 2
        grid $parent.vol_$molid.med -row 2 -column 1 -sticky w -padx 2
        grid $parent.vol_$molid.high -row 2 -column 2 -sticky w -padx 2

        # Visibility toggle
        checkbutton $parent.vol_$molid.visible -text "Visible" -command "::smiffer::toggle_volume_visibility $molid"
        $parent.vol_$molid.visible select
        grid $parent.vol_$molid.visible -row 2 -column 3 -sticky e -padx 5

        # Configure grid weights
        grid columnconfigure $parent.vol_$molid 0 -weight 1

        incr row
    }

    # Configure parent grid
    grid columnconfigure $parent 0 -weight 1
}

# Update isovalue for a specific volume
proc ::smiffer::update_isovalue {molid isovalue} {
    variable volume_isovalues

    if {[catch {
        # Update the isosurface representation
        mol modstyle 0 $molid "Isosurface $isovalue 0 0 0 1 1"

        # Update the stored value
        set volume_isovalues($molid) $isovalue

        # Update the display label if it exists
        if {[winfo exists .isovalue_controls.main.scrollframe.vol_$molid.current_val]} {
            .isovalue_controls.main.scrollframe.vol_$molid.current_val configure -text [format "%.3f" $isovalue]
        }

    } error]} {
        log_message "Error updating isovalue for molecule $molid: $error"
    }
}

# Set specific isovalue for a volume
proc ::smiffer::set_isovalue {molid isovalue} {
    variable volume_isovalues

    set volume_isovalues($molid) $isovalue
    update_isovalue $molid $isovalue
}

# Toggle volume visibility
proc ::smiffer::toggle_volume_visibility {molid} {
    if {[catch {
        set current_rep [mol showrep $molid 0]
        mol showrep $molid 0 [expr {!$current_rep}]
    } error]} {
        log_message "Error toggling visibility for molecule $molid: $error"
    }
}

# Refresh isovalue controls
proc ::smiffer::refresh_isovalue_controls {} {
    variable isovalue_window
    variable loaded_volumes

    # Clean up loaded_volumes list - remove non-existent molecules
    set valid_volumes [list]
    foreach molid $loaded_volumes {
        if {![catch {molinfo $molid get filename}]} {
            lappend valid_volumes $molid
        }
    }
    set loaded_volumes $valid_volumes

    # Recreate the controls
    if {[winfo exists $isovalue_window.main.scrollframe]} {
        destroy $isovalue_window.main.scrollframe
        frame $isovalue_window.main.scrollframe
        $isovalue_window.main.canvas create window 0 0 -anchor nw -window $isovalue_window.main.scrollframe
        create_volume_controls $isovalue_window.main.scrollframe
    }
}

# Reset all volumes to default isovalues
proc ::smiffer::reset_isovalues {} {
    variable loaded_volumes

    foreach molid $loaded_volumes {
        if {[catch {
            set filename [molinfo $molid get filename]
            set base_name [file rootname [file tail $filename]]

            # Determine default isovalue based on file type
            set default_isovalue 0.1
            if {[string match "*hydrophobic*" [string tolower $base_name]]} {
                set default_isovalue 0.05
            } elseif {[string match "*hydrophilic*" [string tolower $base_name]]} {
                set default_isovalue 0.08
            } elseif {[string match "*hbacceptors*" [string tolower $base_name]]} {
                set default_isovalue 0.15
            } elseif {[string match "*hbdonors*" [string tolower $base_name]]} {
                set default_isovalue 0.15
            } elseif {[string match "*stacking*" [string tolower $base_name]]} {
                set default_isovalue 0.12
            } elseif {[string match "*apbs*" [string tolower $base_name]]} {
                set default_isovalue 0.5
            }

            set_isovalue $molid $default_isovalue

        } error]} {
            log_message "Error resetting isovalue for molecule $molid: $error"
        }
    }
}

# Configure scrollable area for isovalue window
proc configure_isovalue_scroll {canvas scrollframe} {
    $canvas configure -scrollregion [$canvas bbox all]
}

# Clear log
proc ::smiffer::clear_log {} {
    variable log_text

    $log_text configure -state normal
    $log_text delete 1.0 end
    $log_text configure -state disabled
}

# Log message
proc ::smiffer::log_message {message} {
    variable log_text

    set timestamp [clock format [clock seconds] -format "%H:%M:%S"]

    $log_text configure -state normal
    $log_text insert end "\[$timestamp\] $message\n"
    $log_text see end
    $log_text configure -state disabled

    # Also print to VMD console
    puts "Smiffer: $message"
}

# Show help
proc ::smiffer::show_help {} {
    set help_text {
VMD Smiffer Plugin Help
========================

This plugin provides a GUI interface for running Smiffer calculations on protein and RNA structures within VMD.

Basic Usage:
1. Select an input structure file or load the current VMD structure
2. Choose the molecular type (prot/rna)
3. Select an output directory
4. Click "Run Smiffer"

Advanced Options:
- Trajectory analysis: Select a trajectory file for multi-frame analysis
- APBS integration: Provide APBS .dx file or enable automatic APBS calculation
- Pocket sphere mode: Restrict calculations to a spherical region
- Chemical table: Use custom chemical parameters
- Configuration: Use custom configuration file

Results:
- Click "Load Results" to automatically load all generated grid files
- Files are auto-colored based on their type (hydrophobic=yellow, hydrophilic=cyan, etc.)
- Click "Isovalue Controls" to open a separate window for adjusting isosurface values

Isovalue Controls:
- Interactive sliders for each loaded volume to adjust isosurface thresholds
- Quick preset buttons for low, medium, and high isovalue settings
- Visibility toggles for each volume
- Real-time updates of isosurface rendering in VMD
- Default isovalues are automatically set based on volume type

Requirements:
- Python 3 with smiffer package installed
- APBS (optional, for electrostatic calculations)
- pdb2pqr (optional, for APBS preparation)

For more information, see the smiffer documentation.
    }

    set help_win [toplevel .smiffer_help]
    wm title $help_win "Smiffer Help"
    wm geometry $help_win 600x500

    text $help_win.text -wrap word -yscrollcommand "$help_win.scroll set"

    if {[catch {
        ttk::scrollbar $help_win.scroll -orient vertical -command "$help_win.text yview"
    }]} {
        scrollbar $help_win.scroll -orient vertical -command "$help_win.text yview"
    }

    pack $help_win.scroll -side right -fill y
    pack $help_win.text -side left -fill both -expand true

    $help_win.text insert end $help_text
    $help_win.text configure -state disabled

    if {[catch {
        ttk::button $help_win.close -text "Close" -command "destroy $help_win"
    }]} {
        button $help_win.close -text "Close" -command "destroy $help_win"
    }
    pack $help_win.close -pady 10
}

# VMD plugin registration
proc vmd_smiffer_tk {} {
    ::smiffer::show_gui
    return $::smiffer::w
}

# Menu integration
if {[info exists vmd_menu_data]} {
    lappend vmd_menu_data "Smiffer Tool" vmd_smiffer_tk
}

# Initialize the plugin
puts "VMD Smiffer Plugin loaded successfully"
puts "Use 'vmd_smiffer_tk' command or Extensions->Smiffer Tool to open the GUI"
