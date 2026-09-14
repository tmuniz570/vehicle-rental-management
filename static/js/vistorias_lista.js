let paginaAtual = 1;
let termoBusca = '';
let tipoFiltro = '';
let dataFiltro = '';
let contratoFiltro = '';
let sortCol = 'data';
let sortOrder = 'desc';
let vistoriasCache = [];

async function atualizarBannerEControlesContrato() {
    const banner = document.getElementById('contractContextBanner');
    const badge = document.getElementById('contratoBadge');
    const badgeId = document.getElementById('contratoBadgeId');
    const btnNewInsp = document.getElementById('btnNewInspection');
    const btnNewInspText = document.getElementById('btnNewInspectionText');
    
    if (!contratoFiltro) {
        if (banner) banner.style.display = 'none';
        if (badge) badge.style.display = 'none';
        if (btnNewInsp) btnNewInsp.href = '/vistorias/nova';
        if (btnNewInspText) btnNewInspText.textContent = 'New Inspection';
        return;
    }

    // Show filter badge
    if (badge && badgeId) {
        badgeId.textContent = contratoFiltro;
        badge.style.display = 'inline-flex';
    }

    // Update New Inspection button to pre-fill contract
    if (btnNewInsp) {
        btnNewInsp.href = `/vistorias/nova?contrato_id=${contratoFiltro}`;
    }
    if (btnNewInspText) {
        btnNewInspText.textContent = `New Inspection (#${contratoFiltro})`;
    }

    // Setup Context Banner
    if (banner) {
        banner.style.display = 'flex';
        const bannerContractId = document.getElementById('bannerContractId');
        const btnBackToContract = document.getElementById('btnBackToContract');
        const btnBackContractId = document.getElementById('btnBackContractId');
        const bannerPlateBadge = document.getElementById('bannerPlateBadge');
        const bannerCustomerName = document.getElementById('bannerCustomerName');
        const bannerStatusBadge = document.getElementById('bannerStatusBadge');

        if (bannerContractId) bannerContractId.textContent = contratoFiltro;
        if (btnBackContractId) btnBackContractId.textContent = contratoFiltro;
        if (btnBackToContract) btnBackToContract.href = `/contratos/${contratoFiltro}`;

        // Fetch contract details for rich context
        try {
            const res = await fetch(`/api/contratos/${contratoFiltro}`);
            if (res.ok) {
                const c = await res.json();
                const nomeCliente = c.cliente || c.cliente_nome;
                if (bannerPlateBadge) bannerPlateBadge.textContent = c.placa || '-';
                if (bannerCustomerName) bannerCustomerName.textContent = nomeCliente ? `• ${nomeCliente}` : '';
                if (bannerStatusBadge) {
                    bannerStatusBadge.textContent = c.status || '';
                    const st = (c.status || '').toLowerCase();
                    bannerStatusBadge.className = 'badge ' + (st === 'active' || st === 'ativo' ? 'badge-success' : 'badge-warning');
                }
            }
        } catch (e) {
            console.error("Error fetching contract info for banner:", e);
        }
    }
}

function limparFiltroContrato() {
    contratoFiltro = '';
    paginaAtual = 1;
    if (window.history.replaceState) {
        const url = new URL(window.location);
        url.searchParams.delete('contrato_id');
        url.searchParams.delete('contrato');
        window.history.replaceState({}, document.title, url.pathname + (url.search ? url.search : ''));
    }
    carregarVistorias();
}

async function carregarVistorias() {
    const tbody = document.querySelector('#vistoriasTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    const btnClear = document.getElementById('btnClearFilters');
    
    // Show/hide clear filters button
    if (btnClear) {
        btnClear.style.display = (termoBusca || tipoFiltro || dataFiltro || contratoFiltro) ? 'inline-block' : 'none';
    }
    atualizarBannerEControlesContrato();

    try {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:2rem; color:var(--text-secondary);">Loading inspections...</td></tr>';
        
        const params = new URLSearchParams({
            page: paginaAtual,
            limit: 15,
            search: termoBusca,
            tipo: tipoFiltro,
            data: dataFiltro,
            sort_by: sortCol,
            sort_order: sortOrder
        });
        if (contratoFiltro) {
            params.set('contrato_id', contratoFiltro);
        }

        const res = await fetch(`/api/vistorias?${params.toString()}`);
        const data = await res.json();
        const vistorias = data.itens || [];
        vistoriasCache = vistorias;
        
        if (vistorias.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:2.5rem; color:var(--text-secondary); font-size: 0.95rem;">No inspections found with the selected filters.</td></tr>';
            if (paginationInfo) paginationInfo.textContent = '';
            const btnPrev = document.getElementById('btnPrevPage');
            const btnNext = document.getElementById('btnNextPage');
            if (btnPrev) btnPrev.disabled = true;
            if (btnNext) btnNext.disabled = true;
            return;
        }
        
        tbody.innerHTML = '';
        vistorias.forEach((v, index) => {
            const tr = document.createElement('tr');
            const dataVistoria = new Date(v.data_vistoria).toLocaleString('en-GB');
            
            let tipoBadge = '';
            const tLower = (v.tipo || '').toLowerCase();
            if (tLower === 'check-out' || tLower === 'saída') {
                tipoBadge = '<span class="badge badge-info">Check-out (Collection)</span>';
            } else if (tLower === 'check-in' || tLower === 'entrada') {
                tipoBadge = '<span class="badge badge-warning">Check-in (Return)</span>';
            } else if (tLower === 'incident' || tLower === 'ocorrência') {
                tipoBadge = '<span class="badge badge-danger">Incident</span>';
            } else {
                tipoBadge = `<span class="badge">${escapeHtml(v.tipo)}</span>`;
            }
            
            // Photos count
            const fotosArray = v.foto_url ? v.foto_url.split(',').map(f => f.trim()).filter(Boolean) : [];
            const fotosCount = fotosArray.length;
            const btnVerText = fotosCount > 0 ? `📷 Photos (${fotosCount})` : `View Details`;

            // Observações snippet
            const obsSnippet = v.observacoes 
                ? `<span title="${escapeHtml(v.observacoes)}" style="display:inline-block; max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--text-secondary);">${escapeHtml(v.observacoes)}</span>`
                : '<span style="color:var(--text-secondary); opacity:0.5;">-</span>';

            const staffTag = v.realizado_por_nome ? `<small style="display:block; color:#c084fc; font-size:0.75rem; margin-top:2px;">👤 ${escapeHtml(v.realizado_por_nome)}</small>` : '';

            tr.innerHTML = `
                <td style="font-weight: 500; font-size: 0.9rem; white-space: nowrap;">${dataVistoria}${staffTag}</td>
                <td>
                    <a href="/contratos/${v.id_contrato}" class="link-contrato" title="Open Contract #${v.id_contrato}">
                        Contract #${v.id_contrato} &rarr;
                    </a>
                </td>
                <td class="nowrap"><span class="badge-plate">${escapeHtml(v.placa || '-')}</span></td>
                <td style="font-weight: 500; white-space: nowrap;" title="${escapeHtml(v.cliente || '')}">${escapeHtml(v.cliente || '-')}</td>
                <td>${tipoBadge}</td>
                <td>${obsSnippet}</td>
                <td style="text-align: right; white-space: nowrap;">
                    <button class="btn-action btn-ver-detalhes" data-index="${index}">
                        ${btnVerText}
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Pagination
        if (paginationInfo) {
            paginationInfo.textContent = `Page ${data.pagina_atual} of ${data.paginas || 1} (${data.total} records)`;
        }
        const btnPrev = document.getElementById('btnPrevPage');
        const btnNext = document.getElementById('btnNextPage');
        if (btnPrev) btnPrev.disabled = data.pagina_atual <= 1;
        if (btnNext) btnNext.disabled = data.pagina_atual >= (data.paginas || 1);
        
        // Listeners for View Details / Photos
        document.querySelectorAll('.btn-ver-detalhes').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(btn.getAttribute('data-index'), 10);
                abrirModalVistoria(vistoriasCache[idx]);
            });
        });

        if (typeof setTableSortIndicator === 'function') {
            setTableSortIndicator('vistoriasTable', sortCol, sortOrder);
        }
        
    } catch (e) {
        console.error("Error loading inspections:", e);
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:2rem; color:var(--error);">Failed to load inspections from server.</td></tr>';
    }
}

function abrirModalVistoria(v) {
    if (!v) return;
    const modal = document.getElementById('viewVistoriaModal');
    if (!modal) return;

    const dataVistoria = new Date(v.data_vistoria).toLocaleString('en-GB');
    
    // Title & Badge
    document.getElementById('modalTitle').textContent = `Inspection #${v.id}`;
    const badgeEl = document.getElementById('modalTipoBadge');
    badgeEl.textContent = v.tipo;
    const tLower = (v.tipo || '').toLowerCase();
    badgeEl.className = 'badge ' + (
        tLower === 'check-out' || tLower === 'saída' ? 'badge-info' :
        tLower === 'check-in' || tLower === 'entrada' ? 'badge-warning' :
        tLower === 'incident' || tLower === 'ocorrência' ? 'badge-danger' : ''
    );

    // Fields
    document.getElementById('modalData').textContent = dataVistoria;
    document.getElementById('modalContratoLink').innerHTML = `
        <a href="/contratos/${v.id_contrato}" class="link-contrato" style="font-size:0.9rem;">
            Contract #${v.id_contrato} &rarr;
        </a>
    `;
    document.getElementById('modalPlaca').textContent = v.placa || '-';
    document.getElementById('modalCliente').textContent = v.cliente || '-';
    const elOp = document.getElementById('modalOperador');
    if (elOp) elOp.textContent = v.realizado_por_nome || '-';
    document.getElementById('modalObs').textContent = v.observacoes ? v.observacoes : 'No notes recorded.';

    // Gallery
    const fotosContainer = document.getElementById('modalGaleria');
    fotosContainer.innerHTML = '';
    
    const fotosArray = v.foto_url ? v.foto_url.split(',').map(f => f.trim()).filter(Boolean) : [];
    document.getElementById('modalFotoCount').textContent = fotosArray.length;

    if (fotosArray.length > 0) {
        fotosArray.forEach((url, i) => {
            const item = document.createElement('a');
            item.href = url;
            item.target = '_blank';
            item.className = 'photo-item';
            item.title = `Photo ${i + 1} - Click to open in full resolution`;
            item.innerHTML = `
                <img src="${url}" alt="Inspection Photo ${i + 1}" loading="lazy">
                <span class="photo-zoom-icon">&#x1F50D; Enlarge</span>
            `;
            fotosContainer.appendChild(item);
        });
    } else {
        fotosContainer.innerHTML = '<p style="color:var(--text-secondary); font-size:0.9rem; grid-column: 1 / -1; padding:1rem 0;">No photos attached to this inspection.</p>';
    }

    modal.classList.add('active');
}

function fecharModal() {
    const modal = document.getElementById('viewVistoriaModal');
    if (modal) modal.classList.remove('active');
}

document.addEventListener('DOMContentLoaded', () => {
    // Check URL parameters for contract filter
    const urlParams = new URLSearchParams(window.location.search);
    const contratoParam = urlParams.get('contrato_id') || urlParams.get('contrato');
    if (contratoParam) {
        contratoFiltro = contratoParam;
    }

    carregarVistorias();
    
    // Pagination
    const btnPrev = document.getElementById('btnPrevPage');
    const btnNext = document.getElementById('btnNextPage');
    if (btnPrev) {
        btnPrev.addEventListener('click', () => {
            if (paginaAtual > 1) {
                paginaAtual--;
                carregarVistorias();
            }
        });
    }
    if (btnNext) {
        btnNext.addEventListener('click', () => {
            paginaAtual++;
            carregarVistorias();
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
                carregarVistorias();
            }, 300);
        });
    }

    // Filter by type
    const filterTipo = document.getElementById('filterTipo');
    if (filterTipo) {
        filterTipo.addEventListener('change', (e) => {
            tipoFiltro = e.target.value;
            paginaAtual = 1;
            carregarVistorias();
        });
    }

    // Filter by date
    const filterDate = document.getElementById('filterDate');
    if (filterDate) {
        filterDate.addEventListener('change', (e) => {
            dataFiltro = e.target.value;
            paginaAtual = 1;
            carregarVistorias();
        });
    }

    // Remove Contract Filter Badge Button
    const btnRemoveContrato = document.getElementById('btnRemoveContratoFiltro');
    if (btnRemoveContrato) {
        btnRemoveContrato.addEventListener('click', limparFiltroContrato);
    }

    // Exit Contract Filter Button on Banner
    const btnExitContract = document.getElementById('btnExitContractFilter');
    if (btnExitContract) {
        btnExitContract.addEventListener('click', limparFiltroContrato);
    }

    // Clear Filters Button
    const btnClear = document.getElementById('btnClearFilters');
    if (btnClear) {
        btnClear.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            if (filterTipo) filterTipo.value = '';
            if (filterDate) filterDate.value = '';
            termoBusca = '';
            tipoFiltro = '';
            dataFiltro = '';
            contratoFiltro = '';
            sortCol = 'data';
            sortOrder = 'desc';
            paginaAtual = 1;
            if (window.history.replaceState) {
                const url = new URL(window.location);
                url.searchParams.delete('contrato_id');
                url.searchParams.delete('contrato');
                window.history.replaceState({}, document.title, url.pathname + (url.search ? url.search : ''));
            }
            carregarVistorias();
        });
    }

    // Enable Server-Side Table Sorting
    if (typeof enableTableSorting === 'function') {
        enableTableSorting('vistoriasTable', (field, order) => {
            sortCol = field;
            sortOrder = order;
            paginaAtual = 1;
            carregarVistorias();
        });
    }

    // Close Modal
    const modal = document.getElementById('viewVistoriaModal');
    const closeBtn = document.getElementById('closeViewModal');
    if (closeBtn) closeBtn.addEventListener('click', fecharModal);
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) fecharModal();
        });
    }
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') fecharModal();
    });
});


