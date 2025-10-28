"""
Funções utilitárias para processamento de heatmap (reuso e testes fáceis)
"""

from qgis.core import QgsMapLayer, QgsProject, QgsRasterLayer
import os


def estimate_dynamic_radius(layer, feature_count: int) -> int:
    try:
        extent = layer.extent()
        area_m2 = max(1.0, extent.width() * extent.height())
        points = max(1, feature_count or 1)
        density = points / area_m2
        import math
        k = 250.0
        base = 35.0
        return int(max(30.0, min(180.0, k / math.sqrt(max(density, 1e-9)) + base)))
    except Exception:
        return 50


def resolve_output_layer(ref):
    # Já é camada
    if hasattr(ref, 'type'):
        return ref
    # Tentar por ID no projeto
    lyr = None
    try:
        lyr = QgsProject.instance().mapLayer(str(ref))
    except Exception:
        lyr = None
    if lyr:
        return lyr
    # Tentar como caminho
    try:
        path = str(ref)
        if os.path.exists(path):
            for existing in QgsProject.instance().mapLayers().values():
                try:
                    if isinstance(existing, QgsRasterLayer):
                        src = existing.source()
                        if src == path or src.endswith(os.path.basename(path)):
                            return existing
                except Exception:
                    continue
            new_layer = QgsRasterLayer(path, os.path.basename(path))
            if new_layer.isValid():
                return new_layer
    except Exception:
        pass
    return ref


