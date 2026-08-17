"""
Combina vários ficheiros de tracking (.parquet gerados por track.py) numa
só tabela por jogo — para o caso de "clips por meio-campo" (Veo limita a
15min por clip, e só mostra metade do campo de cada vez).

Cada clip já tem timestamp_s em tempo absoluto de jogo (graças a
--time-offset em calibration.py), por isso combinar é sobretudo
concatenar + ordenar. A parte que precisa de atenção humana é a ZONA DE
SOBREPOSIÇÃO perto do meio-campo: se os dois meios-campos foram calibrados
a partir do mesmo referencial (mesmos --pitch-length/--pitch-width), um
jogador perto do meio-campo pode aparecer nos DOIS clips ao mesmo tempo,
com coordenadas ligeiramente diferentes (erro de calibração em cada lado)
e SEM garantia de ser o mesmo track_id nos dois (o ByteTrack corre
independentemente em cada clip). Este script NÃO tenta resolver isso
automaticamente — marca as deteções na zona de sobreposição para
inspeção manual, não as remove nem as funde.

Uso:
    python fase1_tracking/merge_clips.py \
        --in fase1_tracking/output/jogo1_esquerdo_p1.parquet:esquerdo \
        --in fase1_tracking/output/jogo1_direito_p1.parquet:direito \
        --in fase1_tracking/output/jogo1_esquerdo_p2.parquet:esquerdo \
        --in fase1_tracking/output/jogo1_direito_p2.parquet:direito \
        --pitch-length 105 \
        --overlap-margin-m 5 \
        --out fase1_tracking/output/jogo1_completo.parquet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def merge(inputs: list[tuple[str, str]], pitch_length_m: float, overlap_margin_m: float) -> pd.DataFrame:
    frames = []
    for path, label in inputs:
        df = pd.read_parquet(path)
        df["source_clip"] = label
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("timestamp_s").reset_index(drop=True)

    midfield = pitch_length_m / 2
    combined["na_zona_sobreposicao"] = combined["x_m"].apply(
        lambda x: (midfield - overlap_margin_m) <= x <= (midfield + overlap_margin_m)
        if x is not None else False
    )
    return combined


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--in", dest="inputs", action="append", required=True,
        help="caminho.parquet:etiqueta (ex.: jogo1_esquerdo_p1.parquet:esquerdo), repetível",
    )
    parser.add_argument("--pitch-length", type=float, default=105.0)
    parser.add_argument("--overlap-margin-m", type=float, default=5.0,
                         help="distância ao meio-campo (m) considerada zona de sobreposição")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    parsed = []
    for item in args.inputs:
        if ":" not in item:
            raise SystemExit(f"--in precisa do formato caminho:etiqueta, recebeu '{item}'")
        path, label = item.rsplit(":", 1)
        parsed.append((path, label))

    result = merge(parsed, args.pitch_length, args.overlap_margin_m)

    out_file = Path(args.out)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(out_file, index=False)

    n_overlap = int(result["na_zona_sobreposicao"].sum())
    print(f"{len(result)} deteções combinadas de {len(parsed)} clip(s) -> {out_file}")
    print(f"AVISO: {n_overlap} deteções na zona de sobreposição perto do meio-campo "
          f"(±{args.overlap_margin_m}m) — podem estar duplicadas entre clips, inspecionar "
          f"antes de usar para contagens (coluna 'na_zona_sobreposicao').")
