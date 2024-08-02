from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from app.models import UnidadeConsumidora, HistoricoConsumo, Usina, RateioMensal, Usuario
from sqlalchemy import func
from app import db
from datetime import datetime, timedelta
import calendar
from collections import defaultdict

bp = Blueprint('admin_routes', __name__)

@bp.route('/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin():
        flash('Acesso negado. Somente administradores podem acessar esta página.', 'danger')
        return redirect(url_for('auth_routes.index'))

    # Obtém todos os clientes
    clientes = Usuario.query.filter_by(role='cliente').all()

    dados_clientes = []

    for cliente in clientes:
        # Obtenha todas as unidades consumidoras do cliente
        unidades_consumidoras = UnidadeConsumidora.query.filter_by(cliente_id=cliente.id).all()

        # Obtenha o histórico de consumo para cada unidade consumidora
        historico_consumo = defaultdict(list)
        for uc in unidades_consumidoras:
            consumos = HistoricoConsumo.query.filter_by(unidade_consumidora_id=uc.id).all()
            for consumo in consumos:
                historico_consumo[uc.id].append(consumo)

        # Obtenha as usinas associadas a cada unidade consumidora
        usinas = {uc.id: Usina.query.get(uc.usina_id) for uc in unidades_consumidoras}

        # Calcule o total de energia necessária para cada cliente
        total_energia_necessaria = 0
        for uc in unidades_consumidoras:
            consumos = HistoricoConsumo.query.filter_by(unidade_consumidora_id=uc.id).all()
            if consumos:
                total_consumo = sum(c.consumo for c in consumos)
                num_meses = len(consumos)
                media_mensal = total_consumo / num_meses
                margem_segura = 0.1  # Exemplo de margem segura de 10%
                total_energia_necessaria += (media_mensal / num_meses) * (1 + margem_segura)

        dados_clientes.append({
            'cliente': cliente,
            'unidades_consumidoras': unidades_consumidoras,
            'historico_consumo': historico_consumo,
            'usinas': usinas,
            'total_energia_necessaria': total_energia_necessaria
        })

    # Obtém todas as usinas
    usinas = Usina.query.all()

    # Cria uma lista de dados para passar para o template
    dados_usinas = []
    for usina in usinas:
        # Total de energia consumida para a usina
        total_consumido = sum(
            hc.consumo for uc in usina.unidades_consumidoras for hc in uc.consumos
        )
        percentual_utilizado = (total_consumido / usina.capacidade_total) * 100 if usina.capacidade_total > 0 else 0
        percentual_disponivel = (usina.energia_disponivel / usina.capacidade_total) * 100 if usina.capacidade_total > 0 else 0

        dados_usinas.append({
            'nome': usina.nome,
            'capacidade_total': usina.capacidade_total,
            'energia_disponivel': usina.energia_disponivel,
            'total_consumido': total_consumido,
            'percentual_utilizado': percentual_utilizado,
            'percentual_disponivel': percentual_disponivel
        })

        # Obtém todas as unidades consumidoras
        unidades_consumidoras = UnidadeConsumidora.query.all()

        # Define o número de meses a ser considerado
        num_meses = 12
        hoje = datetime.utcnow()
        datas = [(hoje - timedelta(days=i*30)).strftime('%Y-%m') for i in range(num_meses)]
        datas.sort()

        consumo_por_mes = defaultdict(float)
        geracao_por_mes = defaultdict(float)

    # Obtém todas as unidades consumidoras e calcula o consumo por mês
    unidades_consumidoras = UnidadeConsumidora.query.all()
    for uc in unidades_consumidoras:
        consumos = HistoricoConsumo.query.filter_by(unidade_consumidora_id=uc.id).all()
        for consumo in consumos:
            mes_ano = consumo.data.strftime('%Y-%m')
            if mes_ano in datas:
                consumo_por_mes[mes_ano] += consumo.consumo

    # Pega a capacidade total de todas as usinas
    capacidade_total = db.session.query(func.sum(Usina.capacidade_total)).scalar()
    capacidade_disponivel = capacidade_total

    # Calcula a geração por mês
    for mes_ano in datas:
        consumo_mes = consumo_por_mes.get(mes_ano, 0)
        if consumo_mes > 0:
            geracao_por_mes[mes_ano] = capacidade_disponivel - consumo_mes
            capacidade_disponivel -= consumo_mes

    # Converte os dicts para listas de valores e labels
    consumo_list = [consumo_por_mes.get(data, 0) for data in datas]
    geracao_list = [geracao_por_mes.get(data, 0) for data in datas]

    print(geracao_list)

    print(consumo_list)
    return render_template('admin_dashboard.html', dados_clientes=dados_clientes, 
                                                    usinas=dados_usinas,
                                                    datas=datas,
                                                    consumo=consumo_list,
                                                    geracao=geracao_list)

@bp.route('/cadastro_uc', methods=['GET', 'POST'])
@login_required
def cadastro_uc():
    if not current_user.is_admin():
        flash('Acesso negado. Somente administradores podem acessar esta página.', 'danger')
        return redirect(url_for('auth_routes.index'))
    
    if request.method == 'POST':
        numero = request.form['numero']
        endereco = request.form['endereco']
        cliente_id = request.form['cliente_id']
        usina_id = request.form['usina_id']
        
        # Verifica se o número da unidade consumidora já existe
        if UnidadeConsumidora.query.filter_by(numero=numero).first():
            flash('Número da unidade consumidora já existe. Escolha um número diferente.', 'danger')
            return redirect(url_for('admin_routes.cadastro_uc'))
        
        # Cria a nova unidade consumidora
        nova_uc = UnidadeConsumidora(numero=numero, endereco=endereco, cliente_id=cliente_id, usina_id=usina_id)
        db.session.add(nova_uc)
        db.session.commit()
        
        # Adiciona o histórico de consumo
        datas = request.form.getlist('data')
        consumos = request.form.getlist('consumo')
        creditos = request.form.getlist('credito')

        total_consumo = 0
        for data, consumo, credito in zip(datas, consumos, creditos):
            data_obj = datetime.strptime(data, '%Y-%m-%d').date()  # Converte string para objeto date
            novo_historico = HistoricoConsumo(
                unidade_consumidora_id=nova_uc.id,
                data=data_obj,
                consumo=float(consumo),
                credito=float(credito)
            )
            db.session.add(novo_historico)
            total_consumo += float(consumo)
        
        db.session.commit()
        
        # Atualiza a energia disponível da usina
        usina = Usina.query.get(usina_id)
        usina.energia_disponivel -= total_consumo
        db.session.commit()

        flash('Unidade Consumidora cadastrada com sucesso!', 'success')
        return redirect(url_for('admin_routes.admin_dashboard'))

    # Obtém todos os clientes e usinas para o formulário de cadastro
    clientes = Usuario.query.filter_by(role='cliente').all()
    usinas = Usina.query.all()

    return render_template('cadastro_uc.html', clientes=clientes, usinas=usinas)