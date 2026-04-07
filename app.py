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

# 2. FUNÇÃO PARA EXECUTAR COMANDOS NO BANCO (Abre e fecha a cada uso para não travar)
def executar_db(sql, params=None, retorno=True):
    try:
        config = {
            'host': st.secrets["DB_HOST"],
            'user': st.secrets["DB_USER"],
            'password': st.secrets["DB_PASSWORD"],
            'database': st.secrets["DB_NAME"],
            'port': int(st.secrets["DB_PORT"]),
            'use_pure': True,
            'ssl_disabled': False,  # TiDB EXIGE SSL ATIVADO
            'connect_timeout': 15
        }
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        
        if retorno:
            resultado = cursor.fetchall()
            cursor.close()
            conn.close()
            return resultado
        else:
            conn.commit()
            cursor.close()
            conn.close()
            return True
    except Exception as e:
        st.error(f"Erro no Banco de Dados: {e}")
        return None

# 3. CONTROLE DE SESSÃO / LOGIN
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Login - Sistema 5W2H")
    with st.form("login_form"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            check = executar_db("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (usuario, senha))
            if check:
                st.session_state['logado'] = True
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos.")
    st.stop()

# 4. DASHBOARD (APÓS LOGIN)
st.sidebar.title("Opções")
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

st.title("📋 Plano de Ação Estratégico 5W2H")

# Buscar Usuários para o selectbox
res_usuarios = executar_db("SELECT id_usuario, nome FROM Usuarios")
dict_users = {u['nome']: u['id_usuario'] for u in res_usuarios} if res_usuarios else {}

# --- FORMULÁRIO DE CADASTRO ---
with st.expander("➕ Adicionar Nova Ação"):
    if not dict_users:
        st.warning("⚠️ Cadastre um usuário na tabela 'Usuarios' no painel do TiDB primeiro!")
    else:
        with st.form("add_acao", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                what = st.text_input("O que (Ação)?")
                why = st.text_area("Por que?")
            with col2:
                who = st.selectbox("Quem?", list(dict_users.keys()))
                when = st.date_input("Prazo", datetime.now())
                status = st.selectbox("Status", ["Pendente", "Em Andamento", "Concluído", "Atrasado"])
            
            if st.form_submit_button("Salvar"):
                sql_ins = "INSERT INTO Acoes (descricao_acao, porque, id_responsavel, prazo, status) VALUES (%s, %s, %s, %s, %s)"
                executar_db(sql_ins, (what, why, dict_users[who], when, status), retorno=False)
                st.success("Ação cadastrada!")
                st.rerun()

# --- LISTAGEM E EXCLUSÃO ---
st.subheader("Lista de Ações")
dados_acoes = executar_db("""
    SELECT A.id_acao, A.descricao_acao, U.nome as quem, A.prazo, A.status 
    FROM Acoes A 
    JOIN Usuarios U ON A.id_responsavel = U.id_usuario
    ORDER BY A.prazo ASC
""")

if dados_acoes:
    for acao in dados_acoes:
        with st.container():
            c_txt, c_btn = st.columns([0.85, 0.15])
            c_txt.write(f"**{acao['descricao_acao']}** | {acao['quem']} | {acao['prazo']} | `{acao['status']}`")
            if c_btn.button("🗑️", key=f"del_{acao['id_acao']}"):
                executar_db("DELETE FROM Acoes WHERE id_acao=%s", (acao['id_acao'],), retorno=False)
                st.rerun()
            st.divider()

    # --- BOTÃO PDF ---
    def gerar_pdf(lista):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
        elements = [Paragraph("RELATÓRIO 5W2H", getSampleStyleSheet()['Title']), Spacer(1,12)]
        tab_data = [["Ação", "Quem", "Prazo", "Status"]]
        for r in lista:
            tab_data.append([r['descricao_acao'], r['quem'], str(r['prazo']), r['status']])
        t = Table(tab_data)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.navy),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),1,colors.grey)]))
        elements.append(t)
        doc.build(elements)
        return buf.getvalue()

    st.download_button("📥 Baixar Relatório PDF", gerar_pdf(dados_acoes), "plano_5w2h.pdf", "application/pdf")
else:
    st.info("Nenhuma ação cadastrada.")
