import os
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox


class ImportService:

    @staticmethod
    def import_map(parent=None):
        """Abre diálogo para escolher um arquivo qgis e adiciona ao projeto."""
        try:
            filter_str = (
                "Todos (*.*);;"
                "Projeto QGIS (*.qgs *.qgz);;"
                "Raster (*.tif *.tiff *.img *.jpg *.jpeg *.png);;"
                "Vetorial (*.gpkg *.shp *.geojson *.json *.kml *.gpx)"
            )
            path, _ = QFileDialog.getOpenFileName(parent, "Importar camada ou projeto", "", filter_str)
            if not path:
                return

            # Verificar se é um projeto QGIS
            if path.endswith('.qgs') or path.endswith('.qgz'):
                # Carregar projeto QGIS
                if QgsProject.instance().read(path):
                    QMessageBox.information(parent, "Sucesso", f"Projeto QGIS importado: {path}")
                else:
                    QMessageBox.critical(parent, "Erro", f"Falha ao carregar projeto: {path}")
                return

            # Tentar raster primeiro
            layer = QgsRasterLayer(path, os.path.basename(path))
            if not layer.isValid():
                # Tentar vetor (usar provider 'ogr')
                layer = QgsVectorLayer(path, os.path.basename(path), "ogr")

            if not layer or not layer.isValid():
                QMessageBox.critical(parent, "Erro", f"Falha ao carregar camada: {path}")
                return

            QgsProject.instance().addMapLayer(layer)
            QMessageBox.information(parent, "Sucesso", f"Camada importada: {path}")
        except Exception as e:
            QMessageBox.critical(parent, "Erro", f"Erro ao importar camada: {str(e)}")


