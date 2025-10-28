# Instruções para Testar o Plugin CTCO

## Problemas Corrigidos

1. **Ícones inexistentes**: O plugin estava tentando carregar ícones que não existiam, causando falhas na inicialização
2. **Algoritmo de heatmap**: Melhorado com parâmetros mais completos e verificação de existência
3. **Tratamento de erros**: Adicionado melhor debugging e mensagens de erro mais informativas
4. **Erro de validação de camada**: Corrigido erro que tentava chamar geometryType() em camadas raster

## Como Testar

### 1. Reiniciar o QGIS
- Feche completamente o QGIS
- Abra o QGIS novamente
- O plugin deve aparecer na barra de ferramentas

### 2. Testar o Mapa de Calor (Heatmap)
1. Carregue uma camada de pontos no QGIS
2. Selecione a camada de pontos (clique nela no painel de camadas)
3. Clique no botão CTCO na barra de ferramentas
4. Selecione "Mapa de Calor" no menu suspenso
5. O mapa de calor deve ser criado e carregado automaticamente

### 3. Verificar se está funcionando
- Se aparecer uma mensagem "Mapa de calor criado com sucesso!", o plugin está funcionando
- Se aparecer uma mensagem de erro, anote o erro e reporte

### 4. Testar outras funcionalidades
- **Buffer**: Funciona com qualquer camada vetorial
- **Dissolver**: Funciona com qualquer camada vetorial

## Possíveis Problemas

### Se o plugin não aparecer na barra de ferramentas:
1. Vá em Plugins > Gerenciar e Instalar Plugins
2. Desative o plugin CTCO
3. Ative novamente
4. Reinicie o QGIS

### Se o heatmap não funcionar:
1. Verifique se a camada ativa é de pontos
2. Verifique se há pontos na camada
3. Verifique o console do QGIS para mensagens de erro detalhadas

## Parâmetros do Heatmap
- **Raio**: 100 metros (pode ser ajustado no código)
- **Tamanho do pixel**: 1 metro
- **Kernel**: Quartic
- **Valor de saída**: Raw (valores brutos)

## Debugging
Se houver problemas, verifique o console do QGIS (Visualizar > Painéis > Log de Mensagens) para mensagens de erro detalhadas.
