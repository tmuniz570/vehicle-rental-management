from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from enum import Enum
import os
from sqlalchemy import event
db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='admin', nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.ativo

class MotoStatus(str, Enum):
    AVAILABLE = "Available"
    RENTED = "Rented"
    MAINTENANCE = "Maintenance"
    # Legacy aliases
    DISPONIVEL = "Available"
    ALUGADA = "Rented"
    MANUTENCAO = "Maintenance"

class ContractStatus(str, Enum):
    ACTIVE = "Active"
    DEPOSIT_HOLD = "Deposit_Hold"
    COMPLETED = "Completed"
    # Legacy aliases
    ATIVO = "Active"
    QUARENTENA_DEPOSITO = "Deposit_Hold"
    FINALIZADO = "Completed"

class InspectionType(str, Enum):
    CHECK_OUT = "Check-out"
    CHECK_IN = "Check-in"
    INCIDENT = "Incident"
    # Legacy aliases
    SAIDA = "Check-out"
    ENTRADA = "Check-in"
    OCORRENCIA = "Incident"

class TransactionType(str, Enum):
    RENT = "Rent"
    DEPOSIT = "Deposit"
    FINE = "Fine"
    DAMAGE = "Damage"
    DEPOSIT_REFUND = "Deposit_Refund"
    # Legacy aliases
    ALUGUEL = "Rent"
    DEPOSITO = "Deposit"
    MULTA = "Fine"
    DANO = "Damage"
    DEVOLUCAO_DEPOSITO = "Deposit_Refund"

class TransactionStatus(str, Enum):
    PENDING = "Pending"
    PAID = "Paid"
    CANCELLED = "Cancelled"
    # Legacy aliases
    PENDENTE = "Pending"
    PAGO = "Paid"
    CANCELADO = "Cancelled"

class Client(db.Model):
    __tablename__ = 'clientes'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    endereco = db.Column(db.String(255), nullable=True)
    url_habilitacao = db.Column(db.String(255), nullable=True)
    url_comprovante_endereco = db.Column(db.String(255), nullable=True)
    
    contratos = db.relationship('Contract', backref='cliente', lazy=True)

class Motorcycle(db.Model):
    __tablename__ = 'motos'
    
    placa = db.Column(db.String(10), primary_key=True)
    modelo = db.Column(db.String(100), nullable=False)
    cor = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default=MotoStatus.DISPONIVEL.value, nullable=False)
    
    contratos = db.relationship('Contract', backref='moto', lazy=True)

class Contract(db.Model):
    __tablename__ = 'contratos'
    
    id = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    placa = db.Column(db.String(10), db.ForeignKey('motos.placa'), nullable=False)
    
    data_retirada = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    dia_pagamento_semanal = db.Column(db.Integer, nullable=False) # 0-6 (Segunda-Domingo)
    valor_aluguel_semanal = db.Column(db.Float, nullable=False, default=250.00)
    data_devolucao = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default=ContractStatus.ATIVO.value, nullable=False)
    url_seguro = db.Column(db.String(255), nullable=True)
    url_comprovante_deposito = db.Column(db.String(255), nullable=True)
    
    vistorias = db.relationship('Inspection', backref='contrato', lazy=True)
    transacoes = db.relationship('FinancialTransaction', backref='contrato', lazy=True)

class Inspection(db.Model):
    __tablename__ = 'vistorias'
    
    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contratos.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False) # Saída ou Entrada
    data = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    observacoes = db.Column(db.Text, nullable=True)
    url_fotos = db.Column(db.String(255), nullable=True) # Pode ser JSON array se forem várias fotos

class FinancialTransaction(db.Model):
    __tablename__ = 'financeiro_transacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contratos.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False) # Aluguel, Deposito, Multa, Dano, Devolucao_Deposito
    data_vencimento = db.Column(db.DateTime, nullable=False)
    data_pagamento = db.Column(db.DateTime, nullable=True)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default=TransactionStatus.PENDENTE.value, nullable=False)
    forma_pagamento = db.Column(db.String(50), nullable=True)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()

# --- Garbage Collector (File Cleanup) ---
def delete_file_if_exists(filepath):
    if not filepath: return
    # filepath is like "/static/uploads/file.png"
    if filepath.startswith('/'):
        filepath = filepath.lstrip('/')
    
    # Try to delete from the filesystem relative to the app root
    full_path = os.path.join(os.getcwd(), filepath)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except Exception as e:
            print(f"Error removing file {full_path}: {e}")

@event.listens_for(Client, 'after_delete')
def receive_after_delete_client(mapper, connection, target):
    delete_file_if_exists(target.url_habilitacao)
    delete_file_if_exists(target.url_comprovante_endereco)

@event.listens_for(Contract, 'after_delete')
def receive_after_delete_contract(mapper, connection, target):
    delete_file_if_exists(target.url_seguro)
    delete_file_if_exists(target.url_comprovante_deposito)

@event.listens_for(Inspection, 'after_delete')
def receive_after_delete_inspection(mapper, connection, target):
    if target.url_fotos:
        fotos = target.url_fotos.split(',')
        for f in fotos:
            delete_file_if_exists(f.strip())
