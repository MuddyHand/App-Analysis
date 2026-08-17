"""
Fase 1 — Deteção e tracking (YOLO + ByteTrack) com projeção para
coordenadas do campo, usando a(s) calibração(ões) manual(is) geradas
por calibration.py.

LIMITAÇÕES A CONHECER (honestidade técnica, não escondas isto):
- Usa um modelo YOLO pré-treinado em COCO (deteta a classe genérica
  "person" e "sports ball"). NÃO distingue jogadores de equipas
  diferentes, árbitro, ou staff no banco — tudo o que for "person" é
  marcado. Separar por equipa (ex.: cor do equipamento) não está
  implementado nesta fase.
- ByteTrack pode perder/trocar IDs em oclusões (jogadores muito perto
  uns dos outros, perto da baliza, etc.) — não tratar os track_id como
  identidade de jogador garantida ao longo do jogo inteiro.
- A projeção para metros só é válida dentro da janela [valid_from_s,
  valid_to_s] de cada keyframe de calibração. Frames fora de todas as
  janelas calibradas ficam sem coordenadas de campo (x_m/y_m = None).
- Se a calibração usar método "poly2" (fontes com distorção de lente,
  ex. gravação do modo Panorâmico), a projeção é um ajuste empírico, não
  uma homografia exata — fiável dentro da zona coberta pelos pontos
  clicados, não garantida fora dela.
- timestamp_s no output é tempo ABSOLUTO de jogo (soma o
  clip_time_offset_s da calibração), para clips parciais (ex.: meio-
  campo) poderem ser combinados depois com merge_clips.py.

Uso:
    python fase1_tracking/track.py video.mp4 \
        --calibration fase1_tracking/calibration/jogo1.json \
        --out fase1_tracking/output/jogo1_tracking.parquet
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import pandas as pd
from ultralytics import YOLO

from homography import compute_homography, apply_homography, is_within_pitch, PolynomialWarp

COCO_PERSON = 0
COCO_SPORTS_BALL = 32


def load_calibration(path: str):
    data = json.loads(Path(path).read_text())
    dims = data["pitch_dimensions"]
    time_offset_s = data.get("clip_time_offset_s", 0.0)
    keyframes = []
    for kf in data["keyframes"]:
        image_points = [tuple(p["image_xy"]) for p in kf["points"]]
        pitch_points = [tuple(p["pitch_xy"]) for p in kf["points"]]
        method = kf.get("method", "homography")

        if method == "poly2":
            warp = PolynomialWarp.from_json(kf["polynomial"]) if "polynomial" in kf \
                else PolynomialWarp.fit(image_points, pitch_points)
            project = warp.apply
        else:
            H = compute_homography(image_points, pitch_points)
            project = lambda x, y, H=H: apply_homography(H, x, y)

        keyframes.append({
            "id": kf["id"],
            "valid_from_s": kf["valid_from_s"],
            "valid_to_s": kf["valid_to_s"],
            "project": project,
            "method": method,
        })
    return dims, keyframes, time_offset_s


def active_keyframe(keyframes: list[dict], t: float):
    for kf in keyframes:
        if t >= kf["valid_from_s"] and (kf["valid_to_s"] is None or t < kf["valid_to_s"]):
            return kf
    return None


def _video_fps(video_path: str) -> float:
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.release()
    return fps


def run_tracking(video_path: str, calibration_path: str, out_path: str, model_name: str) -> None:
    dims, keyframes, time_offset_s = load_calibration(calibration_path)
    model = YOLO(model_name)
    fps = _video_fps(video_path)

    results = model.track(
        source=video_path,
        classes=[COCO_PERSON, COCO_SPORTS_BALL],
        tracker="bytetrack.yaml",
        persist=True,
        stream=True,
        verbose=False,
    )

    rows = []
    frame_idx = 0

    for result in results:
        t = frame_idx / fps
        kf = active_keyframe(keyframes, t)

        boxes = result.boxes
        if boxes is not None and boxes.id is not None:
            for box, track_id, cls in zip(boxes.xyxy.cpu().numpy(), boxes.id.cpu().numpy(), boxes.cls.cpu().numpy()):
                x1, y1, x2, y2 = box
                # ponto de contacto com o chão: base do bounding box, centro horizontal
                x_px = float((x1 + x2) / 2)
                y_px = float(y2)

                x_m = y_m = None
                within_pitch = None
                calibration_id = None
                if kf is not None:
                    x_m, y_m = kf["project"](x_px, y_px)
                    within_pitch = is_within_pitch(x_m, y_m, dims["length_m"], dims["width_m"])
                    calibration_id = kf["id"]

                rows.append({
                    "frame": frame_idx,
                    "timestamp_s": round(t + time_offset_s, 3),
                    "track_id": int(track_id),
                    "class": "player_or_person" if int(cls) == COCO_PERSON else "ball",
                    "x_px": x_px,
                    "y_px": y_px,
                    "x_m": x_m,
                    "y_m": y_m,
                    "within_pitch": within_pitch,
                    "calibration_keyframe_id": calibration_id,
                })

        frame_idx += 1

    df = pd.DataFrame(rows)
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_file, index=False)

    n_uncalibrated = int((df["calibration_keyframe_id"].isna()).sum()) if not df.empty else 0
    n_outside = int((df["within_pitch"] == False).sum()) if not df.empty else 0  # noqa: E712
    print(f"{len(df)} deteções guardadas em {out_file}")
    if n_uncalibrated:
        print(f"AVISO: {n_uncalibrated} deteções sem keyframe de calibração ativo (sem x_m/y_m).")
    if n_outside:
        print(f"AVISO: {n_outside} deteções caem fora dos limites do campo — "
              f"possível erro de calibração ou deteção espúria, inspecionar.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_path")
    parser.add_argument("--calibration", required=True, help="JSON gerado por calibration.py")
    parser.add_argument("--out", required=True, help="ficheiro .parquet de saída")
    parser.add_argument("--model", default="yolov8n.pt", help="pesos YOLO (baixa automaticamente na 1a vez)")
    args = parser.parse_args()

    run_tracking(args.video_path, args.calibration, args.out, args.model)
