import streamlit as st
import pymysql
import pandas as pd
from datetime import datetime
import io
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(page_title="Sistema 5W2H Completo", layout="wide")

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
    st.title("🔐 Login - 5W2H")
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

# --- DASHBOARD ---
st.title("🚀 Plano de Ação Estratégico 5W2H")
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

res_users = executar_db("SELECT id_usuario, nome FROM Usuarios")
dict_u = {user['nome']: user['id_usuario'] for user in res_users} if res_users else {}

# --- FORMULÁRIO 5W2H ---
with st.expander("➕ Cadastrar Novo Checklist 5W2H", expanded=True):
    with st.form("form_5w2h", clear_on_submit=True):
        c1, c2 = st.columns(2)
        
        with c1:
            what = st.text_input("What (O que será feito?)", placeholder="Ex: Treinamento de vendas")
            why = st.text_area("Why (Por que será feito?)", placeholder="Ex: Melhorar conversão de leads")
            where = st.text_input("Where (Onde será feito?)", placeholder="Ex: Sala de reuniões A")
            who = st.selectbox("Who (Quem fará?)", list(dict_u.keys()))
            
        with c2:
            when = st.date_input("When (Quando será feito? - Prazo)")
            how = st.text_area("How (Como será feito?)", placeholder="Ex: Através de workshop prático")
            how_much = st.number_input("How Much (Quanto custa?)", min_value=0.0, step=0.01)
            status = st.selectbox("Status Atual", ["Pendente", "Em Andamento", "Concluído", "Atrasado"])

        if st.form_submit_button("💾 Salvar Plano de Ação"):
            if not what:
                st.error("O campo 'What' é obrigatório!")
            else:
                sql_ins = """INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, quanto_custa, status) 
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                executar_db(sql_ins, (what, why, where, dict_u[who], when, how, how_much, status), retorno=False)
                st.success("Plano 5W2H salvo com sucesso!")
                st.rerun()

# --- LISTAGEM ---
st.subheader("📋 Ações em Execução")
acoes = executar_db("""
    SELECT A.*, U.nome as quem FROM Acoes A 
    JOIN Usuarios U ON A.id_responsavel = U.id_usuario 
    ORDER BY A.prazo ASC
""")

if acoes:
    df = pd.DataFrame(acoes)
    # Formatação visual da tabela
    st.dataframe(df[['descricao_acao', 'porque', 'onde', 'prazo', 'quem', 'como', 'quanto_custa', 'status']], use_container_width=True)
    
    # Opção de Exclusão por ID
    with st.sidebar:
        st.subheader("Gerenciar Dados")
        id_excluir = st.number_input("ID para excluir", min_value=1, step=1)
        if st.button("🗑️ Excluir Ação"):
            executar_db("DELETE FROM Acoes WHERE id_acao=%s", (id_excluir,), retorno=False)
            st.rerun()

    # --- GERAR PDF ---
    def gerar_pdf(lista):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
        elements = [Paragraph("RELATÓRIO ESTRATÉGICO 5W2H", getSampleStyleSheet()['Title']), Spacer(1,12)]
        data = [["What", "Why", "Where", "When", "Who", "How", "How Much"]]
        for r in lista:
            data.append([r['descricao_acao'], r['porque'], r['onde'], str(r['prazo']), r['quem'], r['como'], f"R$ {r['quanto_custa']:.2f}"])
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),colors.navy),
            ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
            ('GRID',(0,0),(-1,-1),1,colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 7)
        ]))
        elements.append(t)
        doc.build(elements)
        return buf.getvalue()

    st.download_button("📥 Exportar Plano 5W2H (PDF)", gerar_pdf(acoes), "plano_5w2h.pdf", "application/pdf")
else:
    st.info("Nenhum plano de ação cadastrado.")
