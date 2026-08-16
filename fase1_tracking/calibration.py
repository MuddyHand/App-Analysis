"""
Ferramenta de calibração manual do campo — por clicagem de pontos de
referência numa frame do vídeo.

IMPORTANTE: este script abre uma janela gráfica (cv2.imshow) — corre-o
na tua máquina local, não neste ambiente remoto (que não tem ecrã).

Suporta **várias calibrações (keyframes) por jogo**, para lidar com
vídeo onde o enquadramento da câmara muda ao longo do jogo (ver
../fase0_api/README.md e ../fase1_tracking/README.md sobre os modos
Broadcast vs. Tactical da Veo). Não faz homografia automática — a
deteção de *quando* recalibrar é so uma sugestão heurística
(ver recalibration_candidates.py); a calibração em si é sempre manual.

Uso:
    python fase1_tracking/calibration.py video.mp4 \
        --timestamp 0 \
        --out fase1_tracking/calibration/jogo1.json

    # Mais tarde, se o enquadramento mudou aos 12m30s do jogo:
    python fase1_tracking/calibration.py video.mp4 \
        --timestamp 750 \
        --out fase1_tracking/calibration/jogo1.json   # acrescenta novo keyframe

Controlos na janela:
    clique esquerdo  -> marca um ponto (depois escreve o nome no terminal)
    u                -> desfaz o último ponto
    s                -> guarda este keyframe (precisa de >= 4 pontos)
    q / ESC           -> sai sem guardar
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2

from pitch_reference import PitchDimensions, named_reference_points
from homography import compute_homography


def load_frame_at(video_path: str, timestamp_s: float):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise SystemExit(f"Não foi possível abrir o vídeo: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_number = int(timestamp_s * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit(f"Não foi possível ler a frame no timestamp {timestamp_s}s")
    return frame, frame_number


def pick_reference_name(reference_names: list[str], point_index: int) -> str:
    print(f"\nPonto #{point_index + 1} — que ponto de referência é este?")
    for i, name in enumerate(reference_names):
        print(f"  [{i}] {name}")
    print("  [livre] escreve outro nome (para pontos fora da lista)")
    choice = input("Escolhe o índice ou escreve um nome: ").strip()
    if choice.isdigit() and int(choice) < len(reference_names):
        return reference_names[int(choice)]
    return choice or f"ponto_{point_index}"


def run_calibration(video_path: str, timestamp_s: float, out_path: str, dims: PitchDimensions) -> None:
    frame, frame_number = load_frame_at(video_path, timestamp_s)
    ref_points = named_reference_points(dims)
    ref_names = list(ref_points.keys())

    clicked: list[dict] = []
    window = "Calibracao - clica nos pontos de referencia (u=undo, s=guardar, q=sair)"

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            name = pick_reference_name(ref_names, len(clicked))
            pitch_xy = ref_points.get(name)
            if pitch_xy is None:
                print(f"Nome '{name}' não está na lista de pontos nomeados — "
                      "não sei as coordenadas em metros, ponto ignorado.")
                return
            clicked.append({"name": name, "image_xy": [float(x), float(y)], "pitch_xy": list(pitch_xy)})
            print(f"  + {name} @ pixel ({x},{y}) -> campo {pitch_xy} m")

    cv2.namedWindow(window)
    cv2.setMouseCallback(window, on_mouse)

    while True:
        display = frame.copy()
        for p in clicked:
            xy = tuple(int(v) for v in p["image_xy"])
            cv2.circle(display, xy, 5, (0, 0, 255), -1)
            cv2.putText(display, p["name"], (xy[0] + 6, xy[1] - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
        cv2.imshow(window, display)
        key = cv2.waitKey(20) & 0xFF

        if key == ord("u") and clicked:
            removed = clicked.pop()
            print(f"  - removido {removed['name']}")
        elif key == ord("s"):
            if len(clicked) < 4:
                print(f"Precisas de pelo menos 4 pontos (tens {len(clicked)}).")
                continue
            break
        elif key in (ord("q"), 27):
            print("Cancelado, nada foi guardado.")
            cv2.destroyAllWindows()
            return

    cv2.destroyAllWindows()

    # Valida já a homografia antes de guardar (falha cedo se os pontos forem maus).
    image_points = [tuple(p["image_xy"]) for p in clicked]
    pitch_points = [tuple(p["pitch_xy"]) for p in clicked]
    compute_homography(image_points, pitch_points)  # levanta erro se degenerado

    out_file = Path(out_path)
    data = {"video_path": video_path, "pitch_dimensions": dims.__dict__, "keyframes": []}
    if out_file.exists():
        data = json.loads(out_file.read_text())

    keyframe_id = len(data["keyframes"])
    # fecha a validade do keyframe anterior no momento deste novo
    if data["keyframes"]:
        data["keyframes"][-1]["valid_to_s"] = timestamp_s

    data["keyframes"].append({
        "id": keyframe_id,
        "frame_number": frame_number,
        "timestamp_s": timestamp_s,
        "valid_from_s": timestamp_s,
        "valid_to_s": None,
        "points": clicked,
    })

    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(f"\nKeyframe #{keyframe_id} guardado em {out_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_path")
    parser.add_argument("--timestamp", type=float, default=0.0, help="segundos no vídeo")
    parser.add_argument("--out", required=True, help="ficheiro JSON de calibração do jogo")
    parser.add_argument("--pitch-length", type=float, default=105.0)
    parser.add_argument("--pitch-width", type=float, default=68.0)
    args = parser.parse_args()

    dims = PitchDimensions(length_m=args.pitch_length, width_m=args.pitch_width)
    run_calibration(args.video_path, args.timestamp, args.out, dims)
