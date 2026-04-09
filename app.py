import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import io

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Sistema 5W2H Profissional", layout="wide")

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
if 'nivel' not in st.session_state: st.session_state['nivel'] = 'Comum'

if not st.session_state['logado']:
    st.title("🔐 Login")
    u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
    if st.button("Entrar"):
        res = executar_db("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s))
        if res:
            st.session_state['logado'] = True
            st.session_state['nivel'] = res[0].get('nivel', 'Comum')
            st.rerun()
    st.stop()

# --- CARREGAR DADOS ---
@st.cache_data(ttl=30)
def buscar_dados():
    return executar_db("SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario")

dados_db = buscar_dados()
df_total = pd.DataFrame(dados_db) if dados_db else pd.DataFrame()

# --- BARRA LATERAL ---
st.sidebar.title("📊 Painel de Controle")
if st.session_state['nivel'] == 'Admin':
    st.sidebar.success("Modo Administrador")
    if st.sidebar.checkbox("Gerenciar Acessos"):
        st.subheader("👥 Novo Usuário/Acesso")
        with st.form("form_usuarios"):
            novo_u = st.text_input("Novo Usuário")
            novo_s = st.text_input("Senha", type="password")
            tipo = st.selectbox("Nível", ["Comum", "Admin"])
            if st.form_submit_button("Cadastrar"):
                executar_db("INSERT INTO Credenciais (usuario, senha, nivel) VALUES (%s,%s,%s)", (novo_u, novo_s, tipo), retorno=False)
                # Também cria na tabela de responsáveis para o 5W2H
                executar_db("INSERT INTO Usuarios (nome) VALUES (%s)", (novo_u,), retorno=False)
                st.success("Usuário criado!")

if st.sidebar.button("🚪 Sair"):
    st.session_state['logado'] = False
    st.rerun()

# --- DASHBOARD ---
st.title("🚀 Gestão Estratégica 5W2H")

if not df_total.empty:
    hoje = date.today()
    df_total['prazo_dt'] = pd.to_datetime(df_total['prazo']).dt.date
    # Filtro de Prioridade
    f_prio = st.sidebar.multiselect("Prioridade:", ["Alta", "Média", "Baixa"], default=["Alta", "Média", "Baixa"])
    df = df_total[df_total['prioridade'].isin(f_prio)]
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Ações", len(df))
    c2.metric("Investimento", f"R$ {pd.to_numeric(df['quanto_custa']).sum():,.2f}")
    atrasos = len(df[(df['prazo_dt'] < hoje) & (df['status'] != 'Concluído')])
    c3.metric("🚨 Atrasos", atrasos)

# --- FORMULÁRIO 5W2H ---
with st.expander("➕ Nova Ação"):
    res_u = executar_db("SELECT id_usuario, nome FROM Usuarios")
    dict_u = {user['nome']: user['id_usuario'] for user in res_u} if res_u else {}
    with st.form("form_5w2h"):
        col1, col2 = st.columns(2)
        with col1:
            what = st.text_input("O que fazer?")
            why = st.text_area("Por que?")
            prio = st.select_slider("Prioridade", options=["Baixa", "Média", "Alta"], value="Média")
        with col2:
            who = st.selectbox("Responsável", list(dict_u.keys()))
            # FORMATO DE DATA BR NO INPUT
            when = st.date_input("Prazo", format="DD/MM/YYYY")
            cost = st.number_input("Custo R$", min_value=0.0)
            status = st.selectbox("Status", ["Em análise", "Em andamento", "Concluído"])
            obs = st.text_input("Observações")
        
        if st.form_submit_button("Salvar"):
            sql = "INSERT INTO Acoes (descricao_acao, porque, id_responsavel, prazo, quanto_custa, status, prioridade, observacoes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
            executar_db(sql, (what, why, dict_u[who], when, cost, status, prio, obs), retorno=False)
            st.cache_data.clear()
            st.rerun()

# --- LISTAGEM ---
st.subheader("📋 Planilha de Controle")
if not df.empty:
    for _, row in df.iterrows():
        # DATA FORMATADA EM PORTUGUÊS (dd/mm/aaaa)
        data_br = row['prazo_dt'].strftime('%d/%m/%Y')
        atraso = row['prazo_dt'] < hoje and row['status'] != 'Concluído'
        cor = "#dc3545" if atraso else ("#28a745" if row['status'] == "Concluído" else "#ffc107")
        
        with st.container():
            c1, c2, c3 = st.columns([0.02, 0.88, 0.1])
            c1.markdown(f"<div style='background-color:{cor}; height:75px; width:8px; border-radius:5px'></div>", unsafe_allow_html=True)
            with c2:
                st.write(f"**{row['descricao_acao']}** | Resp: {row['quem']} | **Prazo: {data_br}**")
                if row['observacoes']: st.caption(f"💬 {row['observacoes']}")
                st.caption(f"Status: {row['status']} | Prioridade: {row['prioridade']} | R$ {row['quanto_custa']:,.2f} {'🔴 ATRASO' if atraso else ''}")
            with c3:
                if st.button("🗑️", key=f"d_{row['id_acao']}"):
                    executar_db("DELETE FROM Acoes WHERE id_acao=%s", (row['id_acao'],), retorno=False)
                    st.cache_data.clear()
                    st.rerun()
            st.divider()
