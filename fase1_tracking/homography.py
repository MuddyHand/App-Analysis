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


class PolynomialWarp:
    """Ajuste polinomial de 2º grau pixel -> metros do campo.

    Alternativa à homografia linear para fontes com distorção de lente
    (ex.: gravação de ecrã do modo Panorâmico da Veo, que usa uma lente
    wide-angle/fisheye — uma homografia de 4 pontos não é fiável longe
    desses 4 pontos porque assume projeção pinhole sem distorção).

    Ajusta x_m = f(x_px, y_px) e y_m = g(x_px, y_px) por mínimos quadrados,
    com f,g polinómios de 2º grau (1, x, y, x², xy, y²). Precisa de pelo
    menos 6 pontos, e o resultado só é fiável DENTRO da área coberta pelos
    pontos clicados — extrapolar para fora da malha de pontos não tem
    garantias (ao contrário de uma homografia verdadeira, isto não modela
    a física da lente, é um ajuste empírico)."""

    MIN_POINTS = 6

    def __init__(self, coeffs_x: np.ndarray, coeffs_y: np.ndarray):
        self.coeffs_x = coeffs_x
        self.coeffs_y = coeffs_y

    @staticmethod
    def _design_matrix(xy: np.ndarray) -> np.ndarray:
        x, y = xy[:, 0], xy[:, 1]
        return np.column_stack([np.ones_like(x), x, y, x * x, x * y, y * y])

    @classmethod
    def fit(cls, image_points: list[tuple[float, float]], pitch_points: list[tuple[float, float]]) -> "PolynomialWarp":
        if len(image_points) != len(pitch_points):
            raise ValueError("image_points e pitch_points têm de ter o mesmo tamanho")
        if len(image_points) < cls.MIN_POINTS:
            raise InsufficientPointsError(
                f"Ajuste polinomial precisa de pelo menos {cls.MIN_POINTS} pontos, recebeu {len(image_points)}"
            )
        src = np.array(image_points, dtype=np.float64)
        dst = np.array(pitch_points, dtype=np.float64)
        A = cls._design_matrix(src)
        coeffs_x, *_ = np.linalg.lstsq(A, dst[:, 0], rcond=None)
        coeffs_y, *_ = np.linalg.lstsq(A, dst[:, 1], rcond=None)
        return cls(coeffs_x, coeffs_y)

    def apply(self, x_px: float, y_px: float) -> tuple[float, float]:
        A = self._design_matrix(np.array([[x_px, y_px]], dtype=np.float64))
        x_m = float((A @ self.coeffs_x)[0])
        y_m = float((A @ self.coeffs_y)[0])
        return x_m, y_m

    def to_json(self) -> dict:
        return {"coeffs_x": self.coeffs_x.tolist(), "coeffs_y": self.coeffs_y.tolist()}

    @classmethod
    def from_json(cls, data: dict) -> "PolynomialWarp":
        return cls(np.array(data["coeffs_x"]), np.array(data["coeffs_y"]))


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
