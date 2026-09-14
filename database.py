from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from enum import Enum
import os
import sqlite3
from sqlalchemy import event, inspect
from sqlalchemy.engine import Engine

db = SQLAlchemy()

# Enable WAL mode, fast synchronization, and enforce foreign keys on SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
            cursor.execute("PRAGMA foreign_keys = ON;")
        finally:
            cursor.close()

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
    nome = db.Column(db.String(100), nullable=False, index=True)
    telefone = db.Column(db.String(20), nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    endereco = db.Column(db.String(255), nullable=True)
    url_habilitacao = db.Column(db.String(255), nullable=True)
    url_habilitacao_verso = db.Column(db.String(255), nullable=True)
    url_cbt = db.Column(db.String(255), nullable=True)
    url_comprovante_endereco = db.Column(db.String(255), nullable=True)
    
    contratos = db.relationship('Contract', backref='cliente', lazy=True)

class Motorcycle(db.Model):
    __tablename__ = 'motos'
    
    placa = db.Column(db.String(10), primary_key=True)
    modelo = db.Column(db.String(100), nullable=False)
    cor = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), default=MotoStatus.DISPONIVEL.value, nullable=False, index=True)
    vencimento_mot = db.Column(db.Date, nullable=True, index=True)
    vencimento_tax = db.Column(db.Date, nullable=True, index=True)
    
    contratos = db.relationship('Contract', backref='moto', lazy=True)

class Contract(db.Model):
    __tablename__ = 'contratos'
    
    id = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False, index=True)
    placa = db.Column(db.String(10), db.ForeignKey('motos.placa'), nullable=False, index=True)
    
    data_retirada = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    dia_pagamento_semanal = db.Column(db.Integer, nullable=False) # 0-6 (Segunda-Domingo)
    valor_aluguel_semanal = db.Column(db.Float, nullable=False, default=250.00)
    data_devolucao = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default=ContractStatus.ATIVO.value, nullable=False, index=True)
    url_seguro = db.Column(db.String(255), nullable=True)
    url_comprovante_deposito = db.Column(db.String(255), nullable=True)
    criado_por_nome = db.Column(db.String(100), nullable=True)
    
    # 15-Day Insurance Compliance (askMID Verification)
    data_ultima_checagem_seguro = db.Column(db.Date, nullable=True)
    status_seguro = db.Column(db.String(20), default='Valid', nullable=False) # Valid, Cancelled
    seguro_verificado_por = db.Column(db.String(100), nullable=True)
    
    vistorias = db.relationship('Inspection', backref='contrato', lazy=True)
    transacoes = db.relationship('FinancialTransaction', backref='contrato', lazy=True)

class Inspection(db.Model):
    __tablename__ = 'vistorias'
    
    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contratos.id'), nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False, index=True) # Saída ou Entrada
    data = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    observacoes = db.Column(db.Text, nullable=True)
    url_fotos = db.Column(db.String(255), nullable=True) # Pode ser JSON array se forem várias fotos
    realizado_por_nome = db.Column(db.String(100), nullable=True)

class FinancialTransaction(db.Model):
    __tablename__ = 'financeiro_transacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contratos.id'), nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False, index=True) # Aluguel, Deposito, Multa, Dano, Devolucao_Deposito
    data_vencimento = db.Column(db.DateTime, nullable=False, index=True)
    data_pagamento = db.Column(db.DateTime, nullable=True, index=True)
    valor = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), default=TransactionStatus.PENDENTE.value, nullable=False, index=True)
    forma_pagamento = db.Column(db.String(50), nullable=True)
    registrado_por_nome = db.Column(db.String(100), nullable=True)

class AuditLog(db.Model):
    __tablename__ = 'logs_auditoria'
    
    id = db.Column(db.Integer, primary_key=True)
    data_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True)
    usuario_nome = db.Column(db.String(100), nullable=True)
    acao = db.Column(db.String(50), nullable=False, index=True)
    entidade = db.Column(db.String(50), nullable=False)
    entidade_id = db.Column(db.String(50), nullable=True)
    descricao = db.Column(db.Text, nullable=False)
    ip_origem = db.Column(db.String(50), nullable=True)

class JobExecutionLock(db.Model):
    __tablename__ = 'job_locks'
    
    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    last_run_date = db.Column(db.String(10), nullable=False) # Format YYYY-MM-DD
    last_run_at = db.Column(db.DateTime, nullable=False)
    executed_by = db.Column(db.String(100), nullable=True)

def init_db(app):
    if 'sqlalchemy' not in app.extensions:
        db.init_app(app)
    with app.app_context():
        db.create_all()
        try:
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            with db.engine.connect() as conn:
                # Contratos
                if 'contratos' in existing_tables:
                    cols_c = [col['name'] for col in inspector.get_columns('contratos')]
                    if 'criado_por_nome' not in cols_c:
                        conn.execute(db.text("ALTER TABLE contratos ADD COLUMN criado_por_nome VARCHAR(100)"))
                        conn.commit()
                    if 'data_ultima_checagem_seguro' not in cols_c:
                        conn.execute(db.text("ALTER TABLE contratos ADD COLUMN data_ultima_checagem_seguro DATE"))
                        conn.commit()
                    if 'status_seguro' not in cols_c:
                        conn.execute(db.text("ALTER TABLE contratos ADD COLUMN status_seguro VARCHAR(20) DEFAULT 'Valid'"))
                        conn.commit()
                    if 'seguro_verificado_por' not in cols_c:
                        conn.execute(db.text("ALTER TABLE contratos ADD COLUMN seguro_verificado_por VARCHAR(100)"))
                        conn.commit()
                    
                # Vistorias
                if 'vistorias' in existing_tables:
                    cols_i = [col['name'] for col in inspector.get_columns('vistorias')]
                    if 'realizado_por_nome' not in cols_i:
                        conn.execute(db.text("ALTER TABLE vistorias ADD COLUMN realizado_por_nome VARCHAR(100)"))
                        conn.commit()
                    
                # Financeiro Transações
                if 'financeiro_transacoes' in existing_tables:
                    cols_t = [col['name'] for col in inspector.get_columns('financeiro_transacoes')]
                    if 'registrado_por_nome' not in cols_t:
                        conn.execute(db.text("ALTER TABLE financeiro_transacoes ADD COLUMN registrado_por_nome VARCHAR(100)"))
                        conn.commit()

                # Motos
                if 'motos' in existing_tables:
                    cols_m = [col['name'] for col in inspector.get_columns('motos')]
                    if 'vencimento_mot' not in cols_m:
                        conn.execute(db.text("ALTER TABLE motos ADD COLUMN vencimento_mot DATE"))
                        conn.commit()
                    if 'vencimento_tax' not in cols_m:
                        conn.execute(db.text("ALTER TABLE motos ADD COLUMN vencimento_tax DATE"))
                        conn.commit()

                # Clientes
                if 'clientes' in existing_tables:
                    cols_cl = [col['name'] for col in inspector.get_columns('clientes')]
                    if 'url_habilitacao_verso' not in cols_cl:
                        conn.execute(db.text("ALTER TABLE clientes ADD COLUMN url_habilitacao_verso VARCHAR(255)"))
                        conn.commit()
                    if 'url_cbt' not in cols_cl:
                        conn.execute(db.text("ALTER TABLE clientes ADD COLUMN url_cbt VARCHAR(255)"))
                        conn.commit()

                # Performance: Auto-create essential indexes on existing database
                indexes_to_create = [
                    ("idx_contratos_cliente", "contratos", "id_cliente"),
                    ("idx_contratos_placa", "contratos", "placa"),
                    ("idx_contratos_status", "contratos", "status"),
                    ("idx_transacoes_contrato", "financeiro_transacoes", "id_contrato"),
                    ("idx_transacoes_status", "financeiro_transacoes", "status"),
                    ("idx_transacoes_vencimento", "financeiro_transacoes", "data_vencimento"),
                    ("idx_transacoes_pagamento", "financeiro_transacoes", "data_pagamento"),
                    ("idx_transacoes_tipo", "financeiro_transacoes", "tipo"),
                    ("idx_vistorias_contrato", "vistorias", "id_contrato"),
                    ("idx_vistorias_data", "vistorias", "data"),
                    ("idx_motos_status", "motos", "status"),
                    ("idx_motos_mot", "motos", "vencimento_mot"),
                    ("idx_motos_tax", "motos", "vencimento_tax"),
                    ("idx_clientes_nome", "clientes", "nome"),
                    ("idx_clientes_telefone", "clientes", "telefone"),
                ]
                for idx_name, tbl, col in indexes_to_create:
                    if tbl in existing_tables:
                        try:
                            conn.execute(db.text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {tbl} ({col});"))
                        except Exception:
                            pass
                conn.commit()

        except Exception as e:
            print(f"[DB Auto-Migration] Info: {e}")

# --- Garbage Collector (File Cleanup) ---
def delete_file_if_exists(filepath):
    if not filepath: return
    filename = os.path.basename(filepath)
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    
    for base in [uploads_dir, os.path.join(os.getcwd(), 'static', 'uploads'), os.getcwd()]:
        full_path = os.path.join(base, filename)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            try:
                os.remove(full_path)
                break
            except Exception as e:
                print(f"Error removing file {full_path}: {e}")

@event.listens_for(Client, 'after_delete')
def receive_after_delete_client(mapper, connection, target):
    delete_file_if_exists(target.url_habilitacao)
    delete_file_if_exists(target.url_habilitacao_verso)
    delete_file_if_exists(target.url_cbt)
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
