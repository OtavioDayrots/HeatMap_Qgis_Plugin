"""
Definições de paletas e utilitários de transformação de posições
"""

from qgis.PyQt.QtGui import QColor


def bcyr_template():
    return [
        (0.00, QColor(0, 0, 139)),
        (0.15, QColor(0, 80, 180)),
        (0.30, QColor(0, 150, 255)),
        (0.45, QColor(120, 255, 120)),
        (0.50, QColor(255, 255, 120)),
        (0.80, QColor(255, 150, 0)),
        (1.00, QColor(255, 0, 0)),
    ]


def heatmap_template():
    return [
        (0.00, QColor(0, 0, 128)),
        (0.20, QColor(0, 0, 255)),
        (0.40, QColor(0, 128, 255)),
        (0.60, QColor(128, 255, 128)),
        (0.80, QColor(255, 255, 0)),
        (1.00, QColor(255, 0, 0)),
    ]


def viridis_template():
    return [
        (0.00, QColor(68, 1, 84)),
        (0.20, QColor(59, 82, 139)),
        (0.40, QColor(33, 144, 140)),
        (0.60, QColor(92, 200, 99)),
        (0.80, QColor(253, 231, 37)),
        (1.00, QColor(255, 255, 255)),
    ]


def plasma_template():
    return [
        (0.00, QColor(13, 8, 135)),
        (0.20, QColor(75, 3, 161)),
        (0.40, QColor(125, 3, 168)),
        (0.60, QColor(168, 34, 150)),
        (0.80, QColor(203, 70, 121)),
        (1.00, QColor(240, 249, 33)),
    ]


def inferno_template():
    return [
        (0.00, QColor(0, 0, 4)),
        (0.20, QColor(31, 12, 72)),
        (0.40, QColor(85, 15, 109)),
        (0.60, QColor(136, 34, 94)),
        (0.80, QColor(186, 54, 85)),
        (1.00, QColor(252, 255, 164)),
    ]


PALETTES = {
    "bcyr": bcyr_template,
    "heatmap": heatmap_template,
    "viridis": viridis_template,
    "plasma": plasma_template,
    "inferno": inferno_template,
}


def apply_scale_positions(template, mode: str):
    if mode == "log":
        import math
        adjusted = []
        for pos, color in template:
            p = max(1e-6, min(1.0, float(pos)))
            y = math.log10(1 + 9 * p)
            adjusted.append((y, color))
        return adjusted
    return template


# Utilitários para redistribuição de stops próximo ao máximo
def _interpolate_color(c1: QColor, c2: QColor, t: float) -> QColor:
    r = int(round(c1.red() + (c2.red() - c1.red()) * t))
    g = int(round(c1.green() + (c2.green() - c1.green()) * t))
    b = int(round(c1.blue() + (c2.blue() - c1.blue()) * t))
    a = int(round(c1.alpha() + (c2.alpha() - c1.alpha()) * t))
    return QColor(r, g, b, a)


def redistribute_for_max(template):
    """Rebalanceia posições para melhor gradação próximo ao máximo sem alterar a escala.

    Insere stops em posições canônicas (com maior densidade no topo) e interpola
    as cores a partir do template de entrada, preservando as cores originais.
    """
    if not template:
        return template
    tpl = sorted(template, key=lambda x: float(x[0]))
    targets = [
        0.00, 0.10, 0.22, 0.38,
        0.47, 0.55, 0.65, 0.70,
        0.77, 0.84, 0.86, 0.92,
        0.94, 0.97, 0.98, 1.00
    ]
    existing = {float(p): c for p, c in tpl}

    def color_at(p: float) -> QColor:
        p = max(0.0, min(1.0, float(p)))
        if p in existing:
            return existing[p]
        left_p, left_c = tpl[0]
        right_p, right_c = tpl[-1]
        for i in range(len(tpl) - 1):
            p1, c1 = tpl[i]
            p2, c2 = tpl[i + 1]
            if p1 <= p <= p2:
                left_p, left_c = p1, c1
                right_p, right_c = p2, c2
                break
        span = max(1e-9, float(right_p) - float(left_p))
        t = (p - float(left_p)) / span
        return _interpolate_color(left_c, right_c, t)

    combined = []
    used = set()
    for p, c in tpl:
        pf = float(p)
        if pf not in used:
            combined.append((pf, c))
            used.add(pf)
    for p in targets:
        if p not in used:
            combined.append((p, color_at(p)))
            used.add(p)
    combined.sort(key=lambda x: x[0])
    return combined

