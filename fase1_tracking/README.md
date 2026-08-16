# Fase 1 — Tracking

🟢 **Implementada (v1), por validar com jogo real.** Pipeline pronto e
testado estruturalmente (smoke test), mas ainda sem calibração real nem
vídeo suficientemente longo para validar qualidade.

## Contexto da decisão de design

A Fase 0 tentou confirmar que a Veo tem um modo de export "Tactical/
Panoramic" totalmente fixo. Ao aprofundar, a informação pública revelou-se
inconsistente: pode ser uma definição da câmara (não do export), e mesmo o
modo Tactical "segue a bola" em plano largo — ou seja, **não podemos
assumir enquadramento 100% fixo durante o jogo todo**, mesmo no melhor
cenário.

Por isso, em vez de "uma calibração manual por jogo" (assunção original),
o pipeline foi desenhado para **várias calibrações (keyframes) por jogo**,
com uma heurística a sugerir *quando* pode ser preciso recalibrar — sempre
com confirmação humana antes de qualquer recalibração ser aplicada. A
calibração em si continua a ser manual (nunca homografia automática, como
pedido).

## Como funciona

1. **`calibration.py`** — script interativo (corre localmente, não no
   sandbox remoto — precisa de ecrã). Abre uma frame do vídeo num
   timestamp à tua escolha, clicas pontos de referência do campo (cantos,
   áreas, círculo central), e guarda um "keyframe" de calibração num JSON.
   Podes correr isto várias vezes no mesmo jogo, em timestamps diferentes,
   para acrescentar keyframes adicionais.

2. **`recalibration_candidates.py`** — heurística (fluxo ótico) que
   percorre o vídeo e sinaliza momentos onde o enquadramento pode ter
   mudado, com um score de confiança. **Não é uma deteção fiável** — serve
   só para não teres de vasculhar o jogo todo manualmente à procura de
   onde recalibrar. Confirma sempre visualmente antes de agir.

3. **`track.py`** — corre YOLO + ByteTrack (via `ultralytics`) sobre o
   vídeo, e para cada deteção usa o keyframe de calibração ativo nesse
   timestamp para converter pixels em metros no campo. Output: `.parquet`
   com uma linha por deteção (frame, timestamp, track_id, classe,
   posição em pixels e em metros, se dentro do campo, id do keyframe
   usado).

4. **`homography.py`** / **`pitch_reference.py`** — funções puras de
   apoio (sem GUI), com testes rápidos possíveis fora do vídeo real.

## Limitações conhecidas — testadas, não hipotéticas

Corri um smoke test end-to-end com o clip de 9s que já enviaste
(`Amora vs Belenenses`), com uma calibração fictícia só para validar que o
pipeline corre sem erros. Resultados reais desse teste, não suposições:

- **O modelo YOLO pré-treinado (COCO) não detetou a bola nenhuma vez** no
  clip — bola pequena/distante numa vista wide-angle é um problema
  conhecido de modelos genéricos. Vamos provavelmente precisar de um
  modelo afinado especificamente para bola de futebol em vista tática, ou
  aceitar que a deteção da bola é o ponto mais fraco do pipeline nesta
  fase.
- **59 track_ids diferentes** foram gerados para o que deviam ser ~14-20
  pessoas em campo (jogadores + staff) ao longo de só 298 frames —
  confirma a limitação já esperada: o ByteTrack troca/perde IDs com
  facilidade, não tratar track_id como identidade fiável de jogador.
- O modelo deteta a classe genérica "person" — não distingue equipas,
  árbitro, ou banco. Sem separação por equipa nesta fase.

Nenhuma destas limitações bloqueia a fase — só significa que os dados
desta fase são um ponto de partida para heurísticas (Fase 2), não um
tracking "pronto a usar" sem revisão.

## Como usar (num jogo real)

```bash
# 1. Calibrar (localmente, com ecrã):
python fase1_tracking/calibration.py video.mp4 --timestamp 0 \
    --out fase1_tracking/calibration/jogo1.json

# 2. (opcional) ver onde pode ser preciso recalibrar:
python fase1_tracking/recalibration_candidates.py video.mp4 \
    --out fase1_tracking/calibration/jogo1_candidatos.csv
# confirma visualmente cada candidato e, se necessário, repete o passo 1
# nesse timestamp (acrescenta um novo keyframe ao mesmo JSON)

# 3. Correr o tracking:
python fase1_tracking/track.py video.mp4 \
    --calibration fase1_tracking/calibration/jogo1.json \
    --out fase1_tracking/output/jogo1_tracking.parquet
```

## Próximo passo

Preciso de um vídeo mais longo (idealmente um jogo completo, ou pelo menos
vários minutos com jogadas variadas) para calibrar de verdade e avaliar a
qualidade do tracking antes de avançar para a Fase 2 (heurísticas de
eventos). Sem isso, não há como validar se o pipeline serve o propósito.
