let paginaAtual = 1;
let termoBusca = '';
let statusFiltro = 'operational';
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

// Quick DVLA check helper: copies plate to clipboard and provides subtle visual feedback
window.copiarPlacaDVLA = function(event, placa) {
    if (event) {
        event.stopPropagation();
    }
    if (!placa) {
        placa = document.getElementById('edit_placa')?.value || document.getElementById('placa')?.value || '';
    }
    if (!placa) return;
    placa = placa.trim().toUpperCase();
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(placa).then(() => {
            const btn = event ? (event.currentTarget || event.target) : null;
            if (btn) {
                const origText = btn.innerHTML;
                btn.innerHTML = '✓ Copied!';
                btn.style.color = '#4ade80';
                btn.style.borderColor = '#4ade80';
                setTimeout(() => {
                    btn.innerHTML = origText;
                    btn.style.color = '';
                    btn.style.borderColor = '';
                }, 2000);
            }
        }).catch(() => {});
    }
};

// Hook called when V5C or Trackers are updated inside the shared modal
window.onMotoModalUpdated = function() {
    carregarMotos();
};

function atualizarKpiCards(kpis) {
    if (!kpis) return;
    const elOp = document.getElementById('kpiVal_operational');
    const elAv = document.getElementById('kpiVal_available');
    const elRe = document.getElementById('kpiVal_rented');
    const elMa = document.getElementById('kpiVal_maintenance');
    const elV5 = document.getElementById('kpiVal_missing_v5c');
    const elWa = document.getElementById('kpiVal_tax_mot_warnings');

    if (elOp) elOp.textContent = kpis.operational !== undefined ? kpis.operational : '-';
    if (elAv) elAv.textContent = kpis.available !== undefined ? kpis.available : '-';
    if (elRe) elRe.textContent = kpis.rented !== undefined ? kpis.rented : '-';
    if (elMa) elMa.textContent = kpis.maintenance !== undefined ? kpis.maintenance : '-';
    if (elV5) elV5.textContent = kpis.missing_v5c !== undefined ? kpis.missing_v5c : '-';
    if (elWa) elWa.textContent = kpis.tax_mot_warnings !== undefined ? kpis.tax_mot_warnings : '-';

    sincronizarKpiCardAtivo();
}

function sincronizarKpiCardAtivo() {
    const currentFilter = v5cFiltro === 'missing' ? 'missing_v5c' : (statusFiltro || 'operational');
    document.querySelectorAll('.kpi-card').forEach(card => {
        if (card.dataset.filter === currentFilter) {
            card.classList.add('active');
        } else {
            card.classList.remove('active');
        }
    });
}

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
        
        // Update Fleet KPIs strip
        if (data.kpis) {
            atualizarKpiCards(data.kpis);
        }

        if (motos.length === 0) {
            const hasFilter = statusFiltro && statusFiltro !== 'all';
            const clearFilterAction = hasFilter ? `
                <div style="margin-top: 12px;">
                    <button type="button" class="btn-secondary" onclick="document.getElementById('statusFilter').value='all'; document.getElementById('statusFilter').dispatchEvent(new Event('change'));" style="padding: 6px 14px; font-size: 0.82rem; border-radius: 8px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
                        🔍 Search All Fleet (incl. Sold & Pound)
                    </button>
                </div>
            ` : '';
            tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; padding: 2.5rem 1rem; color: var(--text-secondary);"><div style="margin-bottom: 4px;">No motorbikes found matching criteria.</div>${clearFilterAction}</td></tr>`;
            if(paginationInfo) paginationInfo.textContent = '';
            return;
        }
        
        // Cache motos for fast modal population
        motosCache = {};
        motos.forEach(m => { motosCache[m.placa] = m; });
        
        tbody.innerHTML = '';
        motos.forEach(m => {
            const tr = document.createElement('tr');
            
            const st = (m.status || '').toLowerCase();
            const isPound = (st === 'pound');
            const isSold = (st === 'sold' || st === 'vendida');

            // 1. Status Column with interactive Contract link and Hirer info
            let statusHtml = '';
            if (st === 'rented' || st === 'alugada') {
                if (m.active_contract) {
                    const c = m.active_contract;
                    let waBtn = '';
                    if (c.cliente_telefone) {
                        const phoneClean = (typeof formatWhatsAppNumber === 'function')
                            ? formatWhatsAppNumber(c.cliente_telefone)
                            : (() => {
                                let w = c.cliente_telefone.replace(/\D/g, '');
                                if (w.startsWith('0')) w = '44' + w.substring(1);
                                return w;
                            })();
                        const waMsg = encodeURIComponent(`Hello ${c.cliente_nome || ''}, this is FF Motors regarding motorbike ${m.placa || ''}: `);
                        waBtn = phoneClean ? `<a href="https://wa.me/${phoneClean}?text=${waMsg}" target="_blank" rel="noopener noreferrer" title="WhatsApp ${escapeHtml(c.cliente_telefone)}" style="text-decoration:none; margin-left:4px; font-size:0.85rem;" onclick="event.stopPropagation();">💬</a>` : '';
                    }
                    statusHtml = `
                        <div>
                            <a href="/contratos/${c.id}" class="badge badge-info" style="text-decoration:none; display:inline-flex; align-items:center; gap:4px; font-weight:700;" title="View Active Contract #${c.id}">
                                Rented #${c.id} ↗
                            </a>
                            <div style="font-size:0.75rem; margin-top:4px; display:flex; align-items:center; color:#cbd5e1;">
                                <span style="font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:130px;" title="Current Hirer: ${escapeHtml(c.cliente_nome)}">
                                    👤 ${escapeHtml(c.cliente_nome)}
                                </span>
                                ${waBtn}
                            </div>
                        </div>
                    `;
                } else {
                    statusHtml = '<span class="badge badge-info">Rented</span>';
                }
            } else if (isSold) {
                const c = m.active_contract || m.last_contract;
                const isFinancedActive = !!m.active_contract;
                if (c) {
                    const badgeText = isFinancedActive ? `Financed #${c.id} ↗` : `Sold #${c.id} ↗`;
                    const badgeTitle = isFinancedActive ? `View Active Financed Contract #${c.id}` : `View Completed Sale Contract #${c.id}`;
                    let waBtn = '';
                    if (isFinancedActive && c.cliente_telefone) {
                        const phoneClean = (typeof formatWhatsAppNumber === 'function')
                            ? formatWhatsAppNumber(c.cliente_telefone)
                            : (() => {
                                let w = c.cliente_telefone.replace(/\D/g, '');
                                if (w.startsWith('0')) w = '44' + w.substring(1);
                                return w;
                            })();
                        const waMsg = encodeURIComponent(`Hello ${c.cliente_nome || ''}, this is FF Motors regarding motorbike ${m.placa || ''}: `);
                        waBtn = phoneClean ? `<a href="https://wa.me/${phoneClean}?text=${waMsg}" target="_blank" rel="noopener noreferrer" title="WhatsApp ${escapeHtml(c.cliente_telefone)}" style="text-decoration:none; margin-left:4px; font-size:0.85rem;" onclick="event.stopPropagation();">💬</a>` : '';
                    }
                    statusHtml = `
                        <div>
                            <a href="/contratos/${c.id}" class="badge" style="background:${isFinancedActive ? 'rgba(168,85,247,0.2)' : 'rgba(100,116,139,0.2)'}; color:${isFinancedActive ? '#c084fc' : '#94a3b8'}; border:1px solid ${isFinancedActive ? 'rgba(168,85,247,0.4)' : 'rgba(100,116,139,0.4)'}; text-decoration:none; display:inline-flex; align-items:center; gap:4px; font-weight:700;" title="${badgeTitle}">
                                ${badgeText}
                            </a>
                            ${c.cliente_nome ? `
                            <div style="font-size:0.75rem; margin-top:4px; display:flex; align-items:center; color:#cbd5e1;">
                                <span style="font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:130px;" title="${isFinancedActive ? 'Hirer / Buyer' : 'Buyer'}: ${escapeHtml(c.cliente_nome)}">
                                    👤 ${escapeHtml(c.cliente_nome)}
                                </span>
                                ${waBtn}
                            </div>` : ''}
                        </div>
                    `;
                } else {
                    statusHtml = '<span class="badge" style="background:rgba(100,116,139,0.2); color:#94a3b8; border:1px solid rgba(100,116,139,0.4);">Sold</span>';
                }
            } else if (st === 'available' || st === 'disponível') {
                if (m.last_contract) {
                    const c = m.last_contract;
                    statusHtml = `
                        <div>
                            <span class="badge badge-success">Available</span>
                            <div style="font-size:0.72rem; margin-top:3px; opacity:0.8;">
                                <a href="/contratos/${c.id}" style="color:var(--text-secondary); text-decoration:none;" title="Previous Contract #${c.id} (${escapeHtml(c.cliente_nome)})">
                                    Last: #${c.id} ↗
                                </a>
                            </div>
                        </div>
                    `;
                } else {
                    statusHtml = '<span class="badge badge-success">Available</span>';
                }
            } else if (st === 'maintenance' || st === 'manutenção') {
                if (m.last_contract) {
                    const c = m.last_contract;
                    statusHtml = `
                        <div>
                            <span class="badge badge-warning">Maintenance</span>
                            <div style="font-size:0.72rem; margin-top:3px; opacity:0.8;">
                                <a href="/contratos/${c.id}" style="color:var(--text-secondary); text-decoration:none;" title="Previous Contract #${c.id} (${escapeHtml(c.cliente_nome)})">
                                    Last: #${c.id} ↗
                                </a>
                            </div>
                        </div>
                    `;
                } else {
                    statusHtml = '<span class="badge badge-warning">Maintenance</span>';
                }
            } else if (isPound) {
                statusHtml = '<span class="badge" style="background:rgba(239,68,68,0.18); color:#fca5a5; border:1px solid rgba(239,68,68,0.4); font-weight:700;" title="Out of operation (Impounded / Off-road)">🏛️ Pound</span>';
            } else {
                statusHtml = `<span class="badge badge-danger">${escapeHtml(m.status)}</span>`;
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
            } else {
                v5cBadge = `<span class="badge" style="background: rgba(239,68,68,0.16); color: #fca5a5; border: 1px solid rgba(239,68,68,0.38); font-size:0.75rem; cursor:pointer; font-weight:700;" title="⚠️ Missing V5C Logbook! Click to attach" onclick="abrirModalMoto('${escapeHtml(m.placa)}', 'tabV5C', motosCache['${escapeHtml(m.placa)}'])">⚠️ No V5C</span>`;
            }

            const trackerBadge = trackersCount > 0
                ? `<span class="badge" style="background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3); font-size:0.75rem; cursor:pointer;" title="View ${trackersCount} GPS tracker(s)" onclick="abrirModalMoto('${escapeHtml(m.placa)}', 'tabTrackers', motosCache['${escapeHtml(m.placa)}'])">📡 ${trackersCount} GPS</span>`
                : `<span style="opacity:0.4; font-size:0.75rem; color:var(--text-secondary); cursor:pointer; text-decoration: underline;" title="Register tracker" onclick="abrirModalMoto('${escapeHtml(m.placa)}', 'tabTrackers', motosCache['${escapeHtml(m.placa)}'])">+ Tracker</span>`;

            // Actions Column: compact "+ Deal" for Available bikes and "Manage"
            let actionsHtml = '';
            if (st === 'available' || st === 'disponível') {
                actionsHtml = `
                    <div style="display:inline-flex; gap:3px; align-items:center;">
                        <a href="/contratos/novo?moto_placa=${encodeURIComponent(m.placa)}" class="btn-primary" style="padding:3px 7px; font-size:0.72rem; text-decoration:none; display:inline-flex; align-items:center; gap:2px; border-radius:5px; background:var(--accent); color:#fff; font-weight:700; white-space:nowrap;" title="Create new agreement (Rental, Sale, Finance) for ${escapeHtml(m.placa)}">+ Deal</a>
                        <button type="button" class="btn-edit" onclick="abrirModalMoto('${escapeHtml(m.placa)}', 'tabInfo', motosCache['${escapeHtml(m.placa)}'])" data-placa="${escapeHtml(m.placa)}" style="background:transparent; color:var(--text-secondary); border:1px solid rgba(255,255,255,0.15); padding:3px 7px; border-radius:5px; cursor:pointer; font-weight:600; font-size:0.72rem;">Manage</button>
                    </div>
                `;
            } else {
                actionsHtml = `
                    <button type="button" class="btn-edit" onclick="abrirModalMoto('${escapeHtml(m.placa)}', 'tabInfo', motosCache['${escapeHtml(m.placa)}'])" data-placa="${escapeHtml(m.placa)}" style="background:transparent; color:var(--accent); border:1px solid var(--accent); padding:3px 10px; min-height:26px; border-radius:5px; cursor:pointer; font-weight:600; font-size:0.75rem;">Manage</button>
                `;
            }

            // Plate with DVLA check button stacked vertically underneath to prevent horizontal stretching
            const plateHtml = `
                <div style="display:flex; flex-direction:column; align-items:flex-start; gap:2px;">
                    <span class="badge-plate" style="cursor:pointer;" onclick="abrirModalMoto('${escapeHtml(m.placa)}', 'tabInfo', motosCache['${escapeHtml(m.placa)}'])">${escapeHtml(m.placa)}</span>
                    <a href="https://www.check-mot.service.gov.uk/" target="_blank" rel="noopener noreferrer" class="dvla-btn" onclick="copiarPlacaDVLA(event, '${escapeHtml(m.placa)}')" title="Check MOT & Tax on GOV.UK (copies plate to clipboard)">DVLA ↗</a>
                </div>
            `;

            tr.innerHTML = `
                <td class="nowrap">${plateHtml}</td>
                <td>${escapeHtml(m.modelo)}</td>
                <td>${escapeHtml(m.cor || '-')}</td>
                <td data-sort="${m.milhagem_atual || 0}" style="font-weight: 600; color: #f8fafc;"><span style="color: var(--accent); font-weight:700;">${milhagemFormatada}</span></td>
                <td data-sort="${isPound ? 'POUND' : (m.tax_sorn ? 'SORN' : (m.vencimento_tax || ''))}" class="nowrap">${taxBadge}</td>
                <td data-sort="${isPound ? 'POUND' : (m.vencimento_mot || '')}" class="nowrap">${motBadge}</td>
                <td class="nowrap">
                    <div style="display: inline-flex; gap: 4px; align-items: center; min-height: 28px;">
                        ${v5cBadge}
                        ${trackerBadge}
                    </div>
                </td>
                <td>${statusHtml}</td>
                <td>${actionsHtml}</td>
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
        tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--error); padding:2rem;">Failed to load motorbikes.</td></tr>';
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
        if (initialStatus.toLowerCase() === 'all' || initialStatus === '') {
            statusFiltro = 'all';
            v5cFiltro = '';
            const sf = document.getElementById('statusFilter');
            if (sf) sf.value = 'all';
        } else {
            statusFiltro = initialStatus;
            v5cFiltro = '';
            const sf = document.getElementById('statusFilter');
            if (sf) sf.value = initialStatus;
        }
    } else if (initialSearch) {
        // When searching for a specific motorbike or plate, search across all statuses (including Sold and Pound)
        statusFiltro = 'all';
        v5cFiltro = '';
        const sf = document.getElementById('statusFilter');
        if (sf) sf.value = 'all';
    } else {
        // Default: active fleet (operational - excludes Sold and Pound)
        statusFiltro = 'operational';
        v5cFiltro = '';
        const sf = document.getElementById('statusFilter');
        if (sf) sf.value = 'operational';
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
            } else if (val === 'all') {
                statusFiltro = 'all';
                v5cFiltro = '';
            } else if (val === 'warnings') {
                statusFiltro = 'warnings';
                v5cFiltro = '';
            } else {
                statusFiltro = val;
                v5cFiltro = '';
            }
            sincronizarKpiCardAtivo();
            paginaAtual = 1;
            carregarMotos();
        });
    }

    // KPI Cards click handler to filter table
    document.querySelectorAll('.kpi-card').forEach(card => {
        card.addEventListener('click', () => {
            const filter = card.dataset.filter;
            const sf = document.getElementById('statusFilter');
            if (filter === 'missing_v5c') {
                statusFiltro = '';
                v5cFiltro = 'missing';
                if (sf) sf.value = 'missing_v5c';
            } else if (filter === 'all') {
                statusFiltro = 'all';
                v5cFiltro = '';
                if (sf) sf.value = 'all';
            } else if (filter === 'warnings') {
                statusFiltro = 'warnings';
                v5cFiltro = '';
                if (sf) sf.value = 'warnings';
            } else {
                statusFiltro = filter;
                v5cFiltro = '';
                if (sf) sf.value = filter;
            }
            sincronizarKpiCardAtivo();
            paginaAtual = 1;
            carregarMotos();
        });
    });

    // PDF Report button handler
    const btnExport = document.getElementById('btnExportPdf');
    if (btnExport) {
        btnExport.addEventListener('click', () => {
            const queryParams = new URLSearchParams({
                search: termoBusca
            });
            if (statusFiltro) queryParams.set('status', statusFiltro);
            if (v5cFiltro) queryParams.set('v5c', v5cFiltro);
            window.location.href = `/motos/relatorio-pdf?${queryParams.toString()}`;
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
