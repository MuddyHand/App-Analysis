"""
Fase 0 — Validação do caminho alternativo: ficheiro mp4 exportado
manualmente da Veo (sem depender da API).

Não faz deteção nem tracking — só confirma que o vídeo abre, e imprime
metadados básicos (resolução, fps, duração, nº de frames) para percebermos
se a qualidade/estabilização exportada é suficiente para a Fase 1.

Uso:
    python fase0_api/test_manual_export.py caminho/para/video.mp4

Ou definir MANUAL_EXPORT_MP4_PATH no .env e correr sem argumentos.
"""

import os
import sys

import cv2
from dotenv import load_dotenv

load_dotenv()


def inspect_video(path: str) -> int:
    if not os.path.isfile(path):
        print(f"Ficheiro não encontrado: {path}")
        return 1

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"Não foi possível abrir o vídeo (formato/codec não suportado?): {path}")
        return 1

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_s = frame_count / fps if fps else 0

    ok, frame = cap.read()
    cap.release()

    print(f"Ficheiro: {path}")
    print(f"Resolução: {width}x{height}")
    print(f"FPS: {fps:.2f}")
    print(f"Frames: {frame_count}")
    print(f"Duração estimada: {duration_s / 60:.1f} min")
    print(f"Primeira frame legível: {'sim' if ok and frame is not None else 'não'}")

    return 0


if __name__ == "__main__":
    video_path = sys.argv[1] if len(sys.argv) > 1 else os.getenv("MANUAL_EXPORT_MP4_PATH", "")
    if not video_path:
        print(
            "Indica o caminho do vídeo como argumento ou define "
            "MANUAL_EXPORT_MP4_PATH no .env."
        )
        sys.exit(1)

    sys.exit(inspect_video(video_path))
