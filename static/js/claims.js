let paginaAtual = 1;
let termoBusca = '';
let filtroEmpresaVal = '';
let filtroStatusVal = 'Em Aberto';
let campoDataVal = 'acidente';
let dataInicioVal = '';
let dataFimVal = '';
let sortCol = 'id';
let sortOrder = 'desc';
let claimSelecionadoId = null;

document.addEventListener('DOMContentLoaded', () => {
    // Inicializa listeners de busca e filtros
    const searchInput = document.getElementById('claimSearchInput');
    let timeoutId;
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                termoBusca = e.target.value.trim();
                paginaAtual = 1;
                carregarClaims();
            }, 400);
        });
    }

    const selEmpresa = document.getElementById('filtroEmpresa');
    if (selEmpresa) {
        selEmpresa.addEventListener('change', (e) => {
            filtroEmpresaVal = e.target.value;
            paginaAtual = 1;
            carregarClaims();
        });
    }

    const selStatus = document.getElementById('filtroStatus');
    if (selStatus) {
        selStatus.addEventListener('change', (e) => {
            filtroStatusVal = e.target.value;
            paginaAtual = 1;
            carregarClaims();
        });
    }

    const selCampoData = document.getElementById('filtroCampoData');
    if (selCampoData) {
        selCampoData.addEventListener('change', (e) => {
            campoDataVal = e.target.value;
            if (dataInicioVal || dataFimVal) {
                paginaAtual = 1;
                carregarClaims();
            }
        });
    }

    const inpDataInicio = document.getElementById('filtroDataInicio');
    if (inpDataInicio) {
        inpDataInicio.addEventListener('change', (e) => {
            dataInicioVal = e.target.value;
            paginaAtual = 1;
            carregarClaims();
        });
    }

    const inpDataFim = document.getElementById('filtroDataFim');
    if (inpDataFim) {
        inpDataFim.addEventListener('change', (e) => {
            dataFimVal = e.target.value;
            paginaAtual = 1;
            carregarClaims();
        });
    }

    const btnClear = document.getElementById('btnClearClaimFilters');
    if (btnClear) {
        btnClear.addEventListener('click', () => {
            termoBusca = '';
            filtroEmpresaVal = '';
            filtroStatusVal = 'Em Aberto';
            campoDataVal = 'acidente';
            dataInicioVal = '';
            dataFimVal = '';
            sortCol = 'id';
            sortOrder = 'desc';
            paginaAtual = 1;

            if (searchInput) searchInput.value = '';
            if (selEmpresa) selEmpresa.value = '';
            if (selStatus) selStatus.value = 'Em Aberto';
            if (selCampoData) selCampoData.value = 'acidente';
            if (inpDataInicio) inpDataInicio.value = '';
            if (inpDataFim) inpDataFim.value = '';

            carregarClaims();
        });
    }

    // Botões de Paginação
    const btnPrev = document.getElementById('btnPrevPage');
    const btnNext = document.getElementById('btnNextPage');
    if (btnPrev) btnPrev.addEventListener('click', () => { if (paginaAtual > 1) { paginaAtual--; carregarClaims(); } });
    if (btnNext) btnNext.addEventListener('click', () => { paginaAtual++; carregarClaims(); });

    // Habilitar ordenação na tabela
    if (typeof enableTableSorting === 'function') {
        enableTableSorting('claimsTable', (field, order) => {
            sortCol = field;
            sortOrder = order;
            paginaAtual = 1;
            carregarClaims();
        });
    }

    carregarClaims();
});

async function carregarClaims() {
    const tbody = document.getElementById('claimsTableBody');
    const paginationInfo = document.getElementById('paginationInfo');
    const btnClear = document.getElementById('btnClearClaimFilters');
    const btnPrev = document.getElementById('btnPrevPage');
    const btnNext = document.getElementById('btnNextPage');

    if (!tbody) return;

    if (btnClear) {
        const hasFilters = termoBusca || filtroEmpresaVal || (filtroStatusVal !== 'Em Aberto') || dataInicioVal || dataFimVal;
        btnClear.style.display = hasFilters ? 'inline-block' : 'none';
    }

    const params = new URLSearchParams({
        page: paginaAtual,
        limit: 20,
        search: termoBusca,
        empresa: filtroEmpresaVal,
        status: (filtroStatusVal === 'todos') ? '' : filtroStatusVal,
        campo_data: campoDataVal,
        data_inicio: dataInicioVal,
        data_fim: dataFimVal,
        sort_by: sortCol,
        sort_order: sortOrder
    });

    try {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:2.5rem; color:var(--text-secondary);">Carregando processos de claims...</td></tr>`;

        const res = await fetch(`/api/claims?${params.toString()}`);
        if (!res.ok) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:2rem; color:#f87171;">Erro ao carregar claims (${res.status}).</td></tr>`;
            return;
        }

        const data = await res.json();
        const claims = data.claims || data.itens || [];
        listaClaims = claims;
        atualizarKPIs(data.resumo || {});
        renderizarTabelaClaims(claims);

        // Paginação UI
        if (paginationInfo) {
            paginationInfo.textContent = `Página ${data.pagina_atual || 1} de ${data.paginas || 1} (${data.total || 0} processos)`;
        }
        if (btnPrev) btnPrev.disabled = (data.pagina_atual || 1) <= 1;
        if (btnNext) btnNext.disabled = (data.pagina_atual || 1) >= (data.paginas || 1);

        if (typeof setTableSortIndicator === 'function') {
            setTableSortIndicator('claimsTable', sortCol, sortOrder);
        }

    } catch (err) {
        console.error('Erro ao buscar claims:', err);
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:2rem; color:#f87171;">Erro de conexão com o servidor.</td></tr>`;
    }
}

function atualizarKPIs(resumo) {
    const kpiIndicacao = document.getElementById('kpi_indicacao_pendente');
    const kpiIndicacaoDesc = document.getElementById('kpi_indicacao_desc');
    const kpiStorage = document.getElementById('kpi_motos_storage');
    const kpiStorageDesc = document.getElementById('kpi_storage_desc');
    const kpiInvoice = document.getElementById('kpi_storage_pendente');
    const kpiInvoiceDesc = document.getElementById('kpi_invoice_desc');
    const kpiTotal = document.getElementById('kpi_total_claims');
    const kpiTotalDesc = document.getElementById('kpi_total_claims_desc');

    if (kpiIndicacao) kpiIndicacao.textContent = `£${(resumo.total_indicacao_pendente || 0).toFixed(2)}`;
    if (kpiIndicacaoDesc) {
        const at = resumo.alertas_indicacao_atrasada || 0;
        kpiIndicacaoDesc.textContent = at > 0 ? `⚠️ ${at} indicação(ões) atrasada(s)` : `🟢 Todas no prazo`;
        kpiIndicacaoDesc.style.color = at > 0 ? '#f87171' : '#10b981';
    }

    if (kpiStorage) kpiStorage.textContent = resumo.motos_no_storage || 0;
    if (kpiStorageDesc) {
        const st28 = resumo.alertas_storage_28d || 0;
        kpiStorageDesc.textContent = st28 > 0 ? `⚠️ ${st28} moto(s) atingindo 28 dias` : `Pátio em conformidade`;
        kpiStorageDesc.style.color = st28 > 0 ? '#f59e0b' : 'var(--text-secondary)';
    }

    if (kpiInvoice) kpiInvoice.textContent = `£${(resumo.total_storage_pendente || 0).toFixed(2)}`;
    if (kpiInvoiceDesc) {
        const invAt = resumo.alertas_invoice_atrasado || 0;
        kpiInvoiceDesc.textContent = invAt > 0 ? `⚠️ ${invAt} invoice(s) vencido(s)` : `Cobranças em dia`;
        kpiInvoiceDesc.style.color = invAt > 0 ? '#f87171' : 'var(--text-secondary)';
    }

    // Processos Abertos
    if (kpiTotal) kpiTotal.textContent = resumo.processos_abertos !== undefined ? resumo.processos_abertos : (resumo.total_claims || 0);
    if (kpiTotalDesc) {
        kpiTotalDesc.textContent = `${resumo.total_claims || 0} cadastrados no total`;
    }
}

function formatarDataUK(dataStr) {
    if (!dataStr) return '-';
    // Accepts YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
    const parteData = dataStr.includes('T') ? dataStr.split('T')[0] : dataStr.split(' ')[0];
    const partes = parteData.split('-');
    if (partes.length === 3) {
        return `${partes[2]}/${partes[1]}/${partes[0]}`;
    }
    return dataStr;
}

function renderizarTabelaClaims(claims) {
    const tbody = document.getElementById('claimsTableBody');
    if (!tbody) return;

    if (claims.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:3rem; color:var(--text-secondary);">Nenhum claim encontrado para os filtros selecionados.</td></tr>`;
        return;
    }

    tbody.innerHTML = '';
    claims.forEach(c => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid var(--border-color)';

        // 0. Badge Status Geral do Processo (agora integrado na 1ª coluna)
        let badgeStatusGeral = '';
        if (c.status === 'Concluido') {
            badgeStatusGeral = `<span class="badge badge-success" style="font-size: 0.7rem; font-weight: 700; padding: 2px 7px;">Concluído</span>`;
        } else if (c.status === 'Cancelado') {
            badgeStatusGeral = `<span class="badge badge-danger" style="font-size: 0.7rem; font-weight: 700; padding: 2px 7px;">Cancelado</span>`;
        } else {
            badgeStatusGeral = `<span class="badge badge-warning" style="background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); font-size: 0.7rem; font-weight: 700; padding: 2px 7px;">Em Aberto</span>`;
        }

        // 1. Badge Indicação (14 dias)
        let badgeInd = '';
        if (c.status_indicacao === 'Pago') {
            badgeInd = `<span class="badge badge-success">✓ Pago (£${c.valor_indicacao.toFixed(2)})</span>`;
        } else if (c.indicacao_atrasada) {
            badgeInd = `<span class="badge badge-danger">⚠️ ATRASADO (£${c.valor_indicacao.toFixed(2)})</span>`;
        } else if (c.dias_para_indicacao !== null) {
            const cor = c.dias_para_indicacao <= 3 ? 'badge-warning' : 'badge-info';
            badgeInd = `<span class="badge ${cor}">£${c.valor_indicacao.toFixed(2)} (em ${c.dias_para_indicacao}d)</span>`;
        } else {
            badgeInd = `<span class="badge badge-secondary">Aguardando Aprov.</span>`;
        }

        // 2. Badge Storage (28 dias para liberar moto)
        let badgeStorage = '';
        if (c.status_storage === 'No Pátio') {
            if (c.storage_vencendo_28d) {
                badgeStorage = `<span class="badge badge-warning" style="background:rgba(245,158,11,0.2); color:#f59e0b; border:1px solid rgba(245,158,11,0.4);">⚠️ No Pátio (${c.dias_storage}d / limite 28d)</span>`;
            } else {
                badgeStorage = `<span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3);">No Pátio (${c.dias_storage} dias)</span>`;
            }
        } else if (c.status_storage === 'Liberado') {
            badgeStorage = `<span class="badge" style="background:rgba(168,85,247,0.15); color:#c084fc; border:1px solid rgba(168,85,247,0.3);">Moto Liberada (${c.dias_storage}d)</span>`;
        } else {
            badgeStorage = `<span class="badge badge-success">Liberado & Faturado</span>`;
        }

        // 3. Badge Invoice / Cobrança
        let badgeInvoice = '';
        if (c.status_pagamento_storage === 'Pago') {
            badgeInvoice = `<span class="badge badge-success">✓ Storage Pago (£${c.valor_total_storage.toFixed(2)})</span>`;
        } else if (c.data_envio_invoice) {
            if (c.invoice_atrasado) {
                badgeInvoice = `<span class="badge badge-danger">⚠️ Invoice Vencido (£${c.valor_total_storage.toFixed(2)})</span>`;
            } else {
                badgeInvoice = `<span class="badge badge-info">Invoice Enviado (vence em ${c.dias_para_pagamento_invoice}d)</span>`;
            }
        } else if (c.status_storage === 'Liberado') {
            badgeInvoice = `<span class="badge badge-warning" style="background:rgba(234,88,12,0.15); color:var(--accent); border:1px solid rgba(234,88,12,0.3);">⚠️ Enviar Invoice (£${c.valor_total_storage.toFixed(2)})</span>`;
        } else {
            badgeInvoice = `<span style="font-size:0.8rem; color:var(--text-secondary);">Acumulando: £${c.valor_total_storage.toFixed(2)}</span>`;
        }

        const dataAprovUK = c.data_aprovacao ? formatarDataUK(c.data_aprovacao) : 'Pendente';
        const dataEntradaUK = c.data_entrada_storage ? formatarDataUK(c.data_entrada_storage) : '-';
        const dataLibUK = c.data_liberacao_storage ? formatarDataUK(c.data_liberacao_storage) : '-';
        const dataInvoiceUK = c.data_envio_invoice ? formatarDataUK(c.data_envio_invoice) : '';
        const dataCriacaoUK = c.data_criacao ? formatarDataUK(c.data_criacao) : '-';

        tr.innerHTML = `
            <td style="padding: 1rem;">
                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                    <span style="font-weight: 700; color: var(--text-primary); font-size: 0.95rem;">
                        ${escapeHtml(c.claim_number)}
                    </span>
                    ${badgeStatusGeral}
                </div>
                <div style="font-size: 0.82rem; color: #f59e0b; font-weight: 600; margin-top: 3px;">
                    ${escapeHtml(c.empresa_parceira)}
                </div>
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px;">
                    Criado em ${dataCriacaoUK}
                </div>
            </td>

            <td style="padding: 1rem;">
                <div style="font-weight: 600; color: var(--text-primary);">
                    ${escapeHtml(c.cliente_nome)}
                </div>
                <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
                    <span class="badge" style="background: rgba(255,255,255,0.06); font-family: monospace; font-weight: 700;">
                        ${escapeHtml(c.placa)}
                    </span>
                    <span style="font-size: 0.78rem; color: var(--text-secondary);">
                        ${escapeHtml(c.modelo_moto || '')}
                    </span>
                </div>
            </td>

            <td style="padding: 1rem;">
                ${badgeInd}
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px;">
                    Aprov: ${dataAprovUK}
                </div>
            </td>

            <td style="padding: 1rem;">
                ${badgeStorage}
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px;">
                    Entrada: ${dataEntradaUK} | Lib: ${dataLibUK}
                </div>
            </td>

            <td style="padding: 1rem;">
                ${badgeInvoice}
                <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 4px;">
                    ${dataInvoiceUK ? `Envio: ${dataInvoiceUK}` : ''}
                </div>
            </td>

            <td style="padding: 1rem; text-align: right;">
                <div style="display: inline-flex; gap: 6px;">
                    <button type="button" class="btn-secondary" onclick="abrirModalEditClaim(${c.id})" style="padding: 6px 12px; font-size: 0.8rem;">
                        Editar / Baixa
                    </button>
                    ${c.dias_storage > 0 ? `
                    <a href="/claims/invoice/${c.id}" class="btn-secondary" title="Abrir Invoice de Storage" style="padding: 6px 10px; font-size: 0.8rem; text-decoration: none;">
                        📄
                    </a>
                    ` : ''}
                </div>
            </td>
        `;

        tbody.appendChild(tr);
    });
}

// --- Modals Novo Claim ---
function abrirModalNovoClaim() {
    const f = document.getElementById('formNovoClaim');
    if (f) f.reset();
    const modal = document.getElementById('modalNovoClaim');
    if (modal) modal.style.display = 'flex';
}

function fecharModalNovoClaim() {
    const modal = document.getElementById('modalNovoClaim');
    if (modal) modal.style.display = 'none';
}

async function handleNovoClaimSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSalvarNovoClaim');
    if (btn) btn.disabled = true;

    const payload = {
        empresa_parceira: document.getElementById('novo_empresa_parceira').value,
        claim_number: document.getElementById('novo_claim_number').value.trim(),
        cliente_nome: document.getElementById('novo_cliente_nome').value.trim(),
        cliente_telefone: document.getElementById('novo_cliente_telefone').value.trim(),
        placa: document.getElementById('novo_placa').value.trim(),
        modelo_moto: document.getElementById('novo_modelo_moto').value.trim(),
        data_aprovacao: document.getElementById('novo_data_aprovacao').value || null,
        valor_indicacao: document.getElementById('novo_valor_indicacao').value,
        data_entrada_storage: document.getElementById('novo_data_entrada_storage').value || null,
        valor_diaria_storage: document.getElementById('novo_valor_diaria_storage').value,
        observacoes: document.getElementById('novo_observacoes').value.trim()
    };

    try {
        const res = await fetch('/api/claims', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) {
            alert(data.error || 'Erro ao registrar claim');
            return;
        }

        fecharModalNovoClaim();
        await carregarClaims();
        alert('Processo de Claim registrado com sucesso!');
    } catch (err) {
        console.error('Erro:', err);
        alert('Erro ao se conectar com o servidor.');
    } finally {
        if (btn) btn.disabled = false;
    }
}

// --- Modal Edição e Baixas ---
function abrirModalEditClaim(id) {
    const claim = listaClaims.find(c => c.id === id);
    if (!claim) return;

    claimSelecionadoId = id;
    document.getElementById('edit_claim_id').value = id;
    document.getElementById('editClaimTitle').textContent = `Claim #${claim.claim_number} — ${claim.empresa_parceira}`;
    document.getElementById('editClaimSubtitle').textContent = `Cliente: ${claim.cliente_nome} | Moto: ${claim.placa}`;

    // Bloco 1: Indicação
    document.getElementById('edit_data_aprovacao').value = claim.data_aprovacao || '';
    document.getElementById('edit_valor_indicacao').value = claim.valor_indicacao || 0;
    document.getElementById('edit_data_pagamento_indicacao').value = claim.data_pagamento_indicacao || '';
    const badgeInd = document.getElementById('badgeIndicacaoModal');
    if (badgeInd) {
        badgeInd.innerHTML = claim.status_indicacao === 'Pago'
            ? '<span class="badge badge-success">Pago</span>'
            : (claim.indicacao_atrasada ? '<span class="badge badge-danger">Atrasado</span>' : '<span class="badge badge-info">Pendente</span>');
    }

    // Bloco 2: Storage
    document.getElementById('edit_data_entrada_storage').value = claim.data_entrada_storage || '';
    document.getElementById('edit_data_liberacao_storage').value = claim.data_liberacao_storage || '';
    document.getElementById('storageResumoModal').textContent = `${claim.dias_storage} dia(s) calculados — Total: £${claim.valor_total_storage.toFixed(2)}`;
    const badgeSt = document.getElementById('badgeStorageModal');
    if (badgeSt) {
        badgeSt.innerHTML = `<span class="badge badge-secondary">${claim.status_storage}</span>`;
    }

    // Bloco 3: Invoices
    document.getElementById('edit_data_envio_invoice').value = claim.data_envio_invoice || '';
    document.getElementById('edit_data_pagamento_storage').value = claim.data_pagamento_storage || '';
    const badgeInv = document.getElementById('badgeInvoiceModal');
    if (badgeInv) {
        badgeInv.innerHTML = claim.status_pagamento_storage === 'Pago'
            ? '<span class="badge badge-success">Storage Quitado</span>'
            : (claim.invoice_atrasado ? '<span class="badge badge-danger">Atrasado</span>' : '<span class="badge badge-info">Pendente</span>');
    }

    // Campos Gerais
    document.getElementById('edit_status').value = claim.status || 'Em Aberto';
    document.getElementById('edit_valor_diaria_storage').value = claim.valor_diaria_storage || 15.0;
    document.getElementById('edit_observacoes').value = claim.observacoes || '';

    const modal = document.getElementById('modalEditClaim');
    if (modal) modal.style.display = 'flex';
}

function fecharModalEditClaim() {
    const modal = document.getElementById('modalEditClaim');
    if (modal) modal.style.display = 'none';
    claimSelecionadoId = null;
}

function imprimirInvoiceStorageModal() {
    if (claimSelecionadoId) {
        window.open(`/claims/invoice/${claimSelecionadoId}`, '_blank');
    }
}

async function handleEditClaimSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSalvarEditClaim');
    if (btn) btn.disabled = true;

    const id = document.getElementById('edit_claim_id').value;
    const payload = {
        data_aprovacao: document.getElementById('edit_data_aprovacao').value || null,
        valor_indicacao: document.getElementById('edit_valor_indicacao').value,
        data_pagamento_indicacao: document.getElementById('edit_data_pagamento_indicacao').value || null,
        status_indicacao: document.getElementById('edit_data_pagamento_indicacao').value ? 'Pago' : 'Pendente',
        data_entrada_storage: document.getElementById('edit_data_entrada_storage').value || null,
        data_liberacao_storage: document.getElementById('edit_data_liberacao_storage').value || null,
        data_envio_invoice: document.getElementById('edit_data_envio_invoice').value || null,
        data_pagamento_storage: document.getElementById('edit_data_pagamento_storage').value || null,
        status_pagamento_storage: document.getElementById('edit_data_pagamento_storage').value ? 'Pago' : 'Pendente',
        status: document.getElementById('edit_status').value,
        valor_diaria_storage: document.getElementById('edit_valor_diaria_storage').value,
        observacoes: document.getElementById('edit_observacoes').value.trim()
    };

    try {
        const res = await fetch(`/api/claims/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) {
            alert(data.error || 'Erro ao atualizar claim');
            return;
        }

        fecharModalEditClaim();
        await carregarClaims();
        alert('Processo de Claim atualizado com sucesso!');
    } catch (err) {
        console.error('Erro:', err);
        alert('Erro ao se conectar com o servidor.');
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function confirmarExclusaoClaimModal() {
    if (!claimSelecionadoId) return;
    if (!confirm('Tem certeza de que deseja excluir permanentemente este registro de claim?')) return;

    try {
        const res = await fetch(`/api/claims/${claimSelecionadoId}`, {
            method: 'DELETE'
        });

        const data = await res.json();
        if (!res.ok) {
            alert(data.error || 'Erro ao excluir claim');
            return;
        }

        fecharModalEditClaim();
        await carregarClaims();
        alert('Claim excluído com sucesso.');
    } catch (err) {
        console.error('Erro:', err);
        alert('Erro ao se conectar com o servidor.');
    }
}
