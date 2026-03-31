# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

from qgis.PyQt.QtWidgets import QDialog

from gui.cityjson_loader_dialog import CityJsonLoaderDialog


class TestCityJsonLoaderDialog:
    def setup_method(self, method):
        """Set up for each test method."""
        self.dialog = None

    def teardown_method(self, method):
        """Clean up after each test method."""
        if hasattr(self, "dialog") and self.dialog:
            self.dialog.close()
            self.dialog = None

    def test_close_button(self, qgis_app):
        """Test the close button functionality."""
        self.dialog = CityJsonLoaderDialog()
        button = self.dialog.closeButton
        assert button.isEnabled()
        button.click()
        result = self.dialog.result()
        assert result == QDialog.Rejected

    def test_load_button(self, qgis_app):
        """Test the load button functionality."""
        self.dialog = CityJsonLoaderDialog()
        button = self.dialog.loadButton
        assert button.isEnabled()
        button.click()

    def test_cancel_button(self, qgis_app):
        """Test the cancel button functionality."""
        self.dialog = CityJsonLoaderDialog()
        button = self.dialog.cancelButton
        button.click()
        assert not button.isEnabled()
        result = self.dialog.result()
        assert result == QDialog.Rejected

    def test_browse_files_button(self, qgis_app):
        """Test the browse files button functionality."""
        self.dialog = CityJsonLoaderDialog()
        button = self.dialog.browseFilesButton
        button.click()
        assert button.isEnabled()

    def test_browse_directory_button(self, qgis_app):
        """Test the browse directory button functionality."""
        self.dialog = CityJsonLoaderDialog()
        button = self.dialog.browseDirectoryButton
        button.click()
        assert button.isEnabled()

    def test_remove_files_button(self, qgis_app):
        """Test the remove files button initial state."""
        self.dialog = CityJsonLoaderDialog()
        button = self.dialog.removeFilesButton
        assert not button.isEnabled()

    def test_clear_all_button(self, qgis_app):
        """Test the clear all button initial state."""
        self.dialog = CityJsonLoaderDialog()
        button = self.dialog.clearAllButton
        assert not button.isEnabled()

    def test_change_crs_button(self, qgis_app):
        """Test the change CRS button initial state."""
        self.dialog = CityJsonLoaderDialog()
        button = self.dialog.changeCrsButton
        assert not button.isEnabled()

    def test_checkboxes(self, qgis_app):
        """Test checkbox functionality."""
        self.dialog = CityJsonLoaderDialog()
        for name in [
            "inheritParentAttributesCheckBox",
            "splitByTypeCheckBox",
            "semanticsLoadingCheckBox",
            "semanticSurfacesStylingCheckBox",
        ]:
            checkbox = getattr(self.dialog, name)
            checkbox.setChecked(True)
            assert checkbox.isChecked()
            checkbox.setChecked(False)
            assert not checkbox.isChecked()

    def test_dialog_initialization(self, qgis_app):
        """Test that the dialog initializes correctly."""
        self.dialog = CityJsonLoaderDialog()

        # Check that the dialog is a QDialog
        assert isinstance(self.dialog, QDialog)

        # Check that UI elements exist
        assert hasattr(self.dialog, "listWidget")
        assert hasattr(self.dialog, "cityjsonVersionLineEdit")
        assert hasattr(self.dialog, "compressedLineEdit")
        assert hasattr(self.dialog, "crsLineEdit")
        assert hasattr(self.dialog, "metadataTreeView")

    def test_line_edit_fields(self, qgis_app):
        """Test the line edit fields functionality."""
        self.dialog = CityJsonLoaderDialog()

        # Test cityjsonVersionLineEdit
        self.dialog.cityjsonVersionLineEdit.setText("1.0")
        assert self.dialog.cityjsonVersionLineEdit.text() == "1.0"

        # Test compressedLineEdit
        self.dialog.compressedLineEdit.setText("Yes")
        assert self.dialog.compressedLineEdit.text() == "Yes"

        # Test crsLineEdit
        self.dialog.crsLineEdit.setText("4326")
        assert self.dialog.crsLineEdit.text() == "4326"

    def test_combo_boxes(self, qgis_app):
        """Test the combo box functionality."""
        self.dialog = CityJsonLoaderDialog()

        # Test loDLoadingComboBox
        assert hasattr(self.dialog, "loDLoadingComboBox")
        initial_index = self.dialog.loDLoadingComboBox.currentIndex()
        assert isinstance(initial_index, int)

        # Test loDSelectionComboBox
        assert hasattr(self.dialog, "loDSelectionComboBox")
        initial_index = self.dialog.loDSelectionComboBox.currentIndex()
        assert isinstance(initial_index, int)

    def test_reset_fields_method(self, qgis_app):
        """Test the reset_fields method."""
        self.dialog = CityJsonLoaderDialog()

        # Set some values first
        self.dialog.cityjsonVersionLineEdit.setText("1.0")
        self.dialog.compressedLineEdit.setText("Yes")
        self.dialog.crsLineEdit.setText("4326")
        self.dialog.inheritParentAttributesCheckBox.setChecked(True)
        self.dialog.splitByTypeCheckBox.setChecked(True)

        # Call reset_fields
        self.dialog.reset_fields()

        # Check that fields are cleared
        assert self.dialog.cityjsonVersionLineEdit.text() == ""
        assert self.dialog.compressedLineEdit.text() == ""
        assert self.dialog.crsLineEdit.text() == ""

        # Check that checkboxes are unchecked and disabled
        assert not self.dialog.inheritParentAttributesCheckBox.isChecked()
        assert not self.dialog.splitByTypeCheckBox.isChecked()
        assert not self.dialog.semanticsLoadingCheckBox.isChecked()
        assert not self.dialog.semanticSurfacesStylingCheckBox.isChecked()

        assert not self.dialog.inheritParentAttributesCheckBox.isEnabled()
        assert not self.dialog.splitByTypeCheckBox.isEnabled()
        assert not self.dialog.semanticsLoadingCheckBox.isEnabled()
        assert not self.dialog.semanticSurfacesStylingCheckBox.isEnabled()

        # Check that combo boxes are reset to index 0
        assert self.dialog.loDLoadingComboBox.currentIndex() == 0
        assert self.dialog.loDSelectionComboBox.currentIndex() == 0

        # Check that list widget is cleared
        assert self.dialog.listWidget.count() == 0

        # Check that metadata tree view model is cleared
        assert self.dialog.metadataTreeView.model() is None

    def test_list_widget(self, qgis_app):
        """Test the list widget functionality."""
        self.dialog = CityJsonLoaderDialog()

        # Initially should be empty
        assert self.dialog.listWidget.count() == 0

        # Add some items
        self.dialog.listWidget.addItem("test_file1.json")
        self.dialog.listWidget.addItem("test_file2.json")

        assert self.dialog.listWidget.count() == 2
        assert self.dialog.listWidget.item(0).text() == "test_file1.json"
        assert self.dialog.listWidget.item(1).text() == "test_file2.json"

        # Clear the list
        self.dialog.listWidget.clear()
        assert self.dialog.listWidget.count() == 0

    def test_metadata_tree_view(self, qgis_app):
        """Test the metadata tree view functionality."""
        self.dialog = CityJsonLoaderDialog()

        # Initially should have no model
        assert self.dialog.metadataTreeView.model() is None

        # Check that the tree view exists and is accessible
        assert hasattr(self.dialog, "metadataTreeView")

    def test_dialog_buttons_initial_state(self, qgis_app):
        """Test the initial state of all dialog buttons."""
        self.dialog = CityJsonLoaderDialog()

        # These buttons should be enabled by default
        assert self.dialog.closeButton.isEnabled()
        assert self.dialog.loadButton.isEnabled()
        assert self.dialog.browseFilesButton.isEnabled()
        assert self.dialog.browseDirectoryButton.isEnabled()

        # These buttons should be disabled initially (no files selected)
        assert not self.dialog.removeFilesButton.isEnabled()
        assert not self.dialog.clearAllButton.isEnabled()
        assert not self.dialog.changeCrsButton.isEnabled()

    def test_progress_tracking_elements(self, qgis_app):
        """Test elements related to progress tracking."""
        self.dialog = CityJsonLoaderDialog()

        # Check for progress-related UI elements if they exist
        if hasattr(self.dialog, "progressBar"):
            assert self.dialog.progressBar is not None

        if hasattr(self.dialog, "fileCountLabel"):
            assert self.dialog.fileCountLabel is not None
