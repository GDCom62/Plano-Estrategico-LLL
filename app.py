import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime
import io
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Sistema 5W2H", layout="wide")

# 2. CONEXÃO COM CACHE (Evita travar o app abrindo várias conexões)
@st.cache_resource
def init_connection():
    return mysql.connector.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_NAME"],
        port=int(st.secrets["DB_PORT"]),
        use_pure=True,
        ssl_disabled=False,
        autocommit=True # Garante que as mudanças sejam salvas na hora
    )

# 3. CONTROLE DE LOGIN
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Login - 5W2H")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        conn = init_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s))
        if cursor.fetchone():
            st.session_state['logado'] = True
            st.rerun()
        else:
            st.error("Incorreto")
    st.stop()

# 4. DASHBOARD
st.title("📋 Plano de Ação Estratégico 5W2H")

conn = init_connection()
cursor = conn.cursor(dictionary=True)

# BUSCAR USUÁRIOS
cursor.execute("SELECT id_usuario, nome FROM Usuarios")
usuarios_db = cursor.fetchall()
dict_usuarios = {u['nome']: u['id_usuario'] for u in usuarios_db}

# --- FORMULÁRIO DE CADASTRO ---
with st.expander("➕ Nova Ação"):
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            what = st.text_input("O que (Ação)?")
            why = st.text_area("Por que?")
        with col2:
            who = st.selectbox("Quem?", list(dict_usuarios.keys()))
            when = st.date_input("Prazo")
            status = st.selectbox("Status", ["Pendente", "Em Andamento", "Concluído"])
        
        if st.form_submit_button("Salvar"):
            cursor.execute("INSERT INTO Acoes (descricao_acao, porque, id_responsavel, prazo, status) VALUES (%s,%s,%s,%s,%s)", 
                           (what, why, dict_usuarios[who], when, status))
            st.success("Salvo!")
            st.rerun()

# --- TABELA E EXCLUSÃO ---
st.subheader("Ações Registradas")
cursor.execute("SELECT A.id_acao, A.descricao_acao, U.nome as quem, A.prazo, A.status FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario")
dados = cursor.fetchall()

if dados:
    for item in dados:
        with st.container():
            col_txt, col_btn = st.columns([0.85, 0.15])
            with col_txt:
                # Exibe a linha formatada
                st.write(f"**{item['descricao_acao']}** | Resp: {item['quem']} | Prazo: {item['prazo']} | [{item['status']}]")
            with col_btn:
                # Botão de Excluir com ID Único
                if st.button("🗑️ Excluir", key=f"del_{item['id_acao']}"):
                    cursor.execute("DELETE FROM Acoes WHERE id_acao = %s", (item['id_acao'],))
                    st.toast(f"Ação {item['id_acao']} removida!")
                    st.rerun()
            st.divider()

    # --- PDF ---
    def gerar_pdf(lista):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
        elements = [Paragraph("RELATÓRIO 5W2H", getSampleStyleSheet()['Title'])]
        data = [["Ação", "Quem", "Prazo", "Status"]]
        for r in lista: data.append([r['descricao_acao'], r['quem'], str(r['prazo']), r['status']])
        t = Table(data); t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),1,colors.black)]))
        elements.append(t); doc.build(elements)
        return buf.getvalue()

    st.download_button("📥 PDF", gerar_pdf(dados), "plano.pdf", "application/pdf")
else:
    st.info("Nada cadastrado.")

if st.sidebar.button("Logout"):
    st.session_state['logado'] = False
    st.rerun()
