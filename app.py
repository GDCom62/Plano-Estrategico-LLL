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

# Função para conectar ao TiDB usando os Secrets do Streamlit
def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["DB_HOST"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_NAME"],
        port=int(st.secrets["DB_PORT"]),
        ssl_disabled=False  # TiDB exige SSL para conexões externas
    )

# --- CONTROLE DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔑 Login - Sistema 5W2H")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    
    if st.button("Entrar"):
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (usuario, senha))
            user_data = cursor.fetchone()
            if user_data:
                st.session_state['logado'] = True
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")
            conn.close()
        except Exception as e:
            st.error(f"Erro ao conectar no banco: {e}")
    st.stop()

# --- LOGOUT ---
if st.sidebar.button("Sair / Logout"):
    st.session_state['logado'] = False
    st.rerun()

# --- DASHBOARD PRINCIPAL ---
st.title("📋 Plano de Ação Estratégico 5W2H")

try:
    conn = get_db_connection()

    # Buscar dados para a tabela
    query = "SELECT A.*, U.nome as responsavel_nome FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario ORDER BY A.prazo ASC"
    df = pd.read_sql(query, conn)

    # Buscar usuários para o formulário
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Usuarios")
    usuarios = cursor.fetchall()
    lista_usuarios = {u['nome']: u['id_usuario'] for u in usuarios}

    # --- FORMULÁRIO DE ADIÇÃO ---
    with st.expander("➕ Adicionar Nova Ação"):
        with st.form("form_acao"):
            col1, col2 = st.columns(2)
            with col1:
                descricao = st.text_input("Ação (What)")
                porque = st.text_area("Por que? (Why)")
                onde = st.text_input("Onde? (Where)")
            with col2:
                resp_nome = st.selectbox("Quem? (Who)", list(lista_usuarios.keys()))
                prazo = st.date_input("Prazo (When)", datetime.now())
                como = st.text_area("Como? (How)")
                quando_det = st.text_input("Detalhe do Quando")
                status = st.selectbox("Status", ["Pendente", "Em Andamento", "Concluído", "Atrasado"])
            
            if st.form_submit_button("Salvar Ação"):
                cursor.execute("""
                    INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, quando_detalhe, status) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (descricao, porque, onde, lista_usuarios[resp_nome], prazo, como, quando_det, status))
                conn.commit()
                st.success("Salvo com sucesso!")
                st.rerun()

    # --- EXIBIÇÃO ---
    st.subheader("Ações Cadastradas")
    st.dataframe(df, use_container_width=True)

    # --- FUNÇÃO GERAR PDF ---
    def gerar_pdf(dados):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        elements = []
        styles = getSampleStyleSheet()
        elements.append(Paragraph("PLANO DE AÇÃO ESTRATÉGICO 5W2H", styles['Title']))
        
        table_data = [["Ação", "Quem", "Prazo", "Status", "Como"]]
        for _, row in dados.iterrows():
            table_data.append([row['descricao_acao'], row['responsavel_nome'], str(row['prazo']), row['status'], row['como']])
        
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.navy),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 8)
        ]))
        elements.append(t)
        doc.build(elements)
        return buffer.getvalue()

    st.download_button("📥 Baixar Relatório PDF", data=gerar_pdf(df), file_name="Plano_5W2H.pdf", mime="application/pdf")
    
    conn.close()

except Exception as e:
    st.error(f"Ocorreu um erro: {e}")
