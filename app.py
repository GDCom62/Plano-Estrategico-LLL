import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Lavo e Levo - Plano Estratégico", layout="wide")

# 2. FUNÇÃO DE CONEXÃO
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

# 3. CONTROLE DE SESSÃO
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'edit_id' not in st.session_state: st.session_state.edit_id = None
if 'confirmar_excluir' not in st.session_state: st.session_state.confirmar_excluir = None

# --- LOGIN ---
if not st.session_state['logado']:
    st.markdown("<h2 style='text-align: center;'>🧺 Lavanderia Lavo e Levo</h2>", unsafe_allow_html=True)
    with st.form("login_form"):
        u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar no Sistema"):
            res = executar_db("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s))
            if res:
                st.session_state['logado'], st.session_state['nivel'] = True, res[0].get('nivel', 'Comum')
                st.rerun()
            else:
                st.error("Dados de acesso incorretos.")
    st.stop()

# --- CARREGAR DADOS ---
@st.cache_data(ttl=10)
def buscar_dados():
    return executar_db("SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario ORDER BY A.prazo ASC")

dados_db = buscar_dados()
df = pd.DataFrame(dados_db) if dados_db else pd.DataFrame()

# --- TITULO PERSONALIZADO ---
st.markdown("""
    <h1 style='text-align: center; color: #1E3A8A; padding-bottom: 5px;'>
        🧺 PLANO ESTRATÉGICO DA LAVANDERIA LAVO E LEVO
    </h1>
    <p style='text-align: center; color: #6B7280; font-size: 1.1em;'>Gestão 5W2H e Controle de Performance</p>
    <hr style='border: 1px solid #3B82F6; margin-bottom: 30px;'>
""", unsafe_allow_html=True)

# --- ABAS ---
tab_lista, tab_graficos = st.tabs(["📝 Lançamentos e Controle", "📊 Análise de Performance"])

with tab_lista:
    # FORMULÁRIO (CADASTRO / EDIÇÃO)
    dados_edit = None
    if st.session_state.edit_id:
        res_e = executar_db("SELECT * FROM Acoes WHERE id_acao=%s", (st.session_state.edit_id,))
        if res_e: dados_edit = res_e[0]

    with st.expander("📝 Formulário 5W2H", expanded=(st.session_state.edit_id is not None)):
        res_u = executar_db("SELECT id_usuario, nome FROM Usuarios")
        dict_u = {u['nome']: u['id_usuario'] for u in res_u} if res_u else {}
        
        with st.form("form_5w2h", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                what = st.text_input("What (O que?)", value=dados_edit['descricao_acao'] if dados_edit else "")
                why = st.text_area("Why (Por que?)", value=dados_edit['porque'] if dados_edit else "")
                prio = st.select_slider("Prioridade", options=["Baixa", "Média", "Alta"], value=dados_edit['prioridade'] if dados_edit else "Média")
            with c2:
                who = st.selectbox("Who (Quem?)", list(dict_u.keys()))
                when = st.date_input("When (Prazo)", dados_edit['prazo'] if dados_edit else date.today(), format="DD/MM/YYYY")
                cost = st.number_input("How Much (Custo R$)", value=float(dados_edit['quanto_custa'] or 0) if dados_edit else 0.0)
                status = st.selectbox("Status", ["Em análise", "Em andamento", "Concluído"], index=0)
                obs = st.text_input("Observações", value=dados_edit['observacoes'] if dados_edit else "")

            if st.form_submit_button("💾 Salvar Plano de Ação"):
                if st.session_state.edit_id:
                    sql = "UPDATE Acoes SET descricao_acao=%s, porque=%s, id_responsavel=%s, prazo=%s, quanto_custa=%s, status=%s, prioridade=%s, observacoes=%s WHERE id_acao=%s"
                    executar_db(sql, (what, why, dict_u[who], when, cost, status, prio, obs, st.session_state.edit_id), False)
                    st.session_state.edit_id = None
                else:
                    sql = "INSERT INTO Acoes (descricao_acao, porque, id_responsavel, prazo, quanto_custa, status, prioridade, observacoes) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
                    executar_db(sql, (what, why, dict_u[who], when, cost, status, prio, obs), False)
                st.cache_data.clear()
                st.rerun()
        
        if st.session_state.edit_id: 
            if st.button("❌ Cancelar Edição"):
                st.session_state.edit_id = None
                st.rerun()

    # LISTAGEM
    st.subheader("📋 Ações e Prazos")
    if not df.empty:
        hoje = date.today()
        for _, row in df.iterrows():
            dt_br = pd.to_datetime(row['prazo']).strftime('%d/%m/%Y')
            atraso = pd.to_datetime(row['prazo']).date() < hoje and row['status'] != 'Concluído'
            cor = "#dc3545" if atraso else "#28a745" if row['status'] == "Concluído" else "#ffc107"
            
            with st.container():
                c1, c2, c3, c4 = st.columns([0.02, 0.78, 0.1, 0.1])
                c1.markdown(f"<div style='background-color:{cor}; height:75px; width:8px; border-radius:5px'></div>", unsafe_allow_html=True)
                with c2:
                    st.write(f"**{row['descricao_acao']}** | {row['quem']} | **{dt_br}**")
                    st.caption(f"Status: {row['status']} | Prioridade: {row['prioridade']} | R$ {float(row['quanto_custa'] or 0):,.2f}")
                    if row['observacoes']: st.info(f"💬 {row['observacoes']}")
                
                if c3.button("✏️", key=f"ed_{row['id_acao']}"):
                    st.session_state.edit_id = row['id_acao']
                    st.rerun()
                
                if c4.button("🗑️", key=f"btn_ex_{row['id_acao']}"):
                    st.session_state.confirmar_excluir = row['id_acao']
                
                if st.session_state.confirmar_excluir == row['id_acao']:
                    st.warning(f"Excluir item {row['id_acao']}?")
                    ca, cb = st.columns(2)
                    if ca.button("✅ SIM", key=f"sim_{row['id_acao']}"):
                        executar_db("DELETE FROM Acoes WHERE id_acao=%s", (row['id_acao'],), False)
                        st.session_state.confirmar_excluir = None
                        st.cache_data.clear()
                        st.rerun()
                    if cb.button("❌ NÃO", key=f"nao_{row['id_acao']}"):
                        st.session_state.confirmar_excluir = None
                        st.rerun()
                st.divider()
    else:
        st.info("Nenhuma ação registrada para a lavanderia.")

with tab_graficos:
    if not df.empty:
        st.subheader("📊 Indicadores da Lavo e Levo")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Ações Ativas", len(df))
        m2.metric("Concluídas", len(df[df['status'] == 'Concluído']))
        m3.metric("Inv. Total", f"R$ {pd.to_numeric(df['quanto_custa']).sum():,.2f}")
        m4.metric("🚨 Atrasos", len(df[(pd.to_datetime(df['prazo']).dt.date < hoje) & (df['status'] != 'Concluído')]))
        
        g1, g2 = st.columns(2)
        with g1:
            fig1 = px.pie(df, names='status', title="Distribuição por Status", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig1, use_container_width=True)
        with g2:
            fig2 = px.bar(df, x='prioridade', y='quanto_custa', color='status', title="Investimento por Prioridade", barmode='group')
            st.plotly_chart(fig2, use_container_width=True)

# BARRA LATERAL
st.sidebar.markdown(f"**Usuário:** {st.session_state.get('user', 'Admin')}")
if st.sidebar.button("Sair do Sistema"):
    st.session_state['logado'] = False
    st.rerun()
