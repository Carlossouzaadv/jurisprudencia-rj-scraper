
import streamlit as st
import sqlite3
import pandas as pd
import textwrap

st.set_page_config(page_title="Jurimetria CC-RJ", page_icon="⚖️", layout="wide")

DB_PATH = "jurisprudencia_fts.db"

@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

conn = get_connection()

@st.cache_data
def search_jurisprudencia(_conn, query):
    # AQUI ESTÁ A MUDANÇA: Usamos 'acordaos' em vez de 'jurisprudencia_fts'
    sql_query = """
    SELECT
        nome_arquivo,
        ano,
        camara,
        acordao,
        processo,
        snippet(acordaos, 5, '<b>', '</b>', '...', 25) as snippet,
        texto_completo
    FROM acordaos
    WHERE acordaos MATCH ?
    ORDER BY ano DESC, acordao DESC
    LIMIT 200;
    """
    params = [query]
    df = pd.read_sql_query(sql_query, _conn, params=params)
    return df

st.image("https://portal.fazenda.rj.gov.br/wp-content/uploads/2023/11/logo-fazenda-white-new.png", width=300)
st.title("Ferramenta de Busca e Jurimetria")
st.markdown("Base de dados do Conselho de Contribuintes do Estado do Rio de Janeiro")

st.sidebar.header("Filtros da Pesquisa")
st.sidebar.info("Filtros de ano e câmara serão habilitados em uma versão futura.")

search_query = st.text_input("Digite os termos da sua pesquisa", placeholder="Ex: cassação inscrição estadual")

if search_query:
    st.markdown("---")
    query_formatada = ' '.join([f'"{term}"*' for term in search_query.split()])
    results_df = search_jurisprudencia(conn, query_formatada)

    st.subheader(f"Resultados da busca: {len(results_df)} acórdãos encontrados")

    if not results_df.empty:
        for index, row in results_df.iterrows():
            st.markdown(f"##### 📄 **{row['nome_arquivo']}**")
            col1, col2, col3 = st.columns(3)
            with col1: st.info(f"**Ano:** {row.get('ano', 'N/A')}")
            with col2: st.warning(f"**Acórdão:** {row.get('acordao', 'N/A')}")
            with col3: st.error(f"**Processo:** {row.get('processo', 'N/A')}")
            st.markdown(f"**Contexto:** ...{row['snippet']}...", unsafe_allow_html=True)
            with st.expander("Ver texto completo do acórdão"):
                st.text(textwrap.fill(row['texto_completo'], width=120))
            st.markdown("---")
    else:
        st.warning("Nenhum resultado encontrado.")
else:
    st.info("Digite um termo de busca e pressione Enter para ver os resultados.")
