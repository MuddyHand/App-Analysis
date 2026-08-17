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

## Duas fontes de vídeo suportadas

A Veo não permite exportar a câmara Panorâmica diretamente. Depois de
validar (ver secção seguinte) que essa vista é genuinamente estável
(câmara parada, sem pan/zoom automático — ao contrário do export
normal), o pipeline suporta duas formas de lá chegar:

**A. Panorâmico + gravação de ecrã** — abres o jogo na app/site da Veo,
mudas para modo Panorâmico (campo inteiro), gravas o ecrã durante o
jogo. Vantagem: uma vista só, as duas balizas sempre visíveis, uma
calibração chega para o jogo todo. Desvantagens reais, testadas com um
exemplo enviado:
- **Distorção de lente wide-angle/fisheye** (linhas do campo aparecem
  curvas) — uma homografia normal de 4 pontos não é precisa. Por isso
  foi adicionado um segundo método de projeção, **`poly2`** (ver
  `homography.py`): ajuste polinomial de 2º grau com >= 6 pontos, que
  absorve parte da distorção. Não é uma correção física da lente, é um
  ajuste empírico — fiável dentro da zona coberta pelos pontos clicados.
- A gravação de ecrã inclui **barras pretas e a interface do leitor**
  (ícones, barra de progresso). Usa **`prepare_screen_recording.py`**
  para recortar isso antes de calibrar — testado com o exemplo real
  enviado, resultado limpo (só ficou um cursor do rato, pequeno, no céu,
  sem interferir com o campo).
- **Ficheiro grande**: à taxa de bits do exemplo testado, um jogo
  completo dava ~8-9GB — passa o limite de 2GB por asset do GitHub
  Release, pode ser preciso dividir a gravação em partes.
- Gravar o jogo todo ao vivo é operacionalmente exigente (alguém tem de
  estar a gravar o ecrã ~90-100min seguidos). **Sugestão para gravações
  futuras:** afasta o rato do vídeo antes de começar e usa o modo de
  ecrã inteiro do browser — a maioria dos leitores esconde os controlos
  ao fim de segundos sem interação, evitando precisar de
  `prepare_screen_recording.py` de todo.

**B. Clips por meio-campo** — na app da Veo, fixas manualmente a câmara
num meio-campo e exportas um clip normal (a Veo limita a 15min por
clip, por isso um jogo dá ~12 clips: 2 meios-campo × ~6 segmentos de
15min). Vantagem: export nativo, sem distorção, sem gravação ao vivo —
podes fazer depois do jogo, a partir da gravação normal. Desvantagem:
cada clip só mostra metade do campo, por isso o tracking corre
**separadamente por clip** e depois é preciso juntar tudo com
**`merge_clips.py`** — usa `--time-offset` em `calibration.py` para
dizeres em que minuto do jogo cada clip começa, para os timestamps
finais ficarem em tempo absoluto de jogo. A zona perto do meio-campo
pode aparecer nos dois clips ao mesmo tempo (jogador perto da linha) —
`merge_clips.py` não tenta resolver isso automaticamente, só marca essas
deteções para inspeção manual.

Ambas testadas estruturalmente (ver "Validação" abaixo) — nenhuma foi
validada ainda com um jogo completo real dessa fonte.

## Como funciona

1. **`calibration.py`** — script interativo (corre localmente, não no
   sandbox remoto — precisa de ecrã). Abre uma frame do vídeo num
   timestamp à tua escolha, clicas pontos de referência do campo (cantos,
   áreas, círculo central), e guarda um "keyframe" de calibração num JSON.
   Podes correr isto várias vezes no mesmo jogo, em timestamps diferentes,
   para acrescentar keyframes adicionais. Escolhe o método de projeção
   automaticamente (`homography` com <6 pontos, `poly2` com >=6 — força
   com `--projection`), e aceita `--time-offset` para clips parciais.

2. **`prepare_screen_recording.py`** — recorta barras pretas e interface
   do leitor de uma gravação de ecrã do modo Panorâmico, antes de
   calibrar (caminho A).

3. **`recalibration_candidates.py`** — ⚠️ **experimental, não confiável**
   (ver secção "Jogo completo" abaixo). Tentativa de heurística
   automática para sinalizar mudanças de enquadramento — três abordagens
   diferentes testadas com o jogo real, nenhuma deu um sinal em que se
   possa confiar. **Recomendação atual: inspeção visual manual espaçada**
   (abrir o vídeo a cada 5-10min e ver se o enquadramento mudou), não
   este script.

4. **`track.py`** — corre YOLO + ByteTrack (via `ultralytics`) sobre o
   vídeo, e para cada deteção usa o keyframe de calibração ativo nesse
   timestamp para converter pixels em metros no campo (via `homography`
   ou `poly2`, consoante a calibração). Output: `.parquet` com uma linha
   por deteção (frame, timestamp absoluto de jogo, track_id, classe,
   posição em pixels e em metros, se dentro do campo, id do keyframe
   usado).

5. **`merge_clips.py`** — junta vários `.parquet` de `track.py` (caminho
   B, clips por meio-campo) numa só tabela por jogo, marcando a zona de
   sobreposição perto do meio-campo para inspeção manual.

6. **`homography.py`** / **`pitch_reference.py`** — funções puras de
   apoio (sem GUI, incluindo `PolynomialWarp`), com testes rápidos
   possíveis fora do vídeo real.

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

## Validação dos exemplos (Panorâmico + meio-campo)

Recebi um exemplo de cada caminho (clips de ~14s, não o jogo todo):

- **Panorâmico (gravação de ecrã):** comparei o primeiro e o último frame
  do exemplo — enquadramento **pixel a pixel idêntico** (câmara
  genuinamente parada). Confirmada a distorção fisheye (linhas curvas) e
  a interface do leitor sobreposta. `prepare_screen_recording.py`
  testado neste exemplo real: remove barras pretas + interface,
  resultado limpo. `track.py` com calibração `poly2` corre sem erros
  sobre o vídeo recortado (teste estrutural, pontos de calibração
  aproximados à mão, não uma calibração real).
- **Meio-campo (clip nativo):** também comparei início e fim — igualmente
  estável, sem distorção visível (linhas retas). Ainda não testado com
  `track.py` + `merge_clips.py` (só recebi um clip de exemplo, não um par
  esquerdo+direito do mesmo período).
- Em ambos os exemplos, tal como no jogo completo, **a bola não foi
  detetada** — limitação já documentada, não é específica de nenhum dos
  dois caminhos.

## Como usar

**Caminho A — Panorâmico:**
```bash
# 1. Recortar a gravação de ecrã (localmente ou aqui, não precisa de GUI):
python fase1_tracking/prepare_screen_recording.py gravacao.mp4 --preview
# confirma a pré-visualização, ajusta --top-margin/--bottom-margin se preciso,
# depois processa o vídeo todo:
python fase1_tracking/prepare_screen_recording.py gravacao.mp4 \
    --out fase1_tracking/video_input/panoramico_cortado.mp4

# 2. Calibrar (localmente, com ecrã — clica pelo menos 6 pontos espalhados
#    pelo frame para o poly2 funcionar bem):
python fase1_tracking/calibration.py fase1_tracking/video_input/panoramico_cortado.mp4 \
    --timestamp 0 --out fase1_tracking/calibration/jogo1.json

# 3. Tracking:
python fase1_tracking/track.py fase1_tracking/video_input/panoramico_cortado.mp4 \
    --calibration fase1_tracking/calibration/jogo1.json \
    --out fase1_tracking/output/jogo1_tracking.parquet
```

**Caminho B — Clips por meio-campo:**
```bash
# Para cada um dos ~12 clips (repete com --time-offset correto para cada):
python fase1_tracking/calibration.py clip_esquerdo_p1.mp4 --timestamp 0 \
    --time-offset 0 --out fase1_tracking/calibration/jogo1_esq_p1.json
python fase1_tracking/track.py clip_esquerdo_p1.mp4 \
    --calibration fase1_tracking/calibration/jogo1_esq_p1.json \
    --out fase1_tracking/output/jogo1_esq_p1.parquet
# ... repetir para direito_p1, esquerdo_p2, direito_p2, etc.

# Juntar tudo:
python fase1_tracking/merge_clips.py \
    --in fase1_tracking/output/jogo1_esq_p1.parquet:esquerdo \
    --in fase1_tracking/output/jogo1_dir_p1.parquet:direito \
    --out fase1_tracking/output/jogo1_completo.parquet
```

Em ambos: vê o vídeo espaçadamente e anota timestamps onde o
enquadramento muda visivelmente — `recalibration_candidates.py` é
experimental e não fiável, não uses os resultados dele. Para cada
mudança, repete o passo de calibração nesse timestamp (acrescenta
keyframe ao mesmo JSON).

## Próximo passo

Já temos o jogo completo (caminho manual original, câmara instável —
ver "Validação com jogo completo real" acima) e exemplos validados
estruturalmente dos dois novos caminhos. Falta decidir qual caminho (A
ou B) usar de facto para um jogo completo, e depois:
1. Calibrar de verdade (clicagem manual, com ecrã — não pode ser feito
   neste sandbox remoto).
2. Correr o tracking sobre um jogo completo dessa fonte e avaliar a
   qualidade real antes de avançar para a Fase 2.
