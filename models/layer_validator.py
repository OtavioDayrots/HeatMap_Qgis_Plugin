"""
Modelo para validação de camadas
Contém lógica de validação de tipos de camadas
"""

from qgis.core import QgsWkbTypes, QgsMapLayer


class LayerValidator:
    """Classe para validação de camadas do QGIS"""
    
    @staticmethod
    def validate_layer(layer, required_type=None, required_geometry=None):
        """
        Valida se a camada ativa atende aos requisitos
        
        Args:
            layer: Camada ativa do QGIS
            required_type: Tipo de camada requerido (QgsMapLayer.VectorLayer, etc.)
            required_geometry: Tipo de geometria requerido (QgsWkbTypes.PointGeometry, etc.)
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not layer:
            return False, "Nenhuma camada ativa encontrada!"
        
        if required_type and layer.type() != required_type:
            return False, f"Esta ferramenta só funciona com camadas {LayerValidator._get_layer_type_name(required_type)}."
        
        if required_geometry and layer.geometryType() != required_geometry:
            return False, f"Esta ferramenta só funciona com camadas de {LayerValidator._get_geometry_type_name(required_geometry)}."
        
        return True, ""
    
    @staticmethod
    def _get_layer_type_name(layer_type):
        """Converte tipo de camada para nome legível"""
        type_names = {
            QgsMapLayer.VectorLayer: "vetoriais",
            QgsMapLayer.RasterLayer: "raster",
            QgsMapLayer.PluginLayer: "plugin"
        }
        return type_names.get(layer_type, "desconhecidas")
    
    @staticmethod
    def _get_geometry_type_name(geometry_type):
        """Converte tipo de geometria para nome legível"""
        geometry_names = {
            QgsWkbTypes.PointGeometry: "pontos",
            QgsWkbTypes.LineGeometry: "linhas",
            QgsWkbTypes.PolygonGeometry: "polígonos"
        }
        return geometry_names.get(geometry_type, "desconhecidas")
    
    @staticmethod
    def get_feature_count(layer):
        """
        Obtém contagem robusta de features
        
        Args:
            layer: Camada do QGIS
        
        Returns:
            int: Número de features
        """
        # Verificar se é uma camada vetorial antes de contar features
        if layer.type() != QgsMapLayer.VectorLayer:
            print("Aviso: Tentativa de contar features em camada não-vetorial")
            return 0
        
        try:
            # Log auxiliar para depuração de tipo/nome da camada
            try:
                layer_name = getattr(layer, 'name', lambda: '<sem nome>')()
                print(f"Contando features na camada: {layer_name} (type={layer.type()}, geom={layer.geometryType()})")
            except Exception:
                pass

            feature_count = layer.featureCount()
            # Quando a contagem é 0 ou negativa, há provedores que atrasam; validar manualmente
            if feature_count is None or feature_count <= 0:
                manual = 0
                try:
                    manual = sum(1 for _ in layer.getFeatures())
                except Exception:
                    manual = feature_count or 0
                if manual is not None:
                    feature_count = manual
                    print(f"Contagem manual de features aplicada: {feature_count}")
            else:
                print(f"Número de features: {feature_count}")

            return int(feature_count or 0)
            
        except Exception as e:
            print(f"Erro ao contar features: {e}")
            return 0
