"""
Funções puras de homografia — sem dependência de GUI, testáveis isoladamente.

Mapeiam pontos de pixel (frame do vídeo) para coordenadas do campo em
metros, dado um conjunto de pontos de correspondência clicados
manualmente (ver calibration.py).
"""

from __future__ import annotations

import numpy as np
import cv2


class InsufficientPointsError(ValueError):
    pass


def compute_homography(
    image_points: list[tuple[float, float]],
    pitch_points: list[tuple[float, float]],
) -> np.ndarray:
    """Calcula a matriz de homografia pixel -> metros do campo.

    Precisa de pelo menos 4 pares de pontos não-colineares. Com mais de 4,
    usa RANSAC para absorver algum erro de clicagem manual.
    """
    if len(image_points) != len(pitch_points):
        raise ValueError("image_points e pitch_points têm de ter o mesmo tamanho")
    if len(image_points) < 4:
        raise InsufficientPointsError(
            f"Precisa de pelo menos 4 pontos, recebeu {len(image_points)}"
        )

    src = np.array(image_points, dtype=np.float64)
    dst = np.array(pitch_points, dtype=np.float64)

    method = cv2.RANSAC if len(image_points) > 4 else 0
    H, _mask = cv2.findHomography(src, dst, method=method)
    if H is None:
        raise ValueError("Não foi possível calcular a homografia — pontos degenerados?")
    return H


def apply_homography(H: np.ndarray, x_px: float, y_px: float) -> tuple[float, float]:
    """Transforma um ponto de pixel (x, y) em coordenadas do campo (metros)."""
    pt = np.array([[[x_px, y_px]]], dtype=np.float64)
    out = cv2.perspectiveTransform(pt, H)
    return float(out[0, 0, 0]), float(out[0, 0, 1])


def is_within_pitch(
    x_m: float, y_m: float, length_m: float, width_m: float, margin_m: float = 3.0
) -> bool:
    """Verificação de sanidade: o ponto cai dentro do campo (+ margem)?

    Usado só como sinal de aviso (ex.: erro de calibração, deteção
    espúria) — nunca para descartar dados silenciosamente.
    """
    return (-margin_m <= x_m <= length_m + margin_m) and (
        -margin_m <= y_m <= width_m + margin_m
    )
