# Fase 0 — Validação de acesso a dados

Objetivo desta fase: decidir se vamos trabalhar com a **API oficial da Veo**
(`api.veo.co`) ou com **export manual de mp4**, antes de avançar para o
tracking (Fase 1). Não se avança sem essa decisão confirmada.

## Estado

✅ **Fechada.** Decisão: seguir com o caminho B (export manual mp4) para
desbloquear a Fase 1. Caminho A (API) fica em aberto para integrar mais
tarde, se/quando houver credenciais — sem bloquear o progresso entretanto.

## Validação feita

- Testado com um excerto real exportado da Veo (`Amora vs Clube de Futebol
  Os Belenenses`, 1280x720, ~30fps). Ficheiro abre corretamente, qualidade
  suficiente para tracking.
- **Achado importante:** a Veo tem dois modos de exportação —
  **Broadcast/Follow-cam** (zoom/pan automático a seguir a bola — a baliza
  oposta pode sair de vista) e **Tactical/Panoramic view** (plano fixo,
  campo inteiro sempre visível, sem zoom automático). A câmara grava sempre
  o campo completo (lentes wide-angle); o follow-cam é só uma vista gerada
  a partir dessa gravação.
  **Para a Fase 1, o export tem de ser sempre em modo Tactical/Panoramic** —
  é isso que sustenta a premissa de "uma calibração manual dos pontos de
  referência por frame fixa por jogo". Em modo Broadcast essa premissa
  não se aplica (o enquadramento muda dentro do próprio jogo).

## O que preciso de ti para correr isto

### Caminho A — API Veo
1. **Credenciais de acesso à API.** A Veo não tem um portal de developer
   claro e público — normalmente é preciso pedir acesso à equipa de suporte
   da Veo (via app/site, referindo que és cliente e queres aceder à API de
   dados). O que precisamos é um dos seguintes:
   - Um token de acesso (Bearer) já emitido, **ou**
   - Um `client_id` + `client_secret`.
   Coloca o que tiveres em `.env` (copia de `.env.example`), nunca no código.
2. Confirmar se a tua conta Veo tem a subscrição/plano que dá acesso à API
   (algumas funcionalidades da API são pagas ou por convite).

Corre depois:
```bash
python fase0_api/test_veo_api_access.py
```
Isto tenta autenticar e faz `GET` a um conjunto de endpoints candidatos
(`/me`, `/recordings`, `/matches`, `/videos`) — **os endpoints são hipóteses**,
não estão confirmados pela documentação pública. As respostas brutas ficam
em `fase0_api/output/*.json` (pasta ignorada pelo git) para inspecionarmos
juntos e ajustarmos.

### Caminho B — Export manual mp4
1. Um ficheiro `.mp4` exportado manualmente da Veo (um jogo, ou um excerto).
   Não precisa de ser o jogo todo — 5-10 minutos com um pontapé de baliza e
   um cruzamento já chega para validar o caminho.

Corre depois:
```bash
python fase0_api/test_manual_export.py caminho/para/o/video.mp4
```
Isto só confirma que o ficheiro abre e imprime metadados (resolução, fps,
duração) — não faz deteção nem tracking.

## Caminho A (API) — em aberto, não bloqueia

Continua sem credenciais. Quando (e se) chegarem, corre:
```bash
python fase0_api/test_veo_api_access.py
```
e integramos o que fizer sentido (ex.: eventos já etiquetados) como
complemento ao pipeline de vídeo — nunca como substituto, já que a Fase 1
já está a avançar com o caminho B.
