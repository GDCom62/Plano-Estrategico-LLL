import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Sistema 5W2H Performance", layout="wide")

# 2. FUNÇÃO DE CONEXÃO COM CACHE (Para evitar travamentos)
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

# 3. CONTROLE DE LOGIN
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🔐 Login - Gestão Estratégica")
    with st.form("login_form"):
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            res = executar_db("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s))
            if res:
                st.session_state['logado'] = True
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()

# 4. BARRA LATERAL E LOGOUT
st.sidebar.title("⚙️ Menu")
if st.sidebar.button("Sair / Logout"):
    st.session_state['logado'] = False
    st.rerun()

if st.sidebar.button("🔄 Atualizar Dashboard"):
    st.cache_data.clear()
    st.rerun()

# 5. CARREGAMENTO DE DADOS (USANDO CACHE PARA PERFORMANCE)
@st.cache_data(ttl=60)
def buscar_dados_completos():
    return executar_db("SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario ORDER BY A.prazo ASC")

dados_raw = buscar_dados_completos()
df = pd.DataFrame(dados_raw) if dados_raw else pd.DataFrame()

# 6. DASHBOARD DE GRÁFICOS
st.title("🚀 Performance 5W2H")

if not df.empty:
    # Métricas Rápidas
    m1, m2, m3 = st.columns(3)
    m1.metric("Total de Ações", len(df))
    m2.metric("Concluídas", len(df[df['status'] == 'Concluído']))
    m3.metric("Em Andamento", len(df[df['status'] == 'Em andamento']))

    # Gráficos Lado a Lado
    c1, c2 = st.columns(2)
    with c1:
        fig_pie = px.pie(df, names='status', title="Status Geral", hole=0.4,
                         color_discrete_map={'Concluído':'#28a745', 'Em andamento':'#ffc107', 'Em análise':'#17a2b8', 'Atrasado':'#dc3545'})
        st.plotly_chart(fig_pie, use_container_width=True)
    with c2:
        df['ano'] = pd.to_datetime(df['prazo']).dt.year
        df_ano = df.groupby(['ano', 'status']).size().reset_index(name='total')
        fig_bar = px.bar(df_ano, x='ano', y='total', color='status', barmode='group', title="Comparativo Anual")
        st.plotly_chart(fig_bar, use_container_width=True)

# 7. FORMULÁRIO DE DADOS (5W2H COMPLETO)
res_u = executar_db("SELECT id_usuario, nome FROM Usuarios")
dict_u = {user['nome']: user['id_usuario'] for user in res_u} if res_u else {}

with st.expander("➕ Cadastrar Nova Ação"):
    with st.form("form_novo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            what = st.text_input("What (O que?)")
            why = st.text_area("Why (Por que?)")
            where = st.text_input("Where (Onde?)")
        with col2:
            who = st.selectbox("Who (Responsável)", list(dict_u.keys()))
            when = st.date_input("When (Prazo)")
            status = st.selectbox("Status", ["Em análise", "Em andamento", "Concluído", "Atrasado"])
        
        if st.form_submit_button("Salvar Ação"):
            sql = "INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, status) VALUES (%s,%s,%s,%s,%s,%s)"
            executar_db(sql, (what, why, where, dict_u[who], when, status), retorno=False)
            st.cache_data.clear()
            st.success("Salvo!")
            st.rerun()

# 8. LISTAGEM COM EDIÇÃO E EXCLUSÃO
st.subheader("📋 Detalhes do Plano")
if not df.empty:
    for _, row in df.iterrows():
        cor = "#28a745" if row['status'] == "Concluído" else "#ffc107" if row['status'] == "Em andamento" else "#17a2b8"
        with st.container():
            c_faixa, c_info, c_btns = st.columns([0.02, 0.78, 0.2])
            c_faixa.markdown(f"<div style='background-color:{cor}; height:50px; width:8px; border-radius:5px'></div>", unsafe_allow_html=True)
            c_info.write(f"**{row['descricao_acao']}** | {row['quem']} | `{row['status']}`")
            if c_btns.button("🗑️ Excluir", key=f"del_{row['id_acao']}"):
                executar_db("DELETE FROM Acoes WHERE id_acao=%s", (row['id_acao'],), retorno=False)
                st.cache_data.clear()
                st.rerun()
            st.divider()
