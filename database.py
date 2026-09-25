from datetime import datetime
import pytz
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
    role = db.Column(db.String(20), default='staff', nullable=False) # Mantido para compatibilidade descritiva
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    perm_alugueis = db.Column(db.Boolean, default=True, nullable=False)
    perm_claims = db.Column(db.Boolean, default=False, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    data_criacao = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Europe/London')).replace(tzinfo=None), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return self.ativo

    def pode_alugueis(self):
        return bool(self.is_admin or self.perm_alugueis)

    def pode_claims(self):
        return bool(self.is_admin or self.perm_claims)

    def pode_admin(self):
        return bool(self.is_admin)

class MotoStatus(str, Enum):
    AVAILABLE = "Available"
    RENTED = "Rented"
    MAINTENANCE = "Maintenance"
    SOLD = "Sold"
    POUND = "Pound"
    # Legacy aliases
    DISPONIVEL = "Available"
    ALUGADA = "Rented"
    MANUTENCAO = "Maintenance"
    VENDIDA = "Sold"

class ContractStatus(str, Enum):
    ACTIVE = "Active"
    DEPOSIT_HOLD = "Deposit_Hold"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    # Legacy aliases
    ATIVO = "Active"
    QUARENTENA_DEPOSITO = "Deposit_Hold"
    FINALIZADO = "Completed"
    CANCELADO = "Cancelled"

class ContractType(str, Enum):
    RENT = "Rent"
    SALE_FULL = "Sale_Full"
    SALE_INSTALLMENT = "Sale_Installment"
    # Legacy aliases
    ALUGUEL = "Rent"
    VENDA_VISTA = "Sale_Full"
    VENDA_PARCELADA = "Sale_Installment"

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
    SALE_FULL = "Sale_Full"
    SALE_DEPOSIT = "Sale_Deposit"
    SALE_INSTALLMENT = "Sale_Installment"
    # Legacy aliases
    ALUGUEL = "Rent"
    DEPOSITO = "Deposit"
    MULTA = "Fine"
    DANO = "Damage"
    DEVOLUCAO_DEPOSITO = "Deposit_Refund"
    VENDA_VISTA = "Sale_Full"
    VENDA_ENTRADA = "Sale_Deposit"
    VENDA_PARCELA = "Sale_Installment"

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
    email = db.Column(db.String(120), unique=True, nullable=True)
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
    milhagem_atual = db.Column(db.Integer, default=0, nullable=False)
    vencimento_mot = db.Column(db.Date, nullable=True, index=True)
    vencimento_tax = db.Column(db.Date, nullable=True, index=True)
    tax_sorn = db.Column(db.Boolean, default=False, nullable=False, index=True)
    
    contratos = db.relationship('Contract', backref='moto', lazy=True)
    v5c_arquivos = db.relationship('MotorcycleV5C', backref='moto', lazy=True, cascade='all, delete-orphan')
    trackers = db.relationship('MotorcycleTracker', backref='moto', lazy=True, cascade='all, delete-orphan')

class MotorcycleV5C(db.Model):
    __tablename__ = 'moto_v5c'
    
    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(10), db.ForeignKey('motos.placa', ondelete='CASCADE'), nullable=False, index=True)
    url_arquivo = db.Column(db.String(255), nullable=False)
    nome_original = db.Column(db.String(255), nullable=True)
    tipo_arquivo = db.Column(db.String(20), default='image', nullable=False) # 'image' or 'pdf'
    criado_por_nome = db.Column(db.String(100), nullable=True)
    data_criacao = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Europe/London')).replace(tzinfo=None), nullable=False)

class MotorcycleTracker(db.Model):
    __tablename__ = 'moto_trackers'
    
    id = db.Column(db.Integer, primary_key=True)
    placa = db.Column(db.String(10), db.ForeignKey('motos.placa', ondelete='CASCADE'), nullable=False, index=True)
    numero = db.Column(db.String(100), nullable=False) # Serial / IMEI / Número do tracker
    tipo_propriedade = db.Column(db.String(30), default='Company', nullable=False) # 'Company' (Nosso) ou 'Customer' (Cliente)
    observacoes = db.Column(db.Text, nullable=True) # Ex: local de instalação, fiação, operadora
    url_fotos = db.Column(db.Text, nullable=True) # URLs separadas por vírgula ou JSON das fotos do serial e instalação
    instalado_por_nome = db.Column(db.String(100), nullable=True)
    data_instalacao = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Europe/London')).replace(tzinfo=None), nullable=False)

class Contract(db.Model):
    __tablename__ = 'contratos'
    
    id = db.Column(db.Integer, primary_key=True)
    id_cliente = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False, index=True)
    placa = db.Column(db.String(10), db.ForeignKey('motos.placa'), nullable=False, index=True)
    
    tipo_contrato = db.Column(db.String(30), default=ContractType.RENT.value, nullable=False, index=True) # Rent, Sale_Full, Sale_Installment
    data_retirada = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Europe/London')).replace(tzinfo=None), nullable=False)
    dia_pagamento_semanal = db.Column(db.Integer, nullable=True, default=0, index=True) # 0-6 (Segunda-Domingo, relevante para Rent)
    valor_aluguel_semanal = db.Column(db.Float, nullable=True, default=0.0)
    data_devolucao = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default=ContractStatus.ATIVO.value, nullable=False, index=True)
    url_seguro = db.Column(db.String(255), nullable=True)
    url_comprovante_deposito = db.Column(db.String(255), nullable=True)
    criado_por_nome = db.Column(db.String(100), nullable=True)

    # Specific Vehicle Sale Fields & UK Category
    categoria_historico = db.Column(db.String(50), nullable=True) # Clear, Cat N, Cat S, Cat C, Cat D, Cat B
    valor_venda_veiculo = db.Column(db.Numeric(10, 2), nullable=True)
    acessorios_extras = db.Column(db.Text, nullable=True)
    valor_admin_fee = db.Column(db.Numeric(10, 2), default=0.0, nullable=True)
    valor_total_venda = db.Column(db.Numeric(10, 2), nullable=True)
    valor_entrada = db.Column(db.Numeric(10, 2), default=0.0, nullable=True) # Down payment / Deposit da venda
    saldo_devedor = db.Column(db.Numeric(10, 2), default=0.0, nullable=True) # Outstanding balance
    cronograma_parcelas_json = db.Column(db.Text, nullable=True) # JSON list with installments schedule
    
    # Mileage Tracker (UK Miles)
    milhagem_inicial = db.Column(db.Integer, default=0, nullable=True)
    milhagem_final = db.Column(db.Integer, nullable=True)
    
    # Signatures: Start of Rental & Termination of Rental
    assinatura_cliente_inicial = db.Column(db.String(255), nullable=True)
    data_assinatura_inicial = db.Column(db.DateTime, nullable=True)
    assinatura_cliente_devolucao = db.Column(db.String(255), nullable=True)
    data_assinatura_devolucao = db.Column(db.DateTime, nullable=True)
    
    # 15-Day Insurance Compliance (askMID Verification)
    data_ultima_checagem_seguro = db.Column(db.Date, nullable=True)
    status_seguro = db.Column(db.String(20), default='Valid', nullable=False) # Valid, Cancelled
    seguro_verificado_por = db.Column(db.String(100), nullable=True)
    
    # Immutable Snapshots (Captured when Contract is Created)
    cliente_nome = db.Column(db.String(100), nullable=True)
    cliente_telefone = db.Column(db.String(20), nullable=True)
    cliente_email = db.Column(db.String(120), nullable=True)
    cliente_endereco = db.Column(db.String(255), nullable=True)
    url_habilitacao = db.Column(db.String(255), nullable=True)
    url_habilitacao_verso = db.Column(db.String(255), nullable=True)
    url_cbt = db.Column(db.String(255), nullable=True)
    url_comprovante_endereco = db.Column(db.String(255), nullable=True)
    
    moto_modelo = db.Column(db.String(100), nullable=True)
    moto_cor = db.Column(db.String(50), nullable=True)
    moto_placa = db.Column(db.String(10), nullable=True)
    valor_deposito = db.Column(db.Numeric(10, 2), nullable=True)
    dia_pagamento_semanal_original = db.Column(db.Integer, nullable=True) # Snapshot: dia da semana originalmente assinado no documento impresso
    
    vistorias = db.relationship('Inspection', backref='contrato', lazy=True)
    transacoes = db.relationship('FinancialTransaction', backref='contrato', lazy=True)
    anexos = db.relationship('ContractAttachment', backref='contrato', lazy=True, cascade='all, delete-orphan')

class ContractAttachment(db.Model):
    __tablename__ = 'contrato_anexos'
    
    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contratos.id', ondelete='CASCADE'), nullable=False, index=True)
    tipo = db.Column(db.String(30), default='initial_contract', nullable=False) # initial_contract, return_contract, general
    url_arquivo = db.Column(db.String(255), nullable=False)
    nome_original = db.Column(db.String(255), nullable=True)
    data_criacao = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Europe/London')).replace(tzinfo=None), nullable=False)

class Inspection(db.Model):
    __tablename__ = 'vistorias'
    
    id = db.Column(db.Integer, primary_key=True)
    id_contrato = db.Column(db.Integer, db.ForeignKey('contratos.id'), nullable=False, index=True)
    tipo = db.Column(db.String(20), nullable=False, index=True) # Saída ou Entrada
    data = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Europe/London')).replace(tzinfo=None), nullable=False, index=True)
    milhagem = db.Column(db.Integer, nullable=True)
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
    forma_pagamento = db.Column(db.String(255), nullable=True)
    detalhes_pagamento_json = db.Column(db.Text, nullable=True)
    nota = db.Column(db.Text, nullable=True)
    id_transacao_origem = db.Column(db.Integer, nullable=True)
    registrado_por_nome = db.Column(db.String(100), nullable=True)

    __table_args__ = (
        db.Index('idx_ft_status_vencimento', 'status', 'data_vencimento'),
    )

class AuditLog(db.Model):
    __tablename__ = 'logs_auditoria'
    
    id = db.Column(db.Integer, primary_key=True)
    data_hora = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Europe/London')).replace(tzinfo=None), nullable=False, index=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'), nullable=True)
    usuario_nome = db.Column(db.String(100), nullable=True)
    acao = db.Column(db.String(50), nullable=False, index=True)
    entidade = db.Column(db.String(50), nullable=False)
    entidade_id = db.Column(db.String(50), nullable=True)
    descricao = db.Column(db.Text, nullable=False)
    ip_origem = db.Column(db.String(50), nullable=True)

class Claim(db.Model):
    __tablename__ = 'claims'
    
    id = db.Column(db.Integer, primary_key=True)
    claim_number = db.Column(db.String(50), nullable=False, index=True) # Ref seguradora / claim company
    empresa_parceira = db.Column(db.String(50), nullable=False, index=True) # McAms, ALS, 365, etc.
    
    # Informações do Cliente e Moto
    cliente_nome = db.Column(db.String(100), nullable=False, index=True)
    cliente_telefone = db.Column(db.String(30), nullable=True)
    placa = db.Column(db.String(20), nullable=False, index=True)
    modelo_moto = db.Column(db.String(100), nullable=True)
    
    # Status Geral do Processo: Em Aberto, Concluido, Cancelado
    status = db.Column(db.String(30), default='Em Aberto', nullable=False, index=True)
    
    # Ciclo 1: Aprovação e Indicação (Prazo: 14 dias a partir da aprovação)
    data_acidente = db.Column(db.Date, nullable=True)
    data_aprovacao = db.Column(db.Date, nullable=True, index=True)
    valor_indicacao = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    prazo_indicacao = db.Column(db.Date, nullable=True, index=True) # data_aprovacao + 14 dias
    status_indicacao = db.Column(db.String(20), default='Pendente', nullable=False, index=True) # Pendente, Pago, Atrasado
    data_pagamento_indicacao = db.Column(db.Date, nullable=True)
    
    # Ciclo 2: Pátio / Storage (Prazo: 28 dias a partir da aprovação para liberação)
    data_entrada_storage = db.Column(db.Date, nullable=True)
    prazo_liberacao_storage = db.Column(db.Date, nullable=True, index=True) # data_aprovacao + 28 dias
    data_liberacao_storage = db.Column(db.Date, nullable=True) # Data em que a moto saiu do pátio
    status_storage = db.Column(db.String(30), default='No Pátio', nullable=False, index=True) # No Pátio, Liberado, Invoice Enviado, Pago
    valor_diaria_storage = db.Column(db.Numeric(10, 2), default=15.00, nullable=False)
    dias_storage = db.Column(db.Integer, default=0, nullable=False)
    valor_total_storage = db.Column(db.Numeric(10, 2), default=0.0, nullable=False)
    
    # Ciclo 3: Faturamento do Storage (Prazo: 14 dias a partir do invoice)
    data_envio_invoice = db.Column(db.Date, nullable=True, index=True)
    prazo_pagamento_invoice = db.Column(db.Date, nullable=True, index=True) # data_envio_invoice + 14 dias
    status_pagamento_storage = db.Column(db.String(20), default='Pendente', nullable=False, index=True) # Pendente, Pago, Atrasado
    data_pagamento_storage = db.Column(db.Date, nullable=True)
    
    # Observações e Auditoria
    observacoes = db.Column(db.Text, nullable=True)
    criado_por_nome = db.Column(db.String(100), nullable=True)
    data_criacao = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('Europe/London')).replace(tzinfo=None), nullable=False)

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
                    if 'milhagem_inicial' not in cols_c:
                        conn.execute(db.text("ALTER TABLE contratos ADD COLUMN milhagem_inicial INTEGER DEFAULT 0"))
                        conn.commit()
                    if 'milhagem_final' not in cols_c:
                        conn.execute(db.text("ALTER TABLE contratos ADD COLUMN milhagem_final INTEGER"))
                        conn.commit()
                    if 'assinatura_cliente_inicial' not in cols_c:
                        conn.execute(db.text("ALTER TABLE contratos ADD COLUMN assinatura_cliente_inicial VARCHAR(255)"))
                        conn.commit()
                    if 'data_assinatura_inicial' not in cols_c:
                        conn.execute(db.text("ALTER TABLE contratos ADD COLUMN data_assinatura_inicial DATETIME"))
                        conn.commit()
                    if 'assinatura_cliente_devolucao' not in cols_c:
                        conn.execute(db.text("ALTER TABLE contratos ADD COLUMN assinatura_cliente_devolucao VARCHAR(255)"))
                        conn.commit()
                    if 'data_assinatura_devolucao' not in cols_c:
                        conn.execute(db.text("ALTER TABLE contratos ADD COLUMN data_assinatura_devolucao DATETIME"))
                        conn.commit()

                    # Immutable snapshot fields for contracts
                    snapshot_cols = [
                        ('cliente_nome', 'VARCHAR(100)'),
                        ('cliente_telefone', 'VARCHAR(20)'),
                        ('cliente_email', 'VARCHAR(120)'),
                        ('cliente_endereco', 'VARCHAR(255)'),
                        ('url_habilitacao', 'VARCHAR(255)'),
                        ('url_habilitacao_verso', 'VARCHAR(255)'),
                        ('url_cbt', 'VARCHAR(255)'),
                        ('url_comprovante_endereco', 'VARCHAR(255)'),
                        ('moto_modelo', 'VARCHAR(100)'),
                        ('moto_cor', 'VARCHAR(50)'),
                        ('moto_placa', 'VARCHAR(10)'),
                        ('valor_deposito', 'NUMERIC(10, 2)'),
                        ('dia_pagamento_semanal_original', 'INTEGER'),
                    ]
                    for col_name, col_type in snapshot_cols:
                        if col_name not in cols_c:
                            conn.execute(db.text(f"ALTER TABLE contratos ADD COLUMN {col_name} {col_type}"))
                            conn.commit()

                    # Vehicle Sale & UK Category Columns
                    sale_cols = [
                        ('tipo_contrato', "VARCHAR(30) DEFAULT 'Rent'"),
                        ('categoria_historico', 'VARCHAR(50)'),
                        ('valor_venda_veiculo', 'NUMERIC(10, 2)'),
                        ('acessorios_extras', 'TEXT'),
                        ('valor_admin_fee', 'NUMERIC(10, 2) DEFAULT 0.0'),
                        ('valor_total_venda', 'NUMERIC(10, 2)'),
                        ('valor_entrada', 'NUMERIC(10, 2) DEFAULT 0.0'),
                        ('saldo_devedor', 'NUMERIC(10, 2) DEFAULT 0.0'),
                        ('cronograma_parcelas_json', 'TEXT'),
                    ]
                    for col_name, col_type in sale_cols:
                        if col_name not in cols_c:
                            conn.execute(db.text(f"ALTER TABLE contratos ADD COLUMN {col_name} {col_type}"))
                            conn.commit()

                    try:
                        conn.execute(db.text("CREATE INDEX IF NOT EXISTS idx_contratos_tipo ON contratos (tipo_contrato);"))
                        conn.commit()
                    except Exception as idx_err:
                        print(f"[DB Auto-Migration] Index idx_contratos_tipo info: {idx_err}")

                    # Backfill existing contracts if snapshot fields are null
                    try:
                        conn.execute(db.text("""
                            UPDATE contratos 
                            SET 
                                cliente_nome = (SELECT nome FROM clientes WHERE clientes.id = contratos.id_cliente),
                                cliente_telefone = (SELECT telefone FROM clientes WHERE clientes.id = contratos.id_cliente),
                                cliente_email = (SELECT email FROM clientes WHERE clientes.id = contratos.id_cliente),
                                cliente_endereco = (SELECT endereco FROM clientes WHERE clientes.id = contratos.id_cliente),
                                url_habilitacao = (SELECT url_habilitacao FROM clientes WHERE clientes.id = contratos.id_cliente),
                                url_habilitacao_verso = (SELECT url_habilitacao_verso FROM clientes WHERE clientes.id = contratos.id_cliente),
                                url_cbt = (SELECT url_cbt FROM clientes WHERE clientes.id = contratos.id_cliente),
                                url_comprovante_endereco = (SELECT url_comprovante_endereco FROM clientes WHERE clientes.id = contratos.id_cliente),
                                moto_modelo = (SELECT modelo FROM motos WHERE motos.placa = contratos.placa),
                                moto_cor = (SELECT cor FROM motos WHERE motos.placa = contratos.placa),
                                moto_placa = contratos.placa
                            WHERE cliente_nome IS NULL;
                        """))
                        conn.commit()

                        conn.execute(db.text("""
                            UPDATE contratos
                            SET dia_pagamento_semanal_original = dia_pagamento_semanal
                            WHERE dia_pagamento_semanal_original IS NULL AND dia_pagamento_semanal IS NOT NULL;
                        """))
                        conn.commit()

                        conn.execute(db.text("""
                            UPDATE contratos
                            SET valor_deposito = (
                                SELECT valor FROM financeiro_transacoes 
                                WHERE financeiro_transacoes.id_contrato = contratos.id 
                                  AND (financeiro_transacoes.tipo IN ('Deposit', 'Deposito', 'Depósito') 
                                       OR LOWER(financeiro_transacoes.tipo) = 'deposit')
                                LIMIT 1
                            )
                            WHERE valor_deposito IS NULL;
                        """))
                        conn.commit()

                        conn.execute(db.text("""
                            UPDATE contratos
                            SET tipo_contrato = 'Rent'
                            WHERE tipo_contrato IS NULL;
                        """))
                        conn.commit()
                    except Exception as backfill_err:
                        print(f"[DB Auto-Migration] Backfill info: {backfill_err}")
                    
                # Vistorias
                if 'vistorias' in existing_tables:
                    cols_i = [col['name'] for col in inspector.get_columns('vistorias')]
                    if 'realizado_por_nome' not in cols_i:
                        conn.execute(db.text("ALTER TABLE vistorias ADD COLUMN realizado_por_nome VARCHAR(100)"))
                        conn.commit()
                    if 'milhagem' not in cols_i:
                        conn.execute(db.text("ALTER TABLE vistorias ADD COLUMN milhagem INTEGER"))
                        conn.commit()
                    
                # Financeiro Transações
                if 'financeiro_transacoes' in existing_tables:
                    cols_t = [col['name'] for col in inspector.get_columns('financeiro_transacoes')]
                    if 'registrado_por_nome' not in cols_t:
                        conn.execute(db.text("ALTER TABLE financeiro_transacoes ADD COLUMN registrado_por_nome VARCHAR(100)"))
                        conn.commit()
                    if 'detalhes_pagamento_json' not in cols_t:
                        conn.execute(db.text("ALTER TABLE financeiro_transacoes ADD COLUMN detalhes_pagamento_json TEXT"))
                        conn.commit()
                    if 'id_transacao_origem' not in cols_t:
                        conn.execute(db.text("ALTER TABLE financeiro_transacoes ADD COLUMN id_transacao_origem INTEGER"))
                        conn.commit()
                    if 'nota' not in cols_t:
                        conn.execute(db.text("ALTER TABLE financeiro_transacoes ADD COLUMN nota TEXT"))
                        conn.commit()
                    if db.engine.dialect.name == 'postgresql':
                        try:
                            conn.execute(db.text("ALTER TABLE financeiro_transacoes ALTER COLUMN forma_pagamento TYPE VARCHAR(255);"))
                            conn.commit()
                        except Exception as e_pg_forma:
                            print(f"[DB Auto-Migration] Postgres alter forma_pagamento info: {e_pg_forma}")

                # Motos
                if 'motos' in existing_tables:
                    cols_m = [col['name'] for col in inspector.get_columns('motos')]
                    if 'vencimento_mot' not in cols_m:
                        conn.execute(db.text("ALTER TABLE motos ADD COLUMN vencimento_mot DATE"))
                        conn.commit()
                    if 'vencimento_tax' not in cols_m:
                        conn.execute(db.text("ALTER TABLE motos ADD COLUMN vencimento_tax DATE"))
                        conn.commit()
                    if 'tax_sorn' not in cols_m:
                        if db.engine.dialect.name == 'postgresql':
                            conn.execute(db.text("ALTER TABLE motos ADD COLUMN tax_sorn BOOLEAN DEFAULT FALSE"))
                        else:
                            conn.execute(db.text("ALTER TABLE motos ADD COLUMN tax_sorn BOOLEAN DEFAULT 0"))
                        conn.commit()
                    if 'milhagem_atual' not in cols_m:
                        conn.execute(db.text("ALTER TABLE motos ADD COLUMN milhagem_atual INTEGER DEFAULT 0"))
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

                    # Ensure email is nullable (Optional email)
                    if db.engine.dialect.name == 'postgresql':
                        try:
                            conn.execute(db.text("ALTER TABLE clientes ALTER COLUMN email DROP NOT NULL;"))
                            conn.commit()
                        except Exception as e_pg:
                            print(f"[DB Auto-Migration] Postgres drop not null email info: {e_pg}")
                    elif db.engine.dialect.name == 'sqlite':
                        try:
                            col_email = next((col for col in inspector.get_columns('clientes') if col['name'] == 'email'), None)
                            if col_email and not col_email.get('nullable', True):
                                conn.execute(db.text("PRAGMA foreign_keys = OFF;"))
                                conn.execute(db.text("""
                                    CREATE TABLE IF NOT EXISTS clientes_migration_new (
                                        id INTEGER NOT NULL PRIMARY KEY,
                                        nome VARCHAR(100) NOT NULL,
                                        telefone VARCHAR(20) NOT NULL,
                                        email VARCHAR(120) UNIQUE,
                                        endereco VARCHAR(255),
                                        url_habilitacao VARCHAR(255),
                                        url_comprovante_endereco VARCHAR(255),
                                        url_habilitacao_verso VARCHAR(255),
                                        url_cbt VARCHAR(255)
                                    );
                                """))
                                conn.execute(db.text("""
                                    INSERT INTO clientes_migration_new (id, nome, telefone, email, endereco, url_habilitacao, url_comprovante_endereco, url_habilitacao_verso, url_cbt)
                                    SELECT id, nome, telefone, email, endereco, url_habilitacao, url_comprovante_endereco, url_habilitacao_verso, url_cbt FROM clientes;
                                """))
                                conn.execute(db.text("DROP TABLE clientes;"))
                                conn.execute(db.text("ALTER TABLE clientes_migration_new RENAME TO clientes;"))
                                conn.execute(db.text("PRAGMA foreign_keys = ON;"))
                                conn.commit()
                        except Exception as e_sql:
                            print(f"[DB Auto-Migration] SQLite email nullable migration info: {e_sql}")

                # Usuarios: Permissões Modulares Limpas
                if 'usuarios' in existing_tables:
                    cols_u = [col['name'] for col in inspector.get_columns('usuarios')]
                    if 'is_admin' not in cols_u:
                        conn.execute(db.text("ALTER TABLE usuarios ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
                        conn.commit()
                        conn.execute(db.text("UPDATE usuarios SET is_admin = 1 WHERE role = 'admin'"))
                        conn.commit()
                    if 'perm_alugueis' not in cols_u:
                        conn.execute(db.text("ALTER TABLE usuarios ADD COLUMN perm_alugueis BOOLEAN DEFAULT 1"))
                        conn.commit()
                        conn.execute(db.text("UPDATE usuarios SET perm_alugueis = 1"))
                        conn.commit()
                    if 'perm_claims' not in cols_u:
                        conn.execute(db.text("ALTER TABLE usuarios ADD COLUMN perm_claims BOOLEAN DEFAULT 0"))
                        conn.commit()
                        conn.execute(db.text("UPDATE usuarios SET perm_claims = 1 WHERE role = 'admin'"))
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
                    ("idx_motos_tax_sorn", "motos", "tax_sorn"),
                    ("idx_clientes_nome", "clientes", "nome"),
                    ("idx_clientes_telefone", "clientes", "telefone"),
                    ("idx_claims_number", "claims", "claim_number"),
                    ("idx_claims_placa", "claims", "placa"),
                    ("idx_claims_status", "claims", "status"),
                    ("idx_claims_empresa", "claims", "empresa_parceira"),
                    ("idx_anexos_contrato", "contrato_anexos", "id_contrato"),
                    ("idx_ft_status_vencimento", "financeiro_transacoes", "status, data_vencimento"),
                    ("idx_contratos_dia_pgto", "contratos", "dia_pagamento_semanal"),
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
