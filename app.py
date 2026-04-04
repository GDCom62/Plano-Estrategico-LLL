from flask import Flask, render_template, request, redirect, url_for, session, send_file
import mysql.connector
from datetime import datetime
import io

# Bibliotecas para geração de PDF
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)
app.secret_key = 'chave_mestra_5w2h_segura'

def get_db_connection():
    return mysql.connector.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="sistema_gestao",
        port=3306
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user, pw = request.form['usuario'], request.form['senha']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Credenciais WHERE usuario=%s AND senha=%s", (user, pw))
        if cursor.fetchone():
            session['logado'] = True
            return redirect(url_for('index'))
        conn.close()
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logado', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logado'): return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT A.*, U.nome FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario ORDER BY A.prazo ASC")
    acoes = cursor.fetchall()
    cursor.execute("SELECT * FROM Usuarios")
    usuarios = cursor.fetchall()
    conn.close()
    return render_template('index.html', acoes=acoes, usuarios=usuarios, hoje=datetime.now().date())

@app.route('/salvar', methods=['POST'])
def salvar():
    if not session.get('logado'): return redirect(url_for('login'))
    id_acao = request.form.get('id_acao')
    dados = (request.form['descricao'], request.form['porque'], request.form['onde'], 
             request.form['responsavel'], request.form['prazo'], request.form['como'], 
             request.form['quando_detalhe'], request.form['status'])
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        if id_acao and id_acao.strip() != "":
            sql = "UPDATE Acoes SET descricao_acao=%s, porque=%s, onde=%s, id_responsavel=%s, prazo=%s, como=%s, quando_detalhe=%s, status=%s WHERE id_acao=%s"
            cursor.execute(sql, dados + (id_acao,))
        else:
            sql = "INSERT INTO Acoes (descricao_acao, porque, onde, id_responsavel, prazo, como, quando_detalhe, status) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            cursor.execute(sql, dados)
        conn.commit()
    except Exception as e: print(f"ERRO: {e}")
    finally: conn.close()
    return redirect(url_for('index'))

@app.route('/excluir/<int:id>')
def excluir(id):
    if not session.get('logado'): return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Acoes WHERE id_acao = %s", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/gerar_pdf')
def gerar_pdf():
    if not session.get('logado'): return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT A.*, U.nome FROM Acoes A JOIN Usuarios U ON A.id_responsavel = U.id_usuario ORDER BY A.prazo ASC")
    acoes = cursor.fetchall()
    conn.close()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("PLANO DE AÇÃO ESTRATÉGICO 5W2H", styles['Title']))
    elements.append(Spacer(1, 12))

    data = [["Ação (What)", "Quem", "Prazo", "Status", "Como (How)", "QUANDO (Det)"]]
    for a in acoes:
        data.append([a['descricao_acao'], a['nome'], str(a['prazo']), a['status'], a['como'], a['quando_detalhe']])

    t = Table(data, colWidths=[150, 100, 80, 80, 200, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.navy),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="Plano_5W2H.pdf", mimetype='application/pdf')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
