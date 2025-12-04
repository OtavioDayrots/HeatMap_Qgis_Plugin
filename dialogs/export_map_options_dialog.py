from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QCheckBox, QDialogButtonBox
from ..models.export_options import ExportMapOptions

class ExportMapOptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opções de exportação")
        self.format_combo = QComboBox()
        # Coloca GeoTIFF como primeira opção
        self.format_combo.addItems(["PNG", "JPEG", "SVG", "GEOTIFF", "PDF"])  # 'JPEG' (combina com o serviço)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 1200)  # era 'self.dpi_spin = setRange(...)'
        self.dpi_spin.setValue(300)
        self.chk_border = QCheckBox("Incluir borda"); self.chk_border.setChecked(True)
        self.chk_time = QCheckBox("Incluir carimbo de data"); self.chk_time.setChecked(True)
        self.chk_legend = QCheckBox("Incluir legenda"); self.chk_legend.setChecked(True)

        layout = QVBoxLayout()
        row1 = QHBoxLayout(); row1.addWidget(QLabel("Formato:")); row1.addWidget(self.format_combo)
        row2 = QHBoxLayout(); row2.addWidget(QLabel("DPI:")); row2.addWidget(self.dpi_spin)
        layout.addLayout(row1); layout.addLayout(row2)
        layout.addWidget(self.chk_border); layout.addWidget(self.chk_time); layout.addWidget(self.chk_legend)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self.setLayout(layout)

    def get_options(self):
        return ExportMapOptions(
            fmt=self.format_combo.currentText(),
            dpi=self.dpi_spin.value(),
            include_border=self.chk_border.isChecked(),
            include_timestamp=self.chk_time.isChecked(),
            include_legend=self.chk_legend.isChecked(),
        )
