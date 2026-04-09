import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

st.set_page_config(page_title="Dashboard 5W2H Performance", layout="wide")

# FUNÇÃO DE CONEXÃO
def executar_db(sql, params=None, retorno=True):
    try:
        conn = pymysql.connect(
            host=st.secrets["DB_HOST"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_NAME"],
            port=int(st.secrets["DB_PORT"]),
            ssl={'ssl': {}},
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            if retorno:
                resultado = cursor.fetchall()
                conn.close()
                return resultado
            else:
                conn.commit()
                conn.close()
                return True
    except Exception as e:
        st.error(f"Erro no banco: {e}")
        return None

# --- LOGIN (SIMPLIFICADO PARA O EXEMPLO) ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']:
    st.title("🔐 Login")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if executar_db("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s)):
            st.session_state['logado'] = True
            st.rerun()
    st.stop()

# --- BARRA LATERAL ---
st.sidebar.title("📊 Gestão de Performance")
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

# --- CARREGAR DADOS ---
acoes_raw = executar_db("SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario")
df = pd.DataFrame(acoes_raw) if acoes_raw else pd.DataFrame()

if not df.empty:
    df['prazo'] = pd.to_datetime(df['prazo'])
    df['ano'] = df['prazo'].dt.year

    # --- INDICADORES NO TOPO ---
    st.title("📈 Performance de Produção 5W2H")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Ações", len(df))
    m2.metric("Concluídas", len(df[df['status'] == 'Concluído']))
    m3.metric("Em Andamento", len(df[df['status'] == 'Em andamento']))
    m4.metric("Em Análise", len(df[df['status'] == 'Em análise']))

    st.divider()

    # --- GRÁFICOS ---
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Distribuição por Status")
        fig_pizza = px.pie(df, names='status', color='status',
                           color_discrete_map={'Concluído':'#28a745', 'Em andamento':'#ffc107', 'Em análise':'#17a2b8', 'Atrasado':'#dc3545'})
        st.plotly_chart(fig_pizza, use_container_width=True)

    with c2:
        st.subheader("Performance Ano Atual vs Anterior")
        # Comparativo de conclusão por ano
        df_ano = df.groupby(['ano', 'status']).size().reset_index(name='qtd')
        fig_bar = px.bar(df_ano, x='ano', y='qtd', color='status', barmode='group',
                         title="Comparativo de Produção por Ano")
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- LISTA COM CORES ---
    st.subheader("📋 Detalhamento das Ações")
    
    # Filtro rápido de status na tela
    filtro = st.multiselect("Filtrar visualização:", df['status'].unique(), default=df['status'].unique())
    df_filtrado = df[df['status'].isin(filtro)]

    for _, row in df_filtrado.iterrows():
        # Lógica de cores para o status
        cor = "#28a745" if row['status'] == "Concluído" else "#ffc107" if row['status'] == "Em andamento" else "#17a2b8"
        
        with st.container():
            col_cor, col_info, col_btns = st.columns([0.05, 0.75, 0.2])
            with col_cor:
                st.markdown(f"<div style='height: 50px; width: 10px; background-color: {cor}; border-radius: 5px;'></div>", unsafe_allow_html=True)
            with col_info:
                st.write(f"**{row['descricao_acao']}** ({row['quem']})")
                st.caption(f"Prazo: {row['prazo'].strftime('%d/%m/%Y')} | Status: {row['status']}")
            with col_btns:
                if st.button("✏️", key=f"ed_{row['id_acao']}"):
                    st.session_state.edit_id = row['id_acao']
                    st.rerun()
            st.divider()
else:
    st.info("Nenhuma ação cadastrada para gerar indicadores.")
