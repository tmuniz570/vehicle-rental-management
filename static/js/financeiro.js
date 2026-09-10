let paginaAtual = 1;
let termoBusca = '';
let statusFiltro = 'pendentes';
let tipoFiltro = '';
let transacoesCache = [];

const formatoMoeda = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });

async function carregarFinanceiro() {
    const tbody = document.querySelector('#financeiroTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    const btnClear = document.getElementById('btnClearFilters');

    // Clear Filters Button
    if (btnClear) {
        btnClear.style.display = (termoBusca || statusFiltro !== 'pendentes' || tipoFiltro) ? 'block' : 'none';
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
            tipo: tipoFiltro
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
            const vencimento = dataVencObj ? dataVencObj.toLocaleDateString('en-GB') : '-';
            
            const tStatusLower = (t.status || '').toLowerCase();
            const isPaid = tStatusLower === 'paid' || tStatusLower === 'pago';
            const isPending = tStatusLower === 'pending' || tStatusLower === 'pendente';
            const isVencido = isPending && dataVencObj && dataVencObj < hoje;

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
                statusBadge = `<span class="badge">${t.status}</span>`;
            }

            // Type Badges
            let tipoBadge = '';
            const tipoLower = (t.tipo || '').toLowerCase();
            if (tipoLower === 'rent' || tipoLower === 'aluguel') tipoBadge = '<span class="badge badge-info">Rent</span>';
            else if (tipoLower === 'deposit' || tipoLower === 'deposito') tipoBadge = '<span class="badge" style="background:rgba(168, 85, 247, 0.2); color:#c084fc;">Deposit</span>';
            else if (tipoLower === 'fine' || tipoLower === 'multa') tipoBadge = '<span class="badge badge-danger">Fine</span>';
            else if (tipoLower === 'damage' || tipoLower === 'dano') tipoBadge = '<span class="badge badge-warning">Damage</span>';
            else if (tipoLower === 'deposit_refund' || tipoLower === 'devolucao_deposito') tipoBadge = '<span class="badge badge-success">Deposit Refund</span>';
            else tipoBadge = `<span class="badge">${t.tipo}</span>`;
            
            // Formatted Amount
            const valorFmt = formatoMoeda.format(t.valor);
            
            // Payment Cell
            let celulaPagamento = '<span style="color:var(--text-secondary); opacity:0.6;">-</span>';
            if (isPaid) {
                celulaPagamento = `<div>
                    <span style="font-weight:500;">${pagamento}</span>
                    <small style="display:block; color:var(--text-secondary); font-size:0.75rem;">${t.forma_pagamento || ''}</small>
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
                actBtn = `<button class="btn-action btn-abrir-recibo" data-index="${index}" style="background:rgba(255,255,255,0.06); border:1px solid var(--border-color); color:var(--text-primary);">
                    🧾 Receipt
                </button>`;
            }
            
            tr.innerHTML = `
                <td style="font-weight:700; color:var(--text-secondary); font-size:0.85rem;">#${t.id}</td>
                <td>
                    <a href="/contratos/${t.id_contrato}" class="link-contrato" title="View details for Contract #${t.id_contrato}">
                        Contract #${t.id_contrato} &rarr;
                    </a>
                </td>
                <td style="font-weight:500; max-width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${t.cliente || ''}">${t.cliente || '-'}</td>
                <td><span class="badge-plate">${t.placa || '-'}</span></td>
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
        
    } catch(e) {
        console.error("Error loading financial transactions:", e);
        tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:2rem; color:var(--error);">Failed to load transactions from server.</td></tr>';
    }
}

// Payment Modal
function abrirModalPagamento(t) {
    if (!t) return;
    const modal = document.getElementById('pagamentoModal');
    if (!modal) return;

    document.getElementById('pag_cobranca_id').value = t.id;
    document.getElementById('pag_desc_id').textContent = `#${t.id} (Contract #${t.id_contrato})`;
    document.getElementById('pag_desc_tipo').textContent = t.tipo;
    document.getElementById('pag_desc_valor').textContent = formatoMoeda.format(t.valor);
    document.getElementById('pag_forma').value = 'Cash';

    modal.classList.add('active');
}

function fecharModalPagamento() {
    const modal = document.getElementById('pagamentoModal');
    if (modal) modal.classList.remove('active');
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
    document.getElementById('rec_tipo').textContent = t.tipo;
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

    // Clear Filters Button
    const btnClear = document.getElementById('btnClearFilters');
    if (btnClear) {
        btnClear.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            if (filterStatus) filterStatus.value = 'pendentes';
            if (filterTipo) filterTipo.value = '';
            termoBusca = '';
            statusFiltro = 'pendentes';
            tipoFiltro = '';
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
            const forma = document.getElementById('pag_forma').value;
            const btnSubmit = document.getElementById('btnConfirmarPag');
            
            btnSubmit.disabled = true;
            btnSubmit.textContent = 'Processing...';

            try {
                const res = await fetch(`/api/financeiro/pagar/${id}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ forma_pagamento: forma })
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
                btnSubmit.textContent = 'Confirm Payment';
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

    const btnPrint = document.getElementById('btnPrintRecibo');
    if (btnPrint) {
        btnPrint.addEventListener('click', () => {
            window.print();
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

