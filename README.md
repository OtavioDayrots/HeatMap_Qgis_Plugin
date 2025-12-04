# Plugin CTCO - Versão Modularizada

Plugin CTCO para QGIS que acelera a criação e análise de mapas de calor. Oferece um fluxo simples para gerar heatmaps a partir de camadas de pontos, aplicar paletas de cores otimizadas (BCYR), filtrar dados diretamente na camada antes do processamento e importar projetos QGIS (.qgs/.qgz). Interface enxuta com menu aberto direto no ícone da barra de ferramentas.

## 📁 Estrutura do Projeto

```
CTCO_plugin/
├── __init__.py                 # Inicialização do plugin
├── CTCO_plugin.py              # Classe principal (30 linhas)
├── ui_manager.py               # Gerenciamento da interface
├── models/                     # 📊 Modelos de dados
│   ├── __init__.py
│   ├── layer_validator.py      # Validação de camadas
│   └── heatmap_parameters.py   # Parâmetros do heatmap
├── services/                   # 🔧 Serviços de negócio
│   ├── __init__.py
│   ├── heatmap_service.py      # Lógica de heatmap
│   ├── buffer_service.py       # Lógica de buffer
│   ├── dissolve_service.py     # Lógica de dissolver
│   └── color_service.py        # Gerenciamento de cores
├── algorithms/                 # ⚙️ Algoritmos específicos
│   ├── __init__.py
│   ├── heatmap_algorithm.py    # Algoritmo de heatmap
│   ├── buffer_algorithm.py     # Algoritmo de buffer
│   └── dissolve_algorithm.py   # Algoritmo de dissolver
├── icons/                      # 🎨 Ícones do plugin
│   └── ctco_plugin.jpg
└── docs/                       # 📚 Documentação
    ├── README_MODULARIZACAO.md # Esta documentação
    ├── CORES_BCYR.md           # Sistema de cores
    └── INSTRUCOES_TESTE.md     # Instruções de teste
```

## 🏗️ Arquitetura Modular (MVC + Services)

### **📊 Models (models/)**
**Responsabilidade**: Estruturas de dados e validações

#### **layer_validator.py**
- `LayerValidator`: Validação de tipos de camadas
- `get_feature_count()`: Contagem robusta de features
- Validações de geometria e tipo

#### **heatmap_parameters.py**
- `HeatmapParameters`: Classe de dados para parâmetros
- `get_optimized_parameters()`: Parâmetros baseados no número de features
- `to_processing_params()`: Conversão para QGIS processing

### **🔧 Services (services/)**
**Responsabilidade**: Lógica de negócio e processamento

#### **heatmap_service.py**
- `HeatmapService`: Lógica principal de heatmap
- `run_heatmap()`: Execução com parâmetros otimizados
- Integração com validação e cores

#### **color_service.py**
- `ColorService`: Gerenciamento de cores
- `apply_bcyr_colormap()`: Aplicação de cores BCYR
- Múltiplas rampas de cores (BCYR, Viridis, Plasma, etc.)
- Renderização de camadas raster

#### **buffer_service.py** & **dissolve_service.py**
- `BufferService` & `DissolveService`: Lógica de buffer e dissolver
- Validação e execução de algoritmos

### **⚙️ Algorithms (algorithms/)**
**Responsabilidade**: Implementações específicas de algoritmos

#### **heatmap_algorithm.py**
- `HeatmapAlgorithm`: Interface para algoritmos de heatmap
- Delegação para services

#### **buffer_algorithm.py** & **dissolve_algorithm.py**
- `BufferAlgorithm` & `DissolveAlgorithm`: Interfaces para algoritmos
- Delegação para services

### **🖥️ UI Manager (ui_manager.py)**
**Responsabilidade**: Gerenciamento da interface do usuário
- Criação de menus e ações
- Callbacks para algoritmos
- Gerenciamento de ícones

## 🔄 Fluxo de Execução

### **Heatmap Normal:**
1. **UI Manager** → `HeatmapAlgorithm.run_heatmap()`
2. **Algorithm** → `HeatmapService.run_heatmap()`
3. **Service** → `LayerValidator.validate_layer()`
4. **Service** → `HeatmapParameters.get_optimized_parameters()`
5. **Service** → `processing.runAndLoadResults()`
6. **Service** → `ColorService.apply_bcyr_colormap()`

### **Aplicar Cores:**
1. **UI Manager** → `ColorService.apply_bcyr_colormap()`
2. **Service** → Aplicação direta de cores
