from chimerax.ui import MainToolWindow
from chimerax.core.tools import ToolInstance
from Qt.QtWidgets import (QVBoxLayout, QPushButton, QLabel, QListWidget, QHBoxLayout,
                         QInputDialog, QMessageBox, QFileDialog, QLineEdit, QComboBox,
                         QCheckBox, QSpinBox, QDoubleSpinBox, QTextEdit, QProgressBar,
                         QGroupBox, QGridLayout, QFormLayout, QTabWidget, QWidget,
                         QScrollArea, QSplitter)
from Qt.QtCore import Qt, QThread, QTimer
try:
    from Qt.QtCore import pyqtSignal
except ImportError:
    try:
        from Qt.QtCore import Signal as pyqtSignal
    except ImportError:
        from PyQt5.QtCore import pyqtSignal
import os
import json
import subprocess
import sys
import threading
import os.path

class SmifferTool(ToolInstance):

    SESSION_ENDURING = True
    SESSION_SAVE = True
    help = "help:user/tools/smiffertool.html"

    def __init__(self, session, tool_name):
        ToolInstance.__init__(self, session, tool_name)
        self.display_name = "Smiffer Tool"

        # Initialize smiffer paths
        self.smiffer_path = os.path.join(os.path.dirname(__file__), "volgrids-main", "run", "smiffer.py")
        self.path_output_dir = None
        self.current_process = None
        self.worker_thread = None

        from chimerax.ui import MainToolWindow
        self.tool_window = MainToolWindow(self)
        self.tool_window.fill_context_menu = self.fill_context_menu
        self._build_ui()

    def fill_context_menu(self, menu, x, y):

        from Qt.QtGui import QAction
        clear_action = QAction("Clear", menu)
        clear_action.triggered.connect(lambda *args: self.line_edit.clear())
        menu.addAction(clear_action)

    def _build_ui(self):
        # Create main splitter for layout
        main_splitter = QSplitter(Qt.Vertical)

        # Create tab widget for different sections
        tabs = QTabWidget()

        # Basic Settings Tab
        basic_tab = QWidget()
        basic_layout = QVBoxLayout(basic_tab)

        # Input file section
        input_group = QGroupBox("Input Structure")
        input_layout = QFormLayout(input_group)

        self.input_file_edit = QLineEdit()
        self.first_files_folder = []
        input_browse_btn = QPushButton("Browse")
        input_load_current_structure = QPushButton("Load Currently displayed structure")
        input_browse_btn.clicked.connect(self.browse_input_file)
        input_load_current_structure.clicked.connect(self.load_current_structure)
        input_file_layout = QHBoxLayout()
        input_file_layout.addWidget(self.input_file_edit)
        input_file_layout.addWidget(input_browse_btn)
        input_file_layout.addWidget(input_load_current_structure)
        input_layout.addRow("Structure File:", input_file_layout)

        # Mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["prot", "rna"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        input_layout.addRow("Mode:", self.mode_combo)

        # Output directory
        self.output_dir_edit = QLineEdit()
        output_browse_btn = QPushButton("Browse")
        output_browse_btn.clicked.connect(self.browse_output_dir)
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(output_browse_btn)
        input_layout.addRow("Output Directory:", output_dir_layout)

        basic_layout.addWidget(input_group)

        # Advanced Settings Tab
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout(advanced_tab)

        # Trajectory section
        traj_group = QGroupBox("Trajectory Options")
        traj_layout = QFormLayout(traj_group)

        self.trajectory_edit = QLineEdit()
        traj_browse_btn = QPushButton("Browse")
        traj_browse_btn.clicked.connect(self.browse_trajectory)
        traj_layout_h = QHBoxLayout()
        traj_layout_h.addWidget(self.trajectory_edit)
        traj_layout_h.addWidget(traj_browse_btn)
        traj_layout.addRow("Trajectory File:", traj_layout_h)

        advanced_layout.addWidget(traj_group)

        # APBS section
        apbs_group = QGroupBox("APBS Options")
        apbs_layout = QFormLayout(apbs_group)

        self.apbs_file_edit = QLineEdit()
        apbs_browse_btn = QPushButton("Browse")
        apbs_browse_btn.clicked.connect(self.browse_apbs_file)
        apbs_layout_h = QHBoxLayout()
        apbs_layout_h.addWidget(self.apbs_file_edit)
        apbs_layout_h.addWidget(apbs_browse_btn)
        apbs_layout.addRow("APBS File (.dx):", apbs_layout_h)

        self.run_apbs_checkbox = QCheckBox("Run APBS automatically")
        self.run_apbs_checkbox.setChecked(True)
        apbs_layout.addRow("", self.run_apbs_checkbox)

        advanced_layout.addWidget(apbs_group)

        # Pocket sphere section
        pocket_group = QGroupBox("Pocket Sphere Mode")
        pocket_layout = QFormLayout(pocket_group)

        self.pocket_sphere_checkbox = QCheckBox("Enable Pocket Sphere Mode")
        self.pocket_sphere_checkbox.toggled.connect(self.toggle_pocket_sphere)
        pocket_layout.addRow("", self.pocket_sphere_checkbox)

        self.sphere_radius_spin = QDoubleSpinBox()
        self.sphere_radius_spin.setRange(0.1, 100.0)
        self.sphere_radius_spin.setValue(10.0)
        self.sphere_radius_spin.setEnabled(False)
        pocket_layout.addRow("Radius (Å):", self.sphere_radius_spin)

        sphere_coords_layout = QHBoxLayout()
        self.sphere_x_spin = QDoubleSpinBox()
        self.sphere_x_spin.setRange(-999.0, 999.0)
        self.sphere_x_spin.setEnabled(False)
        self.sphere_y_spin = QDoubleSpinBox()
        self.sphere_y_spin.setRange(-999.0, 999.0)
        self.sphere_y_spin.setEnabled(False)
        self.sphere_z_spin = QDoubleSpinBox()
        self.sphere_z_spin.setRange(-999.0, 999.0)
        self.sphere_z_spin.setEnabled(False)
        sphere_coords_layout.addWidget(QLabel("X:"))
        sphere_coords_layout.addWidget(self.sphere_x_spin)
        sphere_coords_layout.addWidget(QLabel("Y:"))
        sphere_coords_layout.addWidget(self.sphere_y_spin)
        sphere_coords_layout.addWidget(QLabel("Z:"))
        sphere_coords_layout.addWidget(self.sphere_z_spin)
        pocket_layout.addRow("Center:", sphere_coords_layout)

        advanced_layout.addWidget(pocket_group)

        # Chemical table section
        chem_group = QGroupBox("Chemical Table")
        chem_layout = QFormLayout(chem_group)

        self.chem_table_edit = QLineEdit()
        chem_browse_btn = QPushButton("Browse")
        chem_browse_btn.clicked.connect(self.browse_chem_table)
        chem_layout_h = QHBoxLayout()
        chem_layout_h.addWidget(self.chem_table_edit)
        chem_layout_h.addWidget(chem_browse_btn)
        chem_layout.addRow("Table File (.chem):", chem_layout_h)

        advanced_layout.addWidget(chem_group)

        # Configuration section
        config_group = QGroupBox("Configuration")
        config_layout = QFormLayout(config_group)

        self.config_file_edit = QLineEdit()
        config_browse_btn = QPushButton("Browse")
        config_browse_btn.clicked.connect(self.browse_config_file)
        config_layout_h = QHBoxLayout()
        config_layout_h.addWidget(self.config_file_edit)
        config_layout_h.addWidget(config_browse_btn)
        config_layout.addRow("Config File (.ini):", config_layout_h)

        advanced_layout.addWidget(config_group)

        # Add tabs
        tabs.addTab(basic_tab, "Basic Settings")
        tabs.addTab(advanced_tab, "Advanced Settings")

        # Control buttons
        control_layout = QHBoxLayout()

        self.run_button = QPushButton("Run Smiffer")
        self.run_button.clicked.connect(self.run_smiffer)
        self.run_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_smiffer)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; }")

        self.load_results_button = QPushButton("Load Results")
        self.load_results_button.clicked.connect(self.load_results)
        self.load_results_button.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 8px; }")

        control_layout.addWidget(self.run_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.load_results_button)
        control_layout.addStretch()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        # Log area
        log_group = QGroupBox("Progress Log")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("QTextEdit { color: #f5f5f5; background-color: #000000; font-family: monospace; }")
        log_layout.addWidget(self.log_text)

        # Add everything to main splitter
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.addWidget(tabs)
        top_layout.addLayout(control_layout)
        top_layout.addWidget(self.progress_bar)

        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(log_group)
        main_splitter.setStretchFactor(0, 3)
        main_splitter.setStretchFactor(1, 1)

        self.tool_window.ui_area.setLayout(QVBoxLayout())
        self.tool_window.ui_area.layout().addWidget(main_splitter)
        self.tool_window.manage(None)

    def log_message(self, message):
        """Add a message to the log"""
        self.log_text.append(f"[{self._get_timestamp()}] {message}")
        self.log_text.ensureCursorVisible()

    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")

    def browse_input_file(self):
        """Browse for input structure file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.tool_window.ui_area,
            "Select Structure File",
            "",
            "Structure Files (*.pdb *.cif *.mmcif);;All Files (*)"
        )
        if file_path:
            self.input_file_edit.setText(file_path)
            # Auto-set output directory to input file directory
            if not self.output_dir_edit.text():
                self.output_dir_edit.setText(os.path.dirname(file_path))

    def load_current_structure(self):
        """Load actual 3d structure displayed"""
        try:
            from chimerax.atomic import AtomicStructure
            structures = self.session.models.list(type=AtomicStructure)
            print(structures)
            if not structures:
                QMessageBox.information(None, "Info", "No structures loaded to save")
                return
            for structure in structures:
                print(dir(structure))
            if hasattr(structure, 'filename') and structure.filename:
                print(structure.filename)
                print(os.path.splitext(os.path.basename(structure.filename))[0])
                self.input_file_edit.setText(structure.filename)
                self.output_dir_edit.setText(os.path.dirname(structure.filename))


        except Exception as e:
            self.session.logger.error(f"Error {e}")




    def browse_output_dir(self):
        """Browse for output directory"""
        dir_path = QFileDialog.getExistingDirectory(
            self.tool_window.ui_area,
            "Select Output Directory"
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)

    def browse_trajectory(self):
        """Browse for trajectory file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.tool_window.ui_area,
            "Select Trajectory File",
            "",
            "Trajectory Files (*.xtc *.trr *.dcd);;All Files (*)"
        )
        if file_path:
            self.trajectory_edit.setText(file_path)

    def browse_apbs_file(self):
        """Browse for APBS file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.tool_window.ui_area,
            "Select APBS File",
            "",
            "APBS Files (*.dx);;All Files (*)"
        )
        if file_path:
            self.apbs_file_edit.setText(file_path)

    def browse_chem_table(self):
        """Browse for chemical table file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.tool_window.ui_area,
            "Select Chemical Table File",
            "",
            "Chemical Table Files (*.chem);;All Files (*)"
        )
        if file_path:
            self.chem_table_edit.setText(file_path)

    def browse_config_file(self):
        """Browse for configuration file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self.tool_window.ui_area,
            "Select Configuration File",
            "",
            "Configuration Files (*.ini);;All Files (*)"
        )
        if file_path:
            self.config_file_edit.setText(file_path)

    def on_mode_changed(self, mode):
        """Handle mode change"""
        # Enable/disable ligand-specific options
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

    def build_smiffer_params(self):
        """Build smiffer parameters from UI inputs for direct library use"""
        if not self.input_file_edit.text():
            raise ValueError("Please select an input structure file")

        # Prepare parameters for direct AppSmiffer instantiation
        params = {}
        
        # Mode (first positional argument)
        mode = self.mode_combo.currentText()
        
        # Input file (second positional argument) 
        input_file = self.input_file_edit.text()
        
        # Output directory
        if self.output_dir_edit.text():
            params['output'] = [self.output_dir_edit.text()]
            self.path_output_dir = self.output_dir_edit.text()
        else:
            self.path_output_dir = os.path.dirname(self.input_file_edit.text())

        # Trajectory
        if self.trajectory_edit.text():
            params['traj'] = [self.trajectory_edit.text()]

        # APBS file
        if self.apbs_file_edit.text():
            params['apbs'] = [self.apbs_file_edit.text()]

        # Pocket sphere
        if self.pocket_sphere_checkbox.isChecked():
            params['pocket'] = [
                str(self.sphere_radius_spin.value()),
                str(self.sphere_x_spin.value()),
                str(self.sphere_y_spin.value()),
                str(self.sphere_z_spin.value())
            ]

        # Chemical table
        if self.chem_table_edit.text():
            params['table'] = [self.chem_table_edit.text()]

        # Config file
        if self.config_file_edit.text():
            params['config'] = [self.config_file_edit.text()]

        return [mode, input_file], params

    def run_apbs_preparation(self, structure_file):
        """Run APBS preparation commands"""
        try:
            base_name = os.path.splitext(os.path.basename(structure_file))[0]
            output_dir = self.output_dir_edit.text() or os.path.dirname(structure_file)

            # Generate .pqr file
            pqr_file = os.path.join(output_dir, f"{base_name}.pqr")
            input_file = os.path.join(output_dir, "INPUT.in")

            # pdb2pqr command
            pdb2pqr_cmd = [
                "pdb2pqr", "--ff=PARSE", "--titration-state-method=propka",
                "--with-ph=7", f"--apbs-input={input_file}", "--drop-water",
                structure_file, pqr_file
            ]

            self.log_message(f"Running pdb2pqr: {' '.join(pdb2pqr_cmd)}")

            result = subprocess.run(pdb2pqr_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                self.log_message(f"pdb2pqr failed: {result.stderr}")
                return None

            self.log_message("pdb2pqr completed successfully")

            # Run APBS
            apbs_cmd = ["apbs", input_file]
            self.log_message(f"Running APBS: {' '.join(apbs_cmd)}")

            result = subprocess.run(apbs_cmd, capture_output=True, text=True, cwd=output_dir)
            if result.returncode != 0:
                self.log_message(f"APBS failed: {result.stderr}")
                return None

            self.log_message("APBS completed successfully")

            # Find the .dx file
            dx_files = [f for f in os.listdir(output_dir) if f.endswith('.dx')]
            if dx_files:
                return os.path.join(output_dir, dx_files[0])

            return None

        except Exception as e:
            self.log_message(f"Error in APBS preparation: {str(e)}")
            return None

    def run_smiffer(self):
        """Run the smiffer calculation"""
        try:
            # Validate inputs
            if not self.input_file_edit.text():
                QMessageBox.warning(None, "Error", "Please select an input structure file")
                return

            if not os.path.exists(self.input_file_edit.text()):
                QMessageBox.warning(None, "Error", "Input structure file does not exist")
                return

            # Run APBS preparation if needed
            if self.run_apbs_checkbox.isChecked() and not self.apbs_file_edit.text():
                self.log_message("Running APBS preparation...")
                dx_file = self.run_apbs_preparation(self.input_file_edit.text())
                if dx_file:
                    self.apbs_file_edit.setText(dx_file)
                    self.log_message(f"APBS preparation completed: {dx_file}")
                else:
                    self.log_message("APBS preparation failed, continuing without APBS")

            # Build smiffer parameters
            args, kwargs = self.build_smiffer_params()

            list_of_files = os.listdir(self.path_output_dir)
            self.first_files_folder = list_of_files

            self.log_message(f"Running smiffer with args: {args}")
            self.log_message(f"Running smiffer with kwargs: {kwargs}")

            # Create and start worker thread
            self.worker_thread = SmifferWorker(args, kwargs)
            self.worker_thread.finished.connect(self.on_smiffer_finished)
            self.worker_thread.error.connect(self.on_smiffer_error)
            self.worker_thread.output.connect(self.log_message)
            self.worker_thread.progress.connect(self.on_progress_update)

            # Update UI
            self.run_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress

            self.worker_thread.start()

        except Exception as e:
            self.log_message(f"Error starting Smiffer: {str(e)}")
            QMessageBox.warning(None, "Error", f"Failed to start Smiffer: {str(e)}")

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

    def on_smiffer_error(self, error_msg):
        """Handle Smiffer error"""
        self.log_message(f"Smiffer error: {error_msg}")
        QMessageBox.warning(None, "Smiffer Error", error_msg)

    def on_progress_update(self, progress_msg):
        """Handle progress updates"""
        # Could update progress bar here if needed
        pass

    def load_results(self):
        """Load Smiffer results into ChimeraX"""
        try:
            output_dir = self.output_dir_edit.text()
            if not output_dir:
                output_dir = os.path.dirname(self.input_file_edit.text()) if self.input_file_edit.text() else ""

            if not output_dir or not os.path.exists(output_dir):
                QMessageBox.warning(None, "Error", "Output directory not found")
                return

            # Find result files
            result_files = []
            files_in_folder_before = self.first_files_folder
            for ext in ['.cmap', '.h5', '.dx', '.ccp4', '.mrc']:
                files = [f for f in os.listdir(output_dir) if f.endswith(ext)]
                new_files = [x for x in files if x not in files_in_folder_before]
                result_files.extend([os.path.join(output_dir, f) for f in new_files])

            if not result_files:
                QMessageBox.information(None, "Info", "No result files found in output directory")
                return

            # Load files into ChimeraX
            from chimerax.core.commands import run
            loaded_count = 0

            for file_path in result_files:
                try:
                    self.log_message(f"Loading {file_path}")
                    run(self.session, f"open \"{file_path}\"")
                    loaded_count += 1
                except Exception as e:
                    self.log_message(f"Failed to load {file_path}: {str(e)}")

            self.log_message(f"Loaded {loaded_count} result files")

            # Auto-color the loaded volumes
            self.color_loaded_volumes()

            QMessageBox.information(None, "Success", f"Loaded {loaded_count} result files")

        except Exception as e:
            self.log_message(f"Error loading results: {str(e)}")
            QMessageBox.warning(None, "Error", f"Failed to load results: {str(e)}")

    def color_loaded_volumes(self):
        """Auto-color loaded volumes based on their names"""
        try:
            from chimerax.map import Volume
            from chimerax.core.commands import run

            # Color mapping
            color_map = {
                'hydrophobic': "#FFFF00",     # Yellow
                'hydrophilic': "#4DD9FF",     # Light Blue
                'hbacceptors': "#FF8000",     # Orange
                'hbdonors': "#B300FF",        # Purple
                'stacking': "#00FF00",        # Green
                'apbs': "#0000FF"             # Blue
            }

            volumes = self.session.models.list(type=Volume)
            colored_count = 0

            for volume in volumes:
                if hasattr(volume, 'data') and hasattr(volume.data, 'path'):
                    filename = os.path.basename(volume.data.path)
                    base_name = os.path.splitext(filename)[0]

                    # Check for field type in filename
                    for field_type, color in color_map.items():
                        if field_type in base_name.lower():
                            run(self.session, f"color #{volume.id_string} {color}")
                            self.log_message(f"Colored {filename} as {field_type}: {color}")
                            colored_count += 1
                            break

            if colored_count > 0:
                self.log_message(f"Auto-colored {colored_count} volumes")

        except Exception as e:
            self.log_message(f"Error auto-coloring volumes: {str(e)}")

class SmifferWorker(QThread):
    """Worker thread for running Smiffer using direct library interface"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    output = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, args, kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs
        self.should_stop = False

    def run(self):
        """Run smiffer using direct library interface"""
        try:
            self.output.emit(f"Starting smiffer with args: {self.args}")
            self.output.emit(f"Starting smiffer with kwargs: {self.kwargs}")
            
            # Add volgrids to Python path
            volgrids_path = os.path.join(os.path.dirname(__file__), "volgrids-main", "src")
            if volgrids_path not in sys.path:
                sys.path.insert(0, volgrids_path)
            
            # Import volgrids smiffer
            import warnings
            warnings.filterwarnings("ignore", module="MDAnalysis.*")
            
            import volgrids.smiffer as sm
            
            self.output.emit("Volgrids smiffer imported successfully")
            
            # Create AppSmiffer instance with parameters
            self.output.emit("Creating AppSmiffer instance...")
            app = sm.AppSmiffer(*self.args, **self.kwargs)
            
            self.output.emit("AppSmiffer instance created successfully")
            self.output.emit("Starting smiffer calculation...")
            
            # Run the smiffer calculation
            app.run()
            
            if not self.should_stop:
                self.output.emit("Smiffer calculation completed successfully!")
            else:
                self.output.emit("Smiffer calculation stopped by user.")

        except Exception as e:
            import traceback
            error_msg = f"Error running Smiffer: {str(e)}\n{traceback.format_exc()}"
            self.error.emit(error_msg)
        finally:
            self.finished.emit()

    def stop(self):
        """Stop the running process"""
        self.should_stop = True
        # Note: The smiffer library doesn't have a built-in stop mechanism,
        # so we can only set the flag and hope the calculation finishes soon
