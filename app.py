import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Performance, Custos & Prazos 5W2H", layout="wide")

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

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']:
    st.title("🔐 Login")
    u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if executar_db("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s)):
            st.session_state['logado'] = True
            st.rerun()
    st.stop()

# --- CARREGAR DADOS ---
@st.cache_data(ttl=60)
def buscar_dados():
    return executar_db("SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario")

dados = buscar_dados()
df = pd.DataFrame(dados) if dados else pd.DataFrame()

# --- DASHBOARD ---
st.title("🚀 Dashboard Estratégico 5W2H")

if not df.empty:
    df['prazo'] = pd.to_datetime(df['prazo']).dt.date
    df['quanto_custa'] = pd.to_numeric(df['quanto_custa']).fillna(0)
    hoje = date.today()
    
    # Identificar Atrasados (Data < Hoje E Status != Concluído)
    atrasados_df = df[(df['prazo'] < hoje) & (df['status'] != 'Concluído')]
    qtd_atrasados = len(atrasados_df)

    # 1. INDICADORES NO TOPO
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Ações", len(df))
    m2.metric("Concluídas", len(df[df['status'] == 'Concluído']))
    m3.metric("Investimento Total", f"R$ {df['quanto_custa'].sum():,.2f}")
    # Alerta visual no card de atrasados
    m4.metric("🚨 Em Atraso", qtd_atrasados, delta=f"{qtd_atrasados} crítico(s)" if qtd_atrasados > 0 else None, delta_color="inverse")

    # 2. GRÁFICOS
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Situação das Ações")
        fig_pie = px.pie(df, names='status', hole=0.4, color='status',
                         color_discrete_map={'Concluído':'#28a745', 'Em andamento':'#ffc107', 'Em análise':'#17a2b8', 'Atrasado':'#dc3545'})
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        st.subheader("Investimento por Responsável")
        fig_cost = px.bar(df, x='quem', y='quanto_custa', color='status', barmode='group')
        st.plotly_chart(fig_cost, use_container_width=True)

# --- FORMULÁRIO ---
res_u = executar_db("SELECT id_usuario, nome FROM Usuarios")
dict_u = {user['nome']: user['id_usuario'] for user in res_u} if res_u else {}

with st.expander("➕ Nova Ação (Checklist 5W2H)"):
    with st.form("form_novo"):
        col1, col2 = st.columns(2)
        with col1:
            what = st.text_input("What (O que?)")
            why = st.text_area("Why (Por que?)")
            how_much = st.number_input("How Much (Custo R$)", min_value=0.0)
        with col2:
            who = st.selectbox("Who (Quem?)", list(dict_u.keys()))
            when = st.date_input("When (Prazo)")
            status = st.selectbox("Status", ["Em análise", "Em andamento", "Concluído"])
        
        if st.form_submit_button("Salvar"):
            executar_db("INSERT INTO Acoes (descricao_acao, porque, id_responsavel, prazo, quanto_custa, status) VALUES (%s,%s,%s,%s,%s,%s)", 
                       (what, why, dict_u[who], when, how_much, status), retorno=False)
            st.cache_data.clear()
            st.rerun()

# --- LISTA COM ALERTA DE ATRASO ---
st.subheader("📋 Detalhamento e Prazos")
if not df.empty:
    for _, row in df.iterrows():
        # Lógica de cor e alerta
        esta_atrasado = row['prazo'] < hoje and row['status'] != 'Concluído'
        cor_status = "#dc3545" if esta_atrasado else ("#28a745" if row['status'] == "Concluído" else "#ffc107")
        txt_atraso = "⚠️ **EM ATRASO**" if esta_atrasado else ""
        
        with st.container():
            c1, c2, c3 = st.columns([0.02, 0.78, 0.2])
            c1.markdown(f"<div style='background-color:{cor_status}; height:60px; width:8px; border-radius:5px'></div>", unsafe_allow_html=True)
            c2.write(f"**{row['descricao_acao']}** | {row['quem']} | R$ {row['quanto_custa']:,.2f} {txt_atraso}")
            c2.caption(f"Prazo: {row['prazo'].strftime('%d/%m/%Y')} | Status: `{row['status']}`")
            if c3.button("🗑️", key=f"del_{row['id_acao']}"):
                executar_db("DELETE FROM Acoes WHERE id_acao=%s", (row['id_acao'],), retorno=False)
                st.cache_data.clear()
                st.rerun()
            st.divider()

if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()
