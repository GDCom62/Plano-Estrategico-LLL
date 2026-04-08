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

# --- ESTADO DE EDIÇÃO ---
if 'edit_id' not in st.session_state:
    st.session_state.edit_id = None

# --- DASHBOARD ---
st.title("🚀 Plano de Ação Estratégico 5W2H")
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

# Buscar Usuários
res_users = executar_db("SELECT id_usuario, nome FROM Usuarios")
dict_u = {user['nome']: user['id_usuario'] for user in res_users} if res_users else {}

# Se estiver em modo edição, buscar os dados do item
dados_edit = None
if st.session_state.edit_id:
    res = executar_db("SELECT * FROM Acoes WHERE id_acao=%s", (st.session_state.edit_id,))
    if res: dados_edit = res[0]

# --- FORMULÁRIO (CADASTRO OU EDIÇÃO) ---
titulo_form = "📝 Editar Ação" if st.session_state.edit_id else "➕ Novo Plano de Ação"
with st.expander(titulo_form, expanded=True):
    with st.form("form_5w2h", clear_on_submit=True):
        c1, c2 = st.columns(2)
        
        with c1:
            what = st.text_input("What (O que?)", value=dados_edit['descricao_acao'] if dados_edit else "")
            why = st.text_area("Why (Por que?)", value=dados_edit['porque'] if dados_edit else "")
            where = st.text_input("Where (Onde?)", value=dados_edit['onde'] if dados_edit else "")
            
        with c2:
            idx_user = list(dict_u.values()).index(dados_edit['id_responsavel']) if dados_edit and dados_edit['id_responsavel'] in dict_u.values() else 0
            who = st.selectbox("Who (Quem?)", list(dict_u.keys()), index=idx_user)
            
            # Ajuste de data para edição
            data_padrao = dados_edit['prazo'] if dados_edit else datetime.now()
            when = st.date_input("When (Quando?)", data_padrao)
            
            how = st.text_area("How (Como?)", value=dados_edit['como'] if dados_edit else "")
            
            status_opcoes = ["Em análise", "Em andamento", "Concluído", "Atrasado"]
            idx_status = status_opcoes.index(dados_edit['status']) if dados_edit and dados_edit['status'] in status_opcoes else 0
            status = st.selectbox("Status Atual", status_opcoes, index=idx_status)

        col_btn1, col_btn2 = st.columns([0.2, 0.8])
        with col_btn1:
            if st.form_submit_button("💾 Salvar"):
                if st.session_state.edit_id:
                    sql = "UPDATE Acoes SET descricao_acao=%s, porque=%s, onde=%s, id_responsavel=%s, prazo=%s, como=%s, status=%s WHERE id_acao=%s"
                    executar_db(sql, (what, why, where, dict_u[who], when, how, status, st.session_state.edit_id), retorno=False)
                    st.session_state.edit_id = None
                else:
                    sql = "INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, status) VALUES (%s,%s,%s,%s,%s,%s,%s)"
                    executar_db(sql, (what, why, where, dict_u[who], when, how, status), retorno=False)
                st.rerun()
        
        with col_btn2:
            if st.session_state.edit_id:
                if st.form_submit_button("❌ Cancelar Edição"):
                    st.session_state.edit_id = None
                    st.rerun()

# --- LISTAGEM ---
st.subheader("📋 Ações Cadastradas")
acoes = executar_db("SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario ORDER BY A.prazo ASC")

if acoes:
    for a in acoes:
        with st.container():
            col_info, col_edit, col_del = st.columns([0.7, 0.15, 0.15])
            
            with col_info:
                st.markdown(f"**{a['descricao_acao']}** | Resp: {a['quem']} | Status: `{a['status']}`")
                st.caption(f"Prazo: {a['prazo']} | Onde: {a['onde']}")
            
            with col_edit:
                if st.button("✏️ Editar", key=f"edit_{a['id_acao']}"):
                    st.session_state.edit_id = a['id_acao']
                    st.rerun()
            
            with col_del:
                if st.button("🗑️ Excluir", key=f"del_{a['id_acao']}"):
                    executar_db("DELETE FROM Acoes WHERE id_acao=%s", (a['id_acao'],), retorno=False)
                    st.rerun()
            st.divider()

    # --- FUNÇÃO PDF ---
    def gerar_pdf(lista):
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
        elements = [Paragraph("RELATÓRIO 5W2H", getSampleStyleSheet()['Title']), Spacer(1,12)]
        data = [["Ação", "Quem", "Prazo", "Status"]]
        for r in lista:
            data.append([str(r.get('descricao_acao') or ""), str(r.get('quem') or ""), str(r.get('prazo') or ""), str(r.get('status') or "")])
        t = Table(data); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.navy),('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),('GRID',(0,0),(-1,-1),1,colors.grey)]))
        elements.append(t); doc.build(elements)
        return buf.getvalue()

    st.download_button("📥 Gerar PDF", gerar_pdf(acoes), "plano_5w2h.pdf", "application/pdf")
else:
    st.info("Nenhuma ação cadastrada.")
