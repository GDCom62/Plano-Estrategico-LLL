import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import io

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Gestão 5W2H Profissional", layout="wide")

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
@st.cache_data(ttl=60)
def buscar_dados():
    return executar_db("SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario")

dados_db = buscar_dados()
df_total = pd.DataFrame(dados_db) if dados_db else pd.DataFrame()

# --- BARRA LATERAL ---
st.sidebar.title("🎯 Gestão de Foco")
if not df_total.empty:
    df_total['prazo'] = pd.to_datetime(df_total['prazo']).dt.date
    # Filtro de Prioridade
    f_prio = st.sidebar.multiselect("Filtrar Prioridade:", ["Alta", "Média", "Baixa"], default=["Alta", "Média", "Baixa"])
    # Filtro de Data
    d_ini = st.sidebar.date_input("Início", df_total['prazo'].min())
    d_fim = st.sidebar.date_input("Fim", df_total['prazo'].max())
    
    df = df_total[(df_total['prazo'] >= d_ini) & (df_total['prazo'] <= d_fim) & (df_total['prioridade'].isin(f_prio))]

    st.sidebar.divider()
    # Exportação Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='5W2H')
    st.sidebar.download_button("📊 Exportar Excel", output.getvalue(), "plano_5w2h.xlsx")
else:
    df = df_total

if st.sidebar.button("🚪 Sair"):
    st.session_state['logado'] = False
    st.rerun()

# --- DASHBOARD ---
st.title("🚀 Dashboard 5W2H & Performance")

if not df.empty:
    hoje = date.today()
    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Ações Filtradas", len(df))
    c2.metric("Alta Prioridade", len(df[df['prioridade'] == 'Alta']))
    c3.metric("Investimento", f"R$ {pd.to_numeric(df['quanto_custa']).sum():,.2f}")
    atrasos = len(df[(df['prazo'] < hoje) & (df['status'] != 'Concluído')])
    c4.metric("🚨 Atrasadas", atrasos)

    # Gráficos
    g1, g2 = st.columns(2)
    with g1:
        fig_prio = px.bar(df, x='prioridade', title="Distribuição por Prioridade", color='prioridade',
                          color_discrete_map={'Alta':'#dc3545', 'Média':'#ffc107', 'Baixa':'#28a745'})
        st.plotly_chart(fig_prio, use_container_width=True)
    with g2:
        fig_status = px.pie(df, names='status', title="Status das Ações", hole=0.4)
        st.plotly_chart(fig_status, use_container_width=True)

# --- FORMULÁRIO ---
with st.expander("➕ Nova Ação Estratégica"):
    res_u = executar_db("SELECT id_usuario, nome FROM Usuarios")
    dict_u = {user['nome']: user['id_usuario'] for user in res_u} if res_u else {}
    with st.form("form_prio"):
        col1, col2 = st.columns(2)
        with col1:
            what = st.text_input("O que?")
            prio = st.select_slider("Prioridade", options=["Baixa", "Média", "Alta"], value="Média")
            how_much = st.number_input("Custo R$", min_value=0.0)
        with col2:
            who = st.selectbox("Quem?", list(dict_u.keys()))
            when = st.date_input("Prazo")
            status = st.selectbox("Status", ["Em análise", "Em andamento", "Concluído"])
        
        if st.form_submit_button("Salvar Ação"):
            executar_db("INSERT INTO Acoes (descricao_acao, id_responsavel, prazo, quanto_custa, status, prioridade) VALUES (%s,%s,%s,%s,%s,%s)", 
                       (what, dict_u[who], when, how_much, status, prio), retorno=False)
            st.cache_data.clear()
            st.rerun()

# --- LISTAGEM ---
st.subheader("📋 Plano de Ação")
if not df.empty:
    for _, row in df.iterrows():
        # Lógica visual
        hoje = date.today()
        atraso = row['prazo'] < hoje and row['status'] != 'Concluído'
        # Cor da prioridade
        prio_cor = "🔴" if row['prioridade'] == "Alta" else "🟡" if row['prioridade'] == "Média" else "🟢"
        barra_cor = "#dc3545" if atraso else "#28a745" if row['status'] == "Concluído" else "#ffc107"
        
        with st.container():
            c1, c2, c3 = st.columns([0.02, 0.88, 0.1])
            c1.markdown(f"<div style='background-color:{barra_cor}; height:60px; width:8px; border-radius:5px'></div>", unsafe_allow_html=True)
            c2.write(f"{prio_cor} **{row['descricao_acao']}** | Resp: {row['quem']} | Custo: R$ {row['quanto_custa']:,.2f}")
            c2.caption(f"Prioridade: {row['prioridade']} | Prazo: {row['prazo'].strftime('%d/%m/%Y')} | Status: {row['status']} {'⚠️ ATRASADA' if atraso else ''}")
            if c3.button("🗑️", key=f"d_{row['id_acao']}"):
                executar_db("DELETE FROM Acoes WHERE id_acao=%s", (row['id_acao'],), retorno=False)
                st.cache_data.clear()
                st.rerun()
            st.divider()
