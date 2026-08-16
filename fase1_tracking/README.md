# Fase 1 — Tracking

🔵 **Desbloqueada** — Fase 0 fechada com decisão: vídeo exportado
manualmente da Veo, **sempre em modo Tactical/Panoramic** (não Broadcast/
Follow-cam). Ver `../fase0_api/README.md` para o porquê.

⚠️ **Requisito de input não-negociável:** qualquer vídeo usado nesta fase
tem de ser exportado em modo Tactical/Panoramic view. Em modo Broadcast, o
enquadramento muda dentro do jogo (zoom/pan automático a seguir a bola) e a
premissa de "uma calibração manual por jogo" deixa de valer — o pipeline
teria de recalibrar a cada corte, o que não está planeado nem é fiável.
Se receber um vídeo em Broadcast, sinalizo antes de processar.

## O que vai entrar aqui (ainda não implementado)

- Pipeline de deteção e tracking (YOLO + ByteTrack, ou equivalente) sobre
  o vídeo.
- Calibração do campo por **clicagem manual** dos pontos de referência numa
  frame fixa por jogo (sem homografia automática — decisão já tomada por
  falta de fiabilidade).
- Output: posições (x, y no campo) de jogadores e bola por frame, em
  parquet ou formato equivalente.
