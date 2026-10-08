import os
import re
import json
import secrets
import hmac
import time
import threading
from collections import defaultdict
from datetime import datetime, timedelta, date
from functools import wraps
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, jsonify, send_file, redirect, url_for, 
    send_from_directory, flash, session, Response
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from database import (
    db, init_db, Contract, ContractType, FinancialTransaction, TransactionType, 
    TransactionStatus, ContractStatus, MotoStatus, Motorcycle, Client, Inspection, InspectionType,
    User, AuditLog, JobExecutionLock, Claim, ContractAttachment, delete_file_if_exists,
    MotorcycleV5C, MotorcycleTracker
)
from sqlalchemy.orm import joinedload, contains_eager, selectinload
import werkzeug.utils
from apscheduler.schedulers.background import BackgroundScheduler
import pytz
import markupsafe

load_dotenv()

app = Flask(__name__)

# Configuração de ProxyFix: interpreta corretamente o IP real e HTTPS atrás do Nginx (Rate Limiting e Logs)
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Configuração de SECRET_KEY com fallback defensivo para desenvolvimento
secret_key_env = os.environ.get('SECRET_KEY')
if not secret_key_env:
    if os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError("FATAL: Variável de ambiente SECRET_KEY é obrigatória em ambiente de produção!")
    secret_key_env = 'ffmotors-birmingham-uk-secret-key-2026-production'
app.config['SECRET_KEY'] = secret_key_env

# Limite máximo de tamanho de upload no Flask (padrão: 32MB) para prevenir ataques de DoS por esgotamento de recursos
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 32 * 1024 * 1024))

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

def is_transaction_overdue(tx, hoje_date=None):
    """Safely checks if a financial transaction is overdue, regardless of naive/aware datetime."""
    if not tx or not tx.data_vencimento:
        return False
    if hoje_date is None:
        hoje_date = get_london_date()
    venc = tx.data_vencimento
    if isinstance(venc, datetime):
        if venc.tzinfo is not None:
            venc_date = venc.astimezone(LONDON_TZ).date()
        else:
            venc_date = venc.date()
    elif isinstance(venc, date):
        venc_date = venc
    else:
        return False
    return venc_date < hoje_date

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
if os.environ.get('SESSION_COOKIE_SECURE', '').lower() in ('true', '1') or (
    os.environ.get('FLASK_ENV') == 'production' and os.environ.get('SESSION_COOKIE_SECURE', '').lower() not in ('false', '0')
):
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
    target = request.full_path.rstrip('?') if request.query_string else request.path
    return redirect(url_for('login', next=target))

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
            target = request.full_path.rstrip('?') if request.query_string else request.path
            return redirect(url_for('login', next=target))
        if not current_user.pode_claims():
            if request.path.startswith('/api/'):
                return jsonify({"error": "Forbidden", "message": "Acesso restrito ao módulo de claims & storage"}), 403
            flash('Você não tem permissão para acessar o módulo de Claims & Storage.', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def financeiro_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/api/'):
                return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401
            target = request.full_path.rstrip('?') if request.query_string else request.path
            return redirect(url_for('login', next=target))
        if not current_user.pode_financeiro():
            if request.path.startswith('/api/'):
                return jsonify({"error": "Forbidden", "message": "Acesso restrito ao módulo financeiro"}), 403
            flash('Você não tem permissão para acessar o módulo financeiro.', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def registrar_log(acao, entidade, entidade_id, descricao):
    """
    Registra um evento na trilha de auditoria interna.
    Identifica automaticamente o usuário logado e o IP da requisição.
    """
    try:
        user_id = current_user.id if getattr(current_user, 'is_authenticated', False) else None
        user_nome = current_user.nome if getattr(current_user, 'is_authenticated', False) else "System"
        ip = None
        if request:
            forwarded = request.headers.get('X-Forwarded-For')
            if forwarded:
                ip = forwarded.split(',')[0].strip()
            else:
                ip = request.remote_addr
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
def check_cron_auth():
    """Verifica se a chamada ao cron veio com token secreto, de um administrador autenticado ou de chamada local."""
    secret_key = os.environ.get('CRON_SECRET_KEY', 'ffmotors-internal-cron-key-2026')
    header_key = request.headers.get('X-Cron-Key') or request.args.get('cron_key')
    if header_key and hmac.compare_digest(str(header_key), str(secret_key)):
        return True
    if current_user.is_authenticated and current_user.pode_admin():
        return True
    # Chamadas internas originadas estritamente do próprio servidor (localhost / 127.0.0.1)
    remote_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '')
    if remote_ip in ('127.0.0.1', '::1', 'localhost') and request.host.startswith(('127.0.0.1', 'localhost')):
        return True
    return False

def is_safe_redirect_url(target):
    """Garante que a URL de redirecionamento pertença à mesma aplicação e previne Open Redirect."""
    if not target or not isinstance(target, str):
        return False
    # Bloquear protocol-relative URLs (//malicious.com) e backslashes (/\malicious.com)
    if target.startswith('//') or target.startswith('/\\') or target.startswith('\\'):
        return False
    if target.startswith('/') and not target.startswith('//'):
        from urllib.parse import urlparse
        parsed = urlparse(target)
        return parsed.netloc == '' and parsed.scheme == ''
    return False

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
            
        # Isenção de CSRF restrita exclusivamente às rotas dedicadas de cron/jobs
        # (estas rotas validam sua autenticação via check_cron_auth() com chave de cron)
        if request.path.startswith('/api/jobs/') or request.path.startswith('/api/admin/limpar-cobrancas-duplicadas'):
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
        
    # Rotas de automação e cron que validam sua própria autenticação via check_cron_auth()
    if request.path.startswith('/api/jobs/') or request.path.startswith('/api/admin/limpar-cobrancas-duplicadas'):
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
            target = request.full_path.rstrip('?') if request.query_string else request.path
            return redirect(url_for('login', next=target))

        # Atualiza o timestamp da última atividade do usuário
        session['last_activity'] = now
        return

    if not current_user.is_authenticated:
        if request.path.startswith('/api/'):
            return jsonify({"error": "Unauthorized", "message": "Authentication required"}), 401
        target = request.full_path.rstrip('?') if request.query_string else request.path
        return redirect(url_for('login', next=target))

@app.route('/login', methods=['GET', 'POST'])
def login():
    next_page = (request.args.get('next') or request.form.get('next') or '').strip() or None

    if current_user.is_authenticated:
        if next_page and is_safe_redirect_url(next_page) and not next_page.startswith('/login') and not next_page.startswith('/logout'):
            return redirect(next_page)
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        client_ip = request.remote_addr or 'unknown'
        if is_ip_rate_limited(client_ip):
            flash('Too many failed login attempts (maximum 10). For security, please wait 15 minutes before trying again.', 'danger')
            return render_template('login.html', email=request.form.get('email', ''), next_url=next_page), 429

        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.ativo:
                flash('Esta conta de acesso está inativa. Contate o administrador.', 'danger')
                return render_template('login.html', email=email, next_url=next_page)
                
            clear_failed_logins(client_ip)
            session.permanent = True
            login_user(user, remember=remember)
            registrar_log('LOGIN_SUCCESS', 'User', user.id, f"Usuário {user.nome} fez login no sistema.")
            session['last_activity'] = time.time()
            if not next_page or not is_safe_redirect_url(next_page) or next_page.startswith('/login') or next_page.startswith('/logout'):
                next_page = url_for('index')
            return redirect(next_page)
        else:
            record_failed_login(client_ip)
            registrar_log('LOGIN_FAILED', 'User', None, f"Tentativa de login falha para o email: {email} (IP: {client_ip})")
            flash('Credenciais inválidas. Verifique seu e-mail e senha.', 'danger')
            return render_template('login.html', email=email, next_url=next_page)
            
    return render_template('login.html', next_url=next_page)

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
@login_required
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
    response.headers['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
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
        response.headers['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
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
    import traceback
    traceback.print_exc()
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({'error': 'Internal Server Error', 'message': 'An unexpected server error occurred'}), 500
    return render_template('500.html'), 500

@app.errorhandler(413)
def handle_large_file(e):
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({'error': 'Payload Too Large', 'message': 'O arquivo enviado excede o limite máximo permitido de 32MB.'}), 413
    flash('Arquivo muito grande. O limite máximo permitido para envio é 32MB.', 'danger')
    return redirect(request.referrer or url_for('index')), 413

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
            admin = User.query.filter(User.email.ilike("tmuniz570@gmail.com")).first()
            if not admin:
                default_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'Admin123!')
                admin = User(
                    nome="Thiago Brandão",
                    email="tmuniz570@gmail.com",
                    role="admin",
                    is_admin=True,
                    perm_alugueis=True,
                    perm_claims=True,
                    perm_financeiro=True,
                    ativo=True
                )
                admin.set_password(default_password)
                db.session.add(admin)
                db.session.commit()
                print("[Auth] Master Admin 'Thiago Brandão' (tmuniz570@gmail.com) criado com sucesso.")
            else:
                if not admin.is_admin or not admin.ativo or not admin.perm_alugueis or not admin.perm_claims or not getattr(admin, 'perm_financeiro', True) or admin.role != 'admin':
                    admin.is_admin = True
                    admin.role = 'admin'
                    admin.ativo = True
                    admin.perm_alugueis = True
                    admin.perm_claims = True
                    admin.perm_financeiro = True
                    db.session.commit()
                    print("[Auth] Master Admin 'Thiago Brandão' (tmuniz570@gmail.com) privilégios reafirmados.")
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
@financeiro_required
def pagina_financeiro():
    return render_template('financeiro.html')

@app.route('/vistorias')
@alugueis_required
def pagina_vistorias_lista():
    return render_template('vistorias_lista.html')

@app.route('/relatorios')
@financeiro_required
def pagina_relatorios():
    return redirect('/financeiro')

@app.route('/relatorios/vencidos')
@alugueis_required
def relatorio_vencidos():
    agora_london = get_london_now()
    inicio_hoje = agora_london.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    transacoes = FinancialTransaction.query.options(
        db.joinedload(FinancialTransaction.contrato).joinedload(Contract.cliente)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pendente']),
        FinancialTransaction.data_vencimento < inicio_hoje
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

@app.route('/motos/relatorio-pdf')
@alugueis_required
def relatorio_fleet_pdf():
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', '', type=str).strip()
    v5c_filter = request.args.get('v5c', '', type=str).strip().lower()

    query = Motorcycle.query.options(
        selectinload(Motorcycle.v5c_arquivos),
        selectinload(Motorcycle.trackers),
        selectinload(Motorcycle.contratos).selectinload(Contract.cliente)
    )

    hoje_date = datetime.now(pytz.timezone('Europe/London')).date()

    filter_desc = "All Fleet"
    if status_filter:
        sf_lower = status_filter.lower()
        if sf_lower in ['operational', 'in_operation', 'operacao', 'ativa', 'ativas', 'active']:
            query = query.filter(
                ~Motorcycle.status.in_([MotoStatus.POUND.value, 'Pound']),
                db.or_(
                    ~Motorcycle.status.in_([MotoStatus.SOLD.value, 'Sold', 'Vendida']),
                    Motorcycle.contratos.any(Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']))
                )
            )
            filter_desc = "Active Fleet (In Operation)"
        elif sf_lower == 'sorn':
            query = query.filter(Motorcycle.tax_sorn == True)
            filter_desc = "SORN (Statutory Off Road Notification)"
        elif sf_lower in ['missing_v5c', 'no_v5c', 'sem_v5c']:
            query = query.filter(~Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'v5c'))
            filter_desc = "Missing V5C Logbook"
        elif sf_lower in ['awaiting_v5c', 'slip_on_file', 'com_slip']:
            query = query.filter(
                Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'transfer_proof'),
                ~Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'v5c')
            )
            filter_desc = "Awaiting V5C (Slip on File)"
        elif sf_lower in ['no_v5c_no_slip', 'sem_nada']:
            query = query.filter(~Motorcycle.v5c_arquivos.any())
            filter_desc = "No V5C & No Transfer Slip"
        elif sf_lower in ['warnings', 'tax_mot_warnings', 'alert', 'alerts']:
            trinta_dias = hoje_date + timedelta(days=30)
            query = query.filter(
                ~Motorcycle.status.in_([MotoStatus.POUND.value, 'Pound']),
                db.or_(
                    db.and_(
                        db.or_(
                            ~Motorcycle.status.in_([MotoStatus.SOLD.value, 'Sold', 'Vendida']),
                            Motorcycle.contratos.any(Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']))
                        ),
                        Motorcycle.tax_sorn == False,
                        Motorcycle.vencimento_tax <= trinta_dias
                    ),
                    Motorcycle.vencimento_mot <= trinta_dias
                )
            )
            filter_desc = "Compliance Alerts (TAX/MOT <= 30 days)"
        elif sf_lower in ['all', 'todas', 'tudo']:
            filter_desc = "All Statuses (Including Sold & Pound)"
        else:
            query = query.filter(Motorcycle.status.ilike(status_filter))
            filter_desc = f"Status: {status_filter}"

    if v5c_filter in ['missing', 'none', 'sem', '0']:
        query = query.filter(~Motorcycle.v5c_arquivos.any())
        filter_desc += " [Missing V5C]"

    if search:
        search_clean = search.strip().replace(' ', '')
        search_term = f"%{search.strip()}%"
        search_plate_term = f"%{search_clean}%"
        search_filters = [
            Motorcycle.placa.ilike(search_plate_term),
            Motorcycle.placa.ilike(search_term),
            Motorcycle.modelo.ilike(search_term),
            Motorcycle.cor.ilike(search_term),
            Motorcycle.status.ilike(search_term)
        ]
        if search.strip().lower() == 'sorn':
            search_filters.append(Motorcycle.tax_sorn == True)
        elif search.strip().lower() in ['missing_v5c', 'missing v5c', 'no v5c', 'sem v5c']:
            search_filters.append(~Motorcycle.v5c_arquivos.any())
        query = query.filter(db.or_(*search_filters))
        filter_desc += f' (Search: "{search}")'

    motos = query.order_by(Motorcycle.placa.asc()).all()

    dados = []
    for m in motos:
        contratos_sorted = sorted(m.contratos, key=lambda x: x.id, reverse=True) if m.contratos else []
        active_c = next((c for c in contratos_sorted if c.status in [ContractStatus.ACTIVE.value, 'Active', 'Ativo', ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold']), None)
        last_c = contratos_sorted[0] if contratos_sorted else None

        active_str = '-'
        if active_c:
            hirer_nome = (active_c.cliente.nome if active_c.cliente else active_c.cliente_nome) or 'N/A'
            active_str = f"#{active_c.id} • {hirer_nome}"
        elif last_c:
            client_nome = (last_c.cliente.nome if last_c.cliente else last_c.cliente_nome) or ''
            active_str = f"Last: #{last_c.id}" + (f" ({client_nome})" if client_nome else "")

        tax_str = 'SORN' if getattr(m, 'tax_sorn', False) else (m.vencimento_tax.strftime('%d/%m/%Y') if m.vencimento_tax else '-')
        mot_str = m.vencimento_mot.strftime('%d/%m/%Y') if m.vencimento_mot else '-'

        dados.append({
            'placa': m.placa,
            'modelo_cor': f"{m.modelo} ({m.cor})" if m.cor else m.modelo,
            'milhagem': f"{int(m.milhagem_atual or 0):,} mi",
            'status': m.status,
            'tax': tax_str,
            'mot': mot_str,
            'contrato_hirer': active_str
        })

    agora_london = get_london_now()
    agora = agora_london.strftime('%d/%m/%Y %H:%M')
    return render_template('relatorio_fleet.html', dados=dados, total=len(dados), filter_desc=filter_desc, agora=agora)

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

    # Se for Contrato de Compra de Veículo Usado (Used Vehicle Purchase Agreement da J&F Motorcycles LTD)
    if getattr(contrato, 'tipo_contrato', None) in [ContractType.PURCHASE.value, 'Purchase', 'Compra']:
        milhagem_val = contrato.milhagem_inicial if contrato.milhagem_inicial is not None else (moto.milhagem_atual if moto else 0)
        milhagem_str = "Unverified (0 mi / non-runner)" if (contrato.milhagem_nao_verificada or not milhagem_val) else f"{milhagem_val:,} miles"
        data_hora_doc = (contrato.data_assinatura_inicial or contrato.data_retirada or get_local_now()).strftime('%d/%m/%Y %H:%M')

        return render_template(
            'contrato_compra_print.html',
            contrato=contrato,
            cliente=cliente,
            moto=moto,
            cliente_nome=cliente_nome,
            cliente_telefone=cliente_telefone,
            cliente_endereco=cliente_endereco,
            cliente_email=cliente_email or 'N/A',
            moto_modelo=moto_modelo,
            moto_cor=moto_cor,
            moto_placa=moto_placa,
            categoria_historico=contrato.categoria_historico or 'Clear',
            milhagem_str=milhagem_str,
            valor_compra=float(contrato.valor_compra_veiculo or 0.0),
            metodo_pagamento=contrato.metodo_pagamento_compra or 'Bank Transfer',
            detalhes_pagamento=contrato.detalhes_pagamento_compra or '-',
            data_assinatura_uk=data_assinatura_inicial_uk,
            data_hora_documento=data_hora_doc
        )

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
            total_paginas=3 if is_installment else 2,
            cronograma=cronograma,
            data_assinatura_uk=data_assinatura_inicial_uk,
            hoje_uk=get_local_now().strftime('%d/%m/%Y %H:%M')
        )

    # Contrato de Aluguel (Motorcycle Rental Agreement)
    # IMPORTANTE: O documento do contrato impresso é estritamente imutável (legalmente assinado).
    # O dia de pagamento no documento impresso reflete sempre o dia originalmente assinado no snapshot
    # (dia_pagamento_semanal_original), mesmo se a agenda de cobranças futuras for alterada no sistema.
    dia_assinado = contrato.dia_pagamento_semanal_original if contrato.dia_pagamento_semanal_original is not None else contrato.dia_pagamento_semanal
    dias_nomes = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dia_pagamento_nome = dias_nomes[dia_assinado] if (dia_assinado is not None and 0 <= dia_assinado <= 6) else 'Monday'
    
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
        data_assinatura_devolucao_uk=data_assinatura_devolucao_uk,
        total_paginas=3
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

    status_antigo = claim.status
    status_ind_antigo = claim.status_indicacao
    status_stor_antigo = claim.status_storage
    status_pag_stor_antigo = claim.status_pagamento_storage
    data_lib_antiga = claim.data_liberacao_storage
    data_inv_antiga = claim.data_envio_invoice

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

    alteracoes = []
    if claim.status != status_antigo:
        alteracoes.append(f"Status do processo: '{status_antigo}' -> '{claim.status}'")
    if claim.data_liberacao_storage and claim.data_liberacao_storage != data_lib_antiga:
        alteracoes.append(f"Veículo liberado do pátio em {claim.data_liberacao_storage.strftime('%d/%m/%Y')} ({claim.dias_storage} diárias, £{claim.valor_total_storage:.2f})")
    if claim.data_envio_invoice and claim.data_envio_invoice != data_inv_antiga:
        alteracoes.append(f"Invoice enviado em {claim.data_envio_invoice.strftime('%d/%m/%Y')}")
    if claim.status_indicacao == 'Pago' and status_ind_antigo != 'Pago':
        alteracoes.append(f"Comissão de indicação (£{claim.valor_indicacao:.2f}) recebida/paga")
    if claim.status_pagamento_storage == 'Pago' and status_pag_stor_antigo != 'Pago':
        alteracoes.append(f"Storage (£{claim.valor_total_storage:.2f}) recebido/pago")

    detalhes_log = f"Claim #{claim.claim_number} ({claim.empresa_parceira}): {'; '.join(alteracoes)} por {operador}" if alteracoes else f"Claim #{claim.claim_number} ({claim.empresa_parceira}) atualizado por {operador}"
    registrar_log('CLAIM_UPDATE', 'Claim', claim.id, detalhes_log)

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
            'perm_financeiro': bool(getattr(u, 'perm_financeiro', True)),
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
    perm_financeiro = bool(data.get('perm_financeiro', True))
    perm_claims = bool(data.get('perm_claims', False))
    
    if not nome or not email or not password:
        return jsonify({'error': 'Name, email, and password are required'}), 400
        
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long', 'erro': 'A senha deve ter no mínimo 8 caracteres'}), 400
        
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
        perm_financeiro=perm_financeiro,
        perm_claims=perm_claims,
        ativo=True
    )
    novo_user.set_password(password)
    
    db.session.add(novo_user)
    db.session.commit()
    
    perm_textos = []
    if is_admin: perm_textos.append('Admin')
    if perm_alugueis: perm_textos.append('Aluguel / Venda')
    if perm_financeiro: perm_textos.append('Financeiro')
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
            'perm_financeiro': novo_user.perm_financeiro,
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
    
    is_master = bool(user.email and user.email.strip().lower() == 'tmuniz570@gmail.com')

    # Strict protection for root administrator
    if is_master:
        if 'is_admin' in data and not bool(data['is_admin']):
            return jsonify({'error': 'Administrator privileges cannot be removed from root administrator tmuniz570@gmail.com', 'erro': 'Não é permitido remover privilégios de administrador do usuário mestre tmuniz570@gmail.com.'}), 403
        if 'ativo' in data and not bool(data['ativo']):
            return jsonify({'error': 'The root administrator account (tmuniz570@gmail.com) cannot be suspended or deactivated.', 'erro': 'A conta de administrador mestre (tmuniz570@gmail.com) não pode ser desativada ou suspensa.'}), 403
        if 'email' in data and data['email'].strip().lower() != 'tmuniz570@gmail.com':
            return jsonify({'error': 'The email address of root administrator tmuniz570@gmail.com cannot be changed.', 'erro': 'O email do administrador mestre tmuniz570@gmail.com não pode ser alterado.'}), 403

    # Check if modifying name
    if 'nome' in data and data['nome'].strip():
        if user.nome != data['nome'].strip():
            alteracoes.append(f"nome de '{user.nome}' para '{data['nome'].strip()}'")
            user.nome = data['nome'].strip()
        
    # Check if modifying permissions
    if 'is_admin' in data:
        novo_admin = bool(data['is_admin'])
        if is_master and not novo_admin:
            return jsonify({'error': 'Administrator privileges cannot be removed from root administrator tmuniz570@gmail.com'}), 403
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

    if 'perm_financeiro' in data:
        nova_perm_fin = bool(data['perm_financeiro'])
        if user.perm_financeiro != nova_perm_fin:
            alteracoes.append(f"financeiro={'Ativado' if nova_perm_fin else 'Desativado'}")
            user.perm_financeiro = nova_perm_fin

    if 'perm_claims' in data:
        nova_perm_claims = bool(data['perm_claims'])
        if user.perm_claims != nova_perm_claims:
            alteracoes.append(f"modulo_claims={'Ativado' if nova_perm_claims else 'Desativado'}")
            user.perm_claims = nova_perm_claims
            
    # Check if modifying status (ativo)
    if 'ativo' in data:
        novo_status = bool(data['ativo'])
        if is_master and not novo_status:
            return jsonify({'error': 'The root administrator account tmuniz570@gmail.com cannot be suspended'}), 403
        if user.id == current_user.id and not novo_status:
            return jsonify({'error': 'You cannot suspend your own account'}), 400
        if user.ativo != novo_status:
            status_txt = "Ativado" if novo_status else "Suspenso"
            alteracoes.append(f"status alterado para {status_txt}")
            user.ativo = novo_status
        
    # Check if updating password
    if 'password' in data and data['password']:
        if len(data['password']) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long', 'erro': 'A senha deve ter no mínimo 8 caracteres'}), 400
        user.set_password(data['password'])
        alteracoes.append("senha redefinida")
        
    # Guarantee root administrator immutable permissions
    if is_master:
        user.email = 'tmuniz570@gmail.com'
        user.is_admin = True
        user.role = 'admin'
        user.ativo = True
        user.perm_alugueis = True
        user.perm_financeiro = True
        user.perm_claims = True

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
            'perm_financeiro': user.perm_financeiro,
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
    
    if user.email and user.email.strip().lower() == 'tmuniz570@gmail.com':
        return jsonify({
            'error': 'This root administrator account (tmuniz570@gmail.com) is system-protected and cannot be deleted under any circumstances.',
            'erro': 'Esta conta de administrador raiz (tmuniz570@gmail.com) é protegida pelo sistema e não pode ser excluída sob nenhuma circunstância.'
        }), 403

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

    if len(nova_senha) < 8:
        return jsonify({'error': 'A nova senha deve ter no mínimo 8 caracteres.'}), 400

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
    usuario_filtro = request.args.get('usuario', '', type=str).strip()
    entidade_filtro = request.args.get('entidade', '', type=str).strip()
    data_inicio = request.args.get('data_inicio', '', type=str).strip()
    data_fim = request.args.get('data_fim', '', type=str).strip()
    data_filtro = request.args.get('data', '', type=str).strip()
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
    if usuario_filtro:
        query = query.filter(AuditLog.usuario_nome == usuario_filtro)
    if entidade_filtro:
        query = query.filter(AuditLog.entidade.ilike(f"%{entidade_filtro}%"))
        
    if data_inicio and data_fim:
        try:
            dt_i = datetime.strptime(data_inicio, "%Y-%m-%d")
            dt_f = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(AuditLog.data_hora >= dt_i, AuditLog.data_hora < dt_f)
        except ValueError:
            pass
    elif data_inicio:
        try:
            dt_i = datetime.strptime(data_inicio, "%Y-%m-%d")
            query = query.filter(AuditLog.data_hora >= dt_i)
        except ValueError:
            pass
    elif data_fim:
        try:
            dt_f = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(AuditLog.data_hora < dt_f)
        except ValueError:
            pass
    elif data_filtro:
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
        'timestamp': AuditLog.data_hora,
        'usuario_nome': AuditLog.usuario_nome,
        'usuario': AuditLog.usuario_nome,
        'user': AuditLog.usuario_nome,
        'staff': AuditLog.usuario_nome,
        'operator': AuditLog.usuario_nome,
        'acao': AuditLog.acao,
        'action': AuditLog.acao,
        'entidade': AuditLog.entidade,
        'target': AuditLog.entidade,
        'entidade_id': AuditLog.entidade_id,
        'descricao': AuditLog.descricao,
        'description': AuditLog.descricao,
        'activity': AuditLog.descricao,
        'ip_origem': AuditLog.ip_origem,
        'ip': AuditLog.ip_origem
    }
    target_col = sort_map.get(sort_by, AuditLog.data_hora)
    order_func = target_col.desc() if sort_order == 'desc' else target_col.asc()
    # Secondary order on id to ensure deterministic row order across pages
    paginated = query.order_by(order_func, AuditLog.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    
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
    
    # Calculate live audit stats for today
    hoje = get_london_date()
    dt_hoje_inicio = datetime.combine(hoje, datetime.min.time())
    base_hoje = AuditLog.query.filter(AuditLog.data_hora >= dt_hoje_inicio)
    total_hoje = base_hoje.count()
    operadores_hoje = db.session.query(db.func.count(db.distinct(AuditLog.usuario_nome))).filter(AuditLog.data_hora >= dt_hoje_inicio).scalar() or 0
    financeiro_hoje = base_hoje.filter(db.or_(
        AuditLog.acao.ilike('%PAYMENT%'),
        AuditLog.acao.ilike('%CHARGE%'),
        AuditLog.acao.ilike('%TRANSACTION%'),
        AuditLog.acao.ilike('%CASH%')
    )).count()
    seguranca_hoje = base_hoje.filter(db.or_(
        AuditLog.acao.ilike('%LOGIN%'),
        AuditLog.acao.ilike('%USER%'),
        AuditLog.acao.ilike('%PASSWORD%'),
        AuditLog.acao.ilike('%SECURITY%')
    )).count()
    
    return jsonify({
        'itens': itens,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page,
        'stats': {
            'hoje': total_hoje,
            'operadores_hoje': operadores_hoje,
            'financeiro_hoje': financeiro_hoje,
            'seguranca_hoje': seguranca_hoje
        }
    })

@app.route('/api/auditoria/exportar-csv', methods=['GET'])
@admin_required
def exportar_auditoria_csv():
    import io
    import csv
    
    search = request.args.get('search', '', type=str)
    acao = request.args.get('acao', '', type=str)
    usuario_filtro = request.args.get('usuario', '', type=str).strip()
    entidade_filtro = request.args.get('entidade', '', type=str).strip()
    data_inicio = request.args.get('data_inicio', '', type=str).strip()
    data_fim = request.args.get('data_fim', '', type=str).strip()
    data_filtro = request.args.get('data', '', type=str).strip()
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
    if usuario_filtro:
        query = query.filter(AuditLog.usuario_nome == usuario_filtro)
    if entidade_filtro:
        query = query.filter(AuditLog.entidade.ilike(f"%{entidade_filtro}%"))
        
    if data_inicio and data_fim:
        try:
            dt_i = datetime.strptime(data_inicio, "%Y-%m-%d")
            dt_f = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(AuditLog.data_hora >= dt_i, AuditLog.data_hora < dt_f)
        except ValueError:
            pass
    elif data_inicio:
        try:
            dt_i = datetime.strptime(data_inicio, "%Y-%m-%d")
            query = query.filter(AuditLog.data_hora >= dt_i)
        except ValueError:
            pass
    elif data_fim:
        try:
            dt_f = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(AuditLog.data_hora < dt_f)
        except ValueError:
            pass
    elif data_filtro:
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
        'timestamp': AuditLog.data_hora,
        'usuario_nome': AuditLog.usuario_nome,
        'usuario': AuditLog.usuario_nome,
        'user': AuditLog.usuario_nome,
        'operator': AuditLog.usuario_nome,
        'staff': AuditLog.usuario_nome,
        'acao': AuditLog.acao,
        'action': AuditLog.acao,
        'entidade': AuditLog.entidade,
        'target': AuditLog.entidade,
        'entidade_id': AuditLog.entidade_id,
        'descricao': AuditLog.descricao,
        'ip_origem': AuditLog.ip_origem,
        'ip': AuditLog.ip_origem
    }
    target_col = sort_map.get(sort_by, AuditLog.data_hora)
    order_func = target_col.desc() if sort_order == 'desc' else target_col.asc()
    registros = query.order_by(order_func, AuditLog.id.desc()).limit(2500).all()
    
    output = io.StringIO()
    output.write('\ufeff')  # UTF-8 BOM
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(['Event ID', 'Date & Time (London)', 'Staff / Operator', 'Action Key', 'Activity Description', 'Target Entity', 'Target ID', 'IP Address'])
    
    for r in registros:
        dt_fmt = r.data_hora.strftime('%d/%m/%Y %H:%M:%S') if r.data_hora else ''
        writer.writerow([
            r.id,
            dt_fmt,
            r.usuario_nome or 'System',
            r.acao or '',
            r.descricao or '',
            r.entidade or '',
            r.entidade_id or '',
            r.ip_origem or ''
        ])
        
    csv_bytes = output.getvalue().encode('utf-8')
    filename = f"ffmotors_audit_trail_{get_london_date().strftime('%Y%m%d')}.csv"
    
    return Response(
        csv_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# --- CRUD ROUTES ---

def capitalize_words(text):
    if not text:
        return text
    return re.sub(r'\b([a-zÀ-ÿ])', lambda m: m.group(1).upper(), str(text).strip())

def normalize_phone_canonical(phone):
    """
    Normalizes UK and International phone numbers to canonical digits:
    - If starts with '+': international country code (e.g. +55 11 98765-4321 -> 5511987654321, +351 -> 351...)
    - If starts with '00': international dialing prefix (e.g. 0055 11... -> 5511...)
    - If starts with UK '07...' (11 digits): converts to UK international '447...'
    - If starts with UK '7...' (10 digits): converts to UK international '447...'
    - If typed as +4407...: strips redundant UK 0 -> 447...
    - Strips all formatting spaces, dashes, parentheses and non-digit characters.
    """
    if not phone:
        return ""
    raw = str(phone).strip()
    if not raw:
        return ""
    if raw.startswith('+'):
        digits = re.sub(r'\D', '', raw)
        if digits.startswith('440') and len(digits) >= 12:
            digits = '44' + digits[3:]
        return digits
    if raw.startswith('00'):
        digits = re.sub(r'\D', '', raw[2:])
        if digits.startswith('440') and len(digits) >= 12:
            digits = '44' + digits[3:]
        return digits
    digits = re.sub(r'\D', '', raw)
    if not digits:
        return ""
    if digits.startswith('0') and (len(digits) == 11 or digits.startswith('07')):
        return '44' + digits[1:]
    if digits.startswith('7') and len(digits) == 10:
        return '44' + digits
    if digits.startswith('44'):
        if digits.startswith('440') and len(digits) >= 12:
            digits = '44' + digits[3:]
        return digits
    return digits

@app.route('/api/clientes/verificar-duplicado', methods=['GET'])
@alugueis_required
def verificar_cliente_duplicado():
    telefone = request.args.get('telefone', '').strip()
    email = request.args.get('email', '').strip()
    exclude_id = request.args.get('exclude_id', type=int)

    # 1. Check Phone (International & UK Canonical Match)
    if telefone:
        norm_tel = normalize_phone_canonical(telefone)
        if norm_tel and len(norm_tel) >= 7:
            last7 = norm_tel[-7:]
            candidates = Client.query.filter(Client.telefone.ilike(f"%{last7}%")).all()
            for cand in candidates:
                if exclude_id and cand.id == exclude_id:
                    continue
                if normalize_phone_canonical(cand.telefone) == norm_tel:
                    return jsonify({
                        'duplicate': True,
                        'matched_by': 'phone',
                        'client': {
                            'id': cand.id,
                            'nome': cand.nome,
                            'telefone': cand.telefone,
                            'email': cand.email
                        }
                    })

    # 2. Check Email
    if email:
        email_clean = email.strip()
        email_cand = Client.query.filter(db.func.lower(Client.email) == email_clean.lower()).first()
        if email_cand and (not exclude_id or email_cand.id != exclude_id):
            return jsonify({
                'duplicate': True,
                'matched_by': 'email',
                'client': {
                    'id': email_cand.id,
                    'nome': email_cand.nome,
                    'telefone': email_cand.telefone,
                    'email': email_cand.email
                }
            })

    return jsonify({'duplicate': False})

@app.route('/api/clientes', methods=['POST'])
@alugueis_required
def criar_cliente():
    nome = request.form.get('nome')
    telefone = request.form.get('telefone')
    email = request.form.get('email')
    endereco = request.form.get('endereco')
    allow_dup = request.form.get('allow_duplicate') == 'true' or (request.is_json and (request.get_json() or {}).get('allow_duplicate'))
    
    if not nome or not telefone:
        return jsonify({'error': 'Missing required fields (full name and phone are required)', 'erro': 'Dados incompletos (nome e telefone são obrigatórios)'}), 400
    
    nome = capitalize_words(nome)
    telefone = telefone.strip()
    endereco = capitalize_words(endereco) if endereco else None

    # Canonical phone duplicate check
    norm_tel = normalize_phone_canonical(telefone)
    if not allow_dup and norm_tel and len(norm_tel) >= 7:
        last7 = norm_tel[-7:]
        candidates = Client.query.filter(Client.telefone.ilike(f"%{last7}%")).all()
        for cand in candidates:
            if normalize_phone_canonical(cand.telefone) == norm_tel:
                return jsonify({
                    'error': f"A customer with this phone number is already registered: {cand.nome} (#{cand.id}).",
                    'erro': f"Um cliente com este telefone já está cadastrado: {cand.nome} (#{cand.id}).",
                    'existing_client': {
                        'id': cand.id,
                        'nome': cand.nome,
                        'telefone': cand.telefone,
                        'email': cand.email
                    }
                }), 400

    # Optional email: check uniqueness only if provided
    email_clean = email.strip() if (email and email.strip()) else None
    if email_clean:
        outro_email = Client.query.filter(db.func.lower(Client.email) == email_clean.lower()).first()
        if outro_email:
            return jsonify({
                'error': f"Email already registered for another customer: {outro_email.nome} (#{outro_email.id})",
                'erro': f"Email já cadastrado por outro cliente: {outro_email.nome} (#{outro_email.id})"
            }), 400
        
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
            
    notas_internas = request.form.get('notas_internas')
    if notas_internas is None and request.is_json:
        notas_internas = (request.get_json() or {}).get('notas_internas')
    notas_internas_clean = str(notas_internas).strip() if (notas_internas and str(notas_internas).strip()) else None

    novo_cliente = Client(
        nome=nome,
        telefone=telefone,
        email=email_clean,
        endereco=endereco,
        url_habilitacao=url_hab,
        url_habilitacao_verso=url_hab_verso,
        url_cbt=url_cbt,
        url_comprovante_endereco=url_comp_end,
        notas_internas=notas_internas_clean
    )
    db.session.add(novo_cliente)
    db.session.commit()
    
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    docs_anexados = []
    if url_hab: docs_anexados.append('CNH/Licence')
    if url_hab_verso: docs_anexados.append('Verso CNH')
    if url_cbt: docs_anexados.append('CBT')
    if url_comp_end: docs_anexados.append('Comprovante Residência')
    docs_info = f" (Documentos anexados: {', '.join(docs_anexados)})" if docs_anexados else ""
    registrar_log('CREATE_CLIENT', 'Client', novo_cliente.id, f"Cliente {novo_cliente.nome} (Tel: {novo_cliente.telefone}) cadastrado por {operador_atual}{docs_info}")

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

    tax_sorn = bool(dados.get('tax_sorn', False))
    vencimento_tax = None
    if not tax_sorn and dados.get('vencimento_tax'):
        try:
            vencimento_tax = datetime.strptime(dados['vencimento_tax'], "%Y-%m-%d").date()
        except ValueError:
            pass

    notas_moto = dados.get('notas_internas')
    notas_moto_clean = str(notas_moto).strip() if (notas_moto and str(notas_moto).strip()) else None

    nova_moto = Motorcycle(
        placa=placa,
        modelo=dados['modelo'].strip(),
        cor=dados['cor'].strip(),
        status=dados.get('status', MotoStatus.AVAILABLE.value),
        milhagem_atual=int(dados.get('milhagem_atual') or 0),
        vencimento_mot=vencimento_mot,
        vencimento_tax=vencimento_tax,
        tax_sorn=tax_sorn,
        notas_internas=notas_moto_clean
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
    limit = request.args.get('limit', 20, type=int)
    search = request.args.get('search', '', type=str).strip()
    client_id = request.args.get('id', None, type=int)
    status_filter = request.args.get('status', '', type=str).strip().lower()
    sort_by = request.args.get('sort_by', 'id', type=str).strip().lower()
    sort_order = request.args.get('sort_order', 'desc', type=str).strip().lower()
    
    query = Client.query
    if client_id:
        query = query.filter(Client.id == client_id)
    elif search:
        search_term = f"%{search}%"
        search_conds = [
            Client.nome.ilike(search_term),
            Client.telefone.ilike(search_term),
            Client.email.ilike(search_term),
            Client.endereco.ilike(search_term)
        ]
        clean_num = search.lstrip('#').strip()
        if clean_num.isdigit():
            search_conds.append(Client.id == int(clean_num))
        query = query.filter(db.or_(*search_conds))
    
    # Subqueries for status filters & compliance evaluation
    london_now_kpi = get_london_now()
    hoje_zero_kpi = london_now_kpi.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    
    active_contract_subq = db.session.query(Contract.id).filter(
        Contract.id_cliente == Client.id,
        Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo', ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold'])
    ).exists()

    overdue_tx_subq = db.session.query(FinancialTransaction.id).join(
        Contract, FinancialTransaction.id_contrato == Contract.id
    ).filter(
        Contract.id_cliente == Client.id,
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
        FinancialTransaction.data_vencimento < hoje_zero_kpi,
        ~FinancialTransaction.tipo.in_([TransactionType.DEPOSIT_REFUND.value, 'Deposit_Refund', 'Devolucao_Deposito'])
    ).exists()

    missing_docs_cond = db.or_(
        Client.url_habilitacao == None,
        Client.url_habilitacao == '',
        Client.url_habilitacao_verso == None,
        Client.url_habilitacao_verso == '',
        Client.url_comprovante_endereco == None,
        Client.url_comprovante_endereco == ''
    )

    if status_filter:
        if status_filter in ['active', 'active_deals', 'active_drivers', 'active_hirers']:
            query = query.filter(active_contract_subq)
        elif status_filter in ['no_deal', 'inactive']:
            query = query.filter(~active_contract_subq)
        elif status_filter in ['overdue', 'debts', 'late']:
            query = query.filter(overdue_tx_subq)
        elif status_filter in ['missing_docs', 'missing_licence', 'incomplete']:
            query = query.filter(missing_docs_cond)
        elif status_filter in ['clean', 'compliant']:
            query = query.filter(~overdue_tx_subq, ~missing_docs_cond)

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
    order_clauses = []
    if search:
        clean_num = search.lstrip('#').strip()
        if clean_num.isdigit():
            order_clauses.append(db.case((Client.id == int(clean_num), 0), else_=1))
    order_clauses.append(order_func)
    
    paginated = query.order_by(*order_clauses).paginate(page=page, per_page=limit, error_out=False)
    
    client_ids = [c.id for c in paginated.items]

    # Batch load active deals for clients in current page
    active_contracts_map = {}
    if client_ids:
        active_deals = Contract.query.options(
            selectinload(Contract.moto)
        ).filter(
            Contract.id_cliente.in_(client_ids),
            Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo', ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold'])
        ).order_by(Contract.id.desc()).all()
        for deal in active_deals:
            if deal.id_cliente not in active_contracts_map:
                active_contracts_map[deal.id_cliente] = []
            active_contracts_map[deal.id_cliente].append({
                'id': deal.id,
                'tipo': deal.tipo_contrato or 'Rent',
                'status': deal.status,
                'placa': deal.placa or (deal.moto.placa if deal.moto else None),
                'moto_modelo': deal.moto_modelo or (deal.moto.modelo if deal.moto else None),
                'moto_cor': deal.moto_cor or (deal.moto.cor if deal.moto else None)
            })

    # Batch load overdue stats for clients in current page
    overdue_stats_map = {}
    if client_ids:
        overdue_rows = db.session.query(
            Contract.id_cliente,
            db.func.count(FinancialTransaction.id).label('qtd_vencidas'),
            db.func.sum(FinancialTransaction.valor).label('total_vencido')
        ).join(Contract, FinancialTransaction.id_contrato == Contract.id).filter(
            Contract.id_cliente.in_(client_ids),
            FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
            FinancialTransaction.data_vencimento < hoje_zero_kpi,
            ~FinancialTransaction.tipo.in_([TransactionType.DEPOSIT_REFUND.value, 'Deposit_Refund', 'Devolucao_Deposito'])
        ).group_by(Contract.id_cliente).all()
        for row in overdue_rows:
            overdue_stats_map[row.id_cliente] = {
                'qtd_vencidas': int(row.qtd_vencidas or 0),
                'total_vencido': round(float(row.total_vencido or 0.0), 2)
            }

    # Batch load total lifetime deals count per client in current page
    deals_count_map = {}
    if client_ids:
        deals_rows = db.session.query(
            Contract.id_cliente,
            db.func.count(Contract.id)
        ).filter(Contract.id_cliente.in_(client_ids)).group_by(Contract.id_cliente).all()
        deals_count_map = dict(deals_rows)

    itens = []
    for c in paginated.items:
        acts = active_contracts_map.get(c.id, [])
        has_active_deal = len(acts) > 0
        active_deal = acts[0] if has_active_deal else None
        
        ov = overdue_stats_map.get(c.id, {'qtd_vencidas': 0, 'total_vencido': 0.0})
        has_overdue = ov['qtd_vencidas'] > 0
        
        has_licence_front = bool(c.url_habilitacao)
        has_licence_back = bool(c.url_habilitacao_verso)
        has_cbt = bool(c.url_cbt)
        has_proof_address = bool(c.url_comprovante_endereco)
        
        missing_docs = []
        if not has_licence_front: missing_docs.append('Licence Front')
        if not has_licence_back: missing_docs.append('Licence Back')
        if not has_proof_address: missing_docs.append('Proof of Address')
        
        if has_overdue:
            status_dot = 'danger'
            status_dot_title = f"{ov['qtd_vencidas']} overdue payment{'s' if ov['qtd_vencidas'] > 1 else ''} (£{ov['total_vencido']:.2f})"
        elif missing_docs:
            status_dot = 'warning'
            status_dot_title = f"Missing: {', '.join(missing_docs)}"
        else:
            status_dot = 'success'
            status_dot_title = "All clear / Up to date"

        itens.append({
            'id': c.id,
            'nome': c.nome,
            'telefone': c.telefone,
            'email': c.email,
            'endereco': c.endereco,
            'url_habilitacao': c.url_habilitacao,
            'url_habilitacao_verso': c.url_habilitacao_verso,
            'url_cbt': c.url_cbt,
            'url_comprovante_endereco': c.url_comprovante_endereco,
            'has_licence_front': has_licence_front,
            'has_licence_back': has_licence_back,
            'has_cbt': has_cbt,
            'has_proof_address': has_proof_address,
            'missing_docs': missing_docs,
            'notas_internas': c.notas_internas,
            'status_dot': status_dot,
            'status_dot_title': status_dot_title,
            'has_active_deal': has_active_deal,
            'active_deals_count': len(acts),
            'active_deal': active_deal,
            'total_deals': deals_count_map.get(c.id, 0),
            'overdue_count': ov['qtd_vencidas'],
            'overdue_amount': ov['total_vencido']
        })
    
    # Executive KPIs for top summary strip
    kpi_total_customers = Client.query.count()

    kpi_active_hirers_subq = db.session.query(Contract.id_cliente).filter(
        Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo', ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold'])
    ).distinct().subquery()
    kpi_active_hirers = db.session.query(db.func.count()).select_from(kpi_active_hirers_subq).scalar() or 0

    overdue_clients_subq = db.session.query(
        Contract.id_cliente,
        db.func.sum(FinancialTransaction.valor).label('tot_venc')
    ).join(Contract, FinancialTransaction.id_contrato == Contract.id).filter(
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
        FinancialTransaction.data_vencimento < hoje_zero_kpi,
        ~FinancialTransaction.tipo.in_([TransactionType.DEPOSIT_REFUND.value, 'Deposit_Refund', 'Devolucao_Deposito'])
    ).group_by(Contract.id_cliente).subquery()

    overdue_stats = db.session.query(
        db.func.count().label('count'),
        db.func.sum(overdue_clients_subq.c.tot_venc).label('sum_tot')
    ).select_from(overdue_clients_subq).first()

    kpi_overdue_count = overdue_stats.count if overdue_stats else 0
    kpi_overdue_amount = round(float(overdue_stats.sum_tot or 0.0), 2) if overdue_stats else 0.0

    kpi_missing_docs = Client.query.filter(missing_docs_cond).count()

    return jsonify({
        'itens': itens,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page,
        'kpis': {
            'total': kpi_total_customers,
            'active_hirers': kpi_active_hirers,
            'overdue_count': kpi_overdue_count,
            'overdue_amount': kpi_overdue_amount,
            'missing_docs': kpi_missing_docs
        }
    })

@app.route('/api/clientes/<int:id>', methods=['PUT'])
@alugueis_required
def atualizar_cliente(id):
    cliente = db.session.get(Client, id)
    if not cliente:
        return jsonify({'error': 'Customer not found', 'erro': 'Cliente não encontrado'}), 404
        
    nome_antigo = cliente.nome
    tel_antigo = cliente.telefone
    email_antigo = cliente.email
    end_antigo = cliente.endereco
    hab_antiga = cliente.url_habilitacao
    hab_verso_antiga = cliente.url_habilitacao_verso
    cbt_antigo = cliente.url_cbt
    comp_end_antigo = cliente.url_comprovante_endereco
    notas_antigas = getattr(cliente, 'notas_internas', None)

    if request.is_json:
        dados = request.get_json() or {}
        if 'nome' in dados: cliente.nome = capitalize_words(dados['nome']) if dados['nome'] else cliente.nome
        if 'telefone' in dados: cliente.telefone = dados['telefone'].strip() if dados['telefone'] else cliente.telefone
        if 'email' in dados:
            raw_email = dados['email']
            email_clean = raw_email.strip() if (raw_email and raw_email.strip()) else None
            if email_clean:
                outro = Client.query.filter(db.func.lower(Client.email) == email_clean.lower(), Client.id != id).first()
                if outro: return jsonify({'error': 'Email already registered for another customer', 'erro': 'Email já cadastrado por outro cliente'}), 400
            cliente.email = email_clean
        if 'endereco' in dados: cliente.endereco = capitalize_words(dados['endereco']) if dados['endereco'] else None
        if 'notas_internas' in dados:
            cliente.notas_internas = str(dados['notas_internas']).strip() if (dados['notas_internas'] and str(dados['notas_internas']).strip()) else None
    else:
        # Security: Validate upload file extensions
        for campo_file in ['habilitacao', 'habilitacao_verso', 'cbt', 'comprovante_endereco']:
            if campo_file in request.files:
                f = request.files[campo_file]
                if f and f.filename and not is_allowed_file(f.filename):
                    return jsonify({'error': 'Invalid file format. Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': 'Formato de arquivo inválido. Permitido apenas JPG, PNG, WEBP e PDF.'}), 400

        if 'nome' in request.form: cliente.nome = capitalize_words(request.form['nome']) if request.form['nome'] else cliente.nome
        if 'telefone' in request.form: cliente.telefone = request.form['telefone'].strip()
        if 'endereco' in request.form: cliente.endereco = capitalize_words(request.form['endereco']) if request.form['endereco'] else None
        if 'notas_internas' in request.form:
            cliente.notas_internas = str(request.form['notas_internas']).strip() if (request.form['notas_internas'] and str(request.form['notas_internas']).strip()) else None
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

    alteracoes = []
    if cliente.nome != nome_antigo:
        alteracoes.append(f"Nome alterado para '{cliente.nome}'")
    if cliente.telefone != tel_antigo:
        alteracoes.append(f"Telefone alterado de '{tel_antigo or 'N/A'}' para '{cliente.telefone}'")
    if (cliente.email or '').lower() != (email_antigo or '').lower():
        alteracoes.append(f"Email alterado para '{cliente.email or 'Nenhum'}'")
    if cliente.endereco != end_antigo:
        alteracoes.append("Endereço atualizado")
    if (cliente.notas_internas or '').strip() != (notas_antigas or '').strip():
        alteracoes.append("Notas internas atualizadas")
    if cliente.url_habilitacao != hab_antiga:
        alteracoes.append("Nova CNH/Licence anexada")
    if cliente.url_habilitacao_verso != hab_verso_antiga:
        alteracoes.append("Novo Verso da CNH anexado")
    if cliente.url_cbt != cbt_antigo:
        alteracoes.append("Novo certificado CBT anexado")
    if cliente.url_comprovante_endereco != comp_end_antigo:
        alteracoes.append("Novo comprovante de residência anexado")

    detalhes_log = f"Cliente {cliente.nome}: {', '.join(alteracoes)} por {operador_atual}" if alteracoes else f"Cliente {cliente.nome} atualizado por {operador_atual}"
    registrar_log('CLIENT_UPDATE', 'Client', cliente.id, detalhes_log)

    return jsonify({'message': 'Customer updated successfully', 'mensagem': 'Cliente atualizado com sucesso'}), 200

@app.route('/api/clientes/merge', methods=['POST'])
@alugueis_required
def mesclar_clientes():
    dados = request.get_json() or {}
    source_id = dados.get('source_id')
    target_id = dados.get('target_id')
    motivo = (dados.get('motivo') or '').strip()

    if not source_id or not target_id:
        return jsonify({
            'error': 'Both source (duplicate) and target (primary) customer IDs are required',
            'erro': 'IDs do cliente duplicado e principal são obrigatórios'
        }), 400

    try:
        source_id = int(source_id)
        target_id = int(target_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid customer IDs', 'erro': 'IDs de cliente inválidos'}), 400

    if source_id == target_id:
        return jsonify({
            'error': 'Cannot merge a customer into itself. Source and target must be different.',
            'erro': 'Não é possível fundir um cliente nele mesmo. Origem e destino devem ser distintos.'
        }), 400

    source = db.session.get(Client, source_id)
    target = db.session.get(Client, target_id)

    if not source:
        return jsonify({'error': f'Duplicate customer #{source_id} not found', 'erro': f'Cliente duplicado #{source_id} não encontrado'}), 404
    if not target:
        return jsonify({'error': f'Primary customer #{target_id} not found', 'erro': f'Cliente principal #{target_id} não encontrado'}), 404

    source_nome = source.nome
    source_tel = source.telefone
    source_email = source.email
    target_nome = target.nome
    target_tel = target.telefone

    # 1. Transfer all contracts
    contratos = Contract.query.filter_by(id_cliente=source_id).all()
    qtd_contratos = len(contratos)
    for c in contratos:
        c.id_cliente = target_id
        c.cliente = target
    source.contratos = []
    db.session.flush()

    # 2. Enrich target client with missing documents / fields
    docs_merged = []
    if not target.url_habilitacao and source.url_habilitacao:
        target.url_habilitacao = source.url_habilitacao
        docs_merged.append('Driving Licence (Front)')
    if not target.url_habilitacao_verso and source.url_habilitacao_verso:
        target.url_habilitacao_verso = source.url_habilitacao_verso
        docs_merged.append('Driving Licence (Back)')
    if not target.url_cbt and source.url_cbt:
        target.url_cbt = source.url_cbt
        docs_merged.append('CBT Certificate')
    if not target.url_comprovante_endereco and source.url_comprovante_endereco:
        target.url_comprovante_endereco = source.url_comprovante_endereco
        docs_merged.append('Proof of Address')
    if not target.endereco and source.endereco:
        target.endereco = source.endereco

    # Safely transfer email if target doesn't have one and source does
    if not target.email and source.email:
        existing_email_owner = Client.query.filter(
            db.func.lower(Client.email) == source.email.lower(),
            Client.id != source_id,
            Client.id != target_id
        ).first()
        if not existing_email_owner:
            target.email = source.email

    # Append internal notes
    now_london_str = get_london_now().strftime('%d/%m/%Y %H:%M')
    merge_note_header = f"[MERGED from Customer #{source_id} ({source_nome}, Tel: {source_tel}) on {now_london_str}]"
    if motivo:
        merge_note_header += f" Reason: {motivo}."
    
    source_notes = (source.notas_internas or '').strip()
    if source_notes:
        full_note_addition = f"{merge_note_header}\nNotes from #{source_id}:\n{source_notes}"
    else:
        full_note_addition = f"{merge_note_header} (No prior internal notes)"

    if target.notas_internas:
        target.notas_internas = f"{target.notas_internas}\n\n{full_note_addition}"
    else:
        target.notas_internas = full_note_addition

    # 3. Delete source client
    db.session.delete(source)
    db.session.commit()

    # 4. Audit Log
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    desc_audit = (
        f"Fusão de clientes realizada por {operador_atual}: "
        f"Cliente duplicado #{source_id} ({source_nome}, Tel: {source_tel}) fundido no Cliente principal #{target_id} ({target_nome}, Tel: {target_tel}). "
        f"{qtd_contratos} contrato(s) transferido(s)."
    )
    if docs_merged:
        desc_audit += f" Documentos consolidados: {', '.join(docs_merged)}."
    if motivo:
        desc_audit += f" Motivo: {motivo}."

    registrar_log('CLIENT_MERGE', 'Client', str(target_id), desc_audit)

    return jsonify({
        'message': f'Customer #{source_id} ({source_nome}) successfully merged into #{target_id} ({target_nome})',
        'mensagem': f'Cliente #{source_id} ({source_nome}) fundido com sucesso no Cliente #{target_id} ({target_nome})',
        'target_id': target_id,
        'target_nome': target_nome,
        'source_id': source_id,
        'transferred_contracts': qtd_contratos,
        'docs_merged': docs_merged
    }), 200

@app.route('/api/motos', methods=['GET'])
@alugueis_required
def listar_motos():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', '', type=str).strip()
    v5c_filter = request.args.get('v5c', '', type=str).strip().lower()
    sort_by = request.args.get('sort_by', 'placa', type=str).strip().lower()
    sort_order = request.args.get('sort_order', 'asc', type=str).strip().lower()
    
    query = Motorcycle.query.options(
        selectinload(Motorcycle.v5c_arquivos),
        selectinload(Motorcycle.trackers),
        selectinload(Motorcycle.contratos).selectinload(Contract.cliente)
    )

    hoje_date = datetime.now(pytz.timezone('Europe/London')).date()

    # Mapeamento de contratos de compra ativos para ciclo de V5C atualizado (recompras)
    active_purchases = Contract.query.filter(
        Contract.tipo_contrato.in_([ContractType.PURCHASE.value, 'Purchase', 'Compra']),
        Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo'])
    ).all()
    active_purchases_map = {}
    repurchase_missing_plates = []
    repurchase_awaiting_plates = []
    for ap in active_purchases:
        p = (ap.moto_placa or ap.placa or '').strip().upper()
        if p:
            active_purchases_map[p] = ap
            docs_ap = get_purchase_contract_v5c_docs(ap)
            has_v5c_ap = any((getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'v5c' for v in docs_ap)
            has_slip_ap = any((getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'transfer_proof' for v in docs_ap)
            if not has_v5c_ap:
                repurchase_missing_plates.append(p)
                if has_slip_ap:
                    repurchase_awaiting_plates.append(p)

    if status_filter:
        sf_lower = status_filter.lower()
        if sf_lower in ['operational', 'in_operation', 'operacao', 'ativa', 'ativas', 'active']:
            query = query.filter(
                ~Motorcycle.status.in_([MotoStatus.POUND.value, 'Pound']),
                db.or_(
                    ~Motorcycle.status.in_([MotoStatus.SOLD.value, 'Sold', 'Vendida']),
                    Motorcycle.contratos.any(Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']))
                )
            )
        elif sf_lower == 'sorn':
            query = query.filter(Motorcycle.tax_sorn == True)
        elif sf_lower in ['missing_v5c', 'no_v5c', 'sem_v5c']:
            f_missing = [~Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'v5c')]
            if repurchase_missing_plates:
                f_missing.append(Motorcycle.placa.in_(repurchase_missing_plates))
            query = query.filter(db.or_(*f_missing))
        elif sf_lower in ['awaiting_v5c', 'slip_on_file', 'com_slip']:
            f_awaiting = [
                db.and_(
                    Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'transfer_proof'),
                    ~Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'v5c')
                )
            ]
            if repurchase_awaiting_plates:
                f_awaiting.append(Motorcycle.placa.in_(repurchase_awaiting_plates))
            query = query.filter(db.or_(*f_awaiting))
        elif sf_lower in ['no_v5c_no_slip', 'sem_nada']:
            query = query.filter(~Motorcycle.v5c_arquivos.any())
        elif sf_lower in ['warnings', 'tax_mot_warnings', 'alert', 'alerts']:
            trinta_dias = hoje_date + timedelta(days=30)
            query = query.filter(
                ~Motorcycle.status.in_([MotoStatus.POUND.value, 'Pound']),
                db.or_(
                    db.and_(
                        db.or_(
                            ~Motorcycle.status.in_([MotoStatus.SOLD.value, 'Sold', 'Vendida']),
                            Motorcycle.contratos.any(Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']))
                        ),
                        Motorcycle.tax_sorn == False,
                        Motorcycle.vencimento_tax <= trinta_dias
                    ),
                    Motorcycle.vencimento_mot <= trinta_dias
                )
            )
        elif sf_lower in ['all', 'todas', 'tudo']:
            pass
        else:
            query = query.filter(Motorcycle.status.ilike(status_filter))

    if v5c_filter in ['missing', 'none', 'sem', '0']:
        f_missing = [~Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'v5c')]
        if repurchase_missing_plates:
            f_missing.append(Motorcycle.placa.in_(repurchase_missing_plates))
        query = query.filter(db.or_(*f_missing))
    elif v5c_filter in ['awaiting', 'slip']:
        f_awaiting = [
            db.and_(
                Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'transfer_proof'),
                ~Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'v5c')
            )
        ]
        if repurchase_awaiting_plates:
            f_awaiting.append(Motorcycle.placa.in_(repurchase_awaiting_plates))
        query = query.filter(db.or_(*f_awaiting))
    elif v5c_filter in ['no_docs', 'no_slip']:
        query = query.filter(~Motorcycle.v5c_arquivos.any())

    if search:
        search_clean = search.strip().replace(' ', '')
        search_term = f"%{search.strip()}%"
        search_plate_term = f"%{search_clean}%"
        search_filters = [
            Motorcycle.placa.ilike(search_plate_term),
            Motorcycle.placa.ilike(search_term),
            Motorcycle.modelo.ilike(search_term),
            Motorcycle.cor.ilike(search_term),
            Motorcycle.status.ilike(search_term)
        ]
        if search.strip().lower() == 'sorn':
            search_filters.append(Motorcycle.tax_sorn == True)
        elif search.strip().lower() in ['missing_v5c', 'missing v5c', 'no v5c', 'sem v5c']:
            f_missing_search = [~Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'v5c')]
            if repurchase_missing_plates:
                f_missing_search.append(Motorcycle.placa.in_(repurchase_missing_plates))
            search_filters.append(db.or_(*f_missing_search))
        elif search.strip().lower() in ['awaiting_v5c', 'awaiting v5c', 'slip on file', 'slip']:
            f_awaiting_search = [
                db.and_(
                    Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'transfer_proof'),
                    ~Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'v5c')
                )
            ]
            if repurchase_awaiting_plates:
                f_awaiting_search.append(Motorcycle.placa.in_(repurchase_awaiting_plates))
            search_filters.append(db.or_(*f_awaiting_search))
        query = query.filter(db.or_(*search_filters))
        
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

    def _resumir_contrato(c):
        if not c:
            return None
        c_nome = (c.cliente.nome if c.cliente else c.cliente_nome) or 'N/A'
        c_tel = (c.cliente.telefone if c.cliente else c.cliente_telefone) or ''
        return {
            'id': c.id,
            'tipo': c.tipo_contrato,
            'status': c.status,
            'cliente_id': c.id_cliente,
            'cliente_nome': c_nome,
            'cliente_telefone': c_tel
        }
    
    itens = []
    for m in paginated.items:
        contratos_sorted = sorted(m.contratos, key=lambda x: x.id, reverse=True) if m.contratos else []
        active_c = next((c for c in contratos_sorted if c.status in [ContractStatus.ACTIVE.value, 'Active', 'Ativo', ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold']), None)
        last_c = contratos_sorted[0] if contratos_sorted else None

        active_purchase = active_purchases_map.get(m.placa)
        if active_purchase:
            docs_ciclo = get_purchase_contract_v5c_docs(active_purchase)
            v5c_oficiais = [v for v in docs_ciclo if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'v5c']
            transfer_slips = [v for v in docs_ciclo if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'transfer_proof']
        else:
            v5c_oficiais = [v for v in (m.v5c_arquivos or []) if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'v5c']
            transfer_slips = [v for v in (m.v5c_arquivos or []) if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'transfer_proof']

        itens.append({
            'placa': m.placa,
            'modelo': m.modelo,
            'cor': m.cor,
            'status': m.status,
            'milhagem_atual': int(m.milhagem_atual or 0),
            'vencimento_mot': m.vencimento_mot.strftime('%Y-%m-%d') if m.vencimento_mot else None,
            'vencimento_tax': m.vencimento_tax.strftime('%Y-%m-%d') if m.vencimento_tax else None,
            'tax_sorn': bool(getattr(m, 'tax_sorn', False)),
            'notas_internas': m.notas_internas,
            'v5c_count': len(v5c_oficiais),
            'transfer_proof_count': len(transfer_slips),
            'has_v5c': len(v5c_oficiais) > 0,
            'has_transfer_proof': len(transfer_slips) > 0,
            'trackers_count': len(m.trackers) if m.trackers else 0,
            'trackers_summary': [{
                'id': tr.id,
                'numero': tr.numero,
                'tipo_propriedade': tr.tipo_propriedade
            } for tr in (m.trackers or [])],
            'active_contract': _resumir_contrato(active_c),
            'last_contract': _resumir_contrato(last_c)
        })

    # KPIs rápidos para o topo da tela
    todas_motos_kpi = Motorcycle.query.options(
        selectinload(Motorcycle.v5c_arquivos),
        selectinload(Motorcycle.contratos)
    ).all()
    kpi_total = len(todas_motos_kpi)
    kpi_operational = 0
    kpi_available = 0
    kpi_rented = 0
    kpi_maintenance = 0
    kpi_pound = 0
    kpi_sold = 0
    kpi_missing_v5c = 0
    kpi_awaiting_v5c = 0
    kpi_no_v5c_no_slip = 0
    kpi_tax_mot_warnings = 0

    for mk in todas_motos_kpi:
        st = (mk.status or '').lower()
        is_p = (st == 'pound')
        is_s = (st in ['sold', 'vendida'])
        has_active_contract = any(c.status in [ContractStatus.ACTIVE.value, 'Active', 'Ativo'] for c in (mk.contratos or []))
        
        if not is_p and (not is_s or has_active_contract):
            kpi_operational += 1

        if st in ['available', 'disponível']:
            kpi_available += 1
        elif st in ['rented', 'alugada']:
            kpi_rented += 1
        elif st in ['maintenance', 'manutenção']:
            kpi_maintenance += 1
        elif is_p:
            kpi_pound += 1
        elif is_s:
            kpi_sold += 1

        active_purchase = active_purchases_map.get(mk.placa)
        if active_purchase:
            docs_ciclo = get_purchase_contract_v5c_docs(active_purchase)
            has_v5c_official = any((getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'v5c' for v in docs_ciclo)
            has_transfer_slip = any((getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'transfer_proof' for v in docs_ciclo)
        else:
            has_v5c_official = any((getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'v5c' for v in (mk.v5c_arquivos or []))
            has_transfer_slip = any((getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'transfer_proof' for v in (mk.v5c_arquivos or []))

        if not has_v5c_official:
            kpi_missing_v5c += 1
            if has_transfer_slip:
                kpi_awaiting_v5c += 1
            else:
                kpi_no_v5c_no_slip += 1

        if not is_p:
            is_sorn = bool(getattr(mk, 'tax_sorn', False))
            has_w = False
            if not is_s and not is_sorn and mk.vencimento_tax:
                diff_t = (mk.vencimento_tax - hoje_date).days
                if diff_t <= 30:
                    has_w = True
            if mk.vencimento_mot:
                diff_m = (mk.vencimento_mot - hoje_date).days
                if diff_m <= 30:
                    has_w = True
            if has_w:
                kpi_tax_mot_warnings += 1
    
    return jsonify({
        'itens': itens,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page,
        'kpis': {
            'total': kpi_total,
            'operational': kpi_operational,
            'available': kpi_available,
            'rented': kpi_rented,
            'maintenance': kpi_maintenance,
            'pound': kpi_pound,
            'sold': kpi_sold,
            'missing_v5c': kpi_missing_v5c,
            'awaiting_v5c': kpi_awaiting_v5c,
            'no_v5c_no_slip': kpi_no_v5c_no_slip,
            'tax_mot_warnings': kpi_tax_mot_warnings
        }
    })

@app.route('/api/motos/export', methods=['GET'])
@alugueis_required
def export_motos_csv():
    import io
    import csv
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', '', type=str).strip()
    v5c_filter = request.args.get('v5c', '', type=str).strip().lower()

    query = Motorcycle.query.options(
        selectinload(Motorcycle.v5c_arquivos),
        selectinload(Motorcycle.trackers),
        selectinload(Motorcycle.contratos).selectinload(Contract.cliente)
    )

    hoje_date = datetime.now(pytz.timezone('Europe/London')).date()

    if status_filter:
        sf_lower = status_filter.lower()
        if sf_lower in ['operational', 'in_operation', 'operacao', 'ativa', 'ativas', 'active']:
            query = query.filter(
                ~Motorcycle.status.in_([MotoStatus.POUND.value, 'Pound']),
                db.or_(
                    ~Motorcycle.status.in_([MotoStatus.SOLD.value, 'Sold', 'Vendida']),
                    Motorcycle.contratos.any(Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']))
                )
            )
        elif sf_lower == 'sorn':
            query = query.filter(Motorcycle.tax_sorn == True)
        elif sf_lower in ['missing_v5c', 'no_v5c', 'sem_v5c']:
            query = query.filter(~Motorcycle.v5c_arquivos.any())
        elif sf_lower in ['warnings', 'tax_mot_warnings', 'alert', 'alerts']:
            trinta_dias = hoje_date + timedelta(days=30)
            query = query.filter(
                ~Motorcycle.status.in_([MotoStatus.POUND.value, 'Pound']),
                db.or_(
                    db.and_(
                        db.or_(
                            ~Motorcycle.status.in_([MotoStatus.SOLD.value, 'Sold', 'Vendida']),
                            Motorcycle.contratos.any(Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']))
                        ),
                        Motorcycle.tax_sorn == False,
                        Motorcycle.vencimento_tax <= trinta_dias
                    ),
                    Motorcycle.vencimento_mot <= trinta_dias
                )
            )
        elif sf_lower in ['all', 'todas', 'tudo']:
            pass
        else:
            query = query.filter(Motorcycle.status.ilike(status_filter))

    if v5c_filter in ['missing', 'none', 'sem', '0']:
        query = query.filter(~Motorcycle.v5c_arquivos.any())

    if search:
        search_clean = search.strip().replace(' ', '')
        search_term = f"%{search.strip()}%"
        search_plate_term = f"%{search_clean}%"
        search_filters = [
            Motorcycle.placa.ilike(search_plate_term),
            Motorcycle.placa.ilike(search_term),
            Motorcycle.modelo.ilike(search_term),
            Motorcycle.cor.ilike(search_term),
            Motorcycle.status.ilike(search_term)
        ]
        if search.strip().lower() == 'sorn':
            search_filters.append(Motorcycle.tax_sorn == True)
        elif search.strip().lower() in ['missing_v5c', 'missing v5c', 'no v5c', 'sem v5c']:
            search_filters.append(~Motorcycle.v5c_arquivos.any())
        query = query.filter(db.or_(*search_filters))

    motos = query.order_by(Motorcycle.placa.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Reg Plate', 'Model', 'Colour', 'Status', 'Mileage (Miles)',
        'Road Tax Expiry', 'SORN', 'MOT Expiry', 'V5C Documents Count',
        'GPS Trackers Count', 'Active Contract ID', 'Active Hirer Name',
        'Active Hirer Phone', 'Last Contract ID', 'Last Contract Type', 'Last Client Name'
    ])

    for m in motos:
        contratos_sorted = sorted(m.contratos, key=lambda x: x.id, reverse=True) if m.contratos else []
        active_c = next((c for c in contratos_sorted if c.status in [ContractStatus.ACTIVE.value, 'Active', 'Ativo', ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold']), None)
        last_c = contratos_sorted[0] if contratos_sorted else None

        active_id = active_c.id if active_c else ''
        active_nome = ((active_c.cliente.nome if active_c.cliente else active_c.cliente_nome) or '') if active_c else ''
        active_phone = ((active_c.cliente.telefone if active_c.cliente else active_c.cliente_telefone) or '') if active_c else ''

        last_id = last_c.id if last_c else ''
        last_tipo = last_c.tipo_contrato if last_c else ''
        last_nome = ((last_c.cliente.nome if last_c.cliente else last_c.cliente_nome) or '') if last_c else ''

        writer.writerow([
            m.placa,
            m.modelo,
            m.cor or '',
            m.status,
            int(m.milhagem_atual or 0),
            m.vencimento_tax.strftime('%d/%m/%Y') if m.vencimento_tax else '',
            'YES' if getattr(m, 'tax_sorn', False) else 'NO',
            m.vencimento_mot.strftime('%d/%m/%Y') if m.vencimento_mot else '',
            len(m.v5c_arquivos) if m.v5c_arquivos else 0,
            len(m.trackers) if m.trackers else 0,
            active_id,
            active_nome,
            active_phone,
            last_id,
            last_tipo,
            last_nome
        ])

    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename=fleet_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
    )

@app.route('/api/motos/<placa>', methods=['PUT'])
@alugueis_required
def atualizar_moto(placa):
    moto = db.session.get(Motorcycle, placa)
    if not moto:
        return jsonify({'error': 'Motorbike not found', 'erro': 'Moto não encontrada'}), 404
        
    dados = request.get_json() or {}
    status_antigo = moto.status
    modelo_antigo = moto.modelo
    cor_antiga = moto.cor
    milhas_antiga = moto.milhagem_atual
    mot_antigo = moto.vencimento_mot
    tax_antigo = moto.vencimento_tax
    sorn_antigo = bool(getattr(moto, 'tax_sorn', False))
    
    alteracoes = []

    if 'modelo' in dados and dados['modelo']:
        novo_modelo = str(dados['modelo']).strip()
        if novo_modelo != modelo_antigo:
            alteracoes.append(f"Modelo alterado de '{modelo_antigo}' para '{novo_modelo}'")
            moto.modelo = novo_modelo

    if 'cor' in dados and dados['cor']:
        nova_cor = str(dados['cor']).strip()
        if nova_cor != cor_antiga:
            alteracoes.append(f"Cor alterada de '{cor_antiga or 'N/A'}' para '{nova_cor}'")
            moto.cor = nova_cor

    if 'status' in dados and dados['status'] != status_antigo:
        alteracoes.append(f"Status alterado de '{status_antigo}' para '{dados['status']}'")
        moto.status = dados['status']

    if 'milhagem_atual' in dados and dados['milhagem_atual'] is not None:
        try:
            nova_milhagem = int(dados['milhagem_atual'])
            if nova_milhagem != milhas_antiga:
                alteracoes.append(f"Milhagem atualizada de {milhas_antiga or 0} para {nova_milhagem} mi")
                moto.milhagem_atual = nova_milhagem
        except (ValueError, TypeError):
            pass
    
    if 'vencimento_mot' in dados:
        if dados['vencimento_mot']:
            try:
                novo_mot = datetime.strptime(dados['vencimento_mot'], "%Y-%m-%d").date()
                if novo_mot != mot_antigo:
                    alteracoes.append(f"MOT atualizado para {novo_mot.strftime('%d/%m/%Y')}")
                    moto.vencimento_mot = novo_mot
            except ValueError:
                pass
        else:
            if mot_antigo is not None:
                alteracoes.append("MOT removido")
                moto.vencimento_mot = None
            
    if 'tax_sorn' in dados:
        novo_sorn = bool(dados['tax_sorn'])
        if novo_sorn != sorn_antigo:
            alteracoes.append("SORN ativado (Off Road)" if novo_sorn else "SORN desativado")
            moto.tax_sorn = novo_sorn
            if novo_sorn:
                moto.vencimento_tax = None

    if not getattr(moto, 'tax_sorn', False) and 'vencimento_tax' in dados:
        if dados['vencimento_tax']:
            try:
                novo_tax = datetime.strptime(dados['vencimento_tax'], "%Y-%m-%d").date()
                if novo_tax != tax_antigo:
                    alteracoes.append(f"Road Tax atualizado para {novo_tax.strftime('%d/%m/%Y')}")
                    moto.vencimento_tax = novo_tax
            except ValueError:
                pass
        else:
            if tax_antigo is not None:
                alteracoes.append("Road Tax removido")
                moto.vencimento_tax = None

    if 'notas_internas' in dados:
        notas_antigas = getattr(moto, 'notas_internas', None)
        novas_notas = str(dados['notas_internas']).strip() if (dados['notas_internas'] and str(dados['notas_internas']).strip()) else None
        if (novas_notas or '') != (notas_antigas or ''):
            alteracoes.append("Notas internas atualizadas")
            moto.notas_internas = novas_notas
    
    db.session.commit()
    
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    if 'status' in dados and dados['status'] != status_antigo and len(alteracoes) == 1:
        registrar_log('MOTO_STATUS_CHANGE', 'Motorcycle', placa, f"Status da moto {placa} alterado de '{status_antigo}' para '{dados['status']}' por {operador_atual}")
    elif alteracoes:
        registrar_log('MOTO_UPDATE', 'Motorcycle', placa, f"Moto {placa} atualizada por {operador_atual}: {', '.join(alteracoes)}")

    return jsonify({'message': 'Motorbike updated successfully', 'mensagem': 'Moto atualizada com sucesso'})

@app.route('/api/motos/<placa>/detalhes', methods=['GET'])
@alugueis_required
def detalhes_moto(placa):
    placa_clean = str(placa).strip().replace(' ', '').upper()
    moto = Motorcycle.query.options(
        selectinload(Motorcycle.v5c_arquivos),
        selectinload(Motorcycle.trackers)
    ).filter_by(placa=placa_clean).first()
    
    if not moto:
        return jsonify({'error': 'Motorbike not found', 'erro': 'Moto não encontrada'}), 404
        
    v5c_oficiais = [v for v in (moto.v5c_arquivos or []) if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'v5c']
    transfer_slips = [v for v in (moto.v5c_arquivos or []) if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'transfer_proof']

    return jsonify({
        'placa': moto.placa,
        'modelo': moto.modelo,
        'cor': moto.cor,
        'status': moto.status,
        'milhagem_atual': int(moto.milhagem_atual or 0),
        'vencimento_mot': moto.vencimento_mot.strftime('%Y-%m-%d') if moto.vencimento_mot else None,
        'vencimento_tax': moto.vencimento_tax.strftime('%Y-%m-%d') if moto.vencimento_tax else None,
        'tax_sorn': bool(getattr(moto, 'tax_sorn', False)),
        'notas_internas': moto.notas_internas,
        'v5c_count': len(v5c_oficiais),
        'transfer_proof_count': len(transfer_slips),
        'has_v5c': len(v5c_oficiais) > 0,
        'has_transfer_proof': len(transfer_slips) > 0,
        'v5c_arquivos': [{
            'id': v.id,
            'id_contrato': getattr(v, 'id_contrato', None),
            'url_arquivo': v.url_arquivo,
            'nome_original': v.nome_original or f"V5C_{moto.placa}",
            'tipo_arquivo': v.tipo_arquivo,
            'categoria_doc': getattr(v, 'categoria_doc', 'v5c') or 'v5c',
            'criado_por_nome': v.criado_por_nome or '',
            'data_criacao': v.data_criacao.strftime('%d/%m/%Y %H:%M') if v.data_criacao else None
        } for v in sorted(moto.v5c_arquivos, key=lambda x: x.id)],
        'trackers': [{
            'id': t.id,
            'numero': t.numero,
            'tipo_propriedade': t.tipo_propriedade,
            'observacoes': t.observacoes or '',
            'fotos': [f.strip() for f in (t.url_fotos or '').split(',') if f.strip()],
            'instalado_por_nome': t.instalado_por_nome or '',
            'data_instalacao': t.data_instalacao.strftime('%d/%m/%Y %H:%M') if t.data_instalacao else None
        } for t in sorted(moto.trackers, key=lambda x: x.id)]
    }), 200

@app.route('/api/motos/<placa>/v5c', methods=['POST'])
@alugueis_required
def upload_v5c_moto(placa):
    placa_clean = str(placa).strip().replace(' ', '').upper()
    moto = db.session.get(Motorcycle, placa_clean)
    if not moto:
        return jsonify({'error': 'Motorbike not found', 'erro': 'Moto não encontrada'}), 404
        
    arquivos = request.files.getlist('v5c_arquivos') or request.files.getlist('arquivos') or request.files.getlist('files')
    if not arquivos and 'arquivo' in request.files:
        arquivos = [request.files['arquivo']]
    elif not arquivos and 'file' in request.files:
        arquivos = [request.files['file']]
        
    if not arquivos:
        return jsonify({'error': 'No file uploaded', 'erro': 'Nenhum arquivo enviado'}), 400
        
    cat_raw = (request.form.get('categoria_doc') or request.args.get('categoria') or 'v5c').strip().lower()
    categoria_doc = 'transfer_proof' if ('transfer' in cat_raw or 'slip' in cat_raw or 'proof' in cat_raw) else 'v5c'

    id_contrato_param = request.form.get('id_contrato') or request.args.get('id_contrato')
    id_contrato = None
    if id_contrato_param:
        try:
            id_contrato = int(id_contrato_param)
        except (ValueError, TypeError):
            id_contrato = None
    if not id_contrato:
        # Se não informado, vincula automaticamente ao contrato de compra ativo mais recente desta moto
        active_purchase = Contract.query.filter(
            db.or_(Contract.placa == placa_clean, Contract.moto_placa == placa_clean),
            Contract.tipo_contrato.in_([ContractType.PURCHASE.value, 'Purchase', 'Compra']),
            Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo'])
        ).order_by(Contract.id.desc()).first()
        if active_purchase:
            id_contrato = active_purchase.id

    salvos = []
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    
    for f in arquivos:
        if not f or not f.filename:
            continue
        if not is_allowed_file(f.filename):
            return jsonify({'error': f'Invalid file format: {f.filename}. Only JPG, PNG, WEBP and PDF are allowed.', 'erro': 'Formato inválido'}), 400
            
        ext = f.filename.rsplit('.', 1)[1].lower() if '.' in f.filename else ''
        tipo_arq = 'pdf' if ext == 'pdf' else 'image'
        safe_orig = werkzeug.utils.secure_filename(f.filename) or f"{categoria_doc}_{placa_clean}.{ext}"
        prefixo = "transfer_slip" if categoria_doc == 'transfer_proof' else "v5c"
        nome_final = f"{int(get_local_now().timestamp())}_{prefixo}_{placa_clean}_{safe_orig}"
        
        if tipo_arq == 'pdf':
            caminho = os.path.join(app.config['UPLOAD_FOLDER'], nome_final)
            f.save(caminho)
            url_arquivo = f"/static/uploads/{nome_final}"
        else:
            nome_salvo = salvar_arquivo_otimizado(f, nome_final)
            url_arquivo = f"/static/uploads/{nome_salvo}"
            
        v5c_rec = MotorcycleV5C(
            placa=moto.placa,
            id_contrato=id_contrato,
            url_arquivo=url_arquivo,
            nome_original=safe_orig,
            tipo_arquivo=tipo_arq,
            categoria_doc=categoria_doc,
            criado_por_nome=operador_atual
        )
        db.session.add(v5c_rec)
        salvos.append(v5c_rec)
        
    if not salvos:
        return jsonify({'error': 'No valid files processed', 'erro': 'Nenhum arquivo válido processado'}), 400
        
    db.session.commit()
    
    tipo_desc = "comprovante(s) de transferência" if categoria_doc == 'transfer_proof' else "arquivo(s) de V5C"
    log_action = 'MOTO_TRANSFER_PROOF_UPLOADED' if categoria_doc == 'transfer_proof' else 'MOTO_V5C_UPLOADED'
    registrar_log(log_action, 'Motorcycle', moto.placa, f"{len(salvos)} {tipo_desc} anexados à moto {moto.placa} por {operador_atual}")
    
    # Sincroniza status de contratos de compra da moto somente se foi anexado o V5C oficial
    if categoria_doc == 'v5c':
        if id_contrato:
            contrato_alvo = db.session.get(Contract, id_contrato)
            if contrato_alvo:
                sync_purchase_contract_status(contrato_alvo, auto_commit=True)
        else:
            contratos_compra = Contract.query.filter(
                Contract.tipo_contrato.in_([ContractType.PURCHASE.value, 'Purchase', 'Compra']),
                db.or_(Contract.placa == moto.placa, Contract.moto_placa == moto.placa)
            ).all()
            for cc in contratos_compra:
                sync_purchase_contract_status(cc, auto_commit=True)
    
    label_resp = "Transfer proof" if categoria_doc == 'transfer_proof' else "V5C"
    return jsonify({
        'message': f'{len(salvos)} {label_resp} document(s) attached successfully',
        'mensagem': f'{len(salvos)} {tipo_desc} anexado(s) com sucesso',
        'categoria_doc': categoria_doc,
        'id_contrato': id_contrato,
        'v5c_arquivos': [{
            'id': v.id,
            'id_contrato': getattr(v, 'id_contrato', None),
            'url_arquivo': v.url_arquivo,
            'nome_original': v.nome_original,
            'tipo_arquivo': v.tipo_arquivo,
            'categoria_doc': v.categoria_doc,
            'data_criacao': v.data_criacao.strftime('%d/%m/%Y %H:%M')
        } for v in salvos]
    }), 201

@app.route('/api/motos/<placa>/v5c/<int:v5c_id>', methods=['DELETE'])
@alugueis_required
def remover_v5c_moto(placa, v5c_id):
    placa_clean = str(placa).strip().replace(' ', '').upper()
    v5c = db.session.get(MotorcycleV5C, v5c_id)
    if not v5c or v5c.placa != placa_clean:
        return jsonify({'error': 'Document record not found', 'erro': 'Registro de documento não encontrado'}), 404
        
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    nome_orig = v5c.nome_original or str(v5c.id)
    is_official_v5c = (getattr(v5c, 'categoria_doc', 'v5c') == 'v5c')
    tipo_desc = "Documento V5C" if is_official_v5c else "Comprovante de Transferência"
    
    try:
        if v5c.url_arquivo:
            clean_name = os.path.basename(v5c.url_arquivo)
            disk_path = os.path.join(app.config['UPLOAD_FOLDER'], clean_name)
            if os.path.exists(disk_path):
                os.remove(disk_path)
    except Exception as e:
        app.logger.warning(f"Failed to delete physical file {v5c.url_arquivo}: {e}")
        
    db.session.delete(v5c)
    db.session.commit()
    registrar_log('MOTO_V5C_DELETED', 'Motorcycle', placa_clean, f"{tipo_desc} ({nome_orig}) da moto {placa_clean} excluído por {operador_atual}")
    
    # Se era V5C oficial, sincroniza status de contratos de compra da moto (reabre para Active se não possui mais V5C oficial)
    if is_official_v5c:
        contratos_compra = Contract.query.filter(
            Contract.tipo_contrato.in_([ContractType.PURCHASE.value, 'Purchase', 'Compra']),
            db.or_(Contract.placa == placa_clean, Contract.moto_placa == placa_clean)
        ).all()
        for cc in contratos_compra:
            sync_purchase_contract_status(cc, auto_commit=True)
    
    return jsonify({'message': f'{tipo_desc} deleted successfully', 'mensagem': f'{tipo_desc} excluído com sucesso'}), 200

@app.route('/api/motos/<placa>/trackers', methods=['POST'])
@alugueis_required
def adicionar_tracker_moto(placa):
    placa_clean = str(placa).strip().replace(' ', '').upper()
    moto = db.session.get(Motorcycle, placa_clean)
    if not moto:
        return jsonify({'error': 'Motorbike not found', 'erro': 'Moto não encontrada'}), 404
        
    numero = request.form.get('numero', '').strip()
    if not numero and request.is_json:
        numero = request.json.get('numero', '').strip()
        
    if not numero:
        return jsonify({'error': 'Tracker number / serial is required', 'erro': 'O número/serial do tracker é obrigatório'}), 400

    numero_clean = str(numero).strip()
    tracker_existente = MotorcycleTracker.query.filter(
        db.func.lower(MotorcycleTracker.numero) == numero_clean.lower()
    ).first()
    if tracker_existente:
        if tracker_existente.placa == moto.placa:
            return jsonify({
                'error': f"Tracker '{numero_clean}' is already registered on this motorbike ({moto.placa}).",
                'erro': f"Este tracker ({numero_clean}) já está cadastrado nesta moto ({moto.placa})."
            }), 400
        else:
            return jsonify({
                'error': f"Tracker '{numero_clean}' is already registered on motorbike {tracker_existente.placa}. Remove it from {tracker_existente.placa} first before reassigning.",
                'erro': f"Este tracker ({numero_clean}) já está cadastrado na moto {tracker_existente.placa}. Remova-o da moto {tracker_existente.placa} primeiro para vinculá-lo a outro veículo."
            }), 400
        
    tipo_propriedade = request.form.get('tipo_propriedade', 'Company').strip()
    if not tipo_propriedade and request.is_json:
        tipo_propriedade = request.json.get('tipo_propriedade', 'Company').strip()
    if tipo_propriedade not in ['Company', 'Customer']:
        tipo_propriedade = 'Company'
        
    observacoes = request.form.get('observacoes', '').strip()
    if not observacoes and request.is_json:
        observacoes = request.json.get('observacoes', '').strip()
        
    fotos_urls = []
    fotos = request.files.getlist('fotos') or request.files.getlist('fotos[]')
    if not fotos and 'foto' in request.files:
        fotos = [request.files['foto']]
        
    for f in fotos:
        if f and f.filename and is_allowed_file(f.filename):
            safe_orig = werkzeug.utils.secure_filename(f.filename) or 'tracker.jpg'
            nome_final = f"{int(get_local_now().timestamp())}_tracker_{placa_clean}_{safe_orig}"
            nome_salvo = salvar_arquivo_otimizado(f, nome_final)
            fotos_urls.append(f"/static/uploads/{nome_salvo}")
            
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    novo_tracker = MotorcycleTracker(
        placa=moto.placa,
        numero=numero,
        tipo_propriedade=tipo_propriedade,
        observacoes=observacoes or None,
        url_fotos=",".join(fotos_urls) if fotos_urls else None,
        instalado_por_nome=operador_atual
    )
    db.session.add(novo_tracker)
    db.session.commit()
    
    label_prop = "Nosso (Company)" if tipo_propriedade == 'Company' else "Do Cliente (Customer)"
    registrar_log('MOTO_TRACKER_ADDED', 'Motorcycle', moto.placa, f"Tracker #{numero} ({label_prop}) instalado na moto {moto.placa} por {operador_atual} com {len(fotos_urls)} foto(s)")
    
    return jsonify({
        'message': 'Tracker added successfully',
        'mensagem': 'Tracker cadastrado com sucesso',
        'tracker': {
            'id': novo_tracker.id,
            'numero': novo_tracker.numero,
            'tipo_propriedade': novo_tracker.tipo_propriedade,
            'observacoes': novo_tracker.observacoes or '',
            'fotos': fotos_urls,
            'instalado_por_nome': novo_tracker.instalado_por_nome or '',
            'data_instalacao': novo_tracker.data_instalacao.strftime('%d/%m/%Y %H:%M')
        }
    }), 201

@app.route('/api/motos/<placa>/trackers/<int:tracker_id>', methods=['DELETE'])
@alugueis_required
def remover_tracker_moto(placa, tracker_id):
    placa_clean = str(placa).strip().replace(' ', '').upper()
    tracker = db.session.get(MotorcycleTracker, tracker_id)
    if not tracker or tracker.placa != placa_clean:
        return jsonify({'error': 'Tracker not found', 'erro': 'Tracker não encontrado'}), 404
        
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    num_tracker = tracker.numero
    prop_tracker = tracker.tipo_propriedade
    
    if tracker.url_fotos:
        for u in tracker.url_fotos.split(','):
            u_clean = u.strip()
            if u_clean:
                try:
                    fpath = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(u_clean))
                    if os.path.exists(fpath):
                        os.remove(fpath)
                except Exception as e:
                    app.logger.warning(f"Failed to remove tracker photo {u_clean}: {e}")
                    
    db.session.delete(tracker)
    db.session.commit()
    registrar_log('MOTO_TRACKER_REMOVED', 'Motorcycle', placa_clean, f"Tracker #{num_tracker} ({prop_tracker}) removido da moto {placa_clean} por {operador_atual}")
    
    return jsonify({'message': 'Tracker removed successfully', 'mensagem': 'Tracker removido com sucesso'}), 200

def sync_sale_contract_status(contrato_id_or_obj, auto_commit=False):
    """
    Sincroniza dinamicamente o status de contratos de venda (Sale_Full / Sale_Installment):
    - Se houver qualquer cobrança com status Pendente: reabre o contrato para 'Active' se estava 'Completed'.
    - Se todas as cobranças estiverem quitadas (zero pendentes e pelo menos uma paga): conclui para 'Completed'.
    - Respeita contratos com status 'Cancelled'.
    Retorna True se houve alteração no status do contrato.
    """
    if not contrato_id_or_obj:
        return False
        
    contrato = db.session.get(Contract, contrato_id_or_obj) if isinstance(contrato_id_or_obj, int) else contrato_id_or_obj
    if not contrato:
        return False
        
    tipo = getattr(contrato, 'tipo_contrato', '') or ''
    is_venda = tipo in [ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value, 'Sale_Full', 'Sale_Installment']
    if not is_venda:
        return False
        
    if contrato.status in [ContractStatus.CANCELLED.value, 'Cancelled', 'Cancelado']:
        return False
        
    transacoes = FinancialTransaction.query.filter_by(id_contrato=contrato.id).all()
    transacoes_cobrancas = [t for t in transacoes if t.tipo not in [TransactionType.DEPOSIT_REFUND.value, 'Deposit_Refund', 'Devolucao_Deposito']]
    
    if not transacoes_cobrancas:
        return False
        
    tem_pendente = any(t.status in [TransactionStatus.PENDING.value, 'Pending', 'Pendente'] for t in transacoes_cobrancas)
    todas_pagas = all(t.status in [TransactionStatus.PAID.value, 'Paid', 'Pago'] for t in transacoes_cobrancas)
    
    alterou = False
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    
    if tem_pendente:
        if contrato.status in [ContractStatus.COMPLETED.value, 'Completed', 'Finalizado']:
            contrato.status = ContractStatus.ATIVO.value
            registrar_log(
                'CONTRACT_REOPENED', 
                'Contract', 
                contrato.id, 
                f"Contrato de venda #{contrato.id} ({contrato.tipo_contrato}) reaberto para Active devido a cobrança(s) pendente(s) (Operador: {operador_atual})."
            )
            alterou = True
    elif todas_pagas:
        if contrato.status != ContractStatus.COMPLETED.value:
            contrato.status = ContractStatus.COMPLETED.value
            registrar_log(
                'CONTRACT_COMPLETED', 
                'Contract', 
                contrato.id, 
                f"Contrato de venda #{contrato.id} ({contrato.tipo_contrato}) concluído com sucesso após quitação integral de todas as cobranças (Operador: {operador_atual})."
            )
            alterou = True
            
    if alterou and auto_commit:
        db.session.commit()
        
    return alterou

def get_purchase_contract_v5c_docs(contrato):
    """
    Retorna os documentos de V5C/Transferência válidos para o ciclo de um contrato de compra específico.
    Resolve recompras de uma mesma moto:
    - Prioridade 1: Documentos explicitamente vinculados a este contrato (id_contrato == contrato.id).
    - Prioridade 2: Documentos da moto criados no ciclo temporal desta compra (após contratos anteriores não cancelados).
    Documentos de compras anteriores concluídas pertencem ao histórico passado e nunca são reaproveitados para a recompra atual.
    """
    if not contrato:
        return []
        
    placa_alvo = (contrato.moto_placa or contrato.placa or '').strip().upper()
    if not placa_alvo:
        return []
        
    # 1. Documentos explicitamente vinculados a este contrato
    docs_diretos = MotorcycleV5C.query.filter_by(placa=placa_alvo, id_contrato=contrato.id).order_by(MotorcycleV5C.id.asc()).all()
    
    # 2. Busca contrato anterior não cancelado desta moto
    prev_contract = Contract.query.filter(
        db.or_(Contract.placa == placa_alvo, Contract.moto_placa == placa_alvo),
        Contract.id < contrato.id,
        Contract.status.notin_([ContractStatus.CANCELLED.value, 'Cancelled', 'Cancelado'])
    ).order_by(Contract.id.desc()).first()
    
    # Busca contrato posterior não cancelado desta moto (marca o fim do ciclo deste contrato)
    next_contract = Contract.query.filter(
        db.or_(Contract.placa == placa_alvo, Contract.moto_placa == placa_alvo),
        Contract.id > contrato.id,
        Contract.status.notin_([ContractStatus.CANCELLED.value, 'Cancelled', 'Cancelado'])
    ).order_by(Contract.id.asc()).first()
    
    q_ciclo = MotorcycleV5C.query.filter(
        MotorcycleV5C.placa == placa_alvo,
        db.or_(MotorcycleV5C.id_contrato == None, MotorcycleV5C.id_contrato == contrato.id)
    )
    
    if prev_contract and prev_contract.data_retirada:
        cutoff_inicio = prev_contract.data_devolucao or prev_contract.data_retirada
        q_ciclo = q_ciclo.filter(MotorcycleV5C.data_criacao >= cutoff_inicio)
        
    if next_contract and next_contract.data_retirada:
        cutoff_fim = next_contract.data_retirada
        q_ciclo = q_ciclo.filter(MotorcycleV5C.data_criacao < cutoff_fim)
        
    docs_temporais = q_ciclo.order_by(MotorcycleV5C.id.asc()).all()
    
    vistos = set()
    resultado = []
    for d in (docs_diretos + docs_temporais):
        if d.id not in vistos:
            vistos.add(d.id)
            resultado.append(d)
            
    return resultado

def sync_purchase_contract_status(contrato_id_or_obj, auto_commit=False):
    """
    Sincroniza dinamicamente o status de contratos de compra (Purchase):
    - Um contrato de compra finaliza ('Completed') quando:
      1. Está assinado pelo vendedor (assinatura_cliente_inicial presente).
      2. O documento de Logbook (V5C) do veículo para este ciclo de compra está anexado no sistema (MotorcycleV5C).
    - Enquanto não possuir o Logbook (V5C) anexado, permanece 'Active' exibindo alerta.
    - Se o V5C for excluído (e não houver contratos posteriores), reabre o contrato para 'Active'.
    - Imunidade histórica: Contratos finalizados no passado com contratos posteriores NUNCA são reabertos!
    - Respeita contratos com status 'Cancelled'.
    Retorna True se houve alteração no status do contrato.
    """
    if not contrato_id_or_obj:
        return False
        
    contrato = db.session.get(Contract, contrato_id_or_obj) if isinstance(contrato_id_or_obj, int) else contrato_id_or_obj
    if not contrato:
        return False
        
    tipo = getattr(contrato, 'tipo_contrato', '') or ''
    is_purchase = tipo in [ContractType.PURCHASE.value, 'Purchase', 'Compra']
    if not is_purchase:
        return False
        
    if contrato.status in [ContractStatus.CANCELLED.value, 'Cancelled', 'Cancelado']:
        return False
        
    placa_alvo = (contrato.moto_placa or contrato.placa or '').strip().upper()
    if not placa_alvo:
        return False

    # Verifica se existem contratos posteriores não cancelados para esta mesma moto
    has_subsequent_contracts = Contract.query.filter(
        db.or_(Contract.placa == placa_alvo, Contract.moto_placa == placa_alvo),
        Contract.id > contrato.id,
        Contract.status.notin_([ContractStatus.CANCELLED.value, 'Cancelled', 'Cancelado'])
    ).count() > 0

    # Imunidade Histórica: contrato de compra finalizado no passado que já possui contratos posteriores
    # NUNCA pode ser reaberto por alterações ou exclusões de ciclos futuros!
    if has_subsequent_contracts and contrato.status in [ContractStatus.COMPLETED.value, 'Completed', 'Finalizado']:
        return False

    docs_ciclo = get_purchase_contract_v5c_docs(contrato)
    v5c_oficiais = [d for d in docs_ciclo if getattr(d, 'categoria_doc', 'v5c') == 'v5c']
    tem_v5c = (len(v5c_oficiais) > 0)
    tem_assinatura = bool(contrato.assinatura_cliente_inicial)
    
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    alterou = False
    
    if tem_assinatura and tem_v5c:
        if contrato.status != ContractStatus.COMPLETED.value:
            contrato.status = ContractStatus.COMPLETED.value
            registrar_log(
                'CONTRACT_COMPLETED',
                'Contract',
                contrato.id,
                f"Contrato de compra #{contrato.id} ({placa_alvo}) concluído com sucesso após anexo do Logbook (V5C) e assinatura do vendedor (Operador: {operador_atual})."
            )
            alterou = True
    else:
        # Só pode reabrir se NÃO houver contratos posteriores
        if not has_subsequent_contracts and contrato.status in [ContractStatus.COMPLETED.value, 'Completed', 'Finalizado']:
            contrato.status = ContractStatus.ACTIVE.value
            motivo = "ausência do documento de Logbook (V5C)" if not tem_v5c else "ausência de assinatura do vendedor"
            registrar_log(
                'CONTRACT_REOPENED',
                'Contract',
                contrato.id,
                f"Contrato de compra #{contrato.id} ({placa_alvo}) reaberto para Active por {motivo} (Operador: {operador_atual})."
            )
            alterou = True
            
    if alterou and auto_commit:
        db.session.commit()
        
    return alterou

@app.route('/api/contratos', methods=['POST'])
@alugueis_required
def criar_contrato():
    id_cliente = request.form.get('id_cliente') or request.form.get('cliente_id')
    placa = request.form.get('placa') or request.form.get('moto_placa')
    tipo_contrato = request.form.get('tipo_contrato', ContractType.RENT.value)
    if tipo_contrato not in [ContractType.RENT.value, ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value, ContractType.PURCHASE.value]:
        tipo_contrato = ContractType.RENT.value

    dia_pagamento_semanal = int(request.form.get('dia_pagamento_semanal', 0)) if request.form.get('dia_pagamento_semanal') else 0
    valor_aluguel_semanal = float(request.form.get('valor_aluguel_semanal', 250.0)) if request.form.get('valor_aluguel_semanal') else 0.0
    valor_deposito = float(request.form.get('valor_deposito', 0.0)) if request.form.get('valor_deposito') else 0.0
    observacoes = request.form.get('observacoes')
    notas_internas_req = request.form.get('notas_internas')
    if notas_internas_req is None and request.is_json:
        notas_internas_req = (request.get_json() or {}).get('notas_internas')
    notas_internas_contrato_clean = str(notas_internas_req).strip() if (notas_internas_req and str(notas_internas_req).strip()) else None
    
    # Specific Sale & Purchase Fields
    categoria_historico = request.form.get('categoria_historico', 'Clear')
    valor_venda_veiculo = float(request.form.get('valor_venda_veiculo') or 0.0) if request.form.get('valor_venda_veiculo') else None
    acessorios_extras = (request.form.get('acessorios_extras') or '').strip() or 'None'
    valor_total_extras = float(request.form.get('valor_total_extras') or 0.0)
    valor_admin_fee = float(request.form.get('valor_admin_fee') or 0.0)
    valor_total_venda = float(request.form.get('valor_total_venda') or 0.0) if request.form.get('valor_total_venda') else None
    valor_entrada = float(request.form.get('valor_entrada') or 0.0)
    saldo_devedor = float(request.form.get('saldo_devedor') or 0.0)
    cronograma_parcelas_raw = request.form.get('cronograma_parcelas', '[]')
    
    # Specific Purchase Agreement Fields
    valor_compra_veiculo = float(request.form.get('valor_compra_veiculo') or 0.0) if request.form.get('valor_compra_veiculo') else None
    metodo_pagamento_compra = (request.form.get('metodo_pagamento_compra') or '').strip() or None
    detalhes_pagamento_compra = (request.form.get('detalhes_pagamento_compra') or '').strip() or None
    milhagem_nao_verificada = request.form.get('milhagem_nao_verificada') in ['1', 'true', 'True', True]
    status_moto_destino = request.form.get('status_moto_destino') or MotoStatus.AVAILABLE.value
    if status_moto_destino not in [MotoStatus.AVAILABLE.value, MotoStatus.MANUTENCAO.value, MotoStatus.POUND.value, 'Pound']:
        status_moto_destino = MotoStatus.AVAILABLE.value

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
    
    fotos = request.files.getlist('fotos') if 'fotos' in request.files else []
    # Filter empty file objects
    fotos = [f for f in fotos if f and f.filename]

    # Security: Validate upload file extensions for photos and insurance if provided
    for f in fotos:
        if f.filename and not is_allowed_file(f.filename):
            return jsonify({'error': 'Invalid inspection photo format. Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': 'Formato de foto inválido. Permitido apenas JPG, PNG, WEBP e PDF.'}), 400
            
    arq_seguro_check = request.files.get('seguro')
    if arq_seguro_check and arq_seguro_check.filename and not is_allowed_file(arq_seguro_check.filename):
        return jsonify({'error': 'Invalid insurance document format. Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': 'Formato de documento de seguro inválido. Permitido apenas JPG, PNG, WEBP e PDF.'}), 400

    cliente = db.session.get(Client, id_cliente)
    if not cliente:
        return jsonify({'error': 'Customer not found', 'erro': 'Cliente não encontrado'}), 400

    moto = db.session.get(Motorcycle, placa)
    if not moto:
        return jsonify({'error': 'Motorbike not found', 'erro': 'Moto não encontrada'}), 400
    if tipo_contrato != ContractType.PURCHASE.value and moto.status not in [MotoStatus.AVAILABLE.value, 'Disponível']:
        return jsonify({'error': 'Motorbike is not available', 'erro': 'Moto não está disponível'}), 400

    # Atualizar cor da moto se informada no formulário de compra/contrato
    cor_informada = (request.form.get('moto_cor') or '').strip()
    if cor_informada:
        moto.cor = cor_informada
        
    # Save inspection photos
    urls_fotos = []
    timestamp = get_local_now().strftime("%Y%m%d%H%M%S")
    for i, foto in enumerate(fotos):
        if foto and foto.filename:
            filename = werkzeug.utils.secure_filename(foto.filename)
            nome_arquivo = f"{timestamp}_{i}_{filename}"
            nome_salvo = salvar_arquivo_otimizado(foto, nome_arquivo)
            urls_fotos.append(f"/static/uploads/{nome_salvo}")
            
    url_foto_str = ",".join(urls_fotos)
    
    # Save insurance document if provided
    url_seguro = None
    arq_seguro = request.files.get('seguro')
    if arq_seguro and arq_seguro.filename:
        filename_seguro = werkzeug.utils.secure_filename(arq_seguro.filename)
        nome_seguro = f"{timestamp}_seguro_{filename_seguro}"
        nome_salvo = salvar_arquivo_otimizado(arq_seguro, nome_seguro)
        url_seguro = f"/static/uploads/{nome_salvo}"

    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'

    # Milhagem Inicial (UK Miles)
    if milhagem_nao_verificada and tipo_contrato == ContractType.PURCHASE.value:
        milhagem_inicial = 0
    else:
        milhagem_inicial = int(request.form.get('milhagem_inicial') or (moto.milhagem_atual or 0))
    moto.milhagem_atual = milhagem_inicial

    # Create Contract with frozen immutable snapshots
    novo_contrato = Contract(
        id_cliente=id_cliente,
        placa=placa,
        tipo_contrato=tipo_contrato,
        dia_pagamento_semanal=dia_pagamento_semanal if tipo_contrato == ContractType.RENT.value else None,
        valor_aluguel_semanal=valor_aluguel_semanal if tipo_contrato == ContractType.RENT.value else 0.0,
        valor_deposito=valor_deposito if tipo_contrato == ContractType.RENT.value else valor_entrada,
        categoria_historico=categoria_historico if tipo_contrato != ContractType.RENT.value else None,
        valor_venda_veiculo=valor_venda_veiculo,
        acessorios_extras=acessorios_extras if tipo_contrato in [ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value] else None,
        valor_admin_fee=valor_admin_fee if tipo_contrato == ContractType.SALE_INSTALLMENT.value else 0.0,
        valor_total_venda=valor_total_venda,
        valor_entrada=valor_entrada if tipo_contrato == ContractType.SALE_INSTALLMENT.value else 0.0,
        saldo_devedor=saldo_devedor if tipo_contrato == ContractType.SALE_INSTALLMENT.value else 0.0,
        cronograma_parcelas_json=json.dumps(cronograma_parcelas) if (tipo_contrato == ContractType.SALE_INSTALLMENT.value and cronograma_parcelas) else None,
        valor_compra_veiculo=valor_compra_veiculo if tipo_contrato == ContractType.PURCHASE.value else None,
        metodo_pagamento_compra=metodo_pagamento_compra if tipo_contrato == ContractType.PURCHASE.value else None,
        detalhes_pagamento_compra=detalhes_pagamento_compra if tipo_contrato == ContractType.PURCHASE.value else None,
        milhagem_nao_verificada=milhagem_nao_verificada if tipo_contrato == ContractType.PURCHASE.value else False,
        status_moto_destino=status_moto_destino if tipo_contrato == ContractType.PURCHASE.value else None,
        url_seguro=url_seguro,
        status=ContractStatus.ACTIVE.value,
        criado_por_nome=operador_atual,
        milhagem_inicial=milhagem_inicial,
        data_ultima_checagem_seguro=get_local_now().date() if url_seguro else None,
        status_seguro='Valid' if (url_seguro or tipo_contrato == ContractType.PURCHASE.value) else 'Pending',
        seguro_verificado_por=operador_atual if url_seguro else None,
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
        moto_placa=moto.placa,
        dia_pagamento_semanal_original=dia_pagamento_semanal if tipo_contrato == ContractType.RENT.value else None,
        notas_internas=notas_internas_contrato_clean
    )
    db.session.add(novo_contrato)
    
    # Update motorbike status according to contract type
    if tipo_contrato in [ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value]:
        moto.status = MotoStatus.SOLD.value
    elif tipo_contrato == ContractType.PURCHASE.value:
        moto.status = status_moto_destino
    else:
        moto.status = MotoStatus.RENTED.value
    
    db.session.flush() # Retrieve generated contract ID
    
    hoje = get_local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Financial Transactions Provisioning (All transactions start PENDING upon contract creation)
    # NOTA REGRA A1: Contratos de compra NÃO lançam no financeiro (não é recebível, a loja paga ao vendedor).
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
        proximo_vencimento = (hoje + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
        
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
                data_vencimento=p_venc.replace(hour=0, minute=0, second=0, microsecond=0),
                valor=p_valor,
                status=TransactionStatus.PENDING.value
            )
            db.session.add(tx_parcela)
    
    # Create Inspection with mileage only if photos were provided
    if urls_fotos:
        tipo_vistoria = InspectionType.CHECK_IN.value if tipo_contrato == ContractType.PURCHASE.value else InspectionType.CHECK_OUT.value
        nova_vistoria = Inspection(
            id_contrato=novo_contrato.id,
            tipo=tipo_vistoria,
            milhagem=milhagem_inicial,
            observacoes=observacoes,
            url_fotos=url_foto_str,
            realizado_por_nome=operador_atual
        )
        db.session.add(nova_vistoria)
    
    db.session.commit()
    
    insp_obs = " (Vistoria de saída realizada)" if urls_fotos else " (Aguardando vistoria de saída antes da liberação)"
    seg_obs = " (Seguro anexado)" if url_seguro else " (Aguardando apólice de seguro antes da liberação)"

    if tipo_contrato == ContractType.RENT.value:
        detalhes_log = f"Contrato de Aluguel #{novo_contrato.id} aberto para moto {moto.placa} por {operador_atual} (Milhagem: {milhagem_inicial} mi, Aluguel: £{valor_aluguel_semanal:.2f}/sem, Depósito: £{valor_deposito:.2f}){insp_obs}{seg_obs}"
    elif tipo_contrato == ContractType.SALE_FULL.value:
        detalhes_log = f"Contrato de Venda à Vista #{novo_contrato.id} aberto para moto {moto.placa} por {operador_atual} (Preço: £{valor_total_venda:.2f}, Categoria: {categoria_historico}). Moto marcada como Vendida (Sold).{insp_obs}{seg_obs}"
    elif tipo_contrato == ContractType.PURCHASE.value:
        detalhes_log = f"Contrato de Compra de Veículo #{novo_contrato.id} aberto para moto {moto.placa} por {operador_atual} (Valor: £{valor_compra_veiculo or 0:.2f}, Método: {metodo_pagamento_compra or 'N/A'}, Categoria: {categoria_historico}). Moto integrada à frota com status {status_moto_destino}."
    else:
        detalhes_log = f"Contrato de Venda Parcelada #{novo_contrato.id} aberto para moto {moto.placa} por {operador_atual} (Total: £{valor_total_venda:.2f}, Entrada: £{valor_entrada:.2f}, Saldo: £{saldo_devedor:.2f}, {len(cronograma_parcelas)} parcelas, Categoria: {categoria_historico}). Moto marcada como Vendida (Sold).{insp_obs}{seg_obs}"

    registrar_log('CREATE_CONTRACT', 'Contract', novo_contrato.id, detalhes_log)
    
    return jsonify({
        'message': 'Contract registered successfully', 
        'mensagem': 'Contrato registrado com sucesso', 
        'id': novo_contrato.id,
        'tipo_contrato': tipo_contrato,
        'has_inspection': bool(urls_fotos),
        'has_insurance': bool(url_seguro)
    }), 201

@app.route('/api/contratos/<int:id>/seguro', methods=['PUT'])
@alugueis_required
def atualizar_seguro_contrato(id):
    contrato = db.session.get(Contract, id)
    if not contrato:
        return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404
        
    file_key = 'seguro' if 'seguro' in request.files else ('arquivo' if 'arquivo' in request.files else None)
    if file_key:
        f = request.files[file_key]
        if f.filename:
            if not is_allowed_file(f.filename):
                return jsonify({'error': 'Invalid file format. Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': 'Formato de arquivo inválido.'}), 400
            nome_arq = werkzeug.utils.secure_filename(f"{int(get_local_now().timestamp())}_seguro_upd_{f.filename}")
            nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
            contrato.url_seguro = f"/static/uploads/{nome_salvo}"
            db.session.commit()
            operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
            cliente_nome = (contrato.cliente.nome if contrato.cliente else contrato.cliente_nome) or 'Cliente'
            placa = contrato.placa or contrato.moto_placa or 'N/A'
            registrar_log('INSURANCE_UPLOADED', 'Contract', contrato.id, f"Apólice de seguro do Contrato #{contrato.id} (Placa: {placa}, Cliente: {cliente_nome}) atualizada por {operador_atual}.")
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
    tipo_assinatura = str(dados.get('tipo', 'inicial')).strip().lower()
    if tipo_assinatura not in ['inicial', 'devolucao']:
        tipo_assinatura = 'inicial'
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
        upload_folder_abs = os.path.abspath(app.config['UPLOAD_FOLDER'])
        filepath = os.path.abspath(os.path.join(upload_folder_abs, filename))
        if not filepath.startswith(upload_folder_abs + os.sep):
            return jsonify({'error': 'Invalid file target path', 'erro': 'Caminho de gravação inválido'}), 400
        
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
            if contrato.tipo_contrato in [ContractType.PURCHASE.value, 'Purchase', 'Compra']:
                sync_purchase_contract_status(contrato)

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

@app.route('/api/contratos/<int:id>/dia-pagamento', methods=['PUT', 'POST'])
@alugueis_required
def alterar_dia_pagamento_contrato(id):
    """
    Altera o dia da semana de cobrança de contratos de aluguel ativos (0=Monday a 6=Sunday).
    Opcionalmente ajusta a data de vencimento de cobranças pendentes de aluguel.
    """
    contrato = db.session.get(Contract, id)
    if not contrato:
        return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404

    # Validar se o contrato é ativo
    if contrato.status not in [ContractStatus.ACTIVE.value, 'Active', 'Ativo']:
        return jsonify({
            'error': 'Payment due day can only be changed for active contracts',
            'erro': 'O dia de pagamento semanal só pode ser alterado para contratos ativos'
        }), 400

    # Validar se é contrato de aluguel
    tipo_contrato = getattr(contrato, 'tipo_contrato', 'Rent') or 'Rent'
    if tipo_contrato not in [ContractType.RENT.value, 'Rent', 'Aluguel']:
        return jsonify({
            'error': 'Weekly payment day only applies to rental contracts',
            'erro': 'O dia de pagamento semanal se aplica apenas a contratos de aluguel'
        }), 400

    data = request.get_json(silent=True) or request.form
    novo_dia_raw = data.get('dia_pagamento_semanal')
    if novo_dia_raw is None or str(novo_dia_raw).strip() == '':
        return jsonify({'error': 'Weekly payment due day is required', 'erro': 'O dia de pagamento semanal é obrigatório'}), 400

    try:
        novo_dia = int(novo_dia_raw)
        if novo_dia < 0 or novo_dia > 6:
            raise ValueError()
    except (ValueError, TypeError):
        return jsonify({
            'error': 'Invalid day of week (must be between 0 for Monday and 6 for Sunday)',
            'erro': 'Dia da semana inválido (deve ser entre 0 para Segunda e 6 para Domingo)'
        }), 400

    dia_anterior = contrato.dia_pagamento_semanal
    dias_nomes_en = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dias_nomes_pt = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']

    nome_antigo = f"{dias_nomes_en[dia_anterior]} ({dias_nomes_pt[dia_anterior]})" if (dia_anterior is not None and 0 <= dia_anterior <= 6) else 'Not set'
    nome_novo = f"{dias_nomes_en[novo_dia]} ({dias_nomes_pt[novo_dia]})"
    # Preserva o dia originalmente assinado no documento do contrato caso ainda não esteja congelado
    if getattr(contrato, 'dia_pagamento_semanal_original', None) is None and dia_anterior is not None:
        contrato.dia_pagamento_semanal_original = dia_anterior

    contrato.dia_pagamento_semanal = novo_dia

    # Ajuste opcional de cobranças pendentes de aluguel
    ajustar_pendentes = data.get('ajustar_pendentes') in [True, 'true', '1', 'on']
    cobrancas_ajustadas = 0

    if ajustar_pendentes and dia_anterior is not None:
        cobrancas_pendentes = FinancialTransaction.query.filter(
            FinancialTransaction.id_contrato == contrato.id,
            FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
            FinancialTransaction.tipo.in_([TransactionType.RENT.value, 'Rent', 'Aluguel'])
        ).all()

        for t in cobrancas_pendentes:
            if t.data_vencimento:
                venc_dia_semana = t.data_vencimento.weekday()
                diff_dias = (novo_dia - venc_dia_semana)
                if diff_dias != 0:
                    t.data_vencimento = t.data_vencimento + timedelta(days=diff_dias)
                    cobrancas_ajustadas += 1

    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    detalhes_ajuste = f" com ajuste de {cobrancas_ajustadas} cobrança(s) pendente(s)" if cobrancas_ajustadas > 0 else ""
    registrar_log(
        'CONTRACT_DUE_DAY_UPDATED',
        'Contract',
        str(contrato.id),
        f"Dia de cobrança semanal do contrato #{contrato.id} ({contrato.cliente_nome or 'Cliente'}) alterado de {nome_antigo} para {nome_novo} por {operador_atual}{detalhes_ajuste}"
    )

    db.session.commit()

    # Auto-sincronização imediata: se o novo dia de vencimento já exigir cobrança da próxima semana, provisiona de imediato
    try:
        _gerar_cobrancas_semanais_logic()
    except Exception as e_gen:
        print(f"[Dia Pagamento Auto-Sync Error]: {e_gen}")

    return jsonify({
        'message': f"Weekly payment due day updated to {dias_nomes_en[novo_dia]}",
        'mensagem': f"Dia de vencimento semanal alterado com sucesso para {dias_nomes_en[novo_dia]} ({dias_nomes_pt[novo_dia]})",
        'dia_pagamento_semanal': novo_dia,
        'dia_nome': dias_nomes_en[novo_dia],
        'cobrancas_ajustadas': cobrancas_ajustadas
    }), 200

@app.route('/api/contratos/<int:id>/notas', methods=['PUT', 'POST'])
@alugueis_required
def atualizar_notas_contrato(id):
    """
    Atualiza as notas internas do contrato para observações operacionais e particularidades.
    """
    contrato = db.session.get(Contract, id)
    if not contrato:
        return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404

    dados = request.get_json(silent=True) or request.form or {}
    notas = dados.get('notas_internas')
    novas_notas = str(notas).strip() if (notas and str(notas).strip()) else None

    contrato.notas_internas = novas_notas
    db.session.commit()

    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('CONTRACT_NOTES_UPDATE', 'Contract', contrato.id, f"Notas internas do contrato #{contrato.id} atualizadas por {operador_atual}")

    return jsonify({
        'message': 'Internal notes updated successfully',
        'mensagem': 'Notas internas atualizadas com sucesso',
        'notas_internas': contrato.notas_internas
    }), 200

@app.route('/api/contratos', methods=['GET'])
@alugueis_required
def listar_contratos():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    tipo_filter = request.args.get('tipo', '', type=str).strip()
    dia_pagamento_filter = request.args.get('dia_pagamento', '', type=str).strip()
    data_inicio_filter = request.args.get('data_inicio', '', type=str).strip()
    data_fim_filter = request.args.get('data_fim', '', type=str).strip()
    sort_by = request.args.get('sort_by', 'id', type=str).strip().lower()
    sort_order = request.args.get('sort_order', 'desc', type=str).strip().lower()
    
    query = Contract.query.options(
        selectinload(Contract.vistorias),
        selectinload(Contract.moto),
        contains_eager(Contract.cliente)
    ).join(Client, Contract.id_cliente == Client.id)

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
            Contract.cliente_telefone.ilike(search_term),
            Contract.moto_modelo.ilike(search_term),
            Client.nome.ilike(search_term),
            Client.telefone.ilike(search_term)
        ))

    if tipo_filter:
        if tipo_filter.lower() in ['sale', 'venda']:
            query = query.filter(Contract.tipo_contrato.in_([ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value]))
        elif tipo_filter.lower() in ['rent', 'aluguel']:
            query = query.filter(db.or_(Contract.tipo_contrato == ContractType.RENT.value, Contract.tipo_contrato == None))
        elif tipo_filter.lower() in ['purchase', 'compra']:
            query = query.filter(Contract.tipo_contrato.in_([ContractType.PURCHASE.value, 'Purchase', 'Compra']))
        else:
            query = query.filter(Contract.tipo_contrato == tipo_filter)

    if dia_pagamento_filter != '' and dia_pagamento_filter.isdigit():
        query = query.filter(Contract.dia_pagamento_semanal == int(dia_pagamento_filter))

    if data_inicio_filter:
        try:
            dt_ini = datetime.strptime(data_inicio_filter, '%Y-%m-%d')
            query = query.filter(Contract.data_retirada >= dt_ini)
        except ValueError:
            pass

    if data_fim_filter:
        try:
            dt_fim = datetime.strptime(data_fim_filter, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Contract.data_retirada < dt_fim)
        except ValueError:
            pass
        
    status_filter = request.args.get('status', '', type=str)
    if status_filter:
        if status_filter.lower() in ['pending_release', 'pendente_liberacao', 'pre-delivery']:
            # Active contracts with no insurance or no check-out inspection (excluding Purchase contracts)
            checkout_subq = db.session.query(Inspection.id).filter(
                Inspection.id_contrato == Contract.id,
                Inspection.tipo.in_([InspectionType.CHECK_OUT.value, 'Check-out', 'Saída', 'Saida'])
            ).exists()
            query = query.filter(
                Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']),
                ~Contract.tipo_contrato.in_([ContractType.PURCHASE.value, 'Purchase', 'Compra']),
                db.or_(Contract.url_seguro == None, ~checkout_subq)
            )
        elif status_filter.lower() in ['pending_v5c', 'needs_v5c']:
            # Active purchase contracts missing official V5C logbook for their current purchase cycle
            cand_purchases = Contract.query.filter(
                Contract.tipo_contrato.in_([ContractType.PURCHASE.value, 'Purchase', 'Compra']),
                Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo'])
            ).all()
            pending_ids = [
                cp.id for cp in cand_purchases 
                if not any((getattr(d, 'categoria_doc', 'v5c') or 'v5c') == 'v5c' for d in get_purchase_contract_v5c_docs(cp))
            ]
            query = query.filter(Contract.id.in_(pending_ids))
        elif status_filter.lower() in ['overdue', 'devedores', 'atrasados']:
            london_now = get_london_now()
            hoje_zero = london_now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
            overdue_subq = db.session.query(FinancialTransaction.id_contrato).filter(
                FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
                FinancialTransaction.data_vencimento < hoje_zero,
                ~FinancialTransaction.tipo.in_([TransactionType.DEPOSIT_REFUND.value, 'Deposit_Refund', 'Devolucao_Deposito'])
            ).distinct().subquery()
            query = query.filter(Contract.id.in_(db.session.query(overdue_subq.c.id_contrato)))
        elif status_filter.lower() in ['has_issues', 'com_pendencias', 'pendencias']:
            london_now = get_london_now()
            hoje_zero = london_now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
            overdue_subq = db.session.query(FinancialTransaction.id_contrato).filter(
                FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
                FinancialTransaction.data_vencimento < hoje_zero,
                ~FinancialTransaction.tipo.in_([TransactionType.DEPOSIT_REFUND.value, 'Deposit_Refund', 'Devolucao_Deposito'])
            ).distinct().subquery()
            
            checkout_subq = db.session.query(Inspection.id).filter(
                Inspection.id_contrato == Contract.id,
                Inspection.tipo.in_([InspectionType.CHECK_OUT.value, 'Check-out', 'Saída', 'Saida'])
            ).exists()
            
            query = query.filter(
                db.or_(
                    Contract.id.in_(db.session.query(overdue_subq.c.id_contrato)),
                    db.and_(
                        Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']),
                        ~Contract.tipo_contrato.in_([ContractType.PURCHASE.value, 'Purchase', 'Compra']),
                        db.or_(Contract.url_seguro == None, ~checkout_subq)
                    ),
                    Contract.assinatura_cliente_inicial == None
                )
            )
        elif status_filter.lower() in ['clean', 'no_issues', 'sem_pendencias']:
            london_now = get_london_now()
            hoje_zero = london_now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
            overdue_subq = db.session.query(FinancialTransaction.id_contrato).filter(
                FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
                FinancialTransaction.data_vencimento < hoje_zero,
                ~FinancialTransaction.tipo.in_([TransactionType.DEPOSIT_REFUND.value, 'Deposit_Refund', 'Devolucao_Deposito'])
            ).distinct().subquery()
            
            checkout_subq = db.session.query(Inspection.id).filter(
                Inspection.id_contrato == Contract.id,
                Inspection.tipo.in_([InspectionType.CHECK_OUT.value, 'Check-out', 'Saída', 'Saida'])
            ).exists()
            
            query = query.filter(
                ~Contract.id.in_(db.session.query(overdue_subq.c.id_contrato)),
                Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']),
                Contract.url_seguro != None,
                checkout_subq,
                Contract.assinatura_cliente_inicial != None
            )
        elif status_filter.lower() in ['deposit_hold', 'quarentena_deposito', 'quarentena']:
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
    
    # Real-time financial balances: Aggregate unpaid (pending, overdue) and paid totals per contract
    contract_ids = [c.id for c in paginated.items]
    pendentes_map = {}
    pagos_map = {}
    vencidos_map = {}
    vencidos_qtd_map = {}
    if contract_ids:
        hoje_date = get_london_date()

        txs = FinancialTransaction.query.filter(
            FinancialTransaction.id_contrato.in_(contract_ids),
            ~FinancialTransaction.tipo.in_([TransactionType.DEPOSIT_REFUND.value, 'Deposit_Refund', 'Devolucao_Deposito'])
        ).all()

        for tx in txs:
            st_norm = (tx.status or '').strip().lower()
            val = float(tx.valor or 0.0)
            cid = tx.id_contrato
            if st_norm in ['pending', 'pendente']:
                pendentes_map[cid] = pendentes_map.get(cid, 0.0) + val
                if is_transaction_overdue(tx, hoje_date):
                    vencidos_map[cid] = vencidos_map.get(cid, 0.0) + val
                    vencidos_qtd_map[cid] = vencidos_qtd_map.get(cid, 0) + 1
            elif st_norm in ['paid', 'pago']:
                pagos_map[cid] = pagos_map.get(cid, 0.0) + val

    itens = []
    for c in paginated.items:
        is_purchase = (getattr(c, 'tipo_contrato', None) in [ContractType.PURCHASE.value, 'Purchase', 'Compra'])
        tem_checkout = any(v.tipo in [InspectionType.CHECK_OUT.value, 'Check-out', 'Saída', 'Saida'] for v in (c.vistorias or []))
        tem_seguro = bool(c.url_seguro)
        is_active = (c.status in [ContractStatus.ACTIVE.value, 'Active', 'Ativo'])
        pendente_liberacao = is_active and not is_purchase and (not tem_checkout or not tem_seguro)
        
        placa_limpa = (c.moto_placa or c.placa or '').strip().upper()
        if is_purchase:
            docs_ciclo = get_purchase_contract_v5c_docs(c)
            v5c_count = len([v for v in docs_ciclo if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'v5c'])
            transfer_proof_count = len([v for v in docs_ciclo if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'transfer_proof'])
        elif c.moto and hasattr(c.moto, 'v5c_arquivos') and c.moto.v5c_arquivos:
            v5c_count = len([v for v in c.moto.v5c_arquivos if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'v5c'])
            transfer_proof_count = len([v for v in c.moto.v5c_arquivos if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'transfer_proof'])
        elif placa_limpa:
            v5c_count = MotorcycleV5C.query.filter_by(placa=placa_limpa, categoria_doc='v5c').count()
            transfer_proof_count = MotorcycleV5C.query.filter_by(placa=placa_limpa, categoria_doc='transfer_proof').count()
        else:
            v5c_count = 0
            transfer_proof_count = 0

        tem_v5c = (v5c_count > 0)
        tem_transfer_proof = (transfer_proof_count > 0)
        needs_v5c = bool(is_purchase and is_active and not tem_v5c)

        total_vencido = round(vencidos_map.get(c.id, 0.0), 2)
        qtd_vencidas = vencidos_qtd_map.get(c.id, 0)
        tem_pendencia_financeira = (total_vencido > 0)
        
        # Build consolidated pendencias list
        pendencias = []
        if tem_pendencia_financeira:
            pendencias.append(f"Debt: £{total_vencido:.2f}")
        if pendente_liberacao:
            tags = []
            if not tem_checkout: tags.append('Insp')
            if not tem_seguro: tags.append('Ins')
            pendencias.append(f"Needs {' + '.join(tags)}")
        if needs_v5c:
            pendencias.append("Needs V5C")
        if not bool(c.assinatura_cliente_inicial):
            pendencias.append("Unsigned")
        
        tem_pendencia = len(pendencias) > 0

        itens.append({
            'id': c.id, 
            'id_cliente': c.id_cliente, 
            'cliente_nome': c.cliente_nome or (c.cliente.nome if c.cliente else 'Customer'), 
            'cliente_telefone': c.cliente_telefone or (c.cliente.telefone if c.cliente else ''),
            'placa': c.moto_placa or c.placa,
            'moto_modelo': c.moto_modelo or (c.moto.modelo if c.moto else ''),
            'moto_cor': c.moto_cor or (c.moto.cor if c.moto else ''),
            'tipo_contrato': getattr(c, 'tipo_contrato', 'Rent') or 'Rent',
            'categoria_historico': c.categoria_historico,
            'valor_total_venda': float(c.valor_total_venda) if c.valor_total_venda is not None else None,
            'valor_entrada': float(c.valor_entrada) if c.valor_entrada is not None else 0.0,
            'saldo_devedor': float(c.saldo_devedor) if c.saldo_devedor is not None else 0.0,
            'total_pendente': round(pendentes_map.get(c.id, 0.0), 2),
            'total_vencido': total_vencido,
            'qtd_vencidas': qtd_vencidas,
            'tem_pendencia_financeira': tem_pendencia_financeira,
            'pendencias': pendencias,
            'tem_pendencia': tem_pendencia,
            'total_pago': round(pagos_map.get(c.id, 0.0), 2),
            'valor_compra_veiculo': float(c.valor_compra_veiculo) if c.valor_compra_veiculo is not None else None,
            'metodo_pagamento_compra': c.metodo_pagamento_compra,
            'detalhes_pagamento_compra': c.detalhes_pagamento_compra,
            'milhagem_nao_verificada': bool(c.milhagem_nao_verificada),
            'status_moto_destino': c.status_moto_destino,
            'data_retirada': c.data_retirada.isoformat() if c.data_retirada else None,
            'dia_pagamento_semanal': c.dia_pagamento_semanal,
            'valor_aluguel_semanal': c.valor_aluguel_semanal,
            'data_devolucao': c.data_devolucao.isoformat() if c.data_devolucao else None,
            'status': c.status,
            'url_seguro': c.url_seguro,
            'tem_vistoria_checkout': tem_checkout,
            'tem_seguro': tem_seguro,
            'pendente_liberacao': pendente_liberacao,
            'tem_v5c': tem_v5c,
            'tem_transfer_proof': tem_transfer_proof,
            'needs_v5c': needs_v5c,
            'v5c_count': v5c_count,
            'transfer_proof_count': transfer_proof_count,
            'assinado': bool(c.assinatura_cliente_inicial),
            'data_assinatura_inicial': c.data_assinatura_inicial.isoformat() if c.data_assinatura_inicial else None,
            'notas_internas': c.notas_internas
        })

    # Executive KPI Summary for Contracts
    kpi_checkout_subq = db.session.query(Inspection.id).filter(
        Inspection.id_contrato == Contract.id,
        Inspection.tipo.in_([InspectionType.CHECK_OUT.value, 'Check-out', 'Saída', 'Saida'])
    ).exists()

    kpi_v5c_subq = db.session.query(MotorcycleV5C.id).filter(
        MotorcycleV5C.placa == Contract.placa,
        MotorcycleV5C.categoria_doc == 'v5c'
    ).exists()

    kpi_rentals = Contract.query.filter(
        Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']),
        db.or_(Contract.tipo_contrato == ContractType.RENT.value, Contract.tipo_contrato == None, Contract.tipo_contrato == 'Rent')
    ).count()

    kpi_sales = Contract.query.filter(
        Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']),
        Contract.tipo_contrato.in_([ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value, 'Sale_Full', 'Sale_Installment'])
    ).count()

    kpi_pendente_liberacao = Contract.query.filter(
        Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']),
        ~Contract.tipo_contrato.in_([ContractType.PURCHASE.value, 'Purchase', 'Compra']),
        db.or_(Contract.url_seguro == None, ~kpi_checkout_subq)
    ).count()

    kpi_deposit_holds = Contract.query.filter(
        Contract.status.in_([ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito'])
    ).count()

    cand_purchases_kpi = Contract.query.filter(
        Contract.tipo_contrato.in_([ContractType.PURCHASE.value, 'Purchase', 'Compra']),
        Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo'])
    ).all()
    kpi_pending_v5c = sum(
        1 for cp in cand_purchases_kpi 
        if not any((getattr(d, 'categoria_doc', 'v5c') or 'v5c') == 'v5c' for d in get_purchase_contract_v5c_docs(cp))
    )

    london_now_kpi = get_london_now()
    hoje_zero_kpi = london_now_kpi.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    kpi_overdue = db.session.query(FinancialTransaction.id_contrato).filter(
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
        FinancialTransaction.data_vencimento < hoje_zero_kpi,
        ~FinancialTransaction.tipo.in_([TransactionType.DEPOSIT_REFUND.value, 'Deposit_Refund', 'Devolucao_Deposito'])
    ).distinct().count()
    
    return jsonify({
        'itens': itens,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page,
        'kpis': {
            'rentals': kpi_rentals,
            'sales': kpi_sales,
            'pending_release': kpi_pendente_liberacao,
            'deposit_holds': kpi_deposit_holds,
            'pending_v5c': kpi_pending_v5c,
            'overdue': kpi_overdue
        }
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
    has_checkout_inspection = any(v.tipo in [InspectionType.CHECK_OUT.value, 'Check-out', 'Saída', 'Saida'] for v in vistorias)
    has_insurance_doc = bool(c.url_seguro)
    is_active = (c.status in [ContractStatus.ACTIVE.value, 'Active', 'Ativo'])
    is_pre_release_pending = is_active and (not has_checkout_inspection or not has_insurance_doc)
    
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
    total_pago_contrato = sum(float(t.valor) for t in transacoes_cliente if t.status in [TransactionStatus.PAID.value, 'Paid', 'Pago'])
    total_pendente_contrato = sum(float(t.valor) for t in transacoes_cliente if t.status in [TransactionStatus.PENDING.value, 'Pending', 'Pendente', 'Overdue', 'Atrasado'])
    total_faturado_contrato = sum(float(t.valor) for t in transacoes_cliente)
    
    # 15-Day Insurance Compliance (askMID Verification) - apenas para contratos de aluguel (Rent)
    tipo_contrato_val = getattr(c, 'tipo_contrato', 'Rent') or 'Rent'
    is_venda = tipo_contrato_val in [ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value, 'Sale_Full', 'Sale_Installment']
    is_purchase = tipo_contrato_val in [ContractType.PURCHASE.value, 'Purchase', 'Compra']
    is_pre_release_pending = is_active and not (is_venda or is_purchase) and (not has_checkout_inspection or not has_insurance_doc)
    
    hoje = get_local_now().date()
    ultima_checagem = c.data_ultima_checagem_seguro or (c.data_retirada.date() if c.data_retirada else hoje)
    dias_desde_checagem = (hoje - ultima_checagem).days
    dias_para_proxima = max(0, 15 - dias_desde_checagem)
    checagem_seguro_devida = (dias_desde_checagem >= 15) if not (is_venda or is_purchase) else False
    
    # Sincronização dinâmica de contratos de venda e compra
    if is_venda:
        sync_sale_contract_status(c, auto_commit=True)
    elif is_purchase:
        sync_purchase_contract_status(c, auto_commit=True)

    is_completed = (c.status in [ContractStatus.COMPLETED.value, 'Completed', 'Finalizado', ContractStatus.CANCELLED.value, 'Cancelled', 'Cancelado'])
    
    # Parse cronograma se existir
    cronograma_parsed = []
    if c.cronograma_parcelas_json:
        try:
            cronograma_parsed = json.loads(c.cronograma_parcelas_json)
        except Exception:
            cronograma_parsed = []

    # Na tela operacional de detalhes do contrato, os dados do cliente e da moto devem
    # refletir as informações ATUALIZADAS dos respectivos cadastros (telefone, email, endereço, docs, modelo, cor),
    # enquanto o documento impresso do contrato permanece 100% imutável no snapshot original.
    current_cliente_nome = (cliente.nome if cliente and cliente.nome else c.cliente_nome) or 'Customer'
    current_cliente_telefone = cliente.telefone if (cliente and cliente.telefone) else c.cliente_telefone
    current_cliente_email = cliente.email if (cliente and cliente.email) else c.cliente_email
    current_cliente_endereco = cliente.endereco if (cliente and cliente.endereco) else c.cliente_endereco
    current_url_habilitacao = cliente.url_habilitacao if (cliente and cliente.url_habilitacao) else c.url_habilitacao
    current_url_habilitacao_verso = cliente.url_habilitacao_verso if (cliente and cliente.url_habilitacao_verso) else c.url_habilitacao_verso
    current_url_cbt = cliente.url_cbt if (cliente and cliente.url_cbt) else c.url_cbt
    current_url_comprovante_endereco = cliente.url_comprovante_endereco if (cliente and cliente.url_comprovante_endereco) else c.url_comprovante_endereco

    current_moto_placa = moto.placa if (moto and moto.placa) else (c.moto_placa or c.placa)
    current_moto_modelo = (moto.modelo if moto and moto.modelo else c.moto_modelo) or '-'
    current_moto_cor = (moto.cor if moto and moto.cor else c.moto_cor) or '-'

    placa_alvo_c = (current_moto_placa or '').strip().upper()
    if is_purchase:
        docs_ciclo = get_purchase_contract_v5c_docs(c)
        num_v5c = len([v for v in docs_ciclo if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'v5c'])
        num_transfer = len([v for v in docs_ciclo if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'transfer_proof'])
    elif moto and hasattr(moto, 'v5c_arquivos') and moto.v5c_arquivos:
        num_v5c = len([v for v in moto.v5c_arquivos if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'v5c'])
        num_transfer = len([v for v in moto.v5c_arquivos if (getattr(v, 'categoria_doc', 'v5c') or 'v5c') == 'transfer_proof'])
    elif placa_alvo_c:
        num_v5c = MotorcycleV5C.query.filter_by(placa=placa_alvo_c, categoria_doc='v5c').count()
        num_transfer = MotorcycleV5C.query.filter_by(placa=placa_alvo_c, categoria_doc='transfer_proof').count()
    else:
        num_v5c = 0
        num_transfer = 0
    has_v5c_doc = (num_v5c > 0)
    has_transfer_doc = (num_transfer > 0)
    needs_v5c_doc = bool(is_purchase and c.status in [ContractStatus.ACTIVE.value, 'Active', 'Ativo'] and not has_v5c_doc)

    return jsonify({
        'id': c.id,
        'tipo_contrato': getattr(c, 'tipo_contrato', 'Rent') or 'Rent',
        'notas_internas': c.notas_internas,
        'categoria_historico': c.categoria_historico,
        'valor_venda_veiculo': float(c.valor_venda_veiculo) if c.valor_venda_veiculo is not None else None,
        'acessorios_extras': c.acessorios_extras,
        'valor_admin_fee': float(c.valor_admin_fee) if c.valor_admin_fee is not None else 0.0,
        'valor_total_venda': float(c.valor_total_venda) if c.valor_total_venda is not None else None,
        'valor_entrada': float(c.valor_entrada) if c.valor_entrada is not None else 0.0,
        'saldo_devedor': float(c.saldo_devedor) if c.saldo_devedor is not None else 0.0,
        'valor_compra_veiculo': float(c.valor_compra_veiculo) if c.valor_compra_veiculo is not None else None,
        'metodo_pagamento_compra': c.metodo_pagamento_compra,
        'detalhes_pagamento_compra': c.detalhes_pagamento_compra,
        'milhagem_nao_verificada': bool(c.milhagem_nao_verificada),
        'status_moto_destino': c.status_moto_destino,
        'cronograma_parcelas': cronograma_parsed,
        'id_cliente': c.id_cliente,
        'cliente': current_cliente_nome,
        'cliente_nome': current_cliente_nome,
        'telefone': current_cliente_telefone,
        'cliente_telefone': current_cliente_telefone,
        'endereco': current_cliente_endereco,
        'cliente_endereco': current_cliente_endereco,
        'email': current_cliente_email,
        'cliente_email': current_cliente_email,
        'url_habilitacao': current_url_habilitacao,
        'url_habilitacao_verso': current_url_habilitacao_verso,
        'url_cbt': current_url_cbt,
        'url_comprovante_endereco': current_url_comprovante_endereco,
        'placa': current_moto_placa,
        'modelo': current_moto_modelo,
        'moto_modelo': current_moto_modelo,
        'cor': current_moto_cor,
        'moto_cor': current_moto_cor,
        'dia_pagamento_semanal': c.dia_pagamento_semanal,
        'dia_pagamento_semanal_original': c.dia_pagamento_semanal_original if getattr(c, 'dia_pagamento_semanal_original', None) is not None else c.dia_pagamento_semanal,
        # Snapshot imutável preservado para integridade jurídica e auditoria
        'snapshot_cliente_nome': c.cliente_nome,
        'snapshot_cliente_telefone': c.cliente_telefone,
        'snapshot_cliente_email': c.cliente_email,
        'snapshot_cliente_endereco': c.cliente_endereco,
        'snapshot_moto_modelo': c.moto_modelo,
        'snapshot_moto_cor': c.moto_cor,
        'snapshot_moto_placa': c.moto_placa,
        'milhagem_atual_moto': int(moto.milhagem_atual or 0) if moto else 0,
        'milhagem_inicial': c.milhagem_inicial if c.milhagem_inicial is not None else 0,
        'milhagem_final': c.milhagem_final,
        'v5c_count': num_v5c,
        'transfer_proof_count': num_transfer,
        'tem_v5c': has_v5c_doc,
        'tem_transfer_proof': has_transfer_doc,
        'needs_v5c': needs_v5c_doc,
        'trackers_count': len(moto.trackers) if (moto and hasattr(moto, 'trackers') and moto.trackers) else 0,
        'trackers_summary': [{
            'id': t.id,
            'numero': t.numero,
            'tipo_propriedade': t.tipo_propriedade,
            'has_photos': bool(t.url_fotos)
        } for t in (moto.trackers or [])] if (moto and hasattr(moto, 'trackers') and moto.trackers) else [],
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
        'tax_sorn': bool(getattr(moto, 'tax_sorn', False)) if moto else False,
        'data_retirada': c.data_retirada.isoformat() if c.data_retirada else None,
        'data_devolucao': c.data_devolucao.isoformat() if c.data_devolucao else None,
        'dia_pagamento_semanal': c.dia_pagamento_semanal,
        'valor_aluguel_semanal': float(c.valor_aluguel_semanal) if c.valor_aluguel_semanal else 0.0,
        'status': c.status,
        'is_completed': is_completed,
        'url_seguro': c.url_seguro,
        'has_checkout_inspection': has_checkout_inspection,
        'has_insurance_doc': has_insurance_doc,
        'is_pre_release_pending': is_pre_release_pending,
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
        'total_pago': total_pago_contrato,
        'total_pendente': total_pendente_contrato,
        'total_faturado': total_faturado_contrato,
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
            'detalhes_pagamento': json.loads(t.detalhes_pagamento_json) if t.detalhes_pagamento_json else None,
            'id_transacao_origem': t.id_transacao_origem,
            'nota': t.nota or (t.vistoria.observacoes if (t.id_vistoria and t.vistoria and t.vistoria.observacoes) else None),
            'nota_pagamento': t.nota_pagamento,
            'url_anexos': t.url_anexos,
            'id_vistoria': t.id_vistoria,
            'registrado_por_nome': t.registrado_por_nome or '',
            'data_vencimento': t.data_vencimento.isoformat() if t.data_vencimento else None,
            'data_pagamento': t.data_pagamento.isoformat() if t.data_pagamento else None,
            'ultimo_lembrete': t.ultimo_lembrete.isoformat() if t.ultimo_lembrete else None,
            'ultimo_lembrete_por': t.ultimo_lembrete_por or ''
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
        
    is_form = not request.is_json
    dados = request.form if is_form else (request.get_json() or {})

    tipo = dados.get('tipo')
    valor = dados.get('valor')
    data_vencimento_str = dados.get('data_vencimento')
    
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
    nota_input = (dados.get('referencia') or dados.get('nota') or '').strip()

    # Process photo/document attachments if provided
    urls_anexos = []
    if request.files:
        fotos = request.files.getlist('fotos')
        if not fotos and 'foto' in request.files:
            fotos = [request.files['foto']]
        if not fotos and 'anexos' in request.files:
            fotos = request.files.getlist('anexos')

        timestamp = get_local_now().strftime("%Y%m%d%H%M%S")
        for i, foto in enumerate(fotos):
            if foto and foto.filename:
                if not is_allowed_file(foto.filename):
                    return jsonify({'error': 'Invalid attachment format. Only JPG, PNG, WEBP, and PDF documents are allowed.', 'erro': 'Formato de anexo inválido. Permitido apenas JPG, PNG, WEBP e PDF.'}), 400
                filename = werkzeug.utils.secure_filename(foto.filename)
                nome_arquivo = f"{timestamp}_cob_{i}_{filename}"
                nome_salvo = salvar_arquivo_otimizado(foto, nome_arquivo)
                urls_anexos.append(f"/static/uploads/{nome_salvo}")

    url_anexos_str = ",".join(urls_anexos) if urls_anexos else None

    id_vistoria_val = None
    if dados.get('id_vistoria'):
        try:
            id_vistoria_val = int(dados.get('id_vistoria'))
        except (ValueError, TypeError):
            id_vistoria_val = None

    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'

    nova_cobranca = FinancialTransaction(
        id_contrato=c.id,
        tipo=tipo_final,
        data_vencimento=data_vencimento,
        valor=float(valor),
        status=TransactionStatus.PENDING.value,
        nota=nota_input if nota_input else None,
        url_anexos=url_anexos_str,
        id_vistoria=id_vistoria_val,
        registrado_por_nome=operador_atual
    )
    db.session.add(nova_cobranca)
    sync_sale_contract_status(c)
    db.session.commit()
    
    nota_log = f" (Ref/Nota: '{nota_input}')" if nota_input else ""
    anexo_log = f" com {len(urls_anexos)} anexo(s)" if urls_anexos else ""
    registrar_log('CREATE_CHARGE', 'Transaction', nova_cobranca.id, f"Cobrança manual de £{float(valor):.2f} ({tipo_final}) gerada por {operador_atual} para o Contrato #{c.id}{nota_log}{anexo_log}")

    return jsonify({
        'message': 'Charge created successfully',
        'mensagem': 'Cobrança gerada com sucesso',
        'id': nova_cobranca.id,
        'url_anexos': nova_cobranca.url_anexos
    }), 201

@app.route('/api/cobrancas/<int:id>/pagar', methods=['PUT', 'POST'])
@alugueis_required
def pagar_cobranca(id):
    return pagar_transacao(id)

@app.route('/api/vistorias', methods=['POST'])
@alugueis_required
def criar_vistoria():
    id_contrato = request.form.get('id_contrato') or request.form.get('contrato_id')
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
    elif str(tipo).strip().lower() in ['check-out', 'checkout', 'saída', 'saida']:
        if contrato and milhagem_val is not None:
            if not contrato.milhagem_inicial or contrato.milhagem_inicial == 0:
                contrato.milhagem_inicial = milhagem_val

    cobranca_gerada_id = None
    gerar_cobranca_flag = request.form.get('gerar_cobranca') in ['1', 'true', 'True', True]
    valor_cobranca_raw = request.form.get('cobranca_valor')
    if (gerar_cobranca_flag or valor_cobranca_raw) and contrato:
        try:
            valor_cob = float(valor_cobranca_raw or 0.0)
            if valor_cob > 0:
                tipo_cob = request.form.get('cobranca_tipo') or TransactionType.DAMAGE.value
                data_venc_cob_str = request.form.get('cobranca_vencimento')
                try:
                    data_venc_cob = datetime.strptime(data_venc_cob_str, "%Y-%m-%d") if data_venc_cob_str else get_local_now()
                except (ValueError, TypeError):
                    data_venc_cob = get_local_now()
                
                referencia_cob = (request.form.get('cobranca_referencia') or request.form.get('cobranca_nota') or '').strip()
                if not referencia_cob:
                    referencia_cob = f"Damage/Repair from {tipo} Inspection"
                
                db.session.flush()

                nova_cobranca = FinancialTransaction(
                    id_contrato=contrato.id,
                    tipo=tipo_cob,
                    data_vencimento=data_venc_cob,
                    valor=valor_cob,
                    status=TransactionStatus.PENDING.value,
                    nota=referencia_cob,
                    url_anexos=url_foto_str,
                    id_vistoria=nova_vistoria.id,
                    registrado_por_nome=operador_atual
                )
                db.session.add(nova_cobranca)
                sync_sale_contract_status(contrato)
                db.session.flush()
                cobranca_gerada_id = nova_cobranca.id
                registrar_log('CREATE_CHARGE', 'Transaction', nova_cobranca.id, f"Cobrança automática de £{valor_cob:.2f} ({tipo_cob}) vinculada à vistoria #{nova_vistoria.id} gerada por {operador_atual} para o Contrato #{contrato.id} (Ref: '{referencia_cob}')")
        except (ValueError, TypeError):
            pass

    db.session.commit()
    
    milhas_txt = f" (Milhagem: {milhagem_val} mi)" if milhagem_val is not None else ""
    registrar_log('CREATE_INSPECTION', 'Inspection', nova_vistoria.id, f"Vistoria de {tipo} registrada por {operador_atual} no Contrato #{id_contrato}{milhas_txt}")
    if tipo in [InspectionType.CHECK_IN.value, 'Check-in', 'Entrada']:
        registrar_log('RETURN_VEHICLE', 'Contract', id_contrato, f"Moto devolvida / Check-in confirmado por {operador_atual} no Contrato #{id_contrato}{milhas_txt}")
    
    return jsonify({
        'message': 'Inspection recorded successfully',
        'mensagem': 'Vistoria registrada com sucesso',
        'id': nova_vistoria.id,
        'url': url_foto_str,
        'cobranca_id': cobranca_gerada_id,
        'cobranca_gerada': bool(cobranca_gerada_id)
    }), 201

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
@financeiro_required
def listar_financeiro():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    if limit <= 0 or limit > 500:
        limit = 500
    search = request.args.get('search', '', type=str)
    contrato_id = request.args.get('contrato_id', None, type=int)
    cliente_id = request.args.get('cliente_id', None, type=int)
    placa_filtro = request.args.get('placa', '', type=str).strip()
    status_filtro = request.args.get('status', '', type=str)
    tipo_filtro = request.args.get('tipo', '', type=str)
    metodo_filtro = request.args.get('metodo', '', type=str).strip()
    pendentes = request.args.get('pendentes') == 'true'
    data_inicio = request.args.get('data_inicio', '', type=str).strip()
    data_fim = request.args.get('data_fim', '', type=str).strip()
    campo_data = request.args.get('campo_data', '', type=str).strip().lower()
    if not campo_data:
        if status_filtro and status_filtro.lower() in ['paid', 'pago']:
            campo_data = 'pagamento'
        else:
            campo_data = 'vencimento'
    elif campo_data == 'pagamento' and (status_filtro in ['overdue', 'vencidos', 'vencido', 'pending', 'pendente'] or pendentes):
        campo_data = 'vencimento'

    sort_by = request.args.get('sort_by', '', type=str).strip().lower()
    sort_order = request.args.get('sort_order', '', type=str).strip().lower()
    if not sort_by:
        if campo_data == 'pagamento' or (status_filtro and status_filtro.lower() in ['paid', 'pago']):
            sort_by = 'data_pagamento'
            if not sort_order:
                sort_order = 'desc'
        else:
            sort_by = 'data_vencimento'
            if not sort_order:
                sort_order = 'asc'
    elif not sort_order:
        sort_order = 'desc' if sort_by in ['data_pagamento', 'pagamento'] else 'asc'
    
    query = FinancialTransaction.query.outerjoin(Contract, FinancialTransaction.id_contrato == Contract.id).outerjoin(Client, Contract.id_cliente == Client.id)
    
    # Precise Exact Filters (1-Click Filters)
    if contrato_id:
        query = query.filter(FinancialTransaction.id_contrato == contrato_id)
    if cliente_id:
        query = query.filter(Contract.id_cliente == cliente_id)
    if placa_filtro:
        placa_clean = placa_filtro.replace(' ', '')
        query = query.filter(db.or_(Contract.placa.ilike(placa_clean), Contract.placa.ilike(placa_filtro)))

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
            FinancialTransaction.nota.ilike(search_term),
            FinancialTransaction.valor.cast(db.String).ilike(search_term),
            Contract.placa.ilike(search_plate_term),
            Contract.placa.ilike(search_term),
            Client.nome.ilike(search_term)
        ))
        
    if status_filtro:
        if status_filtro.lower() in ['overdue', 'vencidos', 'vencido']:
            inicio_hoje = get_london_now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
            query = query.filter(
                FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
                FinancialTransaction.data_vencimento < inicio_hoje
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

    if metodo_filtro:
        query = query.filter(FinancialTransaction.forma_pagamento.ilike(f"%{metodo_filtro}%"))

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

    # Compute high-risk debt counts (overdue transactions per client)
    client_ids = list(set([t.contrato.id_cliente for t in paginated.items if t.contrato and t.contrato.id_cliente]))
    dividas_map = {}
    if client_ids:
        inicio_hoje = datetime.combine(get_london_date(), datetime.min.time())
        contagem_dividas = db.session.query(
            Contract.id_cliente,
            db.func.count(FinancialTransaction.id)
        ).join(
            FinancialTransaction, Contract.id == FinancialTransaction.id_contrato
        ).filter(
            Contract.id_cliente.in_(client_ids),
            FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
            FinancialTransaction.data_vencimento < inicio_hoje
        ).group_by(Contract.id_cliente).all()
        for cid, cnt in contagem_dividas:
            dividas_map[cid] = int(cnt or 0)
    
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
        'detalhes_pagamento': json.loads(t.detalhes_pagamento_json) if t.detalhes_pagamento_json else None,
        'id_transacao_origem': t.id_transacao_origem,
        'nota': t.nota or (t.vistoria.observacoes if (t.id_vistoria and t.vistoria and t.vistoria.observacoes) else None),
        'nota_pagamento': t.nota_pagamento,
        'url_anexos': t.url_anexos,
        'id_vistoria': t.id_vistoria,
        'registrado_por_nome': t.registrado_por_nome or '',
        'placa': t.contrato.placa if t.contrato else '',
        'cliente': t.contrato.cliente.nome if (t.contrato and t.contrato.cliente) else '',
        'cliente_id': t.contrato.id_cliente if t.contrato else None,
        'cliente_telefone': t.contrato.cliente.telefone if (t.contrato and t.contrato.cliente) else '',
        'cliente_dividas_pendentes': dividas_map.get(t.contrato.id_cliente, 0) if (t.contrato and t.contrato.id_cliente) else 0,
        'ultimo_lembrete': t.ultimo_lembrete.isoformat() if t.ultimo_lembrete else None,
        'ultimo_lembrete_por': t.ultimo_lembrete_por or ''
    } for t in paginated.items]
    
    return jsonify({
        'itens': itens,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page
    })

@app.route('/api/financeiro/<int:id>/lembrete', methods=['POST'])
@alugueis_required
def registrar_lembrete_cobranca(id):
    t = db.session.get(FinancialTransaction, id)
    if not t:
        return jsonify({'error': 'Transaction not found', 'erro': 'Transação não encontrada'}), 404
        
    agora = get_local_now()
    operador = current_user.nome if (current_user and current_user.is_authenticated) else 'Staff'
    t.ultimo_lembrete = agora
    t.ultimo_lembrete_por = operador
    db.session.commit()
    
    cli_nome = (t.contrato.cliente.nome if (t.contrato and t.contrato.cliente) else (t.contrato.cliente_nome if t.contrato else 'Cliente')) or 'Cliente'
    placa = t.contrato.placa if t.contrato else 'N/A'
    venc_str = t.data_vencimento.strftime('%d/%m/%Y') if t.data_vencimento else 'N/A'
    registrar_log(
        'PAYMENT_REMINDER',
        'Transaction',
        t.id,
        f"Lembrete de cobrança WhatsApp enviado por {operador} para {cli_nome} (Contrato #{t.id_contrato or 'N/A'}, Placa: {placa}, Cobrança #{t.id}: £{float(t.valor):.2f} {t.tipo}, Venc: {venc_str})"
    )

    return jsonify({
        'sucesso': True,
        'message': 'Reminder logged successfully',
        'mensagem': 'Lembrete registrado com sucesso',
        'ultimo_lembrete': agora.isoformat(),
        'ultimo_lembrete_por': operador
    }), 200

@app.route('/api/financeiro/pagar-lote', methods=['POST'])
@alugueis_required
def pagar_transacoes_lote():
    data = request.get_json() or {}
    ids = data.get('ids', [])
    forma = (data.get('forma_pagamento') or 'Cash').strip()
    nota = (data.get('nota') or '').strip() or None
    
    if not ids or not isinstance(ids, list):
        return jsonify({'error': 'No transactions selected', 'erro': 'Nenhuma transação selecionada'}), 400
        
    operador = current_user.nome if (current_user and current_user.is_authenticated) else 'Staff'
    agora = get_local_now()
    
    transacoes = FinancialTransaction.query.filter(
        FinancialTransaction.id.in_(ids),
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente'])
    ).all()
    
    if not transacoes:
        return jsonify({'error': 'No pending transactions found for the selected IDs', 'erro': 'Nenhuma cobrança pendente encontrada para os IDs selecionados'}), 400
        
    total_pago = 0.0
    qtd_pagas = 0
    contratos_afetados = set()
    
    for t in transacoes:
        t.status = TransactionStatus.PAID.value
        t.data_pagamento = agora
        t.forma_pagamento = forma
        t.detalhes_pagamento_json = json.dumps([{'forma': forma, 'valor': float(t.valor)}])
        if nota:
            t.nota = f"{t.nota} | {nota}" if t.nota else nota
        t.registrado_por_nome = operador
        total_pago += float(t.valor)
        qtd_pagas += 1
        if t.contrato:
            contratos_afetados.add(t.contrato)
            
    # Sincronização do status de contratos de venda afetados
    for c in contratos_afetados:
        sync_sale_contract_status(c)
                
    db.session.commit()
    registrar_log('BATCH_PAYMENT', 'Transaction', f"{qtd_pagas} items", f"Baixa em lote de {qtd_pagas} cobranças (£{total_pago:.2f}) via {forma} por {operador}")
    
    return jsonify({
        'sucesso': True,
        'message': f'{qtd_pagas} payments recorded successfully',
        'mensagem': f'{qtd_pagas} pagamentos registrados com sucesso',
        'count': qtd_pagas,
        'atualizados': qtd_pagas,
        'total': round(total_pago, 2),
        'total_pago': round(total_pago, 2)
    }), 200

@app.route('/api/financeiro/resumo', methods=['GET'])
@financeiro_required
def financeiro_resumo():
    agora_london = get_london_now()
    hoje_inicio = agora_london.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    hoje_fim = hoje_inicio + timedelta(days=1)
    inicio_semana = hoje_inicio - timedelta(days=agora_london.weekday())
    inicio_mes = hoje_inicio.replace(day=1)
    
    # 1. Total Pendente
    res_pend = db.session.query(
        db.func.coalesce(db.func.sum(FinancialTransaction.valor), 0.0),
        db.func.count(FinancialTransaction.id)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente'])
    ).first()
    total_pendente = float(res_pend[0] or 0.0)
    qtd_pendente = int(res_pend[1] or 0)
    
    # 2. Overdue (Vencidos)
    res_overdue = db.session.query(
        db.func.coalesce(db.func.sum(FinancialTransaction.valor), 0.0),
        db.func.count(FinancialTransaction.id)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
        FinancialTransaction.data_vencimento < hoje_inicio
    ).first()
    total_overdue = float(res_overdue[0] or 0.0)
    qtd_overdue = int(res_overdue[1] or 0)
    
    # 3. Recebido Hoje
    res_hoje = db.session.query(
        db.func.coalesce(db.func.sum(FinancialTransaction.valor), 0.0),
        db.func.count(FinancialTransaction.id)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PAID.value, 'Paid', 'Pago']),
        FinancialTransaction.data_pagamento >= hoje_inicio,
        FinancialTransaction.data_pagamento < hoje_fim
    ).first()
    total_hoje = float(res_hoje[0] or 0.0)
    qtd_hoje = int(res_hoje[1] or 0)
    
    # 4. Recebido na Semana
    res_semana = db.session.query(
        db.func.coalesce(db.func.sum(FinancialTransaction.valor), 0.0),
        db.func.count(FinancialTransaction.id)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PAID.value, 'Paid', 'Pago']),
        FinancialTransaction.data_pagamento >= inicio_semana,
        FinancialTransaction.data_pagamento < hoje_fim
    ).first()
    total_semana = float(res_semana[0] or 0.0)
    qtd_semana = int(res_semana[1] or 0)
    
    # 5. Recebido no Mês
    res_mes = db.session.query(
        db.func.coalesce(db.func.sum(FinancialTransaction.valor), 0.0),
        db.func.count(FinancialTransaction.id)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PAID.value, 'Paid', 'Pago']),
        FinancialTransaction.data_pagamento >= inicio_mes,
        FinancialTransaction.data_pagamento < hoje_fim
    ).first()
    total_mes = float(res_mes[0] or 0.0)
    qtd_mes = int(res_mes[1] or 0)
    
    return jsonify({
        'pendente': {'total': round(total_pendente, 2), 'qtd': qtd_pendente},
        'overdue': {'total': round(total_overdue, 2), 'qtd': qtd_overdue},
        'hoje': {'total': round(total_hoje, 2), 'qtd': qtd_hoje},
        'semana': {'total': round(total_semana, 2), 'qtd': qtd_semana},
        'mes': {'total': round(total_mes, 2), 'qtd': qtd_mes}
    })

@app.route('/api/financeiro/fechamento-caixa', methods=['GET'])
@financeiro_required
def fechamento_caixa():
    data_str = request.args.get('data', '').strip()
    if data_str:
        try:
            target_date = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = get_london_date()
    else:
        target_date = get_london_date()
        
    inicio_dia = datetime.combine(target_date, datetime.min.time())
    fim_dia = inicio_dia + timedelta(days=1)
    
    transacoes = FinancialTransaction.query.options(
        joinedload(FinancialTransaction.contrato).joinedload(Contract.cliente)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PAID.value, 'Paid', 'Pago']),
        FinancialTransaction.data_pagamento >= inicio_dia,
        FinancialTransaction.data_pagamento < fim_dia
    ).order_by(FinancialTransaction.data_pagamento.asc()).all()
    
    metodos_resumo = {
        'Cash': {'total': 0.0, 'qtd': 0, 'itens': []},
        'Card': {'total': 0.0, 'qtd': 0, 'itens': []},
        'Bank Transfer': {'total': 0.0, 'qtd': 0, 'itens': []},
        'Exchange': {'total': 0.0, 'qtd': 0, 'itens': []},
        'Deposit': {'total': 0.0, 'qtd': 0, 'itens': []},
        'Other': {'total': 0.0, 'qtd': 0, 'itens': []}
    }
    
    total_dia = 0.0
    
    for t in transacoes:
        v_total = float(t.valor)
        total_dia += v_total
        
        detalhes = None
        if t.detalhes_pagamento_json:
            try:
                detalhes = json.loads(t.detalhes_pagamento_json)
            except Exception:
                detalhes = None
                
        hora_fmt = t.data_pagamento.strftime('%H:%M') if t.data_pagamento else '--:--'
        base_item = {
            'id': t.id,
            'id_contrato': t.id_contrato,
            'cliente': t.contrato.cliente.nome if (t.contrato and t.contrato.cliente) else 'Unknown',
            'placa': t.contrato.placa if t.contrato else '-',
            'tipo': obter_descricao_recibo_simples(t.tipo),
            'hora': hora_fmt,
            'nota': t.nota or '',
            'registrado_por': t.registrado_por_nome or ''
        }
        
        if detalhes and isinstance(detalhes, list) and len(detalhes) > 0:
            for d in detalhes:
                forma = (d.get('forma') or 'Other').strip()
                v_parte = float(d.get('valor') or 0.0)
                
                key = 'Other'
                forma_lower = forma.lower()
                if 'cash' in forma_lower or 'dinheiro' in forma_lower:
                    key = 'Cash'
                elif 'card' in forma_lower or 'cartao' in forma_lower or 'cartão' in forma_lower:
                    key = 'Card'
                elif 'transfer' in forma_lower or 'bank' in forma_lower or 'banco' in forma_lower:
                    key = 'Bank Transfer'
                elif 'exchange' in forma_lower or 'trade' in forma_lower or 'troca' in forma_lower:
                    key = 'Exchange'
                elif 'deposit' in forma_lower or 'deposito' in forma_lower or 'depósito' in forma_lower:
                    key = 'Deposit'
                    
                metodos_resumo[key]['total'] += v_parte
                metodos_resumo[key]['qtd'] += 1
                item_copy = dict(base_item)
                item_copy['valor'] = v_parte
                item_copy['forma_especifica'] = forma
                metodos_resumo[key]['itens'].append(item_copy)
        else:
            forma = (t.forma_pagamento or 'Cash').strip()
            key = 'Other'
            forma_lower = forma.lower()
            if 'cash' in forma_lower or 'dinheiro' in forma_lower:
                key = 'Cash'
            elif 'card' in forma_lower or 'cartao' in forma_lower or 'cartão' in forma_lower:
                key = 'Card'
            elif 'transfer' in forma_lower or 'bank' in forma_lower or 'banco' in forma_lower:
                key = 'Bank Transfer'
            elif 'exchange' in forma_lower or 'trade' in forma_lower or 'troca' in forma_lower:
                key = 'Exchange'
            elif 'deposit' in forma_lower or 'deposito' in forma_lower or 'depósito' in forma_lower:
                key = 'Deposit'
                
            metodos_resumo[key]['total'] += v_total
            metodos_resumo[key]['qtd'] += 1
            item_copy = dict(base_item)
            item_copy['valor'] = v_total
            item_copy['forma_especifica'] = forma
            metodos_resumo[key]['itens'].append(item_copy)

    for k in metodos_resumo:
        metodos_resumo[k]['total'] = round(metodos_resumo[k]['total'], 2)

    return jsonify({
        'data': target_date.strftime('%Y-%m-%d'),
        'data_formatada': target_date.strftime('%d/%m/%Y'),
        'total_arrecadado': round(total_dia, 2),
        'total_transacoes': len(transacoes),
        'metodos': metodos_resumo
    })


@app.route('/financeiro/fechamento-caixa/print', methods=['GET'])
@financeiro_required
def relatorio_fechamento_caixa_print():
    data_str = request.args.get('data', '').strip()
    if data_str:
        try:
            target_date = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = get_london_date()
    else:
        target_date = get_london_date()
        
    inicio_dia = datetime.combine(target_date, datetime.min.time())
    fim_dia = inicio_dia + timedelta(days=1)
    
    transacoes = FinancialTransaction.query.options(
        joinedload(FinancialTransaction.contrato).joinedload(Contract.cliente)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PAID.value, 'Paid', 'Pago']),
        FinancialTransaction.data_pagamento >= inicio_dia,
        FinancialTransaction.data_pagamento < fim_dia
    ).order_by(FinancialTransaction.data_pagamento.asc()).all()
    
    metodos_resumo = {
        'Cash': {'total': 0.0, 'qtd': 0, 'itens': []},
        'Card': {'total': 0.0, 'qtd': 0, 'itens': []},
        'Bank Transfer': {'total': 0.0, 'qtd': 0, 'itens': []},
        'Exchange': {'total': 0.0, 'qtd': 0, 'itens': []},
        'Deposit': {'total': 0.0, 'qtd': 0, 'itens': []},
        'Other': {'total': 0.0, 'qtd': 0, 'itens': []}
    }
    
    total_dia = 0.0
    itens_todos = []
    
    for t in transacoes:
        v_total = float(t.valor)
        total_dia += v_total
        
        detalhes = None
        if t.detalhes_pagamento_json:
            try:
                detalhes = json.loads(t.detalhes_pagamento_json)
            except Exception:
                detalhes = None
                
        hora_fmt = t.data_pagamento.strftime('%H:%M') if t.data_pagamento else '--:--'
        base_item = {
            'id': t.id,
            'id_contrato': t.id_contrato,
            'cliente': t.contrato.cliente.nome if (t.contrato and t.contrato.cliente) else 'Unknown',
            'placa': t.contrato.placa if t.contrato else '-',
            'tipo': obter_descricao_recibo_simples(t.tipo),
            'hora': hora_fmt,
            'nota': t.nota or '',
            'registrado_por': t.registrado_por_nome or ''
        }
        
        if detalhes and isinstance(detalhes, list) and len(detalhes) > 0:
            for d in detalhes:
                forma = (d.get('forma') or 'Other').strip()
                v_parte = float(d.get('valor') or 0.0)
                
                key = 'Other'
                forma_lower = forma.lower()
                if 'cash' in forma_lower or 'dinheiro' in forma_lower:
                    key = 'Cash'
                elif 'card' in forma_lower or 'cartao' in forma_lower or 'cartão' in forma_lower:
                    key = 'Card'
                elif 'transfer' in forma_lower or 'bank' in forma_lower or 'banco' in forma_lower:
                    key = 'Bank Transfer'
                elif 'exchange' in forma_lower or 'trade' in forma_lower or 'troca' in forma_lower:
                    key = 'Exchange'
                elif 'deposit' in forma_lower or 'deposito' in forma_lower or 'depósito' in forma_lower:
                    key = 'Deposit'
                    
                metodos_resumo[key]['total'] += v_parte
                metodos_resumo[key]['qtd'] += 1
                item_copy = dict(base_item)
                item_copy['valor'] = v_parte
                item_copy['forma_especifica'] = forma
                metodos_resumo[key]['itens'].append(item_copy)
                itens_todos.append(item_copy)
        else:
            forma = (t.forma_pagamento or 'Cash').strip()
            key = 'Other'
            forma_lower = forma.lower()
            if 'cash' in forma_lower or 'dinheiro' in forma_lower:
                key = 'Cash'
            elif 'card' in forma_lower or 'cartao' in forma_lower or 'cartão' in forma_lower:
                key = 'Card'
            elif 'transfer' in forma_lower or 'bank' in forma_lower or 'banco' in forma_lower:
                key = 'Bank Transfer'
            elif 'exchange' in forma_lower or 'trade' in forma_lower or 'troca' in forma_lower:
                key = 'Exchange'
            elif 'deposit' in forma_lower or 'deposito' in forma_lower or 'depósito' in forma_lower:
                key = 'Deposit'
                
            metodos_resumo[key]['total'] += v_total
            metodos_resumo[key]['qtd'] += 1
            item_copy = dict(base_item)
            item_copy['valor'] = v_total
            item_copy['forma_especifica'] = forma
            metodos_resumo[key]['itens'].append(item_copy)
            itens_todos.append(item_copy)

    for k in metodos_resumo:
        metodos_resumo[k]['total'] = round(metodos_resumo[k]['total'], 2)

    operador_nome = current_user.nome if (current_user and current_user.is_authenticated) else 'Duty Staff'
    registrar_log(
        'CASH_CLOSING_PRINTED',
        'Finance',
        target_date.strftime('%Y-%m-%d'),
        f"Folha de fechamento de caixa diário ({target_date.strftime('%d/%m/%Y')}) gerada/impressa por {operador_nome}. Total arrecadado: £{total_dia:.2f} ({len(transacoes)} recebimentos)."
    )

    return render_template(
        'relatorio_fechamento_caixa.html',
        data_formatada=target_date.strftime('%d/%m/%Y'),
        data_iso=target_date.strftime('%Y-%m-%d'),
        data_geracao=get_london_now().strftime('%d/%m/%Y %H:%M'),
        total_arrecadado=round(total_dia, 2),
        total_transacoes=len(transacoes),
        metodos=metodos_resumo,
        itens=itens_todos,
        operador=operador_nome
    )


@app.route('/api/financeiro/nova-cobranca', methods=['POST'])
@alugueis_required
def criar_cobranca_avulsa():
    data = request.get_json() or {}
    id_contrato = data.get('id_contrato')
    tipo = (data.get('tipo') or '').strip()
    valor_raw = data.get('valor')
    data_venc_str = (data.get('data_vencimento') or '').strip()
    nota = (data.get('nota') or '').strip() or None
    
    if not id_contrato or not tipo or not valor_raw or not data_venc_str:
        return jsonify({'error': 'All fields (contract, type, amount, due date) are required.', 'erro': 'Campos obrigatórios ausentes.'}), 400
        
    contrato = db.session.get(Contract, id_contrato)
    if not contrato:
        return jsonify({'error': 'Contract not found.', 'erro': 'Contrato não encontrado.'}), 404
        
    try:
        valor = round(float(valor_raw), 2)
        if valor <= 0:
            return jsonify({'error': 'Amount must be greater than zero.', 'erro': 'O valor deve ser maior que zero.'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid amount.', 'erro': 'Valor inválido.'}), 400
        
    try:
        data_vencimento = datetime.strptime(data_venc_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({'error': 'Invalid due date format (YYYY-MM-DD).', 'erro': 'Formato de data inválido.'}), 400
        
    tipo_map = {
        'fine': TransactionType.FINE.value,
        'damage': TransactionType.DAMAGE.value,
        'rent': TransactionType.RENT.value,
        'deposit': TransactionType.DEPOSIT.value,
        'admin_fee': 'Admin_Fee',
        'extra': 'Accessory_Extra',
        'other': 'Other'
    }
    tipo_final = tipo_map.get(tipo.lower(), tipo)
    
    nova = FinancialTransaction(
        id_contrato=contrato.id,
        tipo=tipo_final,
        valor=valor,
        data_vencimento=data_vencimento,
        status=TransactionStatus.PENDING.value,
        nota=nota
    )
    db.session.add(nova)
    sync_sale_contract_status(contrato)
    db.session.commit()
    
    operador = current_user.nome if (current_user and current_user.is_authenticated) else 'Staff'
    nota_log = f" (Nota: '{nota}')" if nota else ""
    registrar_log('CREATE_CHARGE', 'Transaction', nova.id, f"Cobrança avulsa de £{valor:.2f} ({tipo_final}) criada por {operador} para Contrato #{contrato.id}{nota_log}")
    
    return jsonify({
        'message': 'Charge created successfully',
        'mensagem': 'Cobrança criada com sucesso',
        'id': nova.id
    }), 201

@app.route('/api/financeiro/exportar-csv', methods=['GET'])
@financeiro_required
def exportar_financeiro_csv():
    import io
    import csv
    
    search = request.args.get('search', '', type=str)
    contrato_id = request.args.get('contrato_id', None, type=int)
    cliente_id = request.args.get('cliente_id', None, type=int)
    placa_filtro = request.args.get('placa', '', type=str).strip()
    status_filtro = request.args.get('status', '', type=str)
    tipo_filtro = request.args.get('tipo', '', type=str)
    metodo_filtro = request.args.get('metodo', '', type=str).strip()
    pendentes = request.args.get('pendentes') == 'true'
    data_inicio = request.args.get('data_inicio', '', type=str).strip()
    data_fim = request.args.get('data_fim', '', type=str).strip()
    campo_data = request.args.get('campo_data', '', type=str).strip().lower()
    if not campo_data:
        if status_filtro and status_filtro.lower() in ['paid', 'pago']:
            campo_data = 'pagamento'
        else:
            campo_data = 'vencimento'
    elif campo_data == 'pagamento' and (status_filtro in ['overdue', 'vencidos', 'vencido', 'pending', 'pendente'] or pendentes):
        campo_data = 'vencimento'
    
    query = FinancialTransaction.query.outerjoin(Contract, FinancialTransaction.id_contrato == Contract.id).outerjoin(Client, Contract.id_cliente == Client.id)
    if contrato_id:
        query = query.filter(FinancialTransaction.id_contrato == contrato_id)
    if cliente_id:
        query = query.filter(Contract.id_cliente == cliente_id)
    if placa_filtro:
        placa_clean = placa_filtro.replace(' ', '')
        query = query.filter(db.or_(Contract.placa.ilike(placa_clean), Contract.placa.ilike(placa_filtro)))
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
            FinancialTransaction.nota.ilike(search_term),
            FinancialTransaction.valor.cast(db.String).ilike(search_term),
            Contract.placa.ilike(search_plate_term),
            Contract.placa.ilike(search_term),
            Client.nome.ilike(search_term)
        ))
        
    if status_filtro:
        if status_filtro.lower() in ['overdue', 'vencidos', 'vencido']:
            inicio_hoje = get_london_now().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
            query = query.filter(
                FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
                FinancialTransaction.data_vencimento < inicio_hoje
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

    if metodo_filtro:
        query = query.filter(FinancialTransaction.forma_pagamento.ilike(f"%{metodo_filtro}%"))

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

    transacoes = query.order_by(FinancialTransaction.data_vencimento.desc()).all()
    
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    
    writer.writerow([
        'Transaction ID', 'Contract ID', 'Customer Name', 'Customer Phone', 'Motorbike Reg',
        'Type', 'Description', 'Amount (£)', 'Due Date', 'Payment Date', 'Status',
        'Payment Method', 'Payment Note / Reference', 'Registered By'
    ])
    
    for t in transacoes:
        cli_nome = t.contrato.cliente.nome if (t.contrato and t.contrato.cliente) else ''
        cli_tel = t.contrato.cliente.telefone if (t.contrato and t.contrato.cliente) else ''
        placa = t.contrato.placa if t.contrato else ''
        dt_venc = t.data_vencimento.strftime('%d/%m/%Y') if t.data_vencimento else ''
        dt_pag = t.data_pagamento.strftime('%d/%m/%Y %H:%M') if t.data_pagamento else ''
        desc = obter_descricao_recibo_simples(t.tipo)
        
        writer.writerow([
            t.id,
            t.id_contrato,
            cli_nome,
            cli_tel,
            placa,
            t.tipo,
            desc,
            f"{float(t.valor):.2f}",
            dt_venc,
            dt_pag,
            t.status,
            t.forma_pagamento or '',
            t.nota or '',
            t.registrado_por_nome or ''
        ])
        
    csv_bytes = output.getvalue().encode('utf-8')
    filename = f"ffmotors_financial_{get_london_date().strftime('%Y%m%d')}.csv"
    
    return Response(
        csv_bytes,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route('/financeiro/relatorio-pdf', methods=['GET'])
@financeiro_required
def relatorio_financeiro_pdf():
    try:
        search = request.args.get('search', '', type=str)
        contrato_id = request.args.get('contrato_id', None, type=int)
        cliente_id = request.args.get('cliente_id', None, type=int)
        placa_filtro = request.args.get('placa', '', type=str).strip()
        status_filtro = request.args.get('status', '', type=str)
        tipo_filtro = request.args.get('tipo', '', type=str)
        metodo_filtro = request.args.get('metodo', '', type=str).strip()
        pendentes = request.args.get('pendentes') == 'true'
        data_inicio = request.args.get('data_inicio', '', type=str).strip()
        data_fim = request.args.get('data_fim', '', type=str).strip()
        campo_data = request.args.get('campo_data', '', type=str).strip().lower()
        if not campo_data:
            if status_filtro and status_filtro.lower() in ['paid', 'pago']:
                campo_data = 'pagamento'
            else:
                campo_data = 'vencimento'
        elif campo_data == 'pagamento' and (status_filtro in ['overdue', 'vencidos', 'vencido', 'pending', 'pendente'] or pendentes):
            campo_data = 'vencimento'
        
        query = FinancialTransaction.query.outerjoin(
            Contract, FinancialTransaction.id_contrato == Contract.id
        ).outerjoin(
            Client, Contract.id_cliente == Client.id
        ).options(
            contains_eager(FinancialTransaction.contrato).contains_eager(Contract.cliente)
        )

        if contrato_id:
            query = query.filter(FinancialTransaction.id_contrato == contrato_id)
        if cliente_id:
            query = query.filter(Contract.id_cliente == cliente_id)
        if placa_filtro:
            placa_clean = placa_filtro.replace(' ', '')
            query = query.filter(db.or_(Contract.placa.ilike(placa_clean), Contract.placa.ilike(placa_filtro)))
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
                FinancialTransaction.nota.ilike(search_term),
                FinancialTransaction.valor.cast(db.String).ilike(search_term),
                Contract.placa.ilike(search_plate_term),
                Contract.placa.ilike(search_term),
                Client.nome.ilike(search_term)
            ))
            
        hoje_london_date = get_london_date()
        inicio_hoje = datetime.combine(hoje_london_date, datetime.min.time())
        
        if status_filtro:
            if status_filtro.lower() in ['overdue', 'vencidos', 'vencido']:
                query = query.filter(
                    FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
                    FinancialTransaction.data_vencimento < inicio_hoje
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

        if metodo_filtro:
            query = query.filter(FinancialTransaction.forma_pagamento.ilike(f"%{metodo_filtro}%"))

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

        if campo_data == 'pagamento':
            transacoes_raw = query.order_by(FinancialTransaction.data_pagamento.desc()).all()
        else:
            transacoes_raw = query.order_by(FinancialTransaction.data_vencimento.asc()).all()
        
        tot_val = 0.0
        tot_pago = 0.0
        tot_pendente = 0.0
        tot_overdue = 0.0
        
        lista = []
        for t in transacoes_raw:
            val = float(t.valor or 0.0)
            tot_val += val
            
            st_lower = (t.status or '').strip().lower()
            is_paid = st_lower in ['paid', 'pago']
            is_pending = st_lower in ['pending', 'pendente']
            
            venc_date = None
            if t.data_vencimento:
                if isinstance(t.data_vencimento, datetime):
                    if t.data_vencimento.tzinfo is not None:
                        venc_date = t.data_vencimento.astimezone(LONDON_TZ).date()
                    else:
                        venc_date = t.data_vencimento.date()
                elif isinstance(t.data_vencimento, date):
                    venc_date = t.data_vencimento

            is_overdue = is_pending and (venc_date is not None and venc_date < hoje_london_date)
            
            if is_paid:
                tot_pago += val
            elif is_overdue:
                tot_overdue += val
                tot_pendente += val
            elif is_pending:
                tot_pendente += val
                
            cli_nome = ''
            cli_tel = ''
            placa = ''
            if t.contrato:
                placa = t.contrato.placa or ''
                if t.contrato.cliente:
                    cli_nome = t.contrato.cliente.nome or ''
                    cli_tel = t.contrato.cliente.telefone or ''
                elif getattr(t.contrato, 'cliente_nome', None):
                    cli_nome = t.contrato.cliente_nome or ''
                    cli_tel = getattr(t.contrato, 'cliente_telefone', '') or ''

            dt_venc_fmt = '-'
            if t.data_vencimento:
                if isinstance(t.data_vencimento, (datetime, date)):
                    dt_venc_fmt = t.data_vencimento.strftime('%d/%m/%Y')
                else:
                    dt_venc_fmt = str(t.data_vencimento)[:10]

            dt_pag_fmt = None
            if t.data_pagamento:
                if isinstance(t.data_pagamento, datetime):
                    dt_pag_fmt = t.data_pagamento.strftime('%d/%m/%Y %H:%M')
                elif isinstance(t.data_pagamento, date):
                    dt_pag_fmt = t.data_pagamento.strftime('%d/%m/%Y')
                else:
                    dt_pag_fmt = str(t.data_pagamento)[:16]

            lista.append({
                'id': t.id,
                'id_contrato': t.id_contrato,
                'cliente': cli_nome,
                'cliente_telefone': cli_tel,
                'placa': placa,
                'tipo': t.tipo,
                'descricao': obter_descricao_recibo_simples(t.tipo),
                'valor': val,
                'data_vencimento_fmt': dt_venc_fmt,
                'data_pagamento_fmt': dt_pag_fmt,
                'status': t.status,
                'forma_pagamento': t.forma_pagamento,
                'nota': t.nota,
                'id_transacao_origem': t.id_transacao_origem,
                'is_overdue': is_overdue
            })
            
        totais = {
            'total_count': len(transacoes_raw),
            'total_valor': round(tot_val, 2),
            'total_pago': round(tot_pago, 2),
            'total_pendente': round(tot_pendente, 2),
            'total_overdue': round(tot_overdue, 2)
        }

        filtro_desc = []
        if status_filtro: filtro_desc.append(f"Status: {markupsafe.escape(status_filtro)}")
        elif pendentes: filtro_desc.append("Status: Pending")
        if tipo_filtro: filtro_desc.append(f"Type: {markupsafe.escape(tipo_filtro)}")
        if metodo_filtro: filtro_desc.append(f"Method: {markupsafe.escape(metodo_filtro)}")
        nome_campo = "Payment Date" if campo_data == 'pagamento' else "Due Date"
        if data_inicio or data_fim: filtro_desc.append(f"Date ({nome_campo}): {markupsafe.escape(data_inicio or 'Any')} to {markupsafe.escape(data_fim or 'Any')}")
        if search: filtro_desc.append(f"Search: '{markupsafe.escape(search)}'")
        filtro_label = " &bull; ".join(str(f) for f in filtro_desc) if filtro_desc else "All Transactions"

        return render_template(
            'relatorio_financeiro.html',
            transacoes=lista,
            totais=totais,
            filtro_ativo=filtro_label,
            data_geracao=get_london_now().strftime('%d/%m/%Y %H:%M'),
            operador=current_user.nome if (current_user and current_user.is_authenticated) else 'Staff'
        )
    except Exception as e:
        app.logger.error(f"[relatorio_financeiro_pdf Error]: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        raise


@app.route('/api/financeiro/pagar/<int:id>', methods=['POST', 'PUT'])
@alugueis_required
def pagar_transacao(id):
    t = db.session.get(FinancialTransaction, id)
    if not t:
        return jsonify({'error': 'Transaction not found', 'erro': 'Transação não encontrada'}), 404
        
    if t.status in [TransactionStatus.PAID.value, 'Paid', 'Pago']:
        return jsonify({'error': 'Transaction is already paid', 'erro': 'Esta transação já está paga'}), 400

    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    valor_devido = round(float(t.valor), 2)
    
    # Process payment payload (supports split payment methods list and single method fallback)
    data = {}
    if request.is_json and request.json:
        data = request.json
    elif request.form:
        data = request.form.to_dict()

    metodos_brutos = data.get('metodos_pagamento')
    metodos_validos = []
    
    if metodos_brutos is not None and isinstance(metodos_brutos, list):
        for item in metodos_brutos:
            if not isinstance(item, dict):
                continue
            forma = str(item.get('forma') or '').strip()
            try:
                v = round(float(item.get('valor', 0)), 2)
            except (ValueError, TypeError):
                v = 0.0
            if forma and v > 0:
                metodos_validos.append({'forma': forma, 'valor': v})
    elif 'forma_pagamento' in data or 'forma' in data:
        forma = str(data.get('forma_pagamento') or data.get('forma') or 'Cash').strip()
        try:
            v = round(float(data.get('valor_pago', valor_devido)), 2)
        except (ValueError, TypeError):
            v = valor_devido
        if forma and v > 0:
            metodos_validos.append({'forma': forma, 'valor': v})
    else:
        metodos_validos = [{'forma': 'Cash', 'valor': valor_devido}]

    valor_pago = round(sum(m['valor'] for m in metodos_validos), 2)

    if valor_pago <= 0:
        return jsonify({'error': 'Payment amount must be greater than zero', 'erro': 'O valor pago deve ser maior que zero'}), 400

    if valor_pago > valor_devido + 0.009:
        return jsonify({
            'error': f'Payment amount (£{valor_pago:.2f}) cannot exceed the amount due (£{valor_devido:.2f})',
            'erro': f'O valor pago (£{valor_pago:.2f}) não pode exceder o valor devido (£{valor_devido:.2f})'
        }), 400

    saldo_restante = round(valor_devido - valor_pago, 2)
    is_parcial = saldo_restante > 0.009

    # Generate consolidated forma_pagamento string
    if len(metodos_validos) == 1:
        forma_pagamento_consolidada = metodos_validos[0]['forma']
    else:
        forma_pagamento_consolidada = " + ".join([f"{m['forma']} (£{m['valor']:.2f})" for m in metodos_validos])

    detalhes_json = json.dumps(metodos_validos)

    nota_pag = str(data.get('nota') or '').strip() or None

    # 1. Update current transaction as PAID
    t.valor = valor_pago
    t.status = TransactionStatus.PAID.value
    t.data_pagamento = get_local_now()
    t.forma_pagamento = forma_pagamento_consolidada
    t.detalhes_pagamento_json = detalhes_json
    t.nota_pagamento = nota_pag
    if nota_pag:
        t.nota = f"{t.nota} | {nota_pag}" if t.nota else nota_pag
    elif not t.nota and t.id_vistoria and t.vistoria and t.vistoria.observacoes:
        t.nota = t.vistoria.observacoes
    t.registrado_por_nome = operador_atual

    # 2. If partial payment, generate child transaction for the remaining balance
    t_restante = None
    nota_log = f" (Nota: {nota_pag})" if nota_pag else ""
    if is_parcial:
        t_restante = FinancialTransaction(
            id_contrato=t.id_contrato,
            tipo=t.tipo,
            data_vencimento=t.data_vencimento,
            valor=saldo_restante,
            status=TransactionStatus.PENDING.value,
            forma_pagamento=None,
            detalhes_pagamento_json=None,
            nota=t.nota.split(' | ')[0] if (t.nota and ' | ' in t.nota) else t.nota,
            nota_pagamento=None,
            url_anexos=t.url_anexos,
            id_vistoria=t.id_vistoria,
            registrado_por_nome=operador_atual,
            id_transacao_origem=t.id
        )
        db.session.add(t_restante)
        db.session.flush()

        registrar_log(
            'PAYMENT_RECEIVED', 
            'Transaction', 
            t.id, 
            f"Baixa PARCIAL de £{valor_pago:.2f} ({t.tipo}) confirmada via {forma_pagamento_consolidada} por {operador_atual} no Contrato #{t.id_contrato}. Saldo restante de £{saldo_restante:.2f} lançado na transação #{t_restante.id}.{nota_log}"
        )
    else:
        registrar_log(
            'PAYMENT_RECEIVED', 
            'Transaction', 
            t.id, 
            f"Baixa de £{valor_pago:.2f} ({t.tipo}) confirmada via {forma_pagamento_consolidada} por {operador_atual} no Contrato #{t.id_contrato}.{nota_log}"
        )

        # Sincronização do status para contratos de venda
        if t.contrato:
            sync_sale_contract_status(t.contrato)

    db.session.commit()

    return jsonify({
        'message': 'Payment marked successfully' if not is_parcial else 'Partial payment recorded successfully',
        'mensagem': 'Baixa realizada com sucesso' if not is_parcial else 'Pagamento parcial registrado com sucesso',
        'forma_pagamento': t.forma_pagamento,
        'valor_pago': valor_pago,
        'saldo_restante': saldo_restante,
        'is_partial': is_parcial,
        'id_restante': t_restante.id if t_restante else None,
        'registrado_por_nome': t.registrado_por_nome
    }), 200

@app.route('/api/financeiro/<int:id>/reverter', methods=['POST', 'PUT'])
@app.route('/api/financeiro/reverter/<int:id>', methods=['POST', 'PUT'])
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
    valor_anterior = float(t.valor)
    data_anterior = t.data_pagamento.strftime('%d/%m/%Y %H:%M') if t.data_pagamento else 'N/A'
    
    # Se gerou um saldo restante que ainda está pendente, reintegra o saldo e remove a filha
    filha_pendente = FinancialTransaction.query.filter_by(
        id_transacao_origem=t.id, 
        status=TransactionStatus.PENDING.value
    ).first()
    
    if filha_pendente:
        valor_restante = float(filha_pendente.valor)
        t.valor = round(valor_anterior + valor_restante, 2)
        db.session.delete(filha_pendente)
        registrar_log(
            'TRANSACTION_MERGED',
            'Transaction',
            t.id,
            f"Saldo restante de £{valor_restante:.2f} (Transação #{filha_pendente.id}) foi reintegrado à Transação #{t.id} devido a estorno."
        )

    # Revert to PENDING
    t.status = TransactionStatus.PENDING.value
    t.data_pagamento = None
    t.forma_pagamento = None
    t.detalhes_pagamento_json = None
    t.nota_pagamento = None
    if t.nota and ' | ' in t.nota:
        t.nota = t.nota.split(' | ')[0].strip()
    elif not t.nota and t.id_vistoria and t.vistoria and t.vistoria.observacoes:
        t.nota = t.vistoria.observacoes
    t.registrado_por_nome = None

    # Sincronização do status para contratos de venda (reabre para Active se houver pendência)
    if t.contrato:
        sync_sale_contract_status(t.contrato)

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
        'status': t.status,
        'valor': float(t.valor)
    }), 200

def obter_descricao_recibo(t, contrato=None):
    if not t:
        return ""
    tipo = str(t.tipo or '').strip()
    tipo_lower = tipo.lower()
    
    desc = ""
    if tipo_lower in ['sale_full', 'venda_vista']:
        desc = "Vehicle Sale - Full Payment"
    elif tipo_lower in ['sale_deposit', 'venda_entrada']:
        desc = "Vehicle Sale - Down Payment (Deposit)"
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
                        desc = f"Vehicle Sale - Instalment {idx} of {total}"
                        break
            except Exception:
                pass
        if not desc:
            desc = "Vehicle Sale - Instalment Payment"
    elif tipo_lower in ['rent', 'aluguel']:
        desc = "Vehicle Rental Payment"
    elif tipo_lower in ['deposit', 'deposito']:
        desc = "Rental Security Deposit (Refundable)"
    elif tipo_lower in ['deposit_refund', 'devolucao_deposito']:
        desc = "Security Deposit Refund"
    elif tipo_lower in ['fine', 'multa']:
        desc = "Traffic / Penalty Charge Notice (PCN)"
    elif tipo_lower in ['damage', 'dano']:
        desc = "Vehicle Damage Repair Charge"
    elif tipo_lower in ['other', 'outro']:
        desc = "Additional Charge"
    else:
        desc = tipo.replace('_', ' ').title()

    if getattr(t, 'id_transacao_origem', None):
        desc += " (Remaining Balance)"
    
    return desc

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
    detalhes_pagamento = json.loads(t.detalhes_pagamento_json) if t.detalhes_pagamento_json else None
    return render_template('recibo.html', transacao=t, contrato=contrato, cliente=cliente, descricao=descricao, detalhes_pagamento=detalhes_pagamento)

@app.route('/api/financeiro/<int:id>', methods=['DELETE'])
@alugueis_required
def excluir_transacao(id):
    t = db.session.get(FinancialTransaction, id)
    if not t:
        return jsonify({'error': 'Transaction not found', 'erro': 'Transação não encontrada'}), 404
        
    if t.status in [TransactionStatus.PAID.value, 'Paid', 'Pago']:
        return jsonify({'error': 'Cannot delete an already paid transaction', 'erro': 'Não é possível excluir uma transação já paga'}), 400
        
    id_contrato = t.id_contrato
    valor_t = float(t.valor or 0.0)
    tipo_t = t.tipo
    venc_t = t.data_vencimento.strftime('%d/%m/%Y') if t.data_vencimento else 'N/A'
    placa_t = t.contrato.placa if t.contrato else 'N/A'
    cli_t = (t.contrato.cliente.nome if (t.contrato and t.contrato.cliente) else (t.contrato.cliente_nome if t.contrato else 'N/A')) or 'N/A'
    nota_t = f" (Nota: '{t.nota}')" if t.nota else ""

    db.session.delete(t)
    if id_contrato:
        sync_sale_contract_status(id_contrato)
    db.session.commit()
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('TRANSACTION_DELETE', 'Transaction', id, f"Transação #{id} de £{valor_t:.2f} ({tipo_t}, Venc: {venc_t}) do Contrato #{id_contrato or 'N/A'} (Placa: {placa_t}, Cliente: {cli_t}) excluída por {operador_atual}{nota_t}")
    return jsonify({'message': 'Transaction deleted successfully', 'mensagem': 'Transação excluída com sucesso'}), 200

@app.route('/api/busca-rapida', methods=['GET'])
@alugueis_required
def busca_rapida():
    termo = request.args.get('q', '', type=str).strip()
    termo_limpo = termo.replace(' ', '').replace('#', '')
    if not termo or (len(termo) < 2 and not termo_limpo.isdigit()):
        return jsonify({'motos': [], 'clientes': [], 'contratos': []})

    like_termo = f"%{termo}%"
    like_limpo = f"%{termo_limpo}%"

    # 1. Search Motorbikes (plates, model, color)
    exact_moto = Motorcycle.query.options(
        selectinload(Motorcycle.contratos).selectinload(Contract.cliente)
    ).filter(Motorcycle.placa.ilike(termo_limpo)).first()

    motos_query = Motorcycle.query.options(
        selectinload(Motorcycle.contratos).selectinload(Contract.cliente)
    ).filter(
        db.or_(
            Motorcycle.placa.ilike(like_limpo),
            Motorcycle.placa.ilike(like_termo),
            Motorcycle.modelo.ilike(like_termo),
            Motorcycle.cor.ilike(like_termo)
        )
    ).limit(8).all()

    motos_res = []
    seen_plates = set()

    all_motos = ([exact_moto] if exact_moto else []) + [m for m in motos_query if not exact_moto or m.placa != exact_moto.placa]
    for m in all_motos:
        if m.placa in seen_plates:
            continue
        contratos_sorted = sorted(m.contratos, key=lambda x: x.id, reverse=True) if m.contratos else []
        active_c = next((c for c in contratos_sorted if c.status in [ContractStatus.ACTIVE.value, 'Active', 'Ativo', ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold']), None)
        hirer_name = None
        hirer_tel = None
        contract_id = None
        contract_type = None
        if active_c:
            hirer_name = (active_c.cliente.nome if active_c.cliente else active_c.cliente_nome) or 'N/A'
            hirer_tel = (active_c.cliente.telefone if active_c.cliente else active_c.cliente_telefone) or ''
            contract_id = active_c.id
            contract_type = getattr(active_c, 'tipo_contrato', 'Rent') or 'Rent'

        motos_res.append({
            'placa': m.placa,
            'modelo': m.modelo,
            'cor': m.cor or '',
            'status': m.status,
            'contract_id': contract_id,
            'contrato_ativo_id': contract_id,
            'contract_type': contract_type,
            'hirer_name': hirer_name,
            'cliente_atual': hirer_name,
            'hirer_telefone': hirer_tel or '',
            'milhagem': int(m.milhagem_atual or 0)
        })
        seen_plates.add(m.placa)
        if len(motos_res) >= 6:
            break

    # 2. Search Clients (name, phone, email)
    clientes_query = Client.query.options(
        selectinload(Client.contratos).selectinload(Contract.moto)
    ).filter(
        db.or_(
            Client.nome.ilike(like_termo),
            Client.telefone.ilike(like_termo),
            Client.email.ilike(like_termo)
        )
    ).limit(6).all()

    clientes_res = []
    for c in clientes_query:
        contratos_sorted = sorted(c.contratos, key=lambda x: x.id, reverse=True) if c.contratos else []
        active_c = next((ct for ct in contratos_sorted if ct.status in [ContractStatus.ACTIVE.value, 'Active', 'Ativo', ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold']), None)
        c_id = active_c.id if active_c else None
        placa = active_c.placa if active_c else None
        c_tipo = getattr(active_c, 'tipo_contrato', 'Rent') if active_c else None

        clientes_res.append({
            'id': c.id,
            'nome': c.nome,
            'telefone': c.telefone or '',
            'email': c.email or '',
            'contract_id': c_id,
            'contrato_ativo_id': c_id,
            'moto_placa': placa,
            'contract_type': c_tipo
        })

    # 3. Search Contracts (ID, plate, client name, type)
    exact_contract = None
    if termo_limpo.isdigit():
        exact_contract = Contract.query.options(joinedload(Contract.cliente)).filter(Contract.id == int(termo_limpo)).first()

    contratos_filters = [
        Contract.placa.ilike(like_limpo),
        Contract.placa.ilike(like_termo)
    ]
    if termo_limpo.isdigit():
        contratos_filters.append(Contract.id == int(termo_limpo))
    
    contratos_query = Contract.query.options(
        joinedload(Contract.cliente)
    ).join(Client, Contract.id_cliente == Client.id).filter(
        db.or_(
            *contratos_filters,
            Client.nome.ilike(like_termo),
            Contract.status.ilike(like_termo),
            Contract.tipo_contrato.ilike(like_termo)
        )
    ).order_by(Contract.id.desc()).limit(8).all()

    contratos_res = []
    seen_contract_ids = set()

    if exact_contract:
        cli_nome = (exact_contract.cliente.nome if exact_contract.cliente else exact_contract.cliente_nome) or 'N/A'
        contratos_res.append({
            'id': exact_contract.id,
            'tipo': exact_contract.tipo_contrato or 'Rent',
            'placa': exact_contract.placa,
            'cliente': cli_nome,
            'status': exact_contract.status,
            'valor': float(exact_contract.valor_aluguel_semanal or 0.0) if exact_contract.tipo_contrato in [None, 'Rent', ContractType.RENT.value] else float(exact_contract.valor_total_venda or exact_contract.valor_compra_veiculo or 0.0)
        })
        seen_contract_ids.add(exact_contract.id)

    for ct in contratos_query:
        if ct.id in seen_contract_ids:
            continue
        cli_nome = (ct.cliente.nome if ct.cliente else ct.cliente_nome) or 'N/A'
        contratos_res.append({
            'id': ct.id,
            'tipo': ct.tipo_contrato or 'Rent',
            'placa': ct.placa,
            'cliente': cli_nome,
            'status': ct.status,
            'valor': float(ct.valor_aluguel_semanal or 0.0) if ct.tipo_contrato in [None, 'Rent', ContractType.RENT.value] else float(ct.valor_total_venda or ct.valor_compra_veiculo or 0.0)
        })
        seen_contract_ids.add(ct.id)
        if len(contratos_res) >= 6:
            break

    return jsonify({
        'motos': motos_res,
        'clientes': clientes_res,
        'contratos': contratos_res
    })

def _compilar_dados_claims_dashboard():
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

    return {
        'claims_alerts': {
            'indicacoes_vencidas': ind_vencidas,
            'storage_28d_vencendo': stor_28d,
            'invoices_vencidos': inv_vencidos,
            'invoices_pendentes_envio': inv_pendentes_envio,
            'total_alertas': ind_vencidas + stor_28d + inv_vencidos + inv_pendentes_envio
        }
    }

def _compilar_dados_dashboard(include_claims=False):
    """
    Compila todas as métricas essenciais de operação, frota, financeiro e conformidade do Dashboard.
    Reutilizado pelo endpoint /api/dashboard e pela rotina de warm-up matinal /api/jobs/warmup.
    """
    resp_data = {}

    motos_disponiveis = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.AVAILABLE.value, 'Available', 'Disponível'])).count()
    motos_alugadas = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.RENTED.value, 'Rented', 'Alugada'])).count()
    motos_manutencao = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.MAINTENANCE.value, 'Maintenance', 'Manutenção', 'Manutencao'])).count()
    motos_pound = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.POUND.value, 'Pound'])).count()
    motos_vendidas = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.SOLD.value, 'Sold', 'Vendida'])).count()
    # Total Fleet = frota ativa operacional (disponíveis + alugadas + manutenção; exclui vendidas e pound)
    total_motos = Motorcycle.query.filter(~Motorcycle.status.in_([MotoStatus.SOLD.value, 'Sold', 'Vendida', MotoStatus.POUND.value, 'Pound'])).count()
    
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
        
    # Performance: Single query for active contracts with eager-loaded clients and inspections (reused in askMID compliance & pre-delivery checks)
    contratos_ativos_objs = db.session.query(Contract).options(
        joinedload(Contract.cliente),
        selectinload(Contract.vistorias)
    ).filter(Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo'])).all()
    contratos_ativos = len(contratos_ativos_objs)
    receita_semanal = sum(float(c.valor_aluguel_semanal) for c in contratos_ativos_objs)
    
    # Breakdown of agreements by business model (Rental vs Financed/Rent-to-Buy vs Outright Sold)
    motos_rental = 0
    motos_financed = 0
    motos_sold_outright = 0

    sold_motos_objs = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.SOLD.value, 'Sold', 'Vendida'])).all()
    for m in sold_motos_objs:
        c = next((ca for ca in contratos_ativos_objs if ca.placa == m.placa), None)
        if c and c.tipo_contrato in [ContractType.SALE_INSTALLMENT.value, 'Sale_Installment']:
            motos_financed += 1
        elif c and c.tipo_contrato in [ContractType.SALE_FULL.value, 'Sale_Full']:
            motos_financed += 1
        else:
            motos_sold_outright += 1

    rented_motos_objs = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.RENTED.value, 'Rented', 'Alugada'])).all()
    for m in rented_motos_objs:
        c = next((ca for ca in contratos_ativos_objs if ca.placa == m.placa), None)
        if c and c.tipo_contrato in [ContractType.SALE_INSTALLMENT.value, 'Sale_Installment']:
            motos_financed += 1
        else:
            motos_rental += 1

    # Total Fleet = frota ativa operacional no nome da loja (disponíveis + alugadas + parceladas/vendas com contrato ativo + manutenção; exclui apenas vendidas com contrato completado e pound)
    total_motos = motos_disponiveis + motos_rental + motos_financed + motos_manutencao

    total_clientes = Client.query.count()
    
    # Performance: Direct SQL sum for pending revenue
    receita_pendente = float(db.session.query(
        db.func.coalesce(db.func.sum(FinancialTransaction.valor), 0.0)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
        FinancialTransaction.tipo.in_([TransactionType.RENT.value, TransactionType.FINE.value, 'Rent', 'Fine', 'Aluguel', 'Multa'])
    ).scalar() or 0.0)
    
    # Performance: Direct SQL sum and count for overdue charges using London Time
    agora_london = get_london_now()
    inicio_hoje = agora_london.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    inicio_semana = inicio_hoje - timedelta(days=agora_london.weekday())

    collected_today = float(db.session.query(
        db.func.coalesce(db.func.sum(FinancialTransaction.valor), 0.0)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PAID.value, 'Paid', 'Pago']),
        FinancialTransaction.data_pagamento >= inicio_hoje
    ).scalar() or 0.0)

    collected_this_week = float(db.session.query(
        db.func.coalesce(db.func.sum(FinancialTransaction.valor), 0.0)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PAID.value, 'Paid', 'Pago']),
        FinancialTransaction.data_pagamento >= inicio_semana
    ).scalar() or 0.0)

    vencidas_q = db.session.query(
        db.func.coalesce(db.func.sum(FinancialTransaction.valor), 0.0),
        db.func.count(FinancialTransaction.id)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
        FinancialTransaction.data_vencimento < inicio_hoje
    ).first()
    receita_vencida = float(vencidas_q[0]) if vencidas_q else 0.0
    total_vencidos = int(vencidas_q[1]) if vencidas_q else 0
    
    # Performance: Pre-fetch transactions to prevent N+1 queries during deposit accounting
    contratos_com_deposito = db.session.query(Contract).options(selectinload(Contract.transacoes)).filter(
        Contract.status.in_([
            ContractStatus.ACTIVE.value, 'Active', 'Ativo',
            ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito'
        ]),
        (Contract.tipo_contrato.is_(None) | Contract.tipo_contrato.in_([ContractType.RENT.value, 'Rent', 'Aluguel']))
    ).all()
    quarentenas_count = 0
    quarentenas_valor = 0.0
    depositos_ativos_valor = 0.0
    total_depositos_retidos = 0.0

    for c in contratos_com_deposito:
        is_hold = c.status in [ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito']
        if is_hold:
            quarentenas_count += 1
        
        dep_pago = 0.0
        deducoes = 0.0
        for t in c.transacoes:
            if t.status in [TransactionStatus.PAID.value, 'Paid', 'Pago']:
                if t.tipo in [TransactionType.DEPOSIT.value, 'Deposit', 'Deposito', 'Depósito']:
                    dep_pago += float(t.valor)
                elif t.forma_pagamento and 'deposit' in t.forma_pagamento.lower():
                    deducoes += float(t.valor)
        saldo = max(0.0, dep_pago - deducoes)
        total_depositos_retidos += saldo
        if is_hold:
            quarentenas_valor += saldo
        else:
            depositos_ativos_valor += saldo
                
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
    
    # Alertas de Compliance: Road Tax (apenas frota ativa) e MOT (frota ativa + motos vendidas para prospecção de serviço na oficina)
    hoje_date = get_london_date()
    todas_motos = db.session.query(
        Motorcycle.placa,
        Motorcycle.status,
        Motorcycle.vencimento_tax,
        Motorcycle.vencimento_mot,
        Motorcycle.tax_sorn
    ).all()
    tax_mot_warnings = 0
    tax_warnings = 0
    mot_warnings = 0
    tax_mot_expired = 0
    tax_mot_expiring_soon = 0
    
    placas_contratos_ativos = {ca.placa for ca in contratos_ativos_objs}
    for m in todas_motos:
        is_sold = (m.status in [MotoStatus.SOLD.value, 'Sold', 'Vendida'])
        is_pound = (m.status in [MotoStatus.POUND.value, 'Pound'])

        # Motos com status "Pound" estão fora de operação: NÃO emitem alerta de MOT e nem Road Tax
        if is_pound:
            continue

        has_tax_w = False
        has_mot_w = False
        is_m_expired = False
        
        # Road Tax: checado apenas para frota ativa no nome da loja (apenas motos vendidas com contrato completado e motos SORN são isentas)
        is_sorn = bool(getattr(m, 'tax_sorn', False))
        is_truly_sold = is_sold and (m.placa not in placas_contratos_ativos)
        if not is_truly_sold and not is_sorn and m.vencimento_tax:
            diff_t = (m.vencimento_tax - hoje_date).days
            if diff_t < 0:
                has_tax_w = True
                is_m_expired = True
            elif diff_t <= 30:
                has_tax_w = True
                
        # MOT: checado SEMPRE para todas as motos (inclusive vendidas),
        # permitindo à oficina contatar proativamente o cliente da moto vendida para fazer revisão pré-MOT e faturar o serviço
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
        # Não monitorar seguro quinzenal para motos vendidas (Sale_Full / Sale_Installment) nem compradas (Purchase)
        tipo_ca = getattr(ca, 'tipo_contrato', 'Rent') or 'Rent'
        if tipo_ca in [ContractType.SALE_FULL.value, ContractType.SALE_INSTALLMENT.value, 'Sale_Full', 'Sale_Installment', ContractType.PURCHASE.value, 'Purchase', 'Compra']:
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
    
    # Pre-Delivery Compliance: Motorbikes Pending Check-out Inspection or Insurance Certificate before release
    # Contratos de compra (Purchase) não requerem liberação para cliente (veículo adquirido pela loja)
    contratos_pendentes_liberacao = []
    for ca in contratos_ativos_objs:
        tipo_ca = getattr(ca, 'tipo_contrato', 'Rent') or 'Rent'
        if tipo_ca in [ContractType.PURCHASE.value, 'Purchase', 'Compra']:
            continue
        tem_checkout = any(v.tipo in [InspectionType.CHECK_OUT.value, 'Check-out', 'Saída', 'Saida'] for v in (ca.vistorias or []))
        tem_seguro = bool(ca.url_seguro)
        if not tem_checkout or not tem_seguro:
            pendencias = []
            if not tem_checkout: pendencias.append('Check-out Inspection')
            if not tem_seguro: pendencias.append('Insurance Certificate')
            cli_nome = ca.cliente_nome or (ca.cliente.nome if ca.cliente else f"Client #{ca.id_cliente}")
            contratos_pendentes_liberacao.append({
                'id': ca.id,
                'placa': ca.placa,
                'cliente': cli_nome,
                'tipo_contrato': getattr(ca, 'tipo_contrato', 'Rent') or 'Rent',
                'tem_checkout': tem_checkout,
                'tem_seguro': tem_seguro,
                'pendencias': pendencias,
                'pendencias_txt': " & ".join(pendencias)
            })

    # Compliance de Compras: Contratos de Compra pendentes de Logbook (V5C)
    compras_pendentes_v5c = []
    placas_repurchases_sem_v5c = {}
    for ca in contratos_ativos_objs:
        tipo_ca = getattr(ca, 'tipo_contrato', 'Rent') or 'Rent'
        if tipo_ca in [ContractType.PURCHASE.value, 'Purchase', 'Compra']:
            placa_limpa = (ca.moto_placa or ca.placa or '').strip().upper()
            docs_ciclo = get_purchase_contract_v5c_docs(ca)
            tem_v5c = any((getattr(d, 'categoria_doc', 'v5c') or 'v5c') == 'v5c' for d in docs_ciclo)
            tem_slip = any((getattr(d, 'categoria_doc', 'v5c') or 'v5c') == 'transfer_proof' for d in docs_ciclo)
            if not tem_v5c:
                cli_nome = ca.cliente_nome or (ca.cliente.nome if ca.cliente else f"Client #{ca.id_cliente}")
                compras_pendentes_v5c.append({
                    'id': ca.id,
                    'placa': placa_limpa,
                    'cliente': cli_nome,
                    'valor_compra': float(ca.valor_compra_veiculo or 0.0),
                    'data_retirada': ca.data_retirada.strftime('%d/%m/%Y') if ca.data_retirada else None,
                    'has_transfer_proof': tem_slip
                })
                if placa_limpa:
                    placas_repurchases_sem_v5c[placa_limpa] = tem_slip
    compras_pendentes_v5c_count = len(compras_pendentes_v5c)

    # Compliance: Motos sem Documento V5C (Logbook) Oficial - Otimizado com NOT EXISTS em SQL direto
    motos_sem_v5c_objs = db.session.query(
        Motorcycle.placa,
        Motorcycle.modelo,
        Motorcycle.status
    ).filter(
        ~Motorcycle.v5c_arquivos.any(MotorcycleV5C.categoria_doc == 'v5c')
    ).order_by(Motorcycle.placa.asc()).all()

    # Pre-carrega placas que já possuem comprovante de transferência em O(1)
    placas_sem_v5c = [mv.placa for mv in motos_sem_v5c_objs]
    placas_com_slip = set()
    if placas_sem_v5c:
        slips = db.session.query(MotorcycleV5C.placa).filter(
            MotorcycleV5C.placa.in_(placas_sem_v5c),
            MotorcycleV5C.categoria_doc == 'transfer_proof'
        ).all()
        placas_com_slip = {s[0] for s in slips}

    motos_sem_v5c = [{
        'placa': mv.placa,
        'modelo': mv.modelo,
        'status': mv.status,
        'has_transfer_proof': (mv.placa in placas_com_slip)
    } for mv in motos_sem_v5c_objs]

    # Inclui motos de recompra com contrato de compra ativo aguardando V5C do ciclo atual
    placas_motos_incluidas = {m['placa'] for m in motos_sem_v5c}
    for p_rep, has_slip in placas_repurchases_sem_v5c.items():
        if p_rep not in placas_motos_incluidas:
            moto_obj = db.session.get(Motorcycle, p_rep)
            if moto_obj:
                motos_sem_v5c.append({
                    'placa': moto_obj.placa,
                    'modelo': moto_obj.modelo,
                    'status': moto_obj.status,
                    'has_transfer_proof': has_slip
                })
                placas_motos_incluidas.add(p_rep)

    motos_sem_v5c_count = len(motos_sem_v5c)

    # Proactive Collections: Actual pending charges due today (Rent, Sales Installments, Deposits, Fines, etc.)
    fim_hoje = inicio_hoje + timedelta(days=1)
    transacoes_hoje_objs = db.session.query(FinancialTransaction).options(
        joinedload(FinancialTransaction.contrato).joinedload(Contract.cliente)
    ).filter(
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
        FinancialTransaction.data_vencimento >= inicio_hoje,
        FinancialTransaction.data_vencimento < fim_hoje
    ).order_by(FinancialTransaction.data_vencimento.asc()).all()

    due_today_list = []
    for t in transacoes_hoje_objs:
        c = t.contrato
        cli = c.cliente if c else None
        cli_nome = cli.nome if cli else (c.cliente_nome if c else 'N/A')
        cli_tel = cli.telefone if cli else (c.cliente_telefone if c else '')
        placa = c.placa if c else '-'
        c_id = c.id if c else None
        due_today_list.append({
            'transacao_id': t.id,
            'id': t.id,
            'contrato_id': c_id,
            'placa': placa,
            'cliente_nome': cli_nome,
            'cliente_telefone': cli_tel,
            'valor': float(t.valor),
            'valor_semanal': float(t.valor),
            'tipo': t.tipo,
            'nota': t.nota or '',
            'ultimo_lembrete': t.ultimo_lembrete.isoformat() if t.ultimo_lembrete else None,
            'ultimo_lembrete_por': t.ultimo_lembrete_por or ''
        })

    due_today = {
        'count': len(due_today_list),
        'total_count': len(due_today_list),
        'total': round(sum(d['valor'] for d in due_today_list), 2),
        'total_amount': round(sum(d['valor'] for d in due_today_list), 2),
        'itens': due_today_list,
        'items': due_today_list
    }

    resp_data.update({
        'total_motos': total_motos,
        'motos_disponiveis': motos_disponiveis,
        'motos_alugadas': motos_alugadas,
        'motos_rental': motos_rental,
        'motos_financed': motos_financed,
        'motos_sold_outright': motos_sold_outright,
        'motos_manutencao': motos_manutencao,
        'motos_pound': motos_pound,
        'motos_fora_operacao': motos_pound,
        'motos_vendidas': motos_vendidas,
        'motos_sem_v5c_count': motos_sem_v5c_count,
        'motos_sem_v5c': motos_sem_v5c,
        'motos_manutencao_lista': motos_manutencao_lista,
        'tax_mot_warnings': tax_mot_warnings,
        'tax_mot_expired': tax_mot_expired,
        'tax_mot_expiring_soon': tax_mot_expiring_soon,
        'tax_warnings': tax_warnings,
        'mot_warnings': mot_warnings,
        'seguros_pendentes_count': seguros_pendentes_count,
        'seguros_cancelados_count': seguros_cancelados_count,
        'contratos_seguro_alerta': contratos_seguro_alerta,
        'pendentes_liberacao_count': len(contratos_pendentes_liberacao),
        'contratos_pendentes_liberacao': contratos_pendentes_liberacao,
        'compras_pendentes_v5c_count': compras_pendentes_v5c_count,
        'compras_pendentes_v5c': compras_pendentes_v5c,
        'contratos_ativos': contratos_ativos,
        'total_clientes': total_clientes,
        'receita_pendente': receita_pendente,
        'receita_semanal': receita_semanal,
        'receita_vencida': receita_vencida,
        'total_vencidos': total_vencidos,
        'collected_today': collected_today,
        'collected_this_week': collected_this_week,
        'due_today': due_today,
        'quarentenas_count': quarentenas_count,
        'quarentenas_valor': quarentenas_valor,
        'depositos_ativos_valor': depositos_ativos_valor,
        'total_depositos_retidos': total_depositos_retidos,
        'recent_inspections': recent_inspections,
        'recent_contracts': recent_contracts
    })

    if include_claims:
        claims_data = _compilar_dados_claims_dashboard()
        resp_data.update(claims_data)

    return resp_data

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    resp_data = {}

    pode_alugueis = current_user.is_authenticated and current_user.pode_alugueis()
    pode_claims = current_user.is_authenticated and current_user.pode_claims()

    if pode_alugueis:
        resp_data = _compilar_dados_dashboard(include_claims=pode_claims)
    elif pode_claims:
        resp_data = _compilar_dados_claims_dashboard()

    # Checagem de segurança discreta para a conta mestre
    if current_user.is_authenticated and current_user.pode_admin():
        is_master = bool(current_user.email and current_user.email.strip().lower() == "tmuniz570@gmail.com")
        if is_master and current_user.check_password("Admin123!"):
            resp_data['aviso_senha_padrao'] = True

    return jsonify(resp_data)

@app.route('/api/jobs/warmup', methods=['GET', 'POST'])
def api_warmup():
    """
    Endpoint de Warm-up Matinal (Aquecimento de Cache e Conexões).
    Executado preferencialmente via cron às 08:00 AM (Londres),
    1 hora antes da abertura da loja às 09:00 AM.
    Garante que conexões com PostgreSQL estejam ativas e o cache
    de dados quentes (Dashboard, Motos, Contratos) esteja na RAM.
    """
    if not check_cron_auth():
        return jsonify({'error': 'Unauthorized', 'message': 'Chave de cron ou privilégio administrativo requerido.'}), 403

    start_time = time.time()
    dados = _compilar_dados_dashboard(include_claims=True)

    # Pré-carregar consultas frequentes de Clientes e Motos para preencher buffers
    _ = db.session.query(Client.id, Client.nome, Client.telefone).limit(30).all()
    _ = db.session.query(Motorcycle.placa, Motorcycle.status).limit(30).all()

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    try:
        registrar_log(
            'SYSTEM_WARMUP',
            'System/Cron',
            None,
            f"Warm-up matinal executado com sucesso em {elapsed_ms}ms ({dados.get('total_motos')} motos ativas, {dados.get('contratos_ativos')} contratos ativos)."
        )
    except Exception:
        pass

    return jsonify({
        'success': True,
        'message': f'Sistema e cache aquecidos com sucesso em {elapsed_ms}ms.',
        'warmed_at': get_london_now().isoformat(),
        'duration_ms': elapsed_ms,
        'summary': {
            'total_motos': dados.get('total_motos'),
            'contratos_ativos': dados.get('contratos_ativos'),
            'due_today_count': dados.get('due_today', {}).get('count')
        }
    }), 200

@app.route('/api/alertas', methods=['GET'])
@alugueis_required
def listar_alertas():
    alertas = []
    hoje = get_local_now()
    
    # 1. Deposit hold alerts (14 or 15+ days)
    contratos_quarentena = Contract.query.filter(Contract.status.in_([ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito'])).all()
    for c in contratos_quarentena:
        if c.data_devolucao:
            hoje_date = hoje.date() if isinstance(hoje, datetime) else hoje
            devolucao_date = c.data_devolucao.date() if isinstance(c.data_devolucao, datetime) else c.data_devolucao
            dias_passados = (hoje_date - devolucao_date).days
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
    cliente_nome = (contrato.cliente.nome if contrato.cliente else contrato.cliente_nome) or 'Cliente'
    placa = contrato.placa or contrato.moto_placa or 'N/A'
    comp_txt = " com comprovante bancário de restituição anexado" if url_comprovante else " (sem anexo de comprovante)"
    registrar_log('QUARANTINE_END', 'Contract', contrato.id, f"Quarentena do contrato #{contrato.id} (Placa: {placa}, Cliente: {cliente_nome}) finalizada por {operador_atual}{comp_txt}.")
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

_BILLING_MUTEX = threading.Lock()

def _gerar_cobrancas_semanais_logic():
    """
    Gera as cobranças de aluguel semanais para todos os contratos de aluguel ativos.
    Regra de Negócio FF Motors:
    - Cada contrato possui seu dia da semana na coluna Contract.dia_pagamento_semanal (0=Segunda, ..., 6=Domingo).
    - No dia da semana do contrato, gera sempre a cobrança do vencimento para o dia da semana + 7.
      Assim, sempre que o cliente estiver com uma semana vencendo, a fatura da próxima já está gerada e visível.
    - Se por qualquer motivo o sistema não tiver executado no dia exato (ex: reinicialização do servidor ou queda de worker),
      o gerador faz a auto-recuperação (catch-up): verifica se a fatura do próximo ciclo (ou da semana atual)
      está faltando e gera automaticamente, prevenindo qualquer buraco no faturamento.
    - Idempotência absoluta: verifica antes se já existe lançamento de Rent para aquela data (pago ou pendente).
    - Commit e mutex por contrato para isolamento total contra concorrência.
    """
    with _BILLING_MUTEX:
        # London / UK timezone
        tz = pytz.timezone('Europe/London')
        hoje_london = datetime.now(tz)
        hoje_date = hoje_london.date()
        dia_semana_hoje = hoje_date.weekday() # 0 = Monday, ..., 6 = Sunday
        
        contratos_ativos = Contract.query.filter(
            Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']),
            db.or_(Contract.tipo_contrato == ContractType.RENT.value, Contract.tipo_contrato == None, Contract.tipo_contrato == 'Rent')
        ).all()
        
        transacoes_geradas = 0
        
        for contrato in contratos_ativos:
            valor_aluguel = float(contrato.valor_aluguel_semanal or 0.0)
            if valor_aluguel <= 0:
                continue
                
            # Obtém o dia da semana ativo configurado no contrato (0=Segunda a 6=Domingo)
            dia_contrato = contrato.dia_pagamento_semanal
            if dia_contrato is None or dia_contrato < 0 or dia_contrato > 6:
                dia_contrato = contrato.data_retirada.weekday() if getattr(contrato, 'data_retirada', None) else 0
                
            dias_desde_ultimo = (dia_semana_hoje - dia_contrato) % 7
            ultimo_vencimento_date = hoje_date - timedelta(days=dias_desde_ultimo)
            proximo_vencimento_date = ultimo_vencimento_date + timedelta(days=7)
            
            vencimentos_alvo = []
            data_inicio_contrato = getattr(contrato, 'data_retirada', None)
            if not data_inicio_contrato or data_inicio_contrato.date() <= ultimo_vencimento_date:
                vencimentos_alvo.append(ultimo_vencimento_date)
            vencimentos_alvo.append(proximo_vencimento_date)
            
            for v_date in vencimentos_alvo:
                inicio_dia = datetime(v_date.year, v_date.month, v_date.day, 0, 0, 0)
                fim_dia = inicio_dia + timedelta(days=1)
                
                cobranca_existente = FinancialTransaction.query.filter(
                    FinancialTransaction.id_contrato == contrato.id,
                    FinancialTransaction.tipo.in_([TransactionType.RENT.value, 'Rent', 'Aluguel']),
                    FinancialTransaction.data_vencimento >= inicio_dia,
                    FinancialTransaction.data_vencimento < fim_dia
                ).first()
                
                if not cobranca_existente:
                    nova_cobranca = FinancialTransaction(
                        id_contrato=contrato.id,
                        tipo=TransactionType.RENT.value,
                        data_vencimento=inicio_dia,
                        valor=valor_aluguel,
                        status=TransactionStatus.PENDING.value
                    )
                    db.session.add(nova_cobranca)
                    db.session.commit() # Commit imediato por contrato para visibilidade transacional concorrente
                    transacoes_geradas += 1
                    
        return transacoes_geradas

@app.route('/api/jobs/gerar-cobrancas-semanais', methods=['POST'])
def gerar_cobrancas_semanais():
    if not check_cron_auth():
        return jsonify({'error': 'Unauthorized', 'message': 'Chave de cron ou privilégio administrativo requerido.'}), 403
    transacoes = _gerar_cobrancas_semanais_logic()
    registrar_log('JOB_WEEKLY_RENT', 'System', None, f"Job de cobranças semanais executado. {transacoes} novas cobranças geradas.")
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
    registrar_log('JOB_QUARANTINE', 'System', None, f"Job de quarentena executado. {processados} contratos finalizados automaticamente.")
    return jsonify({
        "message": "Deposit holds processed successfully",
        "contracts_completed": processados,
        "contratos_finalizados": processados
    }), 200

def _limpar_cobrancas_semanais_duplicadas_logic(dry_run=False):
    """
    Identifica cobranças de aluguel semanais (tipo Rent/Aluguel) com status PENDING
    que foram criadas em duplicidade para o mesmo contrato e mesma data de vencimento.
    Mantém a cobrança original (menor ID) e remove as duplicatas extras.
    NUNCA toca em cobranças PAID (Pagas), depósitos ou outras transações legítimas.
    """
    from collections import defaultdict
    
    transacoes = FinancialTransaction.query.filter(
        FinancialTransaction.tipo.in_([TransactionType.RENT.value, 'Rent', 'Aluguel']),
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente'])
    ).order_by(FinancialTransaction.id.asc()).all()
    
    grupos = defaultdict(list)
    for t in transacoes:
        if t.data_vencimento:
            venc_str = t.data_vencimento.strftime('%Y-%m-%d')
            chave = (t.id_contrato, venc_str)
            grupos[chave].append(t)
            
    duplicadas_para_remover = []
    detalhes_removidos = []
    
    for (id_contrato, venc_str), lista in grupos.items():
        if len(lista) > 1:
            original = lista[0]
            dups = lista[1:]
            for d in dups:
                duplicadas_para_remover.append(d)
                detalhes_removidos.append({
                    "id_removido": d.id,
                    "id_contrato": id_contrato,
                    "vencimento": venc_str,
                    "valor": float(d.valor),
                    "id_mantido": original.id
                })
                
    total_duplicadas = len(duplicadas_para_remover)
    
    if not dry_run and total_duplicadas > 0:
        for d in duplicadas_para_remover:
            db.session.delete(d)
        db.session.commit()
        registrar_log(
            'CLEANUP_DUPLICATE_RENT',
            'Admin/System',
            None,
            f"Limpeza de cobranças duplicadas executada: {total_duplicadas} cobranças pendentes duplicadas removidas."
        )
        
    return {
        "total_duplicadas": total_duplicadas,
        "dry_run": dry_run,
        "detalhes": detalhes_removidos
    }

@app.route('/api/admin/limpar-cobrancas-duplicadas', methods=['POST'])
def api_limpar_cobrancas_duplicadas():
    """
    Rota administrativa para detecção e limpeza de cobranças duplicadas em produção.
    Aceita {"dry_run": true} para apenas simular sem apagar.
    """
    if not check_cron_auth():
        return jsonify({'error': 'Unauthorized', 'message': 'Chave de cron ou privilégio administrativo requerido.'}), 403
        
    dados = request.get_json(silent=True) or {}
    dry_run = dados.get('dry_run', False)
    if isinstance(dry_run, str):
        dry_run = dry_run.lower() in ('true', '1', 'yes')
        
    resultado = _limpar_cobrancas_semanais_duplicadas_logic(dry_run=dry_run)
    return jsonify({
        "success": True,
        "message": f"{resultado['total_duplicadas']} cobranças duplicadas encontradas." if dry_run else f"{resultado['total_duplicadas']} cobranças duplicadas removidas com sucesso.",
        "dados": resultado
    }), 200

def run_daily_jobs(force=False):
    with app.app_context():
        london_date_str = get_london_date().strftime('%Y-%m-%d')
        job_name = "daily_rent_and_deposit_jobs"
        worker_id = f"worker-pid-{os.getpid()}"
        
        # Concurrency safety across multi-worker deployments (e.g. Gunicorn):
        # 1. Garante que o registro base existe
        try:
            lock = JobExecutionLock.query.filter_by(job_name=job_name).first()
            if not lock:
                try:
                    init_lock = JobExecutionLock(
                        job_name=job_name,
                        last_run_date="",
                        last_run_at=get_local_now(),
                        executed_by="init"
                    )
                    db.session.add(init_lock)
                    db.session.commit()
                except Exception:
                    db.session.rollback()

            # 2. UPDATE CONDICIONAL ATÔMICO:
            # Se force=False: Exatamente UM processo concorrente receberá rows_updated == 1.
            # Todos os demais processos concorrentes receberão 0 e serão abortados.
            # Se force=True (ex: deploy ou catch-up explícito): atualiza timestamp e prossegue.
            if not force:
                rows_updated = JobExecutionLock.query.filter(
                    JobExecutionLock.job_name == job_name,
                    JobExecutionLock.last_run_date != london_date_str
                ).update({
                    'last_run_date': london_date_str,
                    'last_run_at': get_local_now(),
                    'executed_by': worker_id
                })
                db.session.commit()

                if rows_updated == 0:
                    print(f"[Cron Lock] Daily jobs '{job_name}' já foram executados ou adquiridos por outro worker para a data {london_date_str}. Abortando execução duplicada.")
                    return
            else:
                JobExecutionLock.query.filter_by(job_name=job_name).update({
                    'last_run_date': london_date_str,
                    'last_run_at': get_local_now(),
                    'executed_by': f"{worker_id}-forced"
                })
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[Cron Lock] Erro ao tentar adquirir lock atômico de execução diária para {london_date_str}: {e}")
            return

        print(f"[Cron] Iniciando rotinas diárias para {london_date_str} (Europe/London 01:00 AM) no {worker_id} (force={force})...")
        t_cobrancas = _gerar_cobrancas_semanais_logic()
        t_quarentenas = _processar_quarentenas_logic()
        print(f"[Cron] Concluído. {t_cobrancas} cobranças geradas, {t_quarentenas} quarentenas processadas.")
        
        try:
            registrar_log(
                'JOB_DAILY_ROUTINE',
                'System',
                None,
                f"Rotinas diárias automáticas executadas ({london_date_str}). {t_cobrancas} cobrança(s) de aluguel gerada(s), {t_quarentenas} quarentena(s) processada(s)."
            )
        except Exception as e_log:
            print(f"[Cron Log Error]: {e_log}")

if __name__ == '__main__':
    uploads_dir = os.path.join(basedir, 'static', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Start APScheduler with Europe/London timezone at 01:00 AM (guarded for Flask reloader)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        from warmup import run_warmup
        scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/London'))
        scheduler.add_job(
            func=run_daily_jobs,
            trigger="cron",
            hour=1,
            minute=0,
            id="daily_rent_and_deposit_jobs",
            replace_existing=True,
            misfire_grace_time=3600
        )
        scheduler.add_job(
            func=lambda: run_warmup(origem='System/Scheduler'),
            trigger="cron",
            hour=8,
            minute=0,
            id="morning_warmup_job",
            replace_existing=True,
            misfire_grace_time=3600
        )
        scheduler.start()
    
    debug_mode = os.environ.get('FLASK_DEBUG', 'true').lower() in ('true', '1')
    app.run(debug=debug_mode, host='0.0.0.0', use_reloader=debug_mode)
