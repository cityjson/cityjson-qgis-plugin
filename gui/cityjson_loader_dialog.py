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

"""The class that manages the CityJSON Loader dialog"""

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), "cityjson_loader_dialog_base.ui")
)


class CityJsonLoaderDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Initialize the dialog"""
        super(CityJsonLoaderDialog, self).__init__(parent)
        self.setupUi(self)

    def reset_fields(self):
        """Reset the fields in the dialog."""
        self.listWidget.clear()
        self.cityjsonVersionLineEdit.clear()
        self.compressedLineEdit.clear()
        self.crsLineEdit.clear()

        # Clear metadata box
        self.metadataTreeView.setModel(None)

        # Reset checkboxes and disable them
        self.inheritParentAttributesCheckBox.setChecked(False)
        self.splitByTypeCheckBox.setChecked(False)
        self.semanticsLoadingCheckBox.setChecked(False)
        self.semanticSurfacesStylingCheckBox.setChecked(False)
        self.inheritParentAttributesCheckBox.setEnabled(False)
        self.splitByTypeCheckBox.setEnabled(False)
        self.semanticsLoadingCheckBox.setEnabled(False)
        self.semanticSurfacesStylingCheckBox.setEnabled(False)

        # Reset Lod checkboxes
        self.loDLoadingComboBox.setCurrentIndex(0)
        self.loDSelectionComboBox.setCurrentIndex(0)
