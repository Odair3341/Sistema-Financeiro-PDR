
import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func
import json
import io

# --- Configuração ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
# Use um caminho absoluto para o banco de dados
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'financeiro.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Cria as tabelas no contexto da aplicação ---
with app.app_context():
    db.create_all()

# --- Modelos do Banco de Dados ---

class Cliente(db.Model):
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    servicos = db.relationship('Servico', backref='cliente', lazy=True)
    pagamentos = db.relationship('Pagamento', backref='cliente', lazy=True)

class Servico(db.Model):
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    data_servico = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    veiculo = db.Column(db.String(100), nullable=False)
    placa = db.Column(db.String(20), nullable=False)
    valor_bruto = db.Column(db.Float, nullable=False)
    porcentagem_comissao = db.Column(db.Float, nullable=False)
    observacao = db.Column(db.Text, nullable=True)
    valor_pago = db.Column(db.Float, default=0.0)
    quitado = db.Column(db.Boolean, default=False)
    comissao_recebida = db.Column(db.Float, default=0.0)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('cliente.id'), nullable=False)

class Despesa(db.Model):
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.DateTime, nullable=False)
    pago = db.Column(db.Boolean, default=False)

class Pagamento(db.Model):
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    data_pagamento = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    valor = db.Column(db.Float, nullable=False)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('cliente.id'), nullable=False)


# --- Rotas da Aplicação ---

from sqlalchemy import func

@app.route('/')
def painel():
    # Total a Receber (soma das comissões não recebidas)
    total_a_receber = db.session.query(func.sum(Servico.valor_bruto * (Servico.porcentagem_comissao / 100) - Servico.comissao_recebida)).filter(Servico.comissao_recebida < (Servico.valor_bruto * (Servico.porcentagem_comissao / 100))).scalar() or 0.0

    # Total a Pagar (soma das despesas não pagas)
    total_a_pagar = db.session.query(func.sum(Despesa.valor)).filter(Despesa.pago == False).scalar() or 0.0

    # Total Recebido (soma das comissões já recebidas)
    total_recebido_geral = db.session.query(func.sum(Servico.comissao_recebida)).scalar() or 0.0

    # Saldo (Total de Comissões Recebidas - Total de Despesas)
    total_despesas_geral = db.session.query(func.sum(Despesa.valor)).scalar() or 0.0
    saldo = total_recebido_geral - total_despesas_geral

    return render_template('painel.html', 
                           total_a_receber=total_a_receber, 
                           total_a_pagar=total_a_pagar, 
                           saldo=saldo,
                           total_recebido_geral=total_recebido_geral)

@app.route('/receber_comissao/<int:servico_id>', methods=['POST'])
def receber_comissao(servico_id):
    servico = Servico.query.get_or_404(servico_id)
    valor_receber = float(request.form['valor_receber'])

    comissao_total = servico.valor_bruto * (servico.porcentagem_comissao / 100)
    comissao_restante = comissao_total - servico.comissao_recebida

    if valor_receber <= 0:
        flash('O valor a receber deve ser positivo.', 'danger')
    elif valor_receber > comissao_restante + 0.001: # Adiciona uma pequena tolerância para ponto flutuante
        flash(f'O valor a receber (R$ {valor_receber:.2f}) é maior que o restante da comissão (R$ {comissao_restante:.2f}).', 'warning')
    else:
        servico.comissao_recebida += valor_receber
        db.session.commit()
        flash(f'Comissão de R$ {valor_receber:.2f} registrada com sucesso!', 'success')

    return redirect(url_for('comissoes'))

@app.route('/comissao/resetar/<int:servico_id>', methods=['POST'])
def resetar_comissao(servico_id):
    servico = Servico.query.get_or_404(servico_id)
    servico.comissao_recebida = 0.0
    db.session.commit()
    flash('O registro de comissão recebida para este serviço foi zerado.', 'success')
    return redirect(url_for('comissoes'))

@app.route('/servicos', methods=['GET', 'POST'])
def servicos():
    if request.method == 'POST':
        data_servico = datetime.strptime(request.form['data_servico'], '%Y-%m-%d')
        veiculo = request.form['veiculo']
        placa = request.form['placa']
        cliente_id = request.form['cliente_id']
        valor_bruto = float(request.form['valor_bruto'])
        porcentagem_comissao = float(request.form['porcentagem_comissao'])
        observacao = request.form['observacao']

        novo_servico = Servico(
            data_servico=data_servico,
            veiculo=veiculo,
            placa=placa,
            cliente_id=cliente_id,
            valor_bruto=valor_bruto,
            porcentagem_comissao=porcentagem_comissao,
            observacao=observacao
        )
        db.session.add(novo_servico)
        db.session.commit()
        flash('Serviço adicionado com sucesso!', 'success')
        return redirect(url_for('servicos'))

    todos_servicos = Servico.query.order_by(Servico.data_servico.desc()).all()
    todos_clientes = Cliente.query.order_by(Cliente.nome).all()
    return render_template('servicos.html', servicos=todos_servicos, clientes=todos_clientes)

@app.route('/servico/editar/<int:servico_id>', methods=['GET', 'POST'])
def editar_servico(servico_id):
    servico = Servico.query.get_or_404(servico_id)
    todos_clientes = Cliente.query.order_by(Cliente.nome).all()

    if request.method == 'POST':
        servico.data_servico = datetime.strptime(request.form['data_servico'], '%Y-%m-%d')
        servico.veiculo = request.form['veiculo']
        servico.placa = request.form['placa']
        servico.cliente_id = request.form['cliente_id']
        servico.valor_bruto = float(request.form['valor_bruto'])
        servico.porcentagem_comissao = float(request.form['porcentagem_comissao'])
        servico.observacao = request.form['observacao']
        db.session.commit()
        flash('Serviço atualizado com sucesso!', 'success')
        return redirect(url_for('servicos'))

    return render_template('editar_servico.html', servico=servico, clientes=todos_clientes)

@app.route('/servico/deletar/<int:servico_id>', methods=['POST'])
def deletar_servico(servico_id):
    servico = Servico.query.get_or_404(servico_id)

    # Regra de segurança: não deletar se já houve movimentação financeira
    if servico.valor_pago > 0 or servico.comissao_recebida > 0:
        flash('Este serviço não pode ser deletado pois já possui pagamentos ou comissões registradas.', 'danger')
        return redirect(url_for('servicos'))

    db.session.delete(servico)
    db.session.commit()
    flash('Serviço deletado com sucesso!', 'success')
    return redirect(url_for('servicos'))

@app.route('/clientes', methods=['GET', 'POST'])
def clientes():
    if request.method == 'POST':
        nome_cliente = request.form['nome']
        if nome_cliente:
            if not Cliente.query.filter_by(nome=nome_cliente).first():
                novo_cliente = Cliente(nome=nome_cliente)
                db.session.add(novo_cliente)
                db.session.commit()
                flash('Cliente adicionado com sucesso!', 'success')
            else:
                flash('Este cliente já existe.', 'warning')
        else:
            flash('O nome do cliente não pode ser vazio.', 'danger')
        return redirect(url_for('clientes'))
    
    todos_clientes = Cliente.query.order_by(Cliente.nome).all()
    return render_template('clientes.html', clientes=todos_clientes)

@app.route('/despesas', methods=['GET', 'POST'])
def despesas():
    if request.method == 'POST':
        descricao = request.form['descricao']
        valor = float(request.form['valor'])
        data_vencimento = datetime.strptime(request.form['data_vencimento'], '%Y-%m-%d')

        nova_despesa = Despesa(
            descricao=descricao,
            valor=valor,
            data_vencimento=data_vencimento
        )
        db.session.add(nova_despesa)
        db.session.commit()
        flash('Despesa adicionada com sucesso!', 'success')
        return redirect(url_for('despesas'))

    todas_despesas = Despesa.query.order_by(Despesa.data_vencimento.asc()).all()
    return render_template('despesas.html', despesas=todas_despesas)

@app.route('/comissoes')
def comissoes():
    todos_servicos = Servico.query.order_by(Servico.data_servico.asc()).all()
    return render_template('comissoes.html', servicos=todos_servicos)

@app.route('/relatorios')
def relatorios():
    return render_template('relatorios.html')

@app.route('/backup')
def backup():
    return render_template('backup.html')



@app.route('/relatorio/comissoes', methods=['GET', 'POST'])
def relatorio_comissoes():
    # Filtra serviços que geram comissão
    servicos_comissao = Servico.query.filter(Servico.porcentagem_comissao > 0).order_by(Servico.data_servico.asc()).all()

    transacoes_comissao = []
    for s in servicos_comissao:
        comissao_total_servico = s.valor_bruto * (s.porcentagem_comissao / 100)
        # Adiciona a comissão total como um débito (a receber)
        transacoes_comissao.append({'data': s.data_servico, 'tipo': 'Comissão a Receber', 'descricao': f'Comissão de {s.cliente.nome} - {s.veiculo} ({s.placa})', 'valor': comissao_total_servico, 'debito_credito': 'debito', 'comissao_recebida': s.comissao_recebida})
        # Adiciona o valor já recebido como um crédito
        if s.comissao_recebida > 0:
            transacoes_comissao.append({'data': s.data_servico, 'tipo': 'Comissão Recebida', 'descricao': f'Recebimento de comissão - {s.cliente.nome} ({s.placa})', 'valor': s.comissao_recebida, 'debito_credito': 'credito', 'comissao_recebida': s.comissao_recebida})
    
    transacoes_comissao.sort(key=lambda x: x['data'])

    return render_template('relatorio_comissoes_extrato.html', transacoes=transacoes_comissao)




@app.route('/cliente/<int:cliente_id>')
def cliente_detalhe(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    servicos_cliente = Servico.query.filter_by(cliente_id=cliente_id).order_by(Servico.data_servico.asc()).all()
    return render_template('cliente_detalhe.html', cliente=cliente, servicos=servicos_cliente)

@app.route('/pagamento/cliente/<int:cliente_id>', methods=['POST'])
def registrar_pagamento(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    valor_pago = float(request.form['valor'])

    if valor_pago <= 0:
        flash('O valor do pagamento deve ser positivo.', 'danger')
        return redirect(url_for('cliente_detalhe', cliente_id=cliente_id))

    # Registrar o pagamento
    novo_pagamento = Pagamento(valor=valor_pago, cliente_id=cliente_id)
    db.session.add(novo_pagamento)

    # Abater o valor nos serviços em aberto (cronologicamente)
    servicos_em_aberto = Servico.query.filter_by(cliente_id=cliente_id, quitado=False).order_by(Servico.data_servico.asc()).all()
    
    valor_restante_pagamento = valor_pago

    for servico in servicos_em_aberto:
        if valor_restante_pagamento == 0:
            break

        valor_devido_servico = servico.valor_bruto - servico.valor_pago
        
        if valor_restante_pagamento >= valor_devido_servico:
            servico.valor_pago += valor_devido_servico
            servico.quitado = True
            valor_restante_pagamento -= valor_devido_servico
        else:
            servico.valor_pago += valor_restante_pagamento
            valor_restante_pagamento = 0

    db.session.commit()
    flash(f'Pagamento de R$ {valor_pago:.2f} registrado com sucesso!', 'success')
    return redirect(url_for('cliente_detalhe', cliente_id=cliente_id))




@app.route('/backup/export')
def export_data():
    data = {
        'clientes': [],
        'servicos': [],
        'despesas': [],
        'pagamentos': []
    }

    for cliente in Cliente.query.all():
        data['clientes'].append({'id': cliente.id, 'nome': cliente.nome})

    for servico in Servico.query.all():
        data['servicos'].append({
            'id': servico.id,
            'data_servico': servico.data_servico.isoformat(),
            'veiculo': servico.veiculo,
            'placa': servico.placa,
            'valor_bruto': servico.valor_bruto,
            'porcentagem_comissao': servico.porcentagem_comissao,
            'observacao': servico.observacao,
            'valor_pago': servico.valor_pago,
            'quitado': servico.quitado,
            'comissao_recebida': servico.comissao_recebida,
            'cliente_id': servico.cliente_id
        })

    for despesa in Despesa.query.all():
        data['despesas'].append({
            'id': despesa.id,
            'descricao': despesa.descricao,
            'valor': despesa.valor,
            'data_vencimento': despesa.data_vencimento.isoformat(),
            'pago': despesa.pago
        })

    for pagamento in Pagamento.query.all():
        data['pagamentos'].append({
            'id': pagamento.id,
            'data_pagamento': pagamento.data_pagamento.isoformat(),
            'valor': pagamento.valor,
            'cliente_id': pagamento.cliente_id
        })

    json_data = json.dumps(data, indent=4, ensure_ascii=False)
    buffer = io.BytesIO(json_data.encode('utf-8'))
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name='financeiro_backup.json', mimetype='application/json')

@app.route('/backup/import', methods=['POST'])
def import_data():
    if 'backup_file' not in request.files:
        flash('Nenhum arquivo selecionado.', 'danger')
        return redirect(url_for('backup'))

    file = request.files['backup_file']

    if file.filename == '':
        flash('Nenhum arquivo selecionado.', 'danger')
        return redirect(url_for('backup'))

    if file and file.filename.endswith('.json'):
        try:
            json_data = json.load(file)

            # Apagar dados existentes (ordem inversa de dependência)
            db.session.query(Pagamento).delete()
            db.session.query(Servico).delete()
            db.session.query(Despesa).delete()
            db.session.query(Cliente).delete()
            db.session.commit()

            # Importar clientes e criar mapeamento de IDs
            old_to_new_client_id_map = {}
            for item in json_data.get('clientes', []):
                # Explicitamente define o ID do cliente com o ID do backup JSON
                cliente = Cliente(id=item['id'], nome=item['nome'])
                db.session.add(cliente)
                db.session.flush() # Garante que o ID seja gerado/atribuído antes do commit final
                old_to_new_client_id_map[item['id']] = cliente.id
            db.session.commit()

            # Importar despesas
            for item in json_data.get('despesas', []):
                despesa = Despesa(
                    descricao=item['descricao'],
                    valor=item['valor'],
                    data_vencimento=datetime.fromisoformat(item['data_vencimento']),
                    pago=item['pago']
                )
                db.session.add(despesa)
            db.session.commit()

            # Importar serviços
            for item in json_data.get('servicos', []):
                original_cliente_id = item.get('cliente_id') or item.get('clienteId')
                if original_cliente_id is None:
                    print(f"Aviso: cliente_id ou clienteId não encontrado para o serviço. Pulando serviço.")
                    continue
                new_cliente_id = old_to_new_client_id_map.get(original_cliente_id)
                if new_cliente_id is None:
                    print(f"Aviso: cliente_id {original_cliente_id} não encontrado no mapeamento. Pulando serviço.")
                    continue
                
                data_servico_str = item.get('data_servico') or item.get('data')
                if data_servico_str is None:
                    print(f"Aviso: data_servico ou data não encontrada para o serviço. Pulando serviço.")
                    continue

                valor_bruto_val = item.get('valor_bruto') or item.get('valorBruto')
                if valor_bruto_val is None:
                    print(f"Aviso: valor_bruto ou valorBruto não encontrado para o serviço. Pulando serviço.")
                    continue

                porcentagem_comissao_val = item.get('porcentagem_comissao') or item.get('porcentagem')
                if porcentagem_comissao_val is None:
                    print(f"Aviso: porcentagem_comissao ou porcentagem não encontrada para o serviço. Pulando serviço.")
                    continue

                servico = Servico(
                    data_servico=datetime.fromisoformat(data_servico_str),
                    veiculo=item['veiculo'],
                    placa=item['placa'],
                    valor_bruto=float(valor_bruto_val),
                    porcentagem_comissao=float(porcentagem_comissao_val),
                    observacao=item.get('observacao', ''),
                    valor_pago=item.get('valor_pago', 0.0),
                    quitado=item.get('quitado', False),
                    comissao_recebida=item.get('comissao_recebida', 0.0),
                    cliente_id=new_cliente_id
                )
                db.session.add(servico)
            db.session.commit()

            # Importar pagamentos
            for item in json_data.get('pagamentos', []):
                original_cliente_id = item.get('cliente_id') or item.get('clienteId')
                if original_cliente_id is None:
                    print(f"Aviso: cliente_id ou clienteId não encontrado para o pagamento. Pulando pagamento.")
                    continue
                new_cliente_id = old_to_new_client_id_map.get(original_cliente_id)
                if new_cliente_id is None:
                    print(f"Aviso: cliente_id {original_cliente_id} não encontrado no mapeamento. Pulando pagamento.")
                    continue
                
                data_pagamento_str = item.get('data_pagamento') or item.get('data')
                if data_pagamento_str is None:
                    print(f"Aviso: data_pagamento ou data não encontrada para o pagamento. Pulando pagamento.")
                    continue

                pagamento = Pagamento(
                    data_pagamento=datetime.fromisoformat(data_pagamento_str),
                    valor=item['valor'],
                    cliente_id=new_cliente_id
                )
                db.session.add(pagamento)
            db.session.commit()

            flash('Dados importados com sucesso!', 'success')

        except json.JSONDecodeError:
            flash('Erro ao ler o arquivo JSON. Verifique se o formato está correto.', 'danger')
        except Exception as e:
            flash(f'Erro ao importar dados: {e}', 'danger')
    else:
        flash('Formato de arquivo inválido. Por favor, selecione um arquivo JSON.', 'danger')

    return redirect(url_for('backup'))





