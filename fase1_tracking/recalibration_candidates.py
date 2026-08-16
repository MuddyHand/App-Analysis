"""
Heurística para sinalizar candidatos a "o enquadramento da câmara pode
ter mudado aqui" — NÃO é deteção automática fiável, é só um filtro para
reduzires o trabalho de vasculhar o jogo todo à procura de onde
recalibrar manualmente (ver calibration.py).

Método: mede o deslocamento médio de fluxo ótico denso entre frames
amostradas. Um pan/zoom sustentado da câmara produz um fluxo médio alto
e consistente numa direção; ruído normal de jogo (jogadores a mexer-se)
tende a ser mais disperso/cancela-se. Isto é uma aproximação — pode
gerar falsos positivos (ex.: câmara genuinamente fixa mas com jogadores
a correr em massa numa direção) e falsos negativos (pans lentos e
graduais). Cada candidato tem um score, não um veredicto.

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


def scan_video(video_path: str, sample_every_s: float, motion_threshold: float):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise SystemExit(f"Não foi possível abrir o vídeo: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_step = max(1, int(round(fps * sample_every_s)))

    candidates = []
    prev_gray = None
    prev_t = None
    frame_idx = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % frame_step == 0:
            small = cv2.resize(frame, (160, 90))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            t = frame_idx / fps

            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None, 0.5, 2, 15, 3, 5, 1.2, 0
                )
                mean_dx = float(np.mean(flow[..., 0]))
                mean_dy = float(np.mean(flow[..., 1]))
                magnitude = float(np.hypot(mean_dx, mean_dy))

                if magnitude >= motion_threshold:
                    candidates.append({
                        "timestamp_s": round(t, 2),
                        "frame_number": frame_idx,
                        "mean_flow_magnitude": round(magnitude, 3),
                        "confidence": "baixa" if magnitude < motion_threshold * 1.5 else "média",
                    })

            prev_gray = gray
            prev_t = t
        frame_idx += 1

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
            last["mean_flow_magnitude"] = max(last["mean_flow_magnitude"], c["mean_flow_magnitude"])
        else:
            merged.append(dict(c, start_s=c["timestamp_s"], end_s=c["timestamp_s"]))
    return merged


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_path")
    parser.add_argument("--sample-every", type=float, default=1.0, help="segundos entre amostras")
    parser.add_argument("--threshold", type=float, default=0.8, help="magnitude mínima de fluxo para sinalizar")
    parser.add_argument("--out", required=True, help="CSV de saída")
    args = parser.parse_args()

    raw = scan_video(args.video_path, args.sample_every, args.threshold)
    merged = merge_consecutive(raw)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["start_s", "end_s", "mean_flow_magnitude", "confidence"])
        writer.writeheader()
        for row in merged:
            writer.writerow({k: row[k] for k in writer.fieldnames})

    print(f"{len(merged)} candidato(s) a mudança de enquadramento -> {out_path}")
    print("Isto é uma heurística — confirma visualmente cada candidato antes de recalibrar.")
