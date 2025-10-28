# Sistema de Cores BCYR - Plugin CTCO

## 🎨 **Rampa de Cores BCYR Implementada**

O plugin agora aplica automaticamente uma rampa de cores **BCYR** (Blue-Cyan-Yellow-Red) aos heatmaps gerados.

### 🌈 **Esquema de Cores:**

| Valor | Cor | Descrição |
|-------|-----|-----------|
| **0%** | 🔵 **Azul** | Baixa densidade |
| **25%** | 🔷 **Ciano** | Densidade baixa-média |
| **50%** | 🟢 **Verde** | Densidade média |
| **75%** | 🟡 **Amarelo** | Densidade alta |
| **100%** | 🔴 **Vermelho** | Máxima densidade |

## 🚀 **Funcionalidades Implementadas:**

### **1. Aplicação Automática**
- **Heatmap Normal**: Aplica cores BCYR automaticamente
- **Heatmap Rápido**: Aplica cores BCYR automaticamente
- **Sem intervenção manual**: Cores aplicadas automaticamente após geração

### **2. Aplicação Manual**
- **Menu "Aplicar Cores BCYR"**: Para aplicar cores a heatmaps existentes
- **Validação**: Só funciona com camadas raster
- **Feedback**: Mensagem de sucesso/erro

### **3. Rampas Adicionais Disponíveis**
- **BCYR**: Blue-Cyan-Yellow-Red (padrão)
- **Heatmap**: Azul para Vermelho (clássico)
- **Viridis**: Tons de roxo/azul/verde/amarelo
- **Plasma**: Tons de roxo/rosa/amarelo
- **Inferno**: Tons de preto/vermelho/amarelo

## 🔧 **Como Usar:**

### **Método 1: Automático (Recomendado)**
1. Selecione camada de pontos
2. Clique em "Mapa de Calor" ou "Mapa de Calor Rápido"
3. As cores BCYR são aplicadas automaticamente! ✨

### **Método 2: Manual**
1. Selecione um heatmap existente (camada raster)
2. Clique em "Aplicar Cores BCYR"
3. Cores aplicadas instantaneamente!

## 📊 **Vantagens da Rampa BCYR:**

### **1. Visualização Intuitiva**
- **Azul**: Áreas de baixa atividade
- **Verde**: Áreas de atividade moderada  
- **Amarelo**: Áreas de alta atividade
- **Vermelho**: Áreas de máxima atividade

### **2. Acessibilidade**
- **Contraste adequado** para diferentes tipos de daltonismo
- **Transição suave** entre cores
- **Fácil interpretação** pelos usuários

### **3. Padrão Científico**
- **Comumente usado** em análises espaciais
- **Reconhecido internacionalmente**
- **Compatível** com softwares GIS

## 🎯 **Exemplos de Uso:**

### **Análise de Atividade:**
- 🔵 **Azul**: Baixa atividade
- 🟢 **Verde**: Atividade moderada
- 🟡 **Amarelo**: Alta atividade
- 🔴 **Vermelho**: Zonas críticas

## ⚙️ **Configuração Técnica:**

### **Código RGB das Cores:**
```python
BCYR_COLORS = [
    (1, QColor(0, 0, 255)),      # Azul
    (5, QColor(0, 255, 255)),   # Ciano
    (10, QColor(0, 255, 0)),      # Verde
    (20, QColor(255, 255, 0)),   # Amarelo
    (30, QColor(255, 0, 0))       # Vermelho
]
```

### **Interpolação:**
- **Tipo**: Interpolada (transições suaves)
- **Pontos**: 5 pontos de cor
- **Método**: Linear entre pontos

## 🔄 **Compatibilidade:**

- ✅ **QGIS 3.x**: Totalmente compatível
- ✅ **Windows/Linux/Mac**: Funciona em todos os sistemas
- ✅ **Camadas Raster**: Qualquer formato suportado pelo QGIS
- ✅ **Performance**: Aplicação instantânea

## 🎉 **Resultado:**

Agora seus heatmaps terão cores **profissionais e intuitivas** automaticamente! 

**Antes**: Heatmap em tons de cinza (monótono)
**Depois**: Heatmap BCYR colorido e informativo!
