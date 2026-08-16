"""
Dimensões do campo e pontos de referência usados na calibração.

O sistema de coordenadas do campo é em metros, origem no canto inferior
esquerdo (perspetiva de quem vê o campo de cima), eixo X ao longo da
linha lateral (comprimento) e eixo Y ao longo da linha de baliza (largura).

AVISO: os valores por omissão são os de um campo regulamentar (105x68m).
Campos de sub-17 / relvados de clube variam bastante. CONFIRMA as
dimensões reais do teu campo antes de calibrar um jogo — os pontos de
referência clicados na Fase 1 só fazem sentido se estas dimensões
corresponderem ao terreno real.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PitchDimensions:
    length_m: float = 105.0
    width_m: float = 68.0
    penalty_area_length_m: float = 16.5
    penalty_area_width_m: float = 40.32
    goal_area_length_m: float = 5.5
    goal_area_width_m: float = 18.32
    center_circle_radius_m: float = 9.15


# Pontos de referência "nomeados" — usados como opções no clicker de
# calibração. Cada um mapeia para uma coordenada (x, y) em metros no
# sistema de eixos descrito acima. São os pontos mais fáceis de
# identificar visualmente num frame de vídeo (interseções de linhas).
def named_reference_points(dims: PitchDimensions = PitchDimensions()) -> dict[str, tuple[float, float]]:
    L, W = dims.length_m, dims.width_m
    pa_l, pa_w = dims.penalty_area_length_m, dims.penalty_area_width_m
    ga_l, ga_w = dims.goal_area_length_m, dims.goal_area_width_m

    half_pa_w = pa_w / 2
    half_ga_w = ga_w / 2
    half_w = W / 2

    return {
        "canto_inferior_esquerdo": (0.0, 0.0),
        "canto_superior_esquerdo": (0.0, W),
        "canto_inferior_direito": (L, 0.0),
        "canto_superior_direito": (L, W),
        "meio_campo_lateral_inferior": (L / 2, 0.0),
        "meio_campo_lateral_superior": (L / 2, W),
        "centro_do_campo": (L / 2, half_w),
        "grande_area_esquerda_inferior": (0.0, half_w - half_pa_w),
        "grande_area_esquerda_superior": (0.0, half_w + half_pa_w),
        "grande_area_esquerda_frente_inferior": (pa_l, half_w - half_pa_w),
        "grande_area_esquerda_frente_superior": (pa_l, half_w + half_pa_w),
        "pequena_area_esquerda_inferior": (0.0, half_w - half_ga_w),
        "pequena_area_esquerda_superior": (0.0, half_w + half_ga_w),
        "pequena_area_esquerda_frente_inferior": (ga_l, half_w - half_ga_w),
        "pequena_area_esquerda_frente_superior": (ga_l, half_w + half_ga_w),
        "grande_area_direita_inferior": (L, half_w - half_pa_w),
        "grande_area_direita_superior": (L, half_w + half_pa_w),
        "grande_area_direita_frente_inferior": (L - pa_l, half_w - half_pa_w),
        "grande_area_direita_frente_superior": (L - pa_l, half_w + half_pa_w),
        "pequena_area_direita_inferior": (L, half_w - half_ga_w),
        "pequena_area_direita_superior": (L, half_w + half_ga_w),
        "pequena_area_direita_frente_inferior": (L - ga_l, half_w - half_ga_w),
        "pequena_area_direita_frente_superior": (L - ga_l, half_w + half_ga_w),
    }
