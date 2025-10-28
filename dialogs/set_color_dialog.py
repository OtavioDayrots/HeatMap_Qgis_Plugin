"""
Diálogo de configuração para parâmetros do setColor
"""

import os
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QDialogButtonBox,
    QSpinBox,
    QComboBox,

)

from ..services.color_service import ColorService

class SetColorDialog(QDialog):
    # Configuações do dialog setColor
    def __init__(self, parent= None, layer= None):
        super().__init__(parent)
        self.setWindowTitle("Configurações SetColor")
        self._layer = layer
        self._chosen_filename = None

        self.transparent_input = QSpinBox()
        self.transparent_input.setRange(0, 100)
        self.transparent_input.setValue(60)

        self.palette_input = QComboBox()
        self.palette_names = list(ColorService.get_available_colormaps().keys())
        for name in self.palette_names:
            self.palette_input.addItem(name)
        # Padrão solicitado: BCYR
        default_index = self.palette_names.index("BCYR") if "BCYR" in self.palette_names else 0
        self.palette_input.setCurrentIndex(default_index)

        form = QFormLayout()
        form.addRow("Transparência (%)", self.transparent_input)
        form.addRow("Paleta", self.palette_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def get_config(self):
        return {
            "palette": str(self.palette_input.currentText()),
            "transparent": int(self.transparent_input.value())
        }
        