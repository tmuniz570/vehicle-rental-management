# Plano de Implementação: Arquitetura Limpa para Módulo de Claims & Storage com Permissões Modulares

Este documento reflete a diretriz de **código limpo, direto e sem gambiarras**, uma vez que o sistema ainda está em fase de pré-produção.
Tudo será desenvolvido, executado e testado **exclusivamente no ambiente local** até sua aprovação expressa para deploy.

---

## 1. Arquitetura Limpa de Usuários & Permissões (Adeus campo genérico `role`)

Substituímos o conceito ambíguo de `role` por **permissões booleanas explícitas** no modelo `User` (`database.py`):

```python
class User(db.Model, UserMixin):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Permissões Modulares Diretas e Limpas:
    is_admin = db.Column(db.Boolean, default=False, nullable=False)      # Gestão de usuários, logs e configs
    perm_alugueis = db.Column(db.Boolean, default=True, nullable=False)  # Frota, Clientes, Contratos, Vistorias, Financeiro
    perm_claims = db.Column(db.Boolean, default=False, nullable=False)   # Módulo Claims, Pátio/Storage e Invoices
```

### Regras de Acesso Limpas no Backend:
- `@admin_required`: Exige `current_user.is_admin == True`
- `@alugueis_required`: Exige `current_user.perm_alugueis == True or current_user.is_admin == True`
- `@claims_required`: Exige `current_user.perm_claims == True or current_user.is_admin == True`

---

## 2. Modelo de Dados Limpo: Tabela `claims`

Tabela modelada especificamente para o negócio de acidentes da FF Motors com as claim companies (**McAms**, **ALS**, **365**):

```python
class Claim(db.Model):
    __tablename__ = 'claims'
    
    id = db.Column(db.Integer, primary_key=True)
    claim_number = db.Column(db.String(50), nullable=False, index=True)  # Ref da seguradora
    empresa_parceira = db.Column(db.String(50), nullable=False)         # McAms, ALS, 365, etc.
    
    # Dados da Moto e Cliente
    cliente_nome = db.Column(db.String(100), nullable=False)
    cliente_telefone = db.Column(db.String(30))
    placa = db.Column(db.String(20), nullable=False, index=True)
    modelo_moto = db.Column(db.String(100))
    
    # Status Geral do Processo
    status = db.Column(db.String(30), default='Em Aberto', nullable=False) # 'Em Aberto', 'Concluído', 'Cancelado'
    
    # 1. Ciclo de Aprovação & Indicação (Prazo: 14 dias a partir da aprovação)
    data_acidente = db.Column(db.Date)
    data_aprovacao = db.Column(db.Date)                                  # Gatilho inicial
    valor_indicacao = db.Column(db.Numeric(10, 2), default=0.0)         # Referral Fee
    prazo_indicacao = db.Column(db.Date)                                 # data_aprovacao + 14 dias
    status_indicacao = db.Column(db.String(20), default='Pendente')      # 'Pendente', 'Pago', 'Atrasado'
    data_pagamento_indicacao = db.Column(db.Date)
    
    # 2. Ciclo de Storage (Prazo: 28 dias a partir da aprovação para liberar moto)
    data_entrada_storage = db.Column(db.Date)
    prazo_liberacao_storage = db.Column(db.Date)                          # data_aprovacao + 28 dias
    data_liberacao_storage = db.Column(db.Date)                          # Quando a moto de fato saiu do pátio
    status_storage = db.Column(db.String(30), default='No Pátio')        # 'No Pátio', 'Liberado', 'Invoice Enviado', 'Pago'
    valor_diaria_storage = db.Column(db.Numeric(10, 2), default=15.00)   # Taxa de diária (£/dia)
    dias_storage = db.Column(db.Integer, default=0)                      # Dias totais apurados
    valor_total_storage = db.Column(db.Numeric(10, 2), default=0.0)      # dias_storage * valor_diaria_storage
    
    # 3. Ciclo de Faturamento do Storage (Prazo: 14 dias a partir do envio do invoice)
    data_envio_invoice = db.Column(db.Date)                              # Quando Aline enviou
    prazo_pagamento_invoice = db.Column(db.Date)                         # data_envio_invoice + 14 dias
    status_pagamento_storage = db.Column(db.String(20), default='Pendente') # 'Pendente', 'Pago', 'Atrasado'
    data_pagamento_storage = db.Column(db.Date)
    
    # Metadados
    observacoes = db.Column(db.Text)
    criado_por_nome = db.Column(db.String(100))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
```

---

## 3. Isolamento Cauteloso de Alertas e Telas

1. **Dashboard Principal (`/api/dashboard`):**
   - Se `current_user.perm_claims` for falso (e não for admin), o JSON **não conterá nenhuma chave** sobre claims ou storage.
   - Os cards de alerta só aparecem no HTML caso o usuário tenha permissão.

2. **Alertas Específicos para quem tem Permissão:**
   - 🔴 **Indicações Vencidas**: Claims aprovados há mais de 14 dias sem baixa de pagamento.
   - 🟡 **Storage em Risco (28 dias)**: Motos retidas há mais de 21 dias sem liberação registrada.
   - 🔴 **Invoices Vencidos**: Invoices enviados há mais de 14 dias sem confirmação de pagamento.
   - 📋 **Ação Pendente**: Motos que já foram liberadas mas a Aline ainda não registrou o envio do invoice.

3. **Navegação (Layout):**
   - A aba `Claims & Storage` só é injetada no DOM se o usuário tiver `perm_claims` ou `is_admin`.

---

## 4. Gestão de Usuários Modular (`/usuarios`)

- Reformulação dos modais de **Criar Usuário** e **Editar Usuário**:
  - Removemos o `select` de papel único.
  - Adicionamos 3 checkboxes/toggles estilizados e claros:
    - ☑️ **Módulo Aluguéis** (Frota, Clientes, Contratos, Vistorias)
    - ☑️ **Módulo Claims & Storage** (Processos McAms/ALS/365 e Invoices)
    - ☑️ **Acesso Administrador** (Gerenciar contas de usuários e auditoria)

---

## 5. Interface do Módulo `Claims & Storage` (`/claims`)

Uma interface moderna, clean e com foco na usabilidade da Aline:
- **Resumo Financeiro e Operacional** no topo (Total a receber de indicação, motos no storage, total a receber de diárias).
- **Lista Inteligente com Badges Coloridos de Prazos**:
  - Dias restantes calculados automaticamente.
  - Botão de ação rápida: "Registrar Pagamento de Indicação", "Registrar Liberação de Moto", "Registrar Envio de Invoice", "Dar Baixa em Storage".
- **Geração de Invoice de Storage**:
  - Cálculo automático de `(Data Liberação - Data Entrada) × Diária (£15)`.
  - Página de impressão/PDF timbrada com os dados da FF Motors para envio à seguradora.

---

## 6. Passos de Execução (100% Local)

1. **Migração Local Limpa do Banco de Dados**:
   - Ajustar modelos no `database.py`.
   - Atualizar a base local `ffmotors.db` adicionando as novas colunas e a nova tabela `claims`.
   - Garantir que o usuário do Fernando (`tmuniz570@gmail.com`) já fique configurado com `is_admin=True`, `perm_alugueis=True` e `perm_claims=True`.
2. **Atualização da Gestão de Usuários**:
   - Ajustar rotas de criação/edição em `app.py` e os modais em `templates/usuarios.html` e `static/js/usuarios.js`.
3. **Backend de Claims**:
   - Rotas `/claims`, `/api/claims`, `/claims/invoice/<id>` com todos os cálculos automáticos de prazos.
4. **Frontend de Claims**:
   - Template `templates/claims.html` e script `static/js/claims.js`.
5. **Ajuste Cauteloso de Alertas no Dashboard e Layout**:
   - Ocultação estrita de menus e alertas para quem não tiver permissão.
6. **Testes Locais**:
   - Testar login com usuário Staff (somente aluguéis).
   - Testar login com usuário Aline (aluguéis + claims).
   - Testar login Admin (acesso total).
   - Simular um claim completo (Aprovação -> 14 dias -> Liberação 28 dias -> Invoice -> Pagamento).
