# No topo do main.py
import pandas as pd
from io import BytesIO
from flask import send_file
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
from collections import defaultdict
import xlsxwriter
    
app = Flask(__name__)
app.secret_key = 'chave-secreta'
    
    # Usuários e produtos armazenados em memória
users = {
        '123456': {'nome': 'Administrador', 'senha': 'admin', 'tipo': 'admin'}
    }
    
produtos = []  # Cada produto é dict: {'nome', 'preco', 'estoque'}
compras = defaultdict(list)  # {matricula: [(data, produto, valor, quantidade)]}
    
    
@app.route('/')
def index():
        return redirect(url_for('login'))
    
    
@app.route('/login', methods=['GET', 'POST'])
def login():
        erro = None
        if request.method == 'POST':
            matricula = request.form['matricula']
            senha = request.form['senha']
            user = users.get(matricula)
            if user and user['senha'] == senha:
                session['user'] = matricula
                if user.get('senha_temporaria'):
                    return redirect(url_for('trocar_senha'))
                return redirect(url_for('admin' if user['tipo'] == 'admin' else 'client_dashboard'))
            erro = 'Matrícula ou senha inválida'
        return render_template('login.html', erro=erro)

    
    
@app.route('/register', methods=['GET', 'POST'])
def register():
        if request.method == 'POST':
            matricula = request.form['matricula']
            nome = request.form['nome']
            senha = request.form['senha']
            if matricula not in users:
                users[matricula] = {'nome': nome, 'senha': senha, 'tipo': 'cliente', 'senha_temporaria': True}
                return redirect(url_for('login'))
            return 'Matrícula já cadastrada', 400
        return render_template('register.html')

@app.route('/trocar_senha', methods=['GET', 'POST'])
def trocar_senha():
    if 'user' not in session:
        return redirect(url_for('login'))

    erro = None
    if request.method == 'POST':
        nova_senha = request.form['nova_senha']
        confirmar_senha = request.form['confirmar_senha']

        if nova_senha != confirmar_senha:
            erro = 'As senhas não coincidem!'
        else:
            users[session['user']]['senha'] = nova_senha
            users[session['user']]['senha_temporaria'] = False
            return redirect(url_for('client_dashboard' if users[session['user']]['tipo'] == 'cliente' else 'admin'))

    return render_template('trocar_senha.html', erro=erro)

@app.route('/esqueci_senha', methods=['GET', 'POST'])
def esqueci_senha():
    erro = None
    sucesso = None
    if request.method == 'POST':
        matricula = request.form['matricula']
        if matricula in users:
            users[matricula]['senha'] = 'nova123'
            users[matricula]['senha_temporaria'] = True
            sucesso = "Uma nova senha foi gerada: nova123. Por favor, altere ao fazer login."
        else:
            erro = "Matrícula não encontrada."
    return render_template('esqueci_senha.html', erro=erro, sucesso=sucesso)
    
    
@app.route('/admin')
def admin():
    if session.get('user') != '123456':
        return redirect(url_for('login'))

    data_hoje = datetime.now().strftime('%Y-%m-%d')
    compras_hoje = []
    for mat in compras:
        for c in compras[mat]:
            if c[0] == data_hoje:
                compras_hoje.append({
                    'matricula': mat,
                    'produto': c[1],
                    'valor_total': c[2],
                    'quantidade': c[3],
                    'data': c[0]
                })

    # Capturar todos os meses com compras
    meses = sorted(
        {c[0][:7] for compras_cliente in compras.values() for c in compras_cliente},
        reverse=True
    )

    return render_template('admin.html', produtos=produtos, compras_hoje=compras_hoje, users=users, meses=meses)
    
@app.route('/adicionar_produto', methods=['POST'])
def adicionar_produto():
        if session.get('user') != '123456':
            return redirect(url_for('login'))
        nome = request.form['produto']
        preco = float(request.form['preco'])
        estoque = int(request.form['estoque'])
        produtos.append({'nome': nome, 'preco': preco, 'estoque': estoque})
        return redirect(url_for('admin'))
    
    
@app.route('/editar_produto/<int:index>', methods=['POST'])
def editar_produto(index):
        if session.get('user') != '123456':
            return redirect(url_for('login'))
    
        produto = produtos[index]
        novo_nome = request.form.get('novo_nome')
        novo_preco = request.form.get('novo_preco')
        novo_estoque = request.form.get('novo_estoque')
    
        if novo_nome:
            produto['nome'] = novo_nome
        if novo_preco:
            produto['preco'] = float(novo_preco)
        if novo_estoque:
            produto['estoque'] = int(novo_estoque)
        return redirect(url_for('admin'))
    
    
@app.route('/deletar_produto/<int:index>', methods=['POST'])
def deletar_produto(index):
        if session.get('user') != '123456':
            return redirect(url_for('login'))
        produtos.pop(index)
        return redirect(url_for('admin'))
    
    
@app.route('/registrar_venda', methods=['POST'])
def registrar_venda():
        if session.get('user') != '123456':
            return redirect(url_for('login'))
    
        matricula_cliente = request.form['matricula_cliente']
        produto_index = int(request.form['produto_index'])
        quantidade = int(request.form['quantidade'])
    
        if matricula_cliente not in users or users[matricula_cliente]['tipo'] != 'cliente':
            return "Cliente inválido", 400
    
        if produto_index < 0 or produto_index >= len(produtos):
            return "Produto inválido", 400
    
        produto = produtos[produto_index]
        if produto['estoque'] < quantidade:
            return "Estoque insuficiente", 400
    
        produto['estoque'] -= quantidade
        valor_total = produto['preco'] * quantidade
        data = datetime.now().strftime('%Y-%m-%d')
    
        compras[matricula_cliente].append((data, produto['nome'], valor_total, quantidade))
    
        return redirect(url_for('admin'))
    
    
@app.route('/client', methods=['GET', 'POST'])
def client_dashboard():
        user = users.get(session.get('user'))
        if not user or user['tipo'] != 'cliente':
            return redirect(url_for('login'))
    
        matricula = session['user']
        gastos = []
        total = 0
    
        # Identificar meses disponíveis com compras
        meses_disponiveis = sorted(
            set(compra[0][:7] for compra in compras[matricula]), reverse=True
        )
    
        mes_selecionado = ''
        if request.method == 'POST':
            mes_selecionado = request.form['mes']
            for compra in compras[matricula]:
                if compra[0].startswith(mes_selecionado):
                    gastos.append(compra)
                    total += compra[2]
    
        return render_template(
            'client_dashboard.html',
            gastos=gastos,
            total=total,
            meses=meses_disponiveis,
            mes_selecionado=mes_selecionado
        )
    
    
    
@app.route('/comprar', methods=['POST'])
def comprar():
        if 'user' not in session:
            return redirect(url_for('login'))
    
        user = users.get(session['user'])
        if user['tipo'] != 'cliente':
            return 'Apenas clientes podem comprar', 403
    
        produto_id = int(request.form['produto_id'])
        if produto_id < 0 or produto_id >= len(produtos):
            return "Produto inválido", 400
    
        produto = produtos[produto_id]
        if produto['estoque'] < 1:
            return "Produto sem estoque", 400
    
        produto['estoque'] -= 1
        compras[session['user']].append((datetime.now().strftime('%Y-%m-%d'), produto['nome'], produto['preco'], 1))
    
        return redirect(url_for('client_dashboard'))

@app.route('/gerar_planilha_gastos', methods=['POST'])
def gerar_planilha_gastos():
    mes = request.form['mes']

    # Filtrar as compras do mês selecionado corretamente
    compras_do_mes = []
    for matricula, lista_compras in compras.items():
        for c in lista_compras:
            if c[0].startswith(mes):
                compras_do_mes.append({
                    'matricula': matricula,
                    'produto': c[1],
                    'valor_total': c[2],
                    'quantidade': c[3],
                    'data': c[0]
                })

    # Criar dicionário com total por cliente
    totais_por_cliente = {}
    for c in compras_do_mes:
        matricula = c['matricula']
        nome = users.get(matricula, {}).get('nome', 'Desconhecido')
        if matricula not in totais_por_cliente:
            totais_por_cliente[matricula] = {'nome': nome, 'total': 0}
        totais_por_cliente[matricula]['total'] += c['valor_total']

    # Criar planilha Excel
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Relatório')

    bold = workbook.add_format({'bold': True})

    # Cabeçalho de compras
    worksheet.write('A1', 'Matrícula', bold)
    worksheet.write('B1', 'Produto', bold)
    worksheet.write('C1', 'Quantidade', bold)
    worksheet.write('D1', 'Valor Total (R$)', bold)
    worksheet.write('E1', 'Data', bold)

    row = 1
    for c in compras_do_mes:
        worksheet.write(row, 0, c['matricula'])
        worksheet.write(row, 1, c['produto'])
        worksheet.write(row, 2, c['quantidade'])
        worksheet.write(row, 3, c['valor_total'])
        worksheet.write(row, 4, c['data'])
        row += 1

    # Cabeçalho da seção total por cliente
    row += 2  # Espaço entre as tabelas
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
    
    
if __name__ == '__main__':
        app.run(debug=True)
    