"""
Serviço de gerenciamento de cores para o plugin CTCO
Contém lógica de negócio para aplicação de cores.

Ideia central:
- Templates de paleta trabalham em posições normalizadas (0..1) para reuso.
- Ao aplicar na camada, reescalamos essas posições para o range efetivo do raster
  (min/max dinâmico ou informado), garantindo contraste e legibilidade.
- Suporta modo "log" (rearranja as posições) para destacar altas intensidades.
"""

from qgis.core import QgsColorRampShader, QgsRasterShader, QgsSingleBandPseudoColorRenderer
from .palette_definitions import PALETTES, apply_scale_positions


class ColorService:
    """Serviço para gerenciar cores e rampas de cores.

    Por que esta classe existe:
    - Centraliza a criação de rampas (BCYR, Heatmap, Viridis etc.).
    - Aplica a rampa respeitando estatísticas do raster (min/max) para evitar faixas “mortas”.
    - Persiste propriedades na camada (paleta/escala/min/max) para permitir resetar.
    """
    
    @staticmethod
    def apply_bcyr_colormap(layer):
        """Aplica rampa BCYR com distribuição linear (uso mais comum)."""
        try:
            ColorService.apply_colormap(layer, name="BCYR", scale_mode="linear")
            layer.triggerRepaint()
            print("Rampa de cores BCYR aplicada com sucesso!")
        except Exception as e:
            print(f"Erro ao aplicar rampa de cores: {e}")
            try:
                ColorService._apply_colormap_alternative(layer, "bcyr")
            except Exception as e2:
                print(f"Erro no método alternativo: {e2}")
    
    @staticmethod
    def _apply_colormap_alternative(layer, colormap_type):
        """
        Método alternativo para aplicar rampa de cores
        
        Args:
            layer: Camada raster
            colormap_type: Tipo de rampa ("bcyr", "classic", etc.)
        """
        from qgis.core import QgsRasterRenderer, QgsColorRampShader, QgsRasterShader
        
        # Criar rampa de cores baseada no tipo
        if colormap_type == "bcyr":
            color_ramp = ColorService.create_bcyr_ramp()
        else:
            color_ramp = ColorService.create_heatmap_ramp()
        
        # Debug: verificar tipo do color_ramp
        print(f"[CTCO] Debug alternative: color_ramp type = {type(color_ramp)}")
        if not hasattr(color_ramp, 'colorRampItemList'):
            print(f"[CTCO] Debug alternative: color_ramp NÃO tem colorRampItemList")
            raise ValueError(f"color_ramp deve ser QgsColorRampShader, recebido: {type(color_ramp)}")
        
        # Criar shader
        shader = QgsRasterShader()
        shader.setRasterShaderFunction(color_ramp)
        
        # Aplicar diretamente
        layer.setRenderer(QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader))
        layer.triggerRepaint()
    
    @staticmethod
    def create_bcyr_ramp():
        """
        Mantém compatibilidade: cria uma rampa BCYR padrão.
        Nota: valores são relativos (0..1) e serão mapeados ao range efetivo.
        """
        template = PALETTES["bcyr"]()
        print(f"[CTCO] Debug create_bcyr_ramp: template = {template}")
        # Por compatibilidade com chamadas antigas que esperam um QgsColorRampShader,
        # retornamos uma rampa normalizada 0..1; ela será reescalada em apply_color_ramp_to_layer
        result = ColorService._create_color_ramp([(pos, color) for pos, color in template])
        print(f"[CTCO] Debug create_bcyr_ramp: result type = {type(result)}")
        return result
    
    @staticmethod
    def create_heatmap_ramp():
        """
        Cria rampa de cores específica para heatmap (azul para vermelho)
        
        Returns:
            QgsColorRampShader: Rampa de cores para heatmap
        """
        template = PALETTES["heatmap"]()
        print(f"[CTCO] Debug create_heatmap_ramp: template = {template}")
        result = ColorService._create_color_ramp(template)
        print(f"[CTCO] Debug create_heatmap_ramp: result type = {type(result)}")
        return result
    
    @staticmethod
    def create_viridis_ramp():
        """Cria rampa de cores Viridis"""
        template = PALETTES["viridis"]()
        return ColorService._create_color_ramp(template)
    
    @staticmethod
    def create_plasma_ramp():
        """Cria rampa de cores Plasma"""
        template = PALETTES["plasma"]()
        return ColorService._create_color_ramp(template)
    
    @staticmethod
    def create_inferno_ramp():
        """Cria rampa de cores Inferno"""
        template = PALETTES["inferno"]()
        return ColorService._create_color_ramp(template)
    
    @staticmethod
    def _create_color_ramp(colors):
        """Cria `QgsColorRampShader` a partir de [(posicao, QColor)].

        Observação: `posicao` pode vir normalizada (0..1) ou já na escala de dados.
        Em `apply_color_ramp_to_layer` detectamos e reescalamos quando necessário.
        """
        # Criar shader de rampa de cores
        color_ramp = QgsColorRampShader()
        color_ramp.setColorRampType(QgsColorRampShader.Interpolated)
        
        # Adicionar pontos de cor
        color_ramp_items = []
        for value, color in colors:
            # A legenda é apenas ilustrativa; evita sufixo % quando value está em escala de dados
            try:
                label = f"{float(value):.2f}"
            except Exception:
                label = str(value)
            item = QgsColorRampShader.ColorRampItem(value, color, label)
            color_ramp_items.append(item)
        
        color_ramp.setColorRampItemList(color_ramp_items)
        
        print(f"[CTCO] Debug _create_color_ramp: criado QgsColorRampShader com {len(color_ramp_items)} itens")
        return color_ramp
    
    @staticmethod
    def apply_color_ramp_to_layer(layer, color_ramp, min_val=None, max_val=None, opacity: float = 0.6):
        """Aplica a rampa à camada com normalização para o range efetivo.

        Passos:
        1) Lê estatísticas (min/max/mean/std) com flags completos.
        2) Define faixa efetiva: dinâmica (mean±k*std) ou min/max informados.
        3) Reescala itens 0..1 para [min,max] efetivo e aplica renderer.
        Por quê: melhora contraste e evita "mapa todo azul/vermelho".
        """
        try:
            # Debug: verificar tipo do color_ramp
            print(f"[CTCO] Debug: color_ramp type = {type(color_ramp)}")
            if hasattr(color_ramp, 'colorRampItemList'):
                print(f"[CTCO] Debug: color_ramp tem colorRampItemList")
            else:
                print(f"[CTCO] Debug: color_ramp NÃO tem colorRampItemList, tem: {dir(color_ramp)}")
                raise ValueError(f"color_ramp deve ser QgsColorRampShader, recebido: {type(color_ramp)}")
            # Obter estatísticas da camada para normalizar valores
            provider = layer.dataProvider()
            try:
                # Usar flags completos e considerar a extensão atual
                from qgis.core import QgsRasterBandStats
                stats = provider.bandStatistics(1, QgsRasterBandStats.All, layer.extent(), 0)
            except Exception:
                stats = provider.bandStatistics(1)
            stats_min = stats.minimumValue
            stats_max = stats.maximumValue
            stats_mean = getattr(stats, 'mean', None)
            stats_std = getattr(stats, 'stdDev', None)

            # Capturar NoData e tipo de banda para diagnóstico
            try:
                no_data_val = provider.sourceNoDataValue(1)
            except Exception:
                no_data_val = None
            try:
                band_type = provider.dataType(1)
            except Exception:
                band_type = None

            print(f"[CTCO] Raster info: band_type={band_type}, no_data={no_data_val}")
            print(f"[CTCO] Stats: min={stats_min}, max={stats_max}, mean={stats_mean}, std={stats_std}")

            # Usar SEMPRE min/max reais do raster, a menos que min/max tenham sido informados
            effective_min = stats_min if min_val is None else float(min_val)
            effective_max = stats_max if max_val is None else float(max_val)

            # Salvaguarda: se a faixa ainda for degenerada (ex.: tudo zero)
            if effective_max == effective_min:
                print(f"[CTCO] Aviso: faixa degenerada (min==max=={effective_min}). Tentando usar stats min/max brutos.")
                effective_min, effective_max = stats_min, stats_max

            # Reescalar itens da rampa quando valores estão normalizados 0..1
            scaled_items = []
            for item in color_ramp.colorRampItemList():
                pos = float(item.value)
                if 0.0 <= pos <= 1.0 and effective_max > effective_min:
                    value = effective_min + pos * (effective_max - effective_min)
                else:
                    value = pos
                # Atualizar o rótulo para refletir a posição normalizada desejada (ex.: 0.50 para o meio)
                label = f"{pos:.2f}" if 0.0 <= pos <= 1.0 else str(item.label)
                scaled_items.append(QgsColorRampShader.ColorRampItem(value, item.color, label))

            # Logar primeiros itens para depuração
            if scaled_items:
                preview = ", ".join([f"{i.value:.4f}" if isinstance(i.value, float) else str(i.value) for i in scaled_items[:5]])
                print(f"[CTCO] Itens de rampa (exemplo): {preview} ...")

            scaled_ramp = QgsColorRampShader()
            scaled_ramp.setColorRampType(QgsColorRampShader.Interpolated)
            scaled_ramp.setColorRampItemList(scaled_items)

            # Criar shader e renderer
            shader = QgsRasterShader()
            shader.setRasterShaderFunction(scaled_ramp)
            renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)
            renderer.setClassificationMin(effective_min)
            renderer.setClassificationMax(effective_max)
            try:
                renderer.setOpacity(float(opacity))
            except:
                pass

            # Aplicar renderizador à camada
            layer.setRenderer(renderer)
            layer.triggerRepaint()
            print(f"[CTCO] Rampa de cores aplicada com normalização (min={effective_min}, max={effective_max})")
            
        except Exception as e:
            print(f"Erro ao aplicar rampa de cores: {e}")
            # Fallback: aplicar sem normalização
            try:
                print(f"[CTCO] Debug fallback: color_ramp type = {type(color_ramp)}")
                if not hasattr(color_ramp, 'colorRampItemList'):
                    print(f"[CTCO] Debug fallback: color_ramp NÃO tem colorRampItemList")
                    raise ValueError(f"color_ramp deve ser QgsColorRampShader, recebido: {type(color_ramp)}")
                
                shader = QgsRasterShader()
                shader.setRasterShaderFunction(color_ramp)
                renderer = QgsSingleBandPseudoColorRenderer(provider, 1, shader)
                layer.setRenderer(renderer)
                layer.triggerRepaint()
            except Exception as e2:
                print(f"Erro no fallback: {e2}")

    @staticmethod
    def apply_colormap(layer, name, min_val=None, max_val=None, scale_mode: str = "linear", opacity: float = 0.6):
        """
        Aplica rampa de cores pelo nome, com opção de escala.
        
        Args:
            layer: Camada raster
            name: Nome da rampa ("BCYR", "Heatmap", "Viridis", "Plasma", "Inferno")
            min_val: Valor mínimo para classificação (opcional)
            max_val: Valor máximo para classificação (opcional)
            scale_mode: "linear" ou "log" (melhora contraste em altas intensidades)
        """
        try:
            # Normalizar nome para aceitar diferentes capitalizações e aliases
            key = (name or "BCYR").strip().lower()
            # aliases simples
            if key in ("iferno", "inferno_r"):
                key = "inferno"

            template_fn = PALETTES.get(key, PALETTES.get("bcyr"))
            template = template_fn()
            try:
                preview_in = ", ".join([f"{float(p):.2f}" for p, _ in template[:8]])
                print(f"[CTCO] Template '{key}' (in): {preview_in}")
            except Exception:
                pass
            # Correção solicitada: garantir amarelo exatamente no meio para BCYR
            if key == "bcyr":
                # Recriar stops com amarelo em 0.50, verde em 0.45 e laranja em 0.80
                # Cores herdadas do template original, ajustando apenas as posições
                try:
                    # Buscar cores mais próximas no template para cada faixa
                    def nearest_color(pos_fallback: float):
                        # Encontra a cor no template pela posição mais próxima
                        best = min(template, key=lambda pc: abs(float(pc[0]) - pos_fallback))
                        return best[1]
                    template = [
                        (0.00, nearest_color(0.00)),
                        (0.15, nearest_color(0.15)),
                        (0.30, nearest_color(0.30)),
                        (0.45, nearest_color(0.45)),
                        (0.50, nearest_color(0.60)),  # amarelo fica em 0.50
                        (0.80, nearest_color(0.80)),
                        (1.00, nearest_color(1.00)),
                    ]
                except Exception:
                    pass

            # Converter template para rampa normalizada (0..1)
            base_ramp = ColorService._create_color_ramp(template)
            print(f"[CTCO] Debug apply_colormap: base_ramp type = {type(base_ramp)}")

            # Aplicar ao layer com reescala e modo de escala
            if scale_mode == "log":
                adjusted = apply_scale_positions(template, "log")
                try:
                    preview_adj = ", ".join([f"{float(p):.2f}" for p, _ in adjusted[:8]])
                    print(f"[CTCO] Template '{key}' (log-adjusted): {preview_adj}")
                except Exception:
                    pass
                base_ramp = ColorService._create_color_ramp(adjusted)
                print(f"[CTCO] Debug apply_colormap log: base_ramp type = {type(base_ramp)}")

            # min/max deixam de ser configuráveis pelo usuário; usar normalização dinâmica
            # Logar stops da rampa antes de aplicar
            try:
                items_dbg = base_ramp.colorRampItemList()
                dbg_vals = ", ".join([f"{float(i.value):.4f}" for i in items_dbg[:10]])
                print(f"[CTCO] ColorRamp stops (pre-apply): {dbg_vals}")
            except Exception:
                pass

            ColorService.apply_color_ramp_to_layer(layer, base_ramp, min_val=None, max_val=None, opacity = opacity)

            # Registrar propriedades na camada para permitir "Resetar Cores" à configuração original/atual
            try:
                layer.setCustomProperty("ctco_palette", name)
                layer.setCustomProperty("ctco_scale", scale_mode)
                layer.setCustomProperty("ctco_opacity", opacity)
                # Remover propriedades antigas
                layer.removeCustomProperty("ctco_min")
                layer.removeCustomProperty("ctco_max")
            except Exception:
                pass

            layer.triggerRepaint()
            print(f"Rampa '{name}' aplicada com sucesso")
        except Exception as e:
            print(f"Erro ao aplicar rampa '{name}': {e}")
    
    @staticmethod
    def get_available_colormaps():
        """
        Retorna lista de rampas de cores disponíveis
        
        Returns:
            dict: Dicionário com nomes e funções das rampas
        """
        return {
            "BCYR": ColorService.create_bcyr_ramp,
            "Heatmap": ColorService.create_heatmap_ramp,
            "Viridis": lambda: ColorService._create_color_ramp(PALETTES["viridis"]()),
            "Plasma": lambda: ColorService._create_color_ramp(PALETTES["plasma"]()),
            "Inferno": lambda: ColorService._create_color_ramp(PALETTES["inferno"]()),
        }

    @staticmethod
    def _bcyr_template():
        # Manter compatibilidade com chamadas antigas
        return PALETTES["bcyr"]()
