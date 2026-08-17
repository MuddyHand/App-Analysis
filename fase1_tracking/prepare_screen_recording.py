"""
Prepara uma gravação de ecrã do modo Panorâmico da Veo para calibração/
tracking: remove as barras pretas (letterbox) e, opcionalmente, uma
margem extra para cortar a interface do leitor (ícones/barra de
progresso) que fica sobreposta ao vídeo.

TESTADO com um exemplo real enviado pelo utilizador: no exemplo, a área
útil (sem letterbox) era 1920x970 de um frame 1920x1080 — a interface do
leitor (ícones em cima, controlos de reprodução em baixo) fica dentro
dessa área útil, sobre zonas de bancada/céu, não sobre o relvado. Por
isso os valores por omissão de margem extra (--top-margin/--bottom-margin)
são uma estimativa a partir desse exemplo, não uma deteção garantida —
confirma visualmente com --preview antes de processar o vídeo todo.

MELHOR SOLUÇÃO (evita este script todo): ao gravar o ecrã, afasta o rato
da janela do vídeo antes de começar e usa o modo de ecrã inteiro do
browser — a maioria dos leitores esconde os controlos ao fim de poucos
segundos sem interação do rato, e a gravação fica limpa sem precisar de
recorte.

Uso:
    # ver só a proposta de corte numa frame, sem processar o vídeo todo:
    python fase1_tracking/prepare_screen_recording.py gravacao.mp4 --preview

    # processar o vídeo todo:
    python fase1_tracking/prepare_screen_recording.py gravacao.mp4 \
        --out fase1_tracking/video_input/panoramico_cortado.mp4
"""

from __future__ import annotations

import argparse

import cv2
import numpy as np


def detect_letterbox_bbox(frame: np.ndarray, black_threshold: float = 10.0) -> tuple[int, int, int, int]:
    """Devolve (top, bottom, left, right) — a bbox de conteúdo não-preto."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    row_means = gray.mean(axis=1)
    col_means = gray.mean(axis=0)

    top = 0
    while top < len(row_means) - 1 and row_means[top] < black_threshold:
        top += 1
    bottom = len(row_means) - 1
    while bottom > 0 and row_means[bottom] < black_threshold:
        bottom -= 1
    left = 0
    while left < len(col_means) - 1 and col_means[left] < black_threshold:
        left += 1
    right = len(col_means) - 1
    while right > 0 and col_means[right] < black_threshold:
        right -= 1

    return top, bottom, left, right


def crop_video(video_path: str, out_path: str, top_margin: int, bottom_margin: int,
                left_margin: int, right_margin: int) -> None:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise SystemExit(f"Não foi possível abrir o vídeo: {video_path}")

    ok, first_frame = cap.read()
    if not ok:
        raise SystemExit("Vídeo vazio ou ilegível.")

    top, bottom, left, right = detect_letterbox_bbox(first_frame)
    top += top_margin
    bottom -= bottom_margin
    left += left_margin
    right -= right_margin

    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        raise SystemExit(f"Margens demasiado grandes — resultou em recorte inválido ({width}x{height}).")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        writer.write(frame[top:bottom, left:right])
        n += 1
        if n % 1000 == 0:
            print(f"  ... {n} frames processadas", flush=True)

    cap.release()
    writer.release()
    print(f"{n} frames -> {out_path} ({width}x{height})")


def preview(video_path: str, top_margin: int, bottom_margin: int,
            left_margin: int, right_margin: int, out_path: str) -> None:
    cap = cv2.VideoCapture(video_path)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise SystemExit("Não foi possível ler o vídeo.")

    top, bottom, left, right = detect_letterbox_bbox(frame)
    print(f"Letterbox detetado (sem margem extra): top={top} bottom={bottom} left={left} right={right}")
    top += top_margin
    bottom -= bottom_margin
    left += left_margin
    right -= right_margin
    print(f"Com margens (top+{top_margin}, bottom-{bottom_margin}, "
          f"left+{left_margin}, right-{right_margin}): "
          f"área final top={top} bottom={bottom} left={left} right={right} "
          f"({right-left}x{bottom-top})")

    marked = frame.copy()
    cv2.rectangle(marked, (left, top), (right, bottom), (0, 0, 255), 3)
    cv2.imwrite(out_path, marked)
    print(f"Pré-visualização guardada em {out_path} — confirma visualmente antes de processar o vídeo todo.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video_path")
    parser.add_argument("--out", help="vídeo cortado de saída (obrigatório sem --preview)")
    parser.add_argument("--preview", action="store_true",
                         help="só grava uma imagem com o retângulo de corte proposto, não processa o vídeo")
    parser.add_argument("--preview-out", default="fase1_tracking/output/_preview_corte.jpg")
    parser.add_argument("--top-margin", type=int, default=30,
                         help="pixels extra a cortar no topo (interface do leitor), além do letterbox")
    parser.add_argument("--bottom-margin", type=int, default=45,
                         help="pixels extra a cortar em baixo (controlos de reprodução), além do letterbox")
    parser.add_argument("--left-margin", type=int, default=0)
    parser.add_argument("--right-margin", type=int, default=0)
    args = parser.parse_args()

    if args.preview:
        preview(args.video_path, args.top_margin, args.bottom_margin,
                args.left_margin, args.right_margin, args.preview_out)
    else:
        if not args.out:
            raise SystemExit("--out é obrigatório sem --preview")
        crop_video(args.video_path, args.out, args.top_margin, args.bottom_margin,
                   args.left_margin, args.right_margin)
