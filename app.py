import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
from datetime import datetime
import io

st.set_page_config(page_title="Performance 5W2H", layout="wide")

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
if 'logado' not in st.session_state: st.session_state['logado'] = False
if not st.session_state['logado']:
    st.title("🔐 Login")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if executar_db("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s)):
            st.session_state['logado'] = True
            st.rerun()
    st.stop()

# --- CARREGAR DADOS ---
acoes_raw = executar_db("SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario")
df = pd.DataFrame(acoes_raw) if acoes_raw else pd.DataFrame()

# --- BARRA LATERAL ---
st.sidebar.title("⚙️ Configurações")
meta_conclusao = st.sidebar.slider("Meta de Conclusão (%)", 0, 100, 80)
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

st.title("🚀 Dashboard de Performance 5W2H")

if not df.empty:
    # Tratamento de datas
    df['prazo'] = pd.to_datetime(df['prazo'])
    df['ano'] = df['prazo'].dt.year
    df['mes'] = df['prazo'].dt.month
    
    # 1. INDICADORES (METRICS)
    total = len(df)
    concluidos = len(df[df['status'] == 'Concluído'])
    perc_atingido = (concluidos / total * 100) if total > 0 else 0
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Ações", total)
    m2.metric("Concluídas", concluidos)
    m3.metric("Performance Atual", f"{perc_atingido:.1f}%", delta=f"{perc_atingido - meta_conclusao:.1f}% vs Meta")
    m4.metric("Atrasadas/Pendentes", len(df[df['status'] != 'Concluído']))

    # 2. GRÁFICOS
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Situação das Ações")
        fig_pie = px.pie(df, names='status', color='status', hole=0.4,
                         color_discrete_map={'Concluído':'#28a745', 'Em andamento':'#ffc107', 'Em análise':'#17a2b8', 'Atrasado':'#dc3545'})
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        st.subheader("Histórico de Produção (Anual)")
        df_ano = df.groupby(['ano', 'status']).size().reset_index(name='qtd')
        fig_bar = px.bar(df_ano, x='ano', y='qtd', color='status', barmode='group',
                         color_discrete_map={'Concluído':'#28a745', 'Em andamento':'#ffc107', 'Em análise':'#17a2b8', 'Atrasado':'#dc3545'})
        st.plotly_chart(fig_bar, use_container_width=True)

# --- FORMULÁRIO DE CADASTRO ---
with st.expander("➕ Adicionar/Editar Plano de Ação"):
    # (O formulário que já tínhamos nos passos anteriores entra aqui)
    st.info("Formulário de cadastro pronto para uso.")

# --- LISTA COM CORES ---
st.subheader("📋 Status da Produção")
if not df.empty:
    for _, row in df.iterrows():
        # Define a cor baseada no status
        cor_status = "#28a745" if row['status'] == "Concluído" else "#ffc107" if row['status'] == "Em andamento" else "#17a2b8"
        
        with st.container():
            col_faixa, col_info, col_btn = st.columns([0.02, 0.88, 0.1])
            with col_faixa:
                st.markdown(f"<div style='background-color:{cor_status}; height:60px; width:10px; border-radius:10px'></div>", unsafe_allow_html=True)
            with col_info:
                st.write(f"**{row['descricao_acao']}** | Responsável: {row['quem']}")
                st.caption(f"Prazo: {row['prazo'].strftime('%d/%m/%Y')} | Status: {row['status']}")
            with col_btn:
                if st.button("✏️", key=f"ed_{row['id_acao']}"):
                    st.session_state.edit_id = row['id_acao']
                    st.rerun()
            st.divider()
else:
    st.warning("Sem dados para exibir.")
