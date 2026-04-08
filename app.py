import streamlit as st
import pymysql
import pandas as pd
from datetime import datetime
import io
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="Sistema 5W2H Pro", layout="wide")

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
            st.error("Usuário ou senha inválidos.")
    st.stop()

# --- DASHBOARD ---
st.title("🚀 Plano de Ação Estratégico 5W2H")
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

# Buscar Usuários
res_users = executar_db("SELECT id_usuario, nome FROM Usuarios")
dict_u = {user['nome']: user['id_usuario'] for user in res_users} if res_users else {}

# --- FORMULÁRIO COMPLETO ---
with st.expander("➕ Novo Plano de Ação", expanded=True):
    with st.form("form_5w2h", clear_on_submit=True):
        c1, c2 = st.columns(2)
        
        with c1:
            what = st.text_input("What (O que?)", placeholder="Ação a ser realizada")
            why = st.text_area("Why (Por que?)", placeholder="Motivo/Justificativa")
            where = st.text_input("Where (Onde?)", placeholder="Local ou setor")
            who = st.selectbox("Who (Quem?)", list(dict_u.keys()))
            
        with c2:
            when = st.date_input("When (Quando?)", datetime.now())
            how = st.text_area("How (Como?)", placeholder="Método ou etapas")
            how_much = st.number_input("How Much (Quanto custa?)", min_value=0.0)
            # CAMPO DE STATUS SOLICITADO:
            status = st.selectbox("Status Atual", ["Em análise", "Em andamento", "Concluído", "Atrasado"])

        if st.form_submit_button("💾 Salvar Plano de Ação"):
            if not what:
                st.error("Preencha o campo 'What'!")
            else:
                sql_ins = """INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, quanto_custa, status) 
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                executar_db(sql_ins, (what, why, where, dict_u[who], when, how, how_much, status), retorno=False)
                st.success("Plano salvo com sucesso!")
                st.rerun()

# --- LISTAGEM ---
st.subheader("📋 Ações Cadastradas")
acoes = executar_db("""
    SELECT A.*, U.nome as quem FROM Acoes A 
    JOIN Usuarios U ON A.id_responsavel = U.id_usuario 
    ORDER BY A.prazo ASC
""")

if acoes:
    df = pd.DataFrame(acoes)
    # Reorganizar colunas para exibição amigável
    colunas_exibir = ['id_acao', 'descricao_acao', 'quem', 'prazo', 'status', 'porque', 'onde', 'como', 'quanto_custa']
    st.dataframe(df[colunas_exibir], use_container_width=True)
    
    # Exclusão
    with st.sidebar:
        st.subheader("Gerenciar")
        id_del = st.number_input("ID da ação para excluir", min_value=1, step=1)
        if st.button("🗑️ Excluir"):
            executar_db("DELETE FROM Acoes WHERE id_acao=%s", (id_del,), retorno=False)
            st.rerun()

    # PDF
    def gerar_pdf(lista):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
        elements = [Paragraph("RELATÓRIO 5W2H", getSampleStyleSheet()['Title']), Spacer(1,12)]
        data = [["Ação", "Quem", "Prazo", "Status", "Por que", "Como"]]
        for r in lista:
            data.append([r['descricao_acao'], r['quem'], str(r['prazo']), r['status'], r['porque'][:30], r['como'][:30]])
        t = Table(data)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.navy),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),1,colors.grey)]))
        elements.append(t)
        doc.build(elements)
        return buf.getvalue()

    st.download_button("📥 Gerar PDF", gerar_pdf(acoes), "plano_5w2h.pdf", "application/pdf")
else:
    st.info("Nenhuma ação no momento.")
