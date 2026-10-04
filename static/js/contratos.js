let paginaAtual = 1;
let termoBusca = '';
let sortCol = 'id';
let sortOrder = 'desc';
let filtroDia = '';
let filtroDataInicio = '';
let filtroDataFim = '';
let limitPorPagina = 20;

function safeEscape(str) {
    if (typeof escapeHtml === 'function') return escapeHtml(str);
    if (str === null || str === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
}

function formatWhatsAppUrl(phone, customerName, plate) {
    if (!phone) return null;
    let clean = String(phone).replace(/[^0-9]/g, '');
    if (!clean) return null;
    if (clean.startsWith('0')) {
        clean = '44' + clean.slice(1);
    } else if (clean.length === 10 && clean.startsWith('7')) {
        clean = '44' + clean;
    }
    const bikeRef = (plate && plate !== '-') ? `regarding vehicle ${plate}` : 'regarding your vehicle';
    const msg = `Hello ${customerName || ''}, this is FF Motors ${bikeRef}: `;
    return `https://wa.me/${clean}?text=${encodeURIComponent(msg.trim())}`;
}

function atualizarKpiCards(kpis) {
    if (!kpis) return;
    const elRentals = document.getElementById('kpiVal_rentals');
    const elSales = document.getElementById('kpiVal_sales');
    const elPending = document.getElementById('kpiVal_pending_release');
    const elHolds = document.getElementById('kpiVal_deposit_holds');
    const elV5c = document.getElementById('kpiVal_pending_v5c');

    if (elRentals) elRentals.textContent = kpis.rentals !== undefined ? kpis.rentals : '-';
    if (elSales) elSales.textContent = kpis.sales !== undefined ? kpis.sales : '-';
    if (elPending) elPending.textContent = kpis.pending_release !== undefined ? kpis.pending_release : '-';
    if (elHolds) elHolds.textContent = kpis.deposit_holds !== undefined ? kpis.deposit_holds : '-';
    if (elV5c) elV5c.textContent = kpis.pending_v5c !== undefined ? kpis.pending_v5c : '-';

    sincronizarKpiCardAtivo();
}

function sincronizarKpiCardAtivo() {
    const filterStatus = document.getElementById('filterStatus')?.value || '';
    const filterTipo = document.getElementById('filterTipo')?.value || '';

    document.querySelectorAll('.kpi-card').forEach(card => {
        const cTipo = card.dataset.filterTipo || '';
        const cStatus = card.dataset.filterStatus || '';

        let isActive = false;
        if (cStatus === 'pending_release' && filterStatus === 'pending_release') {
            isActive = true;
        } else if (cStatus === 'pending_v5c' && filterStatus === 'pending_v5c') {
            isActive = true;
        } else if (cStatus === 'Deposit_Hold' && filterStatus === 'Deposit_Hold') {
            isActive = true;
        } else if (cTipo && cStatus && filterTipo === cTipo && filterStatus === cStatus) {
            isActive = true;
        }

        if (isActive) {
            card.classList.add('active');
        } else {
            card.classList.remove('active');
        }
    });
}

async function carregarContratos() {
    const tbody = document.querySelector('#contratosTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    
    try {
        const filterStatus = document.getElementById('filterStatus');
        const filterTipo = document.getElementById('filterTipo');
        const filterDiaElem = document.getElementById('filterDia');
        const filterDataIniElem = document.getElementById('filterDataInicio');
        const filterDataFimElem = document.getElementById('filterDataFim');
        const filterLimitElem = document.getElementById('filterLimit');

        const statusVal = filterStatus ? filterStatus.value : 'open';
        const tipoVal = filterTipo ? filterTipo.value : '';
        const diaVal = filterDiaElem ? filterDiaElem.value : '';
        const dataIniVal = filterDataIniElem ? filterDataIniElem.value : '';
        const dataFimVal = filterDataFimElem ? filterDataFimElem.value : '';
        limitPorPagina = filterLimitElem ? parseInt(filterLimitElem.value, 10) || 20 : 20;
        
        let url = `/api/contratos?page=${paginaAtual}&limit=${limitPorPagina}&search=${encodeURIComponent(termoBusca)}&sort_by=${encodeURIComponent(sortCol)}&sort_order=${encodeURIComponent(sortOrder)}`;
        
        if (statusVal === 'open') {
            url += '&nao_finalizados=true';
        } else if (statusVal !== 'all') {
            url += `&status=${encodeURIComponent(statusVal)}`;
        }
        if (tipoVal) {
            url += `&tipo=${encodeURIComponent(tipoVal)}`;
        }
        if (diaVal !== '') {
            url += `&dia_pagamento=${encodeURIComponent(diaVal)}`;
        }
        if (dataIniVal) {
            url += `&data_inicio=${encodeURIComponent(dataIniVal)}`;
        }
        if (dataFimVal) {
            url += `&data_fim=${encodeURIComponent(dataFimVal)}`;
        }

        const res = await fetch(url);
        if (res.status === 401) {
            window.location.href = '/login?msg=session_expired';
            return;
        }

        const data = await res.json();
        const contratos = data.itens || [];

        // Atualizar KPI strip
        if (data.kpis) {
            atualizarKpiCards(data.kpis);
        } else {
            sincronizarKpiCardAtivo();
        }
        
        const headerCols = document.querySelectorAll('#contratosTable thead th');
        const totalCols = headerCols.length > 0 ? headerCols.length : 9;

        if (contratos.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${totalCols}" style="text-align:center; padding: 2.5rem; color: var(--text-secondary);">No contracts found matching your filters.</td></tr>`;
            if (paginationInfo) paginationInfo.textContent = '';
            const btnPrev = document.getElementById('btnPrevPage');
            const btnNext = document.getElementById('btnNextPage');
            if (btnPrev) btnPrev.disabled = true;
            if (btnNext) btnNext.disabled = true;
            return;
        }
        
        const diasSemana = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        const gbp = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });
        
        tbody.innerHTML = '';
        contratos.forEach(c => {
            const tr = document.createElement('tr');
            const dataRetirada = c.data_retirada ? new Date(c.data_retirada).toLocaleDateString('en-GB') : '-';
            
            // Tipo de Contrato Badge
            const tipo = (c.tipo_contrato || 'Rent').toLowerCase();
            let tipoBadge = '';
            let dueTerms = '-';
            let amountText = '-';

            if (tipo === 'purchase') {
                tipoBadge = '<span class="badge" style="background: rgba(6, 182, 212, 0.15); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.35); font-weight: 600;">🤝 Purchase</span>';
                dueTerms = `<span style="color: var(--text-secondary); font-size: 0.85rem;">${safeEscape(c.metodo_pagamento_compra || 'Paid / Credit')}</span>`;
                const total = c.valor_compra_veiculo !== null && c.valor_compra_veiculo !== undefined ? c.valor_compra_veiculo : 0;
                amountText = `<span style="font-weight: 700; color: #22d3ee;">${gbp.format(total)}</span>`;
            } else if (tipo === 'sale_full') {
                tipoBadge = '<span class="badge" style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); font-weight: 600;">Sale: Full</span>';
                dueTerms = '<span style="color: var(--text-secondary); font-size: 0.85rem;">At Signing</span>';
                const total = c.valor_total_venda !== null && c.valor_total_venda !== undefined ? c.valor_total_venda : 0;
                const pendente = c.total_pendente !== undefined ? c.total_pendente : 0;
                const pendenteBadge = pendente > 0 
                    ? `<span style="font-size:0.75rem; color: var(--text-secondary);" title="Remaining balance on this contract">Balance: ${gbp.format(pendente)}</span>`
                    : `<span style="font-size:0.75rem; color:#4ade80; font-weight:600;">✓ Paid in Full</span>`;
                amountText = `<div style="display:flex; flex-direction:column; gap:2px;"><span style="font-weight: 700; color: #4ade80;">${gbp.format(total)}</span>${pendenteBadge}</div>`;
            } else if (tipo === 'sale_installment') {
                tipoBadge = '<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); font-weight: 600;">Sale: Inst.</span>';
                dueTerms = `<span style="color: var(--text-secondary); font-size: 0.85rem;">Dep: £${parseFloat(c.valor_entrada || 0).toFixed(2)}</span>`;
                const total = c.valor_total_venda !== null && c.valor_total_venda !== undefined ? c.valor_total_venda : 0;
                const pendente = c.total_pendente !== undefined ? c.total_pendente : (c.saldo_devedor || 0);
                const pendenteBadge = pendente > 0 
                    ? `<span style="font-size:0.75rem; color: var(--text-secondary);" title="Remaining balance on this contract">Balance: ${gbp.format(pendente)}</span>`
                    : `<span style="font-size:0.75rem; color:#4ade80; font-weight:600;" title="All installments fully settled">✓ Fully Paid</span>`;
                amountText = `<div style="display:flex; flex-direction:column; gap:2px;"><span style="font-weight: 700; color: #fbbf24;">${gbp.format(total)}</span>${pendenteBadge}</div>`;
            } else {
                tipoBadge = '<span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); font-weight: 600;">Rental</span>';
                dueTerms = c.dia_pagamento_semanal !== undefined && c.dia_pagamento_semanal !== null ? `<span style="font-weight:600; color: #93c5fd;">${diasSemana[c.dia_pagamento_semanal]}</span>` : '-';
                const rentVal = c.valor_aluguel_semanal ? `${gbp.format(c.valor_aluguel_semanal)}/wk` : '-';
                const pendente = c.total_pendente !== undefined ? c.total_pendente : 0;
                let pendenteBadge = '';
                if (pendente > 0) {
                    pendenteBadge = `<span style="font-size:0.72rem; color: var(--text-secondary);" title="Remaining balance on this contract">Balance: ${gbp.format(pendente)}</span>`;
                } else if (c.status === 'Active' || c.status === 'Ativo') {
                    pendenteBadge = `<span style="font-size:0.72rem; color:#4ade80; font-weight:500;">✓ Up to date</span>`;
                }
                amountText = `<div style="display:flex; flex-direction:column; gap:2px;"><span style="font-weight:700; color:#f8fafc;">${rentVal}</span>${pendenteBadge}</div>`;
            }
            
            // Status Badge
            let statusBadge = '';
            if (c.status === 'Active' || c.status === 'Ativo') {
                statusBadge = '<span class="badge badge-success">Active</span>';
            } else if (c.status === 'Deposit_Hold' || c.status === 'Quarentena_Deposito') {
                statusBadge = '<span class="badge badge-warning">Deposit Hold</span>';
            } else if (c.status === 'Completed' || c.status === 'Finalizado') {
                statusBadge = '<span class="badge" style="opacity: 0.8;">Completed</span>';
            } else if (c.status === 'Cancelled' || c.status === 'Cancelado') {
                statusBadge = '<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); font-weight: 700;">Cancelled</span>';
            } else {
                statusBadge = `<span class="badge">${safeEscape(c.status)}</span>`;
            }

            // Compliance & Signature Reminders
            let pendingWarningBadge = '';
            if (c.pendente_liberacao) {
                let tags = [];
                if (!c.tem_vistoria_checkout) tags.push('Insp');
                if (!c.tem_seguro) tags.push('Ins');
                const tagStr = tags.length > 0 ? tags.join(' + ') : 'Pending';
                pendingWarningBadge = `<div style="margin-top: 4px;"><span class="badge" style="background: rgba(245, 158, 11, 0.18); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.45); font-size: 0.7rem; font-weight: 700; white-space: nowrap;" title="Motorbike cannot be released until check-out photos and insurance certificate are registered">⚠️ Needs ${safeEscape(tagStr)}</span></div>`;
            } else if (c.needs_v5c) {
                if (c.tem_transfer_proof || (c.transfer_proof_count > 0)) {
                    pendingWarningBadge = `<div style="margin-top: 4px;"><span class="badge" style="background: rgba(245, 158, 11, 0.18); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.45); font-size: 0.7rem; font-weight: 700; white-space: nowrap;" title="Purchase agreement has provisional transfer slip on file, awaiting official postal V5C logbook">⏳ Needs V5C (Slip OK)</span></div>`;
                } else {
                    pendingWarningBadge = `<div style="margin-top: 4px;"><span class="badge" style="background: rgba(6, 182, 212, 0.18); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.45); font-size: 0.7rem; font-weight: 700; white-space: nowrap;" title="Purchase agreement pending vehicle Logbook (V5C) attachment">📑 Needs V5C</span></div>`;
                }
            }

            // Signature Status Pill
            const signPill = c.assinado ?
                `<div style="margin-top: 4px;"><span class="badge" style="background: rgba(34, 197, 94, 0.12); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.25); font-size: 0.7rem; font-weight: 600; padding: 2px 6px;" title="Agreement digitally signed by customer">✓ Signed</span></div>` :
                `<div style="margin-top: 4px;"><span class="badge" style="background: rgba(148, 163, 184, 0.12); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.2); font-size: 0.7rem; padding: 2px 6px;" title="Agreement awaiting customer signature">⏳ Unsigned</span></div>`;
            
            const nomeCliente = safeEscape(c.cliente_nome || '-');
            const placa = safeEscape(c.placa || '-');
            const modeloMoto = safeEscape(c.moto_modelo || '');
            const corMoto = safeEscape(c.moto_cor || '');
            const telCliente = (c.cliente_telefone || '').trim();
            const waUrl = formatWhatsAppUrl(telCliente, c.cliente_nome, c.placa);

            // WhatsApp shortcut link (opens in new tab)
            const waButton = waUrl ? 
                `<a href="${waUrl}" target="_blank" rel="noopener noreferrer" class="btn-wa-link" title="Message ${nomeCliente} on WhatsApp (${safeEscape(telCliente)})">💬</a>` : '';

            // Customer Column (Name + WhatsApp + Phone)
            const customerCell = `
                <div style="display: flex; flex-direction: column; gap: 2px;">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="font-weight: 600; white-space: nowrap;" title="${nomeCliente}">${nomeCliente}</span>
                        ${waButton}
                    </div>
                    ${telCliente ? `<div style="font-size: 0.75rem; color: var(--text-secondary); font-family: monospace;">${safeEscape(telCliente)}</div>` : ''}
                </div>
            `;

            // Vehicle Column (Reg Plate + Model + Colour)
            const vehicleDesc = [modeloMoto, corMoto].filter(Boolean).join(' • ');
            const vehicleCell = `
                <div style="display: flex; flex-direction: column; gap: 3px;">
                    <div><span class="badge-plate">${placa}</span></div>
                    ${vehicleDesc ? `<div style="font-size: 0.75rem; color: var(--text-secondary); max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${vehicleDesc}">${vehicleDesc}</div>` : ''}
                </div>
            `;

            // Actions Column (View + Print/PDF Agreement)
            const actionsCell = `
                <div style="display: flex; align-items: center; gap: 5px;">
                    <a href="/contratos/${c.id}" class="btn-primary" style="padding: 6px 10px; font-size: 0.8rem; font-weight: 500; border-radius: 6px; white-space: nowrap; text-decoration: none;">View</a>
                    <a href="/contratos/${c.id}/imprimir" class="action-icon-btn" title="View / Print Signed Agreement (PDF)">🖨️</a>
                </div>
            `;

            const contractNoteIcon = c.notas_internas 
                ? `<span style="margin-left: 5px; cursor: help; font-size: 0.85rem;" title="Internal Notes: ${safeEscape(c.notas_internas)}">📝</span>` 
                : '';

            tr.innerHTML = `
                <td style="font-weight: 600; color: var(--text-secondary); white-space: nowrap;">#${c.id}${contractNoteIcon}</td>
                <td>${tipoBadge}</td>
                <td>${customerCell}</td>
                <td>${vehicleCell}</td>
                <td style="white-space: nowrap;">${dataRetirada}</td>
                <td>${dueTerms}</td>
                <td>${amountText}</td>
                <td>${statusBadge}${pendingWarningBadge}${signPill}</td>
                <td>${actionsCell}</td>
            `;
            tbody.appendChild(tr);
        });

        // Update pagination UI
        if (paginationInfo) {
            paginationInfo.textContent = `Page ${data.pagina_atual} of ${data.paginas} (${data.total} records)`;
        }
        const btnPrev = document.getElementById('btnPrevPage');
        const btnNext = document.getElementById('btnNextPage');
        if (btnPrev) btnPrev.disabled = data.pagina_atual <= 1;
        if (btnNext) btnNext.disabled = data.pagina_atual >= data.paginas;

        if (typeof setTableSortIndicator === 'function') {
            setTableSortIndicator('contratosTable', sortCol, sortOrder);
        }
        
    } catch(e) {
        console.error('Error loading contracts:', e);
        const colSpan = document.querySelectorAll('#contratosTable thead th').length || 9;
        tbody.innerHTML = `<tr><td colspan="${colSpan}" style="text-align:center; padding: 2rem; color:var(--error);">Error loading contracts. Please refresh the page.</td></tr>`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Check URL parameters for status/tipo filters (e.g. from Dashboard or Fleet links)
    const urlParams = new URLSearchParams(window.location.search);
    const paramStatus = urlParams.get('status');
    const paramTipo = urlParams.get('tipo');
    const filterStatus = document.getElementById('filterStatus');
    const filterTipo = document.getElementById('filterTipo');
    const filterDia = document.getElementById('filterDia');
    const filterDataInicio = document.getElementById('filterDataInicio');
    const filterDataFim = document.getElementById('filterDataFim');
    const filterLimit = document.getElementById('filterLimit');
    const btnClearFilters = document.getElementById('btnClearFilters');
    
    if (paramStatus && filterStatus) {
        const ps = paramStatus.toLowerCase();
        if (ps === 'deposit_hold' || ps === 'quarentena') {
            filterStatus.value = 'Deposit_Hold';
        } else if (ps === 'pending_release' || ps === 'pre-delivery' || ps === 'pendente_liberacao') {
            filterStatus.value = 'pending_release';
        } else if (ps === 'pending_v5c' || ps === 'needs_v5c') {
            filterStatus.value = 'pending_v5c';
        } else if (ps === 'active') {
            filterStatus.value = 'Active';
        } else if (ps === 'completed') {
            filterStatus.value = 'Completed';
        } else if (ps === 'cancelled') {
            filterStatus.value = 'Cancelled';
        } else if (ps === 'all') {
            filterStatus.value = 'all';
        }
    }

    if (paramTipo && filterTipo) {
        filterTipo.value = paramTipo;
    }

    // Filter Change Listeners
    if (filterStatus) {
        filterStatus.addEventListener('change', () => {
            paginaAtual = 1;
            carregarContratos();
        });
    }

    if (filterTipo) {
        filterTipo.addEventListener('change', () => {
            paginaAtual = 1;
            carregarContratos();
        });
    }

    if (filterDia) {
        filterDia.addEventListener('change', () => {
            paginaAtual = 1;
            carregarContratos();
        });
    }

    if (filterDataInicio) {
        filterDataInicio.addEventListener('change', () => {
            paginaAtual = 1;
            carregarContratos();
        });
    }

    if (filterDataFim) {
        filterDataFim.addEventListener('change', () => {
            paginaAtual = 1;
            carregarContratos();
        });
    }

    if (filterLimit) {
        filterLimit.addEventListener('change', () => {
            paginaAtual = 1;
            carregarContratos();
        });
    }

    // Clear Filters Action
    if (btnClearFilters) {
        btnClearFilters.addEventListener('click', () => {
            const searchInput = document.getElementById('searchInput');
            if (searchInput) searchInput.value = '';
            termoBusca = '';
            if (filterTipo) filterTipo.value = '';
            if (filterStatus) filterStatus.value = 'open';
            if (filterDia) filterDia.value = '';
            if (filterDataInicio) filterDataInicio.value = '';
            if (filterDataFim) filterDataFim.value = '';
            paginaAtual = 1;
            carregarContratos();
        });
    }

    // Search Input with Debounce
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let debounceTimer;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                termoBusca = e.target.value.trim();
                paginaAtual = 1;
                carregarContratos();
            }, 300);
        });
    }

    // Interactive KPI Cards Clicks (1-click smart filtering)
    document.querySelectorAll('.kpi-card').forEach(card => {
        card.addEventListener('click', () => {
            const cTipo = card.dataset.filterTipo;
            const cStatus = card.dataset.filterStatus;
            const isAlreadyActive = card.classList.contains('active');

            if (isAlreadyActive) {
                // Toggle off back to default open contracts
                if (filterTipo) filterTipo.value = '';
                if (filterStatus) filterStatus.value = 'open';
            } else {
                if (filterTipo) filterTipo.value = cTipo || '';
                if (filterStatus) filterStatus.value = cStatus || 'all';
            }

            paginaAtual = 1;
            carregarContratos();
        });
    });

    // Pagination
    const btnPrev = document.getElementById('btnPrevPage');
    const btnNext = document.getElementById('btnNextPage');
    if (btnPrev) {
        btnPrev.addEventListener('click', () => {
            if (paginaAtual > 1) {
                paginaAtual--;
                carregarContratos();
            }
        });
    }
    if (btnNext) {
        btnNext.addEventListener('click', () => {
            paginaAtual++;
            carregarContratos();
        });
    }

    // Interactive Column Sorting
    const tableHeaders = document.querySelectorAll('#contratosTable th[data-sort-field]');
    tableHeaders.forEach(th => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', () => {
            const field = th.getAttribute('data-sort-field');
            if (sortCol === field) {
                sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                sortCol = field;
                sortOrder = (field === 'id' || field === 'data_retirada') ? 'desc' : 'asc';
            }
            paginaAtual = 1;
            carregarContratos();
        });
    });

    carregarContratos();
});
