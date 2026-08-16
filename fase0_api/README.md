# Fase 0 — Validação de acesso a dados

Objetivo desta fase: decidir se vamos trabalhar com a **API oficial da Veo**
(`api.veo.co`) ou com **export manual de mp4**, antes de avançar para o
tracking (Fase 1). Não se avança sem essa decisão confirmada.

## Estado

🔵 Scripts de teste criados. A aguardar input para os correr.

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

## Decisão a tomar no fim desta fase

- Se a API der acesso a eventos já etiquetados (mesmo que poucos) que
  reduzam trabalho manual → caminho A, complementado com B onde faltar.
- Se a API não der nada de útil (ou acesso for negado/pago) → caminho B
  como único caminho.

**Não avanço para a Fase 1 (tracking) sem confirmares esta decisão.**
