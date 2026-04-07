import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime
import io
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Sistema 5W2H", layout="wide")

# FUNÇÃO DE CONEXÃO ROBUSTA (Ajustada para não travar no Cloud)
def get_db_connection():
    try:
        return mysql.connector.connect(
            host=st.secrets["DB_HOST"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
            database=st.secrets["DB_NAME"],
            port=int(st.secrets["DB_PORT"]),
            use_pure=True,        # Driver 100% Python
            connect_timeout=20,   # Tempo extra para a nuvem responder
            ssl_disabled=False    # TiDB exige SSL
        )
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {e}")
        return None

# CONTROLE DE SESSÃO / LOGIN
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Acesso ao Sistema 5W2H")
    with st.form("login_form"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (usuario, senha))
                user_data = cursor.fetchone()
                if user_data:
                    st.session_state['logado'] = True
                    conn.close()
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
                    conn.close()
    st.stop()

# DASHBOARD (APÓS LOGIN)
st.sidebar.title("Opções")
if st.sidebar.button("Sair / Logout"):
    st.session_state['logado'] = False
    st.rerun()

st.title("📋 Plano de Ação Estratégico 5W2H")

conn = get_db_connection()
if conn:
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 1. BUSCAR USUÁRIOS (PARA O SELECTBOX)
        cursor.execute("SELECT id_usuario, nome FROM Usuarios")
        usuarios_lista = cursor.fetchall()
        dict_usuarios = {u['nome']: u['id_usuario'] for u in usuarios_lista} if usuarios_lista else {}

        # 2. FORMULÁRIO DE CADASTRO
        with st.expander("➕ Nova Ação"):
            if not dict_usuarios:
                st.warning("Cadastre um responsável na tabela 'Usuarios' do TiDB primeiro.")
            else:
                with st.form("form_nova_acao"):
                    col1, col2 = st.columns(2)
                    with col1:
                        what = st.text_input("O que (Ação)?")
                        why = st.text_area("Por que?")
                        where = st.text_input("Onde?")
                    with col2:
                        who = st.selectbox("Quem?", list(dict_usuarios.keys()))
                        when = st.date_input("Prazo", datetime.now())
                        how = st.text_area("Como?")
                        status = st.selectbox("Status", ["Pendente", "Em Andamento", "Concluído", "Atrasado"])
                    
                    if st.form_submit_button("Salvar Ação"):
                        cursor.execute("""
                            INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (what, why, where, dict_usuarios[who], when, how, status))
                        conn.commit()
                        st.success("Ação salva com sucesso!")
                        st.rerun()

        # 3. EXIBIÇÃO DA TABELA (VERSÃO MANUAL - EVITA TRAVAMENTOS)
        st.subheader("Ações Registradas")
        sql_visualizacao = """
            SELECT A.id_acao, A.descricao_acao, A.porque, A.onde, U.nome as quem, A.prazo, A.como, A.status 
            FROM Acoes A 
            JOIN Usuarios U ON A.id_responsavel = U.id_usuario
            ORDER BY A.prazo ASC
        """
        cursor.execute(sql_visualizacao)
        dados_tabela = cursor.fetchall()

        if not dados_tabela:
            st.info("Nenhuma ação cadastrada ainda.")
        else:
            # Converte para DataFrame só para mostrar na tela
            df_display = pd.DataFrame(dados_tabela)
            st.dataframe(df_display, use_container_width=True)

            # 4. FUNÇÃO GERAR PDF
            def exportar_pdf(lista_registros):
                buf = io.BytesIO()
                doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
                elements = []
                styles = getSampleStyleSheet()
                elements.append(Paragraph("PLANO DE AÇÃO 5W2H", styles['Title']))
                elements.append(Spacer(1, 12))
                
                cabecalho = ["Ação", "Quem", "Prazo", "Status", "Como"]
                corpo_tabela = [cabecalho]
                for r in lista_registros:
                    corpo_tabela.append([r['descricao_acao'], r['quem'], str(r['prazo']), r['status'], r['como']])
                
                t = Table(corpo_tabela)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.navy),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('GRID', (0,0), (-1,-1), 1, colors.grey),
                    ('FONTSIZE', (0,0), (-1,-1), 8)
                ]))
                elements.append(t)
                doc.build(elements)
                return buf.getvalue()

            st.download_button(
                label="📥 Baixar PDF",
                data=exportar_pdf(dados_tabela),
                file_name="relatorio_5w2h.pdf",
                mime="application/pdf"
            )

    except Exception as error:
        st.error(f"Erro ao processar dados: {error}")
    finally:
        conn.close()

st.caption("v1.1 - Conexão Manual Otimizada")
