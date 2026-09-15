# 📜 Changelog — FF Motors Fleet Management

Todas as alterações notáveis, correções de bugs, novos recursos e melhorias de arquitetura implementadas no projeto são documentadas neste arquivo.

O formato segue as diretrizes do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e este projeto adere ao [Versionamento Semântico (SemVer)](https://semver.org/lang/pt-BR/).

## [1.3.0] — 2026-09-15 — *Security Hardening, Database Concurrency & Performance Suite*

### 🛡️ Segurança Web Avançada & Proteção de Dados
* **Whitelist Estrita de Uploads de Arquivos:**
  - Permitidos exclusivamente arquivos de imagem e documentos seguros: `.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf`.
  - Bloqueio e rejeição estrita (HTTP 400) em todos os endpoints de upload (`clientes`, `contratos`, `vistorias`, `quarentena`) para extensões perigosas como `.svg`, `.html`, `.htm`, `.exe`, `.sh`, `.php`.
  - Proteção na rota de entrega estática `/static/uploads/...` aplicando `Content-Security-Policy: default-src 'none'; sandbox` e cabeçalho `X-Content-Type-Options: nosniff`.
* **Neutralização Completa de Cross-Site Scripting (XSS):**
  - Implementada sanitização com `escapeHtml()` em todas as interpolações dinâmicas de tabelas e modais nos arquivos JavaScript (`clientes.js`, `contratos.js`, `financeiro.js`, `detalhe_contrato.js`, `motos.js`, `vistorias_lista.js`).
* **Rate Limiting de Login (10 Tentativas Máximas):**
  - Limitador em memória thread-safe (`threading.Lock`) que restringe tentativas falhas de login por IP.
  - Permite até 10 tentativas incorretas dentro de uma janela de 15 minutos; a 11ª tentativa é bloqueada com HTTP `429 Too Many Requests`.
  - Login bem-sucedido zera imediatamente o histórico de tentativas do IP.
* **Logout Seguro via POST com CSRF:**
  - Rota `/logout` atualizada para aceitar requisições `POST` validadas por token CSRF, mantendo compatibilidade com `GET`.
  - Formulários de logout atualizados no cabeçalho mobile e barra lateral desktop em `layout.html`.
  - Rota `logout` adicionada à lista de rotas públicas para evitar loops de redirecionamento.
* **Timeout de Inatividade de Sessão (Idle Session Timeout de 60 Minutos):**
  - Implementado monitoramento de inatividade no hook global `check_authentication` (`@app.before_request`). Se um operador passar mais de 60 minutos sem realizar requisições, a sessão é automaticamente invalidada no servidor e desconectada (`logout_user()`).
  - Redirecionamento para a tela de login exibindo alerta visual de segurança: *"Sua sessão expirou por inatividade após 60 minutos. Por segurança, faça login novamente."*.
  - Endpoints de API (`/api/...`) respondem com HTTP `401 Unauthorized` estruturado `{"error": "SessionExpired", ...}`.
  - Checkbox *"Keep me signed in"* na tela de login desmarcado por padrão para impedir permanência acidental de acesso.
  - Duração máxima do cookie de persistência (`REMEMBER_COOKIE_DURATION`) e sessão permanente (`PERMANENT_SESSION_LIFETIME`) limitada a **12 horas** (1 turno de trabalho), prevenindo logins ativos durante a noite.
  - Parametrizável via variável de ambiente `SESSION_IDLE_TIMEOUT_SECONDS` (padrão: 3600 segundos).
* **Alteração de Senha para Todos os Usuários (Self-Service Password Change):**
  - Adicionado modal global *"Alterar Minha Senha"* em `layout.html`, acessível para qualquer operador autenticado (Staff ou Admin) diretamente no rodapé da barra lateral desktop e no cabeçalho mobile.
  - Endpoint seguro `@app.route('/api/perfil/alterar-senha', methods=['POST'])` com `@login_required` e validação CSRF.
  - Validações de segurança: exigência da senha atual correta (`check_password`), tamanho mínimo de 6 caracteres, confirmação de senha e proibição de reutilizar a mesma senha.
  - Registro de auditoria automático (`AuditLog` com ação `PASSWORD_CHANGE`).
  - Alternância de visualização de senha (mostrar/ocultar 👁️) e feedback visual instantâneo sem recarregar a página.

### ⚡ Performance & Otimização de Consultas (Zero N+1)
* **Eliminação de Consultas N+1 no Dashboard:**
  - O cálculo de receita pendente e vencida foi transferido para agregações SQL diretas (`db.func.sum(FinancialTransaction.valor)` e `db.func.count`), eliminando o carregamento de milhares de objetos em memória.
  - Eager loading implementado via `joinedload` para carregar simultaneamente contratos, clientes e veículos em vistorias e motos em manutenção.
* **Indexação Completa do Banco de Dados:**
  - Criação de 15 índices estratégicos em `database.py` cobrindo chaves estrangeiras e colunas de busca/filtro (`id_cliente`, `placa`, `status`, `data_vencimento`, `vencimento_mot`, `vencimento_tax`, `nome`, `telefone`).
  - Auto-criação de índices na inicialização (`init_db`) sem risco de perda de dados.

### 🗄️ Concorrência no SQLite & Modernização de Código
* **Ativação do Modo WAL (Write-Ahead Logging) no SQLite:**
  - Conexões configuradas com `PRAGMA journal_mode = WAL;` e `PRAGMA synchronous = NORMAL;`, permitindo leituras concorrentes simultâneas durante gravações e reduzindo travamentos de disco.
  - Ativação obrigatória de integridade relacional com `PRAGMA foreign_keys = ON;`.
  - Timeout de conexão estendido para 30 segundos (`connect_args={'timeout': 30}`).
* **Exclusão Segura de Usuários com Integridade Referencial:**
  - Desacoplamento automático de referências em `logs_auditoria` (`id_usuario = NULL`) antes da exclusão de contas, preservando a trilha histórica e evitando erros de integridade referencial com chaves estrangeiras ativas.
* **Modernização SQLAlchemy 2.0:**
  - Substituição de todas as 23 ocorrências legadas de `Model.query.get(id)` e `Model.query.get_or_404(id)` por `db.session.get(Model, id)`.

### 🕒 Confiabilidade de Jobs em Background & Fuso Horário de Londres
* **Lock de Execução Multi-Worker (`JobExecutionLock`):**
  - Criada tabela no banco para travar a execução do job diário de cobrança semanal e processamento de quarentenas.
  - Impede que múltiplos workers de servidores WSGI (como Gunicorn) executem cobranças duplicadas para os clientes na mesma data.
* **Padronização no Horário de Londres (`Europe/London`):**
  - Unificação de todas as verificações de data sob o fuso britânico através dos helpers `get_london_now()` e `get_london_date()`.
  - Agendador APScheduler configurado exatamente para disparar às **01:00 AM Europe/London**.

### 🎨 Tratamento Global de Erros (404, 500, 429)
* **Respostas Híbridas Inteligentes:**
  - Requisições para `/api/...` retornam respostas JSON estruturadas.
  - Navegação web renderiza páginas de erro modernas e responsivas no tema escuro: `templates/404.html` e `templates/500.html`.

---

## [1.2.0] — 2026-09-14 — *Production Readiness, Web Security & Fleet Operations Suite*

### 🛡️ Segurança Web e Hardening (Pilar 5)
* **Proteção Global contra CSRF:**
  - Middleware `@app.before_request` interceptando e validando todas as requisições que alteram estado (`POST`, `PUT`, `DELETE`, `PATCH`).
  - Geração de tokens criptográficos de 32 bytes (`secrets.token_hex(32)`) vinculados à sessão do operador.
  - Interceptor global no método `window.fetch` (`static/js/app_shared.js`), injetando automaticamente o header `X-CSRFToken` em todas as chamadas AJAX sem necessidade de alteração de cada script isoladamente.
  - Rejeição segura com código HTTP `400 (Bad Request)` para chamadas sem token válido.
* **Cabeçalhos de Segurança HTTP:**
  - Adicionados via middleware `@app.after_request`:
    - `X-Content-Type-Options: nosniff` (prevenção contra ataques de MIME-sniffing).
    - `X-Frame-Options: SAMEORIGIN` (proteção contra clickjacking em iframes maliciosos).
    - `X-XSS-Protection: 1; mode=block` (filtro XSS complementar).
    - `Referrer-Policy: strict-origin-when-cross-origin` (privacidade de navegação de URLs).
* **Isolamento de Segredos e Variáveis de Ambiente:**
  - Geração de chave secreta criptográfica de 64 caracteres salva no arquivo `.env`.
  - `.env` e variações adicionados explicitamente ao `.gitignore` para blindagem contra vazamento de credenciais.
  - Criação do modelo `.env.example` documentando as variáveis de ambiente sem expor dados reais.

---

### 🗄️ Banco de Dados Universal (Pilar 3)
* **Inspeção Universal de Schema com SQLAlchemy:**
  - Substituição das consultas específicas de SQLite (`PRAGMA table_info`) pelo inspetor universal `sqlalchemy.inspect(db.engine).get_columns(...)`.
  - Compatibilidade 100% agnóstica entre SQLite (desenvolvimento local) e PostgreSQL (produção comercial).
* **Normalização Automática de `DATABASE_URL`:**
  - Tratamento inteligente de strings de conexão de provedores de nuvem (Render, Heroku, Supabase), convertendo automaticamente prefixos legados `postgres://` para `postgresql://` sob SQLAlchemy 2.0+.
* **Driver de Banco em Produção:**
  - Adicionada a dependência `psycopg2-binary>=2.9.9` no `requirements.txt`.

---

### 🚀 Camada de Servidor WSGI & Deploy Cloud (Pilar 2)
* **Ponto de Entrada WSGI (`wsgi.py`):**
  - Configuração do ponto de entrada padrão expondo instâncias `app` e `application` compatíveis com os principais servidores WSGI.
  - Garantia de criação de diretórios de mídia (`static/uploads`).
  - Inicialização do agendador em segundo plano (`APScheduler`) para cobranças semanais e quarentenas com fuso horário britânico (`Europe/London`).
* **Suporte Multi-Plataforma:**
  - **Windows / Ambiente Local:** Servidor `Waitress` multi-threaded ativado com 8 workers simultâneos (`python wsgi.py`).
  - **Linux / Servidores Nuvem:** Configuração do `Gunicorn` via `gunicorn_config.py` e `Procfile` (`web: gunicorn -c gunicorn_config.py wsgi:app`), com pool de threads `gthread`, balanceamento de CPU e timeout de 120s para uploads.

---

### 💳 Gestão Financeira, Contratos e Auditoria
* **Cancelamento e Estorno de Pagamentos Concluídos:**
  - Nova ação no extrato financeiro do contrato (`detalhe_contrato.html` / `detalhe_contrato.js`) permitindo estornar pagamentos marcados como `Pago` de volta para `Pendente`.
  - Registro automático e auditável da reversão na tabela `AuditLog`, gravando o ID do operador, data/hora, IP e motivo.
* **Hub Central de Inadimplência (`/relatorio-vencidos`):**
  - Ajuste na navegação: remoção de abertura de abas desnecessárias (`target="_blank"`), mantendo a navegação fluida na mesma aba.
  - Correção do botão "Voltar" utilizando histórico inteligente do navegador.
* **Layout Reorganizado do Detalhe do Contrato:**
  - Reorganização dos 4 cards superiores em grade 2x2 balanceada (Dados do Contrato, Veículo Alugado, Cliente e Vistoria).
  - O card **Financial Statement** foi posicionado isoladamente em linha cheia exclusiva com layout expandido.
* **Enriquecimento do Card do Cliente:**
  - Inclusão do **ID do Cliente** destacado.
  - Campos de contato transformados em links funcionais:
    - Telefone com link `tel:` e atalho direto para WhatsApp (`https://wa.me/...`).
    - E-mail com link `mailto:`.
    - Endereço residencial com link direto de rota no Google Maps.
  - Links diretos com ícones para visualização de documentos (CNH e Comprovante de Residência).
  - Inclusão do ID do cliente na tabela principal de clientes (`/clientes`).

---

### 🛵 Frotas e Alertas
* **Correção no Status do Seguro:**
  - Resolução de erro assíncrono ao alternar o status do seguro entre Válido e Inválido, atualizando a interface em tempo real sem necessidade de F5.
* **Limpeza Visual do Dashboard:**
  - Remoção do card redundante "Quick Management".
  - Agrupamento e deduplicação de alertas no endpoint `/api/alertas` (evitando múltiplos avisos idênticos para a mesma moto).

---

### 🧪 Dados de Demonstração e Mídia
* **Massa de Dados Fictícia Expandida:**
  - `seed_data.py` e `reset_data.py` aprimorados com 18 motos com placas britânicas, 17 clientes, 16 contratos ativos/finalizados e 100 transações financeiras.
  - Inclusão de ativos de demonstração realistas em formato WebP comprimido (`static/demo_assets/`).

---

## [1.1.0] — 2026-09-12
- Implementação de autenticação com Flask-Login e senhas criptografadas.
- Painel de gestão de operadores e usuários (`/usuarios`).
- Trilha de auditoria interna (`AuditLog`).
- PWA instalável com navegação inferior mobile nativa.

## [1.0.0] — 2026-09-10
- Versão inicial do sistema de locação de motos FF Motors Birmingham.
- Gestão de contratos, vistorias fotográficas com compressão no cliente e extrato financeiro.
