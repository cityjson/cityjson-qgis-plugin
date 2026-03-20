# ******************************************************************************
# Project: CityJsonLoader - A QGIS Plugin.
#
# Purpose: This plugin allows for CityJSON files to be loaded in QGIS.
#
# GitHub page: https://github.com/cityjson/cityjson-qgis-plugin
#
# Contact: G.Stavropoulou@tudelft.nl
# ******************************************************************************
#
# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ******************************************************************************

import os.path
import json

from qgis.PyQt.QtCore import (
    QCoreApplication,
    QSettings,
    QTranslator,
    Qt,
    qVersion,
    QTimer,
)
from qgis.PyQt.QtGui import QIcon, QKeySequence
from qgis.PyQt.QtWidgets import (
    QAction,
    QFileDialog,
    QMessageBox,
    QShortcut,
)
from qgis.core import QgsApplication, QgsCoordinateReferenceSystem
from qgis.gui import QgsProjectionSelectionDialog

from .core.helpers.treemodel import MetadataModel
from .core.loading import CityJSONLoader, load_cityjson_model, get_model_epsg
from .core.styling import is_rule_based_3d_styling_available

from .gui.cityjson_loader_dialog import CityJsonLoaderDialog
from .processing.provider import Provider


class CityJsonLoader:
    """QGIS Plugin Implementation"""

    def __init__(self, iface):
        """Initialize the CityJSON Loader plugin"""
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        locale_path = os.path.join(
            self.plugin_dir, "i18n", "CityJsonLoader_{}.qm".format(locale)
        )

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > "4.3.3":
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = CityJsonLoaderDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr("&CityJSON Loader")
        # # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar("CityJsonLoader")
        self.toolbar.setObjectName("CityJsonLoader")

        self._cancel_requested = False

        self.file_epsg_map = {}

        self.citymodel_cache = {}
        self.max_cache_size = 10  # Limit cache to prevent memory issues

        # Variables for asynchronous file processing
        self.file_queue = []
        self.current_file_index = 0
        self.process_timer = None

        self.delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.dlg)
        self.delete_shortcut.activated.connect(self.remove_cityjson_files)

        self.dlg.listWidget.itemSelectionChanged.connect(self.update_file_list)
        self.dlg.browseFilesButton.clicked.connect(self.select_cityjson_files)
        self.dlg.browseDirectoryButton.clicked.connect(
            self.select_cityjson_files_directory
        )

        self.dlg.removeFilesButton.clicked.connect(self.remove_cityjson_files)
        self.dlg.clearAllButton.clicked.connect(self.clear_all_files)

        self.dlg.changeCrsButton.clicked.connect(self.select_crs)
        self.dlg.semanticsLoadingCheckBox.stateChanged.connect(
            self.semantics_loading_changed
        )

        self.dlg.cancelButton.clicked.connect(self.request_cancel)
        self.dlg.loadButton.clicked.connect(self.process_files)
        self.dlg.closeButton.clicked.connect(self.dlg.reject)

        self.provider = None

    def initProcessing(self):
        """Initialises the processing provider."""
        self.provider = Provider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def request_cancel(self):
        """Request cancellation of the current processing operation"""
        self._cancel_requested = True
        if self.process_timer is not None:
            # The timer will check _cancel_requested on next iteration
            pass

    def add_cityjson_files(self, filepaths):
        """Add CityJSON files to the file list"""
        self.reset_progress_format_on_ui_change()
        for filename in filepaths:
            existing_items = self.dlg.listWidget.findItems(filename, Qt.MatchFlag.MatchExactly)
            if not existing_items:
                self.dlg.listWidget.addItem(filename)
                epsg = self.load_file_crs(filename)
                self.file_epsg_map[filename] = epsg

        if self.dlg.listWidget.count() > 0:
            self.dlg.listWidget.setCurrentRow(0)
            self.update_file_list()

        self.update_file_count_label()

    def select_cityjson_files(self):
        """Open file dialog to select CityJSON files"""
        file_filter = "CityJSON files (*.city.json *.json);;CityJSON files (*.city.json);;JSON files (*.json);;All files (*.*)"
        filenames, _ = QFileDialog.getOpenFileNames(
            self.dlg, "Select CityJSON File(s)", "", file_filter
        )

        if filenames:
            self.add_cityjson_files(filenames)

    def select_cityjson_files_directory(self):
        """Select CityJSON files from a directory"""
        directory = QFileDialog.getExistingDirectory(
            self.dlg, "Select Directory", "", QFileDialog.ShowDirsOnly
        )

        if directory:
            filenames = [
                os.path.join(directory, f)
                for f in os.listdir(directory)
                if f.endswith(".city.json") or f.endswith(".json")
            ]
            if filenames:
                self.add_cityjson_files(filenames)

    def remove_cityjson_files(self):
        """Removes CityJSON file(s) from the list"""
        selected_items = self.dlg.listWidget.selectedItems()
        if selected_items:
            self.reset_progress_format_on_ui_change()
            current_row = self.dlg.listWidget.currentRow()
            for item in selected_items:
                self.dlg.listWidget.takeItem(self.dlg.listWidget.row(item))
                filename = item.text()
                self.file_epsg_map.pop(filename, None)
                self.citymodel_cache.pop(filename, None)

            count = self.dlg.listWidget.count()
            if count > 0:
                new_row = current_row if current_row < count else count - 1
                self.dlg.listWidget.setCurrentRow(new_row)
                self.update_file_list()
            else:
                self.clear_file_information()

        self.update_file_count_label()

    def clear_all_files(self):
        """Removes all CityJSON files from the list"""
        if self.dlg.listWidget.count() > 0:
            self.reset_progress_format_on_ui_change()
        self.dlg.listWidget.clear()
        self.clear_file_information()
        self.citymodel_cache.clear()
        self.update_file_count_label()

    def update_file_count_label(self):
        """Updates the file count label to reflect the number of selected files"""
        count = self.dlg.listWidget.count()
        self.dlg.fileCountLabel.setText(f"{count} file(s) selected")

        self.dlg.removeFilesButton.setEnabled(count > 0)
        self.dlg.clearAllButton.setEnabled(count > 0)
        self.dlg.changeCrsButton.setEnabled(count > 0)
        self.dlg.inheritParentAttributesCheckBox.setEnabled(count > 0)
        self.dlg.splitByTypeCheckBox.setEnabled(count > 0)
        self.dlg.semanticsLoadingCheckBox.setEnabled(count > 0)
        self.dlg.loDLoadingComboBox.setEnabled(count > 0)
        self.dlg.loDSelectionComboBox.setEnabled(count > 0)

        if count == 0:
            self.dlg.inheritParentAttributesCheckBox.setChecked(False)
            self.dlg.splitByTypeCheckBox.setChecked(False)
            self.dlg.semanticsLoadingCheckBox.setChecked(False)

    def _manage_cache_size(self):
        """Manage cache size to prevent memory issues"""
        if len(self.citymodel_cache) > self.max_cache_size:
            # Remove oldest entry (FIFO)
            oldest_key = next(iter(self.citymodel_cache))
            del self.citymodel_cache[oldest_key]

    def load_file_crs(self, filename):
        """Load the CRS for the CityJSON file"""
        try:
            if filename in self.citymodel_cache:
                model = self.citymodel_cache[filename]
            else:
                with open(filename, encoding="utf-8-sig") as fstream:
                    model = json.load(fstream)
                    # Cache the model for reuse
                    self.citymodel_cache[filename] = model
                    self._manage_cache_size()

            epsg = get_model_epsg(model)
            return epsg
        except (IOError, OSError, json.JSONDecodeError, KeyError):
            return "None"

    def update_file_list(self):
        """Update metadata fields according to the file selected"""
        self.dlg.listWidget.blockSignals(True)
        try:
            selected_item = self.dlg.listWidget.currentItem()
            if selected_item:
                filename = selected_item.text()
                if not os.path.exists(filename):
                    items = self.dlg.listWidget.findItems(filename, Qt.MatchExactly)
                    for item in items:
                        self.dlg.listWidget.takeItem(self.dlg.listWidget.row(item))
                    self.file_epsg_map.pop(filename, None)
                    self.update_file_count_label()

                    if self.dlg.listWidget.count() > 0:
                        self.dlg.listWidget.setCurrentRow(0)
                        self.update_file_list()
                    else:
                        self.clear_file_information()
                else:
                    self.update_file_information(filename)
            else:
                self.clear_file_information()
        finally:
            self.dlg.listWidget.blockSignals(False)

    def select_crs(self):
        """Shows a dialog to select a new CRS for the model"""
        crs_dialog = QgsProjectionSelectionDialog()
        crs_dialog.setShowNoProjection(True)

        current_item = self.dlg.listWidget.currentItem()
        if current_item:
            current_file = current_item.text()
            current_crs = self.file_epsg_map.get(current_file, None)
            if current_crs:
                old_crs = QgsCoordinateReferenceSystem(
                    "EPSG:{}".format(self.dlg.crsLineEdit.text())
                )
                crs_dialog.setCrs(old_crs)

        crs_dialog.exec()
        new_crs_id = crs_dialog.crs().postgisSrid()

        if new_crs_id == 0:
            self.dlg.crsLineEdit.setText("None")
        else:
            self.dlg.crsLineEdit.setText(str(new_crs_id))

        if current_item:
            filename = current_item.text()
            self.file_epsg_map[filename] = str(new_crs_id)

    def semantics_loading_changed(self):
        """Update the GUI according to the new state of semantic surfaces loading"""
        if is_rule_based_3d_styling_available():
            checked = self.dlg.semanticsLoadingCheckBox.isChecked()
            self.dlg.semanticSurfacesStylingCheckBox.setEnabled(checked)
            if not checked:
                self.dlg.semanticSurfacesStylingCheckBox.setChecked(False)
                self.dlg.semanticSurfacesStylingCheckBox.setEnabled(False)

    def clear_file_information(self):
        """Clear all file information fields"""
        self.dlg.cityjsonVersionLineEdit.clear()
        self.dlg.compressedLineEdit.clear()
        self.dlg.crsLineEdit.clear()
        self.dlg.metadataTreeView.setModel(None)

    def update_file_information(self, filename):
        """Update metadata fields according to the file provided"""

        if filename in self.citymodel_cache:
            model = self.citymodel_cache[filename]
        else:
            with open(filename, encoding="utf-8-sig") as fstream:
                model = json.load(fstream)
                # Cache the model for reuse
                self.citymodel_cache[filename] = model
                self._manage_cache_size()

        lods = {
            geom["lod"]
            for city_object in model["CityObjects"].values()
            if "geometry" in city_object
            for geom in city_object["geometry"]
            if "lod" in geom
        }

        self.dlg.cityjsonVersionLineEdit.setText(model["version"])
        self.dlg.compressedLineEdit.setText("Yes" if "transform" in model else "No")
        self.dlg.crsLineEdit.setText(self.file_epsg_map[filename])

        metadata = model.get(
            "metadata", {"metadata missing": "There is no metadata in this file"}
        )

        if "+metadata-extended" in model:
            metadata.update(model["+metadata-extended"])

        model = MetadataModel(metadata, self.dlg.metadataTreeView)
        self.dlg.metadataTreeView.setModel(model)
        self.dlg.metadataTreeView.setColumnWidth(0, model.getKeyColumnWidth())

        self.dlg.loDSelectionComboBox.clear()
        self.dlg.loDSelectionComboBox.addItem("All")
        self.dlg.loDSelectionComboBox.addItems(sorted(lods) if lods else [])
        self.dlg.loDSelectionComboBox.setEnabled(len(lods) > 0)

    def tr(self, message):
        """Get translation for a string using Qt translation API"""
        return QCoreApplication.translate("CityJsonLoader", message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add an action to the toolbar and/or menu"""

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI"""

        icon_path = ":/plugins/cityjson_loader/cityjson_logo.svg"
        self.add_action(
            icon_path,
            text=self.tr("Load CityJSON..."),
            callback=self.run,
            parent=self.iface.mainWindow(),
        )

        self.initProcessing()

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI"""
        if self.process_timer is not None:
            self.process_timer.stop()
            self.process_timer = None

        for action in self.actions:
            self.iface.removePluginVectorMenu(self.tr("&CityJSON Loader"), action)
            self.iface.removeToolBarIcon(action)

        del self.toolbar

        QgsApplication.processingRegistry().removeProvider(self.provider)

    def run(self):
        """Run method that performs all the real work"""
        if self.dlg.isVisible():
            self.dlg.raise_()
            self.dlg.activateWindow()
            return

        self.dlg.reset_fields()
        self.update_file_count_label()
        self.dlg.progressBar.setValue(0)
        self.dlg.progressBar.setFormat("%p%")

        self.dlg.show()

    def process_files(self):
        """Process files in the list widget. Dialog always stays open after processing. Updates progress bar in percent"""
        filepaths = [
            self.dlg.listWidget.item(i).text()
            for i in range(self.dlg.listWidget.count())
        ]
        if not filepaths:
            QMessageBox.warning(self.dlg, "No files", "No CityJSON files selected.")
            self.dlg.progressBar.setValue(0)
            return

        # Initialize asynchronous processing
        self.file_queue = filepaths
        self.current_file_index = 0
        self._cancel_requested = False

        # Update UI state for processing
        self.dlg.cancelButton.setEnabled(True)
        self.dlg.loadButton.setEnabled(False)
        self.dlg.progressBar.setValue(0)
        self.dlg.progressBar.setFormat("Processing... %p%")

        # Start the timer for asynchronous processing
        if self.process_timer is not None:
            self.process_timer.stop()

        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self.process_next_file)
        self.process_timer.start(50)

    def process_next_file(self):
        """Process the next file in the queue asynchronously"""
        # Check for cancellation
        if self._cancel_requested:
            self.finish_processing("Cancelled")
            return

        # Check if we've processed all files
        if self.current_file_index >= len(self.file_queue):
            self.finish_processing("Complete")
            return

        # Process current file
        filepath = self.file_queue[self.current_file_index]
        try:
            skipped_geometries = self.load_cityjson(filepath)

            # Update progress
            progress = int(((self.current_file_index + 1) / len(self.file_queue)) * 100)
            self.dlg.progressBar.setValue(progress)

            # Handle skipped geometries
            if skipped_geometries > 0:
                # Show warning message without blocking the UI
                msg = QMessageBox(self.dlg)
                msg.setIcon(QMessageBox.Warning)
                msg.setText("CityJSON loaded with issues.")
                msg.setInformativeText("Some geometries were skipped.")
                msg.setDetailedText(
                    f"{skipped_geometries} geometries could not be loaded (p.s. GeometryInstances are not supported yet)."
                )
                msg.setModal(False)  # Non-blocking
                msg.show()

        except Exception as e:
            # Handle any errors gracefully
            QMessageBox.critical(
                self.dlg, "Error", f"Error processing file {filepath}: {str(e)}"
            )

        # Move to next file
        self.current_file_index += 1

    def finish_processing(self, status_text):
        """Clean up and finish the asynchronous processing"""
        if self.process_timer is not None:
            self.process_timer.stop()
            self.process_timer = None

        # Reset state
        self._cancel_requested = False
        self.dlg.cancelButton.setEnabled(False)
        self.dlg.loadButton.setEnabled(True)

        # Update progress bar
        if status_text == "Complete":
            self.dlg.progressBar.setValue(100)
        self.dlg.progressBar.setFormat(status_text)

        # Reset progress bar after a short delay
        QTimer.singleShot(2000, lambda: self.dlg.progressBar.setValue(0))

    def reset_progress_format_on_ui_change(self):
        """Reset progress bar format when UI elements change"""
        if self.dlg.progressBar.format() == "Complete":
            self.dlg.progressBar.setFormat("%p%")

    def load_cityjson(self, filepath):
        """Loads the given CityJSON"""
        if filepath in self.citymodel_cache:
            citymodel = self.citymodel_cache[filepath]
        else:
            citymodel = load_cityjson_model(filepath)
            # Cache the model for potential reuse
            self.citymodel_cache[filepath] = citymodel
            self._manage_cache_size()

        lod_as = "NONE"
        if self.dlg.loDLoadingComboBox.currentIndex() == 1:
            lod_as = "ATTRIBUTES"
        elif self.dlg.loDLoadingComboBox.currentIndex() == 2:
            lod_as = "LAYERS"

        selected_lod = self.dlg.loDSelectionComboBox.currentText()

        if selected_lod == "All":
            lod = "All"
        else:
            lod = selected_lod

        loader = CityJSONLoader(
            filepath,
            citymodel,
            epsg=self.file_epsg_map.get(filepath, self.dlg.crsLineEdit.text()),
            keep_parent_attributes=self.dlg.inheritParentAttributesCheckBox.isChecked(),
            divide_by_object=self.dlg.splitByTypeCheckBox.isChecked(),
            lod_as=lod_as,
            lod=lod,
            load_semantic_surfaces=self.dlg.semanticsLoadingCheckBox.isChecked(),
            style_semantic_surfaces=self.dlg.semanticSurfacesStylingCheckBox.isChecked(),
        )

        skipped_geometries = loader.load()

        return skipped_geometries
