"""
Algoritmo de setColor para o plugin CTCO
Contém implementação específica do algoritmo de setColor
"""

from ..services.color_service import ColorService

class SetColorAlgorithm:
    # Classe para algoritimos do setColor

    @staticmethod
    def run_setColor(layer, config=None):
        """
        Executa algoritmo de SetColor
        
        Args:
            layer: Camada de pontos para processar
            config: Dicionário de configuração opcional (paleta, opacity)
        """    
        # Se config é um dicionário, extrair a paleta e aplicar via apply_colormap
        if isinstance(config, dict):
            palette_name = config.get('palette', 'BCYR')
            # Aceitar tanto 'opacity' (0..1) quanto 'transparent' (0..100)
            if 'opacity' in config:
                try:
                    opacity = float(config.get('opacity', 0.6))
                except Exception:
                    opacity = 0.6
            else:
                # Transparência (%) -> Opacidade (0..1): opacity = 1 - (transparent/100)
                try:
                    transparent_pct = float(config.get('transparent', 60))
                    opacity = max(0.0, min(1.0,(transparent_pct / 100.0)))
                except Exception:
                    opacity = 0.6

            ColorService.apply_colormap(layer, name=palette_name, opacity=opacity)
        else:
            # Se config é um QgsColorRampShader, aplicar diretamente
            ColorService.apply_color_ramp_to_layer(layer, config)