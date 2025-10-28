"""
Serviço para cálculo de estatísticas de heatmaps (camadas raster).

Objetivo prático:
- Resumir o raster (min, max, média, desvio) para calibrar simbologia e thresholds.
- Estimar percentis (p50/p75/p90/p95) via histograma para sugerir limites “automáticos”.
- Calcular área e cobertura acima de um limite (threshold) para comunicar resultado em m² e %.

Design:
- Usa `bandStatistics` com flags completos e a extensão da camada para resultados consistentes.
- Usa histograma do provedor para aproximar percentis e contagens acima de limiar.
- Compatível com diferentes versões do QGIS via `_hist_counts` (normaliza o acesso às contagens).
"""

from typing import Dict, Any, List, Tuple
from qgis.core import QgsRasterLayer


class HeatmapStatsService:
    @staticmethod
    def _hist_counts(h) -> List[int]:
        """Retorna a lista de contagens do histograma `h` de forma robusta.

        Por que existe:
        - QGIS muda o nome/forma de acessar os valores do histograma entre versões.
        - Esta função tenta múltiplas opções (atributos ou métodos) e sempre devolve `List[int]`.
        """
        for attr in ("histogramVector", "values", "counts"):
            vec = getattr(h, attr, None)
            if vec is None:
                getter = getattr(h, attr, None)
                try:
                    if callable(getter):
                        vec = getter()
                except Exception:
                    vec = None
            if vec is not None:
                try:
                    return [int(x) for x in list(vec)]
                except Exception:
                    pass
        return []

    @staticmethod
    def compute_basic_stats(layer: QgsRasterLayer) -> Dict[str, Any]:
        """Obtém estatísticas básicas do raster.

        Retorna:
        - min, max: faixa de valores (para simbologia/normalização).
        - mean, stddev: tendência central e dispersão (diagnóstico de outliers/caudas).
        - sum, count: agregados úteis; `count` permite validar histogramas.
        - pixel_area: área de 1 pixel (para converter contagem em m²).
        """
        provider = layer.dataProvider()
        try:
            from qgis.core import QgsRasterBandStats
            stats = provider.bandStatistics(1, QgsRasterBandStats.All, layer.extent(), 0)
        except Exception:
            stats = provider.bandStatistics(1)
        pixel_size_x = getattr(layer, 'rasterUnitsPerPixelX', lambda: None)()
        pixel_size_y = getattr(layer, 'rasterUnitsPerPixelY', lambda: None)()
        pixel_area = None
        try:
            if pixel_size_x and pixel_size_y:
                pixel_area = abs(pixel_size_x * pixel_size_y)
        except Exception:
            pixel_area = None

        result = {
            'min': stats.minimumValue,
            'max': stats.maximumValue,
            'mean': getattr(stats, 'mean', None),
            'stddev': getattr(stats, 'stdDev', None),
            'sum': getattr(stats, 'sum', None),
            'count': getattr(stats, 'elementCount', None),
            'pixel_area': pixel_area,
        }
        print(f"[CTCO] Basic stats: min={result['min']} max={result['max']} mean={result['mean']} std={result['stddev']} count={result['count']} px_area={result['pixel_area']}")
        return result

    @staticmethod
    def compute_histogram(layer: QgsRasterLayer, bins: int = 20) -> List[Tuple[float, int]]:
        """Calcula histograma (centro do bin, contagem) com `bins` intervalos.

        Por que usar: base para estimar percentis e thresholds sem ler todos os pixels.
        """
        provider = layer.dataProvider()
        h = None
        try:
            h = provider.histogram(1, layer.extent(), 0, True, bins)
        except Exception:
            try:
                h = provider.histogram(1, bins)
            except Exception:
                h = None
        buckets: List[Tuple[float, int]] = []
        try:
            if h is not None:
                counts = HeatmapStatsService._hist_counts(h)
                bin_count = min(int(getattr(h, 'binCount', len(counts)) or 0), len(counts))
                if bin_count <= 0 and len(counts) > 0:
                    bin_count = len(counts)
                for i in range(bin_count):
                    value = h.minimum + (i + 0.5) * (h.maximum - h.minimum) / max(1, bin_count)
                    count = counts[i]
                    buckets.append((value, int(count)))
        except Exception:
            try:
                from qgis.core import QgsRasterBandStats
                stats = provider.bandStatistics(1, QgsRasterBandStats.All, layer.extent(), 0)
            except Exception:
                stats = provider.bandStatistics(1)
            buckets = [(stats.minimumValue, 0), (stats.maximumValue, 0)]
        total = sum(c for _, c in buckets)
        print(f"[CTCO] Histograma: bins={len(buckets)} total={total}")
        return buckets

    @staticmethod
    def estimate_percentiles(layer: QgsRasterLayer, percentiles: List[float]) -> Dict[float, float]:
        """Estima percentis a partir da CDF do histograma.

        Intuição: p90 é o valor que deixa ~90% dos pixels abaixo. Útil como limite “automático”
        para destacar hotspots sem escolher um número arbitrário.
        """
        hist = HeatmapStatsService.compute_histogram(layer, bins=128)
        total = sum(count for _, count in hist) or 1
        cdf: List[Tuple[float, float]] = []
        acc = 0
        for value, count in hist:
            acc += count
            cdf.append((value, acc / total))
        results: Dict[float, float] = {}
        for p in percentiles:
            target = p / 100.0
            val = cdf[-1][0] if cdf else None
            for value, cp in cdf:
                if cp >= target:
                    val = value
                    break
            if val is not None:
                results[p] = val
        print(f"[CTCO] Percentis solicitados={percentiles} -> {results}")
        return results

    @staticmethod
    def compute_area_above(layer: QgsRasterLayer, threshold: float) -> Dict[str, Any]:
        """Calcula pixels, área (m²) e cobertura (%) acima de `threshold`.

        Como:
        - Conta via histograma quantos pixels caem acima do limiar.
        - Converte em área multiplicando por `pixel_area` (tamanho do pixel em m²).
        - Cobertura é a fração sobre o total de pixels válidos.
        """
        provider = layer.dataProvider()
        try:
            from qgis.core import QgsRasterBandStats
            stats = provider.bandStatistics(1, QgsRasterBandStats.All, layer.extent(), 0)
        except Exception:
            stats = provider.bandStatistics(1)
        pixel_size_x = getattr(layer, 'rasterUnitsPerPixelX', lambda: None)()
        pixel_size_y = getattr(layer, 'rasterUnitsPerPixelY', lambda: None)()
        pixel_area = None
        try:
            if pixel_size_x and pixel_size_y:
                pixel_area = abs(pixel_size_x * pixel_size_y)
        except Exception:
            pixel_area = None

        above_count = 0
        total_hist = 0
        try:
            h = provider.histogram(1, layer.extent(), 0, True, 64)
        except Exception:
            try:
                h = provider.histogram(1, 64)
            except Exception:
                h = None
        if h is not None:
            counts = HeatmapStatsService._hist_counts(h)
            bin_count = min(int(getattr(h, 'binCount', len(counts)) or 0), len(counts))
            if bin_count <= 0 and len(counts) > 0:
                bin_count = len(counts)
            for i in range(bin_count):
                bin_min = h.minimum + i * (h.maximum - h.minimum) / max(1, bin_count)
                bin_max = h.minimum + (i + 1) * (h.maximum - h.minimum) / max(1, bin_count)
                count = int(counts[i])
                total_hist += count
                if bin_max <= threshold:
                    continue
                if bin_min < threshold < bin_max and count:
                    frac = (bin_max - threshold) / (bin_max - bin_min)
                    above_count += int(round(count * frac))
                elif bin_min >= threshold:
                    above_count += count
        area_m2 = above_count * pixel_area if pixel_area else None
        coverage_pct = None
        total = getattr(stats, 'elementCount', None)
        if (not total or total <= 0) and total_hist > 0:
            total = total_hist
        if total and total > 0:
            coverage_pct = (above_count / total) * 100.0

        result = {
            'threshold': threshold,
            'pixels_above': above_count,
            'area_m2': area_m2,
            'coverage_pct': coverage_pct,
        }
        print(f"[CTCO] Area above {threshold}: pixels={above_count} area_m2={area_m2} coverage={coverage_pct}")
        return result


