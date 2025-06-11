from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from collections import defaultdict
from io import BytesIO
import pandas as pd
import xlsxwriter
import os

app = Flask(__name__)
app.secret_key = 'chave-secreta'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, 'meubanco.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ Instanciando o banco aqui:
db = SQLAlchemy(app)

class User(db.Model):
    matricula = db.Column(db.String(20), primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(20), default='cliente')
    senha_temporaria = db.Column(db.Boolean, default=True)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    preco = db.Column(db.Float, nullable=False)
    estoque = db.Column(db.Integer, nullable=False)

class Compra(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10), nullable=False)
    produto_nome = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    quantidade = db.Column(db.Integer, nullable=False)
    user_matricula = db.Column(db.String(20), db.ForeignKey('user.matricula'), nullable=False)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        matricula = request.form['matricula']
        senha = request.form['senha']
        user = User.query.filter_by(matricula=matricula).first()
        if user and user.senha == senha:
            session['user'] = user.matricula
            if user.senha_temporaria:
                return redirect(url_for('trocar_senha'))
            return redirect(url_for('admin' if user.tipo == 'admin' else 'client_dashboard'))
        erro = 'Matrícula ou senha inválida'
    return render_template('login.html', erro=erro)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        matricula = request.form['matricula']
        nome = request.form['nome']
        senha = request.form['senha']
        if not User.query.filter_by(matricula=matricula).first():
            novo_user = User(matricula=matricula, nome=nome, senha=senha)
            db.session.add(novo_user)
            db.session.commit()
            return redirect(url_for('login'))
        return 'Matrícula já cadastrada', 400
    return render_template('register.html')

@app.route('/trocar_senha', methods=['GET', 'POST'])
def trocar_senha():
    if 'user' not in session:
        return redirect(url_for('login'))
    erro = None
    user = User.query.get(session['user'])
    if request.method == 'POST':
        nova_senha = request.form['nova_senha']
        confirmar_senha = request.form['confirmar_senha']
        if nova_senha != confirmar_senha:
            erro = 'As senhas não coincidem!'
        else:
            user.senha = nova_senha
            user.senha_temporaria = False
            db.session.commit()
            return redirect(url_for('client_dashboard' if user.tipo == 'cliente' else 'admin'))
    return render_template('trocar_senha.html', erro=erro)

@app.route('/esqueci_senha', methods=['GET', 'POST'])
def esqueci_senha():
    erro = None
    sucesso = None
    if request.method == 'POST':
        matricula = request.form['matricula']
        user = User.query.get(matricula)
        if user:
            user.senha = 'nova123'
            user.senha_temporaria = True
            db.session.commit()
            sucesso = "Uma nova senha foi gerada: nova123. Por favor, altere ao fazer login."
        else:
            erro = "Matrícula não encontrada."
    return render_template('esqueci_senha.html', erro=erro, sucesso=sucesso)

@app.route('/admin')
def admin():
    if session.get('user') != '123456':
        return redirect(url_for('login'))
    data_hoje = datetime.now().strftime('%Y-%m-%d')
    compras_hoje = Compra.query.filter_by(data=data_hoje).all()
    meses = sorted(set(c.data[:7] for c in Compra.query.all()), reverse=True)
    produtos = Produto.query.all()
    users = User.query.all()
    return render_template('admin.html', produtos=produtos, compras_hoje=compras_hoje, users=users, meses=meses)

@app.route('/adicionar_produto', methods=['POST'])
def adicionar_produto():
    if session.get('user') != '123456':
        return redirect(url_for('login'))
    nome = request.form['produto']
    preco = float(request.form['preco'])
    estoque = int(request.form['estoque'])
    novo_produto = Produto(nome=nome, preco=preco, estoque=estoque)
    db.session.add(novo_produto)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/editar_produto/<int:id>', methods=['POST'])
def editar_produto(id):
    novo_nome = request.form['novo_nome']
    novo_preco = float(request.form['novo_preco'])
    novo_estoque = int(request.form['novo_estoque'])

    produto = Produto.query.get(id)
    if produto:
        produto.nome = novo_nome
        produto.preco = novo_preco
        produto.estoque = novo_estoque
        db.session.commit()

    return redirect(url_for('admin'))

@app.route('/deletar_produto/<int:id>', methods=['POST'])
def deletar_produto(id):
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/registrar_venda', methods=['POST'])
def registrar_venda():
    if session.get('user') != '123456':
        return redirect(url_for('login'))
    matricula = request.form['matricula_cliente']
    produto_id = int(request.form['produto_index'])
    quantidade = int(request.form['quantidade'])
    user = User.query.get(matricula)
    produto = Produto.query.get(produto_id)
    if not user or user.tipo != 'cliente':
        return 'Cliente inválido', 400
    if not produto or produto.estoque < quantidade:
        return 'Produto inválido ou estoque insuficiente', 400
    produto.estoque -= quantidade
    valor_total = produto.preco * quantidade
    nova_compra = Compra(data=datetime.now().strftime('%Y-%m-%d'), produto_nome=produto.nome, valor=valor_total, quantidade=quantidade, user_matricula=matricula)
    db.session.add(nova_compra)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/client', methods=['GET', 'POST'])
def client_dashboard():
    user = User.query.get(session.get('user'))
    if not user or user.tipo != 'cliente':
        return redirect(url_for('login'))
    compras_cliente = Compra.query.filter_by(user_matricula=user.matricula).all()
    meses_disponiveis = sorted(set(c.data[:7] for c in compras_cliente), reverse=True)
    mes_selecionado = ''
    gastos = []
    total = 0
    if request.method == 'POST':
        mes_selecionado = request.form['mes']
        for c in compras_cliente:
            if c.data.startswith(mes_selecionado):
                gastos.append(c)
                total += c.valor
    return render_template('client_dashboard.html', gastos=gastos, total=total, meses=meses_disponiveis, mes_selecionado=mes_selecionado)

@app.route('/comprar', methods=['POST'])
def comprar():
    user = User.query.get(session.get('user'))
    if not user or user.tipo != 'cliente':
        return redirect(url_for('login'))
    produto_id = int(request.form['produto_id'])
    produto = Produto.query.get(produto_id)
    if not produto or produto.estoque < 1:
        return 'Produto inválido ou sem estoque', 400
    produto.estoque -= 1
    nova_compra = Compra(data=datetime.now().strftime('%Y-%m-%d'), produto_nome=produto.nome, valor=produto.preco, quantidade=1, user_matricula=user.matricula)
    db.session.add(nova_compra)
    db.session.commit()
    return redirect(url_for('client_dashboard'))

@app.route('/gerar_planilha_gastos', methods=['POST'])
def gerar_planilha_gastos():
    mes = request.form['mes']
    compras_do_mes = Compra.query.filter(Compra.data.startswith(mes)).all()
    totais_por_cliente = {}
    for c in compras_do_mes:
        user = User.query.get(c.user_matricula)
        nome = user.nome if user else 'Desconhecido'
        if c.user_matricula not in totais_por_cliente:
            totais_por_cliente[c.user_matricula] = {'nome': nome, 'total': 0}
        totais_por_cliente[c.user_matricula]['total'] += c.valor

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Relatório')
    bold = workbook.add_format({'bold': True})

    worksheet.write('A1', 'Matrícula', bold)
    worksheet.write('B1', 'Produto', bold)
    worksheet.write('C1', 'Quantidade', bold)
    worksheet.write('D1', 'Valor Total (R$)', bold)
    worksheet.write('E1', 'Data', bold)

    row = 1
    for c in compras_do_mes:
        worksheet.write(row, 0, c.user_matricula)
        worksheet.write(row, 1, c.produto_nome)
        worksheet.write(row, 2, c.quantidade)
        worksheet.write(row, 3, c.valor)
        worksheet.write(row, 4, c.data)
        row += 1

    row += 2
    worksheet.write(row, 0, 'Matrícula', bold)
    worksheet.write(row, 1, 'Nome', bold)
    worksheet.write(row, 2, 'Total Gasto (R$)', bold)
    row += 1

    for matricula, dados in totais_por_cliente.items():
        worksheet.write(row, 0, matricula)
        worksheet.write(row, 1, dados['nome'])
        worksheet.write(row, 2, dados['total'])
        row += 1

    workbook.close()
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'gastos_{mes}.xlsx'
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

with app.app_context():
    db.create_all()

    # Cria admin se não existir
    if not User.query.filter_by(matricula='123456').first():
        admin = User(
            matricula='123456',
            nome='Administrador',
            senha='admin',  # você pode usar hash depois se quiser segurança
            tipo='admin',
            senha_temporaria=True
        )
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)