from PyQt5.QtWidgets import QDialog, QApplication

from gui.cityjson_loader_dialog import CityJsonLoaderDialog


class TestCityJsonLoaderDialog:
    @classmethod
    def setup_class(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setup_method(self):
        self.dialog = CityJsonLoaderDialog()

    def teardown_method(self):
        self.dialog = None

    def test_close_button(self):
        button = self.dialog.closeButton
        assert button.isEnabled()
        button.click()
        result = self.dialog.result()
        assert result == QDialog.Rejected

    def test_load_button(self):
        button = self.dialog.loadButton
        assert button.isEnabled()
        button.click()

    def test_cancel_button(self):
        button = self.dialog.cancelButton
        button.click()
        assert not button.isEnabled()
        result = self.dialog.result()
        assert result == self.dialog.Rejected

    def test_browse_files_button(self):
        button = self.dialog.browseFilesButton
        button.click()
        assert button.isEnabled()

    def test_browse_directory_button(self):
        button = self.dialog.browseDirectoryButton
        button.click()
        assert button.isEnabled()

    def test_remove_files_button(self):
        button = self.dialog.removeFilesButton
        assert not button.isEnabled()

    def test_clear_all_button(self):
        button = self.dialog.clearAllButton
        assert not button.isEnabled()

    def test_change_crs_button(self):
        button = self.dialog.changeCrsButton
        assert not button.isEnabled()

    def test_checkboxes(self):
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


if __name__ == "__main__":
    test = TestCityJsonLoaderDialog()

    print("All tests passed.")
