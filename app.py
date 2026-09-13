import os
import secrets
import hmac
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
    db, init_db, Contract, FinancialTransaction, TransactionType, 
    TransactionStatus, ContractStatus, MotoStatus, Motorcycle, Client, Inspection, InspectionType,
    User, AuditLog
)
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
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')

# Garante tipos MIME corretos no Windows para que imagens e documentos abram em nova aba e não façam download
import mimetypes
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('image/avif', '.avif')
mimetypes.add_type('application/pdf', '.pdf')
mimetypes.add_type('image/jpeg', '.jpg')
mimetypes.add_type('image/jpeg', '.jpeg')
mimetypes.add_type('image/png', '.png')
mimetypes.add_type('image/svg+xml', '.svg')

# Configuração de Autenticação (Flask-Login)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Faça login para acessar o sistema FF Motors.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
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
        if not current_user.is_authenticated or getattr(current_user, 'role', '') != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({"error": "Forbidden", "message": "Admin privileges required"}), 403
            flash('Acesso restrito a administradores.', 'danger')
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
            data_hora=datetime.utcnow()
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
    return response

@app.before_request
def check_authentication():
    # Endpoints públicos permitidos sem autenticação
    allowed_routes = ['login', 'static', 'custom_static_uploads', 'favicon']
    if request.endpoint in allowed_routes:
        return
    if request.path.startswith('/static/'):
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
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            if not user.ativo:
                flash('Esta conta de acesso está inativa. Contate o administrador.', 'danger')
                return render_template('login.html', email=email)
                
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('index')
            return redirect(next_page)
        else:
            flash('Credenciais inválidas. Verifique seu e-mail e senha.', 'danger')
            return render_template('login.html', email=email)
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    flash('Você saiu do sistema com segurança.', 'info')
    return redirect(url_for('login'))

@app.route('/static/uploads/<path:filename>')
def custom_static_uploads(filename):
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
    elif ext == '.svg':
        mimetype = 'image/svg+xml'
    else:
        guessed = mimetypes.guess_type(filename)[0]
        if guessed:
            mimetype = guessed
            
    response = send_from_directory(uploads_dir, filename, mimetype=mimetype, as_attachment=False)
    response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
    response.headers['X-Content-Type-Options'] = 'nosniff'
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
        elif ext == '.svg':
            response.headers['Content-Type'] = 'image/svg+xml'
        response.headers['Content-Disposition'] = 'inline'
        response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

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
    Salva arquivo enviado. Se for imagem, auto-rotaciona via EXIF (corrige fotos de iPhone),
    redimensiona para no máximo 1600px e comprime em WebP com qualidade 80 (~30-90 KB).
    Se for PDF ou outro documento, salva diretamente.
    Retorna o nome do arquivo final salvo.
    """
    uploads_dir = app.config.get('UPLOAD_FOLDER', os.path.join(basedir, 'static', 'uploads'))
    os.makedirs(uploads_dir, exist_ok=True)
    
    ext = os.path.splitext(nome_arquivo)[1].lower()
    caminho_final = os.path.join(uploads_dir, nome_arquivo)
    
    if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.heic']:
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
        img.save(caminho_webp, 'WEBP', quality=80, method=6)
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
def pagina_cadastro_cliente():
    return render_template('cadastro_cliente.html')

@app.route('/clientes')
def pagina_clientes():
    return render_template('clientes.html')

@app.route('/motos')
def pagina_motos():
    return render_template('motos.html')

@app.route('/motos/nova')
def pagina_cadastro_moto():
    return render_template('cadastro_moto.html')

@app.route('/contratos')
def pagina_contratos():
    return render_template('contratos.html')

@app.route('/contratos/novo')
def pagina_novo_contrato():
    return render_template('novo_contrato.html')

@app.route('/vistorias/nova')
def pagina_nova_vistoria():
    return render_template('vistoria.html')

@app.route('/financeiro')
def pagina_financeiro():
    return render_template('financeiro.html')

@app.route('/vistorias')
def pagina_vistorias_lista():
    return render_template('vistorias_lista.html')

@app.route('/relatorios')
def pagina_relatorios():
    return redirect('/financeiro')

@app.route('/relatorios/vencidos')
def relatorio_vencidos():
    transacoes = FinancialTransaction.query.filter(
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pendente']),
        FinancialTransaction.data_vencimento < datetime.utcnow()
    ).order_by(FinancialTransaction.data_vencimento.asc()).all()
    
    dados = []
    total = 0
    for t in transacoes:
        c = Contract.query.get(t.id_contrato)
        cliente = Client.query.get(c.id_cliente) if c else None
        
        dados.append({
            'contrato_id': c.id if c else '-',
            'cliente_nome': cliente.nome if cliente else '-',
            'placa': c.placa if c else '-',
            'tipo': t.tipo,
            'valor': t.valor,
            'vencimento': t.data_vencimento.strftime('%d/%m/%Y') if t.data_vencimento else '-'
        })
        total += float(t.valor)
        
    tz = pytz.timezone('Europe/London')
    agora = datetime.now(tz).strftime('%d/%m/%Y %H:%M:%S')
    return render_template('relatorio_vencidos.html', dados=dados, total=total, agora=agora)

@app.route('/contratos/<int:id>')
def pagina_detalhes_contrato(id):
    return render_template('detalhe_contrato.html', contrato_id=id)

@app.route('/usuarios')
@admin_required
def pagina_usuarios():
    return render_template('usuarios.html')

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
    role = data.get('role', 'staff').strip().lower()
    password = data.get('password', '')
    
    if not nome or not email or not password:
        return jsonify({'error': 'Name, email, and password are required'}), 400
        
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'An account with this email address already exists'}), 400
        
    if role not in ['admin', 'staff']:
        role = 'staff'
        
    novo_user = User(
        nome=nome,
        email=email,
        role=role,
        ativo=True
    )
    novo_user.set_password(password)
    
    db.session.add(novo_user)
    db.session.commit()
    
    registrar_log('USER_CREATE', 'User', novo_user.id, f"Novo usuário cadastrado: {novo_user.nome} ({novo_user.email}) com perfil {novo_user.role}")

    return jsonify({
        'message': 'User created successfully',
        'usuario': {
            'id': novo_user.id,
            'nome': novo_user.nome,
            'email': novo_user.email,
            'role': novo_user.role,
            'ativo': novo_user.ativo
        }
    }), 201

@app.route('/api/usuarios/<int:user_id>', methods=['PUT'])
@admin_required
def atualizar_usuario(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    alteracoes = []
    
    # Check if modifying name
    if 'nome' in data and data['nome'].strip():
        if user.nome != data['nome'].strip():
            alteracoes.append(f"nome de '{user.nome}' para '{data['nome'].strip()}'")
            user.nome = data['nome'].strip()
        
    # Check if modifying role
    if 'role' in data:
        nova_role = data['role'].strip().lower()
        if nova_role in ['admin', 'staff']:
            if user.id == current_user.id and nova_role != 'admin':
                return jsonify({'error': 'You cannot remove your own administrator privileges'}), 400
            if user.role != nova_role:
                alteracoes.append(f"perfil para '{nova_role}'")
                user.role = nova_role
            
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
            'ativo': user.ativo
        }
    }), 200

@app.route('/api/usuarios/<int:user_id>', methods=['DELETE'])
@admin_required
def deletar_usuario(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({'error': 'You cannot delete your own account'}), 400
        
    nome_antigo = user.nome
    email_antigo = user.email
    db.session.delete(user)
    db.session.commit()
    
    registrar_log('USER_DELETE', 'User', user_id, f"Usuário excluído: {nome_antigo} ({email_antigo})")
    return jsonify({'message': f'User {nome_antigo} deleted successfully'}), 200

@app.route('/api/auditoria', methods=['GET'])
@admin_required
def listar_auditoria():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    acao = request.args.get('acao', '', type=str)
    data_filtro = request.args.get('data', '', type=str)
    
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
        
    paginated = query.order_by(AuditLog.data_hora.desc()).paginate(page=page, per_page=limit, error_out=False)
    
    itens = [{
        'id': a.id,
        'data_hora': a.data_hora.isoformat() + 'Z' if a.data_hora else None,
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
def criar_cliente():
    nome = request.form.get('nome')
    telefone = request.form.get('telefone')
    email = request.form.get('email')
    endereco = request.form.get('endereco')
    
    if not nome or not telefone or not email:
        return jsonify({'error': 'Missing required fields (full name, phone and email are required)', 'erro': 'Dados incompletos'}), 400
    
    # Check if email is already registered
    if Client.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered', 'erro': 'Email já cadastrado'}), 400
        
    url_hab = None
    url_comp_end = None
    
    if 'habilitacao' in request.files:
        f = request.files['habilitacao']
        if f.filename:
            nome_arq = werkzeug.utils.secure_filename(f"{int(datetime.utcnow().timestamp())}_{f.filename}")
            nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
            url_hab = f"/static/uploads/{nome_salvo}"
            
    if 'comprovante_endereco' in request.files:
        f = request.files['comprovante_endereco']
        if f.filename:
            nome_arq = werkzeug.utils.secure_filename(f"{int(datetime.utcnow().timestamp())}_comp_end_{f.filename}")
            nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
            url_comp_end = f"/static/uploads/{nome_salvo}"
            
    novo_cliente = Client(
        nome=nome,
        telefone=telefone,
        email=email,
        endereco=endereco,
        url_habilitacao=url_hab,
        url_comprovante_endereco=url_comp_end
    )
    db.session.add(novo_cliente)
    db.session.commit()
    
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('CREATE_CLIENT', 'Client', novo_cliente.id, f"Cliente {novo_cliente.nome} cadastrado por {operador_atual}")

    return jsonify({'message': 'Customer registered successfully', 'mensagem': 'Cliente cadastrado com sucesso', 'id': novo_cliente.id}), 201

@app.route('/api/motos', methods=['POST'])
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
        vencimento_mot=vencimento_mot,
        vencimento_tax=vencimento_tax
    )
    db.session.add(nova_moto)
    db.session.commit()
    
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('MOTO_CREATE', 'Motorcycle', nova_moto.placa, f"Moto {nova_moto.placa} ({nova_moto.modelo}) cadastrada por {operador_atual}")

    return jsonify({'message': 'Motorbike registered successfully', 'mensagem': 'Moto cadastrada com sucesso', 'placa': nova_moto.placa}), 201

@app.route('/api/clientes', methods=['GET'])
def listar_clientes():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    
    query = Client.query
    if search:
        search_term = f"%{search}%"
        query = query.filter(db.or_(
            Client.nome.ilike(search_term),
            Client.telefone.ilike(search_term),
            Client.email.ilike(search_term)
        ))
    
    paginated = query.order_by(Client.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    
    itens = [{
        'id': c.id, 'nome': c.nome, 'telefone': c.telefone, 'email': c.email, 'endereco': c.endereco,
        'url_habilitacao': c.url_habilitacao, 'url_comprovante_endereco': c.url_comprovante_endereco
    } for c in paginated.items]
    
    return jsonify({
        'itens': itens,
        'total': paginated.total,
        'paginas': paginated.pages,
        'pagina_atual': paginated.page
    })

@app.route('/api/clientes/<int:id>', methods=['PUT'])
def atualizar_cliente(id):
    cliente = Client.query.get(id)
    if not cliente:
        return jsonify({'error': 'Customer not found', 'erro': 'Cliente não encontrado'}), 404
        
    if request.is_json:
        dados = request.get_json()
        if 'nome' in dados: cliente.nome = dados['nome']
        if 'telefone' in dados: cliente.telefone = dados['telefone']
        if 'email' in dados:
            outro = Client.query.filter(Client.email == dados['email'], Client.id != id).first()
            if outro: return jsonify({'error': 'Email already registered for another customer', 'erro': 'Email já cadastrado por outro cliente'}), 400
            cliente.email = dados['email']
        if 'endereco' in dados: cliente.endereco = dados['endereco']
    else:
        if 'nome' in request.form: cliente.nome = request.form['nome']
        if 'telefone' in request.form: cliente.telefone = request.form['telefone']
        if 'endereco' in request.form: cliente.endereco = request.form['endereco']
        if 'email' in request.form:
            outro = Client.query.filter(Client.email == request.form['email'], Client.id != id).first()
            if outro: return jsonify({'error': 'Email already registered for another customer', 'erro': 'Email já cadastrado por outro cliente'}), 400
            cliente.email = request.form['email']
            
        if 'habilitacao' in request.files:
            f = request.files['habilitacao']
            if f.filename:
                nome_arq = werkzeug.utils.secure_filename(f"{int(datetime.utcnow().timestamp())}_{f.filename}")
                nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
                cliente.url_habilitacao = f"/static/uploads/{nome_salvo}"
                
        if 'comprovante_endereco' in request.files:
            f = request.files['comprovante_endereco']
            if f.filename:
                nome_arq = werkzeug.utils.secure_filename(f"{int(datetime.utcnow().timestamp())}_comp_end_{f.filename}")
                nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
                cliente.url_comprovante_endereco = f"/static/uploads/{nome_salvo}"
    
    db.session.commit()
    return jsonify({'message': 'Customer updated successfully', 'mensagem': 'Cliente atualizado com sucesso'})

@app.route('/api/motos', methods=['GET'])
def listar_motos():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    
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
        
    paginated = query.order_by(Motorcycle.placa).paginate(page=page, per_page=limit, error_out=False)
    
    itens = [{
        'placa': m.placa,
        'modelo': m.modelo,
        'cor': m.cor,
        'status': m.status,
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
def atualizar_moto(placa):
    moto = Motorcycle.query.get(placa)
    if not moto:
        return jsonify({'error': 'Motorbike not found', 'erro': 'Moto não encontrada'}), 404
        
    dados = request.get_json()
    status_antigo = moto.status
    if 'modelo' in dados: moto.modelo = dados['modelo']
    if 'cor' in dados: moto.cor = dados['cor']
    if 'status' in dados: moto.status = dados['status']
    
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
def criar_contrato():
    id_cliente = request.form.get('id_cliente')
    placa = request.form.get('placa')
    dia_pagamento_semanal = int(request.form.get('dia_pagamento_semanal'))
    valor_aluguel_semanal = float(request.form.get('valor_aluguel_semanal', 250.0))
    valor_deposito = float(request.form.get('valor_deposito'))
    observacoes = request.form.get('observacoes')
    
    if 'fotos' not in request.files:
        return jsonify({'error': 'Initial check-out inspection photos are required', 'erro': 'A vistoria de saída (foto) é obrigatória'}), 400
        
    fotos = request.files.getlist('fotos')
    if not fotos or fotos[0].filename == '':
        return jsonify({'error': 'No photos selected for inspection', 'erro': 'Nenhuma foto selecionada'}), 400
        
    if 'seguro' not in request.files:
        return jsonify({'error': 'Insurance certificate document is required to open a contract', 'erro': 'O arquivo do Seguro é obrigatório para abrir um contrato'}), 400
        
    moto = Motorcycle.query.get(placa)
    if not moto or moto.status not in [MotoStatus.AVAILABLE.value, 'Disponível']:
        return jsonify({'error': 'Motorbike is not available for rental', 'erro': 'Moto não está disponível'}), 400
        
    # Save inspection photos
    urls_fotos = []
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
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

    # Create Contract
    novo_contrato = Contract(
        id_cliente=id_cliente,
        placa=placa,
        dia_pagamento_semanal=dia_pagamento_semanal,
        valor_aluguel_semanal=valor_aluguel_semanal,
        url_seguro=url_seguro,
        status=ContractStatus.ACTIVE.value,
        criado_por_nome=operador_atual,
        data_ultima_checagem_seguro=datetime.utcnow().date(),
        status_seguro='Valid',
        seguro_verificado_por=operador_atual
    )
    db.session.add(novo_contrato)
    
    # Update motorbike status to Rented
    moto.status = MotoStatus.RENTED.value
    
    db.session.flush() # Retrieve generated contract ID
    
    hoje = datetime.utcnow()
    
    # Security deposit transaction
    deposito = FinancialTransaction(
        id_contrato=novo_contrato.id,
        tipo=TransactionType.DEPOSIT.value,
        data_vencimento=hoje,
        valor=valor_deposito,
        status=TransactionStatus.PENDING.value
    )
    db.session.add(deposito)
    
    # Week 1 rent (due today upon collection)
    aluguel_semana_1 = FinancialTransaction(
        id_contrato=novo_contrato.id,
        tipo=TransactionType.RENT.value,
        data_vencimento=hoje,
        valor=valor_aluguel_semanal,
        status=TransactionStatus.PENDING.value
    )
    db.session.add(aluguel_semana_1)
    
    # Week 2 rent (due on next recurring payment day)
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
    
    # Create Check-out Inspection
    nova_vistoria = Inspection(
        id_contrato=novo_contrato.id,
        tipo=InspectionType.CHECK_OUT.value,
        observacoes=observacoes,
        url_fotos=url_foto_str,
        realizado_por_nome=operador_atual
    )
    db.session.add(nova_vistoria)
    
    db.session.commit()
    
    registrar_log('CREATE_CONTRACT', 'Contract', novo_contrato.id, f"Contrato #{novo_contrato.id} aberto para moto {moto.placa} por {operador_atual} (Aluguel: £{valor_aluguel_semanal:.2f}/sem, Depósito: £{valor_deposito:.2f})")
    
    return jsonify({'message': 'Contract and initial inspection created successfully', 'mensagem': 'Contrato e vistoria criados com sucesso', 'id': novo_contrato.id}), 201

@app.route('/api/contratos/<int:id>/seguro', methods=['PUT'])
def atualizar_seguro_contrato(id):
    contrato = Contract.query.get(id)
    if not contrato:
        return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404
        
    if 'seguro' in request.files:
        f = request.files['seguro']
        if f.filename:
            nome_arq = werkzeug.utils.secure_filename(f"{int(datetime.utcnow().timestamp())}_seguro_upd_{f.filename}")
            nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
            contrato.url_seguro = f"/static/uploads/{nome_salvo}"
            db.session.commit()
            return jsonify({'message': 'Insurance document updated successfully', 'mensagem': 'Seguro atualizado'})
            
    return jsonify({'error': 'No file uploaded', 'erro': 'Nenhum arquivo enviado'}), 400

@app.route('/api/contratos/<int:id>/verificar-seguro', methods=['POST'])
@login_required
def verificar_seguro_contrato(id):
    contrato = Contract.query.get(id)
    if not contrato:
        return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404
        
    dados = request.get_json() or {}
    novo_status = dados.get('status', 'Valid')
    if novo_status not in ['Valid', 'Cancelled']:
        novo_status = 'Valid'
        
    operador = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    hoje_date = datetime.utcnow().date()
    
    contrato.data_ultima_checagem_seguro = hoje_date
    contrato.status_seguro = novo_status
    contrato.seguro_verificado_por = operador
    db.session.commit()
    
    if novo_status == 'Valid':
        registrar_log('INSURANCE_VERIFIED', 'Contract', contrato.id, f"Seguro da moto {contrato.placa} verificado como VÁLIDO no askMID por {operador} no Contrato #{contrato.id} (Próxima checagem em 15 dias)")
        msg = "Insurance verified as VALID on askMID. Next check scheduled in 15 days."
    else:
        registrar_log('INSURANCE_CANCELLED', 'Contract', contrato.id, f"ALERTA: Seguro da moto {contrato.placa} reportado CANCELADO/INVÁLIDO no askMID por {operador} no Contrato #{contrato.id}")
        msg = "ALARM: Insurance flagged as CANCELLED/INVALID on askMID."
        
    return jsonify({
        'message': msg,
        'status_seguro': contrato.status_seguro,
        'data_ultima_checagem_seguro': contrato.data_ultima_checagem_seguro.strftime('%Y-%m-%d'),
        'seguro_verificado_por': contrato.seguro_verificado_por
    })

@app.route('/api/contratos', methods=['GET'])
def listar_contratos():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    
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
            Client.nome.ilike(search_term)
        ))
        
    status_filter = request.args.get('status', '', type=str)
    if status_filter:
        if status_filter.lower() in ['deposit_hold', 'quarentena_deposito', 'quarentena']:
            query = query.filter(Contract.status.in_([ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito']))
        elif status_filter.lower() in ['active', 'ativo']:
            query = query.filter(Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']))
        elif status_filter.lower() in ['completed', 'finalizado']:
            query = query.filter(Contract.status.in_([ContractStatus.COMPLETED.value, 'Completed', 'Finalizado']))
        else:
            query = query.filter(Contract.status == status_filter)
    else:
        nao_finalizados = request.args.get('nao_finalizados') == 'true' or request.args.get('ativos') == 'true'
        if nao_finalizados:
            query = query.filter(Contract.status.in_([
                ContractStatus.ACTIVE.value, 'Active', 'Ativo',
                ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito'
            ]))
        
    paginated = query.order_by(Contract.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    
    itens = [{
        'id': c.id, 'id_cliente': c.id_cliente, 'cliente_nome': c.cliente.nome, 'placa': c.placa,
        'data_retirada': c.data_retirada.isoformat() + 'Z' if c.data_retirada else None,
        'dia_pagamento_semanal': c.dia_pagamento_semanal,
        'valor_aluguel_semanal': c.valor_aluguel_semanal,
        'data_devolucao': c.data_devolucao.isoformat() + 'Z' if c.data_devolucao else None,
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
def detalhe_contrato(id):
    c = Contract.query.get(id)
    if not c:
        return jsonify({'error': 'Contract not found', 'erro': 'Contrato não encontrado'}), 404
        
    cliente = Client.query.get(c.id_cliente)
    moto = Motorcycle.query.get(c.placa)
    
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
                    'data_pagamento': t.data_pagamento.strftime('%d/%m/%Y') if t.data_pagamento else None
                })
    is_completed = c.status in [ContractStatus.COMPLETED.value, 'Completed', 'Finalizado']
    valor_restituido = max(0.0, deposito_pago - deducoes_deposito) if is_completed else 0.0
    saldo_deposito = 0.0 if is_completed else max(0.0, deposito_pago - deducoes_deposito)
    
    # Filter out any deposit refund transactions from customer statement
    transacoes_cliente = [t for t in transacoes if t.tipo.lower() not in ['deposit_refund', 'devolucao_deposito', 'deposit refund']]
    
    # 15-Day Insurance Check calculation
    hoje_date = datetime.utcnow().date()
    ultima_checagem = c.data_ultima_checagem_seguro or (c.data_retirada.date() if c.data_retirada else hoje_date)
    dias_desde_checagem = (hoje_date - ultima_checagem).days
    dias_para_proxima = max(0, 15 - dias_desde_checagem)
    checagem_seguro_devida = (dias_desde_checagem >= 15) or (c.status_seguro == 'Cancelled')
    
    return jsonify({
        'id': c.id,
        'cliente': cliente.nome if cliente else f'ID {c.id_cliente}',
        'id_cliente': c.id_cliente,
        'telefone': cliente.telefone if cliente else '-',
        'email': cliente.email if cliente else '-',
        'endereco': cliente.endereco if cliente else None,
        'url_habilitacao': cliente.url_habilitacao if cliente else None,
        'url_comprovante_endereco': cliente.url_comprovante_endereco if cliente else None,
        'placa': c.placa,
        'modelo': moto.modelo if moto else '-',
        'cor': moto.cor if moto else '-',
        'vencimento_mot': moto.vencimento_mot.strftime('%Y-%m-%d') if (moto and moto.vencimento_mot) else None,
        'vencimento_tax': moto.vencimento_tax.strftime('%Y-%m-%d') if (moto and moto.vencimento_tax) else None,
        'data_retirada': c.data_retirada.isoformat() + 'Z' if c.data_retirada else None,
        'data_devolucao': c.data_devolucao.isoformat() + 'Z' if c.data_devolucao else None,
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
        'dias_desde_checagem_seguro': dias_desde_checagem,
        'dias_para_proxima_checagem_seguro': dias_para_proxima,
        'checagem_seguro_devida': checagem_seguro_devida,
        'deposito_pago': deposito_pago,
        'deducoes_deposito': deducoes_deposito,
        'saldo_deposito': saldo_deposito,
        'valor_restituido': valor_restituido,
        'deducoes_lista': deducoes_lista,
        'transacoes': [{
            'id': t.id,
            'tipo': t.tipo,
            'valor': float(t.valor),
            'status': t.status,
            'forma_pagamento': t.forma_pagamento,
            'registrado_por_nome': t.registrado_por_nome or '',
            'data_vencimento': t.data_vencimento.isoformat() + 'Z' if t.data_vencimento else None,
            'data_pagamento': t.data_pagamento.isoformat() + 'Z' if t.data_pagamento else None
        } for t in transacoes_cliente],
        'vistorias': [{
            'id': v.id,
            'tipo': v.tipo,
            'data_vistoria': v.data.isoformat() + 'Z' if v.data else None,
            'foto_url': v.url_fotos,
            'observacoes': v.observacoes,
            'realizado_por_nome': v.realizado_por_nome or ''
        } for v in vistorias]
    })

@app.route('/api/contratos/<int:id>/cobrancas', methods=['POST'])
def criar_cobranca(id):
    c = Contract.query.get(id)
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
        
    nova_cobranca = FinancialTransaction(
        id_contrato=c.id,
        tipo=tipo,
        data_vencimento=data_vencimento,
        valor=float(valor),
        status=TransactionStatus.PENDING.value
    )
    db.session.add(nova_cobranca)
    db.session.commit()
    
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    registrar_log('CREATE_CHARGE', 'Transaction', nova_cobranca.id, f"Cobrança manual de £{float(valor):.2f} ({tipo}) gerada por {operador_atual} para o Contrato #{c.id}")

    return jsonify({'message': 'Charge created successfully', 'mensagem': 'Cobrança gerada com sucesso'}), 201

@app.route('/api/cobrancas/<int:id>/pagar', methods=['PUT'])
def pagar_cobranca(id):
    t = FinancialTransaction.query.get(id)
    if not t:
        return jsonify({'error': 'Charge not found', 'erro': 'Cobrança não encontrada'}), 404
        
    forma_pagamento = request.json.get('forma_pagamento')
    if not forma_pagamento:
        return jsonify({'error': 'Payment method is required', 'erro': 'Forma de pagamento é obrigatória'}), 400
        
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    t.status = TransactionStatus.PAID.value
    t.data_pagamento = datetime.utcnow()
    t.forma_pagamento = forma_pagamento
    t.registrado_por_nome = operador_atual
    
    db.session.commit()
    registrar_log('PAYMENT_RECEIVED', 'Transaction', t.id, f"Baixa de £{float(t.valor):.2f} ({t.tipo}) confirmada via {forma_pagamento} por {operador_atual} no Contrato #{t.id_contrato}")
    return jsonify({'message': 'Payment marked successfully', 'mensagem': 'Baixa realizada com sucesso', 'forma_pagamento': t.forma_pagamento, 'registrado_por_nome': t.registrado_por_nome}), 200

@app.route('/api/vistorias', methods=['POST'])
def criar_vistoria():
    id_contrato = request.form.get('id_contrato')
    tipo = request.form.get('tipo')
    observacoes = request.form.get('observacoes')
    
    if 'fotos' not in request.files:
        return jsonify({'error': 'No photos uploaded', 'erro': 'Nenhuma foto enviada'}), 400
        
    fotos = request.files.getlist('fotos')
    if not fotos or fotos[0].filename == '':
        return jsonify({'error': 'No photos selected', 'erro': 'Nenhuma foto selecionada'}), 400
        
    urls_fotos = []
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    for i, foto in enumerate(fotos):
        if foto.filename:
            filename = werkzeug.utils.secure_filename(foto.filename)
            nome_arquivo = f"{timestamp}_{i}_{filename}"
            nome_salvo = salvar_arquivo_otimizado(foto, nome_arquivo)
            urls_fotos.append(f"/static/uploads/{nome_salvo}")
            
    url_foto_str = ",".join(urls_fotos)
    
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    nova_vistoria = Inspection(
        id_contrato=id_contrato,
        tipo=tipo,
        observacoes=observacoes,
        url_fotos=url_foto_str,
        realizado_por_nome=operador_atual
    )
    db.session.add(nova_vistoria)
    
    if tipo in [InspectionType.CHECK_IN.value, 'Check-in', 'Entrada']:
        contrato = Contract.query.get(id_contrato)
        if contrato:
            contrato.status = ContractStatus.DEPOSIT_HOLD.value
            contrato.data_devolucao = datetime.utcnow()
            moto = Motorcycle.query.get(contrato.placa)
            if moto:
                moto.status = MotoStatus.MAINTENANCE.value
                
    db.session.commit()
    
    registrar_log('CREATE_INSPECTION', 'Inspection', nova_vistoria.id, f"Vistoria de {tipo} registrada por {operador_atual} no Contrato #{id_contrato}")
    if tipo in [InspectionType.CHECK_IN.value, 'Check-in', 'Entrada']:
        registrar_log('RETURN_VEHICLE', 'Contract', id_contrato, f"Moto devolvida / Check-in confirmado por {operador_atual} no Contrato #{id_contrato}")
    
    return jsonify({'message': 'Inspection recorded successfully', 'mensagem': 'Vistoria registrada com sucesso', 'id': nova_vistoria.id, 'url': url_foto_str}), 201

@app.route('/api/vistorias', methods=['GET'])
def listar_vistorias():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    tipo = request.args.get('tipo', '', type=str)
    data_filtro = request.args.get('data', '', type=str)
    contrato_id = request.args.get('contrato_id', type=int)
    
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
        query = query.filter(Inspection.tipo == tipo)
        
    if data_filtro:
        try:
            dt_inicio = datetime.strptime(data_filtro, "%Y-%m-%d")
            dt_fim = dt_inicio + timedelta(days=1)
            query = query.filter(Inspection.data >= dt_inicio, Inspection.data < dt_fim)
        except ValueError:
            pass
        
    paginated = query.order_by(Inspection.data.desc()).paginate(page=page, per_page=limit, error_out=False)
    
    itens = [{
        'id': v.id,
        'id_contrato': v.id_contrato,
        'data_vistoria': v.data.isoformat() + 'Z',
        'tipo': v.tipo,
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
def listar_financeiro():
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    search = request.args.get('search', '', type=str)
    status_filtro = request.args.get('status', '', type=str)
    tipo_filtro = request.args.get('tipo', '', type=str)
    pendentes = request.args.get('pendentes') == 'true'
    
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
            Contract.placa.ilike(search_plate_term),
            Contract.placa.ilike(search_term),
            Client.nome.ilike(search_term)
        ))
        
    if status_filtro:
        if status_filtro.lower() in ['overdue', 'vencidos', 'vencido']:
            agora = datetime.utcnow()
            query = query.filter(
                FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
                FinancialTransaction.data_vencimento < agora
            )
        else:
            query = query.filter(FinancialTransaction.status == status_filtro)
    elif pendentes:
        query = query.filter(FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']))
        
    if tipo_filtro:
        query = query.filter(FinancialTransaction.tipo == tipo_filtro)
        
    paginated = query.order_by(FinancialTransaction.data_vencimento.asc()).paginate(page=page, per_page=limit, error_out=False)
    
    itens = [{
        'id': t.id,
        'id_contrato': t.id_contrato,
        'tipo': t.tipo,
        'data_vencimento': t.data_vencimento.isoformat() + 'Z' if t.data_vencimento else None,
        'data_pagamento': t.data_pagamento.isoformat() + 'Z' if t.data_pagamento else None,
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
def pagar_transacao(id):
    t = FinancialTransaction.query.get(id)
    if not t:
        return jsonify({'error': 'Transaction not found', 'erro': 'Transação não encontrada'}), 404
        
    forma = 'Cash'
    if request.is_json and request.json:
        forma = request.json.get('forma_pagamento', 'Cash')
    elif request.form and 'forma_pagamento' in request.form:
        forma = request.form.get('forma_pagamento', 'Cash')
        
    operador_atual = current_user.nome if (current_user and current_user.is_authenticated) else 'System'
    t.status = TransactionStatus.PAID.value
    t.data_pagamento = datetime.utcnow()
    t.forma_pagamento = forma
    t.registrado_por_nome = operador_atual
    db.session.commit()
    registrar_log('PAYMENT_RECEIVED', 'Transaction', t.id, f"Baixa de £{float(t.valor):.2f} ({t.tipo}) confirmada via {forma} por {operador_atual} no Contrato #{t.id_contrato}")
    return jsonify({'message': 'Transaction marked as paid successfully', 'mensagem': 'Transação paga com sucesso', 'forma_pagamento': t.forma_pagamento, 'registrado_por_nome': t.registrado_por_nome}), 200

@app.route('/api/financeiro/<int:id>/reverter', methods=['POST', 'PUT'])
@app.route('/api/cobrancas/<int:id>/reverter', methods=['POST', 'PUT'])
def reverter_pagamento(id):
    t = FinancialTransaction.query.get(id)
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

@app.route('/recibo/<int:id>')
def pagina_recibo(id):
    t = FinancialTransaction.query.get_or_404(id)
    contrato = Contract.query.get(t.id_contrato) if t.id_contrato else None
    cliente = Client.query.get(contrato.id_cliente) if (contrato and contrato.id_cliente) else None
    return render_template('recibo.html', transacao=t, contrato=contrato, cliente=cliente)

@app.route('/api/financeiro/<int:id>', methods=['DELETE'])
def excluir_transacao(id):
    t = FinancialTransaction.query.get(id)
    if not t:
        return jsonify({'error': 'Transaction not found', 'erro': 'Transação não encontrada'}), 404
        
    if t.status in [TransactionStatus.PAID.value, 'Paid', 'Pago']:
        return jsonify({'error': 'Cannot delete an already paid transaction', 'erro': 'Não é possível excluir uma transação já paga'}), 400
        
    db.session.delete(t)
    db.session.commit()
    return jsonify({'message': 'Transaction deleted successfully', 'mensagem': 'Transação excluída com sucesso'}), 200

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    total_motos = Motorcycle.query.count()
    motos_disponiveis = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.AVAILABLE.value, 'Available', 'Disponível'])).count()
    motos_alugadas = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.RENTED.value, 'Rented', 'Alugada'])).count()
    motos_manutencao = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.MAINTENANCE.value, 'Maintenance', 'Manutenção', 'Manutencao'])).count()
    
    # Detalhes das motos em manutenção
    motos_manutencao_lista = []
    manutencao_objs = Motorcycle.query.filter(Motorcycle.status.in_([MotoStatus.MAINTENANCE.value, 'Maintenance', 'Manutenção', 'Manutencao'])).all()
    for m in manutencao_objs:
        last_c = Contract.query.filter_by(placa=m.placa).order_by(Contract.id.desc()).first()
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
        
    contratos_ativos_lista = Contract.query.filter(Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo'])).all()
    contratos_ativos = len(contratos_ativos_lista)
    receita_semanal = sum(float(c.valor_aluguel_semanal) for c in contratos_ativos_lista)
    
    total_clientes = Client.query.count()
    
    pendentes = FinancialTransaction.query.filter(
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
        FinancialTransaction.tipo.in_([TransactionType.RENT.value, TransactionType.FINE.value, 'Rent', 'Fine', 'Aluguel', 'Multa'])
    ).all()
    receita_pendente = sum(float(t.valor) for t in pendentes)
    
    agora = datetime.utcnow()
    vencidas = FinancialTransaction.query.filter(
        FinancialTransaction.status.in_([TransactionStatus.PENDING.value, 'Pending', 'Pendente']),
        FinancialTransaction.data_vencimento < agora
    ).all()
    receita_vencida = sum(float(t.valor) for t in vencidas)
    total_vencidos = len(vencidas)
    
    contratos_quarentena = Contract.query.filter(Contract.status.in_([ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito'])).all()
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
                
    # Últimas vistorias
    recent_inspections = []
    inspecoes = Inspection.query.order_by(Inspection.id.desc()).limit(5).all()
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
        
    # Últimos contratos
    recent_contracts = []
    contratos = Contract.query.order_by(Contract.id.desc()).limit(4).all()
    for c in contratos:
        recent_contracts.append({
            'id': c.id,
            'cliente': c.cliente.nome if c.cliente else 'N/A',
            'placa': c.placa,
            'status': c.status,
            'valor_semanal': float(c.valor_aluguel_semanal),
            'data_retirada': c.data_retirada.strftime('%d/%m/%Y') if c.data_retirada else '-'
        })
    
    # Alertas de Compliance de Frota: Road Tax e MOT (vencidos ou a vencer em até 30 dias)
    hoje_date = datetime.utcnow().date()
    todas_motos = Motorcycle.query.all()
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
                
    # Compliance: Checagem Quinzenal de Seguro no askMID (15 em 15 dias)
    contratos_ativos_objs = Contract.query.filter(Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo'])).all()
    seguros_pendentes_count = 0
    seguros_cancelados_count = 0
    contratos_seguro_alerta = []
    
    for ca in contratos_ativos_objs:
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
    
    return jsonify({
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

@app.route('/api/alertas', methods=['GET'])
def listar_alertas():
    alertas = []
    hoje = datetime.utcnow()
    
    # 1. Deposit hold alerts (14 or 15+ days)
    contratos_quarentena = Contract.query.filter(Contract.status.in_([ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito'])).all()
    for c in contratos_quarentena:
        if c.data_devolucao:
            dias_passados = (hoje - c.data_devolucao).days
            if dias_passados >= 14:
                cliente = Client.query.get(c.id_cliente)
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
def finalizar_quarentena(id):
    contrato = Contract.query.get(id)
    if not contrato or contrato.status not in [ContractStatus.DEPOSIT_HOLD.value, 'Deposit_Hold', 'Quarentena_Deposito']:
        return jsonify({'error': 'Contract not found or not in deposit hold', 'erro': 'Contrato não encontrado ou não está em quarentena'}), 404
        
    url_comprovante = None
    if 'comprovante' in request.files:
        f = request.files['comprovante']
        if f.filename:
            nome_arq = werkzeug.utils.secure_filename(f"{int(datetime.utcnow().timestamp())}_{f.filename}")
            nome_salvo = salvar_arquivo_otimizado(f, nome_arq)
            url_comprovante = f"/static/uploads/{nome_salvo}"
            
    contrato.url_comprovante_deposito = url_comprovante
    contrato.status = ContractStatus.COMPLETED.value
    db.session.commit()
    return jsonify({'message': 'Deposit hold finalized successfully', 'mensagem': 'Quarentena finalizada com sucesso'})

@app.route('/api/relatorios/resumo', methods=['GET'])
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
    
    hoje_utc = datetime.utcnow()
    
    contratos_ativos = Contract.query.filter(
        Contract.status.in_([ContractStatus.ACTIVE.value, 'Active', 'Ativo']),
        Contract.dia_pagamento_semanal == dia_semana_atual
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

@app.route('/api/jobs/gerar-cobrancas-semanais', methods=['POST'])
def gerar_cobrancas_semanais():
    transacoes = _gerar_cobrancas_semanais_logic()
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
    hoje = datetime.utcnow()
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
        
        moto = Motorcycle.query.get(contrato.placa)
        if moto and moto.status in [MotoStatus.RENTED.value, 'Rented', 'Alugada']:
            moto.status = MotoStatus.AVAILABLE.value
            
        processados += 1
        
    if processados > 0:
        db.session.commit()
        
    return processados

@app.route('/api/jobs/processar-quarentenas', methods=['POST'])
def processar_quarentenas():
    processados = _processar_quarentenas_logic()
    return jsonify({
        "message": "Deposit holds processed successfully",
        "contracts_completed": processados,
        "contratos_finalizados": processados
    }), 200

def run_daily_jobs():
    with app.app_context():
        print("[Cron] Starting daily background jobs (Birmingham UK timezone)...")
        t_cobrancas = _gerar_cobrancas_semanais_logic()
        t_quarentenas = _processar_quarentenas_logic()
        print(f"[Cron] Finished. {t_cobrancas} rent charges generated, {t_quarentenas} deposit holds processed.")

if __name__ == '__main__':
    uploads_dir = os.path.join(basedir, 'static', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Start APScheduler with Europe/London timezone
    scheduler = BackgroundScheduler(timezone=pytz.timezone('Europe/London'))
    scheduler.add_job(func=run_daily_jobs, trigger="cron", hour=1, minute=0)
    scheduler.start()
    
    app.run(debug=True, host='0.0.0.0', use_reloader=False)
