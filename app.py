
import streamlit as st
import sqlite3
import pandas as pd
import textwrap

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Jurimetria CC-RJ",
    page_icon="⚖️",
    layout="wide"
)

# --- CONEXÃO COM O BANCO DE DADOS ---
# O Streamlit no Hugging Face vai procurar o arquivo na raiz do repositório
DB_PATH = "jurisprudencia_fts.db"
DB_PATH_METADADOS = "jurisprudencia.db" # Precisamos recriar este

@st.cache_resource
def get_connection():
    """Cria e gerencia a conexão com o banco de dados de busca."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_data
def get_filter_options(_conn_meta):
    """Busca as opções únicas de ano e câmara para os filtros."""
    try:
        df_anos = pd.read_sql_query("SELECT DISTINCT ano FROM metadados ORDER BY ano DESC", _conn_meta)
        anos = df_anos['ano'].dropna().astype(int).tolist()
        
        df_camaras = pd.read_sql_query("SELECT DISTINCT camara FROM metadados ORDER BY camara", _conn_meta)
        camaras = df_camaras['camara'].dropna().tolist()
    except Exception as e:
        st.error(f"Não foi possível carregar os filtros. O banco de dados de metadados pode estar faltando. Erro: {e}")
        return [], []
    
    return anos, camaras

@st.cache_data
def search_jurisprudencia(_conn, query, anos_selecionados, camaras_selecionadas):
    """Executa a busca no banco de dados FTS com os filtros aplicados."""
    
    # Monta a query base com a função snippet
    # Nota: A junção (JOIN) com metadados pode ser lenta.
    # Uma abordagem futura seria desnormalizar os dados e colocar ano/camara na tabela FTS.
    sql_query = """
    SELECT
        fts.nome_arquivo,
        fts.ano,
        fts.camara,
        fts.acordao,
        fts.processo,
        snippet(jurisprudencia_fts, 5, '<b>', '</b>', '...', 25) as snippet,
        fts.texto_completo
    FROM jurisprudencia_fts fts
    WHERE fts.texto_completo MATCH ?
    """
    
    params = [query]
    
    if anos_selecionados:
        sql_query += f" AND fts.ano IN ({','.join(['?']*len(anos_selecionados))})"
        params.extend(anos_selecionados)
        
    if camaras_selecionadas:
        sql_query += f" AND fts.camara IN ({','.join(['?']*len(camaras_selecionadas))})"
        params.extend(camaras_selecionadas)
        
    sql_query += " ORDER BY fts.ano DESC, fts.acordao DESC LIMIT 200;"

    try:
        df = pd.read_sql_query(sql_query, _conn, params=params)
    except Exception as e:
        st.error(f"Ocorreu um erro na busca. A estrutura da tabela 'jurisprudencia_fts' pode ter mudado. Erro: {e}")
        return pd.DataFrame()
        
    return df

# --- INTERFACE DO USUÁRIO (UI) ---

st.image("https://portal.fazenda.rj.gov.br/wp-content/uploads/2023/11/logo-fazenda-white-new.png", width=300)
st.title("Ferramenta de Busca e Jurimetria")
st.markdown("Base de dados do Conselho de Contribuintes do Estado do Rio de Janeiro")

# Conexões
conn = get_connection()
# Para os filtros, ainda precisamos do banco de dados original. 
# Precisamos garantir que ele seja enviado junto para o deploy.
# Por enquanto, vamos desabilitar os filtros para simplificar.
# conn_meta = get_connection_meta()
# anos_options, camaras_options = get_filter_options(conn_meta)

st.sidebar.header("Filtros da Pesquisa")
# Filtros desabilitados temporariamente para simplificar o deploy inicial
st.sidebar.info("Filtros de ano e câmara serão habilitados em uma versão futura.")
# anos_selecionados = st.sidebar.multiselect("Selecione o(s) Ano(s)", options=anos_options, default=anos_options)
# camaras_selecionadas = st.sidebar.multiselect("Selecione a(s) Câmara(s)", options=camaras_options, default=camaras_options)
anos_selecionados = []
camaras_selecionadas = []


search_query = st.text_input("Digite os termos da sua pesquisa", placeholder="Ex: cassação inscrição estadual")

if search_query:
    st.markdown("---")
    
    # Adiciona wildcards (*) para busca mais flexível
    query_formatada = ' '.join([f'"{term}"*' for term in search_query.split()])

    results_df = search_jurisprudencia(conn, query_formatada, anos_selecionados, camaras_selecionadas)
    
    st.subheader(f"Resultados da busca: {len(results_df)} acórdãos encontrados")

    if not results_df.empty:
        for index, row in results_df.iterrows():
            st.markdown(f"##### 📄 **{row['nome_arquivo']}**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"**Ano:** {row.get('ano', 'N/A')}")
            with col2:
                st.warning(f"**Acórdão:** {row.get('acordao', 'N/A')}")
            with col3:
                st.error(f"**Processo:** {row.get('processo', 'N/A')}")
            
            st.markdown(f"**Contexto:** ...{row['snippet']}...", unsafe_allow_html=True)
            
            with st.expander("Ver texto completo do acórdão"):
                wrapped_text = textwrap.fill(row['texto_completo'], width=120)
                st.text(wrapped_text)
            
            st.markdown("---")
    else:
        st.warning("Nenhum resultado encontrado com os filtros e termos de busca selecionados.")
else:
    st.info("Digite um termo de busca e pressione Enter para ver os resultados.")
