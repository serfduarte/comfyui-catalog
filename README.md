# comfyui-catalog
# 🎨 Catálogo ComfyUI – Sérgio Duarte

Aplicação web em Streamlit para catalogar e consultar Modelos, LoRAs e Workflows do ComfyUI, com dados sincronizados diretamente do Google Sheets.

## 🚀 Funcionalidades

- ✅ Catálogo de Modelos e LoRAs com filtros (tipo, base model, estilo, pesquisa livre)
- ✅ Catálogo de Workflows com parâmetros recomendados (KSampler, dependências, etc.)
- ✅ Leitura direta do Google Sheets (URL ou Sheet ID)
- ✅ Exportação de resultados filtrados para CSV
- ✅ Interface responsiva, cache e mensagens de erro claras

---

## 📋 Pré-requisitos

- Conta Google (para criar o Google Sheet)
- Conta GitHub (para hospedar o código)
- Conta Streamlit Cloud (gratuita, para publicar a app)

---

## 🧩 Estrutura do Google Sheet

Crie um Google Sheet com duas abas (nomes exatos):

1) modelos_loras
   - Cabeçalhos:
     ```
     tipo, nome, base_model, estilo_utilizacao, dimensions_recomendadas, strength_tipica, notas, fonte_url, caminho_local, ultima_atualizacao
     ```

2) workflows
   - Cabeçalhos:
     ```
     nome, objetivo, nodes_principais, ksampler_recomendado, dependencias, tempo_medio, qualidade_esperada, link, versao, ultima_atualizacao
     ```

Exemplos (pode colar no Sheet):

- modelos_loras:
