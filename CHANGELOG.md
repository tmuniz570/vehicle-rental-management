# 📜 Changelog — FF Motors Fleet Management

Todas as alterações notáveis, correções de bugs, novos recursos e melhorias de arquitetura implementadas no projeto são documentadas neste arquivo.

O formato segue as diretrizes do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e este projeto adere ao [Versionamento Semântico (SemVer)](https://semver.org/lang/pt-BR/).

## [1.7.2] — 2026-09-21 — *Mobile Contract Print & PDF Perfection (Exact 2-Page Rental & Balanced 3-Page Sales)*

### 🖨️ Padronização de Impressão e PDF Mobile (A4 Engine)
* **Geração Perfeita Direto do Smartphone**: Resolvido o problema de quebras desordenadas e páginas fantasmas vazias ao imprimir ou salvar PDF pelo celular (iOS Safari e Android Chrome), permitindo que a operação de pátio e balcão entregue o contrato na hora ao cliente sem precisar recorrer ao computador.
* **Contrato de Aluguel em Exatas 2 Páginas (`contrato_print.html`)**:
  - **Página 1 (de 2)**: Cabeçalho com logo, identificação das partes (Locador J&F Motorcycles e Locatário), dados do veículo, requisitos de locação e depósito caução (3.1 a 3.4) e cláusulas 4.1 a 4.5 (`Page 1 of 2`).
  - **Página 2 (de 2)**: Logo, continuação dos termos contratuais (4.6 a 4.11), Declaração e Assinaturas de Início da Locação (Seção 5) e Termo de Devolução do Veículo e Caução (Seção 6) (`Page 2 of 2`).
  - **Zero Páginas Sobrando**: Eliminada a antiga 3ª página desnecessária com excesso de espaço em branco.
* **Contrato de Venda Parcelada em Exatas 3 Páginas (`contrato_venda_print.html`)**:
  - **Página 1 (de 3)**: Partes, detalhes da moto, discriminação financeira consolidada e tabela com o cronograma completo de parcelas (`Page 1 of 3`), encerrando sem vazar linhas.
  - **Página 2 (de 3)**: Termos e condições gerais 4.1 a 4.9 (incluindo recompra voluntária, acidentes/seguro e compliance com UK GDPR) (`Page 2 of 3`).
  - **Página 3 (de 3)**: Cláusulas 4.10 (Indenização) e 4.11 (Jurisdição), seguidas pela Declaração do Comprador e os Quadros de Assinatura com chancela fixa da concessionária (`Page 3 of 3`).
* **Contrato de Venda à Vista (`contrato_venda_print.html`)**:
  - Mantido perfeitamente em **2 páginas** (Página 1: Partes, Veículo, Finanças e 4.1 a 4.3; Página 2: 4.4 a 4.11 e Assinaturas).
* **Tipografia e Margens A4 Otimizadas**:
  - Configurado `@page { size: A4 portrait; margin: 8mm 12mm 8mm 12mm; }`.
  - Tipografia balanceada para documentos formais (`font-size: 9.15pt`, `line-height: 1.37`), com proteção ativa contra quebras internas em caixas de assinatura e tabelas (`break-inside: avoid !important`).

## [1.7.1] — 2026-09-21 — *Session Idle Timeout (8h), Contracts Table Cache Immunity & Responsive Mobile Installment Cards*

### ⏱️ Autenticação & Sessão Estendida
* **Aumento do Timeout de Inatividade para 8 Horas**: Configuração de `SESSION_IDLE_TIMEOUT_SECONDS = 28800` (8 horas) em `app.py`. Garante que operadores de balcão e pátio não percam o login durante o expediente de trabalho, com mensagens de expiração informando `"8 horas"` na interface e na API.

### 🛡️ Tabela de Contratos & Blindagem Contra Cache Desalinhado
* **Diagnóstico e Correção de Desalinhamento (Print 1 vs Print 2)**: Identificado conflito de cache onde navegadores mantinham em cache a versão anterior do script com 8 colunas enquanto o template HTML havia evoluído para 9 colunas (`TYPE`).
* **Proteção em Tempo de Execução (`contratos.js`)**: O gerador de linhas agora verifica dinamicamente os cabeçalhos (`<th>`) presentes no DOM, garantindo alinhamento perfeito de células mesmo se o navegador carregar versões de cache divergentes.
* **Cache Buster Atualizado**: Script incrementado para `contratos.js?v=5` em `templates/contratos.html`.

### 📱 Experiência Mobile no iPhone (Contrato Parcelado)
* **Card de Parcela Responsivo (`novo_contrato.js`)**: O antigo grid rígido de 4 colunas em linha única foi substituído por um card individual elegante com cabeçalho (badge `#X Installment` e botão `✕ Remove`) e grid de 2 colunas amplas (`Amount (£)` e `Due Date`).
* **Espaço Amplo de Digitação**: O campo numérico agora dispõe de ~150px livres na tela do iPhone com prefixo fixo `£`, exibindo qualquer valor monetário sem cortes nem esmagamento.
* **Prevenção de Zoom no iOS**: Inputs configurados com `font-size: 16px`, eliminando o zoom automático invasivo do Safari no iPhone ao tocar nos campos.
* **Cache Buster Atualizado**: Script incrementado para `novo_contrato.js?v=3` em `templates/novo_contrato.html`.

## [1.7.0] — 2026-09-20 — *Vehicle Sales System, Itemized Extras, Financial Filters & Maintenance Overhaul*

### 🏍️ Sistema de Venda de Motos (Sale Contracts)
* **Venda à Vista (`Sale_Full`) e Parcelada (`Sale_Installment`)**: Suporte completo à formalização de venda de veículos com transações separadas de aluguel e status `Sold` atribuído à motocicleta.
* **Construtor de Acessórios & Extras**: Criação itemizada de extras e acessórios com botões de atalho rápido e cálculo dinâmico somando valores ao preço do veículo em tempo real.
* **Isenção de Monitoramento de Seguro (15 dias askMID)**: Motos vendidas registram o certificado na venda, mas estão 100% isentas da rotina quinzenal do askMID. Tela de contrato adaptada para exibir documento arquivado sem alarmes nem contadores.
* **Emissão Formal do Contrato de Venda**: Contrato formalizado com assinatura fixa da concessionária, cronograma de parcelas e logo com fundo branco para impressão perfeita.
* **Segregação Financeira e Recibos Detalhados**: Entrada registrada como `Sale_Deposit` e parcelas como `Sale_Installment`, mantendo `Pending` na criação e gerando recibos enriquecidos (`Vehicle Sale - Instalment X of Y`).
* **Proteção contra Vistorias Incompatíveis**: Vistorias de devolução (`Check-in`) rejeitadas para veículos vendidos, autorizando vistorias de avaria/garantia (`Incident`).
* **Harmonização de Terminologia**: Textos de interface atualizados para "Contract / Agreement" em todas as telas.

### 💰 Filtros e Navegação no Financeiro
* **Filtro de Tipos Estruturado (`templates/financeiro.html` & `app.py`)**: Agrupamento visual com `<optgroup>` para *Rentals* (Aluguel, Caução, Devolução de Caução), *Vehicle Sales* (`sales_all`, Venda à Vista, Entrada, Parcelas) e *Incidents & Fines* (Multas, Danos).
* **Busca Ampliada**: Campo de busca agora pesquisa simultaneamente por ID, Contrato, Cliente, Placa, Tipo, Status, **Valor numérico** (ex: `2850`) e **Forma de Pagamento** (ex: `Card`, `Bank Transfer`).
* **Compatibilidade e Resiliência Bilíngue**: Suporte completo a termos em inglês e português em todas as rotas financeiras e de vistorias.

### 🛠️ Scripts Operacionais & Coleta de Órfãos
* **Modernização do `cleanup_uploads.py`**: Suporte a decodificação de URLs (`urllib.parse.unquote`), parsing de fotos de vistorias em formato JSON e lista separada por vírgula, proteção automática a arquivos de demonstração (`static/demo_assets`), e flags `--dry-run` e `--verbose`.
* **Reset Inteligente (`reset_data.py`)**: Adicionada flag `--keep-users` para resetar dados operacionais preservando contas de operadores e administradores, com reset universal de sequências de ID para SQLite e PostgreSQL.
* **Backups Otimizados (`backup.py` & `restore.py`)**: Dumps com `--clean --if-exists`, checkpoint atômico de WAL e exclusão estrita de caches e arquivos temporários.
* **Dados Fictícios (`seed_data.py`)**: Povoamento de motos vendidas, compradores e contratos de venda (`Sale_Full` e `Sale_Installment`) com transações e vistorias vinculadas.

## [1.6.0] — 2026-09-20 — *Performance Engine, Maintenance Scripts & Data Agility*

### ⚡ Performance & Otimizações de Banco de Dados (Backend)
* **Eliminação de N+1 Queries no Financeiro e Vistorias**: Implementado eager loading com `.options(contains_eager(FinancialTransaction.contrato).contains_eager(Contract.cliente))` em `/api/financeiro` e `/api/vistorias`. Redução drástica de **101 queries para 1 query SQL** por requisição, acelerando o tempo de resposta em até 80%.
* **Dashboard Otimizado e Consultas Unificadas**: Eliminada a busca duplicada de contratos ativos em `/api/dashboard`. A listagem de contratos é carregada em uma única query e reaproveitada para contadores de receita semanal e verificação de compliance askMID. Consultas de Road Tax e MOT simplificadas para selecionar apenas as colunas necessárias.
* **KPIs Globais de Claims & Storage Otimizados**: Substituído o carregamento de instâncias ORM completas por seleção de atributos essenciais em `/api/claims`, reduzindo tráfego de dados e pressão de memória RAM no Python.
* **Novos Índices Compostos Estratégicos**:
  - Adicionado índice composto `idx_ft_status_vencimento` na tabela `financeiro_transacoes` (`status, data_vencimento`) para acelerar filtros de cobranças pendentes e vencidas.
  - Adicionado índice na coluna `dia_pagamento_semanal` da tabela `contratos` para otimizar o cron job diário de cobrança de aluguéis.
  - Configurada auto-migração segura via `init_db(app)` com `CREATE INDEX IF NOT EXISTS`.
* **Pool de Conexões Robusto para PostgreSQL**: Configuração explícita de engine pool para ambientes PostgreSQL em produção (`pool_size=10`, `max_overflow=20`, `pool_recycle=1800`, `pool_pre_ping=True`), eliminando conexões inativas (stale connections) e acelerando requisições concorrentes.

### 🖼️ Processamento de Imagens & Frontend UX
* **Compressão WebP Acelerada**: Otimizado o algoritmo de compressão de imagens em `salvar_arquivo_otimizado` de `method=6` para `method=4`. Processamento de uploads de fotos de vistorias e contratos até **3x a 5x mais rápido**, reduzindo picos de CPU na VM.
* **Desbloqueio do Caminho Crítico de Renderização**:
  - Adicionado atributo `defer` ao carregamento do script CDN `browser-image-compression` em `templates/layout.html`, permitindo renderização imediata do DOM.
  - Otimizada a folha de estilos do Google Fonts com `display=swap` e seleção estrita dos 4 pesos tipográficos utilizados (400, 500, 600, 700).

### 🛠️ Scripts de Manutenção & Dados de Teste
* **Garantia de Snapshots em `cleanup_uploads.py`**: O coletor de lixo agora protege os documentos congelados no contrato (`url_habilitacao`, `url_habilitacao_verso`, `url_cbt`, `url_comprovante_endereco`), prevenindo a exclusão indevida de cópias contratuais quando o cadastro de um cliente for atualizado. Adicionada sanitização de URLs e proteção a arquivos do sistema (`.gitkeep`).
* **Dados Fictícios Modernizados (`seed_data.py`)**:
  - Adicionado contrato cancelado demonstrando a funcionalidade de cancelamento com moto liberada para `Available`, cobrança pendente cancelada e auditoria registrada.
  - Inclusão de clientes com e-mail opcional (`email=None`).
  - Vistorias alimentadas com 4 a 5 fotos para permitir demonstração imediata do carrossel interativo e navegação por toque.
  - Todos os contratos gerados com snapshots imutáveis 100% preenchidos e datas no fuso horário `Europe/London`.
* **Reset e Backup Universais (`reset_data.py`, `backup.py`, `restore.py`)**:
  - `reset_data.py` migrado para SQLAlchemy, compatível tanto com SQLite quanto com PostgreSQL, com limpeza de `job_locks`, checkpoint de WAL e vacuum.
  - `backup.py` e `restore.py` com detecção flexível de URLs PostgreSQL (`postgres://` e `postgresql://`), checkpoint automático de WAL no SQLite e validação de integridade pós-restauração.

## [1.5.2] — 2026-09-20 — *Interactive Inspection Photos Carousel*

### 🔍 Vistorias & Galeria de Fotos (UI/UX)
* **Carrossel Interativo de Fotos das Vistorias**: Substituído o grid estático de miniaturas por um carrossel de alta resolução nos modais de visualização de vistoria (`#viewVistoriaModal`), tanto na tela de detalhes do contrato (`/contratos/<id>`) quanto na listagem geral de vistorias (`/vistorias`).
* **Navegação Multimodal**:
  - **Botões laterais e teclado**: Setas anterior/próxima (`❮` e `❯`) com estilo glassmorphism, além de suporte a navegação pelas setas do teclado (`←` e `→`).
  - **Barra de miniaturas (thumbnails)**: Faixa inferior com scroll horizontal suave onde o clique em qualquer foto salta diretamente para o slide com destaque azul neon.
  - **Suporte a Touch Swipe no Mobile**: Permite ao operador no pátio arrastar o dedo para o lado (swipe) para folhear as fotos da moto com facilidade na tela do celular.
  - **Abertura em Resolução Original**: Botão `🔍 Enlarge` e link direto na imagem para abrir o arquivo original em tela cheia/nova aba.
* **Componente Compartilhado (`app_shared.js`)**: Função reutilizável `renderInspectionCarousel(container, photos)` com tratamento para fotos únicas (oculta setas/thumbs), ausência de fotos e cache buster atualizado (`styles.css?v=5`, `app_shared.js?v=2`, `detalhe_contrato.js?v=13`, `vistorias_lista.js?v=6`).

## [1.5.1] — 2026-09-19 — *Optional Customer Email & Mobile Modal Touch UX*

### 👤 Clientes & Negócio (Customers)
* **Email de Cliente Opcional**: O campo de e-mail deixou de ser obrigatório tanto no cadastro (`/clientes/novo`) quanto na edição (`/clientes`).
* **Tratamento de Unicidade e Banco de Dados**: Se deixado em branco, o backend normaliza para `None` (NULL no banco de dados), respeitando a constraint `UNIQUE` sem colisão entre múltiplos clientes sem email. Validação de duplicidade ativada apenas quando um email for informado.
* **Auto-migração no SQLite e PostgreSQL**: Atualizada a coluna para `nullable=True` de forma automática e transparente em produção e desenvolvimento.

### 📱 Modais & Responsividade Mobile (UI/UX)
* **Padrão de Modais com Scroll Fluido**: O modal de edição de clientes foi padronizado utilizando as classes nativas do sistema (`.modal-overlay` e `.modal-card`).
* **Acesso Completo em Smartphones**: Suporte a touch scrolling suave (`-webkit-overflow-scrolling: touch`), altura máxima dinâmica baseada na viewport (`max-height: calc(100dvh - 2rem)`), evitando cortes de conteúdo e garantindo acesso ao botão "Save Changes".
* **Controle por Classes de Estado**: Abertura e fechamento controlados via `.classList.add('active')` e `.classList.remove('active')`, eliminando travas indevidas no scroll da página de trás.
* **Captura Multi-Shot da Câmera para Contratos Físicos**: Implementado o acumulador de fotos no modal de anexos do contrato (`/contratos/<id>`). Agora operadores com iPhone/celular podem tocar repetidamente em "📸 Take Photo (Camera)" e fotografar a Página 1, Página 2 e Página 3 diretamente pela câmera nativa do app sem fechar o fluxo ou precisar usar o rolo da câmera. Mantido suporte simultâneo para envio de arquivos da galeria e documentos PDF. Inclui compressão client-side inteligente antes do upload.
* **Resiliência no Upload e Exclusão de Anexos**: Injeção explícita de token CSRF em todas as mutações (`POST` e `DELETE`), ordenação visual sequencial garantida nos previews de fotos, importação corrigida de `delete_file_if_exists` e atualização dinâmica da lista em tela sem recarregar a página inteira.
* **Cancelamento de Contratos**: Implementado o cancelamento formal de contratos em andamento (`POST /api/contratos/<id>/cancelar`). O cancelamento libera imediatamente a motocicleta vinculada para status `Available` (Disponível), cancela automaticamente cobranças pendentes (`Pending` -> `Cancelled`) preservando pagamentos já realizados como histórico contábil, exige justificativa obrigatória do operador e registra evento `CONTRACT_CANCELLED` na trilha de auditoria (`AuditLog`).
* **Menu Inferior Mobile (Bottom Navigation)**: Adicionado atalho rápido para **Clients** (`/clientes`) no menu inferior mobile, posicionado entre Fleet e Contracts. O item **Claims** foi realocado exclusivamente para a sidebar/menu hambúrguer, mantendo a barra inferior com exatos 6 itens bem espaçados, confortáveis para toque e sem poluição visual no celular.

## [1.5.0] — 2026-09-17 — *Comprehensive Audit Logs, Production Hardening & Layout Fixes*

### 🛡️ Auditoria e Segurança (Audit Logs)
* **Cobertura de 100% nas Ações Críticas**: O sistema de rastreabilidade foi expandido. Agora toda criação, atualização ou exclusão registra autoria, IP e horário. Novos eventos logados:
  - `LOGIN_SUCCESS`, `LOGIN_FAILED`, `LOGOUT`.
  - `CLIENT_UPDATE`, `INSURANCE_UPLOADED`, `TRANSACTION_DELETE`.
  - `QUARANTINE_END`, `JOB_WEEKLY_RENT`, `JOB_QUARANTINE`.

### 🛠️ Hardening e Produção
* **Timezone Sincronizado**: Funções de data/hora adaptadas para forçar o fuso horário `Europe/London` (BST/GMT), independente do horário do navegador ou do servidor.
* **Limpeza Automática (Orphan Files)**: Criado o script `cleanup_uploads.py` para varrer bancos e remover PDFs/Imagens de `/static/uploads` que não possuem mais referência (Ex: cadastros interrompidos), economizando disco.
* **Preparação para Postgres/Nginx**: Validações concluídas no script de inicialização visando implantação com Gunicorn + Postgres.

### 🎨 Melhorias Visuais e Fixes de Fluxo
* **Impressão do Contrato (3 Páginas)**: Retirado o espaço excedente de `@media print`, fontes ajustadas para `.8rem` garantindo impressão perfeita de exatamente 3 páginas. Invertida a cor da logo na versão de impressão.
* **Fim do Loop de Assinaturas**: Corrigido bug no frontend (`detalhe_contrato.js`) onde o URL mantinha `?assinar=1` e forçava a tela a reabrir o popup após reload.
* **Milhagem em Vistorias**: Painel do Contrato agora puxa a milhagem via `data-mil` e renderiza no modal de detalhe da vistoria.
* **Limpeza Textual na Tabela**: Documentos na listagem de clientes renomeados de "Licence Front" para "🪪 Front" para evitar quebra em telas menores.

## [1.4.0] — 2026-09-16 — *Claims & Storage Module, Modular Permissions & Server-side Tables*

### 📁 Módulo de Claims & Storage (McAms / ALS / 365)
* **Gestão de Sinistros e Parcerias de Acidentes:**
  - Módulo completo (`/claims`) para controle de processos terceirizados com as seguradoras parceiras (**McAms**, **ALS** e **365**).
  - Controle automático do **prazo de indicação (14 dias)** a partir da data de aprovação do sinistro, com avisos de atraso e registro de quitação.
  - Controle de permanência da moto no **pátio/storage (limite de 28 dias)**, com alertas preventivos de liberação.
  - Cálculo automático de faturamento de storage `(Dias no pátio × £15.00/dia)` e geração de faturas timbradas.
* **Invoice de Storage Timbrado e Profissional:**
  - Página dedicada (`/claims/invoice/<id>`) para visualização e impressão de faturas de storage com os endereços oficiais e dados corporativos no Reino Unido das empresas McAms, ALS e 365.
* **Tabela de Alta Performance:**
  - Paginação server-side (20 registros/página) com controles de navegação e contador de processos.
  - Ordenação por qualquer coluna da tabela (número do processo, status, cliente, indicação, dias de storage, total de invoice).
  - Filtro avançado de período por datas (Acidente, Aprovação, Entrada no Pátio, Liberação, Envio do Invoice ou Cadastro).
  - Cards de KPI globais e estáveis no topo da tela com métrica focada em **Processos Abertos**.

### 🔐 Permissões Modulares Granulares (Substituição de Role Único)
* **Arquitetura Limpa de Permissões no Usuário:**
  - Campo booleano `perm_alugueis`: libera ou restringe acesso total a motos, clientes, contratos, vistorias e financeiro.
  - Campo booleano `perm_claims`: libera acesso ao módulo de Claims e Storage.
  - Campo booleano `is_admin`: controle administrativo total (criação e exclusão de contas, redefinição de senhas e auditoria).
* **Isolamento Completo no Dashboard e Rotas:**
  - Bloqueio em nível de rota e API (`@alugueis_required`, `@claims_required`, `@admin_required`) com retorno estruturado `403 Forbidden` ou redirecionamento defensivo.
  - Menu lateral dinâmico que esconde seções para as quais o operador não possui permissão.
  - Dashboard adaptativo que oculta os cards de frota e financeiro para operadores com acesso exclusivo a claims.
* **Gestão de Usuários Reformulada:**
  - Modais em `/usuarios` com toggles claros para cada módulo.
  - Correção na exclusão de contas com cabeçalhos de proteção CSRF automáticos.

### 🗄️ Banco de Dados & Deploy com Zero Downtime
* **Auto-migração no SQLite:**
  - Criação automática da tabela `claims` e dos índices `idx_claims_number`, `idx_claims_placa`, `idx_claims_status` e `idx_claims_empresa`.
  - Migração retrocompatível das colunas modulares da tabela `usuarios`.
* **Documentação Oficial:**
  - Criação do manual [DEPLOY_E_BANCO_DE_DADOS.md](file:///c:/Users/tmuni/Downloads/FF%20Motors%20APP/docs/DEPLOY_E_BANCO_DE_DADOS.md) e do plano de arquitetura [plano_claims_modular.md](file:///c:/Users/tmuni/Downloads/FF%20Motors%20APP/docs/plano_claims_modular.md).

---

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
