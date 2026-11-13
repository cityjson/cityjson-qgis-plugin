# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou.
# Licensed under the Apache License, Version 2.0. See LICENSE file for details.

from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle
from qgis.gui import QgsFileWidget
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

from gui.cityjson_writer_dialog import CityJsonWriterDialog


class TestCityJsonWriterDialog:
    def setup_method(self, method):
        self.dialog = None

    def teardown_method(self, method):
        if self.dialog:
            self.dialog.close()
            self.dialog = None

    # opens the dialog and checks its title and all its widgets
    def test_dialog_initialization(self, qgis_app):
        self.dialog = CityJsonWriterDialog()

        assert isinstance(self.dialog, QDialog)
        assert self.dialog.windowTitle() == "CityJSON Writer"
        for name in (
            "layer_select",
            "save_file_name",
            "keep_unloaded",
            "reload",
            "convert",
            "extent",
        ):
            assert hasattr(self.dialog, name)

    # checks if by deafult "Kepp unloaded" is ticked and "add saved file to map" is unticked
    def test_default_checkbox_states(self, qgis_app):
        self.dialog = CityJsonWriterDialog()

        assert self.dialog.keep_unloaded.isChecked()
        assert not self.dialog.reload.isChecked()

    # checks the save as and file type in export dialog
    def test_save_widget_is_save_mode(self, qgis_app):
        self.dialog = CityJsonWriterDialog()

        widget = self.dialog.save_file_name
        assert widget.storageMode() == QgsFileWidget.StorageMode.SaveFile
        assert "*.city.json" in widget.filter()

    # no area is set at the start, meaning the whole file
    def test_extent_defaults_to_whole_file(self, qgis_app):
        self.dialog = CityJsonWriterDialog()

        assert not self.dialog.extent.isValid()

    # checking iof reset fiels, clears out the filled fields
    def test_reset_fields(self, qgis_app):
        self.dialog = CityJsonWriterDialog()
        self.dialog.layer_select.addItem("a.city.json", "load-a")
        self.dialog.save_file_name.setFilePath("C:/tmp/out.city.json")
        self.dialog.keep_unloaded.setChecked(False)
        self.dialog.extent.setOutputExtentFromUser(
            QgsRectangle(0, 0, 10, 10), QgsCoordinateReferenceSystem("EPSG:28992")
        )
        assert self.dialog.extent.isValid()

        self.dialog.reset_fields()

        assert self.dialog.layer_select.count() == 0
        assert self.dialog.save_file_name.filePath() == ""
        assert self.dialog.keep_unloaded.isChecked()
        assert not self.dialog.extent.isValid()

    # checks if the export dialog hides when you drawing bounding box and comes back after youre done
    def test_extent_hides_dialog_while_drawing(self, qgis_app):
        self.dialog = CityJsonWriterDialog()
        self.dialog.show()

        self.dialog.extent.toggleDialogVisibility.emit(False)
        assert not self.dialog.isVisible()

        self.dialog.extent.toggleDialogVisibility.emit(True)
        assert self.dialog.isVisible()

    # testing close button
    def test_close_button(self, qgis_app):
        self.dialog = CityJsonWriterDialog()
        button = self.dialog.button_box.button(QDialogButtonBox.StandardButton.Close)

        assert button.isEnabled()
        button.click()
        assert self.dialog.result() == 0  # QDialog.Rejected

    def test_convert_button_enabled(self, qgis_app):
        self.dialog = CityJsonWriterDialog()

        assert self.dialog.convert.isEnabled()
        assert self.dialog.convert.text() == "Convert"
