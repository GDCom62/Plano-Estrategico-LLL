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

# 2. FUNÇÃO DE CONEXÃO ROBUSTA (Para TiDB Cloud)
def get_db_connection():
    try:
        return mysql.connector.connect(
            host=st.secrets["DB_HOST"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_NAME"],
            port=int(st.secrets["DB_PORT"]),
            use_pure=True,        # Driver Python puro para evitar erros de biblioteca C
            connect_timeout=15,   # Evita travamento infinito
            ssl_disabled=False    # TiDB exige SSL
        )
    except Exception as e:
        st.error(f"Erro crítico de conexão: {e}")
        return None

# 3. CONTROLE DE SESSÃO / LOGIN
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Acesso ao Sistema 5W2H")
    with st.form("login_form"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        enviar = st.form_submit_button("Entrar")
        
        if enviar:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (usuario, senha))
                if cursor.fetchone():
                    st.session_state['logado'] = True
                    conn.close()
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
                    conn.close()
    st.stop()

# 4. DASHBOARD (APÓS LOGIN)
st.sidebar.title("Opções")
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

st.title("📋 Plano de Ação Estratégico 5W2H")

# Carregar dados do Banco
conn = get_db_connection()
if conn:
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Buscar Usuários para o selectbox
        cursor.execute("SELECT * FROM Usuarios")
        usuarios_db = cursor.fetchall()
        lista_usuarios = {u['nome']: u['id_usuario'] for u in usuarios_db} if usuarios_db else {}

        # --- FORMULÁRIO DE CADASTRO ---
        with st.expander("➕ Nova Ação"):
            if not lista_usuarios:
                st.warning("Cadastre um usuário na tabela 'Usuarios' do banco de dados primeiro.")
            else:
                with st.form("nova_acao"):
                    c1, c2 = st.columns(2)
                    with c1:
                        what = st.text_input("O que (Ação)?")
                        why = st.text_area("Por que?")
                        where = st.text_input("Onde?")
                    with c2:
                        who = st.selectbox("Quem?", list(lista_usuarios.keys()))
                        when = st.date_input("Prazo", datetime.now())
                        how = st.text_area("Como?")
                        status = st.selectbox("Status", ["Pendente", "Em Andamento", "Concluído"])
                    
                    if st.form_submit_button("Salvar"):
                        cursor.execute("""
                            INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (what, why, where, lista_usuarios[who], when, how, status))
                        conn.commit()
                        st.success("Ação salva!")
                        st.rerun()

        # --- TABELA DE EXIBIÇÃO ---
        st.subheader("Ações Registradas")
        try:
            # Query com JOIN para pegar o nome do responsável
            query = """
            SELECT A.id_acao, A.descricao_acao, A.porque, A.onde, U.nome as quem, A.prazo, A.como, A.status 
            FROM Acoes A 
            JOIN Usuarios U ON A.id_responsavel = U.id_usuario
            """
            df = pd.read_sql(query, conn)
            
            if df.empty:
                st.info("Nenhuma ação cadastrada no momento.")
            else:
                st.dataframe(df, use_container_width=True)

                # --- GERAR PDF ---
                def exportar_pdf(data_frame):
                    buf = io.BytesIO()
                    doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
                    elements = []
                    styles = getSampleStyleSheet()
                    elements.append(Paragraph("RELATÓRIO 5W2H", styles['Title']))
                    
                    # Preparar dados para a tabela do PDF
                    tabela_pdf = [["Ação", "Por que", "Quem", "Prazo", "Status"]]
                    for _, row in data_frame.iterrows():
                        tabela_pdf.append([row['descricao_acao'], row['porque'], row['quem'], str(row['prazo']), row['status']])
                    
                    t = Table(tabela_pdf)
                    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.grey),('GRID',(0,0),(-1,-1),1,colors.black)]))
                    elements.append(t)
                    doc.build(elements)
                    return buf.getvalue()

                st.download_button("📥 Baixar PDF", data=exportar_pdf(df), file_name="plano.pdf", mime="application/pdf")
        
        except Exception as e:
            st.warning("Aguardando preenchimento das tabelas ou erro na consulta.")
            st.write(f"Detalhe: {e}")

    finally:
        conn.close()

# Rodapé
st.caption("Sistema 5W2H v1.0 - Rodando via Streamlit Cloud & TiDB")
