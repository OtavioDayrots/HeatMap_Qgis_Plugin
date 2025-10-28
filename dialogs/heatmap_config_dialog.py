"""
Diálogo de configuração para parâmetros do Heatmap
"""

import os
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QDialogButtonBox,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QCheckBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
)

from ..services.color_service import ColorService


class HeatmapConfigDialog(QDialog):
    """Dialogo para configurar parâmetros do heatmap"""

    def __init__(self, parent=None, layer=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Heatmap")
        self._layer = layer
        self._chosen_filename = None

        self.radius_input = QSpinBox()
        self.radius_input.setRange(1, 10000)
        self.radius_input.setValue(100)

        self.pixel_input = QDoubleSpinBox()
        self.pixel_input.setDecimals(3)
        self.pixel_input.setRange(0.01, 1000.0)
        self.pixel_input.setSingleStep(0.1)
        self.pixel_input.setValue(1.0)

        self.transparent_input = QSpinBox()
        self.transparent_input.setRange(0, 100)
        self.transparent_input.setValue(60)

        self.kernel_input = QComboBox()
        # QGIS enums esperados pelo algoritmo
        self.kernel_map = {
            "Quartic (padrão)": 0,
            "Triangular": 1,
            "Uniform": 2,
            "Epanechnikov": 3,
            "Gaussian": 4,
        }
        for name in self.kernel_map.keys():
            self.kernel_input.addItem(name)
        self.kernel_input.setCurrentIndex(0)

        self.palette_input = QComboBox()
        self.palette_names = list(ColorService.get_available_colormaps().keys())
        for name in self.palette_names:
            self.palette_input.addItem(name)
        # Padrão solicitado: BCYR
        default_index = self.palette_names.index("BCYR") if "BCYR" in self.palette_names else 0
        self.palette_input.setCurrentIndex(default_index)

        # Filtro (experto) texto
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Ex.: \"tipo\" = 'escola' AND score > 3")

        # Construtor de filtro (anti-erros)
        self.field_combo = QComboBox()
        self.op_combo = QComboBox()
        self.value_input = QLineEdit()
        self.btn_add_clause = QPushButton("Adicionar")

        self._populate_fields()
        self.field_combo.currentIndexChanged.connect(self._refresh_ops_for_field)
        self.btn_add_clause.clicked.connect(self._append_clause)

        form = QFormLayout()
        form.addRow("Raio (m)", self.radius_input)
        form.addRow("Tamanho do pixel (m)", self.pixel_input)
        form.addRow("Transparência (%)", self.transparent_input)
        form.addRow("Kernel", self.kernel_input)
        form.addRow("Paleta", self.palette_input)

        # Linha do construtor de filtro
        fb_row = QHBoxLayout()
        fb_row.addWidget(self.field_combo)
        fb_row.addWidget(self.op_combo)
        fb_row.addWidget(self.value_input)
        fb_row.addWidget(self.btn_add_clause)
        form.addRow("Filtro (construtor)", fb_row)

        # Campo de expressão completa
        form.addRow("Filtro (expressão)", self.filter_input)

        # Pasta de saída opcional (vazio = temporário)
        out_row = QHBoxLayout()
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("Vazio = arquivo temporário")
        self.btn_browse_out = QPushButton("Salvar como...")
        self.btn_browse_out.clicked.connect(self._choose_output_dir)
        out_row.addWidget(self.output_dir_input)
        out_row.addWidget(self.btn_browse_out)
        form.addRow("Pasta para salvar (opcional)", out_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _populate_fields(self):
        """Preenche lista de campos a partir da camada ativa."""
        self.field_combo.clear()
        if not self._layer or not hasattr(self._layer, 'fields'):
            self.field_combo.setEnabled(False)
            self.op_combo.setEnabled(False)
            self.value_input.setEnabled(False)
            self.btn_add_clause.setEnabled(False)
            return
        try:
            for fld in self._layer.fields():
                self.field_combo.addItem(fld.name())
        except Exception:
            pass
        self._refresh_ops_for_field()

    def _refresh_ops_for_field(self):
        """Atualiza operadores sugeridos conforme tipo do campo."""
        self.op_combo.clear()
        f_name = self.field_combo.currentText()
        f_type = None
        try:
            idx = self._layer.fields().indexFromName(f_name)
            if idx >= 0:
                f_type = self._layer.fields().field(idx).type()
        except Exception:
            f_type = None
        # Operadores básicos comuns
        numeric_ops = [">", ">=", "<", "<=", "=", "!=", "IS NULL", "IS NOT NULL"]
        text_ops = ["=", "!=", "ILIKE", "LIKE", "IS NULL", "IS NOT NULL"]
        ops = numeric_ops if (f_type in (2, 3, 4, 5, 6, 7, 8)) else text_ops  # tipos numéricos comuns
        for op in ops:
            self.op_combo.addItem(op)

    def _append_clause(self):
        """Monta e insere uma cláusula no campo de expressão."""
        field = self.field_combo.currentText()
        op = self.op_combo.currentText()
        val = self.value_input.text().strip()
        if not field or not op:
            return
        # Aspas em campos com caracteres especiais
        field_expr = f'"{field}"'
        # Valor: aspas simples para texto (se não for número) e sem aspas para nulos
        clause = None
        if op in ("IS NULL", "IS NOT NULL"):
            clause = f"{field_expr} {op}"
        else:
            is_number = False
            try:
                float(val)
                is_number = True
            except Exception:
                is_number = False
            if is_number:
                clause = f"{field_expr} {op} {val}"
            else:
                # escapar aspas simples no valor
                val_esc = val.replace("'", "''")
                if op in ("ILIKE", "LIKE") and not (val_esc.startswith('%') or val_esc.endswith('%')):
                    val_esc = f"%{val_esc}%"
                clause = f"{field_expr} {op} '{val_esc}'"
        cur = self.filter_input.text().strip()
        new_expr = clause if not cur else f"{cur} AND {clause}"
        self.filter_input.setText(new_expr)

    def get_config(self) -> dict:
        kernel_name = self.kernel_input.currentText()
        return {
            "radius": int(self.radius_input.value()),
            "pixel_size": float(self.pixel_input.value()),
            "kernel": int(self.kernel_map.get(kernel_name, 0)),
            "palette": str(self.palette_input.currentText()),
            "filter_expr": str(self.filter_input.text()).strip() or None,
            "output_dir": str(self.output_dir_input.text()).strip() or None,
            "output_filename": str(self._chosen_filename).strip() if self._chosen_filename else None,
            "transparent": int(self.transparent_input.value())
        }

    def _choose_output_dir(self):
        try:
            # Abre diálogo de salvar arquivo permitindo informar o nome no explorador
            filename, selected_filter = QFileDialog.getSaveFileName(
                self,
                "Salvar heatmap como",
                "",
                "GeoTIFF (*.tif);;Todos os arquivos (*.*)"
            )
            if filename:
                # Garantir extensão .tif
                if not filename.lower().endswith(".tif"):
                    filename = f"{filename}.tif"
                # Preenche pasta e nome automaticamente
                base_dir = os.path.dirname(filename)
                base_name = os.path.basename(filename)
                self.output_dir_input.setText(base_dir)
                self._chosen_filename = base_name
        except Exception:
            pass


