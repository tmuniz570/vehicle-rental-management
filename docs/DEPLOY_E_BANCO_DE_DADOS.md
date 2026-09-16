# Guia de Deploy e Atualização do Banco de Dados — Módulo Claims & Permissões Modulares

Este guia documenta exatamente o que mudou, como o banco de dados se comporta na VM e os passos simples e seguros para sincronizar via GitHub para a VM.

---

## 1. Como fica a questão do Banco de Dados?

O sistema foi preparado com **migração automática e retrocompatível** (Zero Downtime / Zero Perda de Dados):

1. **O arquivo `.db` NÃO vai para o Git**:
   - O `.gitignore` ignora qualquer arquivo `*.db` ou `*.sqlite`. O banco de produção existente na VM **permanecerá intacto** com todos os clientes, motos e contratos já cadastrados.
2. **Criação Automática da Tabela `claims`**:
   - Quando o `app.py` iniciar na VM (via `systemctl restart ffmotors` ou Gunicorn), a função `init_db(app)` chamará `db.create_all()`.
   - Se a tabela `claims` ainda não existir, o SQLite criará a tabela e todos os seus índices (`idx_claims_number`, `idx_claims_placa`, etc.) instantaneamente.
3. **Auto-Migração da Tabela `usuarios`**:
   - O `database.py` possui verificação com `inspector.get_columns('usuarios')`.
   - Se as colunas `is_admin`, `perm_alugueis` e `perm_claims` ainda não existirem na VM, o sistema executa automaticamente:
     ```sql
     ALTER TABLE usuarios ADD COLUMN is_admin BOOLEAN DEFAULT 0;
     UPDATE usuarios SET is_admin = 1 WHERE role = 'admin';
     ALTER TABLE usuarios ADD COLUMN perm_alugueis BOOLEAN DEFAULT 1;
     UPDATE usuarios SET perm_alugueis = 1;
     ALTER TABLE usuarios ADD COLUMN perm_claims BOOLEAN DEFAULT 0;
     UPDATE usuarios SET perm_claims = 1 WHERE role = 'admin';
     ```
   - **Resultado**: Os usuários já existentes na VM continuam funcionando perfeitamente. Qualquer usuário com `role = 'admin'` recebe permissão total (`is_admin=True`, `perm_alugueis=True`, `perm_claims=True`).

4. **Cadastrando a Aline na VM**:
   - Você poderá cadastrá-la diretamente pela interface em `/usuarios` selecionando apenas o módulo **Claims & Storage**; OU
   - Rodando o script rápido de usuário na VM caso prefira.

---

## 2. Resumo dos Arquivos Modificados

| Arquivo | Descrição |
| :--- | :--- |
| `database.py` | Modelo `Claim`, permissões modulares no `User` (`is_admin`, `perm_alugueis`, `perm_claims`), índices de alta performance e migração automática. |
| `app.py` | Proteção estrita de rotas com `@alugueis_required`, rotas completas de `/claims`, `/api/claims` (paginação, ordenação, filtro de período e KPIs fixos), e autenticação segura nos crons. |
| `templates/claims.html` | Tela de Claims com KPI "Processos Abertos", filtros avançados de data, tabela responsiva e controles de paginação. |
| `templates/claim_invoice.html` | Template de invoice profissional para impressão com endereços oficiais de McAms, ALS e 365. |
| `static/js/claims.js` | Lógica de busca, ordenação de colunas, paginação e navegação do invoice na mesma aba. |
| `templates/index.html` | Dashboard limpo (botão duplicado removido) e isolamento dos cards para quem não possui permissão de aluguéis. |
| `templates/layout.html` | Menu lateral modular (exibe apenas os itens permitidos para o usuário logado). |
| `templates/usuarios.html` & `static/js/usuarios.js` | Modais de usuário com toggles limpos de permissões modulares. |

---

## 3. Passo a Passo do Deploy

### Passo A — No seu Computador (Local)
Fazer o commit e push das alterações para o GitHub:

```bash
git add .
git commit -m "feat: modulo claims e storage, permissoes modulares e melhorias de tabela"
git push origin main
```

---

### Passo B — Na sua VM (Servidor)
Conectar via SSH na VM e puxar as atualizações:

```bash
# 1. Entrar na pasta do projeto na VM
cd /caminho/para/o/projeto  # ex: /var/www/ffmotors ou ~/ffmotors

# 2. Fazer backup preventivo do banco SQLite existente
cp ffmotors.db ffmotors.db.bak_$(date +%Y%m%d_%H%M%S)

# 3. Puxar as atualizações do GitHub
git pull origin main

# 4. Ativar ambiente virtual e garantir dependências
source venv/bin/activate
pip install -r requirements.txt

# 5. Reiniciar o serviço da aplicação (Gunicorn / Systemd)
sudo systemctl restart ffmotors
# (ou sudo systemctl restart gunicorn / touch app.wsgi conforme sua configuração)

# 6. Checar status
sudo systemctl status ffmotors
```

Pronto! Na primeira inicialização, o banco de dados da VM atualiza a estrutura sozinho sem afetar nenhum dado existente.
