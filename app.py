import streamlit as st
import mysql.connector
import pandas as pd
from datetime import datetime

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Sistema 5W2H", layout="wide")

# FUNÇÃO DE CONEXÃO ÚNICA (Abre e fecha em cada operação para não travar)
def executar_db(sql, params=None, retorno=True):
    try:
               config = {
            'host': st.secrets["DB_HOST"],
            'user': st.secrets["DB_USER"],
            'password': st.secrets["DB_PASSWORD"],
            'database': st.secrets["DB_NAME"],
            'port': int(st.secrets["DB_PORT"]),
            'use_pure': True,
            'ssl_disabled': True,  # Tente mudar para True para testar o travamento
            'connect_timeout': 5    # Diminuímos o tempo para ele "desistir" logo e mostrar erro se falhar
        }

        }
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params or ())
        
        if retorno:
            resultado = cursor.fetchall()
            cursor.close()
            conn.close()
            return resultado
        else:
            conn.commit()
            cursor.close()
            conn.close()
            return True
    except Exception as e:
        st.error(f"Erro no Banco de Dados: {e}")
        return None

# --- CONTROLE DE SESSÃO ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

# --- TELA DE LOGIN ---
if not st.session_state['logado']:
    st.title("🔐 Login - Gestão 5W2H")
    with st.form("login"):
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            # Busca simples apenas na tabela de credenciais
            check = executar_db("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (u, s))
            if check:
                st.session_state['logado'] = True
                st.rerun()
            else:
                st.error("Dados inválidos.")
    st.stop()

# --- DASHBOARD (SÓ CARREGA SE LOGADO) ---
st.title("📋 Painel de Ações 5W2H")
if st.sidebar.button("Sair"):
    st.session_state['logado'] = False
    st.rerun()

# 1. Carregar Usuários para o formulário
res_usuarios = executar_db("SELECT id_usuario, nome FROM Usuarios")
dict_users = {user['nome']: user['id_usuario'] for user in res_usuarios} if res_usuarios else {}

# 2. Formulário de Cadastro
with st.expander("➕ Adicionar Nova Ação"):
    if not dict_users:
        st.warning("Cadastre usuários no banco de dados primeiro.")
    else:
        with st.form("form_add"):
            c1, c2 = st.columns(2)
            what = c1.text_input("O que (Ação)?")
            who = c2.selectbox("Responsável", list(dict_users.keys()))
            prazo = c2.date_input("Prazo")
            status = c2.selectbox("Status", ["Pendente", "Em Andamento", "Concluído"])
            
            if st.form_submit_button("Salvar"):
                sql_ins = "INSERT INTO Acoes (descricao_acao, id_responsavel, prazo, status) VALUES (%s, %s, %s, %s)"
                executar_db(sql_ins, (what, dict_users[who], prazo, status), retorno=False)
                st.success("Salvo!")
                st.rerun()

# 3. Listagem das Ações (Onde costuma travar)
st.subheader("Lista de Tarefas")
try:
    # SQL simples com JOIN
    dados_acoes = executar_db("""
        SELECT A.id_acao, A.descricao_acao, U.nome as responsavel, A.prazo, A.status 
        FROM Acoes A 
        JOIN Usuarios U ON A.id_responsavel = U.id_usuario
        ORDER BY A.prazo ASC
    """)

    if dados_acoes:
        for acao in dados_acoes:
            with st.container():
                col_txt, col_del = st.columns([0.85, 0.15])
                with col_txt:
                    st.write(f"**{acao['descricao_acao']}** - {acao['responsavel']} ({acao['prazo']}) | `{acao['status']}`")
                with col_del:
                    if st.button("🗑️", key=f"del_{acao['id_acao']}"):
                        executar_db("DELETE FROM Acoes WHERE id_acao=%s", (acao['id_acao'],), retorno=False)
                        st.rerun()
                st.divider()
    else:
        st.info("Nenhuma ação cadastrada.")

except Exception as e:
    st.error("Não foi possível carregar a lista de ações.")
