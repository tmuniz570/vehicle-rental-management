let paginaAtual = 1;
let termoBusca = '';
let sortCol = 'id';
let sortOrder = 'desc';

async function carregarContratos() {
    const tbody = document.querySelector('#contratosTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    
    try {
        const filterStatus = document.getElementById('filterStatus');
        const filterTipo = document.getElementById('filterTipo');
        const statusVal = filterStatus ? filterStatus.value : 'open';
        const tipoVal = filterTipo ? filterTipo.value : '';
        
        let url = `/api/contratos?page=${paginaAtual}&limit=20&search=${encodeURIComponent(termoBusca)}&sort_by=${encodeURIComponent(sortCol)}&sort_order=${encodeURIComponent(sortOrder)}`;
        if (statusVal === 'open') {
            url += '&nao_finalizados=true';
        } else if (statusVal !== 'all') {
            url += `&status=${encodeURIComponent(statusVal)}`;
        }
        if (tipoVal) {
            url += `&tipo=${encodeURIComponent(tipoVal)}`;
        }

        const res = await fetch(url);
        const data = await res.json();
        const contratos = data.itens || [];
        
        if (contratos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;">No contracts found.</td></tr>';
            if(paginationInfo) paginationInfo.textContent = '';
            return;
        }
        
        const diasSemana = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        tbody.innerHTML = '';
        contratos.forEach(c => {
            const tr = document.createElement('tr');
            const dataRetirada = c.data_retirada ? new Date(c.data_retirada).toLocaleDateString('en-GB') : '-';
            
            // Tipo de Contrato Badge
            const tipo = (c.tipo_contrato || 'Rent').toLowerCase();
            let tipoBadge = '';
            let dueTerms = '-';
            let amountText = '-';

            if (tipo === 'sale_full') {
                tipoBadge = '<span class="badge" style="background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); font-weight: 600;">Sale: Full</span>';
                dueTerms = '<span style="color: var(--text-secondary); font-size: 0.85rem;">At Signing</span>';
                const total = c.valor_total_venda !== null && c.valor_total_venda !== undefined ? c.valor_total_venda : 0;
                amountText = `<span style="font-weight: 700; color: #4ade80;">${new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(total)}</span>`;
            } else if (tipo === 'sale_installment') {
                tipoBadge = '<span class="badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); font-weight: 600;">Sale: Inst.</span>';
                dueTerms = `<span style="color: var(--text-secondary); font-size: 0.85rem;">Dep: £${parseFloat(c.valor_entrada || 0).toFixed(2)}</span>`;
                const total = c.valor_total_venda !== null && c.valor_total_venda !== undefined ? c.valor_total_venda : 0;
                amountText = `<span style="font-weight: 700; color: #fbbf24;">${new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(total)}</span>`;
            } else {
                tipoBadge = '<span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); font-weight: 600;">Rental</span>';
                dueTerms = c.dia_pagamento_semanal !== undefined && c.dia_pagamento_semanal !== null ? diasSemana[c.dia_pagamento_semanal] : '-';
                amountText = c.valor_aluguel_semanal ? `${new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(c.valor_aluguel_semanal)}/wk` : '-';
            }
            
            let statusBadge = '';
            if (c.status === 'Active' || c.status === 'Ativo') {
                statusBadge = '<span class="badge badge-success">Active</span>';
            } else if (c.status === 'Deposit_Hold' || c.status === 'Quarentena_Deposito') {
                statusBadge = '<span class="badge badge-warning">Deposit Hold</span>';
            } else if (c.status === 'Completed' || c.status === 'Finalizado') {
                statusBadge = '<span class="badge">Completed</span>';
            } else if (c.status === 'Cancelled' || c.status === 'Cancelado') {
                statusBadge = '<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); font-weight: 700;">Cancelled</span>';
            } else {
                statusBadge = `<span class="badge">${escapeHtml(c.status)}</span>`;
            }
            
            const nomeCliente = escapeHtml(c.cliente_nome || '-');
            const placa = escapeHtml(c.placa || '-');
            
            tr.innerHTML = `
                <td>#${c.id}</td>
                <td>${tipoBadge}</td>
                <td style="font-weight:600; white-space: nowrap;" title="${nomeCliente}">${nomeCliente}</td>
                <td class="nowrap"><span class="badge-plate">${placa}</span></td>
                <td>${dataRetirada}</td>
                <td>${dueTerms}</td>
                <td>${amountText}</td>
                <td>${statusBadge}</td>
                <td>
                    <a href="/contratos/${c.id}" class="btn-primary" style="padding: 6px 12px; display:inline-flex; align-items:center; justify-content:center; text-decoration:none; font-size:0.8rem; font-weight:500; border-radius:6px; white-space: nowrap;">View Details</a>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Update pagination UI
        if(paginationInfo) {
            paginationInfo.textContent = `Page ${data.pagina_atual} of ${data.paginas} (${data.total} records)`;
        }
        const btnPrev = document.getElementById('btnPrevPage');
        const btnNext = document.getElementById('btnNextPage');
        if(btnPrev) btnPrev.disabled = data.pagina_atual <= 1;
        if(btnNext) btnNext.disabled = data.pagina_atual >= data.paginas;

        if (typeof setTableSortIndicator === 'function') {
            setTableSortIndicator('contratosTable', sortCol, sortOrder);
        }
        
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--error);">Error loading contracts.</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Check URL parameters for status filter (e.g. from Dashboard Deposit Holds link)
    const urlParams = new URLSearchParams(window.location.search);
    const paramStatus = urlParams.get('status');
    const filterStatus = document.getElementById('filterStatus');
    const filterTipo = document.getElementById('filterTipo');
    
    if (paramStatus && filterStatus) {
        if (paramStatus.toLowerCase() === 'deposit_hold' || paramStatus.toLowerCase() === 'quarentena') {
            filterStatus.value = 'Deposit_Hold';
        } else if (paramStatus.toLowerCase() === 'active') {
            filterStatus.value = 'Active';
        } else if (paramStatus.toLowerCase() === 'completed') {
            filterStatus.value = 'Completed';
        } else if (paramStatus.toLowerCase() === 'cancelled') {
            filterStatus.value = 'Cancelled';
        }
    }

    const paramTipo = urlParams.get('tipo');
    if (paramTipo && filterTipo) {
        filterTipo.value = paramTipo;
    }

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
