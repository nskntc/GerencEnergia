from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user
from app.models import UnidadeConsumidora, HistoricoConsumo, Usina, RateioMensal
from sqlalchemy.sql import func
from app import db
from datetime import datetime
import calendar

bp = Blueprint('cliente_routes', __name__)

@bp.route('/dashboard')
@login_required
def cliente_dashboard():
    if not current_user.is_cliente():
        flash('Acesso negado. Somente clientes podem acessar esta página.', 'danger')
        return redirect(url_for('auth_routes.index'))
    
    # Buscar a quantidade total de UCs cadastradas que pertencem ao cliente logado
    total_ucs = UnidadeConsumidora.query.filter_by(cliente_id=current_user.id).count()

    # Economia total devido ao recebimento de créditos de energia
    economia_total = db.session.query(db.func.sum(HistoricoConsumo.credito)).join(UnidadeConsumidora).filter(UnidadeConsumidora.cliente_id == current_user.id).scalar()

    # Se os valores forem None, definir como 0
    if economia_total is None:
        economia_total = 0

    # Buscando as UCs do cliente
    ucs = UnidadeConsumidora.query.filter_by(cliente_id=current_user.id).all()
    
    # Preparando os dados para a tabela
    uc_data = []
    for uc in ucs:
        consumo_total = db.session.query(db.func.sum(HistoricoConsumo.consumo)).filter_by(unidade_consumidora_id=uc.id).scalar()
        if consumo_total is None:
            consumo_total = 0
        
        # Calculando a economia total para a UC
        economia_uc = db.session.query(db.func.sum(HistoricoConsumo.credito)).filter_by(unidade_consumidora_id=uc.id).scalar()
        if economia_uc is None:
            economia_uc = 0
        
        usina = Usina.query.get(uc.usina_id)
        uc_data.append({
            'numero': uc.numero,
            'consumo_total': consumo_total,
            'usina': usina.nome,
            'economia_total': economia_uc
        })

    return render_template('cliente_dashboard.html', 
                           total_unidades=total_ucs, 
                           consumo_total=consumo_total,
                           economia_total=economia_total,
                           uc_data=uc_data)

@bp.route('/consumo_mensal')
@login_required
def consumo_mensal():
    if not current_user.is_cliente():
        return jsonify({'error': 'Acesso negado.'}), 403
    
    # Buscando os dados de consumo mensal do cliente
    consumo_mensal = db.session.query(
        func.strftime('%Y-%m', HistoricoConsumo.data).label('mes'),
        func.sum(HistoricoConsumo.consumo).label('consumo')
    ).join(UnidadeConsumidora).filter(
        UnidadeConsumidora.cliente_id == current_user.id
    ).group_by(
        'mes'
    ).order_by(
        'mes'
    ).all()

    # Preparar os dados para o gráfico
    meses = [calendar.month_name[i] for i in range(1, 13)]
    consumo_por_mes = {mes: 0 for mes in meses}

    for item in consumo_mensal:
        ano_mes = item.mes.split('-')
        ano, mes = int(ano_mes[0]), int(ano_mes[1])
        nome_mes = calendar.month_name[mes]
        consumo_por_mes[nome_mes] = item.consumo

    # Garantir que os dados estejam na ordem cronológica
    consumo_por_mes_ordenado = {mes: consumo_por_mes[mes] for mes in meses}

    return jsonify(consumo_por_mes_ordenado)


@bp.route('/rateio_mensal', methods=['GET', 'POST'])
@login_required
def rateio_mensal():
    # Obtém todas as unidades consumidoras do cliente logado
    unidades_consumidoras = UnidadeConsumidora.query.filter_by(cliente_id=current_user.id).all()
    usinas = {uc.id: Usina.query.get(uc.usina_id) for uc in unidades_consumidoras}

    if request.method == 'POST':
        # Verifica se o cliente já fez rateio neste mês
        hoje = datetime.utcnow().date()
        mes_atual = hoje.strftime('%Y-%m')
        
        # Verifica se já existe um rateio para o mês corrente
        rateio_existente = RateioMensal.query.filter(
            func.strftime('%Y-%m', RateioMensal.data) == mes_atual,
            UnidadeConsumidora.query.filter_by(cliente_id=current_user.id).subquery().c.id == RateioMensal.unidade_consumidora_id
        ).first()
        
        if rateio_existente:
            flash('Você já fez um rateio neste mês. Esses valores não foram salvos no banco de dados.', 'danger')
            return redirect(url_for('cliente_routes.rateio_mensal'))

        # Obtém os dados do formulário
        rateios = []
        total_percentual = 0
        total_energia_disponivel = 0
        
        # Coleta os dados do formulário
        percentuais = request.form.getlist('percentual')
        uc_ids = request.form.getlist('unidade_consumidora_id')
        
        # Verifica se ambos os campos têm o mesmo comprimento
        if len(percentuais) != len(uc_ids):
            flash('Erro ao processar os dados do formulário.', 'danger')
            return redirect(url_for('cliente_routes.cliente_dashboard'))
        
        for percentual, uc_id in zip(percentuais, uc_ids):
            percentual = float(percentual)
            unidade_consumidora = UnidadeConsumidora.query.get(uc_id)
            
            if unidade_consumidora:
                usina_uc = Usina.query.get(unidade_consumidora.usina_id)

                if usina_uc:
                    # Calcular a quantidade de energia rateada com base no percentual
                    energia_rateada = (percentual / 100) * usina_uc.energia_disponivel
                    total_percentual += percentual
                    total_energia_disponivel += energia_rateada

                    # Cria um objeto RateioMensal para cada unidade consumidora
                    rateio = RateioMensal(
                        unidade_consumidora_id=uc_id,
                        usina_id=unidade_consumidora.usina_id,  # Adicione o usina_id aqui
                        data=datetime.utcnow().date(),
                        percentual_rateio=percentual,
                        energia_rateada=energia_rateada
                    )
                    rateios.append(rateio)
                else:
                    flash(f'Usina associada à unidade consumidora {uc_id} não encontrada.', 'danger')
                    return redirect(url_for('cliente_routes.cliente_dashboard'))
            else:
                flash(f'Unidade consumidora com ID {uc_id} não encontrada.', 'danger')
                return redirect(url_for('cliente_routes.cliente_dashboard'))

        if total_percentual > 100:
            flash('A soma dos percentuais deve ser menor ou igual a 100%.', 'danger')
            return redirect(url_for('cliente_routes.cliente_dashboard'))

        # Atualiza o rateio mensal na base de dados
        db.session.bulk_save_objects(rateios)

        # Atualiza a energia disponível das usinas associadas às unidades consumidoras
        for rateio in rateios:
            unidade_consumidora = UnidadeConsumidora.query.get(rateio.unidade_consumidora_id)
            usina = Usina.query.get(unidade_consumidora.usina_id)
            energia_rateada = rateio.energia_rateada
            
            # Atualiza a energia disponível da usina
            usina.energia_disponivel -= energia_rateada

        # Confirma as mudanças no banco de dados
        db.session.commit()

        # Exibe uma mensagem de sucesso e redireciona o usuário
        flash('Rateio realizado com sucesso', 'success')
        return redirect(url_for('cliente_routes.cliente_dashboard'))

    return render_template('rateio_mensal.html', ucs=unidades_consumidoras, usinas=usinas)