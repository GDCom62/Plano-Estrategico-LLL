import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# 1. CONFIGURAÇÃO
st.set_page_config(page_title="Gestão 5W2H - Filtros Temporais", layout="wide")

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

dados = buscar_dados()
df_total = pd.DataFrame(dados) if dados else pd.DataFrame()

# --- BARRA LATERAL (FILTROS DE PERÍODO) ---
st.sidebar.title("📅 Filtros de Período")
if not df_total.empty:
    df_total['prazo'] = pd.to_datetime(df_total['prazo']).dt.date
    min_date = df_total['prazo'].min()
    max_date = df_total['prazo'].max()
    
    data_inicio = st.sidebar.date_input("Data Início", min_date)
    data_fim = st.sidebar.date_input("Data Fim", max_date)

    # Aplicar Filtro de Data
    df = df_total[(df_total['prazo'] >= data_inicio) & (df_total['prazo'] <= data_fim)]
else:
    df = df_total

if st.sidebar.button("🚪 Sair"):
    st.session_state['logado'] = False
    st.rerun()

# --- DASHBOARD ---
st.title("🚀 Performance 5W2H por Período")

if not df.empty:
    hoje = date.today()
    df['quanto_custa'] = pd.to_numeric(df['quanto_custa']).fillna(0)
    
    # KPIs
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ações no Período", len(df))
    concluidos = len(df[df['status'] == 'Concluído'])
    m2.metric("Concluídas", concluidos)
    m3.metric("Investimento", f"R$ {df['quanto_custa'].sum():,.2f}")
    
    atrasados = len(df[(df['prazo'] < hoje) & (df['status'] != 'Concluído')])
    m4.metric("🚨 Atrasadas", atrasados, delta_color="inverse")

    # Gráficos
    c1, c2 = st.columns(2)
    with c1:
        fig_pie = px.pie(df, names='status', title="Status das Ações no Período", hole=0.4,
                         color_discrete_map={'Concluído':'#28a745', 'Em andamento':'#ffc107', 'Em análise':'#17a2b8'})
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        # Evolução Mensal de Custos
        df_temp = df.copy()
        df_temp['mes_ano'] = pd.to_datetime(df_temp['prazo']).dt.strftime('%m/%Y')
        fig_evol = px.line(df_temp.sort_values('prazo'), x='prazo', y='quanto_custa', title="Distribuição Financeira no Tempo", markers=True)
        st.plotly_chart(fig_evol, use_container_width=True)

# --- FORMULÁRIO ---
with st.expander("➕ Nova Ação (Checklist 5W2H)"):
    res_u = executar_db("SELECT id_usuario, nome FROM Usuarios")
    dict_u = {user['nome']: user['id_usuario'] for user in res_u} if res_u else {}
    
    with st.form("form_novo"):
        col1, col2 = st.columns(2)
        with col1:
            what = st.text_input("What (O que?)")
            why = st.text_area("Why (Por que?)")
            how_much = st.number_input("How Much (Custo R$)", min_value=0.0)
        with col2:
            who = st.selectbox("Who (Quem?)", list(dict_u.keys()))
            when = st.date_input("When (Prazo)")
            status = st.selectbox("Status", ["Em análise", "Em andamento", "Concluído"])
        
        if st.form_submit_button("Salvar"):
            executar_db("INSERT INTO Acoes (descricao_acao, porque, id_responsavel, prazo, quanto_custa, status) VALUES (%s,%s,%s,%s,%s,%s)", 
                       (what, why, dict_u[who], when, how_much, status), retorno=False)
            st.cache_data.clear()
            st.rerun()

# --- LISTAGEM ---
st.subheader("📋 Detalhes do Período Selecionado")
if not df.empty:
    for _, row in df.iterrows():
        atraso = row['prazo'] < hoje and row['status'] != 'Concluído'
        cor = "#dc3545" if atraso else ("#28a745" if row['status'] == "Concluído" else "#ffc107")
        
        with st.container():
            c1, c2, c3 = st.columns([0.02, 0.78, 0.2])
            c1.markdown(f"<div style='background-color:{cor}; height:60px; width:8px; border-radius:5px'></div>", unsafe_allow_html=True)
            c2.write(f"**{row['descricao_acao']}** | {row['quem']} | R$ {row['quanto_custa']:,.2f} {'🔴 **ATRASADA**' if atraso else ''}")
            c2.caption(f"Prazo: {row['prazo'].strftime('%d/%m/%Y')} | Status: `{row['status']}`")
            if c3.button("🗑️", key=f"del_{row['id_acao']}"):
                executar_db("DELETE FROM Acoes WHERE id_acao=%s", (row['id_acao'],), retorno=False)
                st.cache_data.clear()
                st.rerun()
            st.divider()
else:
    st.warning("Nenhuma ação encontrada para este período.")
