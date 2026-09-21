import os
import json
import secrets
import hmac
import time
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, jsonify, send_file, redirect, url_for, 
    send_from_directory, flash, session
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from database import (
    db, init_db, Contract, ContractType, FinancialTransaction, TransactionType, 
    TransactionStatus, ContractStatus, MotoStatus, Motorcycle, Client, Inspection, InspectionType,
    User, AuditLog, JobExecutionLock, Claim, ContractAttachment, delete_file_if_exists
)
from sqlalchemy.orm import joinedload, contains_eager
import werkzeug.utils
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'ffmotors-birmingham-uk-secret-key-2026-production')

# Configuração do banco de dados (PostgreSQL em produção ou SQLite local)
basedir = os.path.abspath(os.path.dirname(__file__))
db_uri = os.environ.get('DATABASE_URL')
if db_uri and not db_uri.startswith("sqlite"):
    if db_uri.startswith("postgres://"):
        db_uri = db_uri.replace("postgres://", "postgresql://", 1)
else:
    db_uri = 'sqlite:///' + os.path.join(basedir, 'ffmotors.db')
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database Engine Options: SQLite timeout vs PostgreSQL production pool
if "sqlite" in db_uri.lower():
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'timeout': 30}
    }
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_recycle': 1800,
        'pool_pre_ping': True
    }

app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER') or os.path.join(basedir, 'static', 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Strict Upload Security Whitelist
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'pdf'}

def is_allowed_file(filename):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

# London Timezone Operations
LONDON_TZ = pytz.timezone('Europe/London')

def get_london_now():
    """Returns current timezone-aware datetime in Europe/London."""
    return datetime.now(LONDON_TZ)

def get_local_now():
    """Returns naive datetime representing local London time."""
    return get_london_now().replace(tzinfo=None)

def get_london_date():
    """Returns today's date in Europe/London."""
    return get_london_now().date()

# Thread-safe Rate Limiting for Login (10 attempts per 15 min per IP)
LOGIN_ATTEMPTS = defaultdict(list)
LOGIN_LOCK = threading.Lock()
MAX_LOGIN_ATTEMPTS = 10
LOGIN_WINDOW_SECONDS = 15 * 60

def is_ip_rate_limited(ip):
    now = time.time()
    with LOGIN_LOCK:
        attempts = [t for t in LOGIN_ATTEMPTS[ip] if now - t < LOGIN_WINDOW_SECONDS]
        LOGIN_ATTEMPTS[ip] = attempts
        return len(attempts) >= MAX_LOGIN_ATTEMPTS

def record_failed_login(ip):
    now = time.time()
    with LOGIN_LOCK:
        LOGIN_ATTEMPTS[ip].append(now)

def clear_failed_logins(ip):
    with LOGIN_LOCK:
        LOGIN_ATTEMPTS.pop(ip, None)

# Configurações de Cookie de Sessão
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
if os.environ.get('SESSION_COOKIE_SECURE', '').lower() in ('true', '1') or (os.environ.get('FLASK_ENV') == 'production' and os.environ.get('HTTPS') == 'on'):
    app.config['SESSION_COOKIE_SECURE'] = True

# Segurança de Sessão: Expiração por Inatividade (padrão 8 horas = 28800s) e Duração Máxima
SESSION_IDLE_TIMEOUT_SECONDS = int(os.environ.get('SESSION_IDLE_TIMEOUT_SECONDS', 28800))  # 8 horas
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(hours=12)

# Garante tipos MIME corretos no Windows para que imagens e documentos abram em nova aba e não façam download
import mimetypes
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('image/avif', '.avif')
mimetypes.add_type('application/pdf', '.pdf')
mimetypes.add_type('image/jpeg', '.jpg')
mimetypes.add_type('image/jpeg', '.jpeg')
mimetypes.add_type('image/png', '.png')

# Configuração de Autenticação (Flask-Login)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para acessar o sistema FF Motors.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except Exception:
        return None

@login_manager.unauthorized_handler
def unauthorized_callback():
    if request.path.startswith('/api/'):
        return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401
    return redirect(url_for('login', next=request.path))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            if request.path.startswith('/api/'):
                return jsonify({"error": "Forbidden", "message": "Admin privileges required"}), 403
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def alugueis_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/api/'):
                return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401
            return redirect(url_for('login', next=request.path))
        if not current_user.pode_alugueis():
            if request.path.startswith('/api/'):
                return jsonify({"error": "Forbidden", "message": "Acesso restrito ao módulo de aluguéis"}), 403
            flash('Você não tem permissão para acessar o módulo de aluguéis.', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def claims_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/api/'):
                return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401
            return redirect(url_for('login', next=request.path))
        if not current_user.pode_claims():
            if request.path.startswith('/api/'):
                return jsonify({"error": "Forbidden", "message": "Acesso restrito ao módulo de claims & storage"}), 403
            flash('Você não tem permissão para acessar o módulo de Claims & Storage.', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def registrar_log(acao, entidade, entidade_id, descricao):
    """
    Registra um evento na trilha de auditoria interna.
    Identifica automaticamente o usuário logado e o IP da requisição.
    """
    try:
        user_id = current_user.id if current_user.is_authenticated else None
        user_nome = current_user.nome if current_user.is_authenticated else "System"
        ip = request.remote_addr if request else None
        log = AuditLog(
            id_usuario=user_id,
            usuario_nome=user_nome,
            acao=acao,
            entidade=entidade,
            entidade_id=str(entidade_id) if entidade_id else None,
            descricao=descricao,
            ip_origem=ip,
            data_hora=get_local_now()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"[AuditLog Error]: {e}")

# --- CSRF Protection & Security Headers ---
def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf_token)

app.jinja_env.globals['csrf_token'] = generate_csrf_token

@app.before_request
def validate_csrf():
    if (app.config.get('TESTING') or os.environ.get('FLASK_ENV') == 'testing') and not app.config.get('WTF_CSRF_ENABLED', True):
        return
    if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
        if request.path.startswith('/static/') or request.endpoint == 'custom_static_uploads':
            return
            
        expected_token = session.get('_csrf_token')
        client_token = (
            request.headers.get('X-CSRFToken') or
            request.headers.get('X-CSRF-Token') or
            request.form.get('csrf_token') or
            (request.is_json and isinstance(request.json, dict) and request.json.get('csrf_token'))
        )
        
        if not expected_token or not client_token or not hmac.compare_digest(str(expected_token), str(client_token)):
            if request.path.startswith('/api/'):
                return jsonify({
                    'error': 'CSRF token missing or invalid',
                    'erro': 'Token CSRF ausente ou inválido'
                }), 400
            flash('Sessão expirada ou token de segurança inválido. Por favor, tente novamente.', 'error')
            return redirect(request.referrer or url_for('login'))

@app.after_request
def apply_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

@app.before_request
def check_authentication():
    # Endpoints públicos permitidos sem autenticação
    allowed_routes = ['login', 'logout', 'static', 'custom_static_uploads', 'favicon']
    if request.endpoint in allowed_routes:
        return
    if request.path.startswith('/static/'):
        return
    if app.config.get('LOGIN_DISABLED'):
        return

    # Verificação de sessão ativa e timeout de inatividade (60 minutos)
    if current_user.is_authenticated:
        now = time.time()
        last_activity = session.get('last_activity')

        # Se não há registro de atividade recente ou ultrapassou o tempo limite de inatividade
        if last_activity is None or (now - float(last_activity)) > SESSION_IDLE_TIMEOUT_SECONDS:
            logout_user()
            session.pop('last_activity', None)
            timeout_hours = max(1, SESSION_IDLE_TIMEOUT_SECONDS // 3600)
            timeout_desc = f"{timeout_hours} horas" if timeout_hours > 1 else "60 minutos"
            if request.path.startswith('/api/'):
                return jsonify({
                    "error": "SessionExpired",
                    "message": f"Sua sessão expirou por inatividade ({timeout_desc}). Faça login novamente."
                }), 401
            flash(f'Sua sessão expirou por inatividade após {timeout_desc}. Por segurança, faça login novamente.', 'warning')
            return redirect(url_for('login', next=request.path))

        # Atualiza o timestamp da última atividade do usuário
        session['last_activity'] = now
        return

    if not current_user.is_authenticated:
        if request.path.startswith('/api/'):
            return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401
        return redirect(url_for('login', next=request.path))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        client_ip = request.remote_addr or 'unknown'
        if is_ip_rate_limited(client_ip):
            flash('Too many failed login attempts (maximum 10). For security, please wait 15 minutes before trying again.', 'danger')
            return render_template('login.html', email=request.form.get('email', '')), 429

        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.ativo:
                flash('Esta conta de acesso está inativa. Contate o administrador.', 'danger')
                return render_template('login.html', email=email)
                
            clear_failed_logins(client_ip)
            session.permanent = True
            login_user(user, remember=remember)
            registrar_log('LOGIN_SUCCESS', 'User', user.id, f"Usuário {user.nome} fez login no sistema.")
            session['last_activity'] = time.time()
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('index')
            return redirect(next_page)
        else:
            record_failed_login(client_ip)
            registrar_log('LOGIN_FAILED', 'User', None, f"Tentativa de login falha para o email: {email} (IP: {client_ip})")
            flash('Credenciais inválidas. Verifique seu e-mail e senha.', 'danger')
            return render_template('login.html', email=email)
            
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    session.pop('last_activity', None)
    uid = current_user.id if current_user.is_authenticated else None
    unome = current_user.nome if current_user.is_authenticated else 'System'
    if uid: registrar_log('LOGOUT', 'User', uid, f"Usuário {unome} fez logout.")
    logout_user()
    flash('Você saiu do sistema com segurança.', 'info')
    return redirect(url_for('login'))

@app.route('/static/uploads/<path:filename>')
def custom_static_uploads(filename):
    if not is_allowed_file(filename):
        return jsonify({'error': 'Access denied to this file type', 'erro': 'Acesso negado para este tipo de arquivo'}), 403

    uploads_dir = app.config.get('UPLOAD_FOLDER', os.path.join(basedir, 'static', 'uploads'))
    ext = os.path.splitext(filename)[1].lower()
    mimetype = 'application/octet-stream'
    if ext == '.webp':
        mimetype = 'image/webp'
    elif ext == '.pdf':
        mimetype = 'application/pdf'
    elif ext in ['.jpg', '.jpeg']:
        mimetype = 'image/jpeg'
    elif ext == '.png':
        mimetype = 'image/png'
    else:
        guessed = mimetypes.guess_type(filename)[0]
        if guessed and (guessed.startswith('image/') or guessed == 'application/pdf'):
            mimetype = guessed
            
    response = send_from_directory(uploads_dir, filename, mimetype=mimetype, as_attachment=False)
    response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    return response

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(basedir, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.after_request
def add_inline_document_headers(response):
    if request.path.startswith('/static/uploads/'):
        ext = os.path.splitext(request.path)[1].lower()
        if ext == '.webp':
            response.headers['Content-Type'] = 'image/webp'
        elif ext == '.pdf':
            response.headers['Content-Type'] = 'application/pdf'
        elif ext in ['.jpg', '.jpeg']:
            response.headers['Content-Type'] = 'image/jpeg'
        elif ext == '.png':
            response.headers['Content-Type'] = 'image/png'
        response.headers['Content-Disposition'] = 'inline'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    return response

# --- Global Error Handlers (JSON for APIs, HTML for Web) ---
@app.errorhandler(404)
def handle_not_found(e):
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({'error': 'Not Found', 'message': 'The requested resource was not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def handle_server_error(e):
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected server error occurred'}), 500
    return render_template('500.html'), 500

@app.errorhandler(429)
def handle_rate_limit(e):
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({'error': 'Too Many Requests', 'message': 'Too many requests. Please wait a few minutes before trying again.'}), 429
    flash('Too many requests. Please wait a few minutes before trying again.', 'danger')
    return render_template('login.html'), 429

# Inicializa o banco de dados e cria admin padrão caso ainda não exista
init_db(app)

def seed_default_admin():
    with app.app_context():
        try:
            if User.query.count() == 0:
                admin = User(
                    nome="Thiago Brandão",
                    email="tmuniz570@gmail.com",
                    role="admin",
                    is_admin=True,
                    perm_alugueis=True,
                    perm_claims=True,
                    ativo=True
                )
                admin.set_password("Admin123!")
                db.session.add(admin)
                db.session.commit()
                print("[Auth] Master Admin 'Thiago Brandão' (tmuniz570@gmail.com) criado com sucesso.")
        except Exception as e:
            print(f"[Auth] Erro ao verificar ou criar admin padrão: {e}")

seed_default_admin()

def salvar_arquivo_otimizado(file_storage, nome_arquivo):
    """
    Salva arquivo enviado com whitelist estrita. Se for imagem, auto-rotaciona via EXIF,
    redimensiona para no máximo 1600px e comprime em WebP com qualidade 80 (~30-90 KB).
    Se for PDF, salva diretamente.
    Rejeita estritamente tipos não autorizados (ex: SVG, HTML, executáveis).
    """
    if not is_allowed_file(nome_arquivo):
        raise ValueError("Invalid file format. Only JPG, PNG, WEBP, and PDF documents are allowed.")

    uploads_dir = app.config.get('UPLOAD_FOLDER', os.path.join(basedir, 'static', 'uploads'))
    os.makedirs(uploads_dir, exist_ok=True)
    
    ext = os.path.splitext(nome_arquivo)[1].lower()
    caminho_final = os.path.join(uploads_dir, nome_arquivo)
    
    if ext == '.pdf':
        file_storage.save(caminho_final)
        return nome_arquivo
        
    try:
        from PIL import Image, ImageOps
        img = Image.open(file_storage.stream)
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
            
        if img.mode in ('RGBA', 'P'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                bg.paste(img, mask=img.split()[3])
            else:
                bg.paste(img)
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')
            
        max_dim = 1600
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
        nome_webp = os.path.splitext(nome_arquivo)[0] + '.webp'
        caminho_webp = os.path.join(uploads_dir, nome_webp)
        img.save(caminho_webp, 'WEBP', quality=80, method=4)
        return nome_webp
    except Exception:
        try:
            file_storage.seek(0)
        except Exception:
            pass
        file_storage.save(caminho_final)
        return nome_arquivo

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/clientes/novo')
@alugueis_required
def pagina_cadastro_cliente():
    return render_template('cadastro_cliente.html')

@app.route('/clientes')
@alugueis_required
def pagina_clientes():
    return render_template('clientes.html')

@app.route('/motos')
@alugueis_required
def pagina_motos():
    return render_template('motos.html')

@app.route('/motos/nova')
@alugueis_required
def pagina_cadastro_moto():
    return render_template('cadastro_moto.html')

@app.route('/contratos')
@alugueis_required
def pagina_contratos():
    return render_template('contratos.html')

@app.route('/contratos/novo')
@alugueis_required
def pagina_novo_contrato():
    return render_template('novo_contrato.html')

@app.route('/vistorias/nova')
@alugueis_required
def pagina_nova_vistoria():
    return render_template('vistoria.html')

@app.route('/financeiro')
@alugueis_required
def pagina_financeiro():
    return render_template('financeiro.html')

@app.route('/vistorias')
@alugueis_required
def pagina_vistorias_lista():
    return render_template('vistorias_lista.html')

@app.route('/relatorios')
@alugueis_required
def pagina_relatorios():
    return redirect('/financeiro')

@app.route('/relatorios/vencidos')
@alugueis_required
def relatorio_vencidos():
    agora_london = get_london_now()
    transacoes = FinancialTransaction.query.options(
        db.joinedload(FinancialTransaction.contrato).joinedload(Contract.cliente)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pendente']),
        FinancialTransaction.data_vencimento < agora_london.replace(tzinfo=None)
    ).order_by(FinancialTransaction.data_vencimento.asc()).all()
    
    dados = []
    total = 0
    for t in transacoes:
        c = t.contrato
        cliente = c.cliente if c else None
        
        dados.append({
            'contrato_id': c.id if c else '-',
            'cliente_nome': cliente.nome if cliente else '-',
            'placa': c.placa if c else '-',
            'tipo': t.tipo,
            'valor': t.valor,
            'vencimento': t.data_vencimento.strftime('%d/%m/%Y') if t.data_vencimento else '-'
        })
        total += float(t.valor)
        
    agora = agora_london.strftime('%d/%m/%Y %H:%M:%S')
    return render_template('relatorio_vencidos.html', dados=dados, total=total, agora=agora)

@app.route('/contratos/<int:id>')
@alugueis_required
def pagina_detalhes_contrato(id):
    return render_template('detalhe_contrato.html', contrato_id=id)

@app.route('/contratos/<int:id>/imprimir')
@alugueis_required
def imprimir_contrato(id):
    contrato = db.session.get(Contract, id)
    if not contrato:
        return render_template('404.html'), 404
        
    cliente = db.session.get(Client, contrato.id_cliente) if contrato.id_cliente else None
    if not cliente and contrato.cliente:
        cliente = contrato.cliente
        
    moto = db.session.get(Motorcycle, contrato.placa) if contrato.placa else None
    if not moto and contrato.moto:
        moto = contrato.moto
    if not moto and contrato.placa:
        moto = Motorcycle.query.filter(db.func.lower(Motorcycle.placa) == contrato.placa.strip().lower()).first()
    
    # Dados imutáveis congelados no momento do contrato (com fallback seguro para tabela de clientes/motos)
    cliente_nome = contrato.cliente_nome or (cliente.nome if cliente else 'Customer')
    cliente_telefone = contrato.cliente_telefone or (cliente.telefone if cliente else '-')
    cliente_endereco = contrato.cliente_endereco or (cliente.endereco if cliente else 'Not provided')
    cliente_email = contrato.cliente_email or (cliente.email if cliente else None)
    
    moto_modelo = contrato.moto_modelo or (moto.modelo if moto else '-')
    moto_cor = contrato.moto_cor or (moto.cor if moto else 'Not specified')
    moto_placa = contrato.moto_placa or contrato.placa
    
    # Datas formatadas UK (DD/MM/YYYY)
    data_retirada_uk = contrato.data_retirada.strftime('%d/%m/%Y') if contrato.data_retirada else '-'
    hora_retirada_uk = contrato.data_retirada.strftime('%H:%M') if contrato.data_retirada else '-'
    
    data_devolucao_uk = contrato.data_devolucao.strftime('%d/%m/%Y') if contrato.data_devolucao else None
    hora_devolucao_uk = contrato.data_devolucao.strftime('%H:%M') if contrato.data_devolucao else None
    
    data_assinatura_inicial_uk = contrato.data_assinatura_inicial.strftime('%d/%m/%Y %H:%M') if contrato.data_assinatura_inicial else get_local_now().strftime('%d/%m/%Y %H:%M')
    data_assinatura_devolucao_uk = contrato.data_assinatura_devolucao.strftime('%d/%m/%Y %H:%M') if contrato.data_assinatura_devolucao else None

    # Se for Contrato de Venda (Full ou Installment), utiliza o template Vehicle Sale Agreement da J&F Motorcycles LTD
    if getattr(contrato, 'tipo_contrato', None) in [ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value, 'Sale_Full', 'Sale_Installment']:
        is_installment = (contrato.tipo_contrato in [ContractType.SALE_INSTALLMENT.value, 'Sale_Installment'])
        
        cronograma = []
        if contrato.cronograma_parcelas_json:
            try:
                cronograma_raw = json.loads(contrato.cronograma_parcelas_json)
                for idx, item in enumerate(cronograma_raw, 1):
                    raw_date = item.get('vencimento') or item.get('data_vencimento') or ''
                    formatted_date = str(raw_date)
                    if raw_date and '-' in str(raw_date):
                        try:
                            clean_d = str(raw_date).split('T')[0].strip()
                            parts = clean_d.split('-')
                            if len(parts) == 3:
                                formatted_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
                        except Exception:
                            formatted_date = str(raw_date)
                    cronograma.append({
                        'numero': item.get('numero') or item.get('parcela') or idx,
                        'valor': float(item.get('valor', 0.0)),
                        'vencimento': formatted_date
                    })
            except Exception as e:
                print(f"[Print Error] Falha ao decodificar cronograma_parcelas_json: {e}")
                cronograma = []

        # Fallback para transações caso o json esteja vazio
        if not cronograma and is_installment:
            inst_txs = [t for t in (contrato.transacoes or []) if t.tipo in [TransactionType.SALE_INSTALLMENT.value, 'Sale_Installment']]
            inst_txs.sort(key=lambda x: x.data_vencimento if x.data_vencimento else datetime.min)
            for idx, t in enumerate(inst_txs, 1):
                cronograma.append({
                    'numero': idx,
                    'valor': float(t.valor),
                    'vencimento': t.data_vencimento.strftime('%d/%m/%Y') if t.data_vencimento else '-'
                })
                
        return render_template(
            'contrato_venda_print.html',
            contrato=contrato,
            cliente=cliente,
            moto=moto,
            cliente_nome=cliente_nome,
            cliente_telefone=cliente_telefone,
            cliente_endereco=cliente_endereco,
            cliente_email=cliente_email,
            moto_modelo=moto_modelo,
            moto_cor=moto_cor,
            moto_placa=moto_placa,
            is_installment=is_installment,
            cronograma=cronograma,
            data_assinatura_uk=data_assinatura_inicial_uk,
            hoje_uk=get_local_now().strftime('%d/%m/%Y %H:%M')
        )

    # Contrato de Aluguel (Motorcycle Rental Agreement)
    dias_nomes = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dia_pagamento_nome = dias_nomes[contrato.dia_pagamento_semanal] if (contrato.dia_pagamento_semanal is not None and 0 <= contrato.dia_pagamento_semanal <= 6) else 'Monday'
    
    # Depósito original registrado (prioriza valor_deposito congelado no contrato)
    dep_tx = FinancialTransaction.query.filter_by(
        id_contrato=id, 
        tipo=TransactionType.DEPOSIT.value
    ).first()
    deposito_valor = float(contrato.valor_deposito) if contrato.valor_deposito is not None else (float(dep_tx.valor) if dep_tx else 500.00)

    return render_template(
        'contrato_print.html',
        contrato=contrato,
        cliente=cliente,
        moto=moto,
        cliente_nome=cliente_nome,
        cliente_telefone=cliente_telefone,
        cliente_endereco=cliente_endereco,
        cliente_email=cliente_email,
        moto_modelo=moto_modelo,
        moto_cor=moto_cor,
        moto_placa=moto_placa,
        dia_pagamento_nome=dia_pagamento_nome,
        deposito_valor=deposito_valor,
        data_retirada_uk=data_retirada_uk,
        hora_retirada_uk=hora_retirada_uk,
        data_devolucao_uk=data_devolucao_uk,
        hora_devolucao_uk=hora_devolucao_uk,
        data_assinatura_inicial_uk=data_assinatura_inicial_uk,
        data_assinatura_devolucao_uk=data_assinatura_devolucao_uk
    )

@app.route('/usuarios')
@admin_required
def pagina_usuarios():
    return render_template('usuarios.html')

# --- CLAIMS & STORAGE ROUTES ---

@app.route('/claims')
@claims_required
def pagina_claims():
    return render_template('claims.html')

@app.route('/claims/invoice/<int:id>')
@claims_required
def pagina_claim_invoice(id):
    claim = db.session.get(Claim, id)
    if not claim:
        return render_template('404.html'), 404
    return render_template('claim_invoice.html', claim=claim)

@app.route('/api/claims', methods=['GET'])
@claims_required
def listar_claims():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    search = request.args.get('search', '').strip()
    empresa = request.args.get('empresa', '').strip()
    status_filtro = request.args.get('status', '').strip()
    campo_data = request.args.get('campo_data', 'acidente').strip()
    data_inicio = request.args.get('data_inicio', '').strip()
    data_fim = request.args.get('data_fim', '').strip()
    sort_by = request.args.get('sort_by', 'id').strip().lower()
    sort_order = request.args.get('sort_order', 'desc').strip().lower()
    hoje = get_london_date()

    query = Claim.query
    if search:
        search_clean = search.replace(' ', '')
        term = f"%{search}%"
        term_clean = f"%{search_clean}%"
        query = query.filter(db.or_(
            Claim.claim_number.ilike(term),
            Claim.cliente_nome.ilike(term),
            Claim.placa.ilike(term_clean),
            Claim.placa.ilike(term),
            Claim.modelo_moto.ilike(term)
        ))
    if empresa:
        query = query.filter(Claim.empresa_parceira == empresa)
    if status_filtro:
        query = query.filter(Claim.status == status_filtro)

    # Filtro de Período de Datas
    col_data_map = {
        'acidente': Claim.data_acidente,
        'aprovacao': Claim.data_aprovacao,
        'storage_entrada': Claim.data_entrada_storage,
        'storage_liberacao': Claim.data_liberacao_storage,
        'invoice': Claim.data_envio_invoice,
        'criacao': Claim.data_criacao
    }
    target_data_col = col_data_map.get(campo_data, Claim.data_acidente)

    if data_inicio:
        try:
            d_ini = datetime.strptime(data_inicio, '%Y-%m-%d').date()
            if campo_data == 'criacao':
                query = query.filter(target_data_col >= datetime.combine(d_ini, datetime.min.time()))
            else:
                query = query.filter(target_data_col >= d_ini)
        except Exception:
            pass

    if data_fim:
        try:
            d_fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
            if campo_data == 'criacao':
                query = query.filter(target_data_col <= datetime.combine(d_fim, datetime.max.time()))
            else:
                query = query.filter(target_data_col <= d_fim)
        except Exception:
            pass

    # KPIs Globais do Módulo (otimizado: apenas colunas necessárias em vez do modelo ORM completo)
    all_claims_global = db.session.query(
        Claim.status,
        Claim.prazo_liberacao_storage,
        Claim.status_storage,
        Claim.prazo_indicacao,
        Claim.status_indicacao,
        Claim.prazo_pagamento_invoice,
        Claim.status_pagamento_storage,
        Claim.valor_indicacao,
        Claim.valor_total_storage
    ).all()
    total_indicacao_pendente = 0.0
    total_storage_pendente = 0.0
    motos_no_storage = 0
    alertas_indicacao_atrasada = 0
    alertas_storage_28d = 0
    alertas_invoice_atrasado = 0
    processos_abertos = 0

    for c in all_claims_global:
        if c.status == 'Em Aberto':
            processos_abertos += 1

        dias_para_liberacao = (c.prazo_liberacao_storage - hoje).days if (c.prazo_liberacao_storage and c.status_storage == 'No Pátio') else None
        indicacao_atrasada = bool(c.prazo_indicacao and c.prazo_indicacao < hoje and c.status_indicacao != 'Pago')
        storage_vencendo_28d = bool(c.prazo_liberacao_storage and c.status_storage == 'No Pátio' and (c.prazo_liberacao_storage <= hoje or (dias_para_liberacao is not None and dias_para_liberacao <= 7)))
        invoice_atrasado = bool(c.prazo_pagamento_invoice and c.prazo_pagamento_invoice < hoje and c.status_pagamento_storage != 'Pago')

        if c.status_indicacao != 'Pago':
            total_indicacao_pendente += float(c.valor_indicacao or 0.0)
            if indicacao_atrasada:
                alertas_indicacao_atrasada += 1

        if c.status_storage == 'No Pátio':
            motos_no_storage += 1
            if storage_vencendo_28d:
                alertas_storage_28d += 1

        if c.status_pagamento_storage != 'Pago' and float(c.valor_total_storage or 0.0) > 0:
            total_storage_pendente += float(c.valor_total_storage or 0.0)
            if invoice_atrasado:
                alertas_invoice_atrasado += 1

    # Ordenação
    sort_map = {
        'id': Claim.id,
        'claim_number': Claim.claim_number,
        'processo': Claim.claim_number,
        'empresa': Claim.empresa_parceira,
        'empresa_parceira': Claim.empresa_parceira,
        'status': Claim.status,
        'cliente': Claim.cliente_nome,
        'cliente_nome': Claim.cliente_nome,
        'placa': Claim.placa,
        'indicacao': Claim.valor_indicacao,
        'valor_indicacao': Claim.valor_indicacao,
        'prazo_indicacao': Claim.prazo_indicacao,
        'storage': Claim.dias_storage,
        'prazo_storage': Claim.prazo_liberacao_storage,
        'invoice': Claim.valor_total_storage,
        'valor_total_storage': Claim.valor_total_storage,
        'data_criacao': Claim.data_criacao
    }
    target_sort_col = sort_map.get(sort_by, Claim.id)
    order_func = target_sort_col.desc() if sort_order == 'desc' else target_sort_col.asc()
    
    paginated = query.order_by(order_func).paginate(page=page, per_page=limit, error_out=False)

    dados = []
    for c in paginated.items:
        # Prazos calculados
        dias_para_indicacao = (c.prazo_indicacao - hoje).days if (c.prazo_indicacao and c.status_indicacao != 'Pago') else None
        dias_para_liberacao = (c.prazo_liberacao_storage - hoje).days if (c.prazo_liberacao_storage and c.status_storage == 'No Pátio') else None
        dias_para_pagamento_invoice = (c.prazo_pagamento_invoice - hoje).days if (c.prazo_pagamento_invoice and c.status_pagamento_storage != 'Pago') else None

        indicacao_atrasada = bool(c.prazo_indicacao and c.prazo_indicacao < hoje and c.status_indicacao != 'Pago')
        storage_vencendo_28d = bool(c.prazo_liberacao_storage and c.status_storage == 'No Pátio' and (c.prazo_liberacao_storage <= hoje or (dias_para_liberacao is not None and dias_para_liberacao <= 7)))
        invoice_atrasado = bool(c.prazo_pagamento_invoice and c.prazo_pagamento_invoice < hoje and c.status_pagamento_storage != 'Pago')

        dados.append({
            'id': c.id,
            'claim_number': c.claim_number,
            'empresa_parceira': c.empresa_parceira,
            'cliente_nome': c.cliente_nome,
            'cliente_telefone': c.cliente_telefone or '',
            'placa': c.placa,
            'modelo_moto': c.modelo_moto or '',
            'status': c.status,
            'data_acidente': c.data_acidente.strftime('%Y-%m-%d') if c.data_acidente else None,
            'data_aprovacao': c.data_aprovacao.strftime('%Y-%m-%d') if c.data_aprovacao else None,
            'valor_indicacao': float(c.valor_indicacao or 0.0),
            'prazo_indicacao': c.prazo_indicacao.strftime('%Y-%m-%d') if c.prazo_indicacao else None,
            'status_indicacao': c.status_indicacao,
            'data_pagamento_indicacao': c.data_pagamento_indicacao.strftime('%Y-%m-%d') if c.data_pagamento_indicacao else None,
            'dias_para_indicacao': dias_para_indicacao,
            'indicacao_atrasada': indicacao_atrasada,
            'data_entrada_storage': c.data_entrada_storage.strftime('%Y-%m-%d') if c.data_entrada_storage else None,
            'prazo_liberacao_storage': c.prazo_liberacao_storage.strftime('%Y-%m-%d') if c.prazo_liberacao_storage else None,
            'data_liberacao_storage': c.data_liberacao_storage.strftime('%Y-%m-%d') if c.data_liberacao_storage else None,
            'status_storage': c.status_storage,
            'valor_diaria_storage': float(c.valor_diaria_storage or 15.0),
            'dias_storage': int(c.dias_storage or 0),
            'valor_total_storage': float(c.valor_total_storage or 0.0),
            'dias_para_liberacao': dias_para_liberacao,
            'storage_vencendo_28d': storage_vencendo_28d,
            'data_envio_invoice': c.data_envio_invoice.strftime('%Y-%m-%d') if c.data_envio_invoice else None,
            'prazo_pagamento_invoice': c.prazo_pagamento_invoice.strftime('%Y-%m-%d') if c.prazo_pagamento_invoice else None,
            'status_pagamento_storage': c.status_pagamento_storage,
            'data_pagamento_storage': c.data_pagamento_storage.strftime('%Y-%m-%d') if c.data_pagamento_storage else None,
            'dias_para_pagamento_invoice': dias_para_pagamento_invoice,
            'invoice_atrasado': invoice_atrasado,
            'observacoes': c.observacoes or '',
            'criado_por_nome': c.criado_por_nome or 'System',
            'data_criacao': c.data_criacao.strftime('%Y-%m-%d %H:%M:%S') if c.data_criacao else None
        })

    return jsonify({
        'claims': dados,
        'itens': dados,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page,
        'resumo': {
            'total_claims': len(all_claims_global),
            'processos_abertos': processos_abertos,
            'total_indicacao_pendente': total_indicacao_pendente,
            'total_storage_pendente': total_storage_pendente,
            'motos_no_storage': motos_no_storage,
            'alertas_indicacao_atrasada': alertas_indicacao_atrasada,
            'alertas_storage_28d': alertas_storage_28d,
            'alertas_invoice_atrasado': alertas_invoice_atrasado
        }
    }), 200

@app.route('/api/claims', methods=['POST'])
@claims_required
def criar_claim():
    data = request.get_json() or {}
    claim_number = (data.get('claim_number') or '').strip()
    empresa_parceira = (data.get('empresa_parceira') or '').strip()
    cliente_nome = (data.get('cliente_nome') or '').strip()
    placa = (data.get('placa') or '').strip().upper().replace(' ', '')

    if not claim_number or not empresa_parceira or not cliente_nome or not placa:
        return jsonify({'error': 'Claim number, empresa parceira, cliente e placa são obrigatórios.'}), 400

    # Validação de unicidade do Claim Number
    existente = Claim.query.filter(db.func.lower(Claim.claim_number) == claim_number.lower()).first()
    if existente:
        return jsonify({'error': f'O número de processo "{claim_number}" já está cadastrado no sistema (Processo #{existente.id} - {existente.cliente_nome}).'}), 400

    def parse_date(val):
        if not val: return None
        try:
            return datetime.strptime(val.strip(), '%Y-%m-%d').date()
        except Exception:
            return None

    data_acidente = parse_date(data.get('data_acidente'))
    data_aprovacao = parse_date(data.get('data_aprovacao'))
    data_entrada_storage = parse_date(data.get('data_entrada_storage'))
    data_liberacao_storage = parse_date(data.get('data_liberacao_storage'))
    data_envio_invoice = parse_date(data.get('data_envio_invoice'))
    
    valor_indicacao = float(data.get('valor_indicacao') or 0.0)
    valor_diaria_storage = float(data.get('valor_diaria_storage') or 15.00)

    # Auto-cálculo de prazos:
    # 1. Indicação: data_aprovacao + 14 dias
    prazo_indicacao = (data_aprovacao + timedelta(days=14)) if data_aprovacao else None
    
    # 2. Storage liberação: data_aprovacao + 28 dias
    prazo_liberacao_storage = (data_aprovacao + timedelta(days=28)) if data_aprovacao else None

    # 3. Cálculo de dias e valor de storage
    dias_storage = 0
    valor_total_storage = 0.0
    if data_entrada_storage:
        fim_storage = data_liberacao_storage or get_london_date()
        if fim_storage >= data_entrada_storage:
            dias_storage = (fim_storage - data_entrada_storage).days
            if dias_storage == 0: dias_storage = 1 # Mínimo 1 diária se entrou hoje
            valor_total_storage = round(dias_storage * valor_diaria_storage, 2)

    # 4. Prazo do Invoice: data_envio_invoice + 14 dias
    prazo_pagamento_invoice = (data_envio_invoice + timedelta(days=14)) if data_envio_invoice else None

    # Status automáticos
    status_storage = 'No Pátio'
    if data_liberacao_storage:
        status_storage = 'Liberado'
        if data_envio_invoice:
            status_storage = 'Invoice Enviado'

    criador = current_user.nome if (current_user and current_user.is_authenticated) else 'System'

    claim = Claim(
        claim_number=claim_number,
        empresa_parceira=empresa_parceira,
        cliente_nome=cliente_nome,
        cliente_telefone=(data.get('cliente_telefone') or '').strip(),
        placa=placa,
        modelo_moto=(data.get('modelo_moto') or '').strip(),
        status='Em Aberto',
        data_acidente=data_acidente,
        data_aprovacao=data_aprovacao,
        valor_indicacao=valor_indicacao,
        prazo_indicacao=prazo_indicacao,
        status_indicacao='Pendente',
        data_entrada_storage=data_entrada_storage,
        prazo_liberacao_storage=prazo_liberacao_storage,
        data_liberacao_storage=data_liberacao_storage,
        status_storage=status_storage,
        valor_diaria_storage=valor_diaria_storage,
        dias_storage=dias_storage,
        valor_total_storage=valor_total_storage,
        data_envio_invoice=data_envio_invoice,
        prazo_pagamento_invoice=prazo_pagamento_invoice,
        status_pagamento_storage='Pendente',
        observacoes=(data.get('observacoes') or '').strip(),
        criado_por_nome=criador
    )
    db.session.add(claim)
    db.session.commit()

    registrar_log('CLAIM_CREATE', 'Claim', claim.id, f"Novo claim #{claim.claim_number} ({claim.empresa_parceira}) cadastrado para {claim.cliente_nome} (Placa: {claim.placa}) por {criador}")

    return jsonify({'success': True, 'message': 'Claim registrado com sucesso!', 'id': claim.id}), 201

@app.route('/api/claims/<int:id>', methods=['PUT'])
@claims_required
def atualizar_claim(id):
    claim = db.session.get(Claim, id)
    if not claim:
        return jsonify({'error': 'Claim não encontrado.'}), 404

    data = request.get_json() or {}

    def parse_date(val):
        if val is None: return None
        val_str = str(val).strip()
        if not val_str: return None
        try:
            return datetime.strptime(val_str, '%Y-%m-%d').date()
        except Exception:
            return None

    if 'claim_number' in data and data['claim_number'].strip():
        novo_num = data['claim_number'].strip()
        duplicado = Claim.query.filter(
            db.func.lower(Claim.claim_number) == novo_num.lower(),
            Claim.id != claim.id
        ).first()
        if duplicado:
            return jsonify({'error': f'O número de processo "{novo_num}" já pertence a outro Claim (ID #{duplicado.id} - {duplicado.cliente_nome}).'}), 400
        claim.claim_number = novo_num
    if 'empresa_parceira' in data and data['empresa_parceira'].strip():
        claim.empresa_parceira = data['empresa_parceira'].strip()
    if 'cliente_nome' in data and data['cliente_nome'].strip():
        claim.cliente_nome = data['cliente_nome'].strip()
    if 'cliente_telefone' in data:
        claim.cliente_telefone = data['cliente_telefone'].strip()
    if 'placa' in data and data['placa'].strip():
        claim.placa = data['placa'].strip().upper().replace(' ', '')
    if 'modelo_moto' in data:
        claim.modelo_moto = data['modelo_moto'].strip()
    if 'observacoes' in data:
        claim.observacoes = data['observacoes'].strip()

    # Datas e Prazos
    if 'data_acidente' in data:
        claim.data_acidente = parse_date(data['data_acidente'])
    if 'data_aprovacao' in data:
        claim.data_aprovacao = parse_date(data['data_aprovacao'])
        if claim.data_aprovacao:
            claim.prazo_indicacao = claim.data_aprovacao + timedelta(days=14)
            claim.prazo_liberacao_storage = claim.data_aprovacao + timedelta(days=28)
        else:
            claim.prazo_indicacao = None
            claim.prazo_liberacao_storage = None

    if 'valor_indicacao' in data:
        claim.valor_indicacao = float(data['valor_indicacao'] or 0.0)

    if 'status_indicacao' in data and data['status_indicacao'].strip():
        claim.status_indicacao = data['status_indicacao'].strip()
        if claim.status_indicacao == 'Pago' and not claim.data_pagamento_indicacao:
            claim.data_pagamento_indicacao = get_london_date()

    if 'data_pagamento_indicacao' in data:
        claim.data_pagamento_indicacao = parse_date(data['data_pagamento_indicacao'])
        if claim.data_pagamento_indicacao:
            claim.status_indicacao = 'Pago'

    # Storage
    if 'data_entrada_storage' in data:
        claim.data_entrada_storage = parse_date(data['data_entrada_storage'])
    if 'data_liberacao_storage' in data:
        claim.data_liberacao_storage = parse_date(data['data_liberacao_storage'])
        if claim.data_liberacao_storage and claim.status_storage == 'No Pátio':
            claim.status_storage = 'Liberado'

    if 'valor_diaria_storage' in data:
        claim.valor_diaria_storage = float(data['valor_diaria_storage'] or 15.0)

    # Recalcular storage
    if claim.data_entrada_storage:
        fim_storage = claim.data_liberacao_storage or get_london_date()
        if fim_storage >= claim.data_entrada_storage:
            claim.dias_storage = (fim_storage - claim.data_entrada_storage).days
            if claim.dias_storage == 0: claim.dias_storage = 1
            claim.valor_total_storage = round(claim.dias_storage * float(claim.valor_diaria_storage or 15.0), 2)

    # Invoices
    if 'data_envio_invoice' in data:
        claim.data_envio_invoice = parse_date(data['data_envio_invoice'])
        if claim.data_envio_invoice:
            claim.prazo_pagamento_invoice = claim.data_envio_invoice + timedelta(days=14)
            if claim.status_storage in ['No Pátio', 'Liberado']:
                claim.status_storage = 'Invoice Enviado'
        else:
            claim.prazo_pagamento_invoice = None

    if 'status_pagamento_storage' in data and data['status_pagamento_storage'].strip():
        claim.status_pagamento_storage = data['status_pagamento_storage'].strip()
        if claim.status_pagamento_storage == 'Pago':
            claim.status_storage = 'Pago'
            if not claim.data_pagamento_storage:
                claim.data_pagamento_storage = get_london_date()

    if 'data_pagamento_storage' in data:
        claim.data_pagamento_storage = parse_date(data['data_pagamento_storage'])
        if claim.data_pagamento_storage:
            claim.status_pagamento_storage = 'Pago'
            claim.status_storage = 'Pago'

    # Auto-conclusão: Se indicação está paga e storage pago (ou liberado sem cobrança de storage), e não foi cancelado
    if claim.status != 'Cancelado':
        if 'status' in data and data['status'].strip():
            claim.status = data['status'].strip()
        elif claim.status_indicacao == 'Pago' and (claim.status_pagamento_storage == 'Pago' or float(claim.valor_total_storage or 0.0) == 0):
            claim.status = 'Concluido'

    db.session.commit()
    operador = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('CLAIM_UPDATE', 'Claim', claim.id, f"Claim #{claim.claim_number} ({claim.empresa_parceira}) atualizado por {operador}")

    return jsonify({'success': True, 'message': 'Claim atualizado com sucesso!'}), 200

@app.route('/api/claims/<int:id>', methods=['DELETE'])
@claims_required
def deletar_claim(id):
    claim = db.session.get(Claim, id)
    if not claim:
        return jsonify({'error': 'Claim não encontrado.'}), 404

    num = claim.claim_number
    emp = claim.empresa_parceira
    db.session.delete(claim)
    db.session.commit()

    operador = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('CLAIM_DELETE', 'Claim', id, f"Claim #{num} ({emp}) excluído por {operador}")

    return jsonify({'success': True, 'message': 'Claim excluído com sucesso.'}), 200

# --- USER MANAGEMENT API ROUTES ---

@app.route('/api/usuarios', methods=['GET'])
@admin_required
def listar_usuarios():
    usuarios = User.query.order_by(User.id.asc()).all()
    dados = []
    for u in usuarios:
        dados.append({
            'id': u.id,
            'nome': u.nome,
            'email': u.email,
            'role': u.role,
            'is_admin': bool(u.is_admin),
            'perm_alugueis': bool(u.perm_alugueis),
            'perm_claims': bool(u.perm_claims),
            'ativo': u.ativo,
            'data_criacao': u.data_criacao.strftime('%Y-%m-%d %H:%M:%S') if u.data_criacao else None
        })
    return jsonify({
        'usuarios': dados,
        'current_user_id': current_user.id
    }), 200

@app.route('/api/usuarios', methods=['POST'])
@admin_required
def criar_usuario():
    data = request.get_json() or {}
    nome = data.get('nome', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    is_admin = bool(data.get('is_admin', False))
    perm_alugueis = bool(data.get('perm_alugueis', True))
    perm_claims = bool(data.get('perm_claims', False))
    
    if not nome or not email or not password:
        return jsonify({'error': 'Name, email, and password are required'}), 400
        
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'An account with this email address already exists'}), 400
        
    # Definir role descritiva
    role_desc = 'admin' if is_admin else 'staff'
    
    novo_user = User(
        nome=nome,
        email=email,
        role=role_desc,
        is_admin=is_admin,
        perm_alugueis=perm_alugueis,
        perm_claims=perm_claims,
        ativo=True
    )
    novo_user.set_password(password)
    
    db.session.add(novo_user)
    db.session.commit()
    
    perm_textos = []
    if is_admin: perm_textos.append('Admin')
    if perm_alugueis: perm_textos.append('Aluguel / Venda')
    if perm_claims: perm_textos.append('Claims')
    registrar_log('USER_CREATE', 'User', novo_user.id, f"Novo usuário cadastrado: {novo_user.nome} ({novo_user.email}) com permissões: {', '.join(perm_textos)}")

    return jsonify({
        'message': 'User created successfully',
        'usuario': {
            'id': novo_user.id,
            'nome': novo_user.nome,
            'email': novo_user.email,
            'role': novo_user.role,
            'is_admin': novo_user.is_admin,
            'perm_alugueis': novo_user.perm_alugueis,
            'perm_claims': novo_user.perm_claims,
            'ativo': novo_user.ativo
        }
    }), 201

@app.route('/api/usuarios/<int:user_id>', methods=['PUT'])
@admin_required
def atualizar_usuario(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json() or {}
    alteracoes = []
    
    # Check if modifying name
    if 'nome' in data and data['nome'].strip():
        if user.nome != data['nome'].strip():
            alteracoes.append(f"nome de '{user.nome}' para '{data['nome'].strip()}'")
            user.nome = data['nome'].strip()
        
    # Check if modifying permissions
    if 'is_admin' in data:
        novo_admin = bool(data['is_admin'])
        if user.id == current_user.id and not novo_admin:
            return jsonify({'error': 'You cannot remove your own administrator privileges'}), 400
        if user.is_admin != novo_admin:
            alteracoes.append(f"admin={'Ativado' if novo_admin else 'Desativado'}")
            user.is_admin = novo_admin
            user.role = 'admin' if novo_admin else 'staff'

    if 'perm_alugueis' in data:
        nova_perm_alug = bool(data['perm_alugueis'])
        if user.perm_alugueis != nova_perm_alug:
            alteracoes.append(f"aluguel_venda={'Ativado' if nova_perm_alug else 'Desativado'}")
            user.perm_alugueis = nova_perm_alug

    if 'perm_claims' in data:
        nova_perm_claims = bool(data['perm_claims'])
        if user.perm_claims != nova_perm_claims:
            alteracoes.append(f"modulo_claims={'Ativado' if nova_perm_claims else 'Desativado'}")
            user.perm_claims = nova_perm_claims
            
    # Check if modifying status (ativo)
    if 'ativo' in data:
        novo_status = bool(data['ativo'])
        if user.id == current_user.id and not novo_status:
            return jsonify({'error': 'You cannot suspend your own account'}), 400
        if user.ativo != novo_status:
            status_txt = "Ativado" if novo_status else "Suspenso"
            alteracoes.append(f"status alterado para {status_txt}")
            user.ativo = novo_status
        
    # Check if updating password
    if 'password' in data and data['password']:
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        user.set_password(data['password'])
        alteracoes.append("senha redefinida")
        
    db.session.commit()
    
    if alteracoes:
        registrar_log('USER_UPDATE', 'User', user.id, f"Usuário {user.nome}: {', '.join(alteracoes)}")

    return jsonify({
        'message': 'User updated successfully',
        'usuario': {
            'id': user.id,
            'nome': user.nome,
            'email': user.email,
            'role': user.role,
            'is_admin': user.is_admin,
            'perm_alugueis': user.perm_alugueis,
            'perm_claims': user.perm_claims,
            'ativo': user.ativo
        }
    }), 200

@app.route('/api/usuarios/<int:user_id>', methods=['DELETE'])
@admin_required
def deletar_usuario(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.id == current_user.id:
        return jsonify({'error': 'You cannot delete your own account'}), 400
        
    nome_antigo = user.nome
    email_antigo = user.email

    try:
        # Decouple foreign key references in audit logs so historical activity is preserved
        AuditLog.query.filter_by(id_usuario=user_id).update({'id_usuario': None}, synchronize_session=False)
        db.session.delete(user)
        db.session.commit()
        
        registrar_log('USER_DELETE', 'User', user_id, f"Usuário excluído: {nome_antigo} ({email_antigo})")
        return jsonify({'message': f'User {nome_antigo} deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500

@app.route('/api/perfil/alterar-senha', methods=['POST'])
@login_required
def alterar_propria_senha():
    data = request.get_json() or {}
    senha_atual = (data.get('senha_atual') or '').strip()
    nova_senha = data.get('nova_senha') or ''
    confirmar_senha = data.get('confirmar_senha') or ''

    if not senha_atual or not nova_senha or not confirmar_senha:
        return jsonify({'error': 'Todos os campos de senha são obrigatórios.'}), 400

    if not current_user.check_password(senha_atual):
        return jsonify({'error': 'A senha atual informada está incorreta.'}), 400

    if len(nova_senha) < 6:
        return jsonify({'error': 'A nova senha deve ter no mínimo 6 caracteres.'}), 400

    if nova_senha != confirmar_senha:
        return jsonify({'error': 'A confirmação de senha não confere com a nova senha.'}), 400

    if senha_atual == nova_senha:
        return jsonify({'error': 'A nova senha deve ser diferente da senha atual.'}), 400

    try:
        current_user.set_password(nova_senha)
        db.session.commit()
        registrar_log('PASSWORD_CHANGE', 'User', current_user.id, f"Usuário {current_user.nome} alterou a própria senha")
        return jsonify({'success': True, 'message': 'Sua senha foi alterada com sucesso!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Erro ao salvar nova senha: {str(e)}'}), 500

@app.route('/api/auditoria', methods=['GET'])
@admin_required
def listar_auditoria():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    acao = request.args.get('acao', '', type=str)
    data_filtro = request.args.get('data', '', type=str)
    sort_by = request.args.get('sort_by', 'data_hora', type=str).strip().lower()
    sort_order = request.args.get('sort_order', 'desc', type=str).strip().lower()
    
    query = AuditLog.query
    if search:
        search_clean = search.strip().replace(' ', '')
        search_term = f"%{search.strip()}%"
        search_plate_term = f"%{search_clean}%"
        query = query.filter(db.or_(
            AuditLog.usuario_nome.ilike(search_term),
            AuditLog.descricao.ilike(search_term),
            AuditLog.descricao.ilike(search_plate_term),
            AuditLog.entidade.ilike(search_term),
            AuditLog.entidade_id.ilike(search_term),
            AuditLog.entidade_id.ilike(search_plate_term)
        ))
    if acao:
        query = query.filter(AuditLog.acao == acao)
        
    if data_filtro:
        try:
            dt_inicio = datetime.strptime(data_filtro, "%Y-%m-%d")
            dt_fim = dt_inicio + timedelta(days=1)
            query = query.filter(AuditLog.data_hora >= dt_inicio, AuditLog.data_hora < dt_fim)
        except ValueError:
            pass
            
    sort_map = {
        'data_hora': AuditLog.data_hora,
        'data': AuditLog.data_hora,
        'date': AuditLog.data_hora,
        'usuario_nome': AuditLog.usuario_nome,
        'usuario': AuditLog.usuario_nome,
        'user': AuditLog.usuario_nome,
        'acao': AuditLog.acao,
        'action': AuditLog.acao,
        'entidade': AuditLog.entidade,
        'entidade_id': AuditLog.entidade_id,
        'descricao': AuditLog.descricao
    }
    target_col = sort_map.get(sort_by, AuditLog.data_hora)
    order_func = target_col.desc() if sort_order == 'desc' else target_col.asc()
    paginated = query.order_by(order_func).paginate(page=page, per_page=limit, error_out=False)
    
    itens = [{
        'id': a.id,
        'data_hora': a.data_hora.isoformat() if a.data_hora else None,
        'usuario_nome': a.usuario_nome or 'System',
        'acao': a.acao,
        'entidade': a.entidade,
        'entidade_id': a.entidade_id,
        'descricao': a.descricao,
        'ip_origem': a.ip_origem
    } for a in paginated.items]
    
    return jsonify({
        'itens': itens,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page
    })

# --- CRUD ROUTES ---

@app.route('/api/clientes', methods=['POST'])
@alugueis_required
def criar_cliente():
    nome = request.form.get('nome')
    telefone = request.form.get('telefone')
    email = request.form.get('email')
    endereco = request.form.get('endereco')
    
    if not nome or not telefone:
        return jsonify({'error': 'Missing required fields (full name and phone are required)', 'erro': 'Dados incompletos (nome e telefone são obrigatórios)'}), 400
    
    nome = nome.strip()
    telefone = telefone.strip()
    endereco = endereco.strip() if endereco else None

    # Optional email: check uniqueness only if provided
    email_clean = email.strip() if (email and email.strip()) else None
    if email_clean:
        if Client.query.filter(db.func.lower(Client.email) == email_clean.lower()).first():
            return jsonify({'error': 'Email already registered', 'erro': 'Email já cadastrado'}), 400
        
    # Security: Validate upload file extensions
    for campo_file in ['habilitacao', 'habilitacao_verso', 'cbt', 'comprovante_endereco']:
        if campo_file in request.files:
            f = request.files[campo_file]
            if f and f.filename and not is_allowed_file(f.filename):
                return jsonify({'error': 'Invalid file format. Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': 'Formato de arquivo inválido. Permitido apenas JPG, PNG, WEBP e PDF.'}), 400

    url_hab = None
    url_hab_verso = None
    url_cbt = None
    url_comp_end = None
    
    if 'habilitacao' in request.files:
        f = request.files['habilitacao']
        if f.filename:
            nome_arq = werkzeug.utils.secure_filename(f"{int(get_local_now().timestamp())}_{f.filename}")
            nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
            url_hab = f"/static/uploads/{nome_salvo}"

    if 'habilitacao_verso' in request.files:
        f = request.files['habilitacao_verso']
        if f.filename:
            nome_arq = werkzeug.utils.secure_filename(f"{int(get_local_now().timestamp())}_verso_{f.filename}")
            nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
            url_hab_verso = f"/static/uploads/{nome_salvo}"

    if 'cbt' in request.files:
        f = request.files['cbt']
        if f.filename:
            nome_arq = werkzeug.utils.secure_filename(f"{int(get_local_now().timestamp())}_cbt_{f.filename}")
            nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
            url_cbt = f"/static/uploads/{nome_salvo}"
            
    if 'comprovante_endereco' in request.files:
        f = request.files['comprovante_endereco']
        if f.filename:
            nome_arq = werkzeug.utils.secure_filename(f"{int(get_local_now().timestamp())}_comp_end_{f.filename}")
            nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
            url_comp_end = f"/static/uploads/{nome_salvo}"
            
    novo_cliente = Client(
        nome=nome,
        telefone=telefone,
        email=email_clean,
        endereco=endereco,
        url_habilitacao=url_hab,
        url_habilitacao_verso=url_hab_verso,
        url_cbt=url_cbt,
        url_comprovante_endereco=url_comp_end
    )
    db.session.add(novo_cliente)
    db.session.commit()
    
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('CREATE_CLIENT', 'Client', novo_cliente.id, f"Cliente {novo_cliente.nome} cadastrado por {operador_atual}")

    return jsonify({'message': 'Customer registered successfully', 'mensagem': 'Cliente cadastrado com sucesso', 'id': novo_cliente.id}), 201

@app.route('/api/motos', methods=['POST'])
@alugueis_required
def criar_moto():
    dados = request.get_json()
    if not dados or not all(k in dados for k in ('placa', 'modelo', 'cor')):
        return jsonify({'error': 'Missing required fields (registration plate, model and colour are required)', 'erro': 'Dados incompletos'}), 400
        
    placa = str(dados['placa']).strip().replace(' ', '').upper()
    if not placa:
        return jsonify({'error': 'Invalid registration plate', 'erro': 'Placa inválida'}), 400

    if Motorcycle.query.filter_by(placa=placa).first():
        return jsonify({'error': 'Registration plate already registered', 'erro': 'Placa já cadastrada'}), 400
        
    vencimento_mot = None
    if dados.get('vencimento_mot'):
        try:
            vencimento_mot = datetime.strptime(dados['vencimento_mot'], "%Y-%m-%d").date()
        except ValueError:
            pass

    vencimento_tax = None
    if dados.get('vencimento_tax'):
        try:
            vencimento_tax = datetime.strptime(dados['vencimento_tax'], "%Y-%m-%d").date()
        except ValueError:
            pass

    nova_moto = Motorcycle(
        placa=placa,
        modelo=dados['modelo'].strip(),
        cor=dados['cor'].strip(),
        status=dados.get('status', MotoStatus.AVAILABLE.value),
        milhagem_atual=int(dados.get('milhagem_atual') or 0),
        vencimento_mot=vencimento_mot,
        vencimento_tax=vencimento_tax
    )
    db.session.add(nova_moto)
    db.session.commit()
    
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('MOTO_CREATE', 'Motorcycle', nova_moto.placa, f"Moto {nova_moto.placa} ({nova_moto.modelo}) cadastrada por {operador_atual} (Milhagem: {nova_moto.milhagem_atual} mi)")

    return jsonify({'message': 'Motorbike registered successfully', 'mensagem': 'Moto cadastrada com sucesso', 'placa': nova_moto.placa}), 201

@app.route('/api/clientes', methods=['GET'])
@alugueis_required
def listar_clientes():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    sort_by = request.args.get('sort_by', 'id', type=str).strip().lower()
    sort_order = request.args.get('sort_order', 'desc', type=str).strip().lower()
    
    query = Client.query
    if search:
        search_term = f"%{search}%"
        query = query.filter(db.or_(
            Client.nome.ilike(search_term),
            Client.telefone.ilike(search_term),
            Client.email.ilike(search_term)
        ))
    
    sort_map = {
        'id': Client.id,
        'nome': Client.nome,
        'name': Client.nome,
        'telefone': Client.telefone,
        'phone': Client.telefone,
        'email': Client.email,
        'endereco': Client.endereco,
        'address': Client.endereco
    }
    target_col = sort_map.get(sort_by, Client.id)
    order_func = target_col.desc() if sort_order == 'desc' else target_col.asc()
    paginated = query.order_by(order_func).paginate(page=page, per_page=limit, error_out=False)
    
    itens = [{
        'id': c.id, 'nome': c.nome, 'telefone': c.telefone, 'email': c.email, 'endereco': c.endereco,
        'url_habilitacao': c.url_habilitacao,
        'url_habilitacao_verso': c.url_habilitacao_verso,
        'url_cbt': c.url_cbt,
        'url_comprovante_endereco': c.url_comprovante_endereco
    } for c in paginated.items]
    
    return jsonify({
        'itens': itens,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page
    })

@app.route('/api/clientes/<int:id>', methods=['PUT'])
@alugueis_required
def atualizar_cliente(id):
    cliente = db.session.get(Client, id)
    if not cliente:
        return jsonify({'error': 'Customer not found', 'erro': 'Cliente não encontrado'}), 404
        
    if request.is_json:
        dados = request.get_json() or {}
        if 'nome' in dados: cliente.nome = dados['nome'].strip() if dados['nome'] else cliente.nome
        if 'telefone' in dados: cliente.telefone = dados['telefone'].strip() if dados['telefone'] else cliente.telefone
        if 'email' in dados:
            raw_email = dados['email']
            email_clean = raw_email.strip() if (raw_email and raw_email.strip()) else None
            if email_clean:
                outro = Client.query.filter(db.func.lower(Client.email) == email_clean.lower(), Client.id != id).first()
                if outro: return jsonify({'error': 'Email already registered for another customer', 'erro': 'Email já cadastrado por outro cliente'}), 400
            cliente.email = email_clean
        if 'endereco' in dados: cliente.endereco = dados['endereco'].strip() if dados['endereco'] else None
    else:
        # Security: Validate upload file extensions
        for campo_file in ['habilitacao', 'habilitacao_verso', 'cbt', 'comprovante_endereco']:
            if campo_file in request.files:
                f = request.files[campo_file]
                if f and f.filename and not is_allowed_file(f.filename):
                    return jsonify({'error': 'Invalid file format. Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': 'Formato de arquivo inválido. Permitido apenas JPG, PNG, WEBP e PDF.'}), 400

        if 'nome' in request.form: cliente.nome = request.form['nome'].strip()
        if 'telefone' in request.form: cliente.telefone = request.form['telefone'].strip()
        if 'endereco' in request.form: cliente.endereco = request.form['endereco'].strip() if request.form['endereco'] else None
        if 'email' in request.form:
            raw_email = request.form['email']
            email_clean = raw_email.strip() if (raw_email and raw_email.strip()) else None
            if email_clean:
                outro = Client.query.filter(db.func.lower(Client.email) == email_clean.lower(), Client.id != id).first()
                if outro: return jsonify({'error': 'Email already registered for another customer', 'erro': 'Email já cadastrado por outro cliente'}), 400
            cliente.email = email_clean
            
        if 'habilitacao' in request.files:
            f = request.files['habilitacao']
            if f.filename:
                nome_arq = werkzeug.utils.secure_filename(f"{int(get_local_now().timestamp())}_{f.filename}")
                nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
                cliente.url_habilitacao = f"/static/uploads/{nome_salvo}"

        if 'habilitacao_verso' in request.files:
            f = request.files['habilitacao_verso']
            if f.filename:
                nome_arq = werkzeug.utils.secure_filename(f"{int(get_local_now().timestamp())}_verso_{f.filename}")
                nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
                cliente.url_habilitacao_verso = f"/static/uploads/{nome_salvo}"

        if 'cbt' in request.files:
            f = request.files['cbt']
            if f.filename:
                nome_arq = werkzeug.utils.secure_filename(f"{int(get_local_now().timestamp())}_cbt_{f.filename}")
                nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
                cliente.url_cbt = f"/static/uploads/{nome_salvo}"
                
        if 'comprovante_endereco' in request.files:
            f = request.files['comprovante_endereco']
            if f.filename:
                nome_arq = werkzeug.utils.secure_filename(f"{int(get_local_now().timestamp())}_comp_end_{f.filename}")
                nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
                cliente.url_comprovante_endereco = f"/static/uploads/{nome_salvo}"
    
    db.session.commit()
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('CLIENT_UPDATE', 'Client', cliente.id, f"Cliente {cliente.nome} atualizado por {operador_atual}")

    return jsonify({'message': 'Customer updated successfully', 'mensagem': 'Cliente atualizado com sucesso'}), 200

@app.route('/api/motos', methods=['GET'])
@alugueis_required
def listar_motos():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    sort_by = request.args.get('sort_by', 'placa', type=str).strip().lower()
    sort_order = request.args.get('sort_order', 'asc', type=str).strip().lower()
    
    query = Motorcycle.query
    if search:
        search_clean = search.strip().replace(' ', '')
        search_term = f"%{search.strip()}%"
        search_plate_term = f"%{search_clean}%"
        query = query.filter(db.or_(
            Motorcycle.placa.ilike(search_plate_term),
            Motorcycle.placa.ilike(search_term),
            Motorcycle.modelo.ilike(search_term),
            Motorcycle.cor.ilike(search_term),
            Motorcycle.status.ilike(search_term)
        ))
        
    sort_map = {
        'placa': Motorcycle.placa,
        'reg': Motorcycle.placa,
        'modelo': Motorcycle.modelo,
        'model': Motorcycle.modelo,
        'cor': Motorcycle.cor,
        'colour': Motorcycle.cor,
        'color': Motorcycle.cor,
        'status': Motorcycle.status,
        'milhagem_atual': Motorcycle.milhagem_atual,
        'mileage': Motorcycle.milhagem_atual,
        'vencimento_mot': Motorcycle.vencimento_mot,
        'mot': Motorcycle.vencimento_mot,
        'vencimento_tax': Motorcycle.vencimento_tax,
        'tax': Motorcycle.vencimento_tax
    }
    target_col = sort_map.get(sort_by, Motorcycle.placa)
    order_func = target_col.desc() if sort_order == 'desc' else target_col.asc()
    paginated = query.order_by(order_func).paginate(page=page, per_page=limit, error_out=False)
    
    itens = [{
        'placa': m.placa,
        'modelo': m.modelo,
        'cor': m.cor,
        'status': m.status,
        'milhagem_atual': int(m.milhagem_atual or 0),
        'vencimento_mot': m.vencimento_mot.strftime('%Y-%m-%d') if m.vencimento_mot else None,
        'vencimento_tax': m.vencimento_tax.strftime('%Y-%m-%d') if m.vencimento_tax else None
    } for m in paginated.items]
    
    return jsonify({
        'itens': itens,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page
    })

@app.route('/api/motos/<placa>', methods=['PUT'])
@alugueis_required
def atualizar_moto(placa):
    moto = db.session.get(Motorcycle, placa)
    if not moto:
        return jsonify({'error': 'Motorbike not found', 'erro': 'Moto não encontrada'}), 404
        
    dados = request.get_json()
    status_antigo = moto.status
    if 'modelo' in dados: moto.modelo = dados['modelo']
    if 'cor' in dados: moto.cor = dados['cor']
    if 'status' in dados: moto.status = dados['status']
    if 'milhagem_atual' in dados and dados['milhagem_atual'] is not None:
        try:
            moto.milhagem_atual = int(dados['milhagem_atual'])
        except (ValueError, TypeError):
            pass
    
    if 'vencimento_mot' in dados:
        if dados['vencimento_mot']:
            try:
                moto.vencimento_mot = datetime.strptime(dados['vencimento_mot'], "%Y-%m-%d").date()
            except ValueError:
                pass
        else:
            moto.vencimento_mot = None
            
    if 'vencimento_tax' in dados:
        if dados['vencimento_tax']:
            try:
                moto.vencimento_tax = datetime.strptime(dados['vencimento_tax'], "%Y-%m-%d").date()
            except ValueError:
                pass
        else:
            moto.vencimento_tax = None
    
    db.session.commit()
    
    if 'status' in dados and dados['status'] != status_antigo:
        operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
        registrar_log('MOTO_STATUS_CHANGE', 'Motorcycle', placa, f"Status da moto {placa} alterado de '{status_antigo}' para '{dados['status']}' por {operador_atual}")

    return jsonify({'message': 'Motorbike updated successfully', 'mensagem': 'Moto atualizada com sucesso'})

@app.route('/api/contratos', methods=['POST'])
@alugueis_required
def criar_contrato():
    id_cliente = request.form.get('id_cliente')
    placa = request.form.get('placa')
    tipo_contrato = request.form.get('tipo_contrato', ContractType.RENT.value)
    if tipo_contrato not in [ContractType.RENT.value, ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value]:
        tipo_contrato = ContractType.RENT.value

    dia_pagamento_semanal = int(request.form.get('dia_pagamento_semanal', 0)) if request.form.get('dia_pagamento_semanal') else 0
    valor_aluguel_semanal = float(request.form.get('valor_aluguel_semanal', 250.0)) if request.form.get('valor_aluguel_semanal') else 0.0
    valor_deposito = float(request.form.get('valor_deposito', 0.0)) if request.form.get('valor_deposito') else 0.0
    observacoes = request.form.get('observacoes')
    
    # Specific Sale Fields
    categoria_historico = request.form.get('categoria_historico', 'Clear')
    valor_venda_veiculo = float(request.form.get('valor_venda_veiculo') or 0.0) if request.form.get('valor_venda_veiculo') else None
    acessorios_extras = (request.form.get('acessorios_extras') or '').strip() or 'None'
    valor_total_extras = float(request.form.get('valor_total_extras') or 0.0)
    valor_admin_fee = float(request.form.get('valor_admin_fee') or 0.0)
    valor_total_venda = float(request.form.get('valor_total_venda') or 0.0) if request.form.get('valor_total_venda') else None
    valor_entrada = float(request.form.get('valor_entrada') or 0.0)
    saldo_devedor = float(request.form.get('saldo_devedor') or 0.0)
    cronograma_parcelas_raw = request.form.get('cronograma_parcelas', '[]')
    
    # Calculate or validate valor_total_venda with extras
    if tipo_contrato == ContractType.SALE_FULL.value:
        if not valor_total_venda or valor_total_venda <= 0.0:
            valor_total_venda = (valor_venda_veiculo or 0.0) + valor_total_extras
    elif tipo_contrato == ContractType.SALE_INSTALLMENT.value:
        if not valor_total_venda or valor_total_venda <= 0.0:
            valor_total_venda = (valor_venda_veiculo or 0.0) + valor_admin_fee + valor_total_extras
        if not saldo_devedor or saldo_devedor <= 0.0:
            saldo_devedor = max(0.0, valor_total_venda - valor_entrada)
    
    cronograma_parcelas = []
    if cronograma_parcelas_raw:
        try:
            cronograma_parcelas = json.loads(cronograma_parcelas_raw) if isinstance(cronograma_parcelas_raw, str) else cronograma_parcelas_raw
        except Exception:
            cronograma_parcelas = []
    
    if 'fotos' not in request.files:
        return jsonify({'error': 'Initial check-out inspection photos are required', 'erro': 'A vistoria de saída (foto) é obrigatória'}), 400
        
    fotos = request.files.getlist('fotos')
    if not fotos or fotos[0].filename == '':
        return jsonify({'error': 'No photos selected for inspection', 'erro': 'Nenhuma foto selecionada'}), 400
        
    if 'seguro' not in request.files:
        return jsonify({'error': 'Insurance certificate document is required to open a contract', 'erro': 'O arquivo do Seguro é obrigatório para abrir um contrato'}), 400
        
    # Security: Validate upload file extensions for photos and insurance
    for f in fotos:
        if f.filename and not is_allowed_file(f.filename):
            return jsonify({'error': 'Invalid inspection photo format. Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': 'Formato de foto inválido. Permitido apenas JPG, PNG, WEBP e PDF.'}), 400
            
    arq_seguro_check = request.files['seguro']
    if arq_seguro_check.filename and not is_allowed_file(arq_seguro_check.filename):
        return jsonify({'error': 'Invalid insurance document format. Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': 'Formato de documento de seguro inválido. Permitido apenas JPG, PNG, WEBP e PDF.'}), 400

    cliente = db.session.get(Client, id_cliente)
    if not cliente:
        return jsonify({'error': 'Customer not found', 'erro': 'Cliente não encontrado'}), 400

    moto = db.session.get(Motorcycle, placa)
    if not moto or moto.status not in [MotoStatus.AVAILABLE.value, 'Disponível']:
        return jsonify({'error': 'Motorbike is not available', 'erro': 'Moto não está disponível'}), 400
        
    # Save inspection photos
    urls_fotos = []
    timestamp = get_local_now().strftime("%Y%m%d%H%M%S")
    for i, foto in enumerate(fotos):
        if foto.filename:
            filename = werkzeug.utils.secure_filename(foto.filename)
            nome_arquivo = f"{timestamp}_{i}_{filename}"
            nome_salvo = salvar_arquivo_otimizado(foto, nome_arquivo)
            urls_fotos.append(f"/static/uploads/{nome_salvo}")
            
    url_foto_str = ",".join(urls_fotos)
    
    # Save insurance document
    url_seguro = None
    arq_seguro = request.files['seguro']
    if arq_seguro.filename:
        filename_seguro = werkzeug.utils.secure_filename(arq_seguro.filename)
        nome_seguro = f"{timestamp}_seguro_{filename_seguro}"
        nome_salvo = salvar_arquivo_otimizado(arq_seguro, nome_seguro)
        url_seguro = f"/static/uploads/{nome_salvo}"

    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'

    # Milhagem Inicial (UK Miles)
    milhagem_inicial = int(request.form.get('milhagem_inicial') or (moto.milhagem_atual or 0))
    moto.milhagem_atual = milhagem_inicial

    # Create Contract with frozen immutable snapshots
    novo_contrato = Contract(
        id_cliente=id_cliente,
        placa=placa,
        tipo_contrato=tipo_contrato,
        dia_pagamento_semanal=dia_pagamento_semanal,
        valor_aluguel_semanal=valor_aluguel_semanal if tipo_contrato == ContractType.RENT.value else 0.0,
        valor_deposito=valor_deposito if tipo_contrato == ContractType.RENT.value else valor_entrada,
        categoria_historico=categoria_historico if tipo_contrato != ContractType.RENT.value else None,
        valor_venda_veiculo=valor_venda_veiculo,
        acessorios_extras=acessorios_extras if tipo_contrato != ContractType.RENT.value else None,
        valor_admin_fee=valor_admin_fee if tipo_contrato == ContractType.SALE_INSTALLMENT.value else 0.0,
        valor_total_venda=valor_total_venda,
        valor_entrada=valor_entrada if tipo_contrato == ContractType.SALE_INSTALLMENT.value else 0.0,
        saldo_devedor=saldo_devedor if tipo_contrato == ContractType.SALE_INSTALLMENT.value else 0.0,
        cronograma_parcelas_json=json.dumps(cronograma_parcelas) if (tipo_contrato == ContractType.SALE_INSTALLMENT.value and cronograma_parcelas) else None,
        url_seguro=url_seguro,
        status=ContractStatus.ACTIVE.value,
        criado_por_nome=operador_atual,
        milhagem_inicial=milhagem_inicial,
        data_ultima_checagem_seguro=get_local_now().date(),
        status_seguro='Valid',
        seguro_verificado_por=operador_atual,
        # Immutable Snapshot of Customer at creation time
        cliente_nome=cliente.nome,
        cliente_telefone=cliente.telefone,
        cliente_email=cliente.email,
        cliente_endereco=cliente.endereco,
        url_habilitacao=cliente.url_habilitacao,
        url_habilitacao_verso=cliente.url_habilitacao_verso,
        url_cbt=cliente.url_cbt,
        url_comprovante_endereco=cliente.url_comprovante_endereco,
        # Immutable Snapshot of Motorbike at creation time
        moto_modelo=moto.modelo,
        moto_cor=moto.cor,
        moto_placa=moto.placa
    )
    db.session.add(novo_contrato)
    
    # Update motorbike status according to contract type
    if tipo_contrato in [ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value]:
        moto.status = MotoStatus.SOLD.value
    else:
        moto.status = MotoStatus.RENTED.value
    
    db.session.flush() # Retrieve generated contract ID
    
    hoje = get_local_now()
    
    # Financial Transactions Provisioning (All transactions start PENDING upon contract creation)
    if tipo_contrato == ContractType.RENT.value:
        # 1. Security deposit transaction for rental
        deposito = FinancialTransaction(
            id_contrato=novo_contrato.id,
            tipo=TransactionType.DEPOSIT.value,
            data_vencimento=hoje,
            valor=valor_deposito,
            status=TransactionStatus.PENDING.value
        )
        db.session.add(deposito)
        
        # 2. Week 1 rent (due today upon collection)
        aluguel_semana_1 = FinancialTransaction(
            id_contrato=novo_contrato.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=hoje,
            valor=valor_aluguel_semanal,
            status=TransactionStatus.PENDING.value
        )
        db.session.add(aluguel_semana_1)
        
        # 3. Week 2 rent (due on next recurring payment day)
        days_ahead = dia_pagamento_semanal - hoje.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        proximo_vencimento = hoje + timedelta(days=days_ahead)
        
        aluguel_semana_2 = FinancialTransaction(
            id_contrato=novo_contrato.id,
            tipo=TransactionType.RENT.value,
            data_vencimento=proximo_vencimento,
            valor=valor_aluguel_semanal,
            status=TransactionStatus.PENDING.value
        )
        db.session.add(aluguel_semana_2)

    elif tipo_contrato == ContractType.SALE_FULL.value:
        # Full payment at once (pending upon contract creation)
        tx_venda = FinancialTransaction(
            id_contrato=novo_contrato.id,
            tipo=TransactionType.SALE_FULL.value,
            data_vencimento=hoje,
            valor=valor_total_venda or valor_venda_veiculo or 0.0,
            status=TransactionStatus.PENDING.value
        )
        db.session.add(tx_venda)

    elif tipo_contrato == ContractType.SALE_INSTALLMENT.value:
        # 1. Sale Down Payment / Deposit (pending upon contract creation, clearly distinct from rental deposit)
        if valor_entrada > 0:
            tx_entrada = FinancialTransaction(
                id_contrato=novo_contrato.id,
                tipo=TransactionType.SALE_DEPOSIT.value,
                data_vencimento=hoje,
                valor=valor_entrada,
                status=TransactionStatus.PENDING.value
            )
            db.session.add(tx_entrada)

        # 2. Installments schedule transactions (all pending with respective due dates)
        for i, parcela in enumerate(cronograma_parcelas):
            p_valor = float(parcela.get('valor', 0.0))
            p_venc_str = parcela.get('vencimento') or parcela.get('data_vencimento')
            p_venc = hoje
            if p_venc_str:
                try:
                    clean_d = str(p_venc_str).split('T')[0].strip()
                    p_venc = datetime.strptime(clean_d, '%Y-%m-%d')
                except Exception:
                    p_venc = hoje + timedelta(days=30 * (i + 1))
            else:
                p_venc = hoje + timedelta(days=30 * (i + 1))
                
            tx_parcela = FinancialTransaction(
                id_contrato=novo_contrato.id,
                tipo=TransactionType.SALE_INSTALLMENT.value,
                data_vencimento=p_venc,
                valor=p_valor,
                status=TransactionStatus.PENDING.value
            )
            db.session.add(tx_parcela)
    
    # Create Check-out Inspection with mileage
    nova_vistoria = Inspection(
        id_contrato=novo_contrato.id,
        tipo=InspectionType.CHECK_OUT.value,
        milhagem=milhagem_inicial,
        observacoes=observacoes,
        url_fotos=url_foto_str,
        realizado_por_nome=operador_atual
    )
    db.session.add(nova_vistoria)
    
    db.session.commit()
    
    if tipo_contrato == ContractType.RENT.value:
        detalhes_log = f"Contrato de Aluguel #{novo_contrato.id} aberto para moto {moto.placa} por {operador_atual} (Milhagem: {milhagem_inicial} mi, Aluguel: £{valor_aluguel_semanal:.2f}/sem, Depósito: £{valor_deposito:.2f})"
    elif tipo_contrato == ContractType.SALE_FULL.value:
        detalhes_log = f"Contrato de Venda à Vista #{novo_contrato.id} aberto para moto {moto.placa} por {operador_atual} (Preço: £{valor_total_venda:.2f}, Categoria: {categoria_historico}). Moto marcada como Vendida (Sold)."
    else:
        detalhes_log = f"Contrato de Venda Parcelada #{novo_contrato.id} aberto para moto {moto.placa} por {operador_atual} (Total: £{valor_total_venda:.2f}, Entrada: £{valor_entrada:.2f}, Saldo: £{saldo_devedor:.2f}, {len(cronograma_parcelas)} parcelas, Categoria: {categoria_historico}). Moto marcada como Vendida (Sold)."

    registrar_log('CREATE_CONTRACT', 'Contract', novo_contrato.id, detalhes_log)
    
    return jsonify({
        'message': 'Contract and initial inspection created successfully', 
        'mensagem': 'Contrato e vistoria criados com sucesso', 
        'id': novo_contrato.id,
        'tipo_contrato': tipo_contrato
    }), 201

@app.route('/api/contratos/<int:id>/seguro', methods=['PUT'])
@alugueis_required
def atualizar_seguro_contrato(id):
    contrato = db.session.get(Contract, id)
    if not contrato:
        return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404
        
    if 'seguro' in request.files:
        f = request.files['seguro']
        if f.filename:
            if not is_allowed_file(f.filename):
                return jsonify({'error': 'Invalid file format. Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': 'Formato de arquivo inválido.'}), 400
            nome_arq = werkzeug.utils.secure_filename(f"{int(get_local_now().timestamp())}_seguro_upd_{f.filename}")
            nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
            contrato.url_seguro = f"/static/uploads/{nome_salvo}"
            db.session.commit()
            operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
            registrar_log('INSURANCE_UPLOADED', 'Contract', contrato.id, f"Apólice de seguro do contrato #{contrato.id} atualizada por {operador_atual}.")
            return jsonify({'message': 'Insurance document updated successfully', 'mensagem': 'Seguro atualizado'})
            
    return jsonify({'error': 'No file uploaded', 'erro': 'Nenhum arquivo enviado'}), 400

@app.route('/api/contratos/<int:id>/verificar-seguro', methods=['POST'])
@alugueis_required
def verificar_seguro_contrato(id):
    contrato = db.session.get(Contract, id)
    if not contrato:
        return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404
        
    dados = request.get_json() or {}
    novo_status = dados.get('status', 'Valid')
    if novo_status not in ['Valid', 'Cancelled']:
        novo_status = 'Valid'
        
    operador = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    hoje_date = get_local_now().date()
    
    contrato.data_ultima_checagem_seguro = hoje_date
    contrato.status_seguro = novo_status
    contrato.seguro_verificado_por = operador
    db.session.commit()
    
    if novo_status == 'Valid':
        registrar_log('INSURANCE_VERIFIED', 'Contract', contrato.id, f"Seguro da moto {contrato.placa} verificado como VÁLIDO no askMID por {operador} no Contrato #{contrato.id} (Próxima checagem em 15 dias)")
        msg = "Insurance verified as VALID on askMID. Next check scheduled in 15 dias."
    else:
        registrar_log('INSURANCE_CANCELLED', 'Contract', contrato.id, f"ALERTA: Seguro da moto {contrato.placa} reportado CANCELADO/INVÁLIDO no askMID por {operador} no Contrato #{contrato.id}")
        msg = "ALARM: Insurance flagged as CANCELLED/INVALID on askMID."
        
    return jsonify({
        'message': msg,
        'status_seguro': contrato.status_seguro,
        'data_ultima_checagem_seguro': contrato.data_ultima_checagem_seguro.strftime('%Y-%m-%d'),
        'seguro_verificado_por': contrato.seguro_verificado_por
    })

# --- DIGITAL SIGNATURES & CONTRACT ATTACHMENTS ---

@app.route('/api/contratos/<int:id>/assinar', methods=['POST'])
@alugueis_required
def assinar_contrato(id):
    contrato = db.session.get(Contract, id)
    if not contrato:
        return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404

    dados = request.get_json() or {}
    tipo_assinatura = dados.get('tipo', 'inicial') # 'inicial' ou 'devolucao'
    assinatura_base64 = dados.get('assinatura') # Data URL 'data:image/png;base64,...'

    if not assinatura_base64 or not assinatura_base64.startswith('data:image/'):
        return jsonify({'error': 'Invalid signature data', 'erro': 'Dados de assinatura inválidos'}), 400

    import base64
    try:
        header, encoded = assinatura_base64.split(',', 1)
        data = base64.b64decode(encoded)
        
        agora = get_london_now()
        timestamp = agora.strftime("%Y%m%d_%H%M%S")
        filename = f"sig_{tipo_assinatura}_{id}_{timestamp}.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'wb') as f:
            f.write(data)
            
        url_salva = f"/static/uploads/{filename}"
        operador = current_user.nome if (current_user and current_user.is_authenticated) else 'System'

        # Salva como naive datetime local de Londres no DB SQLite para consistência
        agora_london_naive = agora.replace(tzinfo=None)

        if tipo_assinatura == 'devolucao':
            contrato.assinatura_cliente_devolucao = url_salva
            contrato.data_assinatura_devolucao = agora_london_naive
            registrar_log('CONTRACT_SIGNED_RETURN', 'Contract', contrato.id, f"Contrato #{contrato.id} assinado digitalmente na devolução por {contrato.cliente.nome if contrato.cliente else 'Cliente'} (Operador: {operador})")
        else:
            contrato.assinatura_cliente_inicial = url_salva
            contrato.data_assinatura_inicial = agora_london_naive
            registrar_log('CONTRACT_SIGNED_START', 'Contract', contrato.id, f"Contrato #{contrato.id} assinado digitalmente na retirada por {contrato.cliente.nome if contrato.cliente else 'Cliente'} (Operador: {operador})")

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Signature saved successfully',
            'url': url_salva,
            'data_assinatura': agora.strftime('%d/%m/%Y %H:%M')
        }), 200

    except Exception as e:
        print(f"[Signature Error]: {e}")
        return jsonify({'error': 'Failed to save signature', 'erro': f'Erro ao salvar assinatura: {str(e)}'}), 500

@app.route('/api/contratos/<int:id>/anexos', methods=['POST'])
@alugueis_required
def upload_anexos_contrato(id):
    try:
        contrato = db.session.get(Contract, id)
        if not contrato:
            return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404

        if 'arquivos' not in request.files:
            return jsonify({'error': 'No files provided', 'erro': 'Nenhum arquivo enviado'}), 400

        arquivos = request.files.getlist('arquivos')
        if not arquivos or arquivos[0].filename == '':
            return jsonify({'error': 'No files selected', 'erro': 'Nenhum arquivo selecionado'}), 400

        tipo_anexo = request.form.get('tipo', 'initial_contract')
        
        # Validar extensões
        for arq in arquivos:
            if arq.filename and not is_allowed_file(arq.filename):
                return jsonify({'error': f'Invalid file format for "{arq.filename}". Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': f'Formato inválido para "{arq.filename}". Permitido apenas JPG, PNG, WEBP e PDF.'}), 400

        salvos = []
        timestamp = get_local_now().strftime("%Y%m%d%H%M%S")
        for i, arq in enumerate(arquivos):
            if arq.filename:
                orig_name = arq.filename
                ext = ''
                if '.' in orig_name:
                    ext = '.' + orig_name.rsplit('.', 1)[1].lower()
                else:
                    ext = '.webp' if (arq.content_type and 'webp' in arq.content_type) else ('.pdf' if (arq.content_type and 'pdf' in arq.content_type) else '.jpg')

                base_name = os.path.splitext(orig_name)[0]
                sec_base = werkzeug.utils.secure_filename(base_name) or f"doc_{i}"
                sec_name = f"{sec_base}{ext}"
                nome_arq = f"{timestamp}_anexo_{id}_{i}_{sec_name}"
                nome_salvo = salvar_arquivo_otimizado(arq, nome_arq)
                url_arquivo = f"/static/uploads/{nome_salvo}"

                novo_anexo = ContractAttachment(
                    id_contrato=id,
                    tipo=tipo_anexo,
                    url_arquivo=url_arquivo,
                    nome_original=orig_name[:120] if orig_name else sec_name
                )
                db.session.add(novo_anexo)
                salvos.append(novo_anexo)

        db.session.commit()
        operador = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
        registrar_log('ATTACHMENT_UPLOADED', 'Contract', id, f"{len(salvos)} anexo(s) ({tipo_anexo}) anexados ao Contrato #{id} por {operador}")

        return jsonify({
            'success': True,
            'message': f'{len(salvos)} attachment(s) uploaded successfully',
            'anexos': [{
                'id': a.id,
                'tipo': a.tipo,
                'url_arquivo': a.url_arquivo,
                'nome_original': a.nome_original,
                'data_criacao': a.data_criacao.strftime('%d/%m/%Y %H:%M')
            } for a in salvos]
        }), 201
    except Exception as e:
        db.session.rollback()
        print(f"[Upload Anexos Error] Falha ao processar anexos do contrato #{id}: {e}")
        return jsonify({
            'error': f'Failed to process upload: {str(e)}',
            'erro': f'Erro ao processar envio de arquivos: {str(e)}'
        }), 500

@app.route('/api/contratos/anexos/<int:anexo_id>', methods=['DELETE'])
@alugueis_required
def deletar_anexo_contrato(anexo_id):
    try:
        anexo = db.session.get(ContractAttachment, anexo_id)
        if not anexo:
            return jsonify({'error': 'Attachment not found', 'erro': 'Anexo não encontrado'}), 404

        id_contrato = anexo.id_contrato
        delete_file_if_exists(anexo.url_arquivo)
        db.session.delete(anexo)
        db.session.commit()

        operador = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
        registrar_log('ATTACHMENT_DELETED', 'Contract', id_contrato, f"Anexo #{anexo_id} excluído do Contrato #{id_contrato} por {operador}")

        return jsonify({'success': True, 'message': 'Attachment deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        print(f"[Delete Anexo Error] Falha ao deletar anexo #{anexo_id}: {e}")
        return jsonify({
            'error': f'Failed to delete attachment: {str(e)}',
            'erro': f'Erro ao deletar anexo: {str(e)}'
        }), 500

@app.route('/api/contratos/<int:id>/cancelar', methods=['POST'])
@alugueis_required
def cancelar_contrato(id):
    """
    Cancela um contrato em andamento (Active ou Deposit_Hold).
    - Reverte o status da motocicleta para 'Available' (Disponível).
    - Cancela todas as cobranças pendentes vinculadas ao contrato.
    - Mantém pagamentos já realizados para histórico contábil.
    - Registra a justificativa/motivo na trilha de auditoria.
    """
    try:
        contrato = db.session.get(Contract, id)
        if not contrato:
            return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404

        if contrato.status in [ContractStatus.COMPLETED.value, 'Completed', 'Finalizado']:
            return jsonify({'error': 'Completed contracts cannot be cancelled', 'erro': 'Contratos finalizados não podem ser cancelados'}), 400

        if contrato.status in [ContractStatus.CANCELLED.value, 'Cancelled', 'Cancelado']:
            return jsonify({'error': 'Contract is already cancelled', 'erro': 'O contrato já está cancelado'}), 400

        data = request.get_json(silent=True) or request.form
        motivo = (data.get('motivo') or data.get('reason') or '').strip()
        if not motivo:
            return jsonify({'error': 'Cancellation reason is required', 'erro': 'O motivo do cancelamento é obrigatório'}), 400

        # 1. Atualiza status do contrato
        contrato.status = ContractStatus.CANCELLED.value
        if not contrato.data_devolucao:
            contrato.data_devolucao = get_local_now()

        # 2. Libera a moto vinculada de volta para Disponível
        placa = contrato.placa or contrato.moto_placa
        moto = db.session.get(Motorcycle, placa) if placa else None
        if moto and moto.status in [MotoStatus.ALUGADA.value, 'Rented', 'Alugada', MotoStatus.SOLD.value, 'Sold', 'Vendida']:
            moto.status = MotoStatus.DISPONIVEL.value

        # 3. Cancela cobranças pendentes (Opção A)
        transacoes = FinancialTransaction.query.filter_by(id_contrato=id).all()
        canceladas_count = 0
        for t in transacoes:
            if t.status in [TransactionStatus.PENDING.value, 'Pending', 'Pendente']:
                t.status = TransactionStatus.CANCELLED.value
                canceladas_count += 1

        db.session.commit()

        # 4. Trilha de auditoria
        operador = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
        detalhes_log = f"Contrato #{id} (Placa: {placa or 'N/A'}) cancelado por {operador}. Motivo: '{motivo}'. {canceladas_count} cobrança(s) pendente(s) cancelada(s). Moto liberada para Disponível."
        registrar_log('CONTRACT_CANCELLED', 'Contract', id, detalhes_log)

        return jsonify({
            'success': True,
            'message': 'Contract cancelled successfully',
            'status': ContractStatus.CANCELLED.value,
            'transacoes_canceladas': canceladas_count
        }), 200
    except Exception as e:
        db.session.rollback()
        print(f"[Cancel Contract Error] Erro ao cancelar contrato #{id}: {e}")
        return jsonify({
            'error': f'Failed to cancel contract: {str(e)}',
            'erro': f'Erro ao cancelar contrato: {str(e)}'
        }), 500

@app.route('/api/contratos', methods=['GET'])
@alugueis_required
def listar_contratos():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    tipo_filter = request.args.get('tipo', '', type=str).strip()
    sort_by = request.args.get('sort_by', 'id', type=str).strip().lower()
    sort_order = request.args.get('sort_order', 'desc', type=str).strip().lower()
    
    query = Contract.query.join(Client, Contract.id_cliente == Client.id)
    if search:
        search_clean = search.strip().replace(' ', '')
        search_term = f"%{search.strip()}%"
        search_plate_term = f"%{search_clean}%"
        query = query.filter(db.or_(
            Contract.id.cast(db.String).ilike(search_term),
            Contract.placa.ilike(search_plate_term),
            Contract.placa.ilike(search_term),
            Contract.status.ilike(search_term),
            Contract.tipo_contrato.ilike(search_term),
            Client.nome.ilike(search_term)
        ))

    if tipo_filter:
        if tipo_filter.lower() in ['sale', 'venda']:
            query = query.filter(Contract.tipo_contrato.in_([ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value]))
        elif tipo_filter.lower() in ['rent', 'aluguel']:
            query = query.filter(db.or_(Contract.tipo_contrato == ContractType.RENT.value, Contract.tipo_contrato == None))
        else:
            query = query.filter(Contract.tipo_contrato == tipo_filter)
        
    status_filter = request.args.get('status', '', type=str)
    if status_filter:
        if status_filter.lower() in ['deposit_hold', 'quarentena_deposito', 'quarentena']:
            query = query.filter(Contract.status.in_([ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito']))
        elif status_filter.lower() in ['active', 'ativo']:
            query = query.filter(Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']))
        elif status_filter.lower() in ['completed', 'finalizado']:
            query = query.filter(Contract.status.in_([ContractStatus.COMPLETED.value, 'Completed', 'Finalizado']))
        elif status_filter.lower() in ['cancelled', 'cancelado']:
            query = query.filter(Contract.status.in_([ContractStatus.CANCELLED.value, 'Cancelled', 'Cancelado']))
        else:
            query = query.filter(Contract.status == status_filter)
    else:
        nao_finalizados = request.args.get('nao_finalizados') == 'true' or request.args.get('ativos') == 'true'
        if nao_finalizados:
            query = query.filter(Contract.status.in_([
                ContractStatus.ACTIVE.value, 'Active', 'Ativo',
                ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito'
            ]))
        
    sort_map = {
        'id': Contract.id,
        'cliente': Client.nome,
        'customer': Client.nome,
        'placa': Contract.placa,
        'data_retirada': Contract.data_retirada,
        'data': Contract.data_retirada,
        'collection': Contract.data_retirada,
        'dia_pagamento_semanal': Contract.dia_pagamento_semanal,
        'due_day': Contract.dia_pagamento_semanal,
        'valor_aluguel_semanal': Contract.valor_aluguel_semanal,
        'rent': Contract.valor_aluguel_semanal,
        'data_devolucao': Contract.data_devolucao,
        'return': Contract.data_devolucao,
        'status': Contract.status,
        'tipo': Contract.tipo_contrato,
        'tipo_contrato': Contract.tipo_contrato,
        'status_seguro': Contract.status_seguro
    }
    target_col = sort_map.get(sort_by, Contract.id)
    order_func = target_col.desc() if sort_order == 'desc' else target_col.asc()
    paginated = query.order_by(order_func).paginate(page=page, per_page=limit, error_out=False)
    
    itens = [{
        'id': c.id, 
        'id_cliente': c.id_cliente, 
        'cliente_nome': c.cliente_nome or (c.cliente.nome if c.cliente else 'Customer'), 
        'placa': c.moto_placa or c.placa,
        'tipo_contrato': getattr(c, 'tipo_contrato', 'Rent') or 'Rent',
        'categoria_historico': c.categoria_historico,
        'valor_total_venda': float(c.valor_total_venda) if c.valor_total_venda is not None else None,
        'valor_entrada': float(c.valor_entrada) if c.valor_entrada is not None else 0.0,
        'saldo_devedor': float(c.saldo_devedor) if c.saldo_devedor is not None else 0.0,
        'data_retirada': c.data_retirada.isoformat() if c.data_retirada else None,
        'dia_pagamento_semanal': c.dia_pagamento_semanal,
        'valor_aluguel_semanal': c.valor_aluguel_semanal,
        'data_devolucao': c.data_devolucao.isoformat() if c.data_devolucao else None,
        'status': c.status,
        'url_seguro': c.url_seguro
    } for c in paginated.items]
    
    return jsonify({
        'itens': itens,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page
    })

@app.route('/api/contratos/<int:id>', methods=['GET'])
@alugueis_required
def detalhe_contrato(id):
    c = db.session.get(Contract, id)
    if not c:
        return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404
        
    cliente = db.session.get(Client, c.id_cliente) if c.id_cliente else None
    if not cliente and c.cliente:
        cliente = c.cliente
        
    moto = db.session.get(Motorcycle, c.placa) if c.placa else None
    if not moto and c.moto:
        moto = c.moto
    if not moto and c.placa:
        moto = Motorcycle.query.filter(db.func.lower(Motorcycle.placa) == c.placa.strip().lower()).first()
    
    transacoes = FinancialTransaction.query.filter_by(id_contrato=id).all()
    vistorias = Inspection.query.filter_by(id_contrato=id).all()
    
    # Contabilidade do Depósito (Depósito Inicial - Deduções de multas/danos pagos com depósito)
    deposito_pago = 0.0
    deducoes_deposito = 0.0
    deducoes_lista = []
    for t in transacoes:
        if t.status in [TransactionStatus.PAID.value, 'Paid', 'Pago']:
            if t.tipo in [TransactionType.DEPOSIT.value, 'Deposit', 'Deposito', 'Depósito']:
                deposito_pago += float(t.valor)
            elif t.forma_pagamento and 'deposit' in t.forma_pagamento.lower():
                deducoes_deposito += float(t.valor)
                deducoes_lista.append({
                    'id': t.id,
                    'tipo': t.tipo,
                    'valor': float(t.valor),
                    'forma_pagamento': t.forma_pagamento
                })
                
    saldo_deposito = max(0.0, deposito_pago - deducoes_deposito)
    
    # Identificar restituição de depósito concluída
    tx_restituicao = next((t for t in transacoes if t.tipo in [TransactionType.DEPOSIT_REFUND.value, 'Deposit_Refund', 'Devolucao_Deposito'] and t.status in [TransactionStatus.PAID.value, 'Paid', 'Pago']), None)
    valor_restituido = float(tx_restituicao.valor) if tx_restituicao else 0.0
    
    # Transações filtradas para o extrato do cliente (não exibe a devolução de caução como cobrança devida)
    transacoes_cliente = [t for t in transacoes if t.tipo not in [TransactionType.DEPOSIT_REFUND.value, 'Deposit_Refund', 'Devolucao_Deposito']]
    
    # 15-Day Insurance Compliance (askMID Verification) - apenas para contratos de aluguel (Rent)
    tipo_contrato_val = getattr(c, 'tipo_contrato', 'Rent') or 'Rent'
    is_venda = tipo_contrato_val in [ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value, 'Sale_Full', 'Sale_Installment']
    
    hoje = get_local_now().date()
    ultima_checagem = c.data_ultima_checagem_seguro or (c.data_retirada.date() if c.data_retirada else hoje)
    dias_desde_checagem = (hoje - ultima_checagem).days
    dias_para_proxima = max(0, 15 - dias_desde_checagem)
    checagem_seguro_devida = (dias_desde_checagem >= 15) if not is_venda else False
    
    is_completed = (c.status in [ContractStatus.COMPLETED.value, 'Completed', 'Finalizado', ContractStatus.CANCELLED.value, 'Cancelled', 'Cancelado'])
    
    # Parse cronograma se existir
    cronograma_parsed = []
    if c.cronograma_parcelas_json:
        try:
            cronograma_parsed = json.loads(c.cronograma_parcelas_json)
        except Exception:
            cronograma_parsed = []

    return jsonify({
        'id': c.id,
        'tipo_contrato': getattr(c, 'tipo_contrato', 'Rent') or 'Rent',
        'categoria_historico': c.categoria_historico,
        'valor_venda_veiculo': float(c.valor_venda_veiculo) if c.valor_venda_veiculo is not None else None,
        'acessorios_extras': c.acessorios_extras,
        'valor_admin_fee': float(c.valor_admin_fee) if c.valor_admin_fee is not None else 0.0,
        'valor_total_venda': float(c.valor_total_venda) if c.valor_total_venda is not None else None,
        'valor_entrada': float(c.valor_entrada) if c.valor_entrada is not None else 0.0,
        'saldo_devedor': float(c.saldo_devedor) if c.saldo_devedor is not None else 0.0,
        'cronograma_parcelas': cronograma_parsed,
        'id_cliente': c.id_cliente,
        'cliente': c.cliente_nome or (cliente.nome if cliente else 'Customer'),
        'cliente_nome': c.cliente_nome or (cliente.nome if cliente else 'Customer'),
        'telefone': c.cliente_telefone or (cliente.telefone if cliente else None),
        'cliente_telefone': c.cliente_telefone or (cliente.telefone if cliente else None),
        'endereco': c.cliente_endereco or (cliente.endereco if cliente else None),
        'cliente_endereco': c.cliente_endereco or (cliente.endereco if cliente else None),
        'email': c.cliente_email or (cliente.email if cliente else None),
        'cliente_email': c.cliente_email or (cliente.email if cliente else None),
        'url_habilitacao': c.url_habilitacao or (cliente.url_habilitacao if cliente else None),
        'url_habilitacao_verso': c.url_habilitacao_verso or (cliente.url_habilitacao_verso if cliente else None),
        'url_cbt': c.url_cbt or (cliente.url_cbt if cliente else None),
        'url_comprovante_endereco': c.url_comprovante_endereco or (cliente.url_comprovante_endereco if cliente else None),
        'placa': c.moto_placa or c.placa,
        'modelo': c.moto_modelo or (moto.modelo if moto else '-'),
        'moto_modelo': c.moto_modelo or (moto.modelo if moto else '-'),
        'cor': c.moto_cor or (moto.cor if moto else '-'),
        'moto_cor': c.moto_cor or (moto.cor if moto else '-'),
        'milhagem_atual_moto': int(moto.milhagem_atual or 0) if moto else 0,
        'milhagem_inicial': c.milhagem_inicial if c.milhagem_inicial is not None else 0,
        'milhagem_final': c.milhagem_final,
        'milhas_rodadas': (c.milhagem_final - (c.milhagem_inicial or 0)) if (c.milhagem_final is not None and c.milhagem_inicial is not None) else None,
        'assinatura_cliente_inicial': c.assinatura_cliente_inicial,
        'data_assinatura_inicial': c.data_assinatura_inicial.strftime('%d/%m/%Y %H:%M') if c.data_assinatura_inicial else None,
        'data_assinatura_inicial_uk': c.data_assinatura_inicial.strftime('%d/%m/%Y %H:%M') if c.data_assinatura_inicial else None,
        'assinatura_cliente_devolucao': c.assinatura_cliente_devolucao,
        'data_assinatura_devolucao': c.data_assinatura_devolucao.strftime('%d/%m/%Y %H:%M') if c.data_assinatura_devolucao else None,
        'data_assinatura_devolucao_uk': c.data_assinatura_devolucao.strftime('%d/%m/%Y %H:%M') if c.data_assinatura_devolucao else None,
        'anexos': [{
            'id': a.id,
            'tipo': a.tipo,
            'url_arquivo': a.url_arquivo,
            'nome_original': a.nome_original or 'Anexo',
            'data_criacao': a.data_criacao.strftime('%d/%m/%Y %H:%M') if a.data_criacao else None
        } for a in (c.anexos or [])],
        'vencimento_mot': moto.vencimento_mot.strftime('%Y-%m-%d') if (moto and moto.vencimento_mot) else None,
        'vencimento_tax': moto.vencimento_tax.strftime('%Y-%m-%d') if (moto and moto.vencimento_tax) else None,
        'data_retirada': c.data_retirada.isoformat() if c.data_retirada else None,
        'data_devolucao': c.data_devolucao.isoformat() if c.data_devolucao else None,
        'dia_pagamento_semanal': c.dia_pagamento_semanal,
        'valor_aluguel_semanal': float(c.valor_aluguel_semanal) if c.valor_aluguel_semanal else 0.0,
        'status': c.status,
        'is_completed': is_completed,
        'url_seguro': c.url_seguro,
        'url_comprovante_deposito': c.url_comprovante_deposito,
        'criado_por_nome': c.criado_por_nome or '',
        'data_ultima_checagem_seguro': c.data_ultima_checagem_seguro.strftime('%Y-%m-%d') if c.data_ultima_checagem_seguro else (c.data_retirada.strftime('%Y-%m-%d') if c.data_retirada else None),
        'status_seguro': c.status_seguro or 'Valid',
        'seguro_verificado_por': c.seguro_verificado_por or '',
        'dias_desde_checagem_seguro': None if is_venda else dias_desde_checagem,
        'dias_para_proxima_checagem_seguro': None if is_venda else dias_para_proxima,
        'checagem_seguro_devida': False if is_venda else checagem_seguro_devida,
        'deposito_pago': deposito_pago,
        'deducoes_deposito': deducoes_deposito,
        'saldo_deposito': saldo_deposito,
        'valor_restituido': valor_restituido,
        'deducoes_lista': deducoes_lista,
        'transacoes': [{
            'id': t.id,
            'tipo': t.tipo,
            'descricao': (
                f"Vehicle Sale - Instalment {[tx.id for tx in sorted([p for p in transacoes_cliente if str(p.tipo).lower() in ['sale_installment', 'venda_parcela']], key=lambda x: (x.data_vencimento or datetime.min, x.id))].index(t.id) + 1} of {len([p for p in transacoes_cliente if str(p.tipo).lower() in ['sale_installment', 'venda_parcela']])}"
                if str(t.tipo).lower() in ['sale_installment', 'venda_parcela'] and t.id in [p.id for p in transacoes_cliente if str(p.tipo).lower() in ['sale_installment', 'venda_parcela']]
                else obter_descricao_recibo_simples(t.tipo)
            ),
            'valor': float(t.valor),
            'status': t.status,
            'forma_pagamento': t.forma_pagamento,
            'registrado_por_nome': t.registrado_por_nome or '',
            'data_vencimento': t.data_vencimento.isoformat() if t.data_vencimento else None,
            'data_pagamento': t.data_pagamento.isoformat() if t.data_pagamento else None
        } for t in transacoes_cliente],
        'vistorias': [{
            'id': v.id,
            'tipo': v.tipo,
            'data_vistoria': v.data.isoformat() if v.data else None,
            'milhagem': v.milhagem,
            'foto_url': v.url_fotos,
            'observacoes': v.observacoes,
            'realizado_por_nome': v.realizado_por_nome or ''
        } for v in vistorias]
    })

@app.route('/api/contratos/<int:id>/cobrancas', methods=['POST'])
@alugueis_required
def criar_cobranca(id):
    c = db.session.get(Contract, id)
    if not c:
        return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404
        
    tipo = request.json.get('tipo')
    valor = request.json.get('valor')
    data_vencimento_str = request.json.get('data_vencimento')
    
    if not tipo or not valor or not data_vencimento_str:
        return jsonify({'error': 'Missing required fields (type, amount and due date are required)', 'erro': 'Dados incompletos'}), 400
        
    try:
        data_vencimento = datetime.strptime(data_vencimento_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({'error': 'Invalid due date format', 'erro': 'Data de vencimento inválida'}), 400
        
    tipo_map = {
        'sale_installment': TransactionType.SALE_INSTALLMENT.value,
        'sale_deposit': TransactionType.SALE_DEPOSIT.value,
        'sale_full': TransactionType.SALE_FULL.value,
        'rent': TransactionType.RENT.value,
        'deposit': TransactionType.DEPOSIT.value,
        'fine': TransactionType.FINE.value,
        'damage': TransactionType.DAMAGE.value,
        'other': 'Other'
    }
    tipo_final = tipo_map.get(str(tipo).strip().lower(), str(tipo).strip())

    nova_cobranca = FinancialTransaction(
        id_contrato=c.id,
        tipo=tipo_final,
        data_vencimento=data_vencimento,
        valor=float(valor),
        status=TransactionStatus.PENDING.value
    )
    db.session.add(nova_cobranca)
    db.session.commit()
    
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('CREATE_CHARGE', 'Transaction', nova_cobranca.id, f"Cobrança manual de £{float(valor):.2f} ({tipo_final}) gerada por {operador_atual} para o Contrato #{c.id}")

    return jsonify({'message': 'Charge created successfully', 'mensagem': 'Cobrança gerada com sucesso'}), 201

@app.route('/api/cobrancas/<int:id>/pagar', methods=['PUT'])
@alugueis_required
def pagar_cobranca(id):
    t = db.session.get(FinancialTransaction, id)
    if not t:
        return jsonify({'error': 'Charge not found', 'erro': 'Cobrança não encontrada'}), 404
        
    forma_pagamento = request.json.get('forma_pagamento')
    if not forma_pagamento:
        return jsonify({'error': 'Payment method is required', 'erro': 'Forma de pagamento é obrigatória'}), 400
        
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    t.status = TransactionStatus.PAID.value
    t.data_pagamento = get_local_now()
    t.forma_pagamento = forma_pagamento
    t.registrado_por_nome = operador_atual
    
    db.session.commit()
    registrar_log('PAYMENT_RECEIVED', 'Transaction', t.id, f"Baixa de £{float(t.valor):.2f} ({t.tipo}) confirmada via {forma_pagamento} por {operador_atual} no Contrato #{t.id_contrato}")
    return jsonify({'message': 'Payment marked successfully', 'mensagem': 'Baixa realizada com sucesso', 'forma_pagamento': t.forma_pagamento, 'registrado_por_nome': t.registrado_por_nome}), 200

@app.route('/api/vistorias', methods=['POST'])
@alugueis_required
def criar_vistoria():
    id_contrato = request.form.get('id_contrato')
    tipo = request.form.get('tipo')
    observacoes = request.form.get('observacoes')
    
    contrato = db.session.get(Contract, id_contrato) if id_contrato else None
    if not contrato:
        return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404

    moto = db.session.get(Motorcycle, contrato.placa) if contrato.placa else None
    is_venda = contrato.tipo_contrato in [ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value, 'Sale_Full', 'Sale_Installment']
    is_moto_sold = moto and moto.status == MotoStatus.SOLD.value

    if (is_venda or is_moto_sold) and str(tipo).strip().lower() in ['check-in', 'entrada', 'checkin']:
        return jsonify({
            'error': 'Check-in inspections (return) are not allowed for sold motorcycles / sale contracts.',
            'erro': 'Vistorias de devolução (Check-in) não são permitidas para motos vendidas ou contratos de venda.'
        }), 400

    if 'fotos' not in request.files:
        return jsonify({'error': 'No photos uploaded', 'erro': 'Nenhuma foto enviada'}), 400
        
    fotos = request.files.getlist('fotos')
    if not fotos or fotos[0].filename == '':
        return jsonify({'error': 'No photos selected', 'erro': 'Nenhuma foto selecionada'}), 400
        
    # Security: Validate upload file extensions
    for foto in fotos:
        if foto.filename and not is_allowed_file(foto.filename):
            return jsonify({'error': 'Invalid inspection photo format. Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': 'Formato de foto inválido. Permitido apenas JPG, PNG, WEBP e PDF.'}), 400

    urls_fotos = []
    timestamp = get_local_now().strftime("%Y%m%d%H%M%S")
    for i, foto in enumerate(fotos):
        if foto.filename:
            filename = werkzeug.utils.secure_filename(foto.filename)
            nome_arquivo = f"{timestamp}_{i}_{filename}"
            nome_salvo = salvar_arquivo_otimizado(foto, nome_arquivo)
            urls_fotos.append(f"/static/uploads/{nome_salvo}")
            
    url_foto_str = ",".join(urls_fotos)
    
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    
    milhagem_val = None
    if request.form.get('milhagem'):
        try:
            milhagem_val = int(request.form.get('milhagem'))
        except (ValueError, TypeError):
            milhagem_val = None

    nova_vistoria = Inspection(
        id_contrato=id_contrato,
        tipo=tipo,
        milhagem=milhagem_val,
        observacoes=observacoes,
        url_fotos=url_foto_str,
        realizado_por_nome=operador_atual
    )
    db.session.add(nova_vistoria)
    
    # Atualiza a milhagem da moto se a vistoria contiver uma milhagem maior, 
    # independentemente do tipo de vistoria
    moto = None
    contrato = db.session.get(Contract, id_contrato)
    if contrato and contrato.placa:
        moto = db.session.get(Motorcycle, contrato.placa)
        if moto and milhagem_val is not None:
            if milhagem_val > (moto.milhagem_atual or 0):
                moto.milhagem_atual = milhagem_val

    if tipo in [InspectionType.CHECK_IN.value, 'Check-in', 'Entrada']:
        if contrato:
            contrato.status = ContractStatus.DEPOSIT_HOLD.value
            contrato.data_devolucao = get_local_now()
            if milhagem_val is not None:
                contrato.milhagem_final = milhagem_val
            if moto:
                moto.status = MotoStatus.MAINTENANCE.value
                
    db.session.commit()
    
    milhas_txt = f" (Milhagem: {milhagem_val} mi)" if milhagem_val is not None else ""
    registrar_log('CREATE_INSPECTION', 'Inspection', nova_vistoria.id, f"Vistoria de {tipo} registrada por {operador_atual} no Contrato #{id_contrato}{milhas_txt}")
    if tipo in [InspectionType.CHECK_IN.value, 'Check-in', 'Entrada']:
        registrar_log('RETURN_VEHICLE', 'Contract', id_contrato, f"Moto devolvida / Check-in confirmado por {operador_atual} no Contrato #{id_contrato}{milhas_txt}")
    
    return jsonify({'message': 'Inspection recorded successfully', 'mensagem': 'Vistoria registrada com sucesso', 'id': nova_vistoria.id, 'url': url_foto_str}), 201

@app.route('/api/vistorias', methods=['GET'])
@alugueis_required
def listar_vistorias():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    tipo = request.args.get('tipo', '', type=str)
    data_filtro = request.args.get('data', '', type=str)
    contrato_id = request.args.get('contrato_id', type=int)
    sort_by = request.args.get('sort_by', 'data', type=str).strip().lower()
    sort_order = request.args.get('sort_order', 'desc', type=str).strip().lower()
    
    query = Inspection.query.join(Contract, Inspection.id_contrato == Contract.id).join(Client, Contract.id_cliente == Client.id)
    if contrato_id:
        query = query.filter(Inspection.id_contrato == contrato_id)
    if search:
        search_clean = search.strip().replace(' ', '')
        search_term = f"%{search.strip()}%"
        search_plate_term = f"%{search_clean}%"
        query = query.filter(db.or_(
            Inspection.id_contrato.cast(db.String).ilike(search_term),
            Inspection.tipo.ilike(search_term),
            Contract.placa.ilike(search_plate_term),
            Contract.placa.ilike(search_term),
            Client.nome.ilike(search_term),
            Inspection.observacoes.ilike(search_term)
        ))
        
    if tipo:
        t_lower = tipo.lower()
        if t_lower in ['check-out', 'checkout', 'saida', 'saída']:
            query = query.filter(Inspection.tipo.in_([InspectionType.CHECK_OUT.value, 'Check-out', 'Saída', 'Saida']))
        elif t_lower in ['check-in', 'checkin', 'entrada']:
            query = query.filter(Inspection.tipo.in_([InspectionType.CHECK_IN.value, 'Check-in', 'Entrada']))
        elif t_lower in ['incident', 'ocorrencia', 'ocorrência']:
            query = query.filter(Inspection.tipo.in_([InspectionType.INCIDENT.value, 'Incident', 'Ocorrência', 'Ocorrencia']))
        else:
            query = query.filter(Inspection.tipo == tipo)
        
    if data_filtro:
        try:
            dt_inicio = datetime.strptime(data_filtro, "%Y-%m-%d")
            dt_fim = dt_inicio + timedelta(days=1)
            query = query.filter(Inspection.data >= dt_inicio, Inspection.data < dt_fim)
        except ValueError:
            pass
            
    sort_map = {
        'id': Inspection.id,
        'contrato': Inspection.id_contrato,
        'id_contrato': Inspection.id_contrato,
        'placa': Contract.placa,
        'cliente': Client.nome,
        'tipo': Inspection.tipo,
        'data': Inspection.data,
        'realizado_por_nome': Inspection.realizado_por_nome
    }
    target_col = sort_map.get(sort_by, Inspection.data)
    order_func = target_col.desc() if sort_order == 'desc' else target_col.asc()
    paginated = query.options(
        contains_eager(Inspection.contrato).contains_eager(Contract.cliente)
    ).order_by(order_func).paginate(page=page, per_page=limit, error_out=False)
    
    itens = [{
        'id': v.id,
        'id_contrato': v.id_contrato,
        'data_vistoria': v.data.isoformat(),
        'tipo': v.tipo,
        'milhagem': v.milhagem,
        'foto_url': v.url_fotos,
        'observacoes': v.observacoes,
        'realizado_por_nome': v.realizado_por_nome or '',
        'placa': v.contrato.placa if v.contrato else '',
        'cliente': v.contrato.cliente.nome if v.contrato and v.contrato.cliente else ''
    } for v in paginated.items]
    
    return jsonify({
        'itens': itens,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page
    })

# --- DASHBOARD & JOBS ---

@app.route('/api/financeiro', methods=['GET'])
@alugueis_required
def listar_financeiro():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    status_filtro = request.args.get('status', '', type=str)
    tipo_filtro = request.args.get('tipo', '', type=str)
    pendentes = request.args.get('pendentes') == 'true'
    data_inicio = request.args.get('data_inicio', '', type=str).strip()
    data_fim = request.args.get('data_fim', '', type=str).strip()
    campo_data = request.args.get('campo_data', 'vencimento', type=str).strip().lower()
    sort_by = request.args.get('sort_by', 'data_vencimento', type=str).strip().lower()
    sort_order = request.args.get('sort_order', 'asc', type=str).strip().lower()
    
    query = FinancialTransaction.query.outerjoin(Contract, FinancialTransaction.id_contrato == Contract.id).outerjoin(Client, Contract.id_cliente == Client.id)
    if search:
        search_clean = search.strip().replace(' ', '')
        search_term = f"%{search.strip()}%"
        search_plate_term = f"%{search_clean}%"
        query = query.filter(db.or_(
            FinancialTransaction.id.cast(db.String).ilike(search_term),
            FinancialTransaction.id_contrato.cast(db.String).ilike(search_term),
            FinancialTransaction.tipo.ilike(search_term),
            FinancialTransaction.status.ilike(search_term),
            FinancialTransaction.forma_pagamento.ilike(search_term),
            FinancialTransaction.valor.cast(db.String).ilike(search_term),
            Contract.placa.ilike(search_plate_term),
            Contract.placa.ilike(search_term),
            Client.nome.ilike(search_term)
        ))
        
    if status_filtro:
        if status_filtro.lower() in ['overdue', 'vencidos', 'vencido']:
            agora = get_local_now()
            query = query.filter(
                FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
                FinancialTransaction.data_vencimento < agora
            )
        elif status_filtro.lower() in ['paid', 'pago']:
            query = query.filter(FinancialTransaction.status.in_([TransactionStatus.PAID.value, 'Paid', 'Pago']))
        elif status_filtro.lower() in ['cancelled', 'cancelado']:
            query = query.filter(FinancialTransaction.status.in_([TransactionStatus.CANCELLED.value, 'Cancelled', 'Cancelado']))
        elif status_filtro.lower() in ['pending', 'pendente']:
            query = query.filter(FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']))
        else:
            query = query.filter(FinancialTransaction.status == status_filtro)
    elif pendentes:
        query = query.filter(FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']))
        
    if tipo_filtro:
        tipo_lower = tipo_filtro.lower()
        if tipo_lower in ['sales_all', 'sales', 'vendas']:
            query = query.filter(FinancialTransaction.tipo.in_([
                TransactionType.SALE_FULL.value, TransactionType.SALE_DEPOSIT.value, TransactionType.SALE_INSTALLMENT.value,
                'Sale_Full', 'Sale_Deposit', 'Sale_Installment', 'Venda_Vista', 'Venda_Entrada', 'Venda_Parcela'
            ]))
        elif tipo_lower in ['sale_full', 'venda_vista']:
            query = query.filter(FinancialTransaction.tipo.in_([TransactionType.SALE_FULL.value, 'Sale_Full', 'Venda_Vista']))
        elif tipo_lower in ['sale_deposit', 'venda_entrada']:
            query = query.filter(FinancialTransaction.tipo.in_([TransactionType.SALE_DEPOSIT.value, 'Sale_Deposit', 'Venda_Entrada']))
        elif tipo_lower in ['sale_installment', 'venda_parcela']:
            query = query.filter(FinancialTransaction.tipo.in_([TransactionType.SALE_INSTALLMENT.value, 'Sale_Installment', 'Venda_Parcela']))
        elif tipo_lower in ['rent', 'aluguel']:
            query = query.filter(FinancialTransaction.tipo.in_([TransactionType.RENT.value, 'Rent', 'Aluguel']))
        elif tipo_lower in ['deposit', 'deposito', 'depósito']:
            query = query.filter(FinancialTransaction.tipo.in_([TransactionType.DEPOSIT.value, 'Deposit', 'Deposito', 'Depósito']))
        elif tipo_lower in ['deposit_refund', 'devolucao_deposito']:
            query = query.filter(FinancialTransaction.tipo.in_([TransactionType.DEPOSIT_REFUND.value, 'Deposit_Refund', 'Devolucao_Deposito']))
        elif tipo_lower in ['fine', 'multa']:
            query = query.filter(FinancialTransaction.tipo.in_([TransactionType.FINE.value, 'Fine', 'Multa']))
        elif tipo_lower in ['damage', 'dano']:
            query = query.filter(FinancialTransaction.tipo.in_([TransactionType.DAMAGE.value, 'Damage', 'Dano']))
        else:
            query = query.filter(FinancialTransaction.tipo == tipo_filtro)

    # Date Range Filter
    col_data = FinancialTransaction.data_pagamento if campo_data == 'pagamento' else FinancialTransaction.data_vencimento
    if data_inicio:
        try:
            dt_ini = datetime.strptime(data_inicio, "%Y-%m-%d")
            query = query.filter(col_data >= dt_ini)
        except ValueError:
            pass
    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(col_data < dt_fim)
        except ValueError:
            pass

    # Server-side Sorting
    sort_map = {
        'id': FinancialTransaction.id,
        'contrato': FinancialTransaction.id_contrato,
        'id_contrato': FinancialTransaction.id_contrato,
        'cliente': Client.nome,
        'nome': Client.nome,
        'placa': Contract.placa,
        'tipo': FinancialTransaction.tipo,
        'valor': FinancialTransaction.valor,
        'data_vencimento': FinancialTransaction.data_vencimento,
        'vencimento': FinancialTransaction.data_vencimento,
        'data_pagamento': FinancialTransaction.data_pagamento,
        'pagamento': FinancialTransaction.data_pagamento,
        'status': FinancialTransaction.status,
    }
    target_col = sort_map.get(sort_by, FinancialTransaction.data_vencimento)
    order_func = target_col.desc() if sort_order == 'desc' else target_col.asc()
    paginated = query.options(
        contains_eager(FinancialTransaction.contrato).contains_eager(Contract.cliente)
    ).order_by(order_func).paginate(page=page, per_page=limit, error_out=False)
    
    itens = [{
        'id': t.id,
        'id_contrato': t.id_contrato,
        'tipo': t.tipo,
        'descricao': obter_descricao_recibo_simples(t.tipo),
        'data_vencimento': t.data_vencimento.isoformat() if t.data_vencimento else None,
        'data_pagamento': t.data_pagamento.isoformat() if t.data_pagamento else None,
        'valor': float(t.valor),
        'status': t.status,
        'forma_pagamento': t.forma_pagamento or '',
        'registrado_por_nome': t.registrado_por_nome or '',
        'placa': t.contrato.placa if t.contrato else '',
        'cliente': t.contrato.cliente.nome if (t.contrato and t.contrato.cliente) else ''
    } for t in paginated.items]
    
    return jsonify({
        'itens': itens,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page
    })

@app.route('/api/financeiro/pagar/<int:id>', methods=['POST', 'PUT'])
@alugueis_required
def pagar_transacao(id):
    t = db.session.get(FinancialTransaction, id)
    if not t:
        return jsonify({'error': 'Transaction not found', 'erro': 'Transação não encontrada'}), 404
        
    forma = 'Cash'
    if request.is_json and request.json:
        forma = request.json.get('forma_pagamento', 'Cash')
    elif request.form and 'forma_pagamento' in request.form:
        forma = request.form.get('forma_pagamento', 'Cash')
        
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    t.status = TransactionStatus.PAID.value
    t.data_pagamento = get_local_now()
    t.forma_pagamento = forma
    t.registrado_por_nome = operador_atual
    db.session.commit()
    registrar_log('PAYMENT_RECEIVED', 'Transaction', t.id, f"Baixa de £{float(t.valor):.2f} ({t.tipo}) confirmada via {forma} por {operador_atual} no Contrato #{t.id_contrato}")
    return jsonify({'message': 'Transaction marked as paid successfully', 'mensagem': 'Transação paga com sucesso', 'forma_pagamento': t.forma_pagamento, 'registrado_por_nome': t.registrado_por_nome}), 200

@app.route('/api/financeiro/<int:id>/reverter', methods=['POST', 'PUT'])
@app.route('/api/cobrancas/<int:id>/reverter', methods=['POST', 'PUT'])
@alugueis_required
def reverter_pagamento(id):
    t = db.session.get(FinancialTransaction, id)
    if not t:
        return jsonify({'error': 'Transaction not found', 'erro': 'Transação não encontrada'}), 404
        
    if t.status not in [TransactionStatus.PAID.value, 'Paid', 'Pago']:
        return jsonify({'error': 'Transaction is not paid', 'erro': 'Esta transação não está com status pago'}), 400
        
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    forma_anterior = t.forma_pagamento or 'N/A'
    data_anterior = t.data_pagamento.strftime('%d/%m/%Y %H:%M') if t.data_pagamento else 'N/A'
    
    # Revert to PENDING
    t.status = TransactionStatus.PENDING.value
    t.data_pagamento = None
    t.forma_pagamento = None
    t.registrado_por_nome = None
    db.session.commit()
    
    registrar_log(
        'PAYMENT_CANCELLED', 
        'Transaction', 
        t.id, 
        f"PAGAMENTO CANCELADO: Pagamento #{t.id} de £{float(t.valor):.2f} ({t.tipo}) foi revertido para PENDENTE por {operador_atual} no Contrato #{t.id_contrato} (Pagamento anterior via {forma_anterior} em {data_anterior})"
    )
    
    return jsonify({
        'message': 'Payment cancelled and reverted to Pending successfully', 
        'mensagem': 'Pagamento cancelado e revertido para Pendente com sucesso',
        'status': t.status
    }), 200

def obter_descricao_recibo(t, contrato=None):
    if not t:
        return ""
    tipo = str(t.tipo or '').strip()
    tipo_lower = tipo.lower()
    
    if tipo_lower in ['sale_full', 'venda_vista']:
        return "Vehicle Sale - Full Payment"
    elif tipo_lower in ['sale_deposit', 'venda_entrada']:
        return "Vehicle Sale - Down Payment (Deposit)"
    elif tipo_lower in ['sale_installment', 'venda_parcela']:
        if t.id_contrato:
            try:
                parcelas = FinancialTransaction.query.filter(
                    FinancialTransaction.id_contrato == t.id_contrato,
                    FinancialTransaction.tipo.in_([TransactionType.SALE_INSTALLMENT.value, 'Sale_Installment', 'Venda_Parcela'])
                ).order_by(FinancialTransaction.data_vencimento.asc(), FinancialTransaction.id.asc()).all()
                total = len(parcelas)
                for idx, p in enumerate(parcelas, 1):
                    if p.id == t.id:
                        return f"Vehicle Sale - Instalment {idx} of {total}"
            except Exception:
                pass
        return "Vehicle Sale - Instalment Payment"
    elif tipo_lower in ['rent', 'aluguel']:
        return "Vehicle Rental Payment"
    elif tipo_lower in ['deposit', 'deposito']:
        return "Rental Security Deposit (Refundable)"
    elif tipo_lower in ['deposit_refund', 'devolucao_deposito']:
        return "Security Deposit Refund"
    elif tipo_lower in ['fine', 'multa']:
        return "Traffic / Penalty Charge Notice (PCN)"
    elif tipo_lower in ['damage', 'dano']:
        return "Vehicle Damage Repair Charge"
    elif tipo_lower in ['other', 'outro']:
        return "Additional Charge"
    
    return tipo.replace('_', ' ').title()

def obter_descricao_recibo_simples(tipo):
    tipo_lower = (tipo or '').strip().lower()
    if tipo_lower in ['sale_full', 'venda_vista']:
        return "Vehicle Sale - Full Payment"
    elif tipo_lower in ['sale_deposit', 'venda_entrada']:
        return "Vehicle Sale - Down Payment (Deposit)"
    elif tipo_lower in ['sale_installment', 'venda_parcela']:
        return "Vehicle Sale - Instalment Payment"
    elif tipo_lower in ['rent', 'aluguel']:
        return "Vehicle Rental Payment"
    elif tipo_lower in ['deposit', 'deposito']:
        return "Rental Security Deposit (Refundable)"
    elif tipo_lower in ['deposit_refund', 'devolucao_deposito']:
        return "Security Deposit Refund"
    elif tipo_lower in ['fine', 'multa']:
        return "Traffic / Penalty Charge Notice (PCN)"
    elif tipo_lower in ['damage', 'dano']:
        return "Vehicle Damage Repair Charge"
    elif tipo_lower in ['other', 'outro']:
        return "Additional Charge"
    return (tipo or '').replace('_', ' ').title()

@app.route('/recibo/<int:id>')
@alugueis_required
def pagina_recibo(id):
    t = db.session.get(FinancialTransaction, id)
    if not t:
        return render_template('404.html'), 404
    contrato = db.session.get(Contract, t.id_contrato) if t.id_contrato else None
    cliente = db.session.get(Client, contrato.id_cliente) if (contrato and contrato.id_cliente) else None
    descricao = obter_descricao_recibo(t, contrato)
    return render_template('recibo.html', transacao=t, contrato=contrato, cliente=cliente, descricao=descricao)

@app.route('/api/financeiro/<int:id>', methods=['DELETE'])
@alugueis_required
def excluir_transacao(id):
    t = db.session.get(FinancialTransaction, id)
    if not t:
        return jsonify({'error': 'Transaction not found', 'erro': 'Transação não encontrada'}), 404
        
    if t.status in [TransactionStatus.PAID.value, 'Paid', 'Pago']:
        return jsonify({'error': 'Cannot delete an already paid transaction', 'erro': 'Não é possível excluir uma transação já paga'}), 400
        
    db.session.delete(t)
    db.session.commit()
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('TRANSACTION_DELETE', 'Transaction', id, f"Transação #{id} excluída por {operador_atual}")
    return jsonify({'message': 'Transaction deleted successfully', 'mensagem': 'Transação excluída com sucesso'}), 200

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    resp_data = {}

    # Dados do módulo de aluguéis: SOMENTE para quem possui permissão de aluguéis
    pode_alugueis = current_user.is_authenticated and current_user.pode_alugueis()

    if pode_alugueis:
        total_motos = Motorcycle.query.count()
        motos_disponiveis = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.AVAILABLE.value, 'Available', 'Disponível'])).count()
        motos_alugadas = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.RENTED.value, 'Rented', 'Alugada'])).count()
        motos_manutencao = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.MAINTENANCE.value, 'Maintenance', 'Manutenção', 'Manutencao'])).count()
        
        # Detalhes das motos em manutenção (otimizado com batch query de contratos)
        motos_manutencao_lista = []
        manutencao_objs = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.MAINTENANCE.value, 'Maintenance', 'Manutenção', 'Manutencao'])).all()
        if manutencao_objs:
            placas_manut = [m.placa for m in manutencao_objs]
            latest_contracts = db.session.query(Contract).options(joinedload(Contract.cliente)).filter(Contract.placa.in_(placas_manut)).order_by(Contract.id.desc()).all()
            last_c_by_plate = {}
            for c in latest_contracts:
                if c.placa not in last_c_by_plate:
                    last_c_by_plate[c.placa] = c
            for m in manutencao_objs:
                last_c = last_c_by_plate.get(m.placa)
                cliente_nome = last_c.cliente.nome if last_c and last_c.cliente else None
                contrato_id = last_c.id if last_c else None
                motos_manutencao_lista.append({
                    'placa': m.placa,
                    'modelo': m.modelo,
                    'cor': m.cor or 'N/A',
                    'status': m.status,
                    'contrato_id': contrato_id,
                    'cliente_nome': cliente_nome
                })
            
        # Performance: Single query for active contracts with eager-loaded clients (reused in askMID compliance)
        contratos_ativos_objs = db.session.query(Contract).options(
            joinedload(Contract.cliente)
        ).filter(Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo'])).all()
        contratos_ativos = len(contratos_ativos_objs)
        receita_semanal = sum(float(c.valor_aluguel_semanal) for c in contratos_ativos_objs)
        
        total_clientes = Client.query.count()
        
        # Performance: Direct SQL sum for pending revenue
        receita_pendente = float(db.session.query(
            db.func.coalesce(db.func.sum(FinancialTransaction.valor), 0.0)
        ).filter(
            FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
            FinancialTransaction.tipo.in_([TransactionType.RENT.value, TransactionType.FINE.value, 'Rent', 'Fine', 'Aluguel', 'Multa'])
        ).scalar() or 0.0)
        
        # Performance: Direct SQL sum and count for overdue charges using London Time
        agora = get_london_now().replace(tzinfo=None)
        vencidas_q = db.session.query(
            db.func.coalesce(db.func.sum(FinancialTransaction.valor), 0.0),
            db.func.count(FinancialTransaction.id)
        ).filter(
            FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
            FinancialTransaction.data_vencimento < agora
        ).first()
        receita_vencida = float(vencidas_q[0]) if vencidas_q else 0.0
        total_vencidos = int(vencidas_q[1]) if vencidas_q else 0
        
        # Performance: Pre-fetch transactions to prevent N+1 queries during deposit accounting
        contratos_quarentena = db.session.query(Contract).options(joinedload(Contract.transacoes)).filter(
            Contract.status.in_([ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito'])
        ).all()
        quarentenas_count = len(contratos_quarentena)
        quarentenas_valor = 0.0
        for cq in contratos_quarentena:
            dep_pago = 0.0
            deducoes = 0.0
            for t in cq.transacoes:
                if t.status in [TransactionStatus.PAID.value, 'Paid', 'Pago']:
                    if t.tipo in [TransactionType.DEPOSIT.value, 'Deposit', 'Deposito', 'Depósito']:
                        dep_pago += float(t.valor)
                    elif t.forma_pagamento and 'deposit' in t.forma_pagamento.lower():
                        deducoes += float(t.valor)
            quarentenas_valor += max(0.0, dep_pago - deducoes)
                    
        # Últimas vistorias (eager-loaded)
        recent_inspections = []
        inspecoes = db.session.query(Inspection).options(
            joinedload(Inspection.contrato).joinedload(Contract.cliente)
        ).order_by(Inspection.id.desc()).limit(5).all()
        for i in inspecoes:
            placa = i.contrato.placa if i.contrato else '-'
            cliente = i.contrato.cliente.nome if i.contrato and i.contrato.cliente else '-'
            foto_count = len([f for f in (i.url_fotos or '').split(',') if f.strip()])
            recent_inspections.append({
                'id': i.id,
                'contrato_id': i.id_contrato,
                'placa': placa,
                'cliente': cliente,
                'tipo': i.tipo,
                'data': i.data.strftime('%d/%m/%Y %H:%M') if i.data else '-',
                'foto_count': foto_count,
                'observacoes': i.observacoes or ''
            })
            
        # Últimos contratos (eager-loaded)
        recent_contracts = []
        contratos = db.session.query(Contract).options(
            joinedload(Contract.cliente)
        ).order_by(Contract.id.desc()).limit(4).all()
        for c in contratos:
            recent_contracts.append({
                'id': c.id,
                'cliente': c.cliente.nome if c.cliente else 'N/A',
                'placa': c.placa,
                'status': c.status,
                'valor_semanal': float(c.valor_aluguel_semanal),
                'data_retirada': c.data_retirada.strftime('%d/%m/%Y') if c.data_retirada else '-'
            })
        
        # Alertas de Compliance de Frota: Road Tax e MOT (vencidos ou a vencer em até 30 dias - query colunas necessárias)
        hoje_date = get_london_date()
        todas_motos = db.session.query(
            Motorcycle.placa,
            Motorcycle.vencimento_tax,
            Motorcycle.vencimento_mot
        ).all()
        tax_mot_warnings = 0
        tax_warnings = 0
        mot_warnings = 0
        tax_mot_expired = 0
        tax_mot_expiring_soon = 0
        
        for m in todas_motos:
            has_tax_w = False
            has_mot_w = False
            is_m_expired = False
            
            if m.vencimento_tax:
                diff_t = (m.vencimento_tax - hoje_date).days
                if diff_t < 0:
                    has_tax_w = True
                    is_m_expired = True
                elif diff_t <= 30:
                    has_tax_w = True
                    
            if m.vencimento_mot:
                diff_m = (m.vencimento_mot - hoje_date).days
                if diff_m < 0:
                    has_mot_w = True
                    is_m_expired = True
                elif diff_m <= 30:
                    has_mot_w = True
                    
            if has_tax_w:
                tax_warnings += 1
            if has_mot_w:
                mot_warnings += 1
            if has_tax_w or has_mot_w:
                tax_mot_warnings += 1
                if is_m_expired:
                    tax_mot_expired += 1
                else:
                    tax_mot_expiring_soon += 1
                    
        # Compliance: Checagem Quinzenal de Seguro no askMID (reaproveita contratos_ativos_objs carregados acima)
        seguros_pendentes_count = 0
        seguros_cancelados_count = 0
        contratos_seguro_alerta = []
        
        for ca in contratos_ativos_objs:
            # Não monitorar seguro quinzenal para motos vendidas (Sale_Full / Sale_Installment)
            tipo_ca = getattr(ca, 'tipo_contrato', 'Rent') or 'Rent'
            if tipo_ca in [ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value, 'Sale_Full', 'Sale_Installment']:
                continue
                
            u_check = ca.data_ultima_checagem_seguro or (ca.data_retirada.date() if ca.data_retirada else hoje_date)
            dias_check = (hoje_date - u_check).days
            cli_nome = ca.cliente.nome if ca.cliente else f"Client #{ca.id_cliente}"
            
            if ca.status_seguro == 'Cancelled':
                seguros_cancelados_count += 1
                contratos_seguro_alerta.append({
                    'id': ca.id,
                    'placa': ca.placa,
                    'cliente': cli_nome,
                    'dias': dias_check,
                    'status_seguro': 'Cancelled',
                    'mensagem': f"ALARM: Vehicle {ca.placa} insurance was flagged CANCELLED/INVALID on askMID!"
                })
            elif dias_check >= 15:
                seguros_pendentes_count += 1
                contratos_seguro_alerta.append({
                    'id': ca.id,
                    'placa': ca.placa,
                    'cliente': cli_nome,
                    'dias': dias_check,
                    'status_seguro': 'Check_Due',
                    'mensagem': f"Contract #{ca.id} ({ca.placa} - {cli_nome}) due for 15-day askMID insurance check (last checked {dias_check} days ago)."
                })
        
        resp_data.update({
            'total_motos': total_motos,
            'motos_disponiveis': motos_disponiveis,
            'motos_alugadas': motos_alugadas,
            'motos_manutencao': motos_manutencao,
            'motos_manutencao_lista': motos_manutencao_lista,
            'tax_mot_warnings': tax_mot_warnings,
            'tax_mot_expired': tax_mot_expired,
            'tax_mot_expiring_soon': tax_mot_expiring_soon,
            'tax_warnings': tax_warnings,
            'mot_warnings': mot_warnings,
            'seguros_pendentes_count': seguros_pendentes_count,
            'seguros_cancelados_count': seguros_cancelados_count,
            'contratos_seguro_alerta': contratos_seguro_alerta,
            'contratos_ativos': contratos_ativos,
            'total_clientes': total_clientes,
            'receita_pendente': receita_pendente,
            'receita_semanal': receita_semanal,
            'receita_vencida': receita_vencida,
            'total_vencidos': total_vencidos,
            'quarentenas_count': quarentenas_count,
            'quarentenas_valor': quarentenas_valor,
            'recent_inspections': recent_inspections,
            'recent_contracts': recent_contracts
        })

    # Cautela e Isolamento Total: Alertas de Claims somente para quem tem permissão
    if current_user.is_authenticated and current_user.pode_claims():
        hoje_claim = get_london_date()
        todos_claims = Claim.query.filter(Claim.status == 'Em Aberto').all()
        ind_vencidas = 0
        stor_28d = 0
        inv_vencidos = 0
        inv_pendentes_envio = 0

        for cl in todos_claims:
            if cl.prazo_indicacao and cl.status_indicacao != 'Pago' and cl.prazo_indicacao < hoje_claim:
                ind_vencidas += 1
            if cl.prazo_liberacao_storage and cl.status_storage == 'No Pátio':
                diff_d = (cl.prazo_liberacao_storage - hoje_claim).days
                if diff_d <= 7: # Vence em 7 dias ou já venceu os 28 dias
                    stor_28d += 1
            if cl.status_storage == 'Liberado' and not cl.data_envio_invoice:
                inv_pendentes_envio += 1
            if cl.prazo_pagamento_invoice and cl.status_pagamento_storage != 'Pago' and cl.prazo_pagamento_invoice < hoje_claim:
                inv_vencidos += 1

        resp_data['claims_alerts'] = {
            'indicacoes_vencidas': ind_vencidas,
            'storage_28d_vencendo': stor_28d,
            'invoices_vencidos': inv_vencidos,
            'invoices_pendentes_envio': inv_pendentes_envio,
            'total_alertas': ind_vencidas + stor_28d + inv_vencidos + inv_pendentes_envio
        }

    return jsonify(resp_data)

@app.route('/api/alertas', methods=['GET'])
@alugueis_required
def listar_alertas():
    alertas = []
    hoje = get_local_now()
    
    # 1. Deposit hold alerts (14 or 15+ days)
    contratos_quarentena = Contract.query.filter(Contract.status.in_([ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito'])).all()
    for c in contratos_quarentena:
        if c.data_devolucao:
            dias_passados = (hoje - c.data_devolucao).days
            if dias_passados >= 14:
                cliente = db.session.get(Client, c.id_cliente)
                nome = cliente.nome if cliente else f"ID {c.id_cliente}"
                alertas.append({
                    'tipo': 'deposit_hold_due',
                    'contrato_id': c.id,
                    'cliente_nome': nome,
                    'dias': dias_passados,
                    'mensagem': f"Contract #{c.id} ({nome}) has been on deposit hold for {dias_passados} days. Deposit return due today or tomorrow!"
                })
                
    return jsonify(alertas)

@app.route('/api/contratos/<int:id>/finalizar-quarentena', methods=['POST'])
@alugueis_required
def finalizar_quarentena(id):
    contrato = db.session.get(Contract, id)
    if not contrato or contrato.status not in [ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito']:
        return jsonify({'error': 'Contract not found or not in deposit hold', 'erro': 'Contrato não encontrado ou não está em quarentena'}), 404
        
    url_comprovante = None
    if 'comprovante' in request.files:
        f = request.files['comprovante']
        if f.filename:
            if not is_allowed_file(f.filename):
                return jsonify({'error': 'Invalid file format. Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': 'Formato de arquivo inválido.'}), 400
            nome_arq = werkzeug.utils.secure_filename(f"{int(get_local_now().timestamp())}_{f.filename}")
            nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
            url_comprovante = f"/static/uploads/{nome_salvo}"
            
    contrato.url_comprovante_deposito = url_comprovante
    contrato.status = ContractStatus.COMPLETED.value
    db.session.commit()
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('QUARANTINE_END', 'Contract', contrato.id, f"Quarentena do contrato #{contrato.id} finalizada por {operador_atual}.")
    return jsonify({'message': 'Deposit hold finalized successfully', 'mensagem': 'Quarentena finalizada com sucesso'})

@app.route('/api/relatorios/resumo', methods=['GET'])
@alugueis_required
def get_relatorios_resumo():
    transacoes = FinancialTransaction.query.all()
    faturamento = {'Paid': 0, 'Pending': 0, 'Pago': 0, 'Pendente': 0}
    for t in transacoes:
        if t.tipo in [TransactionType.RENT.value, TransactionType.FINE.value, 'Rent', 'Fine', 'Aluguel', 'Multa']:
            if t.status in [TransactionStatus.PAID.value, 'Paid', 'Pago']:
                faturamento['Paid'] += float(t.valor)
                faturamento['Pago'] += float(t.valor)
            elif t.status in [TransactionStatus.PENDING.value, 'Pending', 'Pendente']:
                faturamento['Pending'] += float(t.valor)
                faturamento['Pendente'] += float(t.valor)
                
    motos = Motorcycle.query.all()
    frota = {'Available': 0, 'Rented': 0, 'Maintenance': 0, 'Disponível': 0, 'Alugada': 0, 'Manutenção': 0}
    for m in motos:
        st = m.status
        if st in ['Available', 'Disponível']:
            frota['Available'] += 1
            frota['Disponível'] += 1
        elif st in ['Rented', 'Alugada']:
            frota['Rented'] += 1
            frota['Alugada'] += 1
        elif st in ['Maintenance', 'Manutenção', 'Manutencao']:
            frota['Maintenance'] += 1
            frota['Manutenção'] += 1
            
    return jsonify({
        'faturamento': faturamento,
        'frota': frota
    })

# --- BUSINESS LOGIC (Background Jobs & Schedulers) ---

def _gerar_cobrancas_semanais_logic():
    # London / UK timezone
    tz = pytz.timezone('Europe/London')
    hoje = datetime.now(tz)
    dia_semana_atual = hoje.weekday() # 0 = Monday, 6 = Sunday
    
    hoje_utc = get_local_now()
    
    contratos_ativos = Contract.query.filter(
        Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']),
        Contract.dia_pagamento_semanal == dia_semana_atual,
        db.or_(Contract.tipo_contrato == ContractType.RENT.value, Contract.tipo_contrato == None, Contract.tipo_contrato == 'Rent')
    ).all()
    
    transacoes_geradas = 0
    proximo_vencimento = hoje_utc + timedelta(days=7)
    inicio_dia_prox = proximo_vencimento.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_dia_prox = inicio_dia_prox + timedelta(days=1)
    
    for contrato in contratos_ativos:
        cobranca_existente = FinancialTransaction.query.filter(
            FinancialTransaction.id_contrato == contrato.id,
            FinancialTransaction.tipo.in_([TransactionType.RENT.value, 'Rent', 'Aluguel']),
            FinancialTransaction.data_vencimento >= inicio_dia_prox,
            FinancialTransaction.data_vencimento < fim_dia_prox
        ).first()
        
        if not cobranca_existente:
            nova_cobranca = FinancialTransaction(
                id_contrato=contrato.id,
                tipo=TransactionType.RENT.value,
                data_vencimento=proximo_vencimento,
                valor=contrato.valor_aluguel_semanal,
                status=TransactionStatus.PENDING.value
            )
            db.session.add(nova_cobranca)
            transacoes_geradas += 1
            
    if transacoes_geradas > 0:
        db.session.commit()
        
    return transacoes_geradas

def check_cron_auth():
    """Verifica se a chamada ao cron veio com token secreto ou de um administrador autenticado."""
    secret_key = os.environ.get('CRON_SECRET_KEY', 'ffmotors-internal-cron-key-2026')
    header_key = request.headers.get('X-Cron-Key') or request.args.get('cron_key')
    if header_key and hmac.compare_digest(str(header_key), str(secret_key)):
        return True
    if current_user.is_authenticated and current_user.pode_admin():
        return True
    return False

@app.route('/api/jobs/gerar-cobrancas-semanais', methods=['POST'])
def gerar_cobrancas_semanais():
    if not check_cron_auth():
        return jsonify({'error': 'Unauthorized', 'message': 'Chave de cron ou privilégio administrativo requerido.'}), 403
    transacoes = _gerar_cobrancas_semanais_logic()
    registrar_log('JOB_WEEKLY_RENT', 'System', None, f"Job de cobranças semanais executado. {len(transacoes)} novas cobranças geradas.")
    return jsonify({
        "message": "Weekly rent charges processed successfully",
        "charges_generated": transacoes,
        "transacoes_geradas": transacoes
    }), 200

def _processar_quarentenas_logic():
    """
    Checks contracts in deposit hold that have exceeded 15 days
    and calculates refundable deposit balance.
    """
    hoje = get_local_now()
    limite_quarentena = hoje - timedelta(days=15)
    
    contratos_quarentena = Contract.query.filter(
        Contract.status.in_([ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito']),
        Contract.data_devolucao <= limite_quarentena
    ).all()
    
    processados = 0
    
    for contrato in contratos_quarentena:
        transacoes = FinancialTransaction.query.filter_by(id_contrato=contrato.id).all()
        
        deposito = 0.0
        deducoes_pagas = 0.0
        multas_e_danos_pendentes = 0.0
        
        for t in transacoes:
            if t.status in [TransactionStatus.PAID.value, 'Paid', 'Pago']:
                if t.tipo in [TransactionType.DEPOSIT.value, 'Deposit', 'Deposito', 'Depósito']:
                    deposito += float(t.valor)
                elif t.forma_pagamento and 'deposit' in t.forma_pagamento.lower():
                    deducoes_pagas += float(t.valor)
            elif t.tipo in [TransactionType.FINE.value, TransactionType.DAMAGE.value, 'Fine', 'Damage', 'Multa', 'Dano'] and t.status in [TransactionStatus.PENDING.value, 'Pending', 'Pendente']:
                multas_e_danos_pendentes += float(t.valor)
        
        contrato.status = ContractStatus.COMPLETED.value
        
        moto = db.session.get(Motorcycle, contrato.placa) if contrato.placa else None
        if moto and moto.status in [MotoStatus.RENTED.value, 'Rented', 'Alugada']:
            moto.status = MotoStatus.AVAILABLE.value
            
        processados += 1
        
    if processados > 0:
        db.session.commit()
        
    return processados

@app.route('/api/jobs/processar-quarentenas', methods=['POST'])
def processar_quarentenas():
    if not check_cron_auth():
        return jsonify({'error': 'Unauthorized', 'message': 'Chave de cron ou privilégio administrativo requerido.'}), 403
    processados = _processar_quarentenas_logic()
    registrar_log('JOB_QUARANTINE', 'System', None, f"Job de quarentena executado. {len(processados)} contratos finalizados automaticamente.")
    return jsonify({
        "message": "Deposit holds processed successfully",
        "contracts_completed": processados,
        "contratos_finalizados": processados
    }), 200

def run_daily_jobs():
    with app.app_context():
        london_date_str = get_london_date().strftime('%Y-%m-%d')
        job_name = "daily_rent_and_deposit_jobs"
        
        # Concurrency safety across multi-worker deployments (e.g. Gunicorn):
        # Prevent multiple workers from executing the 1am job twice on the same day
        try:
            lock = JobExecutionLock.query.filter_by(job_name=job_name).first()
            if lock and lock.last_run_date == london_date_str:
                print(f"[Cron Lock] Daily jobs '{job_name}' already completed for date {london_date_str} by {lock.executed_by}. Skipping duplicate execution.")
                return

            worker_id = f"worker-pid-{os.getpid()}"
            if not lock:
                lock = JobExecutionLock(
                    job_name=job_name,
                    last_run_date=london_date_str,
                    last_run_at=get_local_now(),
                    executed_by=worker_id
                )
                db.session.add(lock)
            else:
                lock.last_run_date = london_date_str
                lock.last_run_at = get_local_now()
                lock.executed_by = worker_id
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[Cron Lock] Worker lock acquired by another process or error for {london_date_str}: {e}")
            return

        print(f"[Cron] Starting daily background jobs for {london_date_str} (Europe/London 01:00 AM)...")
        t_cobrancas = _gerar_cobrancas_semanais_logic()
        t_quarentenas = _processar_quarentenas_logic()
        print(f"[Cron] Finished. {t_cobrancas} rent charges generated, {t_quarentenas} deposit holds processed.")

if __name__ == '__main__':
    uploads_dir = os.path.join(basedir, 'static', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Start APScheduler with Europe/London timezone at 01:00 AM (guarded for Flask reloader)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/London'))
        scheduler.add_job(func=run_daily_jobs, trigger="cron", hour=1, minute=0)
        scheduler.start()
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() in ('true', '1')
    app.run(debug=debug_mode, host='0.0.0.0', use_reloader=debug_mode)
