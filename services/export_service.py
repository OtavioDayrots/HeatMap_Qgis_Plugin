from qgis.core import (
    QgsProject,
    QgsPrintLayout,
    QgsLayoutItemMap,
    QgsLayoutSize,
    QgsLayoutPoint,
    QgsUnitTypes,
    QgsLayoutItemScaleBar,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutExporter,
    QgsLayoutItemPage,
)
from qgis.PyQt.QtWidgets import QFileDialog, QMessageBox
from qgis.PyQt.QtCore import Qt
from datetime import datetime
import os

class ExportService:

    @staticmethod
    def export_map_canvas(iface):
        png_path, _ = QFileDialog.getSaveFileName(None, "Salvar mapa (PNG)", "", "PNG (*.png)")
        if not png_path:
            return
        try:
            iface.mapCanvas().saveAsImage(png_path)
            QMessageBox.information(None, "Sucesso", f"Mapa salvo em: \n {png_path}")
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Falha ao salvar mapa: {str(e)}")

    @staticmethod
    def export_map_with_options(iface, options):
        filters = {
            "GEOTIFF": "GeoTIFF (*.tif *.tiff)",
            "PNG": "PNG (*.png)",
            "JPEG": "JPEG (*.jpg *.jpeg)",
            "SVG": "SVG (*.svg)",
            "PDF": "PDF (*.pdf)",
        }
        path, _ = QFileDialog.getSaveFileName(None, "Salvar mapa", "", filters.get(options.fmt, "PNG (*.png)"))
        if not path:
            return

        # Garantir extensão conforme formato escolhido
        ext_map = {"GEOTIFF": ".tif", "PNG": ".png", "JPEG": ".jpg", "SVG": ".svg", "PDF": ".pdf"}
        desired_ext = ext_map.get(options.fmt, ".png")
        base, ext = os.path.splitext(path)
        if not ext:
            path = base + desired_ext

        project = QgsProject.instance()
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        layout.setName("CTCO_Export_Temp")

        # Página padrão do layout (não alterar tamanho/orientação para manter compatibilidade)
        page = layout.pageCollection().page(0)
        page_size = page.pageSize()  # QgsLayoutSize em mm
        page_width = page_size.width()
        page_height = page_size.height()

        # Mapa ocupando a página com margens e um rodapé reservado para legenda/escala/data
        margin_mm = 5.0
        footer_height_mm = 60.0  # área branca inferior para elementos cartográficos
        map_width = page_width - (2 * margin_mm)
        map_height = page_height - (2 * margin_mm) - footer_height_mm
        map_item = QgsLayoutItemMap(layout)
        map_item.setFrameEnabled(bool(getattr(options, "include_border", True)))
        layout.addLayoutItem(map_item)
        map_item.attemptMove(QgsLayoutPoint(margin_mm, margin_mm, QgsUnitTypes.LayoutMillimeters))
        map_item.attemptResize(QgsLayoutSize(map_width, map_height, QgsUnitTypes.LayoutMillimeters))
        map_item.setExtent(iface.mapCanvas().extent())

        # Barra de escala
        if getattr(options, "include_scalebar", True):
            scalebar = QgsLayoutItemScaleBar(layout)
            scalebar.setLinkedMap(map_item)
            scalebar.setStyle("Single Box")
            scalebar.setNumberOfSegments(4)
            scalebar.setNumberOfSegmentsLeft(0)
            scalebar.setUnits(QgsUnitTypes.DistanceMeters)
            scalebar.setUnitLabel("m")
            scalebar.refresh()
            layout.addLayoutItem(scalebar)
            # posicionar na área branca inferior, à direita da legenda
            scalebar.attemptMove(QgsLayoutPoint(margin_mm + 65.0, page_height - margin_mm - 6, QgsUnitTypes.LayoutMillimeters))

        # Legenda
        if getattr(options, "include_legend", True):
            legend = QgsLayoutItemLegend(layout)
            legend.setTitle("Legenda")
            legend.setLinkedMap(map_item)
            legend.setBackgroundEnabled(True)
            legend.setFrameEnabled(True)
            # Estilos mais compactos
            symbol_size_mm = 4.0
            legend.setSymbolWidth(symbol_size_mm)
            legend.setSymbolHeight(symbol_size_mm)
            layout.addLayoutItem(legend)
            # posicionar na área branca inferior, à esquerda, sem sobrepor escala/data
            legend_height = max(30.0, footer_height_mm - 10.0)
            legend.attemptResize(QgsLayoutSize(60, legend_height, QgsUnitTypes.LayoutMillimeters))
            legend.attemptMove(
                QgsLayoutPoint(
                    margin_mm,
                    margin_mm + map_height + 2.0,
                    QgsUnitTypes.LayoutMillimeters,
                )
            )

        # Carimbo de data
        if getattr(options, "include_timestamp", True):
            label = QgsLayoutItemLabel(layout)
            label.setText(datetime.now().strftime("%Y-%m-%d %H:%M"))
            label.adjustSizeToText()
            layout.addLayoutItem(label)
            label.attemptMove(QgsLayoutPoint(page_width - margin_mm - 35, page_height - margin_mm - 6, QgsUnitTypes.LayoutMillimeters))

        # Exportação por formato
        exporter = QgsLayoutExporter(layout)
        if options.fmt == "GEOTIFF":
            # Exporta o canvas do mapa como GeoTIFF, preservando georreferência
            try:
                from qgis.core import QgsRasterFileWriter, QgsRectangle
                from qgis.gui import QgsMapSettings
            except Exception:
                pass
            # fallback: usar API do canvas direto
            ms = iface.mapCanvas().mapSettings()
            # Define extensão e tamanho baseados no layout (aproximado ao item de mapa)
            img_settings = QgsLayoutExporter.ImageExportSettings()
            img_settings.dpi = int(getattr(options, "dpi", 300))
            tmp_png = os.path.splitext(path)[0] + "__tmp__.png"
            res = exporter.exportToImage(tmp_png, img_settings)
            if res != QgsLayoutExporter.Success:
                QMessageBox.critical(None, "Erro", f"Falha ao exportar raster temporário. Código: {res}\nCaminho: {tmp_png}")
                return
            try:
                # Usa GDAL para gravar como GeoTIFF com geotransform do canvas
                from osgeo import gdal
                extent = map_item.extent()
                width_px = int(img_settings.dpi * (map_item.rect().width() / 25.4))
                height_px = int(img_settings.dpi * (map_item.rect().height() / 25.4))
                ds = gdal.Open(tmp_png)
                if ds is None:
                    raise RuntimeError("GDAL não abriu PNG temporário")
                driver = gdal.GetDriverByName("GTiff")
                out = driver.CreateCopy(path, ds, 0)
                if out is None:
                    raise RuntimeError("Falha ao criar GeoTIFF")
                # Georreferência aproximada do canvas
                gt = [extent.xMinimum(), (extent.width()/width_px), 0, extent.yMaximum(), 0, -(extent.height()/height_px)]
                out.SetGeoTransform(gt)
                if ms.destinationCrs().toWkt():
                    out.SetProjection(ms.destinationCrs().toWkt())
                out.FlushCache()
                del out
            except Exception as e:
                QMessageBox.critical(None, "Erro", f"Falha ao gravar GeoTIFF: {str(e)}")
                try:
                    os.remove(tmp_png)
                except Exception:
                    pass
                return
            try:
                os.remove(tmp_png)
            except Exception:
                pass
        elif options.fmt in ("PNG", "JPEG"):
            img_settings = QgsLayoutExporter.ImageExportSettings()
            img_settings.dpi = int(getattr(options, "dpi", 300))
            res = exporter.exportToImage(path, img_settings)
            if res != QgsLayoutExporter.Success:
                QMessageBox.critical(None, "Erro", f"Falha ao exportar imagem. Código: {res}\nCaminho: {path}")
                return
        elif options.fmt == "SVG":
            svg_settings = QgsLayoutExporter.SvgExportSettings()
            svg_settings.dpi = int(getattr(options, "dpi", 300))
            res = exporter.exportToSvg(path, svg_settings)
            if res != QgsLayoutExporter.Success:
                QMessageBox.critical(None, "Erro", f"Falha ao exportar SVG. Código: {res}\nCaminho: {path}")
                return
        else:
            pdf_settings = QgsLayoutExporter.PdfExportSettings()
            pdf_settings.dpi = int(getattr(options, "dpi", 300))
            res = exporter.exportToPdf(path, pdf_settings)
            if res != QgsLayoutExporter.Success:
                QMessageBox.critical(None, "Erro", f"Falha ao exportar PDF. Código: {res}\nCaminho: {path}")
                return

        QMessageBox.information(None, "Sucesso", f"Mapa exportado em:\n{path}")