let paginaAtual = 1;
let termoBusca = '';
let statusFiltro = 'pendentes';
let tipoFiltro = '';
let campoData = 'vencimento';
let dataInicio = '';
let dataFim = '';
let sortCol = 'data_vencimento';
let sortOrder = 'asc';
let transacoesCache = [];

const formatoMoeda = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });

async function carregarFinanceiro() {
    const tbody = document.querySelector('#financeiroTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    const btnClear = document.getElementById('btnClearFilters');

    // Clear Filters Button
    if (btnClear) {
        btnClear.style.display = (termoBusca || statusFiltro !== 'pendentes' || tipoFiltro || dataInicio || dataFim || campoData !== 'vencimento') ? 'block' : 'none';
    }

    try {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:2.5rem; color:var(--text-secondary);">Loading transactions...</td></tr>';
        
        let pendentesParam = statusFiltro === 'pendentes' ? 'true' : 'false';
        let statusParam = (statusFiltro !== 'pendentes') ? statusFiltro : '';

        const params = new URLSearchParams({
            page: paginaAtual,
            limit: 20,
            search: termoBusca,
            status: statusParam,
            pendentes: pendentesParam,
            tipo: tipoFiltro,
            campo_data: campoData,
            data_inicio: dataInicio,
            data_fim: dataFim,
            sort_by: sortCol,
            sort_order: sortOrder
        });

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
            return;
        }
        
        tbody.innerHTML = '';
        const hoje = new Date();
        hoje.setHours(0, 0, 0, 0);

        transacoes.forEach((t, index) => {
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

            // Type Badges
            let tipoBadge = '';
            const tipoLower = (t.tipo || '').toLowerCase();
            if (tipoLower === 'rent' || tipoLower === 'aluguel') tipoBadge = '<span class="badge badge-info">Rent</span>';
            else if (tipoLower === 'deposit' || tipoLower === 'deposito') tipoBadge = '<span class="badge" style="background:rgba(168, 85, 247, 0.2); color:#c084fc;">Deposit</span>';
            else if (tipoLower === 'sale_full' || tipoLower === 'venda_vista') tipoBadge = '<span class="badge" style="background:rgba(16, 185, 129, 0.2); color:#34d399; border:1px solid rgba(16, 185, 129, 0.4);">Sale: Full Payment</span>';
            else if (tipoLower === 'sale_deposit' || tipoLower === 'venda_entrada') tipoBadge = '<span class="badge" style="background:rgba(217, 119, 6, 0.2); color:#fbbf24; border:1px solid rgba(217, 119, 6, 0.4);">Sale: Down Payment</span>';
            else if (tipoLower === 'sale_installment' || tipoLower === 'venda_parcela') tipoBadge = '<span class="badge" style="background:rgba(59, 130, 246, 0.2); color:#60a5fa; border:1px solid rgba(59, 130, 246, 0.4);">Sale: Installment</span>';
            else if (tipoLower === 'fine' || tipoLower === 'multa') tipoBadge = '<span class="badge badge-danger">Fine</span>';
            else if (tipoLower === 'damage' || tipoLower === 'dano') tipoBadge = '<span class="badge badge-warning">Damage</span>';
            else if (tipoLower === 'deposit_refund' || tipoLower === 'devolucao_deposito') tipoBadge = '<span class="badge badge-success">Deposit Refund</span>';
            else tipoBadge = `<span class="badge">${escapeHtml(t.tipo)}</span>`;
            
            // Formatted Amount
            const valorFmt = formatoMoeda.format(t.valor);
            
            // Payment Cell
            let celulaPagamento = '<span style="color:var(--text-secondary); opacity:0.6;">-</span>';
            if (isPaid) {
                const isDepositDeduction = t.forma_pagamento === 'Deposit';
                const formaLabel = isDepositDeduction ? 'Deposit (Deduction)' : (t.forma_pagamento || '');
                const colorStyle = isDepositDeduction ? 'color:#60a5fa; font-weight:600;' : 'color:var(--text-secondary);';
                const staffHtml = t.registrado_por_nome ? `<span style="display:block; font-size:0.7rem; color:#a855f7; margin-top:2px;">👤 ${escapeHtml(t.registrado_por_nome)}</span>` : '';
                celulaPagamento = `<div>
                    <span style="font-weight:500;">${pagamento}</span>
                    <small style="display:block; ${colorStyle} font-size:0.75rem;">${formaLabel}</small>
                    ${staffHtml}
                </div>`;
            }

            // Due Date Cell
            let celulaVencimento = `<span>${vencimento}</span>`;
            if (isVencido) {
                celulaVencimento = `<span style="color:#f87171; font-weight:600;" title="Charge overdue!">${vencimento} ⚠️</span>`;
            }

            // Action Button
            let actBtn = '-';
            if (isPending) {
                actBtn = `<button class="btn-action btn-abrir-pagar" data-index="${index}" style="background:var(--success);">
                    Mark Paid
                </button>`;
            } else if (isPaid) {
                actBtn = `
                    <div style="display:flex; gap:6px; justify-content:flex-end; align-items:center;">
                        <button class="btn-action btn-abrir-recibo" data-index="${index}" style="background:rgba(255,255,255,0.06); border:1px solid var(--border-color); color:var(--text-primary); padding:4px 8px;" title="View Receipt">
                            🧾 Receipt
                        </button>
                        <button class="btn-action btn-reverter-fin" data-id="${t.id}" data-tipo="${t.tipo}" data-valor="${t.valor}" style="background:rgba(239, 68, 68, 0.12); border:1px solid rgba(239, 68, 68, 0.3); color:#f87171; padding:4px 8px; border-radius:6px; cursor:pointer;" title="Cancel payment and return to Pending">
                            ↩ Revert
                        </button>
                    </div>
                `;
            }
            
            tr.innerHTML = `
                <td style="font-weight:700; color:var(--text-secondary); font-size:0.85rem;">#${t.id}</td>
                <td>
                    <a href="/contratos/${t.id_contrato}" class="link-contrato" title="View details for Contract #${t.id_contrato}">
                        Contract #${t.id_contrato} &rarr;
                    </a>
                </td>
                <td style="font-weight:500; max-width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(t.cliente || '')}">${escapeHtml(t.cliente || '-')}</td>
                <td class="nowrap"><span class="badge-plate">${escapeHtml(t.placa || '-')}</span></td>
                <td class="nowrap">${tipoBadge}</td>
                <td class="nowrap" style="font-weight:700; font-size:1rem; color:var(--text-primary);">${valorFmt}</td>
                <td class="nowrap">${celulaVencimento}</td>
                <td class="nowrap">${celulaPagamento}</td>
                <td class="nowrap">${statusBadge}</td>
                <td style="text-align: right; white-space: nowrap;">${actBtn}</td>
            `;
            tbody.appendChild(tr);
        });

        // Pagination UI
        if (paginationInfo) {
            paginationInfo.textContent = `Page ${data.pagina_atual} of ${data.paginas || 1} (${data.total} records)`;
        }
        const btnPrev = document.getElementById('btnPrevPage');
        const btnNext = document.getElementById('btnNextPage');
        if (btnPrev) btnPrev.disabled = data.pagina_atual <= 1;
        if (btnNext) btnNext.disabled = data.pagina_atual >= (data.paginas || 1);
        
        // Listeners for Mark Paid
        document.querySelectorAll('.btn-abrir-pagar').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(btn.getAttribute('data-index'), 10);
                abrirModalPagamento(transacoesCache[idx]);
            });
        });

        // Listeners for Receipt
        document.querySelectorAll('.btn-abrir-recibo').forEach(btn => {
            btn.addEventListener('click', (e) => {
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
                } catch (err) {
                    console.error('Error reverting payment:', err);
                    alert('Connection error while cancelling payment.');
                    b.disabled = false;
                    b.textContent = '↩ Revert';
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

// Payment Modal
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
    if (t === 'fine' || t === 'multa') return 'Traffic / Parking Fine';
    if (t === 'damage' || t === 'dano') return 'Vehicle Damage Charge';
    if (t === 'other' || t === 'outro') return 'Additional Charge';
    return tipo.replace(/_/g, ' ');
}

// Receipt Modal
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

    const btnLink = document.getElementById('btnLinkRecibo');
    if (btnLink) btnLink.href = `/recibo/${t.id}`;

    modal.classList.add('active');
}

function fecharModalRecibo() {
    const modal = document.getElementById('reciboModal');
    if (modal) modal.classList.remove('active');
}

document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const paramStatus = urlParams.get('status');
    const filterStatusEl = document.getElementById('filterStatus');
    if (paramStatus && filterStatusEl) {
        if (paramStatus.toLowerCase() === 'overdue' || paramStatus.toLowerCase() === 'vencidos') {
            statusFiltro = 'overdue';
            filterStatusEl.value = 'overdue';
        } else if (paramStatus.toLowerCase() === 'paid') {
            statusFiltro = 'Paid';
            filterStatusEl.value = 'Paid';
        } else if (paramStatus.toLowerCase() === 'all') {
            statusFiltro = '';
            filterStatusEl.value = '';
        }
    }

    carregarFinanceiro();
    
    // Pagination
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

    // Search with debounce
    const searchInput = document.getElementById('searchInput');
    let timeoutId;
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                termoBusca = e.target.value.trim();
                paginaAtual = 1;
                carregarFinanceiro();
            }, 300);
        });
    }

    // Filter Status
    const filterStatus = document.getElementById('filterStatus');
    if (filterStatus) {
        filterStatus.addEventListener('change', (e) => {
            statusFiltro = e.target.value;
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

    // Date Filters
    const filterCampoData = document.getElementById('filterCampoData');
    if (filterCampoData) {
        filterCampoData.addEventListener('change', (e) => {
            campoData = e.target.value;
            paginaAtual = 1;
            carregarFinanceiro();
        });
    }

    const filterDataInicio = document.getElementById('filterDataInicio');
    if (filterDataInicio) {
        filterDataInicio.addEventListener('change', (e) => {
            dataInicio = e.target.value;
            paginaAtual = 1;
            carregarFinanceiro();
        });
    }

    const filterDataFim = document.getElementById('filterDataFim');
    if (filterDataFim) {
        filterDataFim.addEventListener('change', (e) => {
            dataFim = e.target.value;
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
            if (filterStatus) filterStatus.value = 'pendentes';
            if (filterTipo) filterTipo.value = '';
            if (filterCampoData) filterCampoData.value = 'vencimento';
            if (filterDataInicio) filterDataInicio.value = '';
            if (filterDataFim) filterDataFim.value = '';
            termoBusca = '';
            statusFiltro = 'pendentes';
            tipoFiltro = '';
            campoData = 'vencimento';
            dataInicio = '';
            dataFim = '';
            sortCol = 'data_vencimento';
            sortOrder = 'asc';
            paginaAtual = 1;
            carregarFinanceiro();
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

    // Modal close handlers
    const closePagBtn = document.getElementById('closePagamentoModal');
    if (closePagBtn) closePagBtn.addEventListener('click', fecharModalPagamento);
    const pagModal = document.getElementById('pagamentoModal');
    if (pagModal) {
        pagModal.addEventListener('click', (e) => {
            if (e.target === pagModal) fecharModalPagamento();
        });
    }

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

    // Close on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            fecharModalPagamento();
            fecharModalRecibo();
        }
    });
});

