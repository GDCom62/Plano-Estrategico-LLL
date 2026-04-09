import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import io

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Sistema 5W2H Profissional", layout="wide")

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
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']:
    st.title("🔐 Login")
    u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if executar_db("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s)):
            st.session_state['logado'] = True
            st.rerun()
    st.stop()

# --- CARREGAR DADOS ---
@st.cache_data(ttl=30)
def buscar_dados():
    return executar_db("SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario")

dados_db = buscar_dados()
df_total = pd.DataFrame(dados_db) if dados_db else pd.DataFrame()

# --- BARRA LATERAL ---
st.sidebar.title("📊 Painel de Controle")
if not df_total.empty:
    df_total['prazo'] = pd.to_datetime(df_total['prazo']).dt.date
    f_prio = st.sidebar.multiselect("Prioridade:", ["Alta", "Média", "Baixa"], default=["Alta", "Média", "Baixa"])
    df = df_total[df_total['prioridade'].isin(f_prio)]
    
    # Exportação Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Gestao_5W2H')
    st.sidebar.download_button("📊 Exportar Excel", output.getvalue(), "relatorio_5w2h.xlsx")
else:
    df = df_total

if st.sidebar.button("🚪 Sair"):
    st.session_state['logado'] = False
    st.rerun()

# --- DASHBOARD ---
st.title("🚀 Gestão Estratégica 5W2H")

if not df.empty:
    hoje = date.today()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Ações", len(df))
    c2.metric("Alta Prioridade", len(df[df['prioridade'] == 'Alta']))
    c3.metric("Investimento Total", f"R$ {pd.to_numeric(df['quanto_custa']).sum():,.2f}")
    atrasos = len(df[(df['prazo'] < hoje) & (df['status'] != 'Concluído')])
    c4.metric("🚨 Em Atraso", atrasos, delta_color="inverse")

# --- FORMULÁRIO ---
with st.expander("➕ Nova Ação / Comentário"):
    res_u = executar_db("SELECT id_usuario, nome FROM Usuarios")
    dict_u = {user['nome']: user['id_usuario'] for user in res_u} if res_u else {}
    with st.form("form_obs"):
        col1, col2 = st.columns(2)
        with col1:
            what = st.text_input("O que fazer?")
            prio = st.select_slider("Prioridade", options=["Baixa", "Média", "Alta"], value="Média")
            obs = st.text_area("Observações / Justificativas", placeholder="Descreva o andamento ou motivos de atraso...")
        with col2:
            who = st.selectbox("Responsável", list(dict_u.keys()))
            when = st.date_input("Prazo")
            cost = st.number_input("Custo R$", min_value=0.0)
            status = st.selectbox("Status", ["Em análise", "Em andamento", "Concluído"])
        
        if st.form_submit_button("Salvar Plano"):
            sql = "INSERT INTO Acoes (descricao_acao, id_responsavel, prazo, quanto_custa, status, prioridade, observacoes) VALUES (%s,%s,%s,%s,%s,%s,%s)"
            executar_db(sql, (what, dict_u[who], when, cost, status, prio, obs), retorno=False)
            st.cache_data.clear()
            st.success("Item registrado com sucesso!")
            st.rerun()

# --- LISTAGEM ---
st.subheader("📋 Plano de Ação Detalhado")
if not df.empty:
    for _, row in df.iterrows():
        hoje = date.today()
        atraso = row['prazo'] < hoje and row['status'] != 'Concluído'
        prio_icon = "🔴" if row['prioridade'] == "Alta" else "🟡" if row['prioridade'] == "Média" else "🟢"
        barra_cor = "#dc3545" if atraso else "#28a745" if row['status'] == "Concluído" else "#ffc107"
        
        with st.container():
            c1, c2, c3 = st.columns([0.02, 0.88, 0.1])
            c1.markdown(f"<div style='background-color:{barra_cor}; height:80px; width:8px; border-radius:5px'></div>", unsafe_allow_html=True)
            with c2:
                st.write(f"{prio_icon} **{row['descricao_acao']}** | Resp: {row['quem']} | R$ {row['quanto_custa']:,.2f}")
                if row['observacoes']:
                    st.info(f"💬 **Obs:** {row['observacoes']}")
                st.caption(f"Prazo: {row['prazo'].strftime('%d/%m/%Y')} | Status: {row['status']} {'⚠️ ATRASADA' if atraso else ''}")
            with c3:
                if st.button("🗑️", key=f"d_{row['id_acao']}"):
                    executar_db("DELETE FROM Acoes WHERE id_acao=%s", (row['id_acao'],), retorno=False)
                    st.cache_data.clear()
                    st.rerun()
            st.divider()
else:
    st.info("Nenhuma ação cadastrada.")
