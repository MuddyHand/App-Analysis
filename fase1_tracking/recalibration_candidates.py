"""
⚠️ EXPERIMENTAL — NÃO CONFIÁVEL. Ver "histórico honesto" abaixo antes de
usar. Recomendação atual (ver fase1_tracking/README.md): faz antes uma
inspeção visual manual espaçada (ex.: um frame a cada 5min) para decidir
onde recalibrar — é mais lento, mas dá-te um resultado em que podes
confiar, o que este script ainda não consegue.

Objetivo original: sinalizar candidatos a "o enquadramento da câmara
pode ter mudado aqui", para reduzir o trabalho de vasculhar o jogo todo
à procura de onde recalibrar manualmente (ver calibration.py).

HISTÓRICO HONESTO — três tentativas, testadas com um jogo real de
166min, nenhuma deu um sinal fiável:

1. Fluxo ótico médio sobre o frame inteiro: sinalizou 58% do vídeo como
   candidato — o movimento normal dos jogadores já produz fluxo médio
   tão alto quanto uma mudança de câmara real.
2. Correlação de uma faixa superior do frame (fundo: bancada, árvores,
   painéis): devia ficar perto de 1.0 em períodos estáveis, mas caiu
   para 0.1-0.4 mesmo entre frames com 1 minuto de diferença e câmara
   aparentemente parada — há um painel publicitário LED com conteúdo a
   mudar dentro dessa faixa, o que contamina a métrica.
3. Feature matching (ORB) + homografia entre frames: os deslocamentos
   estimados não fazem sentido físico (centenas de pixels entre frames
   visualmente semelhantes) — o relvado, a bancada e a folhagem têm
   textura repetitiva que confunde o matching.

Isto fica no repositório como código funcional (a versão 2, por
correlação, é a que está ativa abaixo) mas **não uses os resultados como
verdade** — são só um ponto de partida especulativo, se quiseres
continuar a afinar isto no futuro. Não foi um ajuste rápido de parâmetro
que faltou — é um problema de visão computacional genuinamente difícil
dado o painel LED, variações de luz/exposição, e texturas repetitivas.

Uso:
    python fase1_tracking/recalibration_candidates.py video.mp4 \
        --sample-every 1.0 --out fase1_tracking/calibration/jogo1_candidatos.csv

Depois inspeciona o CSV e, para os candidatos que confirmares visualmente
(abrindo o vídeo nesse timestamp), corre calibration.py nesse ponto.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2
import numpy as np


def _background_strip(frame, strip_fraction: float = 0.3):
    """Recorta a faixa superior do frame (tipicamente fundo estático:
    bancada, árvores, painéis — não o relvado onde os jogadores correm)."""
    small = cv2.resize(frame, (320, 180))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    strip_h = int(gray.shape[0] * strip_fraction)
    return gray[:strip_h, :]


def _correlation(a: np.ndarray, b: np.ndarray) -> float:
    a = a.flatten().astype(np.float64)
    b = b.flatten().astype(np.float64)
    a -= a.mean()
    b -= b.mean()
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom < 1e-6:
        return 1.0
    return float(np.dot(a, b) / denom)


def scan_video(video_path: str, sample_every_s: float, correlation_threshold: float, progress_every: int = 100):
    """Amostra o vídeo por SEEK direto (cap.set POS_FRAMES) em vez de
    descodificar sequencialmente frame a frame — para vídeos longos (jogo
    completo, horas de duração) isto é ordens de magnitude mais rápido do
    que ler frame a frame só para descartar a maioria.

    Sinaliza um candidato quando a correlação da faixa de fundo cai abaixo
    de `correlation_threshold` face à amostra anterior (1.0 = fundo
    idêntico, valores mais baixos = fundo mudou -> câmara mexeu-se)."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise SystemExit(f"Não foi possível abrir o vídeo: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_step = max(1, int(round(fps * sample_every_s)))
    sample_frame_numbers = list(range(0, total_frames, frame_step))

    candidates = []
    prev_strip = None

    for i, frame_idx in enumerate(sample_frame_numbers):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ok, frame = cap.read()
        if not ok:
            continue

        strip = _background_strip(frame)
        t = frame_idx / fps

        if prev_strip is not None:
            corr = _correlation(prev_strip, strip)

            if corr < correlation_threshold:
                candidates.append({
                    "timestamp_s": round(t, 2),
                    "frame_number": frame_idx,
                    "background_correlation": round(corr, 3),
                    "confidence": "baixa" if corr > correlation_threshold * 0.85 else "média",
                })

        prev_strip = strip

        if progress_every and i % progress_every == 0:
            print(f"  ... {i}/{len(sample_frame_numbers)} amostras (t={t/60:.1f}min)", flush=True)

    cap.release()
    return candidates


def merge_consecutive(candidates: list[dict], gap_s: float = 2.0) -> list[dict]:
    """Junta candidatos consecutivos (mesmo evento de pan/zoom) num único
    intervalo, para não inundar o CSV com uma linha por amostra."""
    if not candidates:
        return []
    merged = [dict(candidates[0], start_s=candidates[0]["timestamp_s"], end_s=candidates[0]["timestamp_s"])]
    for c in candidates[1:]:
        last = merged[-1]
        if c["timestamp_s"] - last["end_s"] <= gap_s:
            last["end_s"] = c["timestamp_s"]
            last["background_correlation"] = min(last["background_correlation"], c["background_correlation"])
        else:
            merged.append(dict(c, start_s=c["timestamp_s"], end_s=c["timestamp_s"]))
    return merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_path")
    parser.add_argument("--sample-every", type=float, default=1.0, help="segundos entre amostras")
    parser.add_argument("--threshold", type=float, default=0.9,
                         help="correlação mínima do fundo entre amostras (1.0=idêntico); abaixo disto é sinalizado")
    parser.add_argument("--out", required=True, help="CSV de saída")
    args = parser.parse_args()

    raw = scan_video(args.video_path, args.sample_every, args.threshold)
    merged = merge_consecutive(raw)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["start_s", "end_s", "background_correlation", "confidence"])
        writer.writeheader()
        for row in merged:
            writer.writerow({k: row[k] for k in writer.fieldnames})

    print(f"{len(merged)} candidato(s) a mudança de enquadramento -> {out_path}")
    print("Isto é uma heurística — confirma visualmente cada candidato antes de recalibrar.")
