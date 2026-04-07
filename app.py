import streamlit as st
import pymysql  # Trocamos o driver aqui
import pandas as pd
from datetime import datetime
import io
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors

st.set_page_config(page_title="Sistema 5W2H", layout="wide")

# FUNÇÃO DE CONEXÃO DIRETA E RÁPIDA
def executar_db(sql, params=None, retorno=True):
    try:
        conn = pymysql.connect(
            host=st.secrets["DB_HOST"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_NAME"],
            port=int(st.secrets["DB_PORT"]),
            ssl={'ssl': {}}, # Ativa SSL de forma simples para o TiDB
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10
        )
        with conn.cursor() as cursor:
            cursor.execute(sql, params or ())
            if retorno:
                resultado = cursor.fetchall()
                return resultado
            else:
                conn.commit()
                return True
        conn.close()
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

# --- LOGIN ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Login - 5W2H")
    with st.form("login"):
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            # O PyMySQL é mais rápido para esse check
            check = executar_db("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s))
            if check:
                st.session_state['logado'] = True
                st.rerun()
            else:
                st.error("Dados inválidos.")
    st.stop()

# --- DASHBOARD ---
st.title("📋 Plano de Ação Estratégico 5W2H")
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

# Buscar dados (Só executa se logado)
res_users = executar_db("SELECT id_usuario, nome FROM Usuarios")
dict_u = {user['nome']: user['id_usuario'] for user in res_users} if res_users else {}

with st.expander("➕ Nova Ação"):
    with st.form("add"):
        what = st.text_input("O que?")
        who = st.selectbox("Quem?", list(dict_u.keys()))
        when = st.date_input("Prazo")
        if st.form_submit_button("Salvar"):
            executar_db("INSERT INTO Acoes (descricao_acao, id_responsavel, prazo) VALUES (%s,%s,%s)", 
                       (what, dict_u[who], when), retorno=False)
            st.rerun()

# Listagem
acoes = executar_db("SELECT A.id_acao, A.descricao_acao, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario")
if acoes:
    for a in acoes:
        c1, c2 = st.columns([0.9, 0.1])
        c1.write(f"**{a['descricao_acao']}** - {a['quem']}")
        if c2.button("🗑️", key=f"del_{a['id_acao']}"):
            executar_db("DELETE FROM Acoes WHERE id_acao=%s", (a['id_acao'],), retorno=False)
            st.rerun()
