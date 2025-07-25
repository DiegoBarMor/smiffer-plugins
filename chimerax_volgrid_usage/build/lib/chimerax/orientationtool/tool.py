from chimerax.ui import MainToolWindow
from chimerax.core.tools import ToolInstance
from Qt.QtWidgets import QVBoxLayout, QPushButton, QLabel, QListWidget, QHBoxLayout, QInputDialog, QMessageBox
from Qt.QtCore import Qt
import os
import json

class OrientationTool(ToolInstance):

    SESSION_ENDURING = True
    SESSION_SAVE=True
    help = "help:user/tools/orientationtool.html"

    def __init__(self, session, tool_name):
        ToolInstance.__init__(self, session, tool_name)
        self.display_name = "Orientation Tool"

        # Initialize orientation storage
        self.orientations_file = os.path.expanduser("~/.chimerax_orientations.json")
        self.orientations = self._load_orientations()

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
        # Create main layout
        layout = QVBoxLayout()

        # Add title label
        #title_label = QLabel("Orientation Tool")
        #title_label.setAlignment(Qt.AlignCenter)
        #layout.addWidget(title_label)

        # Save orientation button
        self.save_orientation_button = QPushButton("Save Current Orientation")
        self.save_orientation_button.clicked.connect(self.save_orientation)
        layout.addWidget(self.save_orientation_button)

        # Orientation list and load button
        orientation_layout = QHBoxLayout()
        self.orientation_list = QListWidget()
        self.orientation_list.setMaximumHeight(100)
        self._update_orientation_list()
        orientation_layout.addWidget(self.orientation_list)

        self.load_orientation_button = QPushButton("Load Selected")
        self.load_orientation_button.clicked.connect(self.load_orientation)
        orientation_layout.addWidget(self.load_orientation_button)

        self.delete_orientation_button = QPushButton("Delete Selected")
        self.delete_orientation_button.clicked.connect(self.delete_orientation)
        orientation_layout.addWidget(self.delete_orientation_button)

        layout.addLayout(orientation_layout)
        """
        # Save to CXS button
        self.save_cxs_button = QPushButton("Save to CXS")
        self.save_cxs_button.clicked.connect(self.save_to_cxs)
        layout.addWidget(self.save_cxs_button)
        """

        # Color fields button
        self.color_fields_button = QPushButton("Color Fields")
        self.color_fields_button.clicked.connect(self.color_fields)
        layout.addWidget(self.color_fields_button)

        """
        # Test highlighted models button
        self.test_highlighted_button = QPushButton("Test Highlighted Models")
        self.test_highlighted_button.clicked.connect(self.test_highlighted_models)
        layout.addWidget(self.test_highlighted_button)
        """

        # Color buttons layout
        color_buttons_layout = QHBoxLayout()

        # Define color buttons
        self.color_buttons = {
            'APBS': ("#0000FF", self.color_apbs),
            'APBS-': ("#FF0000", self.color_apbs_minus),
            'Hydrophobic': ("#FFFF00", self.color_hydrophobic),
            'Hydrophilic': ("#4DD9FF", self.color_hydrophilic),
            'H-B Acceptor': ("#FF8000", self.color_h_b_acceptor),
            'H-B Donor': ("#B300FF", self.color_h_b_donor),
            'Pi Stacking': ("#00FF00", self.color_pi_stacking)
        }

        # Create color buttons
        for button_text, (color, callback) in self.color_buttons.items():
            button = QPushButton(button_text)
            button.setStyleSheet(f"background-color: {color}; color: white; font-weight: bold;")
            button.clicked.connect(callback)
            color_buttons_layout.addWidget(button)

        layout.addLayout(color_buttons_layout)

        self.tool_window.ui_area.setLayout(layout)
        self.tool_window.manage(None)

    def _load_orientations(self):
        """Load saved orientations from file"""
        if os.path.exists(self.orientations_file):
            try:
                with open(self.orientations_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_orientations(self):
        """Save orientations to file"""
        with open(self.orientations_file, 'w') as f:
            json.dump(self.orientations, f, indent=2)

    def _update_orientation_list(self):
        """Update the orientation list widget"""
        self.orientation_list.clear()
        for name in self.orientations.keys():
            self.orientation_list.addItem(name)

    def _get_current_orientation(self):
        """Get current camera orientation and position"""
        try:
            # Get the camera position matrix directly
            camera = self.session.main_view.camera
            matrix = camera.position.matrix

            # Convert to the format expected by view matrix command
            # Format: m00,m01,m02,m03,m10,m11,m12,m13,m20,m21,m22,m23
            matrix_values = []
            print(matrix)
            for i in range(3):
                for j in range(4):
                    matrix_values.append(str(matrix[i, j]))

            return ','.join(matrix_values)

        except Exception as e:
            self.session.logger.error(f"Error getting current orientation: {e}")
            return None

    def _get_structure_name(self):
        """Get name for current structure based on loaded files"""
        from chimerax.atomic import AtomicStructure
        structures = self.session.models.list(type=AtomicStructure)
        if structures:
            # Use the first structure's name or filename
            structure = structures[0]
            if hasattr(structure, 'filename') and structure.filename:
                return os.path.splitext(os.path.basename(structure.filename))[0]
            elif structure.name:
                return structure.name
        return "unknown"

    def save_orientation(self):
        """Save current orientation with automatic naming"""
        try:
            base_name = self._get_structure_name()

            # Find unique name
            counter = 1
            name = base_name
            while name in self.orientations:
                name = f"{base_name}_{counter}"
                counter += 1

            # Get current orientation matrix
            matrix_values = self._get_current_orientation()
            if not matrix_values:
                QMessageBox.warning(None, "Error", "Could not get current orientation")
                return

            # Store the matrix values
            self.orientations[name] = matrix_values
            self._save_orientations()
            self._update_orientation_list()

            self.session.logger.info(f"Saved orientation as '{name}'")

        except Exception as e:
            self.session.logger.error(f"Error saving orientation: {e}")
            QMessageBox.warning(None, "Error", f"Failed to save orientation: {e}")

    def load_orientation(self):
        """Load selected orientation"""
        current_item = self.orientation_list.currentItem()
        if not current_item:
            QMessageBox.information(None, "Info", "Please select an orientation to load")
            return

        orientation_name = current_item.text()
        if orientation_name not in self.orientations:
            QMessageBox.warning(None, "Error", "Selected orientation not found")
            return

        try:
            # Get stored matrix values
            matrix_values = self.orientations[orientation_name]
            print(matrix_values)
            """
            # Convert back to matrix format
            from chimerax.geometry import Place
            import numpy as np

            # Parse the comma-separated values
            values = [float(v) for v in matrix_values.split(',')]

            # Reconstruct the 3x4 matrix
            matrix = np.array(values).reshape(3, 4)
            print(matrix)

            # Create a 4x4 transformation matrix
            transform_matrix = np.eye(4)
            transform_matrix[:3, :4] = matrix

            # Set the camera position directly
            camera = self.session.main_view.camera
            camera.position = Place(transform_matrix)
            """
            from chimerax.core.commands import run
            values = [str(v) for v in matrix_values.split(',')]
            command_values = ' '.join(values)
            print(command_values)
            run(self.session, f"view matrix camera {matrix_values}")

            self.session.logger.info(f"Loaded orientation '{orientation_name}'")

        except Exception as e:
            self.session.logger.error(f"Error loading orientation: {e}")
            QMessageBox.warning(None, "Error", f"Failed to load orientation: {e}")

    def delete_orientation(self):
        """Delete selected orientation"""
        current_item = self.orientation_list.currentItem()
        if not current_item:
            QMessageBox.information(None, "Info", "Please select an orientation to delete")
            return

        orientation_name = current_item.text()
        if orientation_name not in self.orientations:
            QMessageBox.warning(None, "Error", "Selected orientation not found")
            return

        # Confirm deletion
        reply = QMessageBox.question(None, "Confirm Delete",
                                   f"Are you sure you want to delete the orientation '{orientation_name}'?",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                # Remove from dictionary
                del self.orientations[orientation_name]
                # Save to file
                self._save_orientations()
                # Update UI
                self._update_orientation_list()

                self.session.logger.info(f"Deleted orientation '{orientation_name}'")

            except Exception as e:
                self.session.logger.error(f"Error deleting orientation: {e}")
                QMessageBox.warning(None, "Error", f"Failed to delete orientation: {e}")

    def save_to_cxs(self):
        """Save current session to CXS file"""
        try:
            from chimerax.atomic import AtomicStructure
            structures = self.session.models.list(type=AtomicStructure)

            if not structures:
                QMessageBox.information(None, "Info", "No structures loaded to save")
                return

            # Get structure name for filename
            base_name = self._get_structure_name()
            filename = f"{base_name}.cxs"

            # Use ChimeraX save command
            from chimerax.core.commands import run
            run(self.session, f"save {filename}")

            self.session.logger.info(f"Saved session to {filename}")
            QMessageBox.information(None, "Success", f"Session saved to {filename}")

        except Exception as e:
            self.session.logger.error(f"Error saving to CXS: {e}")
            QMessageBox.warning(None, "Error", f"Failed to save to CXS: {e}")

    def color_fields(self):
        """Color fields based on their type"""
        try:
            # Color mapping for different field types
            color_map = {
                'apbs': "#0000FF",           # Blue
                'hydrophobic': "#FF0000",     # Red
                'hydrophilic': "#FFFF00",     # Yellow
                'h_b_acceptor': "#4DD9FF",    # Light Blue
                'h_b_donor': "#FF8000",       # Orange
                'pi_stacking': "#B300FF"      # Violet
            }
            color_map_cmap = {
                'hydrophobic': "#FF0000",     # Red
                'hydrophilic': "#FFFF00",     # Yellow
                'hbacceptors': "#4DD9FF",    # Light Blue
                'hbdonors': "#FF8000",       # Orange
                'stacking': "#B300FF"      # Violet
            }


            # Get all loaded models
            from chimerax.map import Volume
            volumes = self.session.models.list(type=Volume)
            from chimerax.core.commands import run
            from chimerax.atomic import AtomicStructure
            structures = self.session.models.list(type=AtomicStructure)
            colored_count = 0
            run(self.session, f"display")
            run(self.session, "wait 10")
            for volume in volumes:
                # Get the filename and extract field type
                if hasattr(volume, 'data') and hasattr(volume.data, 'path'):
                    filename = os.path.basename(volume.data.path)
                    print(f"Filename = {filename}")
                    print(f"Type Volume = {type(volume)}")

                    # Handle .cmap files - these contain multiple maps internally
                    if filename.endswith('.cmap'):
                        # Get child models (the individual maps within the .cmap)
                        child_models = volume.child_models()
                        all_models = volume.all_models()
                        print(all_models)
                        print(len(all_models))
                        for i in all_models:
                            print(getattr(i, 'name', 'unnamed'))

                        for i, child_volume in enumerate(all_models):
                            print(child_volume.id_string)
                            current_child_name = getattr(child_volume, 'name', 'unnamed')
                            if current_child_name != "surface":
                                color = color_map_cmap.get(current_child_name.split(".")[-1], "#FFFFFF")
                                run(self.session, f"display #{child_volume.id_string}")
                                run(self.session, f"color #{child_volume.id_string} {color}")
                                colored_count += 1
                                self.session.logger.info(f"Colored {child_volume.name} map as: {color}")

                        continue

                    # Filter for dx, ccp4, and h5 formats (existing logic)
                    if not filename.endswith(('.dx', '.ccp4', '.h5')):
                        continue

                    # Extract field type from filename
                    # Remove extension and get part after last underscore
                    base_name = os.path.splitext(filename)[0]
                    print(base_name)
                    parts = base_name.split('_')
                    if len(parts) >= 2:
                        field_type = parts[-1]
                        # Handle special cases for APBS positive/negative
                        if field_type == 'apbs':
                            # You might need to detect positive/negative from filename or data
                            # For now, using default blue for APBS
                            color = color_map.get('apbs', "#FFFFFF")
                        else:
                            color = color_map.get(field_type, "#FFFFFF")

                        # Apply color to the volume
                        colored_count += 1
                        run(self.session, f"color #{volume.id_string} {color}")
                        self.session.logger.info(f"Colored {filename} as {field_type}: {color}")

            self.session.logger.info(f"Total volumes colored: {colored_count}")

        except Exception as e:
            self.session.logger.error(f"Error in color_fields: {str(e)}")
            QMessageBox.warning(None, "Error", f"Failed to color fields: {e}")

        if colored_count > 0:
            self.session.logger.info(f"Colored {colored_count} fields")
            QMessageBox.information(None, "Success", f"Colored {colored_count} fields based on their types")
        else:
            QMessageBox.information(None, "Info", "No compatible volume files found to color")

    def get_highlighted_models(self):
        """Get the currently highlighted models from the model panel"""
        try:
            # Find the model panel tool by its display name
            model_panel = None
            for tool in self.session.tools.list():
                print(tool)
                print(tool.display_name)
                if tool.display_name == "Models":
                    model_panel = tool
                    break

            if model_panel is None:
                print("model_panel not found")
                return []

            # Get selected items from the tree
            selected_items = model_panel.tree.selectedItems()
            print(selected_items)

            if not selected_items:
                return []

            # Convert selected items to model objects
            highlighted_models = [model_panel.models[model_panel._items.index(item)]
                                 for item in selected_items]

            return highlighted_models

        except Exception as e:
            self.session.logger.error(f"Error getting highlighted models: {e}")
            return []

    def get_highlighted_models_concise(self):
        """Get highlighted models using the exact logic from model panel buttons"""
        try:
            # Find the model panel tool by its display name
            mp = None
            for tool in self.session.tools.list():
                if tool.display_name == "Models":
                    mp = tool
                    break

            if mp is None:
                return []

            return [mp.models[row] for row in [mp._items.index(i)
                                              for i in mp.tree.selectedItems()]] or []
        except Exception as e:
            self.session.logger.error(f"Error getting highlighted models: {e}")
            return []

    def test_highlighted_models(self):
        """Test function to display highlighted models from the model panel"""
        try:
            highlighted_models = self.get_highlighted_models()

            if not highlighted_models:
                QMessageBox.information(None, "Info", "No models are highlighted in the model panel")
                return

            # Display information about highlighted models
            info_text = f"Found {len(highlighted_models)} highlighted models:\n\n"
            for i, model in enumerate(highlighted_models, 1):
                info_text += f"{i}. ID: {model.id_string}, Name: {getattr(model, 'name', 'unnamed')}, Type: {type(model).__name__}\n"

            QMessageBox.information(None, "Highlighted Models", info_text)

            # Also log to ChimeraX logger
            self.session.logger.info(f"Highlighted models: {[m.id_string for m in highlighted_models]}")

        except Exception as e:
            self.session.logger.error(f"Error testing highlighted models: {e}")
            QMessageBox.warning(None, "Error", f"Failed to get highlighted models: {e}")

    def _apply_color_to_selected(self, color_hex):
        """Apply color to currently selected structures or volumes"""
        try:
            from chimerax.core.commands import run
            from chimerax.atomic import AtomicStructure
            from chimerax.map import Volume

            # Get all models
            #run(self.session, f"display")
            highlighted_models = self.get_highlighted_models()
            for i, model in enumerate(highlighted_models, 1):
                run(self.session, f"display #{model.id_string}")
                run(self.session, f"color #{model.id_string} {color_hex}")
                self.session.logger.info(f"Coloring models: {i}. ID: {model.id_string}, Name: {getattr(model, 'name', 'unnamed')}, Type: {type(model).__name__} in {color_hex}")
            if not highlighted_models:
                QMessageBox.information(None, "Info", "No structures or volumes found to color")

            """
            all_models = self.session.models.list()
            selected_count = 0

            # Color selected structures
            structures = self.session.models.list(type=AtomicStructure)
            print(dir(structures))
            to_color = []
            for structure in structures:
                if structure.child_models():
                    for child in structure.child_models():
                        if child.highlighted:
                            to_color.append(child.id_string)
                            selected_count += 1
                else:
                    if structure.highlighted:
                        to_color.append(structure.id_string)
                        selected_count += 1


            # Color selected volumes
            volumes = self.session.models.list(type=Volume)
            for volume in volumes:
                if volume.child_models():
                    for child in volume.child_models():
                        #print(child.id_string)
                        #print(child.get_selected())
                        #print(child.highlighted)
                        #if hasattr(child, 'selected') and child.selected:
                        if child.highlighted:
                            to_color.append(child.id_string)
                            selected_count += 1
                else:
                    if volume.highlighted:
                        to_color.append(volume.id_string)
                        selected_count += 1

            if not to_color:
                print("Nothing selected")
            else:
                for object_to_color in to_color:
                    run(self.session, f"color #{object_to_color} {color_hex}")


            # If nothing selected, color all structures and volumes
            if selected_count == 0:
                for structure in structures:
                    run(self.session, f"color #{structure.id_string} {color_hex}")
                    selected_count += 1
                for volume in volumes:
                    run(self.session, f"color #{volume.id_string} {color_hex}")
                    selected_count += 1
            """

        except Exception as e:
            self.session.logger.error(f"Error applying color: {e}")
            QMessageBox.warning(None, "Error", f"Failed to apply color: {e}")

    def color_apbs(self):
        """Color selected models with APBS blue"""
        self._apply_color_to_selected("#0000FF")

    def color_apbs_minus(self):
        """Color selected models with APBS minus red"""
        self._apply_color_to_selected("#FF0000")

    def color_hydrophobic(self):
        """Color selected models with hydrophobic yellow"""
        self._apply_color_to_selected("#FFFF00")

    def color_hydrophilic(self):
        """Color selected models with hydrophilic light blue"""
        self._apply_color_to_selected("#4DD9FF")

    def color_h_b_acceptor(self):
        """Color selected models with H-bond acceptor orange"""
        self._apply_color_to_selected("#FF8000")

    def color_h_b_donor(self):
        """Color selected models with H-bond donor purple"""
        self._apply_color_to_selected("#B300FF")

    def color_pi_stacking(self):
        """Color selected models with pi stacking green"""
        self._apply_color_to_selected("#00FF00")
