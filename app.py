import streamlit as st
import pymysql
import pandas as pd
import plotly.express as px
from datetime import datetime, date

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Sistema 5W2H Profissional", layout="wide")

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
    st.title("🔐 Login - Gestão 5W2H")
    u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
    if st.button("Entrar"):
        res = executar_db("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s))
        if res:
            st.session_state['logado'], st.session_state['nivel'] = True, res[0].get('nivel', 'Comum')
            st.rerun()
    st.stop()

# --- DADOS ---
@st.cache_data(ttl=10)
def buscar_dados():
    return executar_db("SELECT A.*, U.nome as quem FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario ORDER BY A.prazo ASC")

dados_db = buscar_dados()
df = pd.DataFrame(dados_db) if dados_db else pd.DataFrame()

# --- INTERFACE ---
st.title("🚀 Gestão Estratégica 5W2H")
tab_lista, tab_graficos = st.tabs(["📝 Lançamentos", "📊 Análise"])

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
                what = st.text_input("O que?", value=dados_edit['descricao_acao'] if dados_edit else "")
                why = st.text_area("Por que?", value=dados_edit['porque'] if dados_edit else "")
                prio = st.select_slider("Prioridade", options=["Baixa", "Média", "Alta"], value=dados_edit['prioridade'] if dados_edit else "Média")
            with c2:
                who = st.selectbox("Quem?", list(dict_u.keys()))
                when = st.date_input("Prazo", dados_edit['prazo'] if dados_edit else date.today(), format="DD/MM/YYYY")
                cost = st.number_input("Custo R$", value=float(dados_edit['quanto_custa'] or 0) if dados_edit else 0.0)
                status = st.selectbox("Status", ["Em análise", "Em andamento", "Concluído"], index=0)
                obs = st.text_input("Obs", value=dados_edit['observacoes'] if dados_edit else "")

            if st.form_submit_button("💾 Salvar"):
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
    st.subheader("📋 Ações Detalhadas")
    if not df.empty:
        hoje = date.today()
        for _, row in df.iterrows():
            dt_br = pd.to_datetime(row['prazo']).strftime('%d/%m/%Y')
            atraso = pd.to_datetime(row['prazo']).date() < hoje and row['status'] != 'Concluído'
            cor = "#dc3545" if atraso else "#28a745" if row['status'] == "Concluído" else "#ffc107"
            
            with st.container():
                c1, c2, c3, c4 = st.columns([0.02, 0.78, 0.1, 0.1])
                c1.markdown(f"<div style='background-color:{cor}; height:70px; width:8px; border-radius:5px'></div>", unsafe_allow_html=True)
                with c2:
                    st.write(f"**{row['descricao_acao']}** | {row['quem']} | **{dt_br}**")
                    st.caption(f"Status: {row['status']} | Prioridade: {row['prioridade']} | R$ {float(row['quanto_custa'] or 0):,.2f}")
                
                # BOTÃO EDITAR
                if c3.button("✏️", key=f"ed_{row['id_acao']}"):
                    st.session_state.edit_id = row['id_acao']
                    st.rerun()
                
                # BOTÃO EXCLUIR COM CONFIRMAÇÃO
                if c4.button("🗑️", key=f"btn_ex_{row['id_acao']}"):
                    st.session_state.confirmar_excluir = row['id_acao']
                
                # AREA DE CONFIRMAÇÃO
                if st.session_state.confirmar_excluir == row['id_acao']:
                    st.warning(f"Confirmar exclusão de: {row['id_acao']}?")
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

with tab_graficos:
    if not df.empty:
        st.subheader("📊 Indicadores")
        m1, m2, m3 = st.columns(3)
        m1.metric("Ações", len(df))
        m2.metric("Concluídas", len(df[df['status'] == 'Concluído']))
        m3.metric("Total", f"R$ {pd.to_numeric(df['quanto_custa']).sum():,.2f}")
        
        g1, g2 = st.columns(2)
        g1.plotly_chart(px.pie(df, names='status', title="Status"), use_container_width=True)
        g2.plotly_chart(px.bar(df, x='prioridade', y='quanto_custa', title="Investimento por Prioridade"), use_container_width=True)

st.sidebar.button("Logout", on_click=lambda: st.session_state.update({"logado": False}))
