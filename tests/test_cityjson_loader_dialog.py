# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

from PyQt5.QtWidgets import QDialog

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
