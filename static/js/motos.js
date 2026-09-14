let paginaAtual = 1;
let termoBusca = '';
let sortCol = 'placa';
let sortOrder = 'asc';

function formatExpiryBadge(dateStr) {
    if (!dateStr) return '<span style="color:var(--text-secondary); opacity:0.6;">-</span>';
    
    const parts = dateStr.split('-');
    if (parts.length !== 3) return dateStr;
    const due = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const formattedDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
    const diffDays = Math.ceil((due - today) / (1000 * 60 * 60 * 24));

    if (diffDays < 0) {
        return `<span class="badge badge-danger" title="Expired ${Math.abs(diffDays)} days ago">⚠️ Expired (${formattedDate})</span>`;
    } else if (diffDays <= 30) {
        return `<span class="badge badge-warning" title="Expiring in ${diffDays} days">⏳ ${formattedDate}</span>`;
    } else {
        return `<span style="color:#4ade80; font-weight:600; font-size:0.85rem; display:inline-flex; align-items:center; gap:3px;">✓ ${formattedDate}</span>`;
    }
}

async function carregarMotos() {
    const tbody = document.querySelector('#motosTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    
    try {
        const res = await fetch(`/api/motos?page=${paginaAtual}&limit=20&search=${encodeURIComponent(termoBusca)}&sort_by=${encodeURIComponent(sortCol)}&sort_order=${encodeURIComponent(sortOrder)}`);
        const data = await res.json();
        const motos = data.itens || [];
        
        if (motos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No motorbikes found.</td></tr>';
            if(paginationInfo) paginationInfo.textContent = '';
            return;
        }
        
        tbody.innerHTML = '';
        motos.forEach(m => {
            const tr = document.createElement('tr');
            
            let statusBadge = '';
            const st = (m.status || '').toLowerCase();
            if (st === 'available' || st === 'disponível') statusBadge = '<span class="badge badge-success">Available</span>';
            else if (st === 'maintenance' || st === 'manutenção') statusBadge = '<span class="badge badge-warning">Maintenance</span>';
            else if (st === 'rented' || st === 'alugada') statusBadge = '<span class="badge badge-info">Rented</span>';
            else statusBadge = `<span class="badge badge-danger">${escapeHtml(m.status)}</span>`;
            
            const btnEdit = `<button class="btn-edit" data-placa="${escapeHtml(m.placa)}" data-modelo="${escapeHtml(m.modelo)}" data-cor="${escapeHtml(m.cor)}" data-status="${escapeHtml(m.status)}" data-mot="${m.vencimento_mot || ''}" data-tax="${m.vencimento_tax || ''}" style="background:transparent; color:var(--accent); border:1px solid var(--accent); padding:10px 15px; min-width:60px; min-height:44px; border-radius:6px; cursor:pointer;">Edit</button>`;
            
            const motBadge = formatExpiryBadge(m.vencimento_mot);
            const taxBadge = formatExpiryBadge(m.vencimento_tax);

            tr.innerHTML = `
                <td class="nowrap"><span class="badge-plate">${escapeHtml(m.placa)}</span></td>
                <td>${escapeHtml(m.modelo)}</td>
                <td>${escapeHtml(m.cor)}</td>
                <td data-sort="${m.vencimento_tax || ''}" class="nowrap">${taxBadge}</td>
                <td data-sort="${m.vencimento_mot || ''}" class="nowrap">${motBadge}</td>
                <td>${statusBadge}</td>
                <td>${btnEdit}</td>
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
        
        // Setup Edit Modal
        const modal = document.getElementById('editMotoModal');
        document.querySelectorAll('.btn-edit').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const placa = e.target.getAttribute('data-placa');
                document.getElementById('edit_placa').value = placa;
                document.getElementById('display_placa').textContent = placa;
                document.getElementById('edit_modelo').value = e.target.getAttribute('data-modelo');
                document.getElementById('edit_cor').value = e.target.getAttribute('data-cor');
                document.getElementById('edit_status').value = e.target.getAttribute('data-status');
                document.getElementById('edit_mot').value = e.target.getAttribute('data-mot') || '';
                document.getElementById('edit_tax').value = e.target.getAttribute('data-tax') || '';
                modal.style.display = 'flex';
            });
        });
        if (typeof setTableSortIndicator === 'function') {
            setTableSortIndicator('motosTable', sortCol, sortOrder);
        }
        
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--error);">Failed to load motorbikes.</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (typeof enableTableSorting === 'function') {
        enableTableSorting('motosTable', (field, order) => {
            sortCol = field;
            sortOrder = order;
            paginaAtual = 1;
            carregarMotos();
        });
    }

    carregarMotos();
    
    // Pagination Buttons
    const btnPrev = document.getElementById('btnPrevPage');
    const btnNext = document.getElementById('btnNextPage');
    if(btnPrev) btnPrev.addEventListener('click', () => { paginaAtual--; carregarMotos(); });
    if(btnNext) btnNext.addEventListener('click', () => { paginaAtual++; carregarMotos(); });

    // Search logic
    const searchInput = document.getElementById('searchInput');
    let timeoutId;
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                termoBusca = e.target.value;
                paginaAtual = 1;
                carregarMotos();
            }, 500);
        });
    }

    const modal = document.getElementById('editMotoModal');
    const closeBtn = document.getElementById('closeMotoModal');
    if(closeBtn) closeBtn.addEventListener('click', () => { modal.style.display = 'none'; });

    document.getElementById('editMotoForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const placa = document.getElementById('edit_placa').value;
        const data = {
            modelo: document.getElementById('edit_modelo').value,
            cor: document.getElementById('edit_cor').value,
            status: document.getElementById('edit_status').value,
            vencimento_mot: document.getElementById('edit_mot').value || null,
            vencimento_tax: document.getElementById('edit_tax').value || null
        };
        
        try {
            const response = await fetch(`/api/motos/${placa}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (response.ok) {
                modal.style.display = 'none';
                carregarMotos();
            } else {
                const res = await response.json();
                alert(res.message || res.mensagem || res.erro || res.error || 'Failed to update motorbike');
            }
        } catch(err) {
            alert('Connection error');
        }
    });
});
