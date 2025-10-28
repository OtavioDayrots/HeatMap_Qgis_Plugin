"""
Serviço de heatmap para o plugin CTCO
Contém lógica de negócio para processamento de heatmaps
"""

import os
import tempfile
import processing
from qgis.core import QgsMapLayer, QgsWkbTypes, QgsProject, QgsRasterLayer
from qgis.PyQt.QtWidgets import QMessageBox, QProgressDialog, QProgressBar, QFileDialog
from qgis.PyQt.QtCore import Qt, QCoreApplication, QTimer

from ..models.layer_validator import LayerValidator
from ..models.heatmap_parameters import HeatmapParameters
from .color_service import ColorService
from .heatmap_utils import estimate_dynamic_radius, resolve_output_layer
from .export_service import ExportService


class HeatmapService:
    """Serviço para processamento de heatmaps"""
    
    @staticmethod
    def _apply_palette_with_retry(output_layer, config=None, attempts=5, delay_ms=150):
        """Aplica a paleta com pequenas tentativas para evitar render cinza.

        Por que: o raster pode ainda estar inicializando quando o renderer é setado.
        Ao aguardar alguns ciclos do event loop, garantimos que a simbologia seja aplicada.
        """
        if attempts <= 0 or not output_layer:
            return

        def do_apply():
            try:
                if not hasattr(output_layer, 'type') or output_layer.type() != QgsMapLayer.RasterLayer:
                    print(f"Aviso: camada de saída não é raster ou inválida: {type(output_layer)}")
                    return
                palette_name = (config or {}).get("palette", "BCYR")
                scale_mode = (config or {}).get("scale", "linear")
                print(f"Aplicando paleta='{palette_name}' escala='{scale_mode}' (tentativas restantes={attempts})")
                ColorService.apply_colormap(output_layer, name=palette_name, scale_mode=scale_mode)
                # Aplicar transparência (config['transparent'] em %) se fornecido
                try:
                    transparent_pct = None
                    if isinstance(config, dict):
                        transparent_pct = config.get("transparent")
                        if transparent_pct is None:
                            transparent_pct = config.get("opacity_percent")
                    if transparent_pct is not None:
                        try:
                            pct = max(0.0, min(100.0, float(transparent_pct)))
                            opacity = (pct / 100.0)
                            applied = False
                            if hasattr(output_layer, 'setOpacity'):
                                output_layer.setOpacity(opacity)
                                applied = True
                            # Fallback via renderer
                            try:
                                renderer = getattr(output_layer, 'renderer', lambda: None)()
                                if renderer and hasattr(renderer, 'setOpacity'):
                                    renderer.setOpacity(opacity)
                                    applied = True
                            except Exception:
                                pass
                            if applied:
                                print(f"Transparência aplicada: {pct}% (opacidade={opacity:.2f})")
                        except Exception as _t:
                            print(f"Falha ao aplicar transparência: {_t}")
                except Exception:
                    pass
                output_layer.triggerRepaint()
            except Exception as e:
                print(f"Tentativa de aplicar paleta falhou: {e}")
                if attempts - 1 > 0:
                    QTimer.singleShot(delay_ms, lambda: HeatmapService._apply_palette_with_retry(output_layer, config, attempts - 1, delay_ms))

        QTimer.singleShot(0, do_apply)

    @staticmethod
    def run_heatmap(layer, config=None):
        """
        Executa algoritmo de mapa de calor com parâmetros otimizados
        
        Args:
            layer: Camada de pontos para processar
            config: Dicionário de configuração opcional (raio, pixel, kernel, paleta, min/max)
        """
        try:
            # Verificar se há camada ativa
            if not layer:
                QMessageBox.warning(None, "Aviso", "Nenhuma camada ativa encontrada!")
                return
            
            # Validar se é camada vetorial
            if layer.type() != QgsMapLayer.VectorLayer:
                if layer.type() == QgsMapLayer.RasterLayer:
                    QMessageBox.warning(None, "Aviso", "Você selecionou um heatmap existente!\n\nPara criar um novo heatmap:\n1. No painel de camadas, clique na camada de pontos original\n2. Depois clique novamente em 'Mapa de Calor'")
                else:
                    QMessageBox.warning(None, "Aviso", "O Mapa de Calor só funciona com camadas vetoriais!\nSelecione uma camada de pontos.")
                return
            
            # Validar geometria de pontos
            is_valid, error_msg = LayerValidator.validate_layer(
                layer,
                required_geometry=QgsWkbTypes.PointGeometry
            )
            if not is_valid:
                QMessageBox.warning(None, "Aviso", error_msg)
                return
            
            # Aplicar filtro se fornecido (na camada original)
            filtered_layer = layer
            filter_expr = (config or {}).get("filter_expr") if config else None
            if filter_expr:
                try:
                    prev_subset = ""
                    try:
                        if hasattr(layer, 'subsetString'):
                            prev_subset = layer.subsetString() or ""
                    except Exception:
                        prev_subset = ""
                    # Tentar aplicar diretamente como subset do provedor
                    if hasattr(layer, 'setSubsetString'):
                        layer.setSubsetString(str(filter_expr))
                        filtered_layer = layer
                        print(f"Subset aplicado na camada original: {filter_expr}")
                    else:
                        raise Exception("Camada não suporta subsetString")
                except Exception as e:
                    print(f"Falha ao aplicar subsetString; tentando extrair por expressão: {e}")
                    # Fallback: usar camada temporária filtrada (não altera original)
                    try:
                        import processing
                        params = {
                            'INPUT': layer,
                            'EXPRESSION': str(filter_expr),
                            'OUTPUT': 'TEMPORARY_OUTPUT'
                        }
                        res = processing.run("native:extractbyexpression", params)
                        cand = res.get('OUTPUT')
                        if cand is not None:
                            filtered_layer = cand
                            print(f"Filtro (fallback) aplicado por expressão: {filter_expr}")
                    except Exception as e2:
                        print(f"Falha no fallback de filtro '{filter_expr}': {e2}")

            # Validação mínima de pontos (>= 3) na camada filtrada
            feature_count = LayerValidator.get_feature_count(filtered_layer)
            if feature_count is not None and feature_count < 3:
                QMessageBox.warning(None, "Aviso", "Filtro resultou em menos de 3 pontos. Ajuste o filtro.")
                return

            # Obter parâmetros (do diálogo ou otimizados)
            if config:
                parameters = HeatmapParameters(
                    radius=config.get("radius", 50),
                    pixel_size=config.get("pixel_size", 1),
                    transparent=config.get("transparent", 60),
                    weight_field='',
                    kernel=config.get("kernel", 0),
                    decay=0,
                    output_value=0,
                    description='Parâmetros personalizados'
                )
            else:
                parameters = HeatmapParameters.get_optimized_parameters(feature_count)

            # Sugerir/ajustar raio dinamicamente por densidade
            try:
                if not config or "radius" not in config:
                    parameters.radius = estimate_dynamic_radius(filtered_layer, feature_count)
            except Exception:
                pass
            
            # Mostrar mensagem de processamento
            HeatmapService._show_processing_message(feature_count, parameters)
            
            # Indicador de progresso não intrusivo na barra do QGIS
            progress = None
            bar_widget = None
            try:
                from qgis.utils import iface
                from qgis.PyQt.QtWidgets import QProgressBar
                if iface is not None and hasattr(iface, 'messageBar'):
                    bar = iface.messageBar()
                    bar_widget = QProgressBar()
                    bar_widget.setRange(0, 0)  # indeterminado
                    bar_widget.setTextVisible(False)
                    bar.pushWidget(bar_widget, level=0)
                    try:
                        QCoreApplication.processEvents()
                    except Exception:
                        pass
                else:
                    raise Exception("iface.messageBar indisponível")
            except Exception:
                # Fallback para QProgressDialog discreto
                try:
                    progress = QProgressDialog("Gerando mapa de calor...", "Ocultar", 0, 0)
                    progress.setWindowTitle("CTCO - Processando")
                    progress.setAutoClose(False)
                    progress.setAutoReset(False)
                    progress.setCancelButton(None)
                    progress.setMinimumDuration(0)
                    progress.setWindowModality(Qt.ApplicationModal)
                    progress.show()
                    try:
                        QCoreApplication.processEvents()
                    except Exception:
                        pass
                except Exception:
                    progress = None

            # Executar algoritmo (usando a camada filtrada)
            result = HeatmapService._execute_heatmap_algorithm(filtered_layer, parameters, feature_count)
            
            # Aplicar rampa de cores (padrão: BCYR). Para testar 0-30, use min_val/max_val do config
            if result and 'OUTPUT' in result:
                output_ref = result['OUTPUT']
                print(f"OUTPUT bruto do processing: {type(output_ref)} -> {output_ref}")

                output_layer = resolve_output_layer(output_ref)
                # Garantir que apenas UMA camada seja adicionada ao projeto
                try:
                    if hasattr(output_layer, 'id'):
                        prj = QgsProject.instance()
                        if prj.mapLayer(output_layer.id()) is None:
                            prj.addMapLayer(output_layer)
                except Exception:
                    pass

                # Se usuário informou uma pasta de saída, salvar cópia do raster lá
                try:
                    out_dir = (config or {}).get("output_dir") if config else None
                    if out_dir and isinstance(output_layer, QgsRasterLayer) and os.path.isdir(out_dir):
                        # Determinar nome base do arquivo
                        user_name = (config or {}).get("output_filename") if config else None
                        if user_name:
                            # Remover caminho, manter somente o nome e sanitizar caracteres inválidos básicos
                            user_name = os.path.basename(str(user_name)).strip()
                            # Substituir separadores e caracteres indesejados
                            safe_name = "".join([c if c.isalnum() or c in ("-", "_", ".", " ") else "_" for c in user_name])
                            # Garantir extensão .tif
                            if not safe_name.lower().endswith(".tif"):
                                safe_name += ".tif"
                            base_name = safe_name
                        else:
                            base_base = os.path.basename(getattr(layer, 'name', lambda: 'layer')() if hasattr(layer, 'name') else 'layer')
                            base_name = f"heatmap_{base_base}.tif"
                        out_path = os.path.join(out_dir, base_name)
                        from qgis.core import QgsRasterFileWriter
                        prov = output_layer.dataProvider()
                        src_path = output_layer.source()
                        # Tenta copiar fisicamente criando novo raster no destino
                        ok = False
                        try:
                            writer = QgsRasterFileWriter(out_path)
                            ok = writer.writeRaster(output_layer.dataProvider().clone(), output_layer.width(), output_layer.height(), output_layer.extent(), output_layer.crs()) == QgsRasterFileWriter.NoError
                        except Exception:
                            ok = False
                        if not ok:
                            try:
                                import shutil
                                if os.path.exists(src_path):
                                    shutil.copy2(src_path, out_path)
                                    ok = True
                            except Exception:
                                ok = False
                        if ok:
                            try:
                                saved_layer = QgsRasterLayer(out_path, os.path.basename(out_path))
                                if saved_layer.isValid():
                                    prj = QgsProject.instance()
                                    # Remover a camada temporária (se já estiver no projeto)
                                    try:
                                        if hasattr(output_layer, 'id') and prj.mapLayer(output_layer.id()) is not None:
                                            prj.removeMapLayer(output_layer.id())
                                    except Exception:
                                        pass
                                    prj.addMapLayer(saved_layer)
                                    output_layer = saved_layer
                                    print(f"Heatmap salvo em: {out_path}")
                            except Exception:
                                pass
                except Exception as _e:
                    print(f"Não foi possível salvar cópia do heatmap: {_e}")

                # Aplicar após o carregamento com pequenas tentativas
                HeatmapService._apply_palette_with_retry(output_layer, config or {}, attempts=6, delay_ms=150)

                # Registrar propriedades iniciais para reset
                try:
                    palette_name = (config or {}).get("palette", "BCYR")
                    scale_mode = (config or {}).get("scale", "linear")
                    output_layer.setCustomProperty("ctco_initial_palette", palette_name)
                    output_layer.setCustomProperty("ctco_initial_scale", scale_mode)
                except Exception:
                    pass
            
            try:
                if progress:
                    progress.setLabelText("Finalizando...")
                    QCoreApplication.processEvents()
            except Exception:
                pass
            QMessageBox.information(None, "Sucesso", "Mapa de calor criado com sucesso!")
            
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Erro ao executar heatmap: {str(e)}")
            print(f"Erro detalhado: {e}")
        finally:
            try:
                if bar_widget is not None:
                    from qgis.utils import iface
                    iface.messageBar().popWidget(bar_widget)
            except Exception:
                pass
            try:
                if progress:
                    progress.close()
            except Exception:
                pass
    
    @staticmethod
    def run_heatmap_fast(layer):
        """
        Executa algoritmo de mapa de calor rápido
        
        Args:
            layer: Camada de pontos para processar
        """
        try:
            # Verificar se há camada ativa
            if not layer:
                QMessageBox.warning(None, "Aviso", "Nenhuma camada ativa encontrada!")
                return
            
            # Validar se é camada vetorial
            if layer.type() != QgsMapLayer.VectorLayer:
                if layer.type() == QgsMapLayer.RasterLayer:
                    QMessageBox.warning(None, "Aviso", "Você selecionou um heatmap existente!\n\nPara criar um novo heatmap:\n1. No painel de camadas, clique na camada de pontos original\n2. Depois clique novamente em 'Mapa de Calor'")
                else:
                    QMessageBox.warning(None, "Aviso", "O Mapa de Calor Rápido só funciona com camadas vetoriais!\nSelecione uma camada de pontos.")
                return
            
            # Validar geometria de pontos
            is_valid, error_msg = LayerValidator.validate_layer(
                layer,
                required_geometry=QgsWkbTypes.PointGeometry
            )
            if not is_valid:
                QMessageBox.warning(None, "Aviso", error_msg)
                return
            
            # Obter parâmetros rápidos
            feature_count = LayerValidator.get_feature_count(layer)
            parameters = HeatmapParameters.get_fast_parameters()
            
            # Mostrar mensagem de processamento
            HeatmapService._show_processing_message(feature_count, parameters)
            
            # Executar algoritmo (sem auto-carregar no projeto para evitar duplicações)
            result = processing.run("qgis:heatmapkerneldensityestimation", 
                                    parameters.to_processing_params(layer))
            
            # Aplicar rampa com retry e registrar metadados
            if result and 'OUTPUT' in result:
                output_layer = resolve_output_layer(result['OUTPUT'])
                # Garantir inclusão única no projeto
                try:
                    if hasattr(output_layer, 'id'):
                        prj = QgsProject.instance()
                        if prj.mapLayer(output_layer.id()) is None:
                            prj.addMapLayer(output_layer)
                except Exception:
                    pass
                HeatmapService._apply_palette_with_retry(output_layer, {"palette": "BCYR", "scale": "linear"}, attempts=6, delay_ms=150)
                try:
                    output_layer.setCustomProperty("ctco_initial_palette", "BCYR")
                    output_layer.setCustomProperty("ctco_initial_scale", "linear")
                except Exception:
                    pass
                print("Rampa de cores 'BCYR' aplicada automaticamente (fast)!")
            
            QMessageBox.information(None, "Sucesso", "Mapa de calor rápido criado com sucesso!")
            
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Erro ao executar heatmap rápido: {str(e)}")
            print(f"Erro detalhado: {e}")

    @staticmethod
    def _execute_heatmap_algorithm(layer, parameters, feature_count):
        """
        Executa o algoritmo de heatmap com base no número de features
        
        Args:
            layer: Camada de entrada
            parameters: Parâmetros do heatmap
            feature_count: Número de features
        
        Returns:
            dict: Resultado do processing
        """
        if feature_count > 5000:
            try:
                # Tentar algoritmo mais rápido primeiro (sem auto-load)
                return processing.run("native:heatmapkerneldensityestimation", 
                                      parameters.to_processing_params(layer))
            except Exception:
                # Se falhar, usar o algoritmo original (sem auto-load)
                return processing.run("qgis:heatmapkerneldensityestimation", 
                                      parameters.to_processing_params(layer))
        else:
            return processing.run("qgis:heatmapkerneldensityestimation", 
                                  parameters.to_processing_params(layer))
    
    @staticmethod
    def _show_processing_message(feature_count, parameters):
        """
        Mostra mensagem de processamento
        
        Args:
            feature_count: Número de features
            parameters: Parâmetros do heatmap
        """
        # Corrigir contagem inválida
        if feature_count < 0:
            feature_count = "desconhecido"
            message = f"Criando mapa de calor com {feature_count} pontos...\n"
            message += f"⚠️ Aviso: Não foi possível contar as features automaticamente\n"
        else:
            message = f"Criando mapa de calor com {feature_count} pontos...\n"
        
        message += f"Raio: {parameters.radius}m, Pixel: {parameters.pixel_size}m\n"
        message += f"Modo: {parameters.description}\n"
        message += "Isso pode levar alguns minutos."
        
        QMessageBox.information(None, "Processando", message)

    @staticmethod
    def export_to_pdf(layer):
        """Proxy para manter compatibilidade com UI antiga."""
        return ExportService.export_to_pdf(layer)

