"""
Modelo para parâmetros do heatmap
Contém configurações e otimizações de parâmetros
"""

from dataclasses import dataclass
from typing import Dict, Any
from qgis.core import QgsProject, QgsPointXY
from qgis.core import QgsUnitTypes, QgsDistanceArea


@dataclass
class HeatmapParameters:
    """Classe para parâmetros do heatmap"""
    
    radius: int
    pixel_size: float
    transparent: int
    weight_field: str
    kernel: int
    decay: int
    output_value: int
    description: str
    
    @classmethod
    def get_optimized_parameters(cls, feature_count: int) -> 'HeatmapParameters':
        """
        Retorna parâmetros otimizados baseado no número de features
        
        Args:
            feature_count: Número de features na camada
        
        Returns:
            HeatmapParameters: Parâmetros otimizados
        """
        # Corrigir contagem inválida (-1 ou None)
        if feature_count is None or feature_count < 0:
            feature_count = 0
            print("Aviso: Não foi possível contar as features, usando parâmetros padrão")
        
        if feature_count > 10000:
            return cls(
                radius=75,
                pixel_size=3.0,
                transparent=60,
                weight_field='',
                kernel=0,  # Quartic
                decay=0,
                output_value=0,  # Raw
                description='Muitos pontos - Performance otimizada'
            )
        elif feature_count > 1000:
            return cls(
                radius=50,
                pixel_size=2.0,
                transparent=60,
                weight_field='',
                kernel=0,
                decay=0,
                output_value=0,
                description='Muitos pontos - Qualidade média'
            )
        else:
            return cls(
                radius=30,
                pixel_size=1.0,
                transparent=60,
                weight_field='',
                kernel=0,
                decay=0,
                output_value=0,
                description='Poucos pontos - Alta qualidade'
            )
    
    @classmethod
    def get_fast_parameters(cls) -> 'HeatmapParameters':
        """
        Retorna parâmetros para versão rápida do heatmap
        
        Returns:
            HeatmapParameters: Parâmetros otimizados para velocidade
        """
        return cls(
            radius=100,
            pixel_size=1.0,
            transparent=60,
            weight_field='',
            kernel=0,
            decay=0,
            output_value=0,
            description='Versão rápida - Máxima performance'
        )
    
    def to_processing_params(self, input_layer) -> Dict[str, Any]:
        """
        Converte para parâmetros do processing do QGIS
        
        Args:
            input_layer: Camada de entrada
        
        Returns:
            Dict: Parâmetros para processing.runAndLoadResults
        """
        # Converter valores em metros para unidades da camada quando necessário
        radius_mu = float(self.radius)
        pixel_mu = float(self.pixel_size)
        try:
            crs = input_layer.crs()
            if crs.isGeographic():
                # Aproximação local usando elipsóide: converte metros -> graus no centro da camada
                d = QgsDistanceArea()
                d.setSourceCrs(crs, QgsProject.instance().transformContext())
                try:
                    d.setEllipsoid(crs.ellipsoidAcronym())
                except Exception:
                    pass
                extent = input_layer.extent()
                center = QgsPointXY(extent.center().x(), extent.center().y())
                # delta lon para deslocamento leste
                p_east = d.computeSpheroidProject(center, 90.0, float(self.radius))
                p_east_px = d.computeSpheroidProject(center, 90.0, float(self.pixel_size))
                dx_radius = abs(p_east.x() - center.x())
                dx_pixel = abs(p_east_px.x() - center.x())
                # delta lat para deslocamento norte (usa o maior para garantir cobertura)
                p_north = d.computeSpheroidProject(center, 0.0, float(self.radius))
                p_north_px = d.computeSpheroidProject(center, 0.0, float(self.pixel_size))
                dy_radius = abs(p_north.y() - center.y())
                dy_pixel = abs(p_north_px.y() - center.y())
                radius_mu = max(dx_radius, dy_radius)
                pixel_mu = max(dx_pixel, dy_pixel)
            else:
                # Se for projetado mas não em metros, converte fator para metros
                try:
                    unit = crs.mapUnits()
                    factor = QgsUnitTypes.fromUnitToUnitFactor(QgsUnitTypes.DistanceMeters, unit)
                    radius_mu = float(self.radius) * factor
                    pixel_mu = float(self.pixel_size) * factor
                except Exception:
                    radius_mu = float(self.radius)
                    pixel_mu = float(self.pixel_size)
        except Exception:
            radius_mu = float(self.radius)
            pixel_mu = float(self.pixel_size)

        return {
            'INPUT': input_layer,
            'RADIUS': radius_mu,
            'PIXEL_SIZE': pixel_mu,
            'TRANSPARENT': self.transparent,
            'WEIGHT_FIELD': self.weight_field,
            'KERNEL': self.kernel,
            'DECAY': self.decay,
            'OUTPUT_VALUE': self.output_value,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }
