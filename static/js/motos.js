let paginaAtual = 1;
let termoBusca = '';
let statusFiltro = '';
let v5cFiltro = '';
let sortCol = 'placa';
let sortOrder = 'asc';
let motosCache = {};

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

// Hook called when V5C or Trackers are updated inside the shared modal
window.onMotoModalUpdated = function() {
    carregarMotos();
};

// Load Motorbikes Table
async function carregarMotos() {
    const tbody = document.querySelector('#motosTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    if (!tbody) return;
    
    try {
        const queryParams = new URLSearchParams({
            page: paginaAtual,
            limit: 20,
            search: termoBusca,
            sort_by: sortCol,
            sort_order: sortOrder
        });
        if (statusFiltro) queryParams.set('status', statusFiltro);
        if (v5cFiltro) queryParams.set('v5c', v5cFiltro);

        const res = await fetch(`/api/motos?${queryParams.toString()}`);
        const data = await res.json();
        const motos = data.itens || [];
        
        if (motos.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding: 2rem; color: var(--text-secondary);">No motorbikes found matching criteria.</td></tr>';
            if(paginationInfo) paginationInfo.textContent = '';
            return;
        }
        
        // Cache motos for fast modal population
        motosCache = {};
        motos.forEach(m => { motosCache[m.placa] = m; });
        
        tbody.innerHTML = '';
        motos.forEach(m => {
            const tr = document.createElement('tr');
            
            let statusBadge = '';
            const st = (m.status || '').toLowerCase();
            const isPound = (st === 'pound');
            const isSold = (st === 'sold' || st === 'vendida');

            if (st === 'available' || st === 'disponível') {
                statusBadge = '<span class="badge badge-success">Available</span>';
            } else if (st === 'maintenance' || st === 'manutenção') {
                statusBadge = '<span class="badge badge-warning">Maintenance</span>';
            } else if (st === 'rented' || st === 'alugada') {
                statusBadge = '<span class="badge badge-info">Rented</span>';
            } else if (isPound) {
                statusBadge = '<span class="badge" style="background:rgba(239,68,68,0.18); color:#fca5a5; border:1px solid rgba(239,68,68,0.4); font-weight:700;" title="Out of operation (Impounded / Off-road)">🏛️ Pound</span>';
            } else if (isSold) {
                statusBadge = '<span class="badge" style="background:rgba(168,85,247,0.2); color:#c084fc; border:1px solid rgba(168,85,247,0.4);">Sold</span>';
            } else {
                statusBadge = `<span class="badge badge-danger">${escapeHtml(m.status)}</span>`;
            }
            
            const milhagemFormatada = Number(m.milhagem_atual || 0).toLocaleString('en-GB') + ' mi';
            
            // Tax and MOT badges - exempt from alerts if in Pound
            let taxBadge = '';
            let motBadge = '';
            if (isPound) {
                taxBadge = `<span class="badge" style="background:rgba(148,163,184,0.12); color:#94a3b8; border:1px solid rgba(148,163,184,0.25); font-size:0.75rem;" title="Out of operation - exempt from Road Tax alerts">Exempt (Pound)</span>`;
                motBadge = `<span class="badge" style="background:rgba(148,163,184,0.12); color:#94a3b8; border:1px solid rgba(148,163,184,0.25); font-size:0.75rem;" title="Out of operation - exempt from MOT alerts">Exempt (Pound)</span>`;
            } else {
                taxBadge = m.tax_sorn
                    ? `<span class="badge" style="background: rgba(168,85,247,0.15); color: #c084fc; border: 1px solid rgba(168,85,247,0.35); font-weight: 700; font-size: 0.78rem;" title="Statutory Off Road Notification (SORN)">🛡️ SORN</span>`
                    : formatExpiryBadge(m.vencimento_tax);
                motBadge = formatExpiryBadge(m.vencimento_mot);
            }

            // V5C and Tracker Badges
            const v5cCount = m.v5c_count || 0;
            const trackersCount = m.trackers_count || 0;
            
            let v5cBadge = '';
            if (v5cCount > 0) {
                v5cBadge = `<span class="badge" style="background: rgba(6,182,212,0.15); color: #22d3ee; border: 1px solid rgba(6,182,212,0.3); font-size:0.75rem; cursor:pointer;" title="View ${v5cCount} V5C document(s)" onclick="abrirModalMoto('${escapeHtml(m.placa)}', 'tabV5C', motosCache['${escapeHtml(m.placa)}'])">📄 ${v5cCount} Doc${v5cCount > 1 ? 's' : ''}</span>`;
            } else if (isSold) {
                v5cBadge = `<span style="opacity:0.4; font-size:0.75rem; color:var(--text-secondary);">-</span>`;
            } else {
                v5cBadge = `<span class="badge" style="background: rgba(239,68,68,0.16); color: #fca5a5; border: 1px solid rgba(239,68,68,0.38); font-size:0.75rem; cursor:pointer; font-weight:700;" title="⚠️ Missing V5C Logbook! Click to attach" onclick="abrirModalMoto('${escapeHtml(m.placa)}', 'tabV5C', motosCache['${escapeHtml(m.placa)}'])">⚠️ No V5C</span>`;
            }

            const trackerBadge = trackersCount > 0
                ? `<span class="badge" style="background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); font-size:0.75rem; cursor:pointer;" title="View ${trackersCount} GPS tracker(s)" onclick="abrirModalMoto('${escapeHtml(m.placa)}', 'tabTrackers', motosCache['${escapeHtml(m.placa)}'])">📡 ${trackersCount} GPS</span>`
                : `<span style="opacity:0.4; font-size:0.75rem; color:var(--text-secondary); cursor:pointer; text-decoration: underline;" title="Register tracker" onclick="abrirModalMoto('${escapeHtml(m.placa)}', 'tabTrackers', motosCache['${escapeHtml(m.placa)}'])">+ Tracker</span>`;

            const btnEdit = `<button type="button" class="btn-edit" onclick="abrirModalMoto('${escapeHtml(m.placa)}', 'tabInfo', motosCache['${escapeHtml(m.placa)}'])" data-placa="${escapeHtml(m.placa)}" style="background:transparent; color:var(--accent); border:1px solid var(--accent); padding:8px 14px; min-width:64px; min-height:36px; border-radius:6px; cursor:pointer; font-weight:600;">Manage</button>`;

            tr.innerHTML = `
                <td class="nowrap"><span class="badge-plate" style="cursor:pointer;" onclick="abrirModalMoto('${escapeHtml(m.placa)}', 'tabInfo', motosCache['${escapeHtml(m.placa)}'])">${escapeHtml(m.placa)}</span></td>
                <td>${escapeHtml(m.modelo)}</td>
                <td>${escapeHtml(m.cor)}</td>
                <td data-sort="${m.milhagem_atual || 0}" style="font-weight: 600; color: #f8fafc;"><span style="color: var(--accent); font-weight:700;">${milhagemFormatada}</span></td>
                <td data-sort="${isPound ? 'POUND' : (m.tax_sorn ? 'SORN' : (m.vencimento_tax || ''))}" class="nowrap">${taxBadge}</td>
                <td data-sort="${isPound ? 'POUND' : (m.vencimento_mot || '')}" class="nowrap">${motBadge}</td>
                <td class="nowrap">
                    <div style="display: inline-flex; gap: 6px; align-items: center; min-height: 36px;">
                        ${v5cBadge}
                        ${trackerBadge}
                    </div>
                </td>
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

        if (typeof setTableSortIndicator === 'function') {
            setTableSortIndicator('motosTable', sortCol, sortOrder);
        }
        
    } catch(e) {
        console.error('Error loading motorbikes:', e);
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--error);">Failed to load motorbikes.</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Read URL query parameters
    const urlParams = new URLSearchParams(window.location.search);
    const initialStatus = urlParams.get('status');
    const initialV5C = urlParams.get('v5c');
    const initialSearch = urlParams.get('search');

    if (initialV5C && ['missing', 'none', 'sem', '0'].includes(initialV5C.toLowerCase())) {
        v5cFiltro = 'missing';
        statusFiltro = '';
        const sf = document.getElementById('statusFilter');
        if (sf) sf.value = 'missing_v5c';
    } else if (initialStatus) {
        statusFiltro = initialStatus;
        v5cFiltro = '';
        const sf = document.getElementById('statusFilter');
        if (sf) sf.value = initialStatus;
    }

    if (initialSearch) {
        termoBusca = initialSearch;
        const si = document.getElementById('searchInput');
        if (si) si.value = initialSearch;
    }

    if (typeof enableTableSorting === 'function') {
        enableTableSorting('motosTable', (field, order) => {
            sortCol = field;
            sortOrder = order;
            paginaAtual = 1;
            carregarMotos();
        });
    }

    // Status / Alert Filter Dropdown
    const statusFilterSelect = document.getElementById('statusFilter');
    if (statusFilterSelect) {
        statusFilterSelect.addEventListener('change', (e) => {
            const val = e.target.value;
            if (val === 'missing_v5c') {
                statusFiltro = '';
                v5cFiltro = 'missing';
            } else {
                statusFiltro = val;
                v5cFiltro = '';
            }
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
            }, 450);
        });
    }
});
