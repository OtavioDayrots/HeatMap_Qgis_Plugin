from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QDoubleSpinBox, QPushButton, QFormLayout, QComboBox
from qgis.PyQt.QtCore import Qt
from ..services.heatmap_stats_service import HeatmapStatsService


class HeatmapStatsDialog(QDialog):
    """Diálogo de estatísticas do heatmap.

    Propósito:
    - Mostrar um resumo legível (Min/Max/Média/Desvio) para calibrar simbologia.
    - Facilitar a escolha de thresholds via percentis (p50/p75/p90/p95).
    - Calcular área e cobertura acima do limite de forma explicável.

    Nota de UX: usamos HTML simples para destacar números e tooltips para explicar
    cada controle. O botão "?" injeta um help conciso no próprio diálogo.
    """
    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Estatísticas do Heatmap")
        self.layer = layer

        layout = QVBoxLayout()

        # Estatísticas básicas
        self.lbl_basic = QLabel()
        self.lbl_basic.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.lbl_basic)

        # Threshold controls
        form = QFormLayout()
        self.spn_threshold = QDoubleSpinBox()
        self.spn_threshold.setDecimals(3)
        self.spn_threshold.setSingleStep(0.1)
        self.spn_threshold.setToolTip(
            "Valor limite para calcular cobertura/área acima.\n"
            "Dica: use p90/p95 para destacar hotspots (topo da distribuição)."
        )
        form.addRow("Limite:", self.spn_threshold)
        # Percentis rápidos
        quick = QHBoxLayout()
        self.cmb_percentil = QComboBox()
        self.cmb_percentil.addItems(["p50", "p75", "p90", "p95"]) 
        self.cmb_percentil.setToolTip(
            "Percentil: p90 é o valor abaixo do qual estão 90% dos pixels.\n"
            "Usar como atalho para thresholds típicos."
        )
        self.btn_apply_percentil = QPushButton("Aplicar")
        self.btn_apply_percentil.setToolTip("Define o Limite com base no percentil selecionado.")
        quick.addWidget(self.cmb_percentil)
        quick.addWidget(self.btn_apply_percentil)
        form.addRow("Percentil:", quick)
        layout.addLayout(form)

        # Buttons
        btns = QHBoxLayout()
        self.btn_calc = QPushButton("Calcular área acima")
        self.btn_calc.setToolTip("Calcula pixels, área e cobertura acima do Limite atual.")
        self.btn_help = QPushButton("?")
        self.btn_help.setFixedWidth(28)
        self.btn_help.setToolTip("Ajuda rápida sobre as métricas exibidas.")
        self.btn_close = QPushButton("Fechar")
        btns.addWidget(self.btn_calc)
        btns.addStretch()
        btns.addWidget(self.btn_help)
        btns.addWidget(self.btn_close)
        layout.addLayout(btns)

        self.setLayout(layout)

        self.btn_calc.clicked.connect(self._calc_area)
        self.btn_apply_percentil.clicked.connect(self._apply_percentil)
        self.btn_close.clicked.connect(self.accept)
        self.btn_help.clicked.connect(self._show_help)

        self._load_basic()

    def _render_basic_html(self, s):
        def fmt(v, places=4):
            return (f"{float(v):.{places}f}" if v is not None else "—")
        html = (
            "<b>Resumo</b><br>"
            f"Min: <b>{fmt(s['min'])}</b><br>"
            f"Max: <b>{fmt(s['max'])}</b><br>"
            f"Média: <b>{fmt(s.get('mean'))}</b><br>"
            f"Desvio: <b>{fmt(s.get('stddev'))}</b><br>"
            "<hr>"
        )
        return html

    def _append_result_html(self, threshold, res):
        area = res['area_m2']
        pct = res['coverage_pct']
        area_txt = f"{area:.2f}" if area is not None else "—"
        pct_txt = f"{pct:.2f}%" if pct is not None else "—"
        blk = (
            f"<div style='margin-top:6px'>"
            f"Acima de <b>{threshold:.3f}</b>:<br>"
            f"Pixels: <b>{res['pixels_above']}</b><br>"
            f"Área (m²): <b>{area_txt}</b><br>"
            f"Cobertura: <b>{pct_txt}</b>"
            f"</div>"
        )
        return blk

    def _load_basic(self):
        s = HeatmapStatsService.compute_basic_stats(self.layer)
        self._basic_stats = s
        self.lbl_basic.setToolTip(
            "Min/Max: limites de intensidade do raster.\n"
            "Média/Desvio: estatísticas descritivas dos pixels válidos (sem NoData)."
        )
        # Ajustar faixa do threshold para o range real e definir valor padrão (p90)
        min_v = s.get('min') or 0.0
        max_v = s.get('max') or 0.0
        if max_v < min_v:
            min_v, max_v = max_v, min_v
        self.spn_threshold.setRange(float(min_v), float(max_v) if max_v != min_v else float(min_v) + 1.0)
        try:
            p = HeatmapStatsService.estimate_percentiles(self.layer, [90])
            p90 = p.get(90)
            if p90 is not None:
                self.spn_threshold.setValue(float(p90))
            else:
                self.spn_threshold.setValue(float(min_v + 0.75 * (max_v - min_v)))
        except Exception:
            self.spn_threshold.setValue(float(min_v + 0.75 * (max_v - min_v)))
        # Render inicial
        self.lbl_basic.setText(self._render_basic_html(s))

    def _calc_area(self):
        threshold = float(self.spn_threshold.value())
        res = HeatmapStatsService.compute_area_above(self.layer, threshold)
        html = self._render_basic_html(self._basic_stats) + self._append_result_html(threshold, res)
        self.lbl_basic.setText(html)

    def _apply_percentil(self):
        text = self.cmb_percentil.currentText().lower()
        p = int(text.replace('p', ''))
        vals = HeatmapStatsService.estimate_percentiles(self.layer, [p])
        val = vals.get(p)
        if val is not None:
            self.spn_threshold.setValue(float(val))
            self._calc_area()

    def _show_help(self):
        # Ajuda simples inline via tooltip/label
        help_text = (
            "<b>Como interpretar</b><br>"
            "- <b>Min/Max</b>: menor e maior intensidade do raster.\n<br>"
            "- <b>Média/Desvio</b>: estatísticas descritivas dos pixels válidos.\n<br>"
            "- <b>Percentil</b>: p90 é o valor abaixo do qual estão 90% dos pixels.\n<br>"
            "- <b>Limite</b>: valor usado para calcular quanto do mapa está acima.\n<br>"
            "- <b>Pixels/Área/Cobertura</b>: contagem, área (px_area) e % de pixels acima do Limite."
        )
        self.lbl_basic.setText(self._render_basic_html(self._basic_stats) + help_text)


