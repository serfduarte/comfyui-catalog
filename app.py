import os
import re
import json
import pandas as pd
import streamlit as st

# Dependências Google (apenas necessárias se usar Service Account)
import gspread
from google.oauth2.service_account import Credentials

# =========================
# CONFIGURAÇÃO STREAMLIT
# =========================
st.set_page_config(
    page_title="Catálogo ComfyUI - Sérgio Duarte",
    page_icon="🎨",
    layout="wide"
)

st.title("🎨 Catálogo ComfyUI")
st.caption("Modelos, LoRAs e Workflows organizados | por Sérgio Duarte")

# =========================
# UTILITÁRIOS
# =========================
def extract_sheet_id(url_or_id: str) -> str:
    """
    Aceita URL completa do Google Sheet OU Sheet ID e retorna o ID.
    """
    if not url_or_id:
        return ""
    # Se já parece um ID puro
    if re.fullmatch(r"[A-Za-z0-9-_]{20,}", url_or_id):
        return url_or_id
    # Extrai de uma URL
    m = re.search(r"/spreadsheets/d/([A-Za-z0-9-_]+)", url_or_id)
    return m.group(1) if m else url_or_id

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza nomes de colunas para minúsculas e sem espaços extras.
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def ensure_cols(df, cols):
    """
    Garante que todas as colunas esperadas existem.
    """
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df

# =========================
# AUTENTICAÇÃO GOOGLE
# =========================
@st.cache_resource
def get_google_client():
    """
    Autentica com Google Sheets usando:
    - st.secrets["gcp_service_account"] (recomendado no Streamlit Cloud), ou
    - variável de ambiente GOOGLE_CREDENTIALS (JSON string), para uso local.
    """
    credentials_dict = None

    # 1) Streamlit Cloud Secrets
    if "gcp_service_account" in st.secrets:
        credentials_dict = dict(st.secrets["gcp_service_account"])

    # 2) Ambiente local (opcional)
    if not credentials_dict:
        try:
            env_json = os.environ.get("GOOGLE_CREDENTIALS", "")
            if env_json.strip():
                credentials_dict = json.loads(env_json)
        except Exception:
            pass

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]

    if credentials_dict:
        try:
            creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            st.error(f"❌ Erro ao autenticar Service Account: {e}")
            st.info("Dica: verifique o bloco [gcp_service_account] nos Secrets e as quebras de linha da private_key.")
            return None
    else:
        # Sem Service Account — será necessário o Sheet estar com “Anyone with the link: Viewer”
        return None

@st.cache_data(ttl=300)
def load_sheet(sheet_url_or_id: str):
    """
    Carrega as folhas 'modelos_loras' e 'workflows' do Google Sheets.
    - Se houver Service Account, usa gspread (open_by_key).
    - Caso contrário, tenta gspread anónimo (falhará se o Sheet não estiver público).
    """
    sheet_id = extract_sheet_id(sheet_url_or_id)
    client = get_google_client()

    try:
        if client:
            sh = client.open_by_key(sheet_id)
        else:
            # Sem credenciais, tentativa com gspread anónimo não é suportada oficialmente.
            # Usuário deve colocar o Sheet como "Anyone with the link: Viewer" e ainda assim
            # open_by_key pode exigir credenciais. Mantemos a necessidade de Service Account
            # para leitura segura. Logo, explicitamos o erro amigável:
            raise RuntimeError("Sem credenciais. Configure a Service Account OU use Secrets.")
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), f"Falha ao abrir Sheet (ID: {sheet_id}): {e}"

    try:
        ws_ml = sh.worksheet("modelos_loras")
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), f"Folha 'modelos_loras' não encontrada: {e}"

    try:
        ws_wf = sh.worksheet("workflows")
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), f"Folha 'workflows' não encontrada: {e}"

    try:
        df_ml = pd.DataFrame(ws_ml.get_all_records()).fillna("")
        df_wf = pd.DataFrame(ws_wf.get_all_records()).fillna("")
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), f"Erro ao ler dados do Sheet: {e}"

    # Normalização
    df_ml = normalize_columns(df_ml).astype(str)
    df_wf = normalize_columns(df_wf).astype(str)

    return df_ml, df_wf, None

def filter_modelos_loras(df, filtro_tipo, filtro_base, filtro_estilo, filtro_search):
    filtered = df.copy()
    if filtro_tipo:
        filtered = filtered[filtered["tipo"].isin(filtro_tipo)]
    if filtro_base:
        filtered = filtered[filtered["base_model"].isin(filtro_base)]
    if filtro_estilo:
        filtered = filtered[filtered["estilo_utilizacao"].str.contains(
            filtro_estilo, case=False, na=False, regex=False
        )]
    if filtro_search:
        patt = filtro_search.lower()
        mask = (
            filtered["nome"].str.lower().str.contains(patt, na=False, regex=False) |
            filtered["notas"].str.lower().str.contains(patt, na=False, regex=False)
        )
        filtered = filtered[mask]
    return filtered.reset_index(drop=True)

def filter_workflows(df, filtro_objetivo, filtro_search):
    filtered = df.copy()
    if filtro_objetivo:
        filtered = filtered[filtered["objetivo"].str.contains(
            filtro_objetivo, case=False, na=False, regex=False
        )]
    if filtro_search:
        patt = filtro_search.lower()
        mask = (
            filtered["nome"].str.lower().str.contains(patt, na=False, regex=False) |
            filtered["nodes_principais"].str.lower().str.contains(patt, na=False, regex=False) |
            filtered["dependencias"].str.lower().str.contains(patt, na=False, regex=False)
        )
        filtered = filtered[mask]
    return filtered.reset_index(drop=True)

# =========================
# ENTRADA: Sheet URL/ID
# =========================
DEFAULT_URL = "https://docs.google.com/spreadsheets/d/SEU_SHEET_ID_AQUI/edit"
SHEET_URL = st.secrets.get("sheet_url", DEFAULT_URL)

with st.sidebar:
    st.header("🛠️ Configuração")
    st.write("Fonte:", "Google Sheets")
    st.text_input("Sheet URL ou ID", value=SHEET_URL, key="sheet_url_input")
    colA, colB = st.columns(2)
    with colA:
        if st.button("🔄 Recarregar dados", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with colB:
        show_debug = st.checkbox("Modo debug", value=False)

    st.markdown("---")
    st.subheader("🔎 Filtros - Modelos/LoRAs")
    filtro_tipo = st.multiselect("Tipo", ["Modelo", "LoRA"], default=[])
    filtro_base = st.multiselect("Base Model", ["SD 1.5", "SDXL", "FLUX", "Outro"], default=[])
    filtro_estilo = st.text_input("Estilo/Utilização contém", "", placeholder="ex: Retrato, Arquitetura...")
    filtro_search_ml = st.text_input("Pesquisa livre (nome/notas)", "", placeholder="ex: realistic, portrait...")

    st.markdown("---")
    st.subheader("🔎 Filtros - Workflows")
    filtro_objetivo = st.text_input("Objetivo contém", "", placeholder="ex: Retrato realista...")
    filtro_search_wf = st.text_input("Pesquisa livre (nome/nodes)", "", placeholder="ex: KSampler, HighRes...")

# =========================
# CARREGAR DADOS
# =========================
with st.spinner("📥 Carregando dados do Google Sheet..."):
    df_ml, df_wf, error = load_sheet(st.session_state["sheet_url_input"])

if error:
    st.error(f"❌ {error}")
    st.info(
        "Verifique:\n"
        "- A URL/ID do Sheet está correta\n"
        "- O Sheet tem as folhas 'modelos_loras' e 'workflows'\n"
        "- A Service Account tem acesso (ou configure nos Secrets)\n"
    )
    st.stop()

# =========================
# VALIDAR COLUNAS
# =========================
df_ml = ensure_cols(df_ml, [
    "tipo", "nome", "base_model", "estilo_utilizacao", "dimensions_recomendadas",
    "strength_tipica", "notas", "fonte_url", "caminho_local", "ultima_atualizacao"
])

df_wf = ensure_cols(df_wf, [
    "nome", "objetivo", "nodes_principais", "ksampler_recomendado", "dependencias",
    "tempo_medio", "qualidade_esperada", "link", "versao", "ultima_atualizacao"
])

# =========================
# TABS
# =========================
tab1, tab2, tab3 = st.tabs(["📦 Modelos/LoRAs", "⚡ Workflows", "ℹ️ Sobre"])

with tab1:
    st.subheader("📦 Modelos e LoRAs")

    filtered_ml = filter_modelos_loras(df_ml, filtro_tipo, filtro_base, filtro_estilo, filtro_search_ml)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"✅ {len(filtered_ml)} de {len(df_ml)} itens encontrados")
    with col2:
        if len(filtered_ml) > 0:
            csv = filtered_ml.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Exportar CSV", csv, "modelos_loras_filtrados.csv", "text/csv", use_container_width=True)

    if len(filtered_ml) > 0:
        st.dataframe(
            filtered_ml[["tipo", "nome", "base_model", "estilo_utilizacao", "dimensions_recomendadas", "strength_tipica"]],
            use_container_width=True,
            height=350
        )

        st.markdown("---")
        st.subheader("🔎 Detalhes")

        nomes = filtered_ml["nome"].tolist()
        sel = st.selectbox("Selecione um item:", nomes, key="ml_sel")
        row = filtered_ml[filtered_ml["nome"] == sel].iloc[0].to_dict()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tipo", row.get("tipo", "—"))
            st.metric("Base Model", row.get("base_model", "—"))
            st.metric("Estilo/Utilização", row.get("estilo_utilizacao", "—"))
        with col2:
            st.metric("Dimensions", row.get("dimensions_recomendadas", "—"))
            st.metric("Strength típica", row.get("strength_tipica", "—"))
            st.metric("Última atualização", row.get("ultima_atualizacao", "—"))
        with col3:
            caminho = row.get("caminho_local", "")
            if caminho:
                st.text("Caminho local:")
                st.code(caminho)
            fonte = row.get("fonte_url", "")
            if fonte and fonte.startswith("http"):
                st.markdown(f"🔗 [Abrir fonte/URL]({fonte})")

        notas = row.get("notas", "")
        if notas:
            st.markdown("**📝 Notas:**")
            st.info(notas)
    else:
        st.warning("⚠️ Nenhum item encontrado com os filtros atuais")

with tab2:
    st.subheader("⚡ Workflows")

    filtered_wf = filter_workflows(df_wf, filtro_objetivo, filtro_search_wf)

    col1, col2 = st.columns([3, 1])
    with col1:
        st.caption(f"✅ {len(filtered_wf)} de {len(df_wf)} workflows encontrados")
    with col2:
        if len(filtered_wf) > 0:
            csv = filtered_wf.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Exportar CSV", csv, "workflows_filtrados.csv", "text/csv", use_container_width=True)

    if len(filtered_wf) > 0:
        st.dataframe(
            filtered_wf[["nome", "objetivo", "tempo_medio", "qualidade_esperada", "versao"]],
            use_container_width=True,
            height=350
        )

        st.markdown("---")
        st.subheader("🔎 Detalhes do Workflow")

        nomes = filtered_wf["nome"].tolist()
        sel = st.selectbox("Selecione um workflow:", nomes, key="wf_sel")
        row = filtered_wf[filtered_wf["nome"] == sel].iloc[0].to_dict()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Objetivo", row.get("objetivo", "—"))
            st.metric("Versão", row.get("versao", "—"))
            st.metric("Última atualização", row.get("ultima_atualizacao", "—"))
        with col2:
            st.metric("Tempo médio", row.get("tempo_medio", "—"))
            st.metric("Qualidade esperada", row.get("qualidade_esperada", "—"))
        with col3:
            link = row.get("link", "")
            if link:
                st.text("Link/Caminho:")
                st.code(link)

        deps = row.get("dependencias", "")
        if deps:
            st.markdown("**📦 Dependências:**")
            st.info(deps)

        nodes = row.get("nodes_principais", "")
        if nodes:
            st.markdown("**🛠️ Nodes principais:**")
            st.code(nodes)

        ks = row.get("ksampler_recomendado", "")
        if ks:
            st.markdown("**⚙️ KSampler recomendado:**")
            try:
                st.json(json.loads(ks))
            except Exception:
                st.code(ks, language="json")
    else:
        st.warning("⚠️ Nenhum workflow encontrado com os filtros atuais")

with tab3:
    st.subheader("ℹ️ Sobre este Catálogo")
    st.markdown("""
### 🎯 Objetivo
Organizar e facilitar o acesso a:
- Modelos e LoRAs para ComfyUI
- Workflows testados e otimizados
- Recomendações de parâmetros

### 🧩 Como usar
1. Navegue pelas tabs "Modelos/LoRAs" e "Workflows"
2. Use os filtros na barra lateral
3. Selecione um item para ver detalhes
4. Exporte resultados em CSV

### 🔄 Atualização dos dados
Carregados diretamente do Google Sheet. Cache de 5 minutos.
Use o botão "🔄 Recarregar dados" para forçar atualização.

### 👤 Autor
**Sérgio Duarte**  
🌐 sergioduarte.pt  
📧 fotografia@sergioduarte.pt
""")

st.markdown("---")
st.caption("🎨 Catálogo ComfyUI | Desenvolvido com Streamlit | © 2025 Sérgio Duarte")