import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime
import io
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Configuração da Página
st.set_page_config(page_title="Sistema 5W2H", layout="wide")

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1", # Se o MySQL estiver em outro PC, mude para o IP dele
        user="root",
        password="",
        database="sistema_gestao",
        port=3306
    )

# --- LOGIN SIMPLES ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("Login - Sistema 5W2H")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (usuario, senha))
        if cursor.fetchone():
            st.session_state['logado'] = True
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")
        conn.close()
    st.stop()

# --- LOGOUT ---
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

# --- DASHBOARD PRINCIPAL ---
st.title("📋 Plano de Ação Estratégico 5W2H")

conn = get_db_connection()

# Buscar dados para a tabela
query = "SELECT A.*, U.nome as responsavel_nome FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario ORDER BY A.prazo ASC"
df = pd.read_sql(query, conn)

# Buscar usuários para o formulário
cursor = conn.cursor(dictionary=True)
cursor.execute("SELECT * FROM Usuarios")
usuarios = cursor.fetchall()
lista_usuarios = {u['nome']: u['id_usuario'] for u in usuarios}

# --- FORMULÁRIO DE ADIÇÃO/EDIÇÃO ---
with st.expander("➕ Adicionar Nova Ação"):
    with st.form("form_acao"):
        col1, col2 = st.columns(2)
        descricao = col1.text_input("Ação (What)")
        porque = col1.text_area("Por que? (Why)")
        onde = col1.text_input("Onde? (Where)")
        
        resp_nome = col2.selectbox("Quem? (Who)", list(lista_usuarios.keys()))
        prazo = col2.date_input("Prazo (When)", datetime.now())
        como = col2.text_area("Como? (How)")
        quando_det = col2.text_input("Detalhe do Quando")
        status = col2.selectbox("Status", ["Pendente", "Em Andamento", "Concluído", "Atrasado"])
        
        if st.form_submit_button("Salvar Ação"):
            cursor.execute("""
                INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, quando_detalhe, status) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (descricao, porque, onde, lista_usuarios[resp_nome], prazo, como, quando_det, status))
            conn.commit()
            st.success("Salvo com sucesso!")
            st.rerun()

# --- EXIBIÇÃO ---
st.dataframe(df, use_container_width=True)

# --- BOTÃO PDF ---
def gerar_pdf(dados):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("PLANO DE AÇÃO ESTRATÉGICO 5W2H", styles['Title']))
    
    table_data = [["Ação", "Quem", "Prazo", "Status", "Como"]]
    for index, row in dados.iterrows():
        table_data.append([row['descricao_acao'], row['responsavel_nome'], str(row['prazo']), row['status'], row['como']])
    
    t = Table(table_data)
    t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.navy), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 0.5, colors.grey)]))
    elements.append(t)
    doc.build(elements)
    return buffer.getvalue()

st.download_button("📥 Baixar PDF", data=gerar_pdf(df), file_name="Plano_5W2H.pdf", mime="application/pdf")

conn.close()
