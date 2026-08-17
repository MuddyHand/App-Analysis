# App-Analysis — Análise Tática de Vídeo (Veo)

Ferramenta complementar ao dashboard de monitorização de carga (Streamlit + Plotly + Google Sheets) já existente. Esta app processa vídeo exportado da câmara Veo para extrair estatísticas táticas específicas, através de um fluxo **semi-automático**: deteção assistida por IA + confirmação/etiquetagem manual por um treinador.

## Estatísticas-alvo

1. Lado de construção do ataque (esquerda / centro / direita) por posse de bola.
2. Saídas de jogo curtas pelos centrais no pontapé de baliza vs. jogo longo/direto.
3. Tipo de cruzamento efetuado (categorias a definir — ver Fase 3).

## Estado do projeto

| Fase | Descrição | Estado |
|---|---|---|
| **Fase 0** | Validação de acesso a dados (API Veo vs. export manual mp4) | ✅ Fechada — ver `fase0_api/README.md` |
| Fase 1 | Tracking (deteção + tracking de jogadores/bola, calibração do campo) | 🟢 Implementada (v1) — por validar com jogo real, ver `fase1_tracking/README.md` |
| Fase 2 | Deteção de eventos candidatos (heurísticas sobre tracking) | ⏸️ Não iniciada |
| Fase 3 | Interface de etiquetagem (Streamlit) | ⏸️ Não iniciada |
| Fase 4 | Relatório (dashboard Streamlit + Plotly) | ⏸️ Não iniciada |

**Regra de trabalho:** não se avança de fase sem confirmação explícita. Decisões táticas (categorias de cruzamento, definição de zonas do campo, etc.) são do treinador, não são assumidas no código.

## Estrutura

```
fase0_api/       # Fase 0 — teste de acesso à API Veo + validação do caminho manual (mp4)
fase1_tracking/  # Fase 1 — pipeline de tracking (a implementar após decisão da Fase 0)
fase2_events/    # Fase 2 — heurísticas de deteção de eventos candidatos
fase3_labeling/  # Fase 3 — app Streamlit de etiquetagem
fase4_report/    # Fase 4 — dashboard de relatório
```

Cada pasta de fase tem o seu próprio `README.md` com o detalhe específico dessa fase.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencher com credenciais reais — nunca commitar .env
```

## Próximo passo

Já temos o jogo completo (via GitHub Release) e a Fase 1 (tracking) tem
uma v1 implementada. Limitações conhecidas, testadas com dados reais (ver
`fase1_tracking/README.md`): deteção de bola fraca, IDs de tracking
instáveis, e a deteção automática de mudanças de enquadramento da câmara
não é fiável (3 heurísticas tentadas, nenhuma funcionou — recomenda-se
inspeção visual manual). Falta calibrar o jogo (só pode ser feito
localmente, com ecrã) e correr o tracking sobre o jogo completo antes de
avançar para a Fase 2.
