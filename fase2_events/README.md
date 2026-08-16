# Fase 2 — Deteção de eventos candidatos (heurísticas)

⏸️ **Não implementada.** Depende do output da Fase 1 (tracking).

## O que vai entrar aqui (quando desbloqueada)

A partir dos dados de tracking (posições x,y por frame), gerar **candidatos
com timestamp** para:
- pontapé de baliza (curto vs. longo)
- mudança de zona de ataque (esquerda / centro / direita)
- cruzamento

Importante: cada candidato tem um **nível de confiança** associado e nunca é
tratado como facto — são heurísticas sobre trajetórias, sujeitas a falsos
positivos, que servem de ponto de partida para a etiquetagem manual na
Fase 3.
