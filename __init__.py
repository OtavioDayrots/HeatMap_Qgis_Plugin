"""
Plugin CTCO para QGIS
Sistema modularizado para ferramentas de análise espacial

Módulos:
- CTCO_plugin: Classe principal do plugin
- ui_manager: Gerenciamento da interface do usuário
- algorithms: Implementação dos algoritmos de processamento
- utils: Utilitários e funções de validação
"""

from .CTCO_plugin import CTCO

# Metadados do plugin
PLUGIN_NAME = "CTCO"
PLUGIN_VERSION = "2.0.0"
PLUGIN_DESCRIPTION = "Plugin modularizado para ferramentas de análise espacial"
PLUGIN_AUTHOR = "José Otavio Alves"

# Função de inicialização do plugin
def classFactory(iface):
    """Função obrigatória para plugins do QGIS"""
    return CTCO(iface)