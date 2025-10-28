"""
Módulo de gerenciamento de interface para o plugin CTCO
Contém a lógica de criação de menus e ações
"""

import os
from qgis.PyQt.QtWidgets import QAction, QMenu, QMessageBox, QInputDialog, QToolButton
from qgis.PyQt.QtGui import QIcon
from .dialogs.export_map_options_dialog import ExportMapOptionsDialog
from .services.export_service import ExportService
from .algorithms import HeatmapAlgorithm, SetColorAlgorithm
from .services import ColorService, ImportService


class UIManager:
    """Classe para gerenciar a interface do usuário"""
    
    def __init__(self, iface, plugin_dir):
        """
        Inicializa o gerenciador de UI
        
        Args:
            iface: Interface do QGIS
            plugin_dir: Diretório do plugin
        """
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.toolbar_action = None
        self.toolbar_button = None
        self.toolbar_widget_action = None
        self.menu = None
        self.actions = {}
    
    def create_icon(self, icon_name, fallback_icon=None):
        """
        Cria ícone com fallback se não existir
        
        Args:
            icon_name: Nome do arquivo de ícone
            fallback_icon: Ícone de fallback (padrão: QIcon vazio)
        
        Returns:
            QIcon: Ícone carregado ou fallback
        """
        icon_path = os.path.join(self.plugin_dir, "icons", icon_name)
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return fallback_icon or QIcon()
    
    def create_action(self, name, text, icon_name, callback, parent=None):
        """
        Cria uma ação com ícone e callback
        
        Args:
            name: Nome interno da ação
            text: Texto exibido
            icon_name: Nome do arquivo de ícone
            callback: Função a ser chamada
            parent: Widget pai
        
        Returns:
            QAction: Ação criada
        """
        icon = self.create_icon(icon_name)
        action = QAction(icon, text, parent or self.iface.mainWindow())
        action.triggered.connect(callback)
        self.actions[name] = action
        return action
    
    def setup_ui(self):
        """Configura toda a interface do usuário"""
        # Ícone principal do plugin
        main_icon = self.create_icon("ctco_plugin.jpg")

        # Criar menu suspenso
        self.menu = QMenu("CTCO", self.iface.mainWindow())
        
        # Heatmap
        heatmap_action = self.create_action(
            "heatmap",
            "Mapa de Calor (Configurar)",
            "heatmap.png",
            self._run_heatmap
        )
        self.menu.addAction(heatmap_action)
        
        # Heatmap Rápido
        heatmap_fast_action = self.create_action(
            "heatmap_fast",
            "Mapa de Calor Rápido",
            "heatmap_fast.webp",
            self._run_heatmap_fast
        )
        self.menu.addAction(heatmap_fast_action)

        # Separador
        self.menu.addSeparator()

        # Importar projeto
        import_action = self.create_action(
            "import_map",
            "Importar projeto...",
            "import.png",
            self._import_map
        )
        self.menu.addAction(import_action)

        # Exportar mapa (PNG)
        export_action = self.create_action(
            "export_map",
            "Exportar mapa...",
            "export.png",
            self._export_map
        )
        self.menu.addAction(export_action)

        # Estatísticas do Heatmap
        stats_action = self.create_action(
            "heatmap_stats",
            "Estatísticas do Heatmap",
            "estatisticas.png",
            self._show_heatmap_stats
        )
        self.menu.addAction(stats_action)
        
        # Aplicar Cores (menu de seleção)
        color_action = self.create_action(
            "apply_colors",
            "Aplicar Cores...",
            "color.png",
            self._apply_colors
        )
        self.menu.addAction(color_action)
        
        
        # Resetar Cores
        reset_colors_action = self.create_action(
            "reset_colors",
            "Resetar Cores",
            "reset.png",
            self._reset_colors
        )
        self.menu.addAction(reset_colors_action)
        
        # Criar botão com menu abrindo no clique do ícone
        self.toolbar_button = QToolButton(self.iface.mainWindow())
        self.toolbar_button.setIcon(main_icon)
        self.toolbar_button.setToolTip("CTCO")
        self.toolbar_button.setMenu(self.menu)
        self.toolbar_button.setPopupMode(QToolButton.InstantPopup)
        # Adicionar o botão como widget na toolbar e guardar a ação retornada
        self.toolbar_widget_action = self.iface.addToolBarWidget(self.toolbar_button)
    
    def cleanup_ui(self):
        """Remove a interface do usuário"""
        if self.toolbar_widget_action:
            try:
                self.iface.removeToolBarIcon(self.toolbar_widget_action)
            except Exception:
                pass
            self.toolbar_widget_action = None
        if self.toolbar_action:
            try:
                self.iface.removeToolBarIcon(self.toolbar_action)
            except Exception:
                pass
    
    def _run_heatmap(self):
        """Callback para executar heatmap"""
        layer = self.iface.activeLayer()
        if not layer:
            QMessageBox.warning(None, "Aviso", "Nenhuma camada ativa encontrada!")
            return

        # Abrir diálogo de configuração
        try:
            from .dialogs.heatmap_config_dialog import HeatmapConfigDialog
        except ImportError:
            from dialogs.heatmap_config_dialog import HeatmapConfigDialog

        dlg = HeatmapConfigDialog(layer=self.iface.activeLayer(), parent=self.iface.mainWindow())
        if dlg.exec_() == 1:  # Accepted
            config = dlg.get_config()
            HeatmapAlgorithm.run_heatmap(layer, config)
    
    def _run_heatmap_fast(self):
        """Callback para executar heatmap rápido"""
        layer = self.iface.activeLayer()
        HeatmapAlgorithm.run_heatmap_fast(layer)
    
    def _show_heatmap_stats(self):
        layer = self.iface.activeLayer()
        if not layer or layer.type() != 1:  # Raster
            QMessageBox.warning(None, "Aviso", "Selecione um heatmap (raster) para ver estatísticas.")
            return
        try:
            try:
                from .dialogs.heatmap_stats_dialog import HeatmapStatsDialog
            except ImportError:
                from dialogs.heatmap_stats_dialog import HeatmapStatsDialog
            dlg = HeatmapStatsDialog(layer, parent=self.iface.mainWindow())
            dlg.exec_()
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Falha ao abrir estatísticas: {str(e)}")

    def _apply_colors(self):
        """Callback para aplicar rampa de cores escolhida"""
        layer = self.iface.activeLayer()
        if not layer:
            QMessageBox.warning(None, "Aviso", "Nenhuma camada ativa encontrada!")
            return
        
        if layer.type() != 1:  # QgsMapLayer.RasterLayer
            QMessageBox.warning(None, "Aviso", "Esta ferramenta só funciona com camadas raster!")
            return
        
        try:
            # Abrir dialogo para obter opções de paleta
            from .dialogs.set_color_dialog import SetColorDialog
        except Exception as e:
            from dialogs.set_color_dialog import SetColorDialog

        dlg = SetColorDialog(layer=self.iface.activeLayer(), parent=self.iface.mainWindow())
        if dlg.exec_() == 1:  # Accepted
            config = dlg.get_config()
            SetColorAlgorithm.run_setColor(layer, config)
    
    def _reset_colors(self):
        """Callback para resetar cores para a configuração original do heatmap"""
        layer = self.iface.activeLayer()
        if not layer:
            QMessageBox.warning(None, "Aviso", "Nenhuma camada ativa encontrada!")
            return
        
        if layer.type() != 1:  # QgsMapLayer.RasterLayer
            QMessageBox.warning(None, "Aviso", "Esta ferramenta só funciona com camadas raster!")
            return
        
        try:
            # 1) Tentar restaurar a paleta inicial registrada na criação do heatmap
            initial_palette = layer.customProperty("ctco_initial_palette", None)
            initial_scale = layer.customProperty("ctco_initial_scale", "linear")

            if initial_palette:
                ColorService.apply_colormap(
                    layer,
                    name=str(initial_palette),
                    scale_mode=str(initial_scale) if initial_scale else "linear",
                )
                QMessageBox.information(None, "Sucesso", "Cores restauradas para a paleta original do heatmap!")
                return

            # 2) Caso não haja metadados, voltar para a paleta padrão BCYR
            ColorService.apply_colormap(layer, name="BCYR", scale_mode="linear")
            QMessageBox.information(None, "Sucesso", "Cores resetadas para a paleta padrão BCYR!")
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Erro ao resetar cores: {str(e)}")

    def _import_map(self):
        try:
            ImportService.import_map(self.iface.mainWindow())
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Falha ao importar mapa: {str(e)}")
    
    def _export_map(self):
        try:
            dlg = ExportMapOptionsDialog(parent=self.iface.mainWindow())
            if dlg.exec_() == 1:
                options = dlg.get_options()
                ExportService.export_map_with_options(self.iface, options)
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Falha ao exportar mapa: {str(e)}")
