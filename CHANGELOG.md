# 📜 Changelog — FF Motors Fleet Management

Todas as alterações notáveis, correções de bugs, novos recursos e melhorias de arquitetura implementadas no projeto são documentadas neste arquivo.

O formato segue as diretrizes do [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e este projeto adere ao [Versionamento Semântico (SemVer)](https://semver.org/lang/pt-BR/).

## [1.9.24] — 2026-09-30 — *Contract Details Screen Ergonomics, Financial Progress & Contextual Intelligence*

### 💎 Experiência, Inteligência de Contexto & Finanças na Tela de Detalhes do Contrato (`/contratos/<id>`)
* **Mini-Barra de Resumo Financeiro & Progresso de Quitação (%) (`#fin_summary_panel`)**:
  - Painel de síntese financeira no topo do Extrato Financeiro com 3 métricas principais:
    - **Contract Total / Total Contratado**: Valor total da venda para contratos de venda (`Sale_Full` e `Sale_Installment`) ou total de cobranças faturadas para locações (`Rent`).
    - **Total Paid / Total Pago**: Somatório em verde de todas as cobranças já quitadas pelo cliente.
    - **Balance / Saldo Restante**: Saldo pendente em cor secundária neutra, atualizado em tempo real.
  - **Barra de Progresso de Quitação (%)**:
    - Para vendas parceladas (`Sale_Installment`): Exibe o percentual concluído (ex: `4 of 12 paid (33%)`), valor e data de vencimento da próxima parcela e badge destacado `SETTLED` ao concluir a quitação.
    - Para vendas à vista (`Sale_Full`): Indicador de compensação integral do pagamento (`CLEARED`).
    - Para locações (`Rent`): Exibe o saldo da caução retida (`Deposit Held`) e seu status de liberação.
* **Limpeza Contextual Inteligente por Modelo de Contrato**:
  - **Vendas (`Sale_Full` & `Sale_Installment`)**: Oculta automaticamente a caixa de caução de locação (`#box_deposito_info`) e mantém ocultas a assinatura de devolução e a rotina quinzenal do askMID.
  - **Compras / Aquisições (`Purchase`)**: Oculta completamente a seção de seguro de cliente (`#box_seguro_section`) e o atalho de extrato financeiro, mantendo o foco operacional na posse do documento V5C (Logbook) e no status do destino da frota.
  - **Aluguéis (`Rent`)**: Mantém integralmente todas as rotinas de locação ativas (caução retida/restituída, assinatura de devolução, monitoramento askMID de 15 em 15 dias e alteração de dia de vencimento semanal).
* **Atalho Direto para WhatsApp em Nova Guia & Remoção de Duplicidade**:
  - Removido o botão duplicado do rodapé do card de cliente (`#info_cliente_links`), mantendo um único atalho direto e limpo ao lado do número de telefone.
  - O botão de WhatsApp agora abre em nova guia (`target="_blank" rel="noopener noreferrer"`).
  - **Revisão Integral de Mensagens Prontas de WhatsApp**: Removida qualquer menção ao número de contrato (que o cliente desconhece). Todas as mensagens em Detalhes, Contratos, Financeiro, Dashboard e Frotas agora identificam o contexto pela **placa do veículo** e nome do cliente (ex: `regarding vehicle XX10YYY`).
* **Pílulas de Navegação Rápida por Seção (`.contract-nav-pills`)**:
  - Sub-header com atalhos de rolagem suave (*smooth scroll*) para navegação rápida: `👤 Overview`, `📄 Agreement & Signatures`, `💳 Financial Statement` e `📷 Inspections`.
* **API Backend Enriquecida (`/api/contratos/<id>`)**:
  - Retorno JSON enriquecido com `total_pago`, `total_pendente` e `total_faturado` calculados diretamente das transações com proteção de tipos de dados.
* **Validação Geral e Suíte de Testes**:
  - Todos os 34 testes automatizados do sistema executados e 100% aprovados, sem regressões.

## [1.9.23] — 2026-09-30 — *Contracts Hub Executive KPIs, Operational Filters & Productivity Boost*

### 🚀 Visão Executiva & Produtividade na Gestão de Contratos (`/contratos`)
* **Cards de Métricas / KPIs Interativos no Topo (`#contractsKpisGrid`)**:
  - **Active Rentals** (Aluguéis Ativos): Contratos de locação semanais vigentes.
  - **Active Sales** (Vendas Ativas): Contratos de venda parcelada (*Rent-to-Buy*) e à vista em andamento.
  - **Pre-Delivery Alert** (Alerta Pré-Entrega): Contratos ativos aguardando vistoria de check-out ou certificado de seguro antes da liberação da moto.
  - **Deposit Holds** (Cauções Retidas / Quarentena): Contratos encerrados aguardando conciliação ou devolução de caução.
  - **Missing V5C** (Aquisições Pendentes de V5C): Contratos de compra de veículos aguardando anexação do documento de propriedade (Logbook).
  - *Filtragem em 1 Clique*: Clicar em qualquer card de KPI filtra instantaneamente a tabela e destaca visualmente o card selecionado.
* **Atalho Direto para WhatsApp (💬)**:
  - Adicionado botão de WhatsApp direto na coluna do cliente para cada contrato.
  - Normaliza telefones ingleses (ex: `07...` para formato internacional `+44...`) e pré-configura mensagem com o nome do cliente e número do contrato, agilizando cobranças e comunicações do pátio.
* **Identificação Completa do Veículo (Placa + Modelo + Cor)**:
  - A coluna do veículo agora exibe a placa estilizada e, logo abaixo, a marca/modelo e cor da moto (ex: `Honda PCX 125 • White`), evitando que os operadores tenham que memorizar qual moto pertence a qual placa.
* **Cálculo em Tempo Real do Saldo Não Pago (`total_pendente` & `total_pago`)**:
  - Corrigido o comportamento anterior onde a coluna de valor exibia um saldo devedor congelado do momento da assinatura (`c.saldo_devedor`).
  - O sistema agora agrega dinamicamente todas as transações financeiras em aberto do contrato (`FinancialTransaction`), exibindo o valor real não pago (`Unpaid: £...`) que diminui instantaneamente a cada pagamento registrado, ou exibe `✓ Fully Paid` / `✓ Up to date` quando todas as pendências estiverem quitadas.
* **Indicador de Assinatura do Contrato**:
  - Selo visual rápido destacando se o contrato já foi assinado digitalmente pelo cliente (`✓ Signed`) ou se continua pendente de assinatura (`⏳ Unsigned`).
* **Filtros Avançados & Produtividade**:
  - **Filtro por Dia de Vencimento Semanal (`#filterDia`)**: Permite filtrar contratos por dia da semana (Segunda a Domingo) para organização das cobranças semanais.
  - **Filtro por Período de Retirada (`#filterDataInicio` e `#filterDataFim`)**: Busca contratos dentro de um intervalo de datas específico.
  - **Seletor de Densidade por Página (`#filterLimit`)**: Opções de 20, 50 ou 100 itens por página.
  - **Botão Limpar Filtros (`✕ Clear`)**: Reseta todos os filtros e a busca para o estado padrão com 1 clique.
* **Ações Rápidas por Linha**:
  - Botão de visualização detalhada (`View`).
  - Atalho direto para abertura/impressão do termo contratual assinado em PDF (`🖨️`).
  - Atalho direto para consulta das vistorias de entrada e saída associadas ao contrato (`🔍`).
* **Cobertura de Testes Automatizados (`tests/test_contratos_improvements.py`)**:
  - Testes unitários validando a integridade dos cálculos de KPI, novos filtros (`dia_pagamento`, intervalo de datas) e enriquecimento de dados da API. Suíte geral expandida para 34 testes automatizados 100% aprovados.

## [1.9.22] — 2026-09-30 — *Audit Trail Enrichment & Granular Operational Logging*

### 🛡️ Rastreabilidade Completa & Auditoria Enriquecida (`AuditLog`)
* **Captura de IP Real em Ambientes de Proxy Reverso**:
  - Atualizada a função central `registrar_log` para priorizar o cabeçalho `X-Forwarded-For` (enviado pelo Nginx em produção), assegurando que o IP de origem real dos clientes e operadores seja armazenado, e não apenas o IP de loopback do proxy local (`127.0.0.1`).
* **Logs Diferenciais em Modificações de Frota (`MOTO_UPDATE`)**:
  - Na rota `PUT /api/motos/<placa>`, adicionado rastreamento diferencial preciso registrando no log exatamente quais campos mudaram: cor, milhagem anterior vs nova, data de MOT anterior vs nova, data de Road Tax anterior vs nova, e ativação/desativação de SORN. Se apenas o status operacional da moto for alterado, preserva a ação canônica `MOTO_STATUS_CHANGE`.
* **Logs Enriquecidos de Clientes (`CREATE_CLIENT` & `CLIENT_UPDATE`)**:
  - `CREATE_CLIENT`: Registra nome, telefone e quais arquivos de comprovação foram anexados (CNH frente/verso, CBT, comprovante de residência).
  - `CLIENT_UPDATE`: Log diferencial registrando alterações de nome, telefone, email, endereço e novos arquivos anexados.
* **Preservação de Contexto em Exclusão de Cobranças (`TRANSACTION_DELETE`)**:
  - A exclusão física de transações financeiras em `DELETE /api/financeiro/<id>` agora pré-captura todos os metadados antes do expurgo (valor em £, tipo de débito, data de vencimento, ID do contrato, placa do veículo, nome do cliente e nota/justificativa cadastrada), garantindo auditoria forense mesmo após a remoção do registro da tabela.
* **Auditoria de Lembretes WhatsApp (`PAYMENT_REMINDER`)**:
  - Adicionado registro formal de auditoria em `POST /api/financeiro/<id>/lembrete`, documentando qual operador disparou o lembrete de cobrança via WhatsApp, o valor da cobrança, data de vencimento, cliente e contrato.
* **Auditoria de Fechamento de Caixa Diário (`CASH_CLOSING_PRINTED`)**:
  - A geração e impressão da folha executiva de fechamento de caixa (`/financeiro/fechamento-caixa/print`) agora gera log de auditoria registrando a data do fechamento, o montante total arrecadado e o operador emissor.
* **Auditoria de Transições Críticas de Sinistros (`CLAIM_UPDATE`)**:
  - Enriquecido o log de atualização de Claims em `PUT /api/claims/<id>` para registrar liberações de pátio (com dias de permanência e valor total de storage), envios de invoice para seguradoras parceiras, e recebimentos de comissão de indicação e taxas de custódia.
* **Enriquecimento de Quarentena e Seguro (`QUARANTINE_END` & `INSURANCE_UPLOADED`)**:
  - Finalizações de quarentena agora explicitam placa, cliente e status de recibo de devolução.
  - Atualizações de seguro gravam a placa do veículo e cliente beneficiado.
* **Correção e Otimização da Ordenação Server-Side (`auditTable`)**:
  - Eliminado o problema de ordenação onde a tabela ordenava apenas 20 linhas locais no DOM via JavaScript e ignorava a coluna de ações.
  - Corrigido [static/js/app_shared.js](file:///c:/Users/tmuni/Downloads/FF%20Motors%20APP/static/js/app_shared.js) para permitir ordenação em colunas marcadas explicitamente com `data-sort-field` mesmo que o título contenha "Action".
  - Implementada ordenação server-side real conectada ao banco de dados com chave secundária estável (`AuditLog.id.desc()`) para evitar salto de linhas na paginação. Indicadores visuais (`▲`/`▼`) sincronizados dinamicamente via `setTableSortIndicator`.
* **Filtros Avançados & Presets Rápidos de Data**:
  - Adicionadas pílulas de período rápido em 1 clique: `All Time`, `Today`, `Yesterday`, `Last 7 Days` e `This Month`.
  - Adicionado seletor de intervalo `From` e `To` permitindo buscar qualquer período específico de auditoria.
  - Filtro dedicado por Operador / Staff (`#auditUserFilter`) populado dinamicamente com os usuários do sistema e processos automáticos (`System`).
  - Filtro por Módulo / Entidade (`#auditModuleFilter`: Contratos, Frota, Clientes, Claims, Financeiro, Usuários).
  - Seletor de densidade de itens por página (`25`, `50`, `100`, `250`).
* **Cards de Indicadores de Auditoria (Audit KPI Cards)**:
  - Adicionados 4 cards no topo da aba de auditoria: `Events Today`, `Active Staff Today`, `Financial Ops Today` e `Security / System`.
* **Modal de Detalhes da Atividade (`#modalAuditDetail`)**:
  - Ao clicar em qualquer linha da tabela ou no botão `👁️`, um modal executivo exibe o ID do evento, data/hora exata no fuso de Londres, operador, ação, entidade alvo, IP de origem e o texto completo/diff das alterações sem truncamento.
* **Exportação para CSV (`/api/auditoria/exportar-csv`)**:
  - Adicionado botão `📥 Export CSV` permitindo o download direto da trilha de auditoria filtrada em formato CSV com UTF-8 BOM, pronto para abertura imediata no Microsoft Excel.
* **Cobertura de Testes Automatizados (`tests/test_audit_log_enrichment.py`)**:
  - Implementada suíte de testes unitários dedicada validando isolamento, CSRF, criação de logs, ordenação asc/desc no banco, filtros por período e ação, e exportação CSV. Total da suíte ampliado para 33 testes automatizados aprovados (0 erros, 0 regressões).

## [1.9.21] — 2026-09-30 — *Financial Statement PDF Report Production Hardening*

### 📱 Navegação de Relatórios na Mesma Aba & Usabilidade Mobile para iPhone (iOS Safari)
* **Abertura de Relatórios na Mesma Guia (`window.location.href`)**:
  - Relatório da Frota (`/motos/relatorio-pdf`) e Fatura de Storage (`/claims/invoice/<id>`) alterados de `window.open(..., '_blank')` para `window.location.href`, garantindo navegação contínua na mesma janela.
  - Atualizados os botões de retorno de todos os relatórios para links explícitos (`&larr; Back to Fleet`, `&larr; Back to Finance`), eliminando dependência frágil de `window.close()`.
* **Eliminação Definitiva do Auto-Zoom do iOS Safari**:
  - Implementada regra global para `@media (max-width: 768px)` com `font-size: 16px !important;` em todos os elementos `input`, `select` e `textarea`. No iOS Safari, qualquer campo com fonte inferior a 16px provoca zoom indesejado ao tocar, desorganizando a tela.
* **Viewport e Scroll Nativo nos Relatórios Imprimíveis**:
  - Adicionado `<meta name="viewport" content="width=device-width, initial-scale=1.0">` em [templates/relatorio_fleet.html](file:///c:/Users/tmuni/Downloads/FF%20Motors%20APP/templates/relatorio_fleet.html), [templates/relatorio_financeiro.html](file:///c:/Users/tmuni/Downloads/FF%20Motors%20APP/templates/relatorio_financeiro.html), [templates/relatorio_fechamento_caixa.html](file:///c:/Users/tmuni/Downloads/FF%20Motors%20APP/templates/relatorio_fechamento_caixa.html) e [templates/relatorio_vencidos.html](file:///c:/Users/tmuni/Downloads/FF%20Motors%20APP/templates/relatorio_vencidos.html), impedindo que o Safari renderize a página emulando 980px de desktop.
  - Tabelas de relatórios envolvidas em contêineres `.table-responsive` com `-webkit-overflow-scrolling: touch;`, permitindo rolagem horizontal suave no polegar.
* **Ergonomia de Toque e Modais com Dynamic Viewport (`100dvh`)**:
  - Modais ajustados com `max-height: calc(100dvh - 2rem)` e padding adaptado para as zonas seguras (`env(safe-area-inset-top)` / `env(safe-area-inset-bottom)`), evitando que a barra de navegação do iPhone corte botões de confirmação.
  - Form inputs e botões móveis com altura mínima de toque de 44px conforme diretrizes da Apple (HIG) e `touch-action: manipulation` para remover atraso de 300ms no clique.
* **Formulário de Novo Contrato Parcelado no iPhone (iOS Ergonomics)**:
  - **Proporção da Linha de Acessórios & Extras**: O campo de descrição agora expande ocupando todo o espaço restante (`minmax(0, 1fr)`), enquanto o campo de valor foi calibrado para 78px com setas de incremento ocultas (sem stepper buttons), exibindo confortavelmente 4 ou mais dígitos (ex: `£ 2500` ou `£ 9999`) sem truncamento. O valor inicial inicia limpo com placeholder `£ 0`, eliminando o incômodo de precisar apagar o zero inicial ao digitar.
  - **Ajuste Responsivo da Barra de Auto Split**: O botão "⚡ Auto Split" (`#btnGenerateSchedule`) e os seletores de quantidade/intervalo de parcelas foram reestruturados com classes responsivas (`.schedule-builder-header`, `.schedule-split-controls`), quebrando linhas graciosamente no iPhone sem transbordar horizontalmente fora da página.
  - **Admin Fee Desobstruído**: Removido o `value="0.00"` fixo do campo de Admin Fee em [templates/novo_contrato.html](file:///c:/Users/tmuni/Downloads/FF%20Motors%20APP/templates/novo_contrato.html), substituído por placeholder `0.00`. O campo agora inicia vazio e limpo para digitação direta, assumindo `0.00` de forma transparente caso não seja preenchido.

### 🛠️ Correção Crítica no Relatório Financeiro PDF (`/financeiro/relatorio-pdf`)
* **Eliminação de Erro 500 por Comparação de Timezone / Date Naive vs Aware (`TypeError`)**:
  - Em produção (PostgreSQL), comparações diretas de `t.data_vencimento < inicio_hoje` no Python causavam `TypeError: can't compare datetime.datetime to datetime.date` ou `TypeError: can't compare offset-naive and offset-aware datetimes` quando os registros retornavam com timezone ou formato date.
  - Normalização universal implementada convertendo com segurança `t.data_vencimento` para `datetime.date` no fuso de Londres (`Europe/London`) e comparando estritamente com `get_london_date()`.
* **Otimização de Performance N+1 (`contains_eager`)**:
  - A rota agora aplica `.options(contains_eager(FinancialTransaction.contrato).contains_eager(Contract.cliente))` na query com `outerjoin`, eliminando centenas de queries repetidas em lazy-load para cada linha e prevenindo exaustão de conexões ou timeout do Gunicorn/Nginx.
* **Blindagem contra Valores Nulos (Null-Safety)**:
  - Tratamento defensivo de montantes `float(t.valor or 0.0)` e formatação segura de somatórios no template Jinja2 (`relatorio_financeiro.html`) com `totais.total_valor or 0.0`, prevenindo `TypeError: must be real number, not NoneType`.
  - Fallback gracioso para dados congelados de cliente no contrato (`cliente_nome`, `cliente_telefone`) caso o registro relacional tenha sido modificado.
* **Diagnóstico e Rastreabilidade (`handle_server_error`)**:
  - Adicionado `traceback.print_exc()` no errorhandler global 500 do Flask e log detalhado de exceção na rota, assegurando visibilidade imediata em logs de serviço do Linux (`journalctl -u ffmotors`).

## [1.9.20] — 2026-09-29 — *Weekly Rent Billing Resilience, Resilient Catch-Up Engine & Purchase Agreement V5C Lifecycle*

### 🤝 Ciclo de Vida de Contratos de Compra (`Purchase`) & V5C Logbook
* **Finalização Condicionada ao V5C (`sync_purchase_contract_status`)**:
  - Contratos de compra de veículo usado (`Purchase`) apenas transitam para `Completed` quando estiverem assinados digitalmente pelo vendedor E possuírem o documento de Logbook (V5C) anexado à motocicleta (`MotorcycleV5C`).
  - Enquanto o V5C não for anexado, o contrato permanece com status `Active` e exibe alerta visual de pendência.
* **Reabertura Dinâmica se V5C for Removido**:
  - Se todos os arquivos de V5C de uma moto comprada forem excluídos, o contrato de compra reabre automaticamente para `Active` com registro de auditoria `CONTRACT_REOPENED`.
  - Ao re-anexar o documento de V5C da moto, o contrato retorna automaticamente para `Completed` com registro `CONTRACT_COMPLETED`.
* **Isenção Total de Vistoria de Check-out e askMID para Compras**:
  - Como a compra é uma entrada de veículo no estoque da oficina (e não uma saída para locação/venda), contratos de compra não exigem nem exibem alertas para vistoria de check-out (`InspectionType.CHECK_OUT`), seguro do cliente ou verificação quinzenal do askMID.
* **Alertas e Filtros no Frontend & Dashboard**:
  - **Banner de Alerta na Tela de Detalhes (`detalhe_contrato.html` / `detalhe_contrato.js`)**: Alerta dedicado em ciano destacando `LOGBOOK (V5C) REQUIRED: Purchase Agreement Incomplete` com botão de ação direta para upload do V5C.
  - **Card no Dashboard (`templates/index.html` & `/api/dashboard`)**: Bloco de conformidade exibindo contratos de compra que aguardam entrega do documento V5C pelo vendedor.
  - **Badge e Filtro na Lista de Contratos (`contratos.html` / `contratos.js`)**: Badge `📑 Needs V5C` e opção de filtro rápido `📑 Purchase: Pending V5C Logbook` (`status=pending_v5c`).

### ⚡ Motor Resiliente de Faturamento Semanal (`_gerar_cobrancas_semanais_logic`)
* **Geração Semanal Contínua (`Dia da Semana + 7`)**:
  - Para cada contrato de aluguel ativo (`Rent` + `Active`), utiliza a coluna ativa `Contract.dia_pagamento_semanal` (que reflete qualquer dia da semana original ou alterado pelo operador de 0=Segunda a 6=Domingo).
  - No dia da semana do vencimento, a rotina assegura a geração da cobrança da semana subsequente (`dia da semana + 7`), garantindo que **sempre que o cliente estiver com uma semana vencendo, a fatura da próxima já estará provisionada e visível**.
* **Auto-Recuperação e Eliminação de Vulnerabilidade "Single-Shot" (Auto-Catch-Up)**:
  - Elimina a dependência frágil de execução em segundo exato: a rotina agora inspeciona todos os contratos de aluguel ativos e verifica se a fatura do ciclo atual e do próximo ciclo (`+7`) já existem.
  - Caso o agendador tenha deixado de rodar em um dia específico (por exemplo, reinício de servidor, suspensão ou queda de worker na segunda-feira), no momento da execução subsequente o sistema detecta as faturas faltantes dos ciclos anteriores e as provisiona imediatamente sem duplicar as existentes.
* **Auto-Sincronização ao Alterar Dia de Vencimento (`PUT /api/contratos/<id>/dia-pagamento`)**:
  - Ao alterar o dia de cobrança de um contrato ativo, o endpoint dispara de imediato uma verificação pelo motor gerador para alinhar o cronograma futuro ao novo dia da semana em tempo real.
* **Fortificação do APScheduler no Gunicorn & Catch-up no Boot (`wsgi.py` & `run_daily_jobs`)**:
  - `open(lock_path, 'a+')` com fallback automático para `/tmp/.ffmotors_scheduler.lock` contra restrições de permissão de diretório.
  - Adicionado `misfire_grace_time=3600` (1 hora) prevenindo descarte de execução por desvios de relógio ou workers ocupados.
  - Adicionada thread daemon de inicialização no WSGI (`_check_and_run_startup_jobs`): no boot/deploy do serviço, executa as rotinas diárias com `force=True` no worker eleito com lock de scheduler, garantindo catch-up imediato de qualquer fatura pendente (ex: faturas de segunda-feira) mesmo que a trava diária tenha sido registrada por workers anteriores.
  - Parâmetro `force=False` adicionado em `run_daily_jobs(force=False)` permitindo execução forçada e segura sem risco de duplicação graças à idempotência inerente do motor.
* **Correção de Timezone Naive/Aware em `/api/alertas` (`listar_alertas`)**:
  - Corrigido erro `TypeError: can't subtract offset-naive and offset-aware datetimes` ao calcular `(hoje - c.data_devolucao).days` no alerta de devolução de caução (`deposit_hold_due`), utilizando conversão explícita para `.date()` em ambos os objetos.
* **Auditoria Formal de Rotinas Diárias (`AuditLog`)**:
  - Registro compulsório do evento `JOB_DAILY_ROUTINE` em `logs_auditoria` com a quantidade de cobranças geradas e quarentenas processadas a cada disparo diário.

## [1.9.19] — 2026-09-28 — *Dynamic Sale Contract Lifecycle & Operational Fleet Alignment*

### 🔄 Ciclo de Vida Dinâmico de Contratos de Venda (`app.py` & `sync_sale_contract_status`)
* **Auto-conclusão para `Completed`**: Contratos de venda (`Sale_Full` e `Sale_Installment`) transitam automaticamente para `Completed` assim que todas as suas cobranças/parcelas forem quitadas (`Paid`), registrando auditoria `CONTRACT_COMPLETED`.
* **Reabertura Dinâmica para `Active`**: Caso qualquer pagamento seja revertido/estornado para `Pending`, ou caso uma nova cobrança pendente seja adicionada (manual ou avulsa), o contrato reabre instantaneamente para `Active` (`ContractStatus.ATIVO.value`), registrando auditoria `CONTRACT_REOPENED`.
* **Retorno Automático a `Completed`**: Ao quitar todas as pendências novamente (ou ao excluir cobranças pendentes avulsas), o contrato retorna de forma transparente para `Completed`.
* **Sincronização nos Pontos de Ação**: Integrado a 7 fluxos do sistema: visualização de detalhes, inclusão de cobrança, cobrança avulsa, pagamento unitário, estorno de pagamento, quitação em lote e exclusão de transação.

### 🛵 Realinhamento da Frota Operacional & Active Deals on Road
* **Inclusão de Vendas Parceladas Ativas no Total Fleet (`total_motos`)**: Motos sob contratos parcelados ativos pertencem legalmente à empresa e estão em circulação no nome da loja. O cálculo da frota ativa operacional agora consolida:
  $$\text{Total Fleet} = \text{Disponíveis} + \text{Alugadas} + \text{Parceladas Ativas (Financed)} + \text{Oficina}$$
* **Ajuste da Taxa de Utilização (`⚡ % Active Deals on Road`)**:
  - Eliminação da distorção que ultrapassava 100%:
  $$\text{Utilização} = \frac{\text{Rentals} + \text{Financed}}{\text{Total Fleet Operacional}} \times 100\%$$
  - Apenas motocicletas com contrato completado/quitado (`motos_sold_outright`) e apreendidas (`Pound`) são consideradas fora da frota operacional.* **Tabela de Frotas (`/motos` & `static/js/motos.js`)**:
  - O filtro padrão **`⚡ Active Fleet (In Operation)`** passa a exibir motos vendidas parceladas que possuem contratos ativos.
  - Exibição do selo **`Financed #ID ↗`** em roxo no status, acompanhado do nome do comprador/locatário e atalho para conversa direta no WhatsApp.
  - Selo **`Sold #ID ↗`** em tom neutro reservado exclusivamente para vendas concluídas/quitadas fora da frota.
* **Monitoramento Contínuo de Road Tax & MOT**: Veículos sob contratos ativos no nome da loja permanecem sob acompanhamento rigoroso de Road Tax e MOT, com isenção de Road Tax aplicada somente após a quitação e transferência definitiva do V5C.

### 🛡️ Defesa em Profundidade & Estabilidade
* **Suíte de Testes Automatizados**: Criação dos testes dedicados `tests/test_sale_lifecycle_sync.py` e `tests/test_security_hardening.py`.
* **Validação Contínua**: 25 testes unitários e de integração executados com 100% de aprovação.

## [1.9.18] — 2026-09-28 — *Asset Delivery Hardening & Access Control Optimization*

### 🛡️ Otimização no Gerenciamento e Entrega de Mídias
* **Controle de Acesso em Rotas de Upload**: Aplicação de verificação de sessão ativa (`@login_required`) na rota `/static/uploads/<path:filename>`.
* **Políticas de Cache Privado**: Configurados cabeçalhos `Cache-Control: private, no-cache, no-store, must-revalidate` e `Pragma: no-cache` para arquivos de mídia da aplicação.
* **Roteamento Nginx**: Otimização no proxy reverso assegurando que mídias passem pela validação do backend antes da entrega.

## [1.9.17] — 2026-09-28 — *Unified Universal WhatsApp Link Formatting Across Dashboard & Fleet*

### 💬 Normalização Universal de Links do WhatsApp
* **Padronização Global E.164 (`window.formatWhatsAppNumber`) em `static/js/app_shared.js`**:
  - Implementada função universal de formatação e higienização de telefones para deep links do WhatsApp (`https://wa.me/<digits>`), disponível globalmente em todas as telas da aplicação.
  - **Tratamento Preciso do Padrão Britânico**:
    - Telefones UK com prefixo local `07...` têm o `0` inicial substituído por `44` (`07360 123456` &rarr; `447360123456`), eliminando a mensagem de erro *"Phone number shared via url is invalid"* do WhatsApp.
    - Suporte a digitação com 10 dígitos iniciando em `7` (`7360123456` &rarr; `447360123456`).
    - Remoção do zero redundante em números com prefixo internacional e nacional misturados (`+44 07...` &rarr; `447...`).
    - Higienização segura de números internacionais com `+` ou `00`.
* **Correção dos Links do WhatsApp no Dashboard Principal (`templates/index.html`)**:
  - **Seção "Payments Due Today"**: O botão `💬 Remind` agora utiliza `formatWhatsAppNumber`, gerando o link internacional correto com mensagem personalizada cordial em inglês britânico.
  - **Timestamp Automático de Cobrança**: Ao clicar em `💬 Remind` no dashboard, o sistema dispara requisição assíncrona para `/api/financeiro/<id>/lembrete`, registrando o horário e operador que enviou a cobrança.
  - **Badge de Status**: Exibição da etiqueta `✓ Reminded` caso a cobrança já tenha recebido lembrete.
  - **Busca Rápida Universal (Quick Search)**:
    - Cartões de **Customers**: Adicionado atalho direto com botão `💬` formatado ao lado do telefone para iniciar conversa imediata com o cliente.
    - Cartões de **Motorbikes**: Para motos alugadas com condutor ativo, o telefone do condutor recebe atalho direto com botão `💬` no popover de busca.
* **Sincronização em Todo o Ecossistema**:
  - Unificação em `static/js/financeiro.js`, `static/js/motos.js`, `static/js/clientes.js` e `static/js/detalhe_contrato.js`.
  - Cachebusters incrementados (`app_shared.js?v=6`, `financeiro.js?v=21`, `motos.js?v=14`).

## [1.9.16] — 2026-09-28 — *Smart Synchronized Financial Filters (Paid -> Payment Date, Pending -> Due Date)*

### 🔄 Sincronização Inteligente de Filtros de Status e Datas
* **Acompanhamento Automático de Campo de Data por Status**:
  - **Status `Paid` (Pagos) &rarr; Data de Pagamento (`Payment Date`)**:
    - Ao selecionar `Paid Only` (ou via cards de KPI `Collected Today` / `This Week`), o seletor de data alterna automaticamente para `💳 Payment Date` (`campoData = 'pagamento'`), garantindo que períodos rápidos como `Today`, `Yesterday`, `This Week` e datas manuais filtrem estritamente as cobranças **efetivamente pagas/arrecadadas no período**, em vez de filtrar por quando elas venciam.
    - Ordenação padrão sincronizada para `data_pagamento desc` (recebimentos mais recentes no topo).
  - **Status `Pending` / `Overdue` / `Cancelled` &rarr; Data de Vencimento (`Due Date`)**:
    - Ao selecionar `Pending Only`, `Overdue Only` ou `Cancelled`, o seletor de data alterna automaticamente para `📅 Due Date` (`campoData = 'vencimento'`), impedindo que filtros por data de pagamento (inexistente em não pagos) resultem em listagens vazias.
    - Qualquer método de pagamento selecionado é automaticamente limpo (já que transações pendentes não possuem forma de pagamento).
    - Ordenação padrão sincronizada para `data_vencimento asc` (vencimentos mais próximos no topo).
  - **Seleção Manual de Data de Pagamento**:
    - Ao selecionar manualmente `💳 Payment Date` no dropdown quando o status estiver em `Pending` ou `Overdue`, o sistema migra automaticamente o status para `Paid Only`.
  - **Seleção de Forma de Pagamento (`Method`)**:
    - Ao filtrar por um método específico (`Cash`, `Card`, `Bank Transfer`, etc.), o sistema migra automaticamente o status para `Paid Only` e ativa a data de pagamento.
  - **Cards de KPI**:
    - `cardKpiPending` e `cardKpiOverdue` reconfiguram o campo de data para `vencimento` e removem eventuais filtros de método.
    - `cardKpiToday` e `cardKpiWeek` ativam status `Paid`, campo de data `pagamento`, período rápido correspondente e ordenação decrescente por pagamento.
  - **Pills de Atalho de Período (`Today`, `Yesterday`, etc.)**:
    - Se o operador estiver na visualização `Overdue` e clicar em `Today`, o status migra inteligentemente para `Pending` para exibir os lançamentos que vencem hoje (já que atrasados, por definição contábil britânica, só contemplam datas anteriores a hoje).
    - Edição manual dos campos `From` / `To` desmarca as pílulas para evitar estados visuais contraditórios, reativando `All Time` caso os campos sejam esvaziados.
  - **Botão de Fechar Pílula de Filtro Exato (`#btnRemoveActiveFilter`)**:
    - Implementado listener para o botão `✕`, permitindo remover contratos, clientes ou placas com um clique.

### 🛡️ Proteção de Fallback no Backend (`app.py`)
* **Tratamento Seguro de `campo_data` e Ordenação**:
  - Nas rotas `/api/financeiro`, `/api/financeiro/exportar-csv` e `/financeiro/relatorio-pdf`, se `campo_data` não for explicitado e `status == 'paid'`, o backend assume `pagamento`.
  - Se `status` for pendente ou overdue mas `campo_data == 'pagamento'`, o backend protege a consulta caindo com segurança para `data_vencimento`.
  - No Relatório PDF A4 (`/financeiro/relatorio-pdf`), a ordenação respeita `data_pagamento desc` quando filtrado por pagamento e exibe a descrição no cabeçalho: `Date (Payment Date): ...` vs `Date (Due Date): ...`.

## [1.9.15] — 2026-09-28 — *Financial High-Density UI, Exact Inline Filters, Daily Closing Sheet & Audit Refinements*

### ⚡ Tabela Financeira de Alta Densidade (Ultra-Compact Layout)
* **Redução Significativa da Altura das Linhas & Otimização de Espaço Vertical**:
  - **Padding de Células Reduzido em >50%**: O espaçamento interno dos `td` da tabela financeira foi ajustado para `0.35rem 0.55rem` com `line-height: 1.25`, reduzindo a altura média das linhas de ~70px para ~35px.
  - **Visualização Dobrada por Viewport**: O operador consegue visualizar aproximadamente o dobro de registros simultaneamente sem necessidade de scroll contínuo.
  - **Badges e Botões Slim**: Tipografia de status e tipos refinada para `0.68rem - 0.74rem`, botões de ação enxutos (`3px 8px`, `Mark Paid`, `🧾 Rec.`, `↩ Rev.`), e alinhamento vertical centralizado.
  - **Célula de Cliente Compacta**: Nome do cliente em linha única com badge de risco, e telefone, WhatsApp e chip de lembrete contíguos na linha inferior com espaçamento reduzido.

### 📐 Enxugamento Horizontal da Tabela (Zero Barra de Rolagem)
* **Cabeçalhos e Larguras Compactas**:
  - Encurtamento de títulos de colunas para termos objetivos: `ID` &rarr; `#`, `Contract` &rarr; `Contr.` (exibindo `#ID 🔍`), `Motorbike` &rarr; `Bike`, `Type & Description` &rarr; `Type`, `Payment Date & Method` &rarr; `Payment`.
  - Economia de mais de 160px na largura total da tabela, garantindo encaixe perfeito na viewport em telas padrão e laptops sem acionar barra de rolagem horizontal desnecessária.

### 🔍 Filtros Inline Exatos (Exact Inline Filtering)
* **Precisão de 100% sem Ruído de Busca Textual**:
  - **Parâmetros Dedicados no Backend (`app.py`)**: Ao clicar nas lupas inline de contrato (`🔍`), nome do cliente ou placa da moto, a consulta envia parâmetros SQL estritos (`contrato_id`, `cliente_id`, `placa`) em vez de injetar texto difuso no `#searchInput`.
  - **Pílula de Filtro Ativo (`#activeFilterPillContainer`)**: Exibição destacada no topo da tabela indicando o filtro em vigor (ex: `📋 Contract #1` ou `👤 Customer: John Doe`) com botão `✕` para cancelamento rápido.

### 🖨️ Folha de Fechamento de Caixa Diário Executiva (*Daily Closing Sheet*)
* **Documento Imprimível A4 Dedicado (`/financeiro/fechamento-caixa/print`)**:
  - Substituição da impressão de tela do navegador (`window.print()`) por uma rota e template dedicado formal ([templates/relatorio_fechamento_caixa.html](file:///c:/Users/tmuni/Downloads/FF%20Motors%20APP/templates/relatorio_fechamento_caixa.html)) diagramado para folha A4 e PDF.
  - **Estrutura Completa de Caixa**: Cabeçalho institucional formal em texto puro (sem imagens de logo), banner com *Grand Total Arrecadado*, cards de método (*Cash in Till*, *Card Terminal*, *Bank Transfer*, *Trade-in*, *Deposit*).
  - **Quadro de Conciliação Física de Gaveta**: Campos estruturados para anotação de Fundo de Troco Inicial (*Opening Float*), Dinheiro Esperado do Sistema, Dinheiro Físico Contado e Diferença / Quebra de Caixa (+/-).
  - **Livro Cronológico de Entradas**: Listagem detalhada de todos os recebimentos do dia com horário, transação, contrato, cliente, placa, descrição, método e operador.
  - **Auditoria & Sign-off**: Campos formais de assinatura para o operador de caixa (*Cashier Verification*) e para o gerente de plantão (*Duty Manager Sign-off & Safe Drop*).

### 🚨 High Debt Risk Badge (Contagem Exclusiva de Vencidas)
* **Correção da Métrica de Risco de Inadimplência**:
  - A contagem de dívidas por cliente foi refinada no backend (`app.py`) para considerar **estritamente cobranças com data de vencimento no passado (`FinancialTransaction.data_vencimento < inicio_hoje`)** e status pendente.
  - Parcelas de aluguel ou financiamento agendadas para semanas ou meses futuros deixam de poluir a contagem de risco.
  - Badge reestilizada para `🔴 N Late` com tooltip indicativo de cobranças vencidas.

### 💬 Lembrete de Cobrança WhatsApp Estético
* **Micro-Badge Esmeralda Translúcido**:
  - Exibição inline contígua ao número de telefone do cliente (`✓ Just now`, `✓ Today 14:20`, `✓ 2h ago`, `✓ Yesterday`).
  - Tooltip completo ao passar o mouse contendo o nome do operador e a data/hora exata do registro.
  - Atualização otimista instantânea na tela ao clicar no ícone do WhatsApp.

### 🧹 Limpeza de Layout & Massa de Demonstração
* **Remoção de Elementos Desnecessários**:
  - Removido o botão e controle de seleção de pagamentos em lote (*Batch Pay Selection*).
  - Removidas imagens de logomarca dos cabeçalhos dos relatórios imprimíveis A4 ([templates/relatorio_financeiro.html](file:///c:/Users/tmuni/Downloads/FF%20Motors%20APP/templates/relatorio_financeiro.html) e [templates/relatorio_fechamento_caixa.html](file:///c:/Users/tmuni/Downloads/FF%20Motors%20APP/templates/relatorio_fechamento_caixa.html)).
* **Atualização dos Scripts Operacionais (`reset_data.py` & `seed_data.py`)**:
  - Suporte completo às novas tabelas (`MotorcycleV5C`, `MotorcycleTracker`).
  - População de cenários financeiros realistas para o dia de hoje (£740.00 arrecadados entre Dinheiro, Cartão, Transferência Bancária e Pagamento Misto/Split), além de transações com lembrete gravado e saldos devedores remanescentes (`⚡ Bal #1`).

## [1.9.14] — 2026-09-27 — *Universal Search Sold Bike Drilldown, Fleet Horizontal Zero-Scroll Optimization & DVLA Quick Actions*

### 📌 Menu Lateral Fixo / Sticky na Rolagem Vertical (`static/css/styles.css`)
* **Sidebar Sempre Visível Durante a Rolagem da Página (Desktop)**:
  - **Posicionamento Sticky**: O menu lateral (`.sidebar`) agora acompanha a rolagem da página verticalmente (`position: sticky; top: 0; height: 100vh; height: 100dvh;`), permanecendo sempre fixo e acessível em páginas longas como o Dashboard ou a listagem financeira.
  - **Scroll Suave Independente**: Adicionado `overflow-y: auto` com barra de rolagem ultrafina e estilizada caso o usuário utilize telas de baixa resolução vertical, garantindo que todos os links e botões de perfil/logout permaneçam alcançáveis.
  - **Ajuste de Container Flex**: Configurado `overflow-x: clip` no layout principal (`.app-layout`) e removido aprisionamento de rolagem no `.main-content`, permitindo que o viewport do navegador gerencie a rolagem fluida mantendo a barra lateral fixa no topo.
  - **Compatibilidade com Modo Recolhido (Collapsed)**: Mantido `overflow: visible` quando a sidebar está recolhida (`.sidebar.collapsed`), preservando os tooltips flutuantes no hover à direita dos ícones.

### 📊 Gráfico de Distribuição da Frota & Modelo de Negócios (`templates/index.html` & `app.py`)
* **Diferenciação Completa do Modelo de Negócios (Locação vs Venda/Financiamento vs Inventário)**:
  - **Separação de Deals Ativos**: A fatia anterior genérica de `Rented` foi aprimorada para distinguir claramente **Rentals** (aluguel semanal, em tom laranja `var(--accent)`) e **Financed** (vendas parceladas / rent-to-buy com parcelas ativas, em tom violeta `#a855f7`).
  - **Visão Integral dos Ativos**: A barra agora contempla todo o portfólio de 33 veículos com segmentos para `Rentals`, `Financed`, `Available`, `Maintenance`, `Pound` e `Sold` (motos vendidas à vista/quitadas).
  - **Indicador de Utilização Operacional (Utilization Rate)**: Adicionado badge inteligente no cabeçalho: `⚡ 73% Active Deals on Road (19/26)`, calculando a porcentagem exata de motos em contrato ativo sobre a frota operacional em circulação.
  - **Pills de Legenda Interativas Estilo SaaS**: Substituídos os textos simples por botões/pills modernos em *dark glass*, com pontos de status iluminados (*glow*), contagem e porcentagem calculada dinamicamente, permitindo filtrar contratos ou frotas diretamente com 1 clique.
  - **Barra de Progresso de 18px**: Altura expandida de 12px para 18px com espaçamento interno, cantos arredondados e efeito de brilho e elevação no hover.

### 🔍 Busca Universal & Navegação da Frota (`/motos` & `templates/index.html`)
* **Exibição Automática de Motos Vendidas e em Pátio (`Sold` / `Pound`) via Busca**:
  - **Correção de Drilldown**: Ao clicar em uma moto vendida ou apreendida nos resultados do buscador geral do Dashboard, o link agora envia explicitamente `status=all` (`/motos?search=<PLACA>&status=all`).
  - **Tratamento Inteligente no Fleet**: Caso a página `/motos` seja acessada com o parâmetro `search` sem especificação de status, o filtro padrão de frota ativa (`operational`) cede lugar automaticamente para `All Statuses (Incl. Sold & Pound)` (`statusFiltro = 'all'`), garantindo que motos vendidas (`Sold`) e apreendidas (`Pound`) sejam localizadas e exibidas imediatamente na tabela.
  - **Ação Proativa de Busca em Estado Vazio**: Quando uma busca na tabela da frota não encontra resultados sob o filtro ativo, é exibido o botão de atalho `🔍 Search All Fleet (incl. Sold & Pound)`, permitindo ao operador expandir a pesquisa para a frota completa com 1 clique.

### 📐 Otimização Horizontal da Tabela de Frotas (Zero Barra de Rolagem)
* **Ajuste de Cabeçalhos e Densidade Visual em 1280px**:
  - Títulos de colunas compactados de forma limpa e compreensível (`Plate`, `Road Tax`, `MOT`, `V5C & GPS`, `Status`).
  - Renomeado o botão de ação rápida de `+ Rent` para `+ Deal` com padding otimizado, refletindo com precisão as operações do negócio (venda, financiamento e aluguel).
  - Espaçamentos horizontais refinados (`padding: 0.55rem 0.35rem`), garantindo que todas as 9 colunas da tabela de frotas caibam 100% visíveis em telas de 1280px (MacBook Air / laptops de 13") sem acionar barra de rolagem horizontal.

### 🛡️ Integração de Consulta DVLA e Limpeza de Formulários
* **Botões DVLA Check nos Modais e Telas de Cadastro**:
  - Adicionado botão `DVLA Check ↗` estilizado e responsivo no modal de edição/gerenciamento de motos (`#motoManageModal`) e na tela de inclusão de novos veículos (`/motos/nova`). O botão copia a placa automaticamente para a área de transferência com feedback visual e abre o portal oficial do governo britânico (`vehicleenquiry.service.gov.uk`).
  - Limpeza dos rótulos dos campos nos formulários, removendo textos redundantes (`(Reg No.)` em *Registration Plate* e `(Miles)` em *Current Mileage*).

## [1.9.13] — 2026-09-26 — *Dashboard Operational Hub: Quick Lookup, Due Today Collections, Interactive Distribution & Cashflow*

### ⚡ Dashboard Operacional (`/` & `templates/index.html`)
* **Barra de Acesso Rápido Universal & Layout Responsivo Mobile (iPhone)**:
  - **Alinhamento no Cabeçalho**: A barra de busca rápida foi realocada para a mesma linha do título `Overview`, ocupando o lado direito do cabeçalho no Desktop e eliminando uma linha inteira de espaço vertical.
  - **Refinamento dos Cartões de Clientes (Customer Cards)**: Corrigida anomalia visual onde badges de tipo de contrato (`Financed`, `Rental`, `Purchase`) quebravam linha e flutuavam isoladas. Agora os badges ficam inline e contíguos ao nome do cliente na primeira linha; a placa da moto (`🛵`) é exibida na linha de detalhes ao lado de telefone e email; e os botões de ação foram encurtados de `Agreement #ID (PLATE) ↗` para `Agreement #ID ↗` em estilo *dark glass* de alto contraste.
  - **Resolução de Sobreposições no Desktop**: Expandido popover para 640px de largura e estruturado em duas linhas verticais sem quebra desordenada (`flex-wrap: nowrap`), eliminando colisão de texto e emojis de motorista sobre modelos de veículos.
  - **Grid Compacto de Botões no iPhone**: No modo retrato do celular, os 5 botões de ação são exibidos em grid de 2 colunas (`+ New Contract` ocupando toda a largura na primeira linha, seguido de pares balanceados: `Add Bike` / `New Inspection`, `Add Customer` / `Overdue Report`), permitindo visualizar **todos os botões simultaneamente sem precisar girar o celular para a horizontal ou fazer scroll**.
  - **Resultados de Busca Legíveis no Celular**: O dropdown de resultados adota formato de cartões responsivos no iPhone (`search-result-card`), separando cabeçalho com placa/status, linha de detalhes e botões de ação touch em linhas dedicadas para evitar sobreposição e truncamento de texto.
  - **Ícone Vetorial de Lupa (SVG com Efeito Focus)**: Substituído o caractere emoji `🔎` por um ícone SVG vetorial ultra-nítido posicionado com `z-index: 2` (eliminando problema de sobreposição pelo plano de fundo do input) e com transição dinâmica de cor para o laranja corporativo (`var(--accent)`) quando o usuário foca na busca.
  - **Prevenção de Zoom no iOS**: Altura mínima de 44px e tamanho de fonte de 16px configurados para evitar que o Safari do iPhone aplique zoom involuntário ao tocar no campo de busca.
* **Seção Proativa "Payments Due Today" Baseada em Lançamentos Financeiros Pendentes**:
  - **Correção da Regra de Negócio**: Listagem agora baseia-se estritamente em **lançamentos reais de cobrança pendentes (`FinancialTransaction`) com vencimento no dia de hoje**, eliminando a geração sintética anterior que se baseava apenas no dia da semana cadastrado no contrato de aluguel.
  - Abrange todas as modalidades de cobrança com vencimento na data: **aluguel semanal (`Rent`)**, **parcelas de venda (`Sale_Installment`)**, entradas (`Sale_Deposit`), quitações integrais (`Sale_Full`), depósitos caução (`Deposit`), multas/PCNs e taxas de avaria.
  - Exibe badges contextuais de tipo (`Rent`, `Sale Installment`, `Sale Down Payment`, `Sale Full Payment`, `Rental Deposit`, `Fine / PCN`, `Damage Charge`) e notas operacionais.
  - Botão direto `💬 Remind` com mensagem amigável e profissional pré-formatada em inglês britânico adaptada dinamicamente ao tipo de encargo (*weekly rent*, *vehicle installment*, *down payment*, etc.) e com a ressalva de cortesia:
    > *"If you have already made this payment, please disregard this message. Thank you!"*
  - Links contextuais inteligentes: direciona para o contrato (`Agreement ↗`) quando vinculado ou para o livro contábil (`Ledger ↗`) com busca pré-filtrada.
* **Métricas de Fluxo de Caixa Realizado (Realized Cashflow)**:
  - Adicionado no card de *Weekly Revenue* o acompanhamento de caixa efetivamente recebido: `Collected this week: £X,XXX.XX (Today: £XXX.XX)`, calculado a partir das transações pagas no horário de Londres.
  - Card de *Weekly Revenue* direciona com filtro para transações pendentes de aluguel (`/financeiro?tipo=Rent&status=pendentes`).
* **Barra de Distribuição da Frota Interativa (Interactive Fleet Distribution)**:
  - Segmentos da barra colorida (`Rented`, `Available`, `In Maintenance`, `Pound`) e itens da legenda agora são interativos (cursor pointer com feedback visual e clique filtrando instantaneamente a lista de motos ou contratos correspondentes).
  - Segmento e legenda de `Rented` direcionam estritamente para contratos de aluguel ativos (`/contratos?status=Active&tipo=Rent`).
* **Navegação Direta e Filtros Corrigidos nos Stat Cards**:
  - `Available` ➔ `/motos?status=Available`.
  - `Rented (Active)` ➔ `/contratos?status=Active&tipo=Rent` (evita misturar contratos de venda).
  - `In Maintenance` ➔ `/motos?status=Maintenance` (direciona para a frota com filtro de oficina).
  - `Weekly Revenue` ➔ `/financeiro?tipo=Rent&status=pendentes` (com suporte a carregamento com filtro `tipo` em `static/js/financeiro.js`).
  - `TAX & MOT Warnings` ➔ `/motos?status=warnings`.
  - Adicionado botão de atalho `+ Add Bike` (`/motos/nova`) no grupo de ações rápidas do cabeçalho.
* **Alertas com Ações Imediatas (Actionable Notices)**:
  - Alertas de verificação de 15 dias de seguro no askMID contam com botão direto `askMID ↗` abrindo o portal oficial do governo britânico (`askmid.com`).
  - Alerta de Tax & MOT direciona diretamente para os avisos filtrados da frota.
  - Alertas de falta de documento V5C permitem acesso direto ao filtro de veículos sem logbook.

## [1.9.12] — 2026-09-26 — *Fleet Operational Hub: Interactive Agreement Links, Hirer Previews, Compact Layout & PDF Report*

### 🏍️ Central Operacional do Fleet (`/motos`)
* **Vinculação Interativa de Contratos no Status da Moto**:
  - Para motos alugadas (`Rented`), o badge transiciona para um link direto para o contrato ativo (`Rented #ID ↗`) acompanhado do nome do condutor atual (`👤 Hirer Name`) e atalho direto para WhatsApp (`💬`).
  - Para motos vendidas (`Sold`), o badge vira link direto para o contrato de venda (`Sold #ID ↗`) com indicação do comprador.
  - Para motos disponíveis (`Available`) ou em oficina (`Maintenance`), exibe o status operacional com indicação sutil de histórico do último contrato concluído (`Last: #ID ↗`).
* **KPI Summary Cards com Filtro Interativo por Clique**:
  - Barra de 6 mini-cards no topo da tela do Fleet: **Active Fleet** (⚡), **Available** (🟢), **Rented** (🔑), **Maintenance** (🔧), **Missing V5C** (⚠️) e **Compliance Alerts** (🛡️).
  - Clicar em qualquer card filtra instantaneamente a tabela com feedback visual ativo (highlight e badge sincronizado).
* **Atalho Multimodal Compacto "+ Deal" para Motos Disponíveis**:
  - Na coluna de ações, motos com status `Available` contam com botão direto e enxuto `+ Deal` (substituindo `+ Rent`/`+ Agreement`) que abre o formulário de novo contrato (`/contratos/novo?moto_placa=...`) com suporte a todas as modalidades operacionais da plataforma: **Aluguel (`Rent`)**, **Venda Parcelada/Financiamento (`Sale_Installment`)**, **Venda à Vista (`Sale_Full`)** ou **Compra/Trade-in (`Purchase`)**.
* **Eliminação da Barra de Rolagem Horizontal no Fleet (Títulos Compactos & Padding Otimizado)**:
  - Preservadas todas as 9 colunas originais separadas, aplicando abreviações inteligentes nos cabeçalhos: `Reg Plate` ➔ `Plate`, `Road Tax Expiry` ➔ `Road Tax`, `MOT Expiry` ➔ `MOT`, `V5C & Trackers` ➔ `V5C & GPS`, e `Status & Agreement` ➔ `Status`.
  - Tabela ajustada para padding refinado (`padding: 0.55rem 0.35rem`), garantindo que 100% da tabela — incluindo as ações `+ Deal` e `Manage` — caiba perfeitamente na horizontal sem gerar barra de rolagem em resoluções padrão (1280px e 1366px).
* **Consulta Rápida DVLA Oficial na Tabela, Modal de Edição e Cadastro de Moto**:
  - O botão `DVLA Check ↗` copia a matrícula para a área de transferência com feedback visual instantâneo (`✓ Copied!`) e abre a consulta oficial de MOT/Tax do governo britânico (`check-mot.service.gov.uk`).
  - Disponível de forma integrada:
    1. **Na Tabela da Frota**: empilhado verticalmente logo abaixo da placa.
    2. **No Modal de Gestão/Edição da Moto (`#motoManageModal`)**: ao lado do badge da placa no cabeçalho.
    3. **Na Tela de Cadastro de Nova Moto (`/motos/nova`)**: ao lado do label do campo de matrícula (`Registration Plate`).
* **Relatório Oficial da Frota em PDF (`/motos/relatorio-pdf` & `templates/relatorio_fleet.html`)**:
  - Botão `🖨️ PDF Report` no topo da tela da frota gerando relatório imprimível e exportável em PDF (A4) com os dados essenciais e úteis da tabela filtrada atual (placa, modelo e cor, milhagem, status, vencimentos de MOT e Tax / SORN, contrato e condutor ativo). Substitui planilhas CSV volumosas por um documento limpo e executivo.

## [1.9.11] — 2026-09-26 — *Used Vehicle Purchase Agreement (Buy-in / Trade-in Contracts)*

### 🤝 Novo Tipo de Contrato: Compra de Veículo Usado (`Purchase`)
* **Fluxo Completo de Aquisição e Troca de Motos**:
  - Implementado o novo tipo de contrato `Purchase` (`Used Vehicle Purchase Agreement`) para formalizar a compra de motos de clientes ou sua entrada como base de troca (trade-in / part-exchange) ou abatimento de serviços.
  - O fluxo segue o mesmo padrão operacional da plataforma: o operador seleciona o cliente (vendedor) e a motocicleta cadastrada, escolhendo a opção **🤝 Vehicle Purchase** no formulário de criação (`/contratos/novo`).
* **Campos e Regras do Formulário de Criação**:
  - **Elegibilidade Total de Motocicletas**: Toda e qualquer moto do sistema fica disponível no seletor de veículos para contratos de compra, independentemente de status atual (`Available`, `Maintenance`, `Rented` ou `Sold`), permitindo recompra de veículos vendidos ou acerto de trocas.
  - **Omissão Completa de Seguro**: O campo de certificado de seguro da motocicleta é completamente omitido e desativado no formulário de compra (`Purchase`), já que a moto está entrando no estoque da oficina/loja.
  - **Categoria do Veículo (`categoria_historico`)**: Histórico de salvado no Reino Unido (`Clear`, `Cat N`, `Cat S`, `Cat C`, `Cat D`, `Cat B`).
  - **Cor do Veículo (`moto_cor`)**: Captura e atualiza a cor do veículo no cadastro da motocicleta e no contrato impresso.
  - **Valor de Compra / Trade-in (`valor_compra_veiculo`)**: Montante acordado pago ou creditado ao cliente.
  - **Método de Pagamento (`metodo_pagamento_compra`)**: `Bank Transfer`, `Cash`, `Trade-in / Exchange`, `Service Credit / Debt Offset` ou `Other`.
  - **Detalhes do Pagamento / Compensação (`detalhes_pagamento_compra`)**: Descrição detalhada dos dados bancários, abatimento de dívida/serviço ou moto de destino do trade-in.
  - **Status de Destino na Frota (`status_moto_destino`)**: Escolha se a moto adquirida entra diretamente no pátio como `Available` (disponível para aluguel/venda), `Maintenance` (oficina / preparação mecânica) ou `Pound` (apreendida / fora de operação).
  - **Milhagem Não Verificada (`milhagem_nao_verificada`)**: Suporte a veículos parados/não funcionais (*non-runners*) cujo odômetro não pode ser lido, permitindo valor 0 ou vazio com ressalva legal.
* **Isenção de Contas a Receber (Regra A1)**:
  - Como a loja está pagando ou concedendo crédito na compra da moto (e não cobrando o cliente), o sistema **não gera nenhuma transação a receber** no ledger financeiro (`FinancialTransaction`), mantendo o extrato financeiro limpo e estritamente informativo.
* **Documento Jurídico Impresso em Página Única A4 (`contrato_compra_print.html`)**:
  - Layout formal condensado de alta fidelidade calibrado rigorosamente para **preencher harmoniosamente 1 página A4 inteira**, com tipografia legível e confortável (`8.9pt` a `9.5pt` no corpo e cabeçalhos nítidos), eliminando áreas vazias excessivas e sem quebras indesejadas para 2ª página:
    - **Buyer & Seller Details**: Bloco lado a lado em 2 colunas com dados da compradora `J&F Motorcycles LTD` (109 Windmill Lane, Birmingham, B66 3EW, Fone: 0121 492 0697) e do cliente vendedor.
    - **Vehicle & Financial Details**: Bloco lado a lado em 2 colunas com dados do veículo (marca, modelo, cor, placa, categoria UK, quilometragem) e termos financeiros (valor, método de pagamento e detalhes de liquidação).
    - **Seller Declarations & Warranties**: Lista clara e completa das declarações estritas de garantia e titularidade (origem UK, ausência de dívidas/financiamentos pendentes, garantia de quilometragem, ausência de vícios ocultos e indenização total de multas e encargos ULEZ/CAZ prévios).
    - **Buyer Declaration & Signatures**: Declaração da compradora e bloco lado a lado com a assinatura digital do vendedor e a assinatura fixa autorizada da loja (`signature_fernando.png`), acompanhado de data/hora da venda e rodapé unificado.
* **Ajuste na Tela de Detalhes (`/contratos/<id>`) para Contratos de Compra**:
  - **Omissão da Assinatura de Devolução**: O card de assinatura de retorno/término (`#card_sig_devolucao`) é completamente ocultado para contratos de compra (`Purchase`), mantendo apenas a assinatura inicial do contrato de aquisição.
  - **Omissão do Card de Extrato Financeiro (`#card_financial_statement`)**: Como a compra é liquidada na aquisição e não gera parcelas nem cobranças contínuas, o card de *Financial Statement* é completamente omitido na visualização de contratos de compra.
* **Assinatura Digital e Conclusão Automática**:
  - Ao colher a assinatura digital do vendedor, o contrato transiciona automaticamente para o status `Completed` (`Finalizado`), dispensando rotinas de encerramento de aluguel.
* **Isenção de Compliance askMID e Pré-Entrega**:
  - Veículos adquiridos não exigem apólice de seguro pessoal do cliente vendedor nem bloqueio de pré-entrega para liberação de pátio.
* **Card de Depósitos no Dashboard (`/api/dashboard` & `index.html`)**:
  - **Total de Depósitos Retidos na Frota**: O endpoint `/api/dashboard` foi otimizado para calcular o montante total de depósitos caução sob custódia da empresa (`total_depositos_retidos`), consolidando tanto as motos ativas em circulação (`depositos_ativos_valor`) quanto as motos em processo de devolução (`quarentenas_valor`).
  - **Exibição Inteligente no Card `Deposit Holds`**: Mantém a contagem de contratos em quarentena/hold em destaque numérico e adiciona no texto descritivo o valor monetário total retido na frota (`Total Held in Fleet: £X,XXX.XX`), com detalhamento contextual quando houver valores sob análise de devolução (`(£XXX.XX on hold)`).
* **Testes Automatizados (`tests/test_compra_contratos.py`)**:
  - Testes cobrindo criação com destinos `Available`, `Maintenance` e `Pound`, validação de página única (1 `.agreement-page`), presença de elementos de UI no detalhe do contrato, assinatura digital e transição de status, aprovados com 100% de sucesso.

## [1.9.10] — 2026-09-25 — *Signed Contract Legal Immutability & Live Operational Details Screen*

### ⚖️ Imutabilidade Jurídica do Documento do Contrato Assinado (`/contratos/<id>/imprimir`)
* **Preservação Rígida do Snapshot Legal Pós-Assinatura**:
  - Modificar termos de um contrato após sua assinatura digital é legalmente inadmissível. O documento formal impresso e PDF gerado (`contrato_print.html` e `contrato_venda_print.html`) mantém congelados permanentemente todos os dados do ato de contratação: nome, telefone, e-mail, endereço registrado, CNH (DVLA), CBT, modelo, cor, placa e valores.
  - **Preservação do Dia de Vencimento Original Assinado (`dia_pagamento_semanal_original`)**:
    - Adicionada a coluna `dia_pagamento_semanal_original` no modelo `Contract` com auto-migração e backfill seguro em PostgreSQL e SQLite.
    - Na criação do contrato (`POST /api/contratos`), o dia da semana assinado é permanentemente arquivado em `dia_pagamento_semanal_original`.
    - Ao alterar o dia de cobrança no sistema (`PUT /api/contratos/<id>/dia-pagamento`), a agenda ativa `dia_pagamento_semanal` e o agendador de cobranças recorrentes são atualizados para as faturas futuras, mas o documento formal de contrato gerado/impresso **nunca é modificado**, continuando a exibir com fidelidade jurídica o dia de vencimento assinado pelo cliente.

### 📱 Dados Vivos e Atualizados na Tela Operacional de Detalhes (`/contratos/<id>`)
* **Sincronização em Tempo Real com Cadastros de Clientes e Motocicletas**:
  - A tela de detalhes do contrato (`/contratos/<id>`) é a ferramenta de trabalho diário da equipe para contato, atendimento e pós-venda.
  - O endpoint `/api/contratos/<id>` foi refatorado para priorizar as **informações atualizadas em tempo real** dos cadastros de `Client` (telefone para chamadas/WhatsApp, e-mail, endereço atualizado para correspondência, fotos de CNH/CBT) e `Motorcycle` (modelo, cor, placa), com fallback seguro para os dados do snapshot caso o registro seja excluído.
  - No card de termos contratuais, a interface agora informa com clareza o dia de cobrança atual da agenda com anotação contextual do dia assinado caso tenha ocorrido alteração posterior (ex.: `Friday (Signed: Wednesday)`).
  - Bump de versão de script para `detalhe_contrato.js?v=27`.

## [1.9.9] — 2026-09-25 — *Contract Details Clipboard Shortcuts & Financial Statement Sorting and Pagination*

### 📋 Botões de Copiar para Área de Transferência (Clipboard Shortcuts)
* **Atalhos Rápidos de Cópia nos Detalhes do Contrato (`/contratos/<id>`)**:
  - Implementados botões discretos e elegantes com ícone `📋` (`.btn-copy`) para cópia instantânea de informações essenciais com um único clique.
  - **Dados do Cliente**: Botões ao lado do **Nome**, **Telefone**, **E-mail** e no cabeçalho do box de **Endereço Cadastrado**.
  - **Dados da Motocicleta**: Botão de cópia posicionado diretamente ao lado da placa (`#info_placa` / `.badge-plate`).
  - **Micro-interação e Feedback Visual**: Ao clicar, o botão transiciona suavemente para o ícone `✓` em tom verde esmeralda com contorno sutil (`#10b981`), retornando automaticamente ao estado original após 1,8 segundos.
  - **Compatibilidade Ampla**: Suporte nativo à API moderna `navigator.clipboard.writeText` com fallback transparente via `document.execCommand('copy')` para ambientes legados ou sem contexto seguro.

### 💳 Ordenação e Paginação no Extrato Financeiro (Financial Statement)
* **Ordenação Interativa Multi-Coluna (Sorting)**:
  - Cabeçalhos da tabela `#extratoTable` atualizados para classes `.sortable-th` com indicadores de direção (`⇅`, `▲`, `▼`).
  - Suporte a ordenação ascendente e descendente nas colunas:
    - **Type**: Ordem alfabética da categoria da transação.
    - **Amount**: Ordenação numérica real do montante devido.
    - **Due Date / Payment Date**: Conversão e ordenação cronológica exata por timestamp de data.
    - **Status**: Ordenação contextual de urgência operacional (`Overdue` > `Pending` > `Paid`).
* **Paginação com Seletor de Registros**:
  - Controles de paginação adicionados abaixo da tabela (`#extratoPaginationContainer`) com botões **« Previous** e **Next »**.
  - Indicador dinâmico de registros (ex.: *"Showing 1 to 10 of 28 charges (Page 1 of 3)"*).
  - Seletor de quantidade por página com opções de **10** (padrão), **25**, **50** e **All**.
  - **Cálculo Consolidado dos Totais**: Os cartões de resumo do extrato (*Total Paid*, *Total Pending*, etc.) continuam computados sobre o histórico integral do contrato, mantendo a integridade contábil independentemente da página selecionada.
* **Cache Buster Bump**: Atualizado script para `detalhe_contrato.js?v=26`.

## [1.9.8] — 2026-09-25 — *Active Fleet Filter, Out-of-Operation Dashboard Indicator, Tracker IMEI Duplicate Protection, Client URL Search & Rental Due Day Management*

### 📅 Alteração de Dia de Vencimento Semanal para Contratos de Aluguel Ativos
* **Ajuste Dinâmico do Dia de Cobrança Semanal (`PUT /api/contratos/<id>/dia-pagamento`)**:
  - Implementado botão **`✏️ Change Due Day`** no card de termos contratuais em `/contratos/<id>`, exibido exclusivamente para contratos de aluguel ativos (`Rent` + `Active`).
  - Modal dedicado (`#modalAlterarDiaVenc`) com design dark glassmorphism permitindo ao operador selecionar o novo dia da semana para o vencimento (Segunda a Domingo / `0..6`).
  - **Ajuste Opcional de Cobranças Pendentes**: Caixa de seleção que, quando marcada, recalcula e realinha a data de vencimento de cobranças semanais de aluguel pendentes para o novo dia da semana.
  - **Sincronização com o Cron Job do APScheduler**: A rotina noturna `gerar_cobrancas_recorrentes()` (à 01:00 AM London Time) passa a gerar as faturas semanais futuras automaticamente no novo dia configurado (`dia_pagamento_semanal == dia_semana_atual`).
  - **Correção Estrutural de Renderização**: Corrigido fechamento de tag `</div>` de `.modal-overlay` em `detalhe_contrato.html`, garantindo exibição nítida do modal e recarregamento limpo pós-salvamento (`window.location.reload()`) com bump de versão para `detalhe_contrato.js?v=25`.
  - Registro de auditoria (`CONTRACT_DUE_DAY_UPDATED`) com trilha completa: operador, dia anterior, novo dia e total de cobranças ajustadas.

### 🛵 Indicador de Motos Fora de Operação no Card "Total Fleet" (Dashboard)
* **Visão Consolidada de Frota Ativa e Veículos Fora de Operação**:
  - O card de estatística **Total Fleet** no Dashboard (`/`) agora exibe o total ativo em operação como métrica principal (`total_motos`) e sinaliza simultaneamente a contagem de motos fora de operação (`Pound`).
  - Adicionado badge estilizado `🏛️ [N] OUT OF OP` em tom âmbar suave ao lado do valor principal, com link direto para `/motos?status=Pound`.
  - A linha descritiva informa em tempo real: `Active in operation • [N] outside operation` (ou `0 outside operation` se toda a frota estiver ativa).

### 📡 Proteção contra Duplicidade de Trackers / IMEIs na Frota & Teclado Numérico Mobile
* **Bloqueio Rigoroso de Tracker Duplicado com Identificação de Placa**:
  - Implementada validação no backend (`/api/motos/<placa>/trackers`) para impedir o cadastro do mesmo número Serial ou IMEI em mais de uma motocicleta.
  - Ao tentar inserir um número já cadastrado em outra moto, a requisição é recusada (`400 Bad Request`) e uma mensagem de alerta detalhada informa explicitamente qual a placa do veículo em que o rastreador já está instalado (ex: *"Este tracker (1234567890) já está cadastrado na moto BK22NMX. Remova-o da moto BK22NMX primeiro para vinculá-lo a outro veículo."*).
  - O campo de entrada `#tracker_numero` é focado e realçado em vermelho suave ao ocorrer erro.
* **Teclado Numérico Otimizado para iPhone / Mobile**:
  - O campo `#tracker_numero` recebeu os atributos `inputmode="numeric"` e `pattern="[0-9]*"`, acionando o teclado numérico de 10 teclas nativo no iOS (iPhone/iPad) e Android, acelerando e simplificando a digitação de números longos de IMEI no balcão e oficina.

### ⚡ Frota Ativa como Filtro Padrão no Fleet (`/motos`)
* **Visualização Focada na Operação Ativa**:
  - A tela de frotas (`/motos`) agora define como filtro padrão **`⚡ Active Fleet (In Operation)`** (`status=operational`).
  - Esse filtro exibe automaticamente apenas veículos operacionais em circulação (`Available`, `Rented` e `Maintenance`), ocultando motos fora de operação (`Pound`) e veículos vendidos (`Sold`).
  - Adicionada opção explícita no dropdown: `All Statuses (Incl. Sold & Pound)` (`value="all"`), permitindo aos operadores consultar o histórico completo de todas as motos cadastradas a qualquer momento.
  - Backend (`app.py` / `/api/motos`) atualizado para suportar o filtro de status `operational` / `in_operation` via negação `~Motorcycle.status.in_(['Sold', 'Vendida', 'Pound'])`.

### 👥 Navegação do Contrato para Clientes com Filtro Automático (`/clientes?search=...`)
* **Filtragem Automática por URL no Módulo de Clientes**:
  - Ao clicar no botão **`👥 View Client`** na tela de detalhes do contrato (`/contratos/<id>`), o operador é redirecionado para `/clientes?search=[ID_cliente]`.
  - Corrigido o script `clientes.js` para ler os parâmetros da query string (`?search=`, `?q=`, `?id=`) no carregamento da página (`DOMContentLoaded`), preenchendo o campo de busca (`#searchInput`) e disparando a consulta automaticamente.
  - **Suporte a Busca por ID e Prioridade de Correspondência**:
    - Backend (`app.py` / `/api/clientes`) atualizado para reconhecer buscas numéricas e identificadores com hash (ex: `12` ou `#12`), buscando diretamente em `Client.id == int(clean_num)`.
    - Ordenação inteligente com `db.case`: a correspondência exata do ID do cliente é garantida como o **primeiro registro no topo da tabela**, mesmo que outros contatos compartilhem dígitos no telefone ou e-mail.
  - Placeholder do campo de busca atualizado para: `"Search by name, phone, email or #ID..."`.

## [1.9.7] — 2026-09-25 — *Collapsible Slim Sidebar, Vehicle Part-Exchange Payment, Pound Status & Missing V5C Alerts*

### 📱 Menu Lateral Compactável / Fino (Collapsible Slim Sidebar)
* **Modo Compacto / Slim com Ícones Centralizados (`.sidebar.collapsed`)**:
  - Implementado botão de alternância suave (`#sidebarToggleBtn`) no cabeçalho do menu lateral com ícone de chevron dinâmico (`<<` para recolher, `>>` para expandir).
  - No modo recolhido, a barra lateral transita de `260px` para `74px`, convertendo todos os links para ícones vetoriais modernos (SVG) centralizados em cor laranja FF Motors.
  - O logotipo alterna automaticamente entre o logo completo (`logo.png`) e o emblema/monograma alado compacto (`icon.png`).
  - O conteúdo principal (`.main-content`) expande dinamicamente para ocupar todo o espaço liberado em tela, proporcionando visualização maximizada de tabelas e dashboards.
* **Tooltips Flutuantes no Hover & Atalho de Teclado**:
  - Ao passar o mouse sobre qualquer link de navegação ou botão no modo fino, um tooltip flutuante com acabamento em vidro escuro e borda âmbar exibe o nome do módulo (`Dashboard`, `Fleet`, `Customers`, `Contracts`, etc.).
  - Adicionado atalho de teclado `Shift + S` no desktop para alternar a barra lateral instantaneamente com uma só mão.
* **Persistência de Estado e Proteção contra FOUC**:
  - A preferência do operador é salva no `localStorage` (`ffmotors_sidebar_collapsed`) e restaurada automaticamente ao navegar entre qualquer página da aplicação.
  - Script preloader inline em `<head>` elimina 100% de qualquer piscamento ou salto visual de tela (FOUC).
  - Responsividade preservada no Mobile (<768px): dispositivos móveis continuam usando o drawer off-canvas e a barra inferior nativa sem interferência.

### 🔄 Forma de Pagamento "Exchange" (Trade-In / Troca com Outra Moto)
* **Novo Método de Pagamento Nativo (`Exchange`)**:
  - Implementado suporte nativo ao método `Exchange` quando o cliente entrega outra motocicleta como parte de pagamento na compra ou aluguel de veículo.
  - Disponível em todo o ecossistema de liquidação financeira (`PAYMENT_METHODS`):
    - Pagamentos manuais e baixas de transação (`/api/financeiro/pagar/<id>`).
    - Pagamentos fracionados / múltiplos (Split Payments: ex: `Exchange (£1,500.00) + Cash (£500.00)`).
    - Tabelas do financeiro (`/financeiro`), recibos e histórico do contrato (`/contratos/<id>`).
    - Destaque visual com badge verde-esmeralda estilizado (`#34d399` / `#10b981`).

### 📝 Campo de Observações/Notas ao Receber Pagamentos (Payment Notes)
* **Campo de Nota Opcional no Modal de Pagamento**:
  - Adicionado campo de texto `Payment Note / Reference (Optional)` nos modais de pagamento de `/financeiro` e `/contratos/<id>`.
  - Permite aos operadores registrarem detalhes cruciais no ato do recebimento (ex: detalhes da moto entregue em trade-in `Exchange`, referência de transferência bancária, observações de desconto ou autorização do Fernando).
* **Armazenamento e Auto-Migração (`database.py` & `app.py`)**:
  - Nova coluna `nota TEXT` na tabela `financeiro_transacoes` com auto-migração transparente para PostgreSQL e SQLite.
  - Log de auditoria (`AuditLog`) enriquecido com o registro da nota inserida.
* **Visualização no Extrato e Recibos**:
  - Extrato financeiro (`/financeiro`) e tabela de transações do contrato (`/contratos/<id>`): exibe linha de nota com ícone `📝` destacada na coluna de pagamento.
  - Recibo impresso (`/recibo/<id>`) e modal pop-up de recibo: exibe linha dedicada `Payment Note:` quando preenchida.
  - Busca inteligente: o campo de busca de transações também permite filtrar e encontrar pagamentos pelo texto da nota.

### 🏛️ Novo Status "Pound" para Motos Fora de Operação
* **Status "Pound" no Ciclo de Vida da Frota (`database.py` & `MotoStatus.POUND`)**:
  - Para veículos apreendidos pela polícia, apreendidos em pátios oficiais ou temporariamente retidos fora de operação.
  - **Isenção Estrita de Alertas de MOT e Road Tax**:
    - Motocicletas com status `Pound` são **automaticamente desconsideradas** dos alertas de validade de MOT e Road Tax no Dashboard (`/api/dashboard`), evitando falsos positivos operacionais.
    - Na tabela de frotas (`/motos`), as colunas de Road Tax e MOT exibem o selo informativo `Exempt (Pound)` em tom neutro.
  - **Filtros e Alocação da Frota**:
    - Novo filtro `🏛️ Pound (Outside Operation)` no dropdown da tabela de frotas (`#statusFilter`) e suporte a busca via URL (`/motos?status=Pound`).
    - Barra de Alocação da Frota no Dashboard atualizada com segmento e contagem dedicada para motos em `Pound`.

### ⚠️ Central de Alertas e Filtros para Motos sem V5C (Missing V5C)
* **Detecção Universal (Inclusive Motos Vendidas)**:
  - Corrigida anomalia onde motocicletas com status `Sold` sem documento V5C exibiam um traço (`-`) em vez do badge de alerta.
  - Como o V5C logbook é crucial para transferência legal ao comprador e auditoria da DVLA, **motos vendidas sem V5C agora exibem o badge chamativo `⚠️ No V5C`** e são integralmente contabilizadas no card de alerta prioritário do Dashboard (`motos_sem_v5c`).
  - O filtro de busca de frotas (`/motos?v5c=missing` ou `status=missing_v5c`) agora lista todas as motos sem documento, sem exceção de status.
* **Visualização e Gestão na Tabela de Frotas (`/motos`)**:
  - Toda motocicleta sem documentos V5C cadastrados passa a exibir badge chamativo `⚠️ No V5C` na coluna *V5C & Trackers*, com atalho direto ao modal na aba de V5C para anexação imediata.
  - Novo filtro rápido no seletor de status: `⚠️ Missing V5C`, exibindo apenas as motos sem documento de porte/registro.
  - Suporte à query string `?v5c=missing` com carregamento automático no `DOMContentLoaded`.
* **Sinalização nos Detalhes do Contrato (`/contratos/<id>`)**:
  - O botão de atalho `#btnShortcutV5C` no card do veículo passa a alertar visualmente em vermelho suave quando o veículo vinculado não possui nenhum V5C anexado (`0`), com atualização em tempo real após upload.

### 🧪 Testes Automatizados & Otimização
* **Nova Suíte de Testes (`tests/test_exchange_pound_v5c.py`)**:
  - Testes integrados cobrindo:
    1. Cadastro de moto em `Pound` com MOT/Tax vencidos e garantia de isenção de alertas no `/api/dashboard`.
    2. Detecção precisa de motos sem V5C e filtros de busca `?v5c=missing`.
    3. Registro e baixa de transação com split payment utilizando método `Exchange`.
* **Cachebusters Atualizados**:
  - `app_shared.js?v=5`, `financeiro.js?v=11`, `detalhe_contrato.js?v=23`, `motos.js?v=9`, `moto_modal_shared.js?v=4`.

## [1.9.6] — 2026-09-24 — *Pre-Delivery Compliance: Optional Initial Inspection & Insurance with Actionable Release Reminders*

### 🚀 Fluxo de Pré-Entrega e Liberação de Veículos (Pre-Delivery Compliance)
* **Contratos Imediatos sem Bloqueio de Cadastro**:
  - No fluxo de vendas e aluguel, motocicletas frequentemente permanecem na oficina para instalação de acessórios extras (baús, suportes de smartphone, alarmes) e os clientes ainda estão cotando ou emitindo suas apólices de seguro.
  - Removida a exigência obrigatória de envio de fotos de vistoria (`fotos`) e apólice de seguro (`seguro`) no formulário de abertura de contrato (`/contratos/novo`).
  - Contratos podem ser formalizados, impressos e assinados imediatamente pelo operador sem travar a negociação comercial.
* **Barreira de Saída e Alertas de Pré-Entrega (Pre-Delivery Checklist)**:
  - O veículo **não pode deixar a loja/pátio** sem a vistoria de saída e o documento do seguro registrados.
  - **Banner de Alerta nos Detalhes do Contrato (`/contratos/<id>`)**:
    - Alerta estilizado em âmbar no topo da página detalhando exatamente o que está pendente (`📷 Check-out Inspection Photos` e/ou `🛡️ Insurance Certificate Document`).
    - Botões de ação rápida em 1 clique: `Record Check-out Inspection` e `Upload Insurance Document`.
    - Na aba de vistorias, caso a vistoria de saída esteja pendente, exibe bloco informativo com botão `📷 Take Photos Now` que abre o modal já configurado em modo `Check-out`.
  - **Badges e Filtro na Listagem de Contratos (`/contratos`)**:
    - Exibe badges informativos na coluna de status: `⚠️ Needs Insp + Ins`, `⚠️ Needs Insp` ou `⚠️ Needs Ins`.
    - Novo filtro rápido no dropdown de status: `⚠️ Pre-Delivery Pending (Needs Insp / Ins)` (`status=pending_release`).
  - **Alerta Proativo no Dashboard (`/`)**:
    - Alerta dinâmico na central de avisos destacando a quantidade de motocicletas com checklist de pré-entrega pendente com links diretos para cada contrato.
* **Performance & Backend**:
  - Otimização com `selectinload(Contract.vistorias)` e `joinedload(Contract.cliente)` em `GET /api/contratos` e `GET /api/dashboard`, eliminando N+1 queries.
* **Suíte de Testes Automatizados (`tests/test_prerelease_compliance.py`)**:
  - Teste cobrindo criação sem vistoria/seguro, flags na API, filtros de listagem, visualização no dashboard, anexação posterior de apólice e registro de vistoria de saída com desbloqueio automático do status.
* **Correção de Renderização nos Detalhes do Contrato (`/contratos/<id>`)**:
  - Corrigido conflito de escopo no JavaScript onde `stLower` havia sido re-declarado com `const`, gerando um SyntaxError no motor V8 que impedia a execução do listener `DOMContentLoaded`.
  - Cachebuster atualizado para `detalhe_contrato.js?v=21` garantindo invalidação imediata do cache do navegador.
* **Cachebusters Atualizados**:
  - `novo_contrato.js?v=4`, `detalhe_contrato.js?v=21`, `contratos.js?v=6`.

## [1.9.5] — 2026-09-24 — *DVLA SORN (Statutory Off Road Notification) Support & Exemption from Road Tax*

### 🛡️ Suporte a Veículos em SORN (Off Road) & Isenção de Road Tax
* **Marcação Oficial de SORN (Statutory Off Road Notification)**:
  - No Reino Unido, veículos parados no pátio ou oficina podem ser registrados como SORN junto à DVLA, ficando legalmente isentos de recolhimento de Road Tax (VED) e sem data de validade de imposto.
  - Implementado suporte nativo ao status **SORN** no cadastro de motos (`/motos/nova`), edição rápida (`#motoManageModal`), tabela de frotas (`/motos`) e detalhes do contrato (`/contratos/<id>`):
    - **Toggle / Checkbox Dinâmico (`🛡️ SORN`)**: ao marcar SORN, o seletor de data de Road Tax é desabilitado e limpo automaticamente, com feedback visual indicando que a moto está fora de circulação.
    - **Isenção de Alertas no Dashboard**: motos ativas com status SORN são automaticamente excluídas dos alertas de vencimento ou atraso de Road Tax (`diff_t < 0` e `diff_t <= 30`), eliminando falsos positivos na operação.
    - **Badge Exclusivo na Tabela de Frotas**: exibição de badge roxo/violeta estilizado `🛡️ SORN`, com suporte a ordenação e busca direta por palavra-chave (`search=sorn`).
    - **Visualização em Contratos**: no card do veículo em `/contratos/<id>`, o status de Road Tax exibe claramente `🛡️ SORN (Off Road)` em vez de "Not registered" ou vencimento inválido.
* **Banco de Dados & Auto-Migração (`database.py`)**:
  - Nova coluna `Motorcycle.tax_sorn = db.Column(db.Boolean, default=False, nullable=False, index=True)` com auto-migração compatível com PostgreSQL (`DEFAULT FALSE`) e SQLite (`DEFAULT 0`).
  - Novo índice `idx_motos_tax_sorn` na tabela `motos`.
* **Suíte de Testes Automatizados (`tests/test_motos_sorn.py`)**:
  - Teste completo cobrindo cadastro com SORN ativo, consulta de detalhes, busca por palavra-chave `sorn`, alteração de status (ligar/desligar SORN) e isenção de alertas no dashboard.
* **Cachebusters Atualizados**:
  - `cadastro_moto.js?v=2`, `motos.js?v=8`, `moto_modal_shared.js?v=3`, `detalhe_contrato.js?v=19`.

## [1.9.4] — 2026-09-24 — *Mobile Multi-Shot Camera Accumulator for V5C Multi-Page Document Uploads*

### 📄 Acumulador Multi-Página de Câmera Mobile para V5C (iOS / iPhone)
* **Solução Definitiva para Upload Multi-Página no iPhone**:
  - No Safari/iOS, o uso de um único `<input type="file" multiple>` forçava o fechamento da câmera após uma única foto, exigindo uploads individuais e lentos para documentos com frente e verso ou múltiplas páginas.
  - Implementado o padrão **Multi-Shot Camera Accumulator** no modal compartilhado de gestão de motos (`templates/moto_manage_modal.html` e `static/js/moto_modal_shared.js?v=2`):
    - **Botão Câmera (`📸 Take Page Photo`)**: aciona diretamente a câmera com `capture="environment"`, permitindo bater foto da Página 1, Página 2, Página 3 sucessivamente sem recarregar nem substituir as anteriores.
    - **Botão Galeria / PDF (`📁 Photo Library / PDF`)**: permite selecionar múltiplos arquivos ou certificados digitais em PDF de uma só vez.
    - **Fila Dinâmica de Pré-visualização**: exibe miniaturas das páginas enfileiradas com identificação (`Page 1`, `Page 2`...), tamanho do arquivo e botão individual de descarte (`×`) para refazer fotos desfocadas antes do envio.
    - **Envio Único e Otimizado**: botão inteligente `Upload to V5C (N pages)` envia todas as páginas acumuladas em uma única requisição POST (`/api/motos/<placa>/v5c`), com processamento e otimização no backend.
* **Cachebuster Atualizado**:
  - `moto_modal_shared.js?v=2` em `templates/motos.html` e `templates/detalhe_contrato.html`.

## [1.9.3] — 2026-09-24 — *Multi-Payment Methods (Split Payments) & Partial Settlement Architecture*

### 💳 Múltiplas Formas de Pagamento e Quitação Parcial (Split & Partial Payments)
* **Flexibilidade Total em Cobranças Financeiras**:
  - Suporte completo para divisão de pagamentos em múltiplas formas simultâneas (Cash, Card, Bank Transfer, Deposit, Other) para qualquer tipo de lançamento (vendas à vista `Sale_Full`, parcelas `Sale_Installment`, aluguel semanal `Rent`, depósitos e multas).
  - Suporte a **baixas parciais** inteligentes: se o cliente pagar um valor inferior ao total devido, o valor pago é liquidado com as formas informadas e o saldo restante é lançado automaticamente como uma nova cobrança filha pendente com o mesmo vencimento original e vinculada via `id_transacao_origem`.
* **Banco de Dados & Auto-Migração (`database.py`)**:
  - Coluna `FinancialTransaction.forma_pagamento` expandida de `VARCHAR(50)` para `VARCHAR(255)` com migração automática para PostgreSQL e SQLite.
  - Adicionadas colunas `detalhes_pagamento_json` (TEXT) e `id_transacao_origem` (INTEGER) para rastreabilidade e histórico estruturado de métodos e divisões parciais.
* **Backend Robusto & Estorno Inteligente (`app.py`)**:
  - `/api/financeiro/pagar/<id>` e `/api/cobrancas/<id>/pagar`: processam payloads com `metodos_pagamento` ou fallback de método único com validação estrita de valores positivos e limite do montante devido.
  - Reversão/Estorno (`/api/financeiro/<id>/reverter`): reintegra automaticamente saldos restantes filhos que continuam pendentes de volta ao lançamento original (auto-merge), excluindo a transação filha e restaurando o montante integral.
  - Finalização de contratos de venda: contratos `Sale_Full` e `Sale_Installment` só transitam para `Completed` quando todas as transações, incluindo saldos parciais, forem integralmente quitadas.
* **Componente de Frontend Universal (`static/js/app_shared.js`)**:
  - Função modular `createSplitPaymentManager`: gerencia dinamicamente linhas de formas de pagamento, sugestão automática de saldo restante ao adicionar novo método, cálculo em tempo real de valores pagos e remanescentes, e badges visuais dinâmicos (Full Settlement / Partial Payment / Exceeds Due).
* **Modais Padronizados & Recibos Aprimorados**:
  - Modais em `/financeiro` (`static/js/financeiro.js?v=8`) e `/contratos/<id>` (`static/js/detalhe_contrato.js?v=18`): interface interativa e responsiva para smartphone e desktop.
  - Recibo `/recibo/<id>` (`templates/recibo.html`): exibe o detalhamento discriminado de cada forma de pagamento e valor quando houver múltiplos métodos.
* **Suíte de Testes Automatizados**:
  - Novo teste `tests/test_split_partial_payments.py` cobrindo quitação total dividida, pagamentos parciais, estorno com auto-merge, quitação em múltiplos passos e validações de segurança.

## [1.9.2] — 2026-09-23 — *Legal Compliance: Clause 4.12 GPS/Telematics Tracking Devices for Rental and Sales Agreements*

### 📜 Atualização dos Contratos Legais (Print & PDF A4)
* **Contrato de Aluguel (`contrato_print.html`)**:
  - Inserida a cláusula **4.12 Vehicle Tracking Devices (GPS/Telematics)** na Página 3, formalizando o consentimento expresso do locatário para fins de segurança, proteção patrimonial e conformidade com o UK GDPR, com autorização de localização e recuperação em casos de inadimplência, furto ou quebra contratual.
* **Contratos de Venda à Vista e Parcelada (`contrato_venda_print.html`)**:
  - Inserida a cláusula **4.12 Vehicle Tracking Devices (GPS/Telematics)** contemplando:
    - **Item a (Venda Parcelada)**: Monitoramento ativo mantido pela FF Motors até a quitação integral do saldo devedor.
    - **Item b (Venda à Vista)**: Confirmação de cessação imediata de monitoramento após quitação integral, com direito de o comprador remover o dispositivo ou solicitar remoção gratuita na oficina.
    - Garantia de processamento de dados sob o UK GDPR.

## [1.9.1] — 2026-09-23 — *Accounting Precision: Due Date Overdue Criterion Alignment & Midnight Normalization*

### 💰 Alinhamento de Regra de Negócio Contábil para Vencimentos em Atraso (Overdue)
* **Correção do Critério Temporal de Atraso**:
  - Ajustadas as consultas em `/relatorios/vencidos`, `/api/financeiro?status=overdue` e `/api/dashboard` para comparar a `data_vencimento` com o **início do dia atual** no fuso de Londres (`00:00:00`), em vez do instante com hora, minuto e segundo (`agora`).
  - Cobranças com vencimento no dia de hoje permanecem com status `Pending` durante as 24 horas do dia (até 23:59:59), tornando-se `Overdue` (em atraso) estritamente a partir da meia-noite (`00:00:00`) do dia seguinte caso não sejam liquidadas.
  - Elimina a divergência na qual cobranças de hoje apareciam no relatório de atrasados, mas com badge amarelo de `Pending` na listagem financeira.
* **Normalização de `data_vencimento` no Banco de Dados**:
  - A criação de contratos de aluguel e venda (`criar_contrato`) e o gerador semanal (`_gerar_cobrancas_semanais_logic`) agora normalizam os vencimentos gerados com hora zerada (`.replace(hour=0, minute=0, second=0, microsecond=0)`), eliminando horários fracionários herdados do momento do clique.
* **Reforço de Comparação de Datas no Frontend**:
  - `static/js/financeiro.js` e `static/js/detalhe_contrato.js`: normalização das datas para `00:00:00` na checagem de `isVencido`, prevenindo inconsistências por fuso horário local do navegador.
  - Cachebusters incrementados em `templates/financeiro.html` (`?v=7`) e `templates/detalhe_contrato.html` (`?v=17`).
* **Suíte de Testes Automatizados Dedicada**:
  - Adicionado `tests/test_overdue_business_rule.py` cobrindo cenários de cobranças de ontem (vencidas), hoje 01:00 AM (não vencidas), hoje 15:30 (não vencidas), pagas (não vencidas) e amanhã (não vencidas).

## [1.9.0] — 2026-09-23 — *Multi-Worker Scheduler Isolation, Atomic Job Concurrency Lock & Safe Deduplication Cleanup Tool*

### ⚙️ Isolamento de Processos e Prevenção de Concorrência
* **Isolamento de Processo para o Agendador (`wsgi.py`)**:
  - Implementado lock exclusivo de arquivo (`fcntl.flock` no arquivo `.scheduler.lock` no Linux).
  - Garante que, mesmo que o Gunicorn execute com múltiplos workers (2 a 4 processos concorrentes), **apenas 1 worker exclusivo** inicialize a thread do `BackgroundScheduler`. Os outros workers ignoram a inicialização.
  - Liberação automática do lock pelo sistema operacional caso o worker seja reciclado.
* **Trava Condicional Atômica no Banco de Dados (`run_daily_jobs`)**:
  - Substituído o padrão vulnerável de `SELECT` + `UPDATE` por um `UPDATE` condicional atômico (`JobExecutionLock.query.filter(job_name == name, last_run_date != london_date_str).update(...)`).
  - Serializado pelo banco de dados (PostgreSQL e SQLite WAL): exatamente **1 chamada** obtém sucesso (`rows_updated == 1`), eliminando qualquer possibilidade de execução duplicada por workers simultâneos às 01:00 AM.
* **Mutex em Memória e Commit por Contrato (`_gerar_cobrancas_semanais_logic`)**:
  - Proteção por `_BILLING_MUTEX` (`threading.Lock`) e execução de `db.session.commit()` imediato após a criação da cobrança de cada contrato, assegurando que transações e threads concorrentes enxerguem os dados atualizados de imediato.
* **Isenção de CSRF e Autenticação para Endpoints de Automação**:
  - Configurada isenção segura de CSRF para chamadas de sistema e cron autenticadas por chave de API (`X-Cron-Key`).

### 🧹 Ferramenta de Auditoria e Limpeza de Duplicidades (`cleanup_duplicate_charges.py`)
* **Script CLI Standalone**:
  - `python cleanup_duplicate_charges.py`: Modo simulação (`--dry-run`) exibindo relatório dos contratos afetados, IDs mantidos e IDs excedentes.
  - `python cleanup_duplicate_charges.py --apply [-y]`: Execução com exclusão segura das cobranças duplicadas pendentes.
* **Regras Estritas de Segurança**:
  - Afeta exclusivamente transações de aluguel (`Rent`) com status `PENDING`.
  - **Preserva sempre** a transação original (menor ID) para cada vencimento.
  - **Nunca toca** em transações pagas (`Paid`), depósitos ou vendas.
* **Endpoint Administrativo (`/api/admin/limpar-cobrancas-duplicadas`)**:
  - Rota protegida por privilégio administrativo ou chave de cron para auditoria e limpeza remota via navegador ou API.

### 🧪 Cobertura de Testes Automatizados
* **Nova Suíte de Testes (`tests/test_concurrency_and_deduplication.py`)**:
  - Simulação de concorrência com 6 workers simultâneos disparando rotinas no mesmo segundo.
  - Validação de idempotência da rotina de aluguel semanal.
  - Validação da detecção e expurgo de duplicatas com proteção a transações pagas e depósitos.

## [1.8.0] — 2026-09-22 — *Motorcycle V5C Logbook Documents & Multi-Tracker Management System*

### 📄 Gestão de Documentos V5C (Logbook)
* **Suporte a Múltiplas Páginas e PDFs**: Cada motocicleta agora pode armazenar páginas fotografadas do seu documento de registro britânico V5C (Logbook) ou o certificado digital completo em PDF.
* **Modelo `MotorcycleV5C`**: Criada a tabela `moto_v5c` com campos `placa`, `url_arquivo`, `nome_original`, `tipo_arquivo` (`image` ou `pdf`), `criado_por_nome` e `data_criacao`.
* **Endpoints Dedicados**:
  - `POST /api/motos/<placa>/v5c`: Upload múltiplo com otimização automática de imagens, suporte a PDF e registro de auditoria `MOTO_V5C_UPLOADED`.
  - `DELETE /api/motos/<placa>/v5c/<id>`: Exclusão com limpeza do arquivo físico em disco e log de auditoria `MOTO_V5C_DELETED`.
* **Interface do Usuário**: Aba dedicada no modal de gerenciamento (`#tabV5C`), miniaturas com zoom interativo (lightbox) para imagens, link de abertura para PDFs e contadores dinâmicos na tabela principal.
* **Atalho no Card de Veículo em Detalhes do Contrato**:
  - Inseridos botões dedicados de atalho rápido no card de veículo da tela de detalhes do contrato (`/contratos/<id>`): **"📄 V5C"** e **"📡 Trackers"** com contadores dinâmicos em tempo real.
  - Permite abrir e gerenciar os documentos V5C e rastreadores GPS diretamente na tela do contrato sem precisar navegar para `/motos`.
  - Atualização reativa instantânea dos badges na tela ao anexar ou excluir documentos e rastreadores.

### 📡 Gestão de Múltiplos Rastreadores GPS (Trackers)
* **Múltiplos Trackers por Moto**: Uma motocicleta pode possuir um ou mais rastreadores GPS simultaneamente (ex: rastreador corporativo da FF Motors + rastreador privado do cliente).
* **Identificação de Propriedade**: Badge visual com distinção imediata entre:
  - 🏢 `Company`: FF Motors (Nosso Tracker) em verde escuro/claro.
  - 👤 `Customer`: Cliente (Tracker do Cliente) em roxo.
* **Número de Série / IMEI e Observações**: Registro obrigatório do serial/IMEI e notas de instalação (ex: modelo Monimoto, chicote da ignição, localização física no chassi).
* **Fotos do Rastreador (Multi-Shot Camera)**:
  - Integração com o acumulador multi-foto mobile (câmera com `capture="environment"` e galeria), permitindo fotografar a etiqueta de número de série e o local de fixação.
  - Armazenamento em `MotorcycleTracker.url_fotos`.
* **Remoção de Tracker**:
  - Endpoint `DELETE /api/motos/<placa>/trackers/<id>` permitindo a desinstalação/remoção completa do rastreador da moto com confirmação e expurgo automático das fotos físicas em disco.

### 🛡️ Proteção de Armazenamento e Limpeza
* **Whitelist `cleanup_uploads.py`**: Atualizada a função `collect_valid_files()` para proteger integralmente todos os documentos V5C e todas as fotos de rastreadores contra purga acidental.
* **Integração `reset_data.py`**: Adicionada limpeza e reset de sequência universal para `moto_v5c` e `moto_trackers`.

## [1.7.4] — 2026-09-21 — *Sales Contract Lifecycle (Auto-Completion upon Quittance) & Mileage Tracker Optimization*

### 🏍️ Ajuste de Quilometragem em Contratos de Venda
* **Remoção de "Return Mileage" para Vendas**: Motocicletas vendidas não retornam à frota de aluguel. O card de informações do veículo em detalhes do contrato (`detalhe_contrato.html` / `detalhe_contrato.js`) agora oculta as linhas `"Return Mileage"` e `"Miles driven"` quando o contrato for `Sale_Full` ou `Sale_Installment`.
* **Rótulo Apropriado**: O rótulo `"Start Mileage:"` é dinamicamente alterado para `"Sale Mileage:"`, exibindo com precisão a quilometragem no momento da entrega da venda.
* **Cache Buster Atualizado**: Script atualizado para `detalhe_contrato.js?v=15`.

### 🏁 Ciclo de Vida e Conclusão de Contratos de Venda
* **Regra de Conclusão Automática (`Completed`)**:
  - **Venda à Vista (`Sale_Full`)**: O contrato transiciona automaticamente para status `Completed` no instante em que a transação de pagamento integral for marcada como `Paid`.
  - **Venda Parcelada (`Sale_Installment`)**: O contrato transiciona automaticamente para status `Completed` assim que a entrada (`Sale_Deposit`) e todas as parcelas (`Sale_Installment`) forem baixadas como `Paid` (saldo devedor liquidado / £0.00 pendente).
  - **Validação Proativa**: A rota de detalhes do contrato (`/api/contratos/<id>`) também checa o status financeiro e atualiza contratos de venda quitados para `Completed`.
* **Estorno Seguro e Reabertura Automática**:
  - Se um operador reverter uma transação (`POST /api/financeiro/<id>/reverter`) de um contrato de venda já concluído, o sistema reabre o contrato automaticamente para `Active` (`ContractStatus.ATIVO`) e grava o evento `CONTRACT_REOPENED` no `AuditLog`.
  - Adicionada rota de conveniência `/api/financeiro/reverter/<id>` em paridade com `/api/financeiro/pagar/<id>`.

### 📊 Ajuste nos Indicadores do Dashboard (Frota Ativa & Disponíveis em Geral)
* **Exclusão de Motos Vendidas do "Total Fleet"**: O total de motocicletas na frota (`total_motos`) agora contabiliza estritamente a frota ativa (`Available` + `Rented` + `Maintenance`), excluindo motos vendidas (`Sold`). A barra de distribuição percentual da frota agora fecha com precisão em 100% da frota em operação.
* **Redefinição de "Available"**: O indicador "Available to Rent" foi renomeado para **"Available"** com descrição `"Available in general"`, esclarecendo que as motos disponíveis no pátio atendem tanto à locação quanto à venda imediata.
* **Compliance de TAX & MOT (Oportunidade Comercial de Oficina)**: 
  - **Road Tax**: Checado exclusivamente para a frota ativa em operação (motos vendidas são isentas, pois o imposto é pago pelo comprador ao DVLA).
  - **MOT**: Monitorado para **toda a base de motocicletas, incluindo motos vendidas (`Sold`)**. Permite que a FF Motors acompanhe vencimentos de MOT de clientes que compraram motos na loja, contatando-os com antecedência para agendar revisão pré-MOT e faturar o serviço de oficina.

## [1.7.3] — 2026-09-21 — *iPhone AirPrint & PDF Perfection (Zero Blank Pages, 3-Page Rental & Balanced Sales)*

### 📱 Correção de Impressão no iPhone / iOS Safari
* **Eliminação de Páginas em Branco no iPhone**:
  - **Diagnóstico WebKit Mobile**: O iOS Safari (AirPrint e Salvar como PDF) impõe margens físicas de hardware de aproximadamente 15mm (~950px de altura disponível), menores que os 1060px do desktop Chrome. Conteúdos que no computador cabiam no limite, no iPhone sofriam um estouro de 10 a 100px, forçando a criação de páginas fantasmas em branco.
  - **Remoção de `break-inside: avoid` em `.agreement-page`**: Evita que o motor de layout do WebKit crie quebras forçadas de página inteira quando o conteúdo se aproxima da borda inferior.
  - **Proteção dos Grids de Assinatura**: Forçado `display: grid; grid-template-columns: 1fr 1fr !important` e `display: flex; flex-direction: row !important` em `@media print`, garantindo que as assinaturas permaneçam lado a lado na impressão mesmo quando disparada de telas pequenas de celular.
* **Contrato de Aluguel em Exatas 3 Páginas Balanceadas (`contrato_print.html`)**:
  - **Página 1 (de 3)**: Partes, Veículo, Requisitos/Depósito (3.1 a 3.4) e Termos 4.1 a 4.3 (`Page 1 of 3`).
  - **Página 2 (de 3)**: Termos operacionais e de responsabilidade 4.4 a 4.8 (MOT, Multas, Acidentes, Furto, Restrições de Uso) (`Page 2 of 3`).
  - **Página 3 (de 3)**: Termos legais 4.9 a 4.11 (GDPR, Indenização, Jurisdição), Declaração e Assinaturas de Início (Seção 5) e Declaração e Assinaturas de Devolução (Seção 6) (`Page 3 of 3`).
  - **Zero Páginas Sobrando**: Todas as páginas possuem entre 280px e 430px de margem de segurança contra estouro de margens.
* **Contrato de Venda à Vista em Exatas 2 Páginas (`contrato_venda_print.html`)**:
  - **Grid Executivo em 2 Colunas (`.print-two-col`)**: Reestruturadas as Seções 1 (Vendedor e Comprador) e Seções 2 & 3 (Veículo e Preço) para exibição lado a lado na impressão. Reduziu a metade superior da Página 1 de 400px para apenas ~190px.
  - **Página 1 (de 2)**: Contém Partes, Veículo, Finanças e Termos 4.1 a 4.4 (~500px de altura total, folga de mais de 400px).
  - **Página 2 (de 2)**: Contém Termos 4.5 a 4.11 e Seção 5 de Assinaturas (~580px de altura total, folga de mais de 350px).
  - **Zero Páginas Sobrando**: Erradicado o vazamento que gerava uma folha intermediária em branco no iPhone.
* **Contrato de Venda Parcelada em Exatas 3 Páginas (`contrato_venda_print.html`)**:
  - **Página 1 (de 3)**: Partes em 2 colunas, Veículo, Finanças e Tabela do Cronograma de Parcelas (`Page 1 of 3`).
  - **Página 2 (de 3)**: Termos gerais 4.1 a 4.8 (`Page 2 of 3`).
  - **Página 3 (de 3)**: Termo 4.9 (GDPR), 4.10, 4.11 e Seção 5 de Assinaturas (`Page 3 of 3`).

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
