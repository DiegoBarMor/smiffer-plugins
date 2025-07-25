"""
PyMOL Smiffer Plugin - A PyMOL plugin for molecular interaction field analysis
Based on the ChimeraX Smiffer Tool functionality
"""

import os
import sys
import json
import subprocess
import threading
from functools import partial

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    import Tkinter as tk
    import tkFileDialog as filedialog
    import tkMessageBox as messagebox
    import ttk

# PyMOL imports
import pymol
from pymol import cmd
from pymol.Qt import QtWidgets, QtCore, QtGui


class SmifferPyMOLPlugin:
    """Main PyMOL Smiffer Plugin class"""

    def __init__(self):
        self.dialog = None
        self.smiffer_path = None
        self.current_process = None
        self.worker_thread = None
        self._find_smiffer_path()

    def _find_smiffer_path(self):
        """Find the smiffer.py script path"""
        # Look for smiffer.py in common locations
        print(os.getcwd())
        print(os.path.dirname(__file__))
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "volgrids-main", "run", "smiffer.py"),
            os.path.join(os.path.dirname(__file__), "smiffer.py"),
            "smiffer.py"  # Assume it's in PATH
        ]

        for path in possible_paths:
            if os.path.exists(path):
                self.smiffer_path = path
                break

    def show_gui(self):
        """Show the Smiffer GUI"""
        if self.dialog is None:
            self.dialog = SmifferDialog(self)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()


class SmifferDialog(QtWidgets.QDialog):
    """PyMOL Smiffer Plugin GUI Dialog"""

    def __init__(self, plugin):
        super().__init__()
        self.plugin = plugin
        self.current_process = None
        self.worker_thread = None
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("PyMOL Smiffer Tool")
        self.setMinimumSize(600, 700)

        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)

        # Tab widget for different sections
        tabs = QtWidgets.QTabWidget()

        # Basic Settings Tab
        basic_tab = QtWidgets.QWidget()
        self.setup_basic_tab(basic_tab)
        tabs.addTab(basic_tab, "Basic Settings")

        # Advanced Settings Tab
        advanced_tab = QtWidgets.QWidget()
        self.setup_advanced_tab(advanced_tab)
        tabs.addTab(advanced_tab, "Advanced Settings")

        main_layout.addWidget(tabs)

        # Control buttons
        self.setup_control_buttons(main_layout)

        # Results loading options
        self.setup_results_options(main_layout)

        # Progress bar
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # Log area
        self.setup_log_area(main_layout)

    def setup_basic_tab(self, tab):
        """Setup the basic settings tab"""
        layout = QtWidgets.QVBoxLayout(tab)

        # Input file section
        input_group = QtWidgets.QGroupBox("Input Structure")
        input_layout = QtWidgets.QFormLayout(input_group)

        self.input_file_edit = QtWidgets.QLineEdit()
        input_browse_btn = QtWidgets.QPushButton("Browse")
        input_browse_btn.clicked.connect(self.browse_input_file)
        input_file_layout = QtWidgets.QHBoxLayout()
        input_file_layout.addWidget(self.input_file_edit)
        input_file_layout.addWidget(input_browse_btn)

        # Add button to use current PyMOL structure
        pymol_structure_btn = QtWidgets.QPushButton("Use Current PyMOL Structure")
        pymol_structure_btn.clicked.connect(self.use_current_pymol_structure)
        input_file_layout.addWidget(pymol_structure_btn)

        input_layout.addRow("Structure File:", input_file_layout)

        # Mode selection
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["prot", "rna", "ligand"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        input_layout.addRow("Mode:", self.mode_combo)

        # Output directory
        self.output_dir_edit = QtWidgets.QLineEdit()
        self.first_files_folder = []
        output_browse_btn = QtWidgets.QPushButton("Browse")
        output_browse_btn.clicked.connect(self.browse_output_dir)
        output_dir_layout = QtWidgets.QHBoxLayout()
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(output_browse_btn)
        input_layout.addRow("Output Directory:", output_dir_layout)

        layout.addWidget(input_group)

    def setup_advanced_tab(self, tab):
        """Setup the advanced settings tab"""
        layout = QtWidgets.QVBoxLayout(tab)

        # Trajectory section
        traj_group = QtWidgets.QGroupBox("Trajectory Options")
        traj_layout = QtWidgets.QFormLayout(traj_group)

        self.trajectory_edit = QtWidgets.QLineEdit()
        traj_browse_btn = QtWidgets.QPushButton("Browse")
        traj_browse_btn.clicked.connect(self.browse_trajectory)
        traj_layout_h = QtWidgets.QHBoxLayout()
        traj_layout_h.addWidget(self.trajectory_edit)
        traj_layout_h.addWidget(traj_browse_btn)
        traj_layout.addRow("Trajectory File:", traj_layout_h)

        layout.addWidget(traj_group)

        # APBS section
        apbs_group = QtWidgets.QGroupBox("APBS Options")
        apbs_layout = QtWidgets.QFormLayout(apbs_group)

        self.apbs_file_edit = QtWidgets.QLineEdit()
        apbs_browse_btn = QtWidgets.QPushButton("Browse")
        apbs_browse_btn.clicked.connect(self.browse_apbs_file)
        apbs_layout_h = QtWidgets.QHBoxLayout()
        apbs_layout_h.addWidget(self.apbs_file_edit)
        apbs_layout_h.addWidget(apbs_browse_btn)
        apbs_layout.addRow("APBS File (.dx):", apbs_layout_h)

        self.run_apbs_checkbox = QtWidgets.QCheckBox("Run APBS automatically")
        self.run_apbs_checkbox.setChecked(True)
        apbs_layout.addRow("", self.run_apbs_checkbox)

        layout.addWidget(apbs_group)

        # Pocket sphere section
        pocket_group = QtWidgets.QGroupBox("Pocket Sphere Mode")
        pocket_layout = QtWidgets.QFormLayout(pocket_group)

        self.pocket_sphere_checkbox = QtWidgets.QCheckBox("Enable Pocket Sphere Mode")
        self.pocket_sphere_checkbox.toggled.connect(self.toggle_pocket_sphere)
        pocket_layout.addRow("", self.pocket_sphere_checkbox)

        self.sphere_radius_spin = QtWidgets.QDoubleSpinBox()
        self.sphere_radius_spin.setRange(0.1, 100.0)
        self.sphere_radius_spin.setValue(10.0)
        self.sphere_radius_spin.setEnabled(False)
        pocket_layout.addRow("Radius (Å):", self.sphere_radius_spin)

        sphere_coords_layout = QtWidgets.QHBoxLayout()
        self.sphere_x_spin = QtWidgets.QDoubleSpinBox()
        self.sphere_x_spin.setRange(-999.0, 999.0)
        self.sphere_x_spin.setEnabled(False)
        self.sphere_y_spin = QtWidgets.QDoubleSpinBox()
        self.sphere_y_spin.setRange(-999.0, 999.0)
        self.sphere_y_spin.setEnabled(False)
        self.sphere_z_spin = QtWidgets.QDoubleSpinBox()
        self.sphere_z_spin.setRange(-999.0, 999.0)
        self.sphere_z_spin.setEnabled(False)

        sphere_coords_layout.addWidget(QtWidgets.QLabel("X:"))
        sphere_coords_layout.addWidget(self.sphere_x_spin)
        sphere_coords_layout.addWidget(QtWidgets.QLabel("Y:"))
        sphere_coords_layout.addWidget(self.sphere_y_spin)
        sphere_coords_layout.addWidget(QtWidgets.QLabel("Z:"))
        sphere_coords_layout.addWidget(self.sphere_z_spin)

        # Add button to get center from PyMOL selection
        get_center_btn = QtWidgets.QPushButton("Get Center from PyMOL Selection")
        get_center_btn.clicked.connect(self.get_center_from_pymol)
        sphere_coords_layout.addWidget(get_center_btn)

        pocket_layout.addRow("Center:", sphere_coords_layout)

        layout.addWidget(pocket_group)

        # Chemical table section
        chem_group = QtWidgets.QGroupBox("Chemical Table")
        chem_layout = QtWidgets.QFormLayout(chem_group)

        self.chem_table_edit = QtWidgets.QLineEdit()
        chem_browse_btn = QtWidgets.QPushButton("Browse")
        chem_browse_btn.clicked.connect(self.browse_chem_table)
        chem_layout_h = QtWidgets.QHBoxLayout()
        chem_layout_h.addWidget(self.chem_table_edit)
        chem_layout_h.addWidget(chem_browse_btn)
        chem_layout.addRow("Table File (.chem):", chem_layout_h)

        layout.addWidget(chem_group)

        # Configuration section
        config_group = QtWidgets.QGroupBox("Configuration")
        config_layout = QtWidgets.QFormLayout(config_group)

        self.config_file_edit = QtWidgets.QLineEdit()
        config_browse_btn = QtWidgets.QPushButton("Browse")
        config_browse_btn.clicked.connect(self.browse_config_file)
        config_layout_h = QtWidgets.QHBoxLayout()
        config_layout_h.addWidget(self.config_file_edit)
        config_layout_h.addWidget(config_browse_btn)
        config_layout.addRow("Config File (.ini):", config_layout_h)

        layout.addWidget(config_group)

    def setup_control_buttons(self, layout):
        """Setup control buttons"""
        control_layout = QtWidgets.QHBoxLayout()

        self.run_button = QtWidgets.QPushButton("Run Smiffer")
        self.run_button.clicked.connect(self.run_smiffer)
        self.run_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")

        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_smiffer)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; }")

        self.load_results_button = QtWidgets.QPushButton("Load Results")
        self.load_results_button.clicked.connect(self.load_results)
        self.load_results_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 8px; }")

        control_layout.addWidget(self.run_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.load_results_button)
        control_layout.addStretch()

        layout.addLayout(control_layout)

    def setup_results_options(self, layout):
        """Setup results loading options"""
        results_group = QtWidgets.QGroupBox("Results Loading Options")
        results_layout = QtWidgets.QFormLayout(results_group)

        # Autoload checkbox
        self.autoload_checkbox = QtWidgets.QCheckBox("Autoload results after completion")
        self.autoload_checkbox.setChecked(False)
        results_layout.addRow("", self.autoload_checkbox)

        # Autocolor checkbox
        self.autocolor_checkbox = QtWidgets.QCheckBox("Autocolor fields on load")
        self.autocolor_checkbox.setChecked(True)
        results_layout.addRow("", self.autocolor_checkbox)

        # Map level control checkbox
        self.map_control_checkbox = QtWidgets.QCheckBox("Open map level control window")
        self.map_control_checkbox.setChecked(True)
        results_layout.addRow("", self.map_control_checkbox)

        layout.addWidget(results_group)

    def setup_log_area(self, layout):
        """Setup log area"""
        log_group = QtWidgets.QGroupBox("Progress Log")
        log_layout = QtWidgets.QVBoxLayout(log_group)

        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("QTextEdit { background-color: #f5f5f5; font-family: monospace; }")
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

    def log_message(self, message):
        """Add a message to the log"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.ensureCursorVisible()

    def browse_input_file(self):
        """Browse for input structure file"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Structure File", "",
            "Structure Files (*.pdb *.cif *.mmcif);;All Files (*)"
        )
        if file_path:
            self.input_file_edit.setText(file_path)
            if not self.output_dir_edit.text():
                self.output_dir_edit.setText(os.path.dirname(file_path))

    def browse_output_dir(self):
        """Browse for output directory"""
        dir_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir_edit.setText(dir_path)

    def browse_trajectory(self):
        """Browse for trajectory file"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Trajectory File", "",
            "Trajectory Files (*.xtc *.trr *.dcd);;All Files (*)"
        )
        if file_path:
            self.trajectory_edit.setText(file_path)

    def browse_apbs_file(self):
        """Browse for APBS file"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select APBS File", "",
            "APBS Files (*.dx);;All Files (*)"
        )
        if file_path:
            self.apbs_file_edit.setText(file_path)

    def browse_chem_table(self):
        """Browse for chemical table file"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Chemical Table File", "",
            "Chemical Table Files (*.chem);;All Files (*)"
        )
        if file_path:
            self.chem_table_edit.setText(file_path)

    def browse_config_file(self):
        """Browse for configuration file"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select Configuration File", "",
            "Configuration Files (*.ini);;All Files (*)"
        )
        if file_path:
            self.config_file_edit.setText(file_path)

    def use_current_pymol_structure(self):
        """Use current PyMOL structure as input"""
        try:
            # Get list of loaded objects
            objects = cmd.get_names("objects")
            if not objects:
                QtWidgets.QMessageBox.warning(self, "Warning", "No structures loaded in PyMOL")
                return

            # If multiple objects, let user choose
            if len(objects) > 1:
                obj_name, ok = QtWidgets.QInputDialog.getItem(
                    self, "Select Object", "Choose PyMOL object:", objects, 0, False
                )
                if not ok:
                    return
            else:
                obj_name = objects[0]

            # Save structure to temporary file
            print(f"Current dir = {os.getcwd()}")
            #temp_dir = self.output_dir_edit.text() or os.path.expanduser("~")
            temp_dir = self.output_dir_edit.text() or os.getcwd()
            temp_file = os.path.join(temp_dir, f"{obj_name}_pymol_export.pdb")

            cmd.save(temp_file, obj_name)
            self.input_file_edit.setText(temp_file)

            if not self.output_dir_edit.text():
                self.output_dir_edit.setText(temp_dir)

            self.log_message(f"Exported PyMOL object '{obj_name}' to {temp_file}")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to export PyMOL structure: {str(e)}")

    def get_center_from_pymol(self):
        """Get center coordinates from PyMOL selection"""
        try:
            # Get current selection
            selection = cmd.get_names("selections")
            if not selection:
                QtWidgets.QMessageBox.warning(self, "Warning", "No selection in PyMOL")
                return

            # Get center of mass
            center = cmd.centerofmass("sele")

            self.sphere_x_spin.setValue(center[0])
            self.sphere_y_spin.setValue(center[1])
            self.sphere_z_spin.setValue(center[2])

            self.log_message(f"Got center from PyMOL selection: ({center[0]:.2f}, {center[1]:.2f}, {center[2]:.2f})")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to get center from PyMOL: {str(e)}")

    def on_mode_changed(self, mode):
        """Handle mode change"""
        if mode == "ligand":
            self.chem_table_edit.setEnabled(True)
        else:
            self.chem_table_edit.setEnabled(False)

    def toggle_pocket_sphere(self, enabled):
        """Toggle pocket sphere controls"""
        self.sphere_radius_spin.setEnabled(enabled)
        self.sphere_x_spin.setEnabled(enabled)
        self.sphere_y_spin.setEnabled(enabled)
        self.sphere_z_spin.setEnabled(enabled)

    def build_smiffer_command(self):
        """Build the smiffer command from UI inputs"""
        if not self.input_file_edit.text():
            raise ValueError("Please select an input structure file")

        if not self.plugin.smiffer_path:
            raise ValueError("Smiffer script not found. Please ensure smiffer.py is available")

        cmd_list = [sys.executable, self.plugin.smiffer_path]

        # Add mode
        mode = self.mode_combo.currentText()
        cmd_list.append(mode)

        # Add input file
        cmd_list.append(self.input_file_edit.text())

        # Add output directory
        if self.output_dir_edit.text():
            cmd_list.extend(["-o", self.output_dir_edit.text()])

        # Add trajectory
        if self.trajectory_edit.text():
            cmd_list.extend(["-t", self.trajectory_edit.text()])

        # Add APBS file
        if self.apbs_file_edit.text():
            cmd_list.extend(["-a", self.apbs_file_edit.text()])

        # Add pocket sphere
        if self.pocket_sphere_checkbox.isChecked():
            cmd_list.extend(["-ps",
                           str(self.sphere_radius_spin.value()),
                           str(self.sphere_x_spin.value()),
                           str(self.sphere_y_spin.value()),
                           str(self.sphere_z_spin.value())])

        # Add chemical table
        if self.chem_table_edit.text():
            cmd_list.extend(["-b", self.chem_table_edit.text()])

        # Add config file
        if self.config_file_edit.text():
            cmd_list.extend(["-c", self.config_file_edit.text()])

        return cmd_list

    def run_smiffer(self):
        """Run the smiffer calculation"""
        try:
            # Validate inputs
            if not self.input_file_edit.text():
                QtWidgets.QMessageBox.warning(self, "Error", "Please select an input structure file")
                return

            if not os.path.exists(self.input_file_edit.text()):
                QtWidgets.QMessageBox.warning(self, "Error", "Input structure file does not exist")
                return
            list_of_files = os.listdir(self.output_dir_edit.text())
            #print(f"list_of_files = {list_of_files}")
            self.first_files_folder = list_of_files
            #print(f"Output folder = {self.first_files_folder}")
            # Build command
            cmd_list = self.build_smiffer_command()

            # Set working directory
            working_dir = os.path.dirname(self.plugin.smiffer_path) if self.plugin.smiffer_path else os.getcwd()

            self.log_message(f"Running command: {' '.join(cmd_list)}")
            self.log_message(f"Working directory: {working_dir}")

            # Create and start worker thread
            self.worker_thread = SmifferWorker(cmd_list, working_dir)
            self.worker_thread.finished.connect(self.on_smiffer_finished)
            self.worker_thread.error.connect(self.on_smiffer_error)
            self.worker_thread.output.connect(self.log_message)

            # Update UI
            self.run_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress

            self.worker_thread.start()

        except Exception as e:
            self.log_message(f"Error starting Smiffer: {str(e)}")
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to start Smiffer: {str(e)}")

    def stop_smiffer(self):
        """Stop the running Smiffer process"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.log_message("Stopping Smiffer process...")
            self.worker_thread.stop()
            self.worker_thread.wait()

    def on_smiffer_finished(self):
        """Handle Smiffer completion"""
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.log_message("Smiffer process finished")

        # Autoload if enabled
        if self.autoload_checkbox.isChecked():
            self.load_results()

    def on_smiffer_error(self, error_msg):
        """Handle Smiffer error"""
        self.log_message(f"Smiffer error: {error_msg}")
        QtWidgets.QMessageBox.warning(self, "Smiffer Error", error_msg)

    def load_results(self):
        """Load Smiffer results into PyMOL"""
        try:
            files_in_folder_before = self.first_files_folder
            output_dir = self.output_dir_edit.text()

            if not output_dir:
                output_dir = os.path.dirname(self.input_file_edit.text()) if self.input_file_edit.text() else ""

            if not output_dir or not os.path.exists(output_dir):
                QtWidgets.QMessageBox.warning(self, "Error", "Output directory not found")
                return

            # Find result files, prioritizing recently created ones
            result_files = []
            for ext in ['.cmap', '.h5', '.dx', '.ccp4', '.mrc']:
                files = [f for f in os.listdir(output_dir) if f.endswith(ext)]
                #print(files)
                new_files = [x for x in files if x not in files_in_folder_before]
                #print(f"NEW FILES: {new_files}")
                files_with_time = [(f, os.path.getmtime(os.path.join(output_dir, f))) for f in new_files]
                files_with_time.sort(key=lambda x: x[1], reverse=True)  # Sort by modification time, newest first
                #print(files_with_time)
                """
                new_files_with_time = []
                for file in files_with_time:
                    print(file)
                    if file not in files_in_folder_before:
                        new_files_with_time.append(file)
                #new_files_with_time = [x for x in files_with_time if x not in files_in_folder_before]
                """
                #print(f"Size of new_files: {len(files_with_time)}")
                result_files.extend([os.path.join(output_dir, f[0]) for f in files_with_time])
                #print(result_files)


            if not result_files:
                QtWidgets.QMessageBox.information(self, "Info", "No result files found in output directory")
                return

            # Load files into PyMOL
            loaded_count = 0
            mrc_files = []

            color_map = {
                'hydrophobic': 'yellow',
                'hydrophilic': 'cyan',
                'hbacceptors': 'orange',
                'hbdonors': 'magenta',
                'stacking': 'green',
                'apbs': 'blue'
            }

            for file_path in result_files:
                try:
                    self.log_message(f"Loading {file_path}")
                    base_name = os.path.splitext(os.path.basename(file_path))[0]

                    # Load the file
                    cmd.load(file_path, base_name)

                    # Auto-color based on filename if enabled
                    if self.autocolor_checkbox.isChecked():
                        for field_type, color in color_map.items():
                            if field_type in base_name.lower():
                                cmd.color(color, base_name)
                                self.log_message(f"Colored {base_name} as {field_type}: {color}")
                                break

                    # Keep track of MRC files for map level control
                    if file_path.endswith('.mrc'):
                        mrc_files.append(base_name)

                    loaded_count += 1

                except Exception as e:
                    self.log_message(f"Failed to load {file_path}: {str(e)}")

            self.log_message(f"Loaded {loaded_count} result files")

            # Open map level control window if enabled and we have MRC files
            if self.map_control_checkbox.isChecked() and mrc_files:
                self.open_map_control_window(mrc_files)

            QtWidgets.QMessageBox.information(self, "Success", f"Loaded {loaded_count} result files")

        except Exception as e:
            self.log_message(f"Error loading results: {str(e)}")
            QtWidgets.QMessageBox.warning(self, "Error", f"Failed to load results: {str(e)}")

    def open_map_control_window(self, mrc_files):
        """Open a new window to control map levels"""
        try:
            self.map_control_window = MapControlWindow(mrc_files, self)
            self.map_control_window.show()
            self.log_message(f"Opened map level control window for {len(mrc_files)} MRC files")
        except Exception as e:
            self.log_message(f"Failed to open map control window: {str(e)}")


class MapControlWindow(QtWidgets.QDialog):
    """Window for controlling map levels with sliders"""

    def __init__(self, mrc_files, parent=None):
        super().__init__(parent)
        self.mrc_files = mrc_files
        self.sliders = {}
        self.level_labels = {}
        self.setup_ui()

    def setup_ui(self):
        """Setup the map control UI"""
        self.setWindowTitle("Map Level Control")
        self.setMinimumSize(400, 300)

        layout = QtWidgets.QVBoxLayout(self)

        # Header
        header_label = QtWidgets.QLabel("Control Map Levels")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(header_label)

        # Scroll area for sliders
        scroll_area = QtWidgets.QScrollArea()
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)

        for mrc_file in self.mrc_files:
            # Create group box for each MRC file
            group_box = QtWidgets.QGroupBox(mrc_file)
            group_layout = QtWidgets.QVBoxLayout(group_box)

            # Level slider
            level_layout = QtWidgets.QHBoxLayout()
            level_layout.addWidget(QtWidgets.QLabel("Level:"))

            level_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            level_slider.setRange(-100, 100)
            level_slider.setValue(0)
            level_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
            level_slider.setTickInterval(20)
            level_slider.valueChanged.connect(partial(self.update_map_level, mrc_file))

            level_label = QtWidgets.QLabel("0.0")
            level_label.setMinimumWidth(50)

            level_layout.addWidget(level_slider)
            level_layout.addWidget(level_label)

            group_layout.addLayout(level_layout)

            # Transparency slider
            transparency_layout = QtWidgets.QHBoxLayout()
            transparency_layout.addWidget(QtWidgets.QLabel("Transparency:"))

            transparency_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            transparency_slider.setRange(0, 100)
            transparency_slider.setValue(0)
            transparency_slider.setTickPosition(QtWidgets.QSlider.TicksBelow)
            transparency_slider.setTickInterval(20)
            transparency_slider.valueChanged.connect(partial(self.update_map_transparency, mrc_file))
            transparency_label = QtWidgets.QLabel("0%")
            transparency_label.setMinimumWidth(50)

            transparency_layout.addWidget(transparency_slider)
            transparency_layout.addWidget(transparency_label)

            group_layout.addLayout(transparency_layout)

            # Show/Hide checkbox
            show_checkbox = QtWidgets.QCheckBox("Show Map")
            show_checkbox.setChecked(True)
            show_checkbox.toggled.connect(partial(self.toggle_map_visibility, mrc_file))
            group_layout.addWidget(show_checkbox)

            scroll_layout.addWidget(group_box)

            # Store references
            self.sliders[mrc_file] = {
                'level': level_slider,
                'transparency': transparency_slider,
                'show': show_checkbox
            }
            self.level_labels[mrc_file] = {
                'level': level_label,
                'transparency': transparency_label
            }

        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # Control buttons
        button_layout = QtWidgets.QHBoxLayout()

        reset_button = QtWidgets.QPushButton("Reset All")
        reset_button.clicked.connect(self.reset_all_levels)
        button_layout.addWidget(reset_button)

        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def update_map_level(self, mrc_file, value):
        """Update map level for a specific MRC file"""
        try:
            # Convert slider value to appropriate level
            level = value / 10.0  # Scale to reasonable range

            # Update PyMOL map level
            cmd.isomesh(f"{mrc_file}_mesh", mrc_file, level)

            # Update label
            self.level_labels[mrc_file]['level'].setText(f"{level:.1f}")

        except Exception as e:
            print(f"Error updating map level for {mrc_file}: {str(e)}")

    def update_map_transparency(self, mrc_file, value):
        """Update map transparency for a specific MRC file"""
        try:
            # Convert slider value to transparency (0-1)
            transparency = value / 100.0

            # Update PyMOL transparency
            cmd.set("transparency", transparency, f"{mrc_file}_mesh")

            # Update label
            self.level_labels[mrc_file]['transparency'].setText(f"{value}%")

        except Exception as e:
            print(f"Error updating transparency for {mrc_file}: {str(e)}")

    def toggle_map_visibility(self, mrc_file, visible):
        """Toggle map visibility"""
        try:
            if visible:
                cmd.show("mesh", f"{mrc_file}_mesh")
            else:
                cmd.hide("mesh", f"{mrc_file}_mesh")
        except Exception as e:
            print(f"Error toggling visibility for {mrc_file}: {str(e)}")

    def reset_all_levels(self):
        """Reset all map levels to default"""
        for mrc_file in self.mrc_files:
            try:
                # Reset sliders
                self.sliders[mrc_file]['level'].setValue(0)
                self.sliders[mrc_file]['transparency'].setValue(0)
                self.sliders[mrc_file]['show'].setChecked(True)

                # Reset PyMOL settings
                cmd.isomesh(f"{mrc_file}_mesh", mrc_file, 0.0)
                cmd.set("transparency", 0.0, f"{mrc_file}_mesh")
                cmd.show("mesh", f"{mrc_file}_mesh")

            except Exception as e:
                print(f"Error resetting {mrc_file}: {str(e)}")


class SmifferWorker(QtCore.QThread):
    """Worker thread for running Smiffer process"""
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(str)
    output = QtCore.pyqtSignal(str)

    def __init__(self, command, working_dir):
        super().__init__()
        self.command = command
        self.working_dir = working_dir
        self.process = None
        self.should_stop = False

    def run(self):
        """Run the smiffer command"""
        try:
            self.process = subprocess.Popen(
                self.command,
                cwd=self.working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            # Read output line by line
            for line in iter(self.process.stdout.readline, ''):
                if self.should_stop:
                    break
                if line.strip():
                    self.output.emit(line.strip())

            self.process.wait()

            if self.process.returncode == 0 and not self.should_stop:
                self.output.emit("Smiffer calculation completed successfully!")
            elif self.should_stop:
                self.output.emit("Smiffer calculation stopped by user.")
            else:
                self.error.emit(f"Smiffer failed with return code: {self.process.returncode}")

        except Exception as e:
            self.error.emit(f"Error running Smiffer: {str(e)}")
        finally:
            self.finished.emit()

    def stop(self):
        """Stop the running process"""
        self.should_stop = True
        if self.process:
            self.process.terminate()
            self.process.wait()


# Plugin initialization and registration
plugin_instance = None

def __init_plugin__(app=None):
    """Initialize the PyMOL plugin"""
    global plugin_instance
    plugin_instance = SmifferPyMOLPlugin()

    # Add menu entry
    from pymol.plugins import addmenuitemqt
    addmenuitemqt('Smiffer Tool', plugin_instance.show_gui)


def smiffer_gui():
    """Command line function to show the Smiffer GUI"""
    global plugin_instance
    if plugin_instance is None:
        plugin_instance = SmifferPyMOLPlugin()
    plugin_instance.show_gui()


# Register the command
cmd.extend('smiffer_gui', smiffer_gui)
