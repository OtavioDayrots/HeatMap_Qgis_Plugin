"""
Algoritmo de heatmap para o plugin CTCO
Contém implementação específica do algoritmo de heatmap
"""

from ..services.heatmap_service import HeatmapService


class HeatmapAlgorithm:
    """Classe para algoritmos de mapa de calor"""
    
    @staticmethod
    def run_heatmap(layer, config=None):
        """
        Executa algoritmo de mapa de calor com parâmetros otimizados
        
        Args:
            layer: Camada de pontos para processar
            config: Dicionário de configuração opcional (raio, pixel, kernel, paleta, min/max)
        """
        HeatmapService.run_heatmap(layer, config)
    
    @staticmethod
    def run_heatmap_fast(layer):
        """
        Executa algoritmo de mapa de calor rápido
        
        Args:
            layer: Camada de pontos para processar
        """
        HeatmapService.run_heatmap_fast(layer)
