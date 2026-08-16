# Fase 1 — Tracking

⏸️ **Não implementada.** Bloqueada até a Fase 0 estar fechada (decisão
confirmada entre API Veo e/ou export manual — ver `../fase0_api/README.md`).

## O que vai entrar aqui (quando desbloqueada)

- Pipeline de deteção e tracking (YOLO + ByteTrack, ou equivalente) sobre
  o vídeo.
- Calibração do campo por **clicagem manual** dos pontos de referência numa
  frame fixa por jogo (sem homografia automática — decisão já tomada por
  falta de fiabilidade).
- Output: posições (x, y no campo) de jogadores e bola por frame, em
  parquet ou formato equivalente.

Nada disto é implementado antes de a Fase 0 confirmar a origem dos dados de
vídeo, porque isso condiciona o formato de input do pipeline.
