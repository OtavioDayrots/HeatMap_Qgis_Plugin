"""
Plugin CTCO para QGIS
Plugin modularizado para ferramentas de análise espacial
"""

import os
try:
    from .ui_manager import UIManager
except Exception:
    import importlib
    pkg_name = __package__ or os.path.basename(os.path.dirname(__file__))
    # Importar SEMPRE como pacote para permitir imports relativos dentro de ui_manager
    UIManager = importlib.import_module(f"{pkg_name}.ui_manager").UIManager


class CTCO:
    """Classe principal do plugin CTCO"""
    
    def __init__(self, iface):
        """
        Inicializa o plugin
        
        Args:
            iface: Interface do QGIS
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.ui_manager = None
    
    def initGui(self):
        """Inicializa a interface gráfica do plugin"""
        self.ui_manager = UIManager(self.iface, self.plugin_dir)
        self.ui_manager.setup_ui()
    
    def unload(self):
        """Remove o plugin da interface"""
        if self.ui_manager:
            self.ui_manager.cleanup_ui()