let paginaAtual = 1;
let termoBusca = '';

async function carregarMotos() {
    const tbody = document.querySelector('#motosTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    
    try {
        const res = await fetch(`/api/motos?page=${paginaAtual}&limit=20&search=${encodeURIComponent(termoBusca)}`);
        const data = await res.json();
        const motos = data.itens || [];
        
        if (motos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">No motorbikes found.</td></tr>';
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
            else statusBadge = `<span class="badge badge-danger">${m.status}</span>`;
            
            const btnEdit = `<button class="btn-edit" data-placa="${m.placa}" data-modelo="${m.modelo}" data-cor="${m.cor}" data-status="${m.status}" style="background:transparent; color:var(--accent); border:1px solid var(--accent); padding:10px 15px; min-width:60px; min-height:44px; border-radius:6px; cursor:pointer;">Edit</button>`;
            
            tr.innerHTML = `
                <td style="font-weight:600;">${m.placa}</td>
                <td>${m.modelo}</td>
                <td>${m.cor}</td>
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
                modal.style.display = 'flex';
            });
        });
        if (typeof enableTableSorting === 'function') {
            enableTableSorting('motosTable');
        }
        
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--error);">Failed to load motorbikes.</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
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
            status: document.getElementById('edit_status').value
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
