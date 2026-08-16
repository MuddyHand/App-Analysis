# Fase 3 — Interface de etiquetagem

⏸️ **Não implementada.** Depende dos candidatos gerados na Fase 2.

## O que vai entrar aqui (quando desbloqueada)

App Streamlit que mostra o clip de cada candidato e permite confirmar/
corrigir com botões, por exemplo:
- "central saiu curto" / "saiu longo" / "não aplicável"
- "esquerda" / "centro" / "direita"
- tipo de cruzamento (categorias **a definir com o treinador antes de
  implementar** — não assumir)

Os dados confirmados são guardados em Google Sheets, usando o service
account já existente no stack de monitorização de carga. As credenciais
serão fornecidas separadamente (nunca em código).

**Antes de implementar esta fase, é preciso confirmar com o treinador:**
- categorias de tipo de cruzamento (ex.: rasteiro, tenso, alto/flutuante — a validar)
- zonas do campo (definição exata de esquerda/centro/direita)
- estrutura da folha de Google Sheets de destino
