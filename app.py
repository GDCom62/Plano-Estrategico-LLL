import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. CONFIGURAÇÃO E CACHE
st.set_page_config(page_title="Performance 5W2H", layout="wide")

@st.cache_data(ttl=600) # Mantém os dados em memória por 10 min para não travar
def carregar_dados():
    try:
        conn = pymysql.connect(
            host=st.secrets["DB_HOST"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_NAME"],
            port=int(st.secrets["DB_PORT"]),
            ssl={'ssl': {}},
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario")
            res = cursor.fetchall()
        conn.close()
        return pd.DataFrame(res)
    except:
        return pd.DataFrame()

# --- INTERFACE ---
st.title("📈 Dashboard de Produção Otimizado")

df = carregar_dados()

if not df.empty:
    # FILTROS RÁPIDOS (Sidebar)
    st.sidebar.header("Filtros")
    if st.sidebar.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

    # BLOCO DE GRÁFICOS (Renderização Isolada)
    c1, c2 = st.columns(2)
    
    with c1:
        # Usando render_mode="svg" para ser mais leve no navegador
        fig_pie = px.pie(df, names='status', hole=0.4, title="Status Geral",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True, theme="streamlit")

    with c2:
        df['ano'] = pd.to_datetime(df['prazo']).dt.year
        df_ano = df.groupby(['ano', 'status']).size().reset_index(name='total')
        fig_bar = px.bar(df_ano, x='ano', y='total', color='status', barmode='group', title="Performance Anual")
        st.plotly_chart(fig_bar, use_container_width=True)

    # LISTAGEM SIMPLIFICADA (Evita travar o scroll)
    st.subheader("📋 Lista de Itens")
    for _, row in df.head(20).iterrows(): # Limitamos a 20 para performance
        cor = "#28a745" if row['status'] == "Concluído" else "#ffc107"
        st.markdown(f"""
            <div style="border-left: 5px solid {cor}; padding-left: 15px; margin-bottom: 10px;">
                <strong>{row['descricao_acao']}</strong> - {row['quem']}<br>
                <small>Status: {row['status']} | Prazo: {row['prazo']}</small>
            </div>
        """, unsafe_allow_html=True)
else:
    st.info("Aguardando dados...")
