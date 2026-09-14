let paginaAtual = 1;
let termoBusca = '';
let sortCol = 'id';
let sortOrder = 'desc';

async function carregarContratos() {
    const tbody = document.querySelector('#contratosTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    
    try {
        const filterStatus = document.getElementById('filterStatus');
        const statusVal = filterStatus ? filterStatus.value : 'open';
        
        let url = `/api/contratos?page=${paginaAtual}&limit=20&search=${encodeURIComponent(termoBusca)}&sort_by=${encodeURIComponent(sortCol)}&sort_order=${encodeURIComponent(sortOrder)}`;
        if (statusVal === 'open') {
            url += '&nao_finalizados=true';
        } else if (statusVal !== 'all') {
            url += `&status=${encodeURIComponent(statusVal)}`;
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
            const dataDevolucao = c.data_devolucao ? new Date(c.data_devolucao).toLocaleDateString('en-GB') : '-';
            const valorFmt = c.valor_aluguel_semanal ? new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' }).format(c.valor_aluguel_semanal) : '-';
            const diaVenc = c.dia_pagamento_semanal !== undefined && c.dia_pagamento_semanal !== null ? diasSemana[c.dia_pagamento_semanal] : '-';
            
            let statusBadge = '';
            if (c.status === 'Active' || c.status === 'Ativo') {
                statusBadge = '<span class="badge badge-success">Active</span>';
            } else if (c.status === 'Deposit_Hold' || c.status === 'Quarentena_Deposito') {
                statusBadge = '<span class="badge badge-warning">Deposit Hold</span>';
            } else if (c.status === 'Completed' || c.status === 'Finalizado') {
                statusBadge = '<span class="badge">Completed</span>';
            } else {
                statusBadge = `<span class="badge">${c.status}</span>`;
            }
            
            const nomeCliente = c.cliente_nome || '-';
            
            tr.innerHTML = `
                <td>#${c.id}</td>
                <td style="font-weight:600; white-space: nowrap;" title="${nomeCliente}">${nomeCliente}</td>
                <td class="nowrap"><span class="badge-plate">${c.placa}</span></td>
                <td>${dataRetirada}</td>
                <td>${diaVenc}</td>
                <td>${valorFmt}</td>
                <td>${dataDevolucao}</td>
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
    if (paramStatus && filterStatus) {
        if (paramStatus.toLowerCase() === 'deposit_hold' || paramStatus.toLowerCase() === 'quarentena') {
            filterStatus.value = 'Deposit_Hold';
        } else if (paramStatus.toLowerCase() === 'active') {
            filterStatus.value = 'Active';
        } else if (paramStatus.toLowerCase() === 'completed') {
            filterStatus.value = 'Completed';
        }
    }

    if (typeof enableTableSorting === 'function') {
        enableTableSorting('contratosTable', (field, order) => {
            sortCol = field;
            sortOrder = order;
            paginaAtual = 1;
            carregarContratos();
        });
    }

    carregarContratos();
    
    // Pagination Buttons
    const btnPrev = document.getElementById('btnPrevPage');
    const btnNext = document.getElementById('btnNextPage');
    if(btnPrev) btnPrev.addEventListener('click', () => { paginaAtual--; carregarContratos(); });
    if(btnNext) btnNext.addEventListener('click', () => { paginaAtual++; carregarContratos(); });

    // Search logic with debounce
    const searchInput = document.getElementById('searchInput');
    let timeoutId;
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                termoBusca = e.target.value;
                paginaAtual = 1;
                carregarContratos();
            }, 500);
        });
    }

    if (filterStatus) {
        filterStatus.addEventListener('change', () => {
            paginaAtual = 1;
            carregarContratos();
        });
    }
});

