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
from qgis.PyQt.QtGui import QFontMetrics

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
        self.value_input = QComboBox()
        self.value_input.setEditable(True)  # Permite digitação além de seleção
        self.operator_combo = QComboBox()
        self.operator_combo.addItem("E", userData="AND")
        self.operator_combo.addItem("OU", userData="OR")
        self.operator_combo.setCurrentIndex(0)  # Padrão: AND
        self.btn_add_clause = QPushButton("+")
        self.btn_add_clause.setFixedSize(30, 30)
        self.btn_add_clause.setStyleSheet(
            "QPushButton {"
            "background-color: #2ecc71;"
            "color: #ffffff;"
            "font-size: 16px;"
            "font-weight: bold;"
            "border: 1px solid #000000;"
            "border-radius: 4px;"
            "padding: 0;"
            "}"
            "QPushButton:hover { background-color: #27ae60; }"
        )

        # Ajustes para que o texto caiba melhor
        for cb in (self.field_combo, self.op_combo, self.value_input):
            try:
                cb.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            except Exception:
                pass
        self.value_input.setMinimumContentsLength(24)

        self._populate_fields()
        self.field_combo.currentIndexChanged.connect(self._refresh_ops_for_field)
        self.field_combo.currentIndexChanged.connect(self._refresh_values_for_field)
        self.btn_add_clause.clicked.connect(self._append_clause)

        form = QFormLayout()
        row = QHBoxLayout()
        row.addWidget(QLabel("Raio (m)"))
        row.addWidget(self.radius_input)
        row.addSpacing(12)
        row.addWidget(QLabel("Tamanho do pixel (m)"))
        row.addWidget(self.pixel_input)
        form.addRow(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Transparência (%)"))
        row2.addWidget(self.transparent_input)
        row2.addSpacing(12)
        row2.addWidget(QLabel("Paleta"))
        row2.addWidget(self.palette_input)
        form.addRow(row2)

        # Linha do construtor de filtro
        fb_row = QHBoxLayout()
        fb_row.addWidget(self.field_combo)
        fb_row.addWidget(self.op_combo)
        fb_row.addWidget(self.value_input)
        fb_row.addWidget(self.btn_add_clause)
        form.addRow("Filtro (construtor)", fb_row)

        # Campo de expressão completa com modo AND/OR
        filter_row = QHBoxLayout()
        filter_row.addWidget(self.filter_input, stretch=1)  # Campo de expressão ocupa mais espaço
        # Define largura fixa para o combo de modo para não ocupar muito espaço
        self.operator_combo.setMaximumWidth(80)
        filter_row.addWidget(self.operator_combo)
        form.addRow("Filtro (expressão)", filter_row)

        # Pasta de saída opcional (vazio = temporário)
        out_row = QHBoxLayout()
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setPlaceholderText("Vazio = arquivo temporário")
        self.btn_browse_out = QPushButton("Salvar como...")
        self.btn_browse_out.clicked.connect(self._choose_output_dir)
        out_row.addWidget(self.output_dir_input)
        out_row.addWidget(self.btn_browse_out)
        form.addRow("Pasta (opcional)", out_row)

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
            self.operator_combo.setEnabled(False)
            self.btn_add_clause.setEnabled(False)
            return
        try:
            for fld in self._layer.fields():
                self.field_combo.addItem(fld.name())
        except Exception:
            pass
        self._refresh_ops_for_field()
        self._refresh_values_for_field()

    def _refresh_ops_for_field(self):
        """Atualiza operadores sugeridos."""
        self.op_combo.clear()
        # Todos os operadores disponíveis (sem filtrar por tipo de campo)
        numeric_ops = [">", ">=", "<", "<=", "=", "!=", "IS NULL", "IS NOT NULL"]
        text_ops = ["ILIKE", "LIKE"]
        # Combina todos os operadores, removendo duplicatas
        all_ops = numeric_ops + [op for op in text_ops if op not in numeric_ops]
        for op in all_ops:
            self.op_combo.addItem(op)

    def _refresh_values_for_field(self):
        """Preenche valores únicos do campo selecionado se for campo de texto/discreto."""
        self.value_input.clear()
        self.value_input.setEditable(True)
        
        if not self._layer or not hasattr(self._layer, 'fields'):
            return
        
        f_name = self.field_combo.currentText()
        if not f_name:
            return
        
        try:
            idx = self._layer.fields().indexFromName(f_name)
            if idx < 0:
                return
            
            # Para campos de texto/discretos, busca uma AMOSTRA de valores únicos
            # Isso imita o comportamento do botão "Amostra" da UI do QGIS.
            max_values = 50  # amostra reduzida para performance
            unique_values = set()
            provider = getattr(self._layer, 'dataProvider', None)

            try:
                if provider and callable(provider):
                    # dataProvider é método nas camadas; obtemos a instância
                    dp = self._layer.dataProvider()
                    # Alguns provedores expõem uniqueValues(field, limit)
                    # limit=0 => sem limite; aqui aplicamos limite pequeno
                    vals = dp.uniqueValues(idx, max_values)
                    unique_values = {str(v) for v in vals if v is not None}
                else:
                    # Fallback: iterar com corte antecipado
                    for feature in self._layer.getFeatures():
                        value = feature.attribute(f_name)
                        if value is not None:
                            unique_values.add(str(value))
                            if len(unique_values) >= max_values:
                                break
            except Exception:
                # Se a API do provedor não suportar limite, cai no fallback simples
                for feature in self._layer.getFeatures():
                    value = feature.attribute(f_name)
                    if value is not None:
                        unique_values.add(str(value))
                        if len(unique_values) >= max_values:
                            break
            
            # Adiciona valores únicos ordenados ao combo
            sorted_values = sorted(unique_values)
            for val in sorted_values:
                self.value_input.addItem(val)
            # Ajusta a largura do popup para o maior item
            self._resize_combo_popup_to_fit(self.value_input, sorted_values)
                
        except Exception:
            # Em caso de erro, apenas deixa o campo editável
            pass

    def _append_clause(self):
        """Monta e insere uma cláusula no campo de expressão."""
        field = self.field_combo.currentText()
        op = self.op_combo.currentText()
        val = self.value_input.currentText().strip()
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
        if not cur:
            new_expr = clause
        else:
            operator = self.operator_combo.currentData() or self.operator_combo.currentText()
            new_expr = f"{cur} {operator} {clause}"
        self.filter_input.setText(new_expr)

    def _resize_combo_popup_to_fit(self, combo: QComboBox, texts):
        """Ajusta a largura do popup do combo para caber o maior texto."""
        try:
            view = combo.view() if hasattr(combo, 'view') else None
            fm = QFontMetrics(view.font() if view else combo.font())
            max_width = 0
            for t in texts or []:
                max_width = max(max_width, fm.horizontalAdvance(str(t)))
            if view and max_width:
                # margem para barra de rolagem e padding
                view.setMinimumWidth(max_width + 40)
        except Exception:
            pass

    def get_config(self) -> dict:
        return {
            "radius": int(self.radius_input.value()),
            "pixel_size": float(self.pixel_input.value()),
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


