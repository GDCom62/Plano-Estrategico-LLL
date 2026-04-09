import streamlit as st
import pymysql
import pandas as pd
from datetime import datetime
import io
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="Sistema 5W2H Pro - Filtros", layout="wide")

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

# --- LOGIN ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Login - Sistema 5W2H")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        res = executar_db("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s))
        if res:
            st.session_state['logado'] = True
            st.rerun()
        else:
            st.error("Dados inválidos.")
    st.stop()

# --- ESTADO DE EDIÇÃO ---
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.title("🔍 Filtros de Busca")

# Status para filtrar
status_filtro = st.sidebar.multiselect(
    "Filtrar por Status:",
    ["Em análise", "Em andamento", "Concluído", "Atrasado"],
    default=["Em análise", "Em andamento", "Concluído", "Atrasado"]
)

# Buscar Usuários para o filtro e formulário
res_users = executar_db("SELECT id_usuario, nome FROM Usuarios")
dict_u = {user['nome']: user['id_usuario'] for user in res_users} if res_users else {}

user_filtro = st.sidebar.selectbox("Filtrar por Responsável:", ["Todos"] + list(dict_u.keys()))

if st.sidebar.button("Limpar Filtros"):
    st.rerun()

st.sidebar.divider()
if st.sidebar.button("🚪 Sair"):
    st.session_state['logado'] = False
    st.rerun()

# --- DASHBOARD ---
st.title("🚀 Plano de Ação Estratégico 5W2H")

# Se estiver em modo edição, buscar os dados
dados_edit = None
if st.session_state.edit_id:
    res = executar_db("SELECT * FROM Acoes WHERE id_acao=%s", (st.session_state.edit_id,))
    if res: dados_edit = res[0]

# --- FORMULÁRIO ---
with st.expander("📝 Cadastro / Edição", expanded=(st.session_state.edit_id is not None)):
    with st.form("form_5w2h", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            what = st.text_input("What (O que?)", value=dados_edit['descricao_acao'] if dados_edit else "")
            why = st.text_area("Why (Por que?)", value=dados_edit['porque'] if dados_edit else "")
            where = st.text_input("Where (Onde?)", value=dados_edit['onde'] if dados_edit else "")
        with c2:
            who = st.selectbox("Who (Quem?)", list(dict_u.keys()), index=list(dict_u.values()).index(dados_edit['id_responsavel']) if dados_edit else 0)
            when = st.date_input("When (Quando?)", dados_edit['prazo'] if dados_edit else datetime.now())
            status_val = st.selectbox("Status", ["Em análise", "Em andamento", "Concluído", "Atrasado"], index=["Em análise", "Em mandamento", "Concluído", "Atrasado"].index(dados_edit['status']) if dados_edit else 0)
        
        if st.form_submit_button("💾 Salvar"):
            if st.session_state.edit_id:
                executar_db("UPDATE Acoes SET descricao_acao=%s, porque=%s, onde=%s, id_responsavel=%s, prazo=%s, status=%s WHERE id_acao=%s", 
                           (what, why, where, dict_u[who], when, status_val, st.session_state.edit_id), retorno=False)
                st.session_state.edit_id = None
            else:
                executar_db("INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, status) VALUES (%s,%s,%s,%s,%s,%s)", 
                           (what, why, where, dict_u[who], when, status_val), retorno=False)
            st.rerun()

# --- LISTAGEM COM FILTRO ---
st.subheader("📋 Ações Filtradas")

# Construção da Query Dinâmica
query = "SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario WHERE 1=1"
params = []

if status_filtro:
    query += f" AND A.status IN ({','.join(['%s']*len(status_filtro))})"
    params.extend(status_filtro)

if user_filtro != "Todos":
    query += " AND U.nome = %s"
    params.append(user_filtro)

acoes = executar_db(query, tuple(params))

if acoes:
    for a in acoes:
        with st.container():
            col_info, col_edit, col_del = st.columns([0.7, 0.15, 0.15])
            with col_info:
                st.markdown(f"**{a['descricao_acao']}** | Resp: `{a['quem']}` | Status: **{a['status']}**")
                st.caption(f"Prazo: {a['prazo']} | Por que: {a['porque'][:50]}...")
            with col_edit:
                if st.button("✏️", key=f"ed_{a['id_acao']}"):
                    st.session_state.edit_id = a['id_acao']
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"dl_{a['id_acao']}"):
                    executar_db("DELETE FROM Acoes WHERE id_acao=%s", (a['id_acao'],), retorno=False)
                    st.rerun()
            st.divider()
else:
    st.info("Nenhuma ação encontrada para os filtros selecionados.")
