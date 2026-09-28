let paginaAtual = 1;
let limitePorPagina = 20;
let termoBusca = '';
let statusFiltro = 'pendentes';
let tipoFiltro = '';
let metodoFiltro = '';
let campoData = 'vencimento';
let dataInicio = '';
let dataFim = '';
let sortCol = 'data_vencimento';
let sortOrder = 'asc';
let transacoesCache = [];
let filtroExatoContrato = null;
let filtroExatoClienteId = null;
let filtroExatoClienteNome = null;
let filtroExatoPlaca = null;

const formatoMoeda = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });

function atualizarPillFiltroExato() {
    const container = document.getElementById('activeFilterPillContainer');
    const textEl = document.getElementById('activeFilterPillText');
    if (!container || !textEl) return;

    if (filtroExatoContrato) {
        textEl.textContent = `📋 Contract #${filtroExatoContrato}`;
        container.style.display = 'inline-flex';
    } else if (filtroExatoClienteId && filtroExatoClienteNome) {
        textEl.textContent = `👤 Customer: ${filtroExatoClienteNome}`;
        container.style.display = 'inline-flex';
    } else if (filtroExatoPlaca) {
        textEl.textContent = `🛵 Bike: ${filtroExatoPlaca}`;
        container.style.display = 'inline-flex';
    } else {
        container.style.display = 'none';
    }
}

function formatarLembreteEstetico(isoStr, staff) {
    if (!isoStr) return '';
    try {
        const d = new Date(isoStr);
        const now = new Date();
        const diffMs = now - d;
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

        let relText = '';
        if (diffMins < 2) {
            relText = 'Just now';
        } else if (diffMins < 60) {
            relText = `${diffMins}m ago`;
        } else if (diffHours < 24 && d.getDate() === now.getDate()) {
            relText = `Today ${d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}`;
        } else {
            relText = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
        }

        const staffStr = staff ? ` by ${escapeHtml(staff)}` : '';
        const fullDateStr = d.toLocaleDateString('en-GB') + ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
        const title = `WhatsApp reminder recorded${staffStr} on ${fullDateStr}`;

        return `<span class="badge-reminded-pill" title="${title}" style="display:inline-flex; align-items:center; gap:2px; font-size:0.65rem; font-weight:600; color:#34d399; background:rgba(16, 185, 129, 0.12); border:1px solid rgba(16, 185, 129, 0.28); border-radius:10px; padding:0 5px; letter-spacing:0.2px; white-space:nowrap; line-height:1.2;">
            <span style="font-size:0.62rem;">✓</span>
            <span>${relText}</span>
        </span>`;
    } catch(e) {
        return '';
    }
}


// ==========================================
// 1. CARREGAR KPIS EM TEMPO REAL
// ==========================================
async function carregarKpis() {
    try {
        const res = await fetch('/api/financeiro/resumo');
        if (!res.ok) return;
        const data = await res.json();
        
        const elPendVal = document.getElementById('kpiPendingValor');
        const elPendQtd = document.getElementById('kpiPendingQtd');
        if (elPendVal) elPendVal.textContent = formatoMoeda.format(data.pendente?.total || 0);
        if (elPendQtd) elPendQtd.textContent = `${data.pendente?.qtd || 0} transactions pending`;

        const elOverVal = document.getElementById('kpiOverdueValor');
        const elOverQtd = document.getElementById('kpiOverdueQtd');
        if (elOverVal) elOverVal.textContent = formatoMoeda.format(data.overdue?.total || 0);
        if (elOverQtd) elOverQtd.textContent = `${data.overdue?.qtd || 0} charges overdue`;

        const elHojeVal = document.getElementById('kpiTodayValor');
        const elHojeQtd = document.getElementById('kpiTodayQtd');
        if (elHojeVal) elHojeVal.textContent = formatoMoeda.format(data.hoje?.total || 0);
        if (elHojeQtd) elHojeQtd.textContent = `${data.hoje?.qtd || 0} payments confirmed`;

        const elWeekVal = document.getElementById('kpiWeekValor');
        const elMonthSub = document.getElementById('kpiMonthSubtext');
        if (elWeekVal) elWeekVal.textContent = formatoMoeda.format(data.semana?.total || 0);
        if (elMonthSub) elMonthSub.textContent = `This Month: ${formatoMoeda.format(data.mes?.total || 0)}`;
    } catch (err) {
        console.warn('Failed to load financial KPIs:', err);
    }
}

// ==========================================
// 2. CARREGAR TABELA FINANCEIRA
// ==========================================
async function carregarFinanceiro() {
    const tbody = document.querySelector('#financeiroTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    const btnClear = document.getElementById('btnClearFilters');
    const tfoot = document.getElementById('financeiroTableFooter');

    // Show/hide Clear Filters button and update Active Filter pill
    atualizarPillFiltroExato();
    if (btnClear) {
        const hasFilters = termoBusca || filtroExatoContrato || filtroExatoClienteId || filtroExatoPlaca || statusFiltro !== 'pendentes' || tipoFiltro || metodoFiltro || dataInicio || dataFim || campoData !== 'vencimento' || limitePorPagina !== 20;
        btnClear.style.display = hasFilters ? 'block' : 'none';
    }

    try {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:2.5rem; color:var(--text-secondary);">Loading transactions...</td></tr>';
        if (tfoot) tfoot.style.display = 'none';

        let pendentesParam = statusFiltro === 'pendentes' ? 'true' : 'false';
        let statusParam = (statusFiltro !== 'pendentes') ? statusFiltro : '';

        const params = new URLSearchParams({
            page: paginaAtual,
            limit: limitePorPagina,
            search: termoBusca,
            status: statusParam,
            pendentes: pendentesParam,
            tipo: tipoFiltro,
            metodo: metodoFiltro,
            campo_data: campoData,
            data_inicio: dataInicio,
            data_fim: dataFim,
            sort_by: sortCol,
            sort_order: sortOrder
        });

        if (filtroExatoContrato) params.append('contrato_id', filtroExatoContrato);
        if (filtroExatoClienteId) params.append('cliente_id', filtroExatoClienteId);
        if (filtroExatoPlaca) params.append('placa', filtroExatoPlaca);

        const res = await fetch(`/api/financeiro?${params.toString()}`);
        const data = await res.json();
        const transacoes = data.itens || [];
        transacoesCache = transacoes;
        
        if (transacoes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:2.5rem; color:var(--text-secondary); font-size: 0.95rem;">No financial transactions found with the current filters.</td></tr>';
            if (paginationInfo) paginationInfo.textContent = '';
            const btnPrev = document.getElementById('btnPrevPage');
            const btnNext = document.getElementById('btnNextPage');
            if (btnPrev) btnPrev.disabled = true;
            if (btnNext) btnNext.disabled = true;
            if (tfoot) tfoot.style.display = 'none';
            return;
        }
        
        tbody.innerHTML = '';
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);

        let somaNaTela = 0;

        transacoes.forEach((t, index) => {
            somaNaTela += (t.valor || 0);
            const tr = document.createElement('tr');
            
            // Dates
            const dataVencObj = t.data_vencimento ? new Date(t.data_vencimento) : null;
            const vencZero = dataVencObj ? new Date(dataVencObj.getFullYear(), dataVencObj.getMonth(), dataVencObj.getDate()) : null;
            const vencimento = dataVencObj ? dataVencObj.toLocaleDateString('en-GB') : '-';
            
            const tStatusLower = (t.status || '').toLowerCase();
            const isPaid = tStatusLower === 'paid' || tStatusLower === 'pago';
            const isPending = tStatusLower === 'pending' || tStatusLower === 'pendente';
            const isVencido = isPending && vencZero && vencZero < hoje;

            const pagamento = t.data_pagamento ? new Date(t.data_pagamento).toLocaleDateString('en-GB') : '-';

            // Status Badges
            let statusBadge = '';
            if (isPaid) {
                statusBadge = '<span class="badge badge-success">PAID</span>';
            } else if (isVencido) {
                statusBadge = '<span class="badge badge-danger" title="Overdue!">OVERDUE</span>';
            } else if (isPending) {
                statusBadge = '<span class="badge badge-warning">PENDING</span>';
            } else {
                statusBadge = `<span class="badge">${escapeHtml(t.status)}</span>`;
            }

            // Type Badges (Compact)
            let tipoBadge = '';
            const tipoLower = (t.tipo || '').toLowerCase();
            if (tipoLower === 'rent' || tipoLower === 'aluguel') tipoBadge = '<span class="badge badge-info">Rent</span>';
            else if (tipoLower === 'deposit' || tipoLower === 'deposito') tipoBadge = '<span class="badge" style="background:rgba(168, 85, 247, 0.2); color:#c084fc;">Deposit</span>';
            else if (tipoLower === 'sale_full' || tipoLower === 'venda_vista') tipoBadge = '<span class="badge" style="background:rgba(16, 185, 129, 0.2); color:#34d399; border:1px solid rgba(16, 185, 129, 0.4);">Sale: Full</span>';
            else if (tipoLower === 'sale_deposit' || tipoLower === 'venda_entrada') tipoBadge = '<span class="badge" style="background:rgba(217, 119, 6, 0.2); color:#fbbf24; border:1px solid rgba(217, 119, 6, 0.4);">Sale: Down</span>';
            else if (tipoLower === 'sale_installment' || tipoLower === 'venda_parcela') tipoBadge = '<span class="badge" style="background:rgba(59, 130, 246, 0.2); color:#60a5fa; border:1px solid rgba(59, 130, 246, 0.4);">Sale: Inst.</span>';
            else if (tipoLower === 'fine' || tipoLower === 'multa') tipoBadge = '<span class="badge badge-danger">Fine/PCN</span>';
            else if (tipoLower === 'damage' || tipoLower === 'dano') tipoBadge = '<span class="badge badge-warning">Damage</span>';
            else if (tipoLower === 'admin_fee') tipoBadge = '<span class="badge" style="background:rgba(148, 163, 184, 0.2); color:#cbd5e1;">Admin</span>';
            else if (tipoLower === 'deposit_refund' || tipoLower === 'devolucao_deposito') tipoBadge = '<span class="badge badge-success">Refund</span>';
            else tipoBadge = `<span class="badge">${escapeHtml(t.tipo)}</span>`;

            // Partial Split badge indicator (Compact)
            const balanceBadgeHtml = t.id_transacao_origem ? `<span style="display:inline-block; font-size:0.65rem; color:#f59e0b; font-weight:700; background:rgba(245, 158, 11, 0.15); border:1px solid rgba(245, 158, 11, 0.35); border-radius:3px; padding:0 4px; margin-top:1px;">⚡ Bal #${t.id_transacao_origem}</span>` : '';
            
            // Formatted Amount
            const valorFmt = formatoMoeda.format(t.valor);
            
            // Payment Cell (Compact)
            let celulaPagamento = '<span style="color:var(--text-secondary); opacity:0.6;">-</span>';
            if (isPaid || t.data_pagamento) {
                const isDepositDeduction = t.forma_pagamento === 'Deposit';
                const isExchange = t.forma_pagamento && t.forma_pagamento.includes('Exchange');
                const formaLabel = isDepositDeduction ? 'Deposit' : (t.forma_pagamento || '');
                let colorStyle = 'color:var(--text-secondary);';
                if (isDepositDeduction) colorStyle = 'color:#60a5fa; font-weight:600;';
                else if (isExchange) colorStyle = 'color:#34d399; font-weight:600;';
                const staffHtml = t.registrado_por_nome ? `<span style="display:block; font-size:0.65rem; color:#a855f7; line-height:1; margin-top:1px;" title="Recorded by ${escapeHtml(t.registrado_por_nome)}">👤 ${escapeHtml(t.registrado_por_nome)}</span>` : '';
                const notaHtml = t.nota ? `<span style="display:block; font-size:0.68rem; color:#cbd5e1; background:rgba(255,255,255,0.06); border-left:2px solid var(--accent, #ff6b00); padding:1px 4px; border-radius:2px; margin-top:2px; max-width:120px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(t.nota)}">📝 ${escapeHtml(t.nota)}</span>` : '';
                celulaPagamento = `<div style="line-height:1.15;">
                    <span style="font-weight:600; font-size:0.8rem;">${pagamento}</span>
                    <small style="display:block; ${colorStyle} font-size:0.7rem; line-height:1;">${escapeHtml(formaLabel)}</small>
                    ${staffHtml}
                    ${notaHtml}
                </div>`;
            }

            // Due Date Cell with Overdue Days Counter (Compact)
            let celulaVencimento = `<span style="font-size:0.8rem;">${vencimento}</span>`;
            if (isVencido) {
                const diffTime = Math.max(0, hoje.getTime() - vencZero.getTime());
                const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
                let lateText = `${diffDays}d late`;
                if (diffDays === 0 || diffDays === 1) {
                    lateText = '1d late';
                } else if (diffDays >= 14) {
                    const weeks = Math.floor(diffDays / 7);
                    lateText = `${weeks}w (${diffDays}d)`;
                }
                celulaVencimento = `
                    <div style="line-height: 1.15;">
                        <span style="color:#f87171; font-weight:600; font-size:0.8rem;" title="Charge overdue!">${vencimento}</span>
                        <span style="font-size: 0.65rem; color: #fca5a5; font-weight: 700; background: rgba(239, 68, 68, 0.12); padding: 0 4px; border-radius: 3px; border: 1px solid rgba(239, 68, 68, 0.25); display: inline-block; white-space: nowrap; margin-top: 1px;">${lateText}</span>
                    </div>
                `;
            }

            // Customer Cell: High Debt Risk Badge (>= 2 overdue debts), Exact Click-to-filter, Sleek Last Reminded Chip
            const debtRiskBadge = (t.cliente_dividas_pendentes && t.cliente_dividas_pendentes >= 2) ? 
                `<span class="badge" style="background: rgba(239, 68, 68, 0.2); border: 1px solid rgba(239, 68, 68, 0.4); color: #f87171; font-weight: 700; font-size: 0.65rem; padding: 1px 4px; border-radius: 3px; display: inline-flex; align-items: center; gap: 2px;" title="High Debt Risk: Customer has ${t.cliente_dividas_pendentes} overdue charges (vencidas)">🔴 ${t.cliente_dividas_pendentes} Late</span>` : '';

            let celulaCliente = `<div style="max-width: 170px;">
                <div style="display: flex; align-items: center; gap: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.2;">
                    <span class="btn-filter-cliente" data-cliente-id="${t.cliente_id || ''}" data-cliente-nome="${escapeHtml(t.cliente || '')}" title="Filter by Customer: ${escapeHtml(t.cliente || '')}" style="color: var(--text-primary); font-weight: 600; font-size: 0.82rem; cursor: pointer; text-decoration: underline dotted var(--text-secondary); overflow: hidden; text-overflow: ellipsis;">${escapeHtml(t.cliente || '-')}</span>
                    ${debtRiskBadge}
                </div>`;
            
            if (t.cliente_telefone) {
                const waTel = (typeof formatWhatsAppNumber === 'function')
                    ? formatWhatsAppNumber(t.cliente_telefone)
                    : (() => {
                        let w = t.cliente_telefone.replace(/\D/g, '');
                        if (w.startsWith('0')) w = '44' + w.substring(1);
                        return w;
                    })();
                
                // WhatsApp friendly message
                const waMsg = encodeURIComponent(`Hi ${t.cliente || 'there'}, this is FF Motors Birmingham. Just a friendly reminder regarding your pending ${t.descricao || 'rental'} payment of ${valorFmt} (Contract #${t.id_contrato}, Bike: ${t.placa || 'fleet'}). If you have already made this payment, please disregard this note. Thank you!`);
                const waLink = waTel ? `https://wa.me/${waTel}?text=${waMsg}` : '#';

                celulaCliente += `
                    <div style="display: flex; align-items: center; gap: 4px; margin-top: 1px; flex-wrap: nowrap; line-height: 1; font-size: 0.7rem;">
                        <span style="color: var(--text-secondary); white-space: nowrap;">${escapeHtml(t.cliente_telefone)}</span>
                        ${(isPending || isVencido) ? `<a href="${waLink}" target="_blank" rel="noopener" class="btn-wa-reminder" data-id="${t.id}" style="text-decoration:none; font-size:0.68rem; background:rgba(37,211,102,0.15); border:1px solid rgba(37,211,102,0.35); color:#25d366; border-radius:3px; padding:0 3px; display:inline-flex; align-items:center; cursor:pointer;" title="Send WhatsApp payment reminder">💬</a>` : ''}
                        <span id="reminder-container-${t.id}">${formatarLembreteEstetico(t.ultimo_lembrete, t.ultimo_lembrete_por)}</span>
                    </div>
                `;
            }
            celulaCliente += '</div>';

            // Action Buttons (Compact)
            let actBtn = '-';
            if (isPending) {
                actBtn = `<button class="btn-action btn-abrir-pagar" data-index="${index}" style="background:var(--success); border-radius:6px; padding:3px 8px; font-weight:600; font-size:0.74rem; white-space:nowrap;">
                    Mark Paid
                </button>`;
            } else if (isPaid) {
                actBtn = `
                    <div style="display:flex; gap:4px; justify-content:flex-end; align-items:center;">
                        <button class="btn-action btn-abrir-recibo" data-index="${index}" style="background:rgba(255,255,255,0.06); border:1px solid var(--border-color); color:var(--text-primary); padding:3px 6px; border-radius:5px; font-size:0.72rem; cursor:pointer;" title="View Receipt">
                            🧾 Rec.
                        </button>
                        <button class="btn-action btn-reverter-fin" data-id="${t.id}" data-tipo="${t.tipo}" data-valor="${t.valor}" style="background:rgba(239, 68, 68, 0.12); border:1px solid rgba(239, 68, 68, 0.3); color:#f87171; padding:3px 6px; border-radius:5px; font-size:0.72rem; cursor:pointer;" title="Cancel payment and return to Pending">
                            ↩ Rev.
                        </button>
                    </div>
                `;
            }
            
            tr.innerHTML = `
                <td style="font-weight:700; color:var(--text-secondary); font-size:0.78rem;">#${t.id}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 4px;">
                        <a href="/contratos/${t.id_contrato}" class="link-contrato" title="Contract #${t.id_contrato}" style="white-space: nowrap;">
                            #${t.id_contrato}
                        </a>
                        <button type="button" class="btn-filter-contrato" data-contrato-id="${t.id_contrato}" title="Filter by Contract #${t.id_contrato}" style="background: rgba(255,255,255,0.06); border: 1px solid var(--border-color); color: var(--text-secondary); border-radius: 3px; padding: 1px 4px; font-size: 0.68rem; cursor: pointer; line-height: 1;">🔍</button>
                    </div>
                </td>
                <td>${celulaCliente}</td>
                <td class="nowrap">${t.placa ? `<span class="badge-plate btn-filter-placa" data-placa="${escapeHtml(t.placa)}" style="cursor:pointer;" title="Filter by plate ${escapeHtml(t.placa)}">${escapeHtml(t.placa)}</span>` : '<span class="badge-plate">-</span>'}</td>
                <td>
                    ${tipoBadge}
                    ${balanceBadgeHtml}
                </td>
                <td class="nowrap" style="font-weight:700; font-size:0.88rem; color:var(--text-primary);">${valorFmt}</td>
                <td class="nowrap">${celulaVencimento}</td>
                <td class="nowrap">${celulaPagamento}</td>
                <td class="nowrap">${statusBadge}</td>
                <td style="text-align: right; white-space: nowrap;">${actBtn}</td>
            `;
            tbody.appendChild(tr);
        });

        // Update Dynamic Table Footer
        if (tfoot) {
            tfoot.style.display = 'table-footer-group';
            const elCount = document.getElementById('footerCountText');
            const elTotal = document.getElementById('footerTotalAmount');
            if (elCount) elCount.textContent = `Showing ${transacoes.length} of ${data.total} records`;
            if (elTotal) elTotal.textContent = formatoMoeda.format(somaNaTela);
        }

        // Pagination UI
        if (paginationInfo) {
            paginationInfo.textContent = `Page ${data.pagina_atual} of ${data.paginas || 1} (${data.total} total records)`;
        }
        const btnPrev = document.getElementById('btnPrevPage');
        const btnNext = document.getElementById('btnNextPage');
        if (btnPrev) btnPrev.disabled = data.pagina_atual <= 1;
        if (btnNext) btnNext.disabled = data.pagina_atual >= (data.paginas || 1);
        
        // Listeners for Mark Paid
        document.querySelectorAll('.btn-abrir-pagar').forEach(btn => {
            btn.addEventListener('click', () => {
                const idx = parseInt(btn.getAttribute('data-index'), 10);
                abrirModalPagamento(transacoesCache[idx]);
            });
        });

        // Listeners for Receipt
        document.querySelectorAll('.btn-abrir-recibo').forEach(btn => {
            btn.addEventListener('click', () => {
                const idx = parseInt(btn.getAttribute('data-index'), 10);
                abrirModalRecibo(transacoesCache[idx]);
            });
        });

        // Listeners for Revert Payment
        document.querySelectorAll('.btn-reverter-fin').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const b = e.target.closest('button');
                const id = b.getAttribute('data-id');
                const tipo = b.getAttribute('data-tipo');
                const valor = parseFloat(b.getAttribute('data-valor')) || 0;

                const confirmar = confirm(`Are you sure you want to CANCEL this completed payment?\n\n• Transaction: #${id} (${tipo})\n• Amount: ${formatoMoeda.format(valor)}\n\nThis will reset the transaction back to PENDING and record this cancellation in the audit trail.`);
                if (!confirmar) return;

                b.disabled = true;
                b.textContent = 'Reverting...';
                try {
                    const res = await fetch(`/api/financeiro/${id}/reverter`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const resJson = await res.json();
                    if (!res.ok) {
                        alert(resJson.error || resJson.erro || 'Failed to revert payment.');
                        b.disabled = false;
                        b.textContent = '↩ Revert';
                        return;
                    }
                    carregarFinanceiro();
                    carregarKpis();
                } catch (err) {
                    console.error('Error reverting payment:', err);
                    alert('Connection error while cancelling payment.');
                    b.disabled = false;
                    b.textContent = '↩ Revert';
                }
            });
        });

        // Listeners for Exact Inline Filter Buttons
        document.querySelectorAll('.btn-filter-contrato').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const cid = parseInt(btn.getAttribute('data-contrato-id'), 10);
                if (cid) {
                    filtroExatoContrato = cid;
                    filtroExatoClienteId = null;
                    filtroExatoClienteNome = null;
                    filtroExatoPlaca = null;
                    termoBusca = '';
                    const searchInput = document.getElementById('searchInput');
                    if (searchInput) searchInput.value = '';
                    paginaAtual = 1;
                    carregarFinanceiro();
                }
            });
        });

        document.querySelectorAll('.btn-filter-cliente').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const cid = btn.getAttribute('data-cliente-id');
                const cnome = btn.getAttribute('data-cliente-nome');
                if (cid) {
                    filtroExatoClienteId = parseInt(cid, 10);
                    filtroExatoClienteNome = cnome || `ID ${cid}`;
                    filtroExatoContrato = null;
                    filtroExatoPlaca = null;
                    termoBusca = '';
                    const searchInput = document.getElementById('searchInput');
                    if (searchInput) searchInput.value = '';
                    paginaAtual = 1;
                    carregarFinanceiro();
                }
            });
        });

        document.querySelectorAll('.btn-filter-placa').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const placa = btn.getAttribute('data-placa');
                if (placa) {
                    filtroExatoPlaca = placa;
                    filtroExatoContrato = null;
                    filtroExatoClienteId = null;
                    filtroExatoClienteNome = null;
                    termoBusca = '';
                    const searchInput = document.getElementById('searchInput');
                    if (searchInput) searchInput.value = '';
                    paginaAtual = 1;
                    carregarFinanceiro();
                }
            });
        });

        // Listeners for WhatsApp Reminders (Records Timestamp asynchronously)
        document.querySelectorAll('.btn-wa-reminder').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.getAttribute('data-id');
                if (!id) return;
                try {
                    const res = await fetch(`/api/financeiro/${id}/lembrete`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    if (res.ok) {
                        const container = document.getElementById(`reminder-container-${id}`);
                        if (container) {
                            container.innerHTML = formatarLembreteEstetico(new Date().toISOString(), 'You');
                        }
                    }
                } catch(err) {
                    console.error('Error recording reminder:', err);
                }
            });
        });

        if (typeof setTableSortIndicator === 'function') {
            setTableSortIndicator('financeiroTable', sortCol, sortOrder);
        }
        
    } catch(e) {
        console.error("Error loading financial transactions:", e);
        tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:2rem; color:var(--error);">Failed to load transactions from server.</td></tr>';
    }
}

// ==========================================
// 3. PAGAMENTO E RECIBO MODAIS (PRESERVADOS)
// ==========================================
let splitPaymentMgr = null;

function abrirModalPagamento(t) {
    if (!t) return;
    const modal = document.getElementById('pagamentoModal');
    if (!modal) return;

    if (!splitPaymentMgr) {
        splitPaymentMgr = createSplitPaymentManager({ formatoMoeda });
    }

    document.getElementById('pag_cobranca_id').value = t.id;
    document.getElementById('pag_desc_id').textContent = `#${t.id} (Contract #${t.id_contrato})`;
    document.getElementById('pag_desc_tipo').textContent = t.descricao || formatarDescricaoTransacao(t.tipo);
    document.getElementById('pag_desc_valor').textContent = formatoMoeda.format(t.valor);
    
    splitPaymentMgr.open(t.valor, 'Cash');
    modal.classList.add('active');
}

function fecharModalPagamento() {
    const modal = document.getElementById('pagamentoModal');
    if (modal) modal.classList.remove('active');
}

function formatarDescricaoTransacao(tipo) {
    if (!tipo) return '-';
    const t = tipo.toLowerCase();
    if (t === 'sale_full' || t === 'venda_vista') return 'Vehicle Sale - Full Payment';
    if (t === 'sale_deposit' || t === 'venda_entrada') return 'Vehicle Sale - Down Payment (Deposit)';
    if (t === 'sale_installment' || t === 'venda_parcela') return 'Vehicle Sale - Instalment Payment';
    if (t === 'rent' || t === 'aluguel') return 'Vehicle Rental Payment';
    if (t === 'deposit' || t === 'deposito') return 'Rental Security Deposit (Refundable)';
    if (t === 'deposit_refund' || t === 'devolucao_deposito') return 'Security Deposit Refund';
    if (t === 'fine' || t === 'multa') return 'Traffic / Parking Fine (PCN)';
    if (t === 'damage' || t === 'dano') return 'Vehicle Damage Repair Charge';
    if (t === 'admin_fee') return 'Administration Fee';
    if (t === 'other' || t === 'outro') return 'Additional Charge';
    return tipo.replace(/_/g, ' ');
}

function abrirModalRecibo(t) {
    if (!t) return;
    const modal = document.getElementById('reciboModal');
    if (!modal) return;

    const dataPag = t.data_pagamento ? new Date(t.data_pagamento).toLocaleString('en-GB') : '-';

    document.getElementById('rec_id').textContent = `#${t.id}`;
    document.getElementById('rec_contrato_id').textContent = `Contract #${t.id_contrato}`;
    document.getElementById('rec_cliente').textContent = t.cliente || '-';
    document.getElementById('rec_placa').textContent = t.placa || '-';
    document.getElementById('rec_tipo').textContent = t.descricao || formatarDescricaoTransacao(t.tipo);
    document.getElementById('rec_data').textContent = dataPag;
    document.getElementById('rec_forma').textContent = t.forma_pagamento || 'Not specified';
    document.getElementById('rec_valor').textContent = formatoMoeda.format(t.valor);

    const rowNota = document.getElementById('rec_row_nota');
    const elNota = document.getElementById('rec_nota');
    if (rowNota && elNota) {
        if (t.nota) {
            elNota.textContent = t.nota;
            rowNota.style.display = 'flex';
        } else {
            rowNota.style.display = 'none';
        }
    }

    const btnLink = document.getElementById('btnLinkRecibo');
    if (btnLink) btnLink.href = `/recibo/${t.id}`;

    modal.classList.add('active');
}

function fecharModalRecibo() {
    const modal = document.getElementById('reciboModal');
    if (modal) modal.classList.remove('active');
}

// ==========================================
// 4. DAILY CASHING UP (RECONCILIAÇÃO)
// ==========================================
async function abrirModalCashingUp(dataEspecifica) {
    const modal = document.getElementById('cashingUpModal');
    if (!modal) return;

    const inputData = document.getElementById('cashingUpDate');
    if (inputData && !dataEspecifica) {
        const d = new Date();
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        inputData.value = `${yyyy}-${mm}-${dd}`;
    } else if (inputData && dataEspecifica) {
        inputData.value = dataEspecifica;
    }

    modal.classList.add('active');
    carregarDadosCashingUp(inputData ? inputData.value : '');
}

async function carregarDadosCashingUp(dataStr) {
    const listContainer = document.getElementById('cashingUpItemsList');
    if (listContainer) {
        listContainer.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding:1rem;">Loading daily transactions...</div>';
    }

    try {
        const url = dataStr ? `/api/financeiro/fechamento-caixa?data=${dataStr}` : '/api/financeiro/fechamento-caixa';
        const res = await fetch(url);
        if (!res.ok) return;
        const data = await res.json();

        const grandTotalEl = document.getElementById('cashingUpGrandTotal');
        if (grandTotalEl) grandTotalEl.textContent = formatoMoeda.format(data.total_arrecadado || 0);

        const m = data.metodos || {};

        // Cash
        const elCashTot = document.getElementById('cashUpTotalCash');
        const elCashQtd = document.getElementById('cashUpCountCash');
        if (elCashTot) elCashTot.textContent = formatoMoeda.format(m['Cash']?.total || 0);
        if (elCashQtd) elCashQtd.textContent = `${m['Cash']?.qtd || 0} tx`;

        // Card
        const elCardTot = document.getElementById('cashUpTotalCard');
        const elCardQtd = document.getElementById('cashUpCountCard');
        if (elCardTot) elCardTot.textContent = formatoMoeda.format(m['Card']?.total || 0);
        if (elCardQtd) elCardQtd.textContent = `${m['Card']?.qtd || 0} tx`;

        // Bank Transfer
        const elBankTot = document.getElementById('cashUpTotalBank');
        const elBankQtd = document.getElementById('cashUpCountBank');
        if (elBankTot) elBankTot.textContent = formatoMoeda.format(m['Bank Transfer']?.total || 0);
        if (elBankQtd) elBankQtd.textContent = `${m['Bank Transfer']?.qtd || 0} tx`;

        // Exchange
        const elExchTot = document.getElementById('cashUpTotalExchange');
        const elExchQtd = document.getElementById('cashUpCountExchange');
        if (elExchTot) elExchTot.textContent = formatoMoeda.format(m['Exchange']?.total || 0);
        if (elExchQtd) elExchQtd.textContent = `${m['Exchange']?.qtd || 0} tx`;

        // Detailed Feed
        if (listContainer) {
            const allItems = [];
            Object.keys(m).forEach(metodoNome => {
                (m[metodoNome].itens || []).forEach(it => {
                    allItems.push(it);
                });
            });

            if (allItems.length === 0) {
                listContainer.innerHTML = '<div style="color:var(--text-secondary); text-align:center; padding:1.5rem; font-size:0.85rem;">No payments registered on this date.</div>';
                return;
            }

            listContainer.innerHTML = allItems.map(item => `
                <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.5rem 0.75rem; display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem;">
                    <div>
                        <div style="font-weight: 600; color: var(--text-primary);">
                            <span>[${item.hora}]</span> ${escapeHtml(item.cliente)} <span style="font-weight: 400; color: var(--text-secondary);">(${escapeHtml(item.placa)})</span>
                        </div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 1px;">
                            ${escapeHtml(item.tipo)} &bull; <span style="color: var(--accent); font-weight: 600;">${escapeHtml(item.forma_especifica || '')}</span>
                            ${item.nota ? `&bull; 📝 ${escapeHtml(item.nota)}` : ''}
                        </div>
                    </div>
                    <strong style="color: var(--success); font-size: 0.95rem;">${formatoMoeda.format(item.valor || 0)}</strong>
                </div>
            `).join('');
        }
    } catch (err) {
        console.error('Error fetching cashing up data:', err);
    }
}

function fecharModalCashingUp() {
    const modal = document.getElementById('cashingUpModal');
    if (modal) modal.classList.remove('active');
}

// ==========================================
// 5. SINCRONIZAÇÃO INTELIGENTE DE FILTROS & DATAS
// ==========================================
function atualizarModoData(novoModo, atualizarTabela = false) {
    campoData = (novoModo === 'pagamento') ? 'pagamento' : 'vencimento';
    const filterCampoData = document.getElementById('filterCampoData');
    if (filterCampoData) {
        filterCampoData.value = campoData;
        if (campoData === 'pagamento') {
            filterCampoData.style.color = '#34d399';
        } else {
            filterCampoData.style.color = 'var(--accent, #ff6b00)';
        }
    }

    // Auto-align default sorting if user hasn't explicitly clicked a different column
    if (campoData === 'pagamento') {
        if (sortCol === 'data_vencimento') {
            sortCol = 'data_pagamento';
            sortOrder = 'desc';
        }
    } else {
        if (sortCol === 'data_pagamento') {
            sortCol = 'data_vencimento';
            sortOrder = 'asc';
        }
    }

    if (atualizarTabela) {
        paginaAtual = 1;
        carregarFinanceiro();
    }
}

function sincronizarFiltrosPorStatus(novoStatus) {
    statusFiltro = novoStatus;
    const filterStatusEl = document.getElementById('filterStatus');
    if (filterStatusEl && filterStatusEl.value !== novoStatus) {
        filterStatusEl.value = novoStatus;
    }

    const stLower = (novoStatus || '').toLowerCase();
    if (stLower === 'paid' || stLower === 'pago') {
        // If Paid is selected, date filtering must follow Payment Date
        atualizarModoData('pagamento', false);
    } else if (stLower === 'pendentes' || stLower === 'pending' || stLower === 'overdue' || stLower === 'vencidos' || stLower === 'cancelled') {
        // Unpaid transactions do not have payment dates, so align date to Due Date
        atualizarModoData('vencimento', false);
        // Also, unpaid transactions do not have a payment method, so reset method filter
        const filterMetodoEl = document.getElementById('filterMetodo');
        if (filterMetodoEl && filterMetodoEl.value) {
            filterMetodoEl.value = '';
            metodoFiltro = '';
        }
    }
}

function desmarcarPillsData() {
    document.querySelectorAll('.btn-date-pill').forEach(btn => {
        btn.classList.remove('active');
        btn.style.background = 'var(--card-bg)';
        btn.style.borderColor = 'var(--border-color)';
        btn.style.color = 'var(--text-secondary)';
    });
}

function aplicarPeriodoRapido(range) {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const hojeStr = `${yyyy}-${mm}-${dd}`;

    const inputIni = document.getElementById('filterDataInicio');
    const inputFim = document.getElementById('filterDataFim');

    // If on Overdue status and user clicks Today: overdue items are past due (< today).
    // An operator clicking "Today" expects today's pending charges or today's collections.
    if (statusFiltro === 'overdue' && range === 'today') {
        sincronizarFiltrosPorStatus('pendentes');
    }

    document.querySelectorAll('.btn-date-pill').forEach(btn => {
        if (btn.getAttribute('data-range') === range) {
            btn.classList.add('active');
            btn.style.background = 'rgba(255, 107, 0, 0.18)';
            btn.style.borderColor = 'var(--accent, #ff6b00)';
            btn.style.color = 'var(--accent, #ff6b00)';
        } else {
            btn.classList.remove('active');
            btn.style.background = 'var(--card-bg)';
            btn.style.borderColor = 'var(--border-color)';
            btn.style.color = 'var(--text-secondary)';
        }
    });

    if (range === 'all') {
        dataInicio = '';
        dataFim = '';
        if (inputIni) inputIni.value = '';
        if (inputFim) inputFim.value = '';
    } else if (range === 'today') {
        dataInicio = hojeStr;
        dataFim = hojeStr;
        if (inputIni) inputIni.value = hojeStr;
        if (inputFim) inputFim.value = hojeStr;
    } else if (range === 'yesterday') {
        const yest = new Date(now);
        yest.setDate(yest.getDate() - 1);
        const yStr = `${yest.getFullYear()}-${String(yest.getMonth() + 1).padStart(2, '0')}-${String(yest.getDate()).padStart(2, '0')}`;
        dataInicio = yStr;
        dataFim = yStr;
        if (inputIni) inputIni.value = yStr;
        if (inputFim) inputFim.value = yStr;
    } else if (range === 'week') {
        const dWeek = new Date(now);
        const dayOfWeek = (dWeek.getDay() + 6) % 7; // Monday = 0
        dWeek.setDate(dWeek.getDate() - dayOfWeek);
        const wStr = `${dWeek.getFullYear()}-${String(dWeek.getMonth() + 1).padStart(2, '0')}-${String(dWeek.getDate()).padStart(2, '0')}`;
        dataInicio = wStr;
        dataFim = hojeStr;
        if (inputIni) inputIni.value = wStr;
        if (inputFim) inputFim.value = hojeStr;
    } else if (range === 'month') {
        const mStr = `${yyyy}-${mm}-01`;
        dataInicio = mStr;
        dataFim = hojeStr;
        if (inputIni) inputIni.value = mStr;
        if (inputFim) inputFim.value = hojeStr;
    }

    paginaAtual = 1;
    carregarFinanceiro();
}

// ==========================================
// 7. INICIALIZAÇÃO DO DOM & EVENTOS
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const paramStatus = urlParams.get('status');
    if (paramStatus) {
        const stLower = paramStatus.toLowerCase();
        if (stLower === 'overdue' || stLower === 'vencidos') {
            sincronizarFiltrosPorStatus('overdue');
        } else if (stLower === 'paid') {
            sincronizarFiltrosPorStatus('Paid');
        } else if (stLower === 'all') {
            sincronizarFiltrosPorStatus('');
        } else if (stLower === 'pendentes' || stLower === 'pending') {
            sincronizarFiltrosPorStatus('pendentes');
        }
    } else {
        sincronizarFiltrosPorStatus('pendentes');
    }

    const paramCampoData = urlParams.get('campo_data');
    if (paramCampoData) {
        atualizarModoData(paramCampoData, false);
    }

    const paramTipo = urlParams.get('tipo');
    const filterTipoEl = document.getElementById('filterTipo');
    if (paramTipo && filterTipoEl) {
        tipoFiltro = paramTipo;
        filterTipoEl.value = paramTipo;
    }

    const paramSearch = urlParams.get('search') || urlParams.get('q');
    const searchInputEl = document.getElementById('searchInput');
    if (paramSearch && searchInputEl) {
        termoBusca = paramSearch;
        searchInputEl.value = paramSearch;
    }

    // Initial Data Fetch
    carregarKpis();
    carregarFinanceiro();
    
    // Pagination Controls
    const btnPrev = document.getElementById('btnPrevPage');
    const btnNext = document.getElementById('btnNextPage');
    if (btnPrev) {
        btnPrev.addEventListener('click', () => {
            if (paginaAtual > 1) {
                paginaAtual--;
                carregarFinanceiro();
            }
        });
    }
    if (btnNext) {
        btnNext.addEventListener('click', () => {
            paginaAtual++;
            carregarFinanceiro();
        });
    }

    // Search input with debounce
    const searchInput = document.getElementById('searchInput');
    let timeoutId;
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                termoBusca = e.target.value.trim();
                filtroExatoContrato = null;
                filtroExatoClienteId = null;
                filtroExatoClienteNome = null;
                filtroExatoPlaca = null;
                atualizarPillFiltroExato();
                paginaAtual = 1;
                carregarFinanceiro();
            }, 300);
        });
    }

    // Filter Status
    const filterStatus = document.getElementById('filterStatus');
    if (filterStatus) {
        filterStatus.addEventListener('change', (e) => {
            sincronizarFiltrosPorStatus(e.target.value);
            paginaAtual = 1;
            carregarFinanceiro();
        });
    }

    // Filter Type
    const filterTipo = document.getElementById('filterTipo');
    if (filterTipo) {
        filterTipo.addEventListener('change', (e) => {
            tipoFiltro = e.target.value;
            paginaAtual = 1;
            carregarFinanceiro();
        });
    }

    // Filter Payment Method
    const filterMetodo = document.getElementById('filterMetodo');
    if (filterMetodo) {
        filterMetodo.addEventListener('change', (e) => {
            metodoFiltro = e.target.value;
            if (metodoFiltro) {
                // Payment methods only exist on completed payments (Paid)
                if (statusFiltro === 'pendentes' || statusFiltro === 'overdue') {
                    sincronizarFiltrosPorStatus('Paid');
                }
            }
            paginaAtual = 1;
            carregarFinanceiro();
        });
    }

    // Filter Page Size
    const filterPageSize = document.getElementById('filterPageSize');
    if (filterPageSize) {
        filterPageSize.addEventListener('change', (e) => {
            limitePorPagina = parseInt(e.target.value, 10) || 20;
            paginaAtual = 1;
            carregarFinanceiro();
        });
    }

    // Date Filters
    const filterCampoData = document.getElementById('filterCampoData');
    if (filterCampoData) {
        filterCampoData.addEventListener('change', (e) => {
            const val = e.target.value;
            if (val === 'pagamento') {
                if (statusFiltro === 'pendentes' || statusFiltro === 'overdue' || statusFiltro === 'Cancelled') {
                    sincronizarFiltrosPorStatus('Paid');
                } else {
                    atualizarModoData('pagamento', false);
                }
            } else {
                atualizarModoData('vencimento', false);
            }
            paginaAtual = 1;
            carregarFinanceiro();
        });
    }

    const filterDataInicio = document.getElementById('filterDataInicio');
    if (filterDataInicio) {
        filterDataInicio.addEventListener('change', (e) => {
            dataInicio = e.target.value;
            desmarcarPillsData();
            if (!dataInicio && !dataFim) {
                const pillAll = document.querySelector('.btn-date-pill[data-range="all"]');
                if (pillAll) {
                    pillAll.classList.add('active');
                    pillAll.style.background = 'rgba(255, 107, 0, 0.18)';
                    pillAll.style.borderColor = 'var(--accent, #ff6b00)';
                    pillAll.style.color = 'var(--accent, #ff6b00)';
                }
            }
            paginaAtual = 1;
            carregarFinanceiro();
        });
    }

    const filterDataFim = document.getElementById('filterDataFim');
    if (filterDataFim) {
        filterDataFim.addEventListener('change', (e) => {
            dataFim = e.target.value;
            desmarcarPillsData();
            if (!dataInicio && !dataFim) {
                const pillAll = document.querySelector('.btn-date-pill[data-range="all"]');
                if (pillAll) {
                    pillAll.classList.add('active');
                    pillAll.style.background = 'rgba(255, 107, 0, 0.18)';
                    pillAll.style.borderColor = 'var(--accent, #ff6b00)';
                    pillAll.style.color = 'var(--accent, #ff6b00)';
                }
            }
            paginaAtual = 1;
            carregarFinanceiro();
        });
    }

    // Date Shortcut Pills
    document.querySelectorAll('.btn-date-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            const range = btn.getAttribute('data-range');
            aplicarPeriodoRapido(range);
        });
    });

    // KPI Cards Click-to-Filter
    const cardKpiPending = document.getElementById('cardKpiPending');
    if (cardKpiPending) {
        cardKpiPending.addEventListener('click', () => {
            sincronizarFiltrosPorStatus('pendentes');
            aplicarPeriodoRapido('all');
        });
    }

    const cardKpiOverdue = document.getElementById('cardKpiOverdue');
    if (cardKpiOverdue) {
        cardKpiOverdue.addEventListener('click', () => {
            sincronizarFiltrosPorStatus('overdue');
            aplicarPeriodoRapido('all');
        });
    }

    const cardKpiToday = document.getElementById('cardKpiToday');
    if (cardKpiToday) {
        cardKpiToday.addEventListener('click', () => {
            sincronizarFiltrosPorStatus('Paid');
            aplicarPeriodoRapido('today');
        });
    }

    const cardKpiWeek = document.getElementById('cardKpiWeek');
    if (cardKpiWeek) {
        cardKpiWeek.addEventListener('click', () => {
            sincronizarFiltrosPorStatus('Paid');
            aplicarPeriodoRapido('week');
        });
    }

    // Dismiss active exact inline filter pill
    const btnRemoveActiveFilter = document.getElementById('btnRemoveActiveFilter');
    if (btnRemoveActiveFilter) {
        btnRemoveActiveFilter.addEventListener('click', (e) => {
            e.preventDefault();
            filtroExatoContrato = null;
            filtroExatoClienteId = null;
            filtroExatoClienteNome = null;
            filtroExatoPlaca = null;
            atualizarPillFiltroExato();
            paginaAtual = 1;
            carregarFinanceiro();
        });
    }

    // Enable Server-Side Table Sorting
    if (typeof enableTableSorting === 'function') {
        enableTableSorting('financeiroTable', (field, order) => {
            sortCol = field;
            sortOrder = order;
            paginaAtual = 1;
            carregarFinanceiro();
        });
    }

    // Clear Filters Button
    const btnClear = document.getElementById('btnClearFilters');
    if (btnClear) {
        btnClear.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            if (filterTipo) filterTipo.value = '';
            if (filterMetodo) filterMetodo.value = '';
            if (filterPageSize) filterPageSize.value = '20';
            termoBusca = '';
            tipoFiltro = '';
            metodoFiltro = '';
            limitePorPagina = 20;
            filtroExatoContrato = null;
            filtroExatoClienteId = null;
            filtroExatoClienteNome = null;
            filtroExatoPlaca = null;
            atualizarPillFiltroExato();
            sincronizarFiltrosPorStatus('pendentes');
            aplicarPeriodoRapido('all');
        });
    }

    // Open Daily Cashing Up Modal
    const btnOpenCashingUp = document.getElementById('btnOpenCashingUp');
    if (btnOpenCashingUp) {
        btnOpenCashingUp.addEventListener('click', () => abrirModalCashingUp());
    }

    const closeCashUpBtn = document.getElementById('closeCashingUpModal');
    if (closeCashUpBtn) closeCashUpBtn.addEventListener('click', fecharModalCashingUp);
    const closeCashUpFoot = document.getElementById('btnCloseCashingUpFoot');
    if (closeCashUpFoot) closeCashUpFoot.addEventListener('click', fecharModalCashingUp);

    const cashUpModal = document.getElementById('cashingUpModal');
    if (cashUpModal) {
        cashUpModal.addEventListener('click', (e) => {
            if (e.target === cashUpModal) fecharModalCashingUp();
        });
    }

    const cashingUpDateInput = document.getElementById('cashingUpDate');
    if (cashingUpDateInput) {
        cashingUpDateInput.addEventListener('change', (e) => {
            carregarDadosCashingUp(e.target.value);
        });
    }

    const btnPrintCashingUp = document.getElementById('btnPrintCashingUp');
    if (btnPrintCashingUp) {
        btnPrintCashingUp.addEventListener('click', () => {
            const dataVal = document.getElementById('cashingUpDate')?.value || '';
            const query = dataVal ? `?data=${encodeURIComponent(dataVal)}` : '';
            window.location.href = `/financeiro/fechamento-caixa/print${query}`;
        });
    }

    // PDF Report Button (Opens in same window)
    const btnOpenPdfReport = document.getElementById('btnOpenPdfReport');
    if (btnOpenPdfReport) {
        btnOpenPdfReport.addEventListener('click', () => {
            let pendentesParam = statusFiltro === 'pendentes' ? 'true' : 'false';
            let statusParam = (statusFiltro !== 'pendentes') ? statusFiltro : '';

            const params = new URLSearchParams({
                search: termoBusca,
                status: statusParam,
                pendentes: pendentesParam,
                tipo: tipoFiltro,
                metodo: metodoFiltro,
                campo_data: campoData,
                data_inicio: dataInicio,
                data_fim: dataFim
            });
            if (filtroExatoContrato) params.append('contrato_id', filtroExatoContrato);
            if (filtroExatoClienteId) params.append('cliente_id', filtroExatoClienteId);
            if (filtroExatoPlaca) params.append('placa', filtroExatoPlaca);

            window.location.href = `/financeiro/relatorio-pdf?${params.toString()}`;
        });
    }

    // Submit Payment Form
    const pagForm = document.getElementById('pagamentoForm');
    if (pagForm) {
        pagForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('pag_cobranca_id').value;
            const btnSubmit = document.getElementById('btnConfirmarPag');
            
            if (!splitPaymentMgr) {
                splitPaymentMgr = createSplitPaymentManager({ formatoMoeda });
            }

            const payload = splitPaymentMgr.getPayload();
            if (payload.valor_pago <= 0) {
                alert('Please enter a valid payment amount greater than zero.');
                return;
            }

            btnSubmit.disabled = true;
            btnSubmit.textContent = 'Processing...';

            try {
                const res = await fetch(`/api/financeiro/pagar/${id}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    fecharModalPagamento();
                    carregarFinanceiro();
                    carregarKpis();
                } else {
                    const err = await res.json();
                    alert(err.message || err.mensagem || err.error || err.erro || 'Failed to record payment');
                }
            } catch (err) {
                alert('Connection error while processing payment.');
            } finally {
                btnSubmit.disabled = false;
                splitPaymentMgr.recalculate();
            }
        });
    }

    // Close Payment Modal
    const closePagBtn = document.getElementById('closePagamentoModal');
    if (closePagBtn) closePagBtn.addEventListener('click', fecharModalPagamento);
    const pagModal = document.getElementById('pagamentoModal');
    if (pagModal) {
        pagModal.addEventListener('click', (e) => {
            if (e.target === pagModal) fecharModalPagamento();
        });
    }

    // Close Receipt Modal
    const closeRecBtn = document.getElementById('closeReciboModal');
    if (closeRecBtn) closeRecBtn.addEventListener('click', fecharModalRecibo);
    const recModal = document.getElementById('reciboModal');
    if (recModal) {
        recModal.addEventListener('click', (e) => {
            if (e.target === recModal) fecharModalRecibo();
        });
    }

    function imprimirReciboDireto(url) {
        if (!url || url === '#' || url.endsWith('#')) {
            window.print();
            return;
        }

        let iframe = document.getElementById('reciboPrintFrame');
        if (!iframe) {
            iframe = document.createElement('iframe');
            iframe.id = 'reciboPrintFrame';
            iframe.style.position = 'fixed';
            iframe.style.top = '-9999px';
            iframe.style.left = '-9999px';
            iframe.style.width = '10px';
            iframe.style.height = '10px';
            iframe.style.border = 'none';
            iframe.style.opacity = '0';
            iframe.style.pointerEvents = 'none';
            document.body.appendChild(iframe);
        }

        iframe.onload = function() {
            setTimeout(() => {
                try {
                    iframe.contentWindow.focus();
                    iframe.contentWindow.print();
                } catch (err) {
                    console.warn('Iframe direct print failed, opening fallback window:', err);
                    window.open(`${url}?autoprint=1`, '_blank');
                }
            }, 250);
        };

        iframe.src = url;
    }

    const btnPrint = document.getElementById('btnPrintRecibo');
    if (btnPrint) {
        btnPrint.addEventListener('click', () => {
            const btnLink = document.getElementById('btnLinkRecibo');
            if (btnLink && btnLink.href && btnLink.href !== '#' && !btnLink.href.endsWith('#')) {
                imprimirReciboDireto(btnLink.href);
            } else {
                window.print();
            }
        });
    }


    // Escape Key Handler for Modals
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            fecharModalPagamento();
            fecharModalRecibo();
            fecharModalCashingUp();
        }
    });
});
