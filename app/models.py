from flask_login import UserMixin
from datetime import datetime
from . import db

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='cliente')
    unidades_consumidoras = db.relationship('UnidadeConsumidora', backref='cliente', lazy=True)

    def is_admin(self):
        return self.role == 'admin'
    
    def is_cliente(self):
        return self.role == 'cliente'

class Usina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    capacidade_total = db.Column(db.Float, nullable=False)
    energia_disponivel = db.Column(db.Float, nullable=False)
    unidades_consumidoras = db.relationship('UnidadeConsumidora', backref='usina', lazy=True)

class UnidadeConsumidora(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(100), unique=True, nullable=False)
    endereco = db.Column(db.String(250), nullable=False)
    cliente_id = db.Column(db.Integer, db.ForeignKey('usuario.id', name='fk_unidade_consumidora_usuario'), nullable=False)
    usina_id = db.Column(db.Integer, db.ForeignKey('usina.id', name='fk_unidade_consumidora_usina'), nullable=False)
    consumos = db.relationship('HistoricoConsumo', backref='unidade_consumidora', lazy=True)

class HistoricoConsumo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unidade_consumidora_id = db.Column(db.Integer, db.ForeignKey('unidade_consumidora.id', name='fk_historico_consumo_unidade_consumidora'), nullable=False)
    data = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    consumo = db.Column(db.Float, nullable=False)
    credito = db.Column(db.Float, nullable=True)

class RateioMensal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unidade_consumidora_id = db.Column(db.Integer, db.ForeignKey('unidade_consumidora.id', name='fk_rateio_mensal_unidade_consumidora'), nullable=False)
    usina_id = db.Column(db.Integer, db.ForeignKey('usina.id', name='fk_rateio_mensal_usina'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    percentual_rateio = db.Column(db.Float, nullable=False)
    energia_rateada = db.Column(db.Float, nullable=False)
    
    unidade_consumidora = db.relationship('UnidadeConsumidora', backref='rateios')
    usina = db.relationship('Usina', backref='rateios')