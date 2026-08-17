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

2. **`recalibration_candidates.py`** — ⚠️ **experimental, não confiável**
   (ver secção "Jogo completo" abaixo). Tentativa de heurística
   automática para sinalizar mudanças de enquadramento — três abordagens
   diferentes testadas com o jogo real, nenhuma deu um sinal em que se
   possa confiar. **Recomendação atual: inspeção visual manual espaçada**
   (abrir o vídeo a cada 5-10min e ver se o enquadramento mudou), não
   este script.

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

## Validação com jogo completo real

Recebemos o jogo completo (`Amora vs Clube de Futebol Os Belenenses`) via
GitHub Release — 1.94GB, 1280x720, 30fps, 166min de ficheiro. Achados:

- **Conteúdo real só até ~127min** — dos 128min aos 166min é frame preto
  (brilho médio ~0), gravação morta depois do jogo. Ao processar este
  jogo, cortar ali para não desperdiçar tempo de cálculo.
- **Tentei 3 heurísticas automáticas diferentes para detetar mudanças de
  enquadramento da câmara, nenhuma funcionou de forma fiável:**
  1. Fluxo ótico médio sobre o frame inteiro → sinalizou 58% do vídeo
     (inútil — o movimento normal dos jogadores já basta para disparar).
  2. Correlação de uma faixa de fundo do frame → devia ficar estável em
     períodos parados, mas caiu para 0.1-0.4 mesmo com só 1 minuto de
     diferença e câmara aparentemente fixa — há um **painel publicitário
     LED com conteúdo a mudar** que contamina a medição.
  3. Feature matching (ORB) + homografia entre frames → deslocamentos
     estimados sem sentido físico, por causa de texturas repetitivas
     (relva, bancada, folhagem) a confundir o matching.

  Isto não foi falta de afinar um parâmetro — é um problema de visão
  computacional genuinamente difícil com este tipo de fundo. Decisão:
  não insistir mais nisto por agora. `recalibration_candidates.py` fica
  no repositório marcado como experimental/não confiável, caso valha a
  pena retomar mais tarde (ex.: mascarar a zona do painel LED, ou usar
  deteção de linhas do campo em vez de features genéricas).
- Inspeção visual manual (frames a cada 5min ao longo do jogo todo)
  mostra o enquadramento a variar em vários pontos, mas sem um padrão
  fácil de automatizar com o tempo disponível — fica confirmado que o
  design de "múltiplos keyframes de calibração por jogo" é mesmo
  necessário, e que a forma prática de decidir onde os colocar é
  inspeção manual espaçada, não deteção automática.

## Como usar (num jogo real)

```bash
# 1. Calibrar (localmente, com ecrã):
python fase1_tracking/calibration.py video.mp4 --timestamp 0 \
    --out fase1_tracking/calibration/jogo1.json

# 2. Vê o vídeo a saltar de 5 em 5 minutos e anota os timestamps onde o
#    enquadramento muda visivelmente (recalibration_candidates.py é
#    experimental e não fiável — não uses os resultados dele para isto).
#    Para cada timestamp identificado, repete o passo 1 nesse ponto
#    (acrescenta um novo keyframe ao mesmo JSON).

# 3. Correr o tracking:
python fase1_tracking/track.py video.mp4 \
    --calibration fase1_tracking/calibration/jogo1.json \
    --out fase1_tracking/output/jogo1_tracking.parquet
```

## Próximo passo

Já temos o jogo completo. Falta:
1. Calibrar de verdade (clicagem manual dos pontos de referência, com
   ecrã — não pode ser feito neste sandbox remoto).
2. Correr `track.py` sobre o jogo completo (ou um excerto representativo)
   e avaliar a qualidade real do tracking antes de avançar para a Fase 2.
