import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime
import io
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors

st.set_page_config(page_title="Sistema 5W2H", layout="wide")

# FUNÇÃO PARA CONECTAR E EXECUTAR (Abre e fecha na hora)
def run_query(query, params=None, is_select=True):
    try:
        conn = mysql.connector.connect(
            host=st.secrets["DB_HOST"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_NAME"],
            port=int(st.secrets["DB_PORT"]),
            use_pure=True,
            ssl_disabled=False # TiDB costuma exigir SSL True para nuvem
        )
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        if is_select:
            result = cursor.fetchall()
            conn.close()
            return result
        else:
            conn.commit()
            conn.close()
            return True
    except Exception as e:
        st.error(f"Erro no banco de dados: {e}")
        return None

# --- LOGIN ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Login - 5W2H")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        res = run_query("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s))
        if res:
            st.session_state['logado'] = True
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")
    st.stop()

# --- DASHBOARD ---
st.title("📋 Plano de Ação Estratégico 5W2H")
if st.sidebar.button("Logout"):
    st.session_state['logado'] = False
    st.rerun()

# BUSCAR USUÁRIOS E AÇÕES
usuarios = run_query("SELECT id_usuario, nome FROM Usuarios")
dict_usuarios = {u['nome']: u['id_usuario'] for u in usuarios} if usuarios else {}

with st.expander("➕ Nova Ação"):
    with st.form("form_add"):
        c1, c2 = st.columns(2)
        what = c1.text_input("O que?")
        who = c2.selectbox("Quem?", list(dict_usuarios.keys()))
        when = c2.date_input("Prazo")
        status = c2.selectbox("Status", ["Pendente", "Em Andamento", "Concluído"])
        if st.form_submit_button("Salvar"):
            run_query("INSERT INTO Acoes (descricao_acao, id_responsavel, prazo, status) VALUES (%s,%s,%s,%s)", 
                      (what, dict_usuarios[who], when, status), is_select=False)
            st.rerun()

# LISTAGEM E EXCLUSÃO
st.subheader("Ações Registradas")
acoes = run_query("SELECT A.id_acao, A.descricao_acao, U.nome as quem, A.prazo, A.status FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario")

if acoes:
    for a in acoes:
        col_txt, col_btn = st.columns([0.8, 0.2])
        col_txt.write(f"**{a['descricao_acao']}** | {a['quem']} | {a['prazo']} | {a['status']}")
        if col_btn.button("🗑️ Excluir", key=f"btn_{a['id_acao']}"):
            run_query("DELETE FROM Acoes WHERE id_acao = %s", (a['id_acao'],), is_select=False)
            st.rerun()
else:
    st.info("Nenhuma ação cadastrada.")
