function formatWhatsAppNumber(phone) {
    if (typeof window.formatWhatsAppNumber === 'function' && window.formatWhatsAppNumber !== formatWhatsAppNumber) {
        return window.formatWhatsAppNumber(phone);
    }
    if (!phone) return '';
    const raw = String(phone).trim();
    if (!raw) return '';
    if (raw.startsWith('+')) {
        let digits = raw.replace(/\D/g, '');
        if (digits.startsWith('440') && digits.length >= 12) digits = '44' + digits.substring(3);
        return digits;
    }
    if (raw.startsWith('00')) {
        let digits = raw.replace(/\D/g, '').substring(2);
        if (digits.startsWith('440') && digits.length >= 12) digits = '44' + digits.substring(3);
        return digits;
    }
    const digits = raw.replace(/\D/g, '');
    if (!digits) return '';
    if (digits.startsWith('0')) return '44' + digits.substring(1);
    if (digits.startsWith('7') && digits.length === 10) return '44' + digits;
    if (digits.startsWith('44')) {
        if (digits.startsWith('440') && digits.length >= 12) return '44' + digits.substring(3);
        return digits;
    }
    return digits;
}

function copyToClipboard(text, triggerBtn) {
    if (!text || text === '-' || text === 'null') return;
    const cleanText = String(text).trim();
    if (!cleanText) return;

    function showSuccess() {
        if (!triggerBtn) return;
        const origHtml = triggerBtn.innerHTML;
        const origTitle = triggerBtn.title;
        triggerBtn.innerHTML = '<span style="color:#4ade80; font-weight:bold;">✓</span>';
        triggerBtn.title = 'Copied to clipboard!';
        triggerBtn.style.borderColor = 'rgba(74, 222, 128, 0.6)';
        triggerBtn.style.color = '#4ade80';
        triggerBtn.style.background = 'rgba(74, 222, 128, 0.15)';
        setTimeout(() => {
            triggerBtn.innerHTML = origHtml;
            triggerBtn.title = origTitle;
            triggerBtn.style.borderColor = '';
            triggerBtn.style.color = '';
            triggerBtn.style.background = '';
        }, 1800);
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(cleanText).then(showSuccess).catch(() => fallbackCopy(cleanText));
    } else {
        fallbackCopy(cleanText);
    }

    function fallbackCopy(val) {
        try {
            const tempInput = document.createElement('textarea');
            tempInput.value = val;
            tempInput.style.position = 'fixed';
            tempInput.style.opacity = '0';
            document.body.appendChild(tempInput);
            tempInput.focus();
            tempInput.select();
            const success = document.execCommand('copy');
            document.body.removeChild(tempInput);
            if (success) showSuccess();
        } catch (e) {
            console.warn('Clipboard copy failed:', e);
        }
    }
}
window.copyToClipboard = copyToClipboard;

// Global fallback stubs for Merge Modal in case called before full DOM init
window.abrirModalMerge = function(sourceId, targetId) {
    const m = document.getElementById('modalMergeCliente');
    if (m) {
        m.classList.add('active');
        m.style.display = 'flex';
    }
};
window.fecharModalMerge = function() {
    const m = document.getElementById('modalMergeCliente');
    if (m) {
        m.classList.remove('active');
        m.style.display = 'none';
    }
};

// Lightbox Logic for high-resolution document zoom & inspection
let lightboxIsZoomed = false;
function abrirLightbox(url, caption = '') {
    const modal = document.getElementById('lightboxModal');
    const img = document.getElementById('lightboxImg');
    const viewport = document.getElementById('lightboxViewport');
    const openFullBtn = document.getElementById('lightboxOpenFullBtn');
    const cap = document.getElementById('lightboxCaption');
    if (!modal || !img) return;

    if (url.toLowerCase().endsWith('.pdf')) {
        window.open(url, '_blank');
        return;
    }

    lightboxIsZoomed = false;
    img.src = url;
    img.style.transform = 'none';
    img.style.cursor = 'zoom-in';
    img.style.maxWidth = '100%';
    img.style.maxHeight = 'calc(82vh - 120px)';

    if (viewport) {
        viewport.scrollTop = 0;
        viewport.scrollLeft = 0;
    }

    if (cap) cap.textContent = caption || 'Document Preview';
    if (openFullBtn) openFullBtn.href = url;

    const zoomBtn = document.getElementById('lightboxToggleZoomBtn');
    if (zoomBtn) zoomBtn.innerHTML = '<span>🔎 Zoom 2x</span>';

    modal.classList.add('active');
}
window.abrirLightbox = abrirLightbox;

function fecharLightbox() {
    const modal = document.getElementById('lightboxModal');
    if (!modal) return;
    modal.classList.remove('active');
    const img = document.getElementById('lightboxImg');
    const viewport = document.getElementById('lightboxViewport');
    if (img) {
        img.src = '';
        img.style.transform = 'none';
        img.style.maxWidth = '100%';
        img.style.maxHeight = 'calc(82vh - 120px)';
    }
    if (viewport) {
        viewport.scrollTop = 0;
        viewport.scrollLeft = 0;
    }
    lightboxIsZoomed = false;
}
window.fecharLightbox = fecharLightbox;

function toggleLightboxZoom(e) {
    if (e) {
        e.preventDefault();
        e.stopPropagation();
    }
    const img = document.getElementById('lightboxImg');
    const viewport = document.getElementById('lightboxViewport');
    const zoomBtn = document.getElementById('lightboxToggleZoomBtn');
    if (!img) return;

    lightboxIsZoomed = !lightboxIsZoomed;
    if (lightboxIsZoomed) {
        img.style.maxWidth = 'none';
        img.style.maxHeight = 'none';
        img.style.width = '200%';
        img.style.cursor = 'zoom-out';
        if (zoomBtn) zoomBtn.innerHTML = '<span>🔍 Fit Screen</span>';
    } else {
        img.style.maxWidth = '100%';
        img.style.maxHeight = 'calc(82vh - 120px)';
        img.style.width = 'auto';
        img.style.cursor = 'zoom-in';
        if (viewport) {
            viewport.scrollTop = 0;
            viewport.scrollLeft = 0;
        }
        if (zoomBtn) zoomBtn.innerHTML = '<span>🔎 Zoom 2x</span>';
    }
}
window.toggleLightboxZoom = toggleLightboxZoom;

let paginaAtual = 1;
let termoBusca = '';
let statusFiltro = '';
let limitePorPagina = 20;
let sortCol = 'id';
let sortOrder = 'desc';

async function carregarClientes() {
    const tbody = document.querySelector('#clientesTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    
    try {
        const queryParams = new URLSearchParams({
            page: paginaAtual,
            limit: limitePorPagina,
            search: termoBusca,
            status: statusFiltro,
            sort_by: sortCol,
            sort_order: sortOrder
        });

        const res = await fetch(`/api/clientes?${queryParams.toString()}`);
        const data = await res.json();
        const clientes = data.itens || [];

        // Update KPI Strip
        if (data.kpis) {
            const kpiTotal = document.getElementById('kpiVal_total');
            const kpiActive = document.getElementById('kpiVal_active');
            const kpiOverdue = document.getElementById('kpiVal_overdue');
            const kpiSubOverdue = document.getElementById('kpiSub_overdue');
            const kpiMissingDocs = document.getElementById('kpiVal_missing_docs');

            if (kpiTotal) kpiTotal.textContent = data.kpis.total !== undefined ? data.kpis.total : '-';
            if (kpiActive) kpiActive.textContent = data.kpis.active_hirers !== undefined ? data.kpis.active_hirers : '-';
            if (kpiOverdue) kpiOverdue.textContent = data.kpis.overdue_count !== undefined ? data.kpis.overdue_count : '-';
            if (kpiSubOverdue && data.kpis.overdue_amount !== undefined) {
                kpiSubOverdue.textContent = `Total: £${Number(data.kpis.overdue_amount).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            }
            if (kpiMissingDocs) kpiMissingDocs.textContent = data.kpis.missing_docs !== undefined ? data.kpis.missing_docs : '-';
        }
        
        if (clientes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding: 2.5rem 1rem; color: var(--text-secondary);">No customers found matching the criteria.</td></tr>';
            if (paginationInfo) paginationInfo.textContent = '';
            const btnPrev = document.getElementById('btnPrevPage');
            const btnNext = document.getElementById('btnNextPage');
            if (btnPrev) btnPrev.disabled = true;
            if (btnNext) btnNext.disabled = true;
            return;
        }
        
        tbody.innerHTML = '';
        clientes.forEach(c => {
            const tr = document.createElement('tr');
            
            // Status dot (🔴, 🟡, 🟢)
            let dotColor = '#22c55e'; // default success
            let dotGlow = 'rgba(34,197,94,0.4)';
            if (c.status_dot === 'danger') {
                dotColor = '#ef4444';
                dotGlow = 'rgba(239,68,68,0.5)';
            } else if (c.status_dot === 'warning') {
                dotColor = '#f59e0b';
                dotGlow = 'rgba(245,158,11,0.5)';
            }
            const dotTitle = escapeHtml(c.status_dot_title || 'Customer status');
            const statusDotHtml = `<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${dotColor}; box-shadow:0 0 6px ${dotGlow}; margin-right:4px; vertical-align:middle;" title="${dotTitle}"></span>`;

            // Customer Name & Note
            const noteBadge = c.notas_internas 
                ? `<span class="badge" style="background:rgba(245,158,11,0.15); color:#fbbf24; border:1px solid rgba(245,158,11,0.3); font-size:0.68rem; margin-left:4px; padding:1px 5px; cursor:help;" title="Internal Notes: ${escapeHtml(c.notas_internas)}">📝 Note</span>` 
                : '';
            const copyNameBtn = `<button type="button" class="btn-copy-chip" onclick="copyToClipboard('${escapeHtml(c.nome)}', this)" title="Copy name">📋</button>`;
            const customerNameHtml = `<div style="display:flex; align-items:center; flex-wrap:wrap; gap:2px;"><strong style="color:var(--text-primary);">${escapeHtml(c.nome)}</strong>${copyNameBtn}${noteBadge}</div>`;

            // Phone & WhatsApp
            const waNum = formatWhatsAppNumber(c.telefone);
            const waGreeting = encodeURIComponent(`Hello ${c.nome || ''}, this is FF Motors: `);
            const copyTelBtn = `<button type="button" class="btn-copy-chip" onclick="copyToClipboard('${escapeHtml(c.telefone)}', this)" title="Copy phone">📋</button>`;
            const telHtml = waNum 
                ? `<a href="https://wa.me/${waNum}?text=${waGreeting}" target="_blank" rel="noopener noreferrer" class="btn-wa-chip" title="Chat with ${escapeHtml(c.nome)} on WhatsApp">💬 ${escapeHtml(c.telefone)}</a>${copyTelBtn}`
                : `<span style="color:var(--text-secondary);">${escapeHtml(c.telefone || '-')}</span>${copyTelBtn}`;

            // Email
            let emailHtml = '';
            if (c.email) {
                const copyEmailBtn = `<button type="button" class="btn-copy-chip" onclick="copyToClipboard('${escapeHtml(c.email)}', this)" title="Copy email">📋</button>`;
                emailHtml = `<div style="font-size:0.75rem; color:var(--text-secondary); margin-top:2px; display:flex; align-items:center;"><a href="mailto:${encodeURIComponent(c.email)}" style="color:var(--text-secondary); text-decoration:none;" title="Send email">${escapeHtml(c.email)}</a>${copyEmailBtn}</div>`;
            }

            const contactCellHtml = `<div>${telHtml}${emailHtml}</div>`;

            // Address
            const copyAddressBtn = c.endereco 
                ? `<button type="button" class="btn-copy-chip" onclick="copyToClipboard('${escapeHtml(c.endereco)}', this)" title="Copy address">📋</button>`
                : '';
            const addressText = c.endereco ? escapeHtml(c.endereco) : '<span style="color:var(--text-secondary);">—</span>';
            const addressHtml = `<div style="display:flex; align-items:center; max-width:180px;"><span style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(c.endereco || '')}">${addressText}</span>${copyAddressBtn}</div>`;

            // Active Deal / Vehicle
            let activeDealHtml = '<span style="color:var(--text-secondary); font-size:0.78rem;">— No active deal</span>';
            if (c.has_active_deal && c.active_deal) {
                const deal = c.active_deal;
                const plate = escapeHtml(deal.placa || 'N/A');
                const model = escapeHtml(deal.moto_modelo || '');
                const cor = deal.moto_cor ? ` • ${escapeHtml(deal.moto_cor)}` : '';
                const moreTag = c.active_deals_count > 1 ? ` <span style="font-size:0.68rem; opacity:0.8;">(+${c.active_deals_count - 1})</span>` : '';
                
                activeDealHtml = `
                    <div style="display:flex; flex-direction:column; gap:2px;">
                        <div style="display:flex; align-items:center; gap:5px; flex-wrap:wrap;">
                            <span class="badge-plate" style="background:#0f172a; color:#f8fafc; border:1px solid #334155;">${plate}</span>
                            <a href="/contratos/${deal.id}" class="badge" style="background:rgba(56,189,248,0.15); color:#38bdf8; border:1px solid rgba(56,189,248,0.3); text-decoration:none;" title="Open Deal #${deal.id}">#${deal.id} ↗</a>${moreTag}
                        </div>
                        <div style="font-size:0.73rem; color:var(--text-secondary); line-height:1.1;" title="${model}${cor}">${model}${cor}</div>
                    </div>
                `;
            } else if (c.total_deals > 0) {
                activeDealHtml += ` <span style="font-size:0.7rem; color:var(--text-secondary);">(${c.total_deals} past)</span>`;
            }

            // Financial Status / Debts
            let finStatusHtml = '<span class="badge" style="background:rgba(34,197,94,0.12); color:#4ade80; border:1px solid rgba(34,197,94,0.3);">✓ Up to date</span>';
            if (c.overdue_count > 0) {
                finStatusHtml = `<span class="badge" style="background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.35); font-weight:700;" title="${c.overdue_count} overdue payments">🔴 £${Number(c.overdue_amount).toFixed(2)} (${c.overdue_count} late)</span>`;
            }

            // Documents
            const docsList = [];
            if (c.url_habilitacao) {
                docsList.push(`<a href="javascript:void(0)" onclick="abrirLightbox('${escapeHtml(c.url_habilitacao)}', 'Driving Licence (Front) - ${escapeHtml(c.nome)}')" class="doc-chip" style="background:rgba(56,189,248,0.15); color:#38bdf8; border:1px solid rgba(56,189,248,0.3);" title="View Driving Licence Front">🪪 Licence (F)</a>`);
            }
            if (c.url_habilitacao_verso) {
                docsList.push(`<a href="javascript:void(0)" onclick="abrirLightbox('${escapeHtml(c.url_habilitacao_verso)}', 'Driving Licence (Back) - ${escapeHtml(c.nome)}')" class="doc-chip" style="background:rgba(56,189,248,0.15); color:#38bdf8; border:1px solid rgba(56,189,248,0.3);" title="View Driving Licence Back">🪪 Licence (B)</a>`);
            }
            if (!c.url_habilitacao && !c.url_habilitacao_verso) {
                docsList.push(`<span class="badge" style="background:rgba(245,158,11,0.12); color:#fbbf24; border:1px solid rgba(245,158,11,0.3);" title="Driving Licence not uploaded">⚠️ No Licence</span>`);
            }

            if (c.url_cbt) {
                docsList.push(`<a href="javascript:void(0)" onclick="abrirLightbox('${escapeHtml(c.url_cbt)}', 'CBT Certificate - ${escapeHtml(c.nome)}')" class="doc-chip" style="background:rgba(74,222,128,0.15); color:#4ade80; border:1px solid rgba(74,222,128,0.3);" title="View CBT Certificate">📜 CBT</a>`);
            }

            if (c.url_comprovante_endereco) {
                docsList.push(`<a href="javascript:void(0)" onclick="abrirLightbox('${escapeHtml(c.url_comprovante_endereco)}', 'Proof of Address - ${escapeHtml(c.nome)}')" class="doc-chip" style="background:rgba(192,132,252,0.15); color:#c084fc; border:1px solid rgba(192,132,252,0.3);" title="View Proof of Address">🏠 Proof</a>`);
            } else {
                docsList.push(`<span class="badge" style="background:rgba(245,158,11,0.12); color:#fbbf24; border:1px solid rgba(245,158,11,0.3);" title="Proof of Address not uploaded">⚠️ No Proof</span>`);
            }

            const docsCellHtml = `<div style="display:flex; flex-wrap:wrap; gap:3px;">${docsList.join('')}</div>`;

            // Actions
            const btnDeal = `<a href="/contratos/novo?cliente_id=${c.id}" class="btn-action-deal" title="Create a new Deal / Agreement for ${escapeHtml(c.nome)}">+ Deal</a>`;
            const btnEdit = `<button type="button" class="btn-action-edit btn-edit" data-id="${c.id}" data-nome="${escapeHtml(c.nome || '')}" data-tel="${escapeHtml(c.telefone || '')}" data-email="${escapeHtml(c.email || '')}" data-endereco="${escapeHtml(c.endereco || '')}" data-notas="${escapeHtml(c.notas_internas || '')}">Edit</button>`;
            const actionsCellHtml = `<div style="display:flex; justify-content:flex-end; gap:5px; align-items:center;">${btnDeal}${btnEdit}</div>`;

            // ID badge
            const idCellHtml = `<div style="display:flex; align-items:center; gap:3px;">${statusDotHtml}<span style="font-weight:700; color:var(--accent); font-size:0.82rem;">#${c.id}</span></div>`;

            tr.innerHTML = `
                <td class="nowrap">${idCellHtml}</td>
                <td>${customerNameHtml}</td>
                <td>${contactCellHtml}</td>
                <td>${addressHtml}</td>
                <td>${activeDealHtml}</td>
                <td>${finStatusHtml}</td>
                <td>${docsCellHtml}</td>
                <td>${actionsCellHtml}</td>
            `;
            tbody.appendChild(tr);
        });

        // Update pagination UI
        if (paginationInfo) {
            paginationInfo.textContent = `Page ${data.pagina_atual} of ${data.paginas} (${data.total} records)`;
        }
        const btnPrev = document.getElementById('btnPrevPage');
        const btnNext = document.getElementById('btnNextPage');
        if (btnPrev) btnPrev.disabled = data.pagina_atual <= 1;
        if (btnNext) btnNext.disabled = data.pagina_atual >= data.paginas;
        
        // Setup Edit Modal Events
        const modal = document.getElementById('editClientModal');
        document.querySelectorAll('.btn-edit').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetBtn = e.target.closest('.btn-edit');
                if (!targetBtn) return;
                document.getElementById('edit_id').value = targetBtn.getAttribute('data-id') || '';
                document.getElementById('edit_nome').value = targetBtn.getAttribute('data-nome') || '';
                document.getElementById('edit_telefone').value = targetBtn.getAttribute('data-tel') || '';
                document.getElementById('edit_email').value = targetBtn.getAttribute('data-email') || '';
                document.getElementById('edit_endereco').value = targetBtn.getAttribute('data-endereco') || '';
                const txtNotas = document.getElementById('edit_notas_internas');
                if (txtNotas) txtNotas.value = targetBtn.getAttribute('data-notas') || '';
                
                // Clear file inputs
                ['edit_habilitacao', 'edit_habilitacao_verso', 'edit_cbt', 'edit_comprovante_endereco'].forEach(fId => {
                    const el = document.getElementById(fId);
                    if (el) el.value = '';
                });

                if (modal) modal.classList.add('active');
            });
        });

        if (typeof setTableSortIndicator === 'function') {
            setTableSortIndicator('clientesTable', sortCol, sortOrder);
        }
        
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--error); padding:2rem 1rem;">Error loading customers. Please refresh the page.</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Read URL query parameters (e.g. ?search=12 or ?id=12 or ?status=active)
    const urlParams = new URLSearchParams(window.location.search);
    const initialSearch = urlParams.get('search') || urlParams.get('q') || urlParams.get('id');
    const initialStatus = urlParams.get('status');
    const searchInput = document.getElementById('searchInput');
    const filterStatusSelect = document.getElementById('filterStatus');
    const filterLimitSelect = document.getElementById('filterLimit');

    if (initialSearch) {
        termoBusca = initialSearch.trim();
        if (searchInput) searchInput.value = initialSearch.trim();
    }

    if (initialStatus) {
        statusFiltro = initialStatus.trim().toLowerCase();
        if (filterStatusSelect) filterStatusSelect.value = statusFiltro;
        syncKpiCardsState();
    }

    if (typeof enableTableSorting === 'function') {
        enableTableSorting('clientesTable', (field, order) => {
            sortCol = field;
            sortOrder = order;
            paginaAtual = 1;
            carregarClientes();
        });
    }

    carregarClientes();
    
    // Pagination Controls
    const btnPrev = document.getElementById('btnPrevPage');
    const btnNext = document.getElementById('btnNextPage');
    if (btnPrev) btnPrev.addEventListener('click', () => { paginaAtual--; carregarClientes(); });
    if (btnNext) btnNext.addEventListener('click', () => { paginaAtual++; carregarClientes(); });

    // Status Filter dropdown
    if (filterStatusSelect) {
        filterStatusSelect.addEventListener('change', (e) => {
            statusFiltro = e.target.value;
            paginaAtual = 1;
            syncKpiCardsState();
            carregarClientes();
        });
    }

    // Page Limit dropdown
    if (filterLimitSelect) {
        filterLimitSelect.addEventListener('change', (e) => {
            limitePorPagina = parseInt(e.target.value, 10) || 20;
            paginaAtual = 1;
            carregarClientes();
        });
    }

    // Search input with debounce
    let timeoutId;
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                termoBusca = e.target.value;
                paginaAtual = 1;
                carregarClientes();
            }, 400);
        });
    }

    // Clear Filters button
    const btnClearFilters = document.getElementById('btnClearFilters');
    if (btnClearFilters) {
        btnClearFilters.addEventListener('click', () => {
            termoBusca = '';
            statusFiltro = '';
            limitePorPagina = 20;
            if (searchInput) searchInput.value = '';
            if (filterStatusSelect) filterStatusSelect.value = '';
            if (filterLimitSelect) filterLimitSelect.value = '20';
            paginaAtual = 1;
            syncKpiCardsState();
            carregarClientes();
        });
    }

    // Interactive KPI Cards (Click to Filter)
    const kpiCards = document.querySelectorAll('.clientes-kpis-grid .kpi-card');
    kpiCards.forEach(card => {
        card.addEventListener('click', () => {
            const filterVal = card.getAttribute('data-filter-status') || '';
            if (statusFiltro === filterVal && filterVal !== '') {
                // Clicking again resets to All
                statusFiltro = '';
                if (filterStatusSelect) filterStatusSelect.value = '';
            } else {
                statusFiltro = filterVal;
                if (filterStatusSelect) filterStatusSelect.value = filterVal;
            }
            paginaAtual = 1;
            syncKpiCardsState();
            carregarClientes();
        });
    });

    function syncKpiCardsState() {
        kpiCards.forEach(card => {
            const fVal = card.getAttribute('data-filter-status') || '';
            if (statusFiltro === fVal) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
        });
    }

    // Lightbox Controls
    const closeLightboxBtn = document.getElementById('closeLightboxBtn');
    const lightboxModal = document.getElementById('lightboxModal');
    const zoomToggleBtn = document.getElementById('lightboxToggleZoomBtn');

    if (closeLightboxBtn) closeLightboxBtn.addEventListener('click', fecharLightbox);
    if (zoomToggleBtn) zoomToggleBtn.addEventListener('click', toggleLightboxZoom);
    if (lightboxModal) {
        lightboxModal.addEventListener('click', (e) => {
            if (e.target === lightboxModal) fecharLightbox();
        });
    }

    // Edit Client Modal controls
    const editModal = document.getElementById('editClientModal');
    const closeBtn = document.getElementById('closeClientModal');
    
    function fecharModalCliente() {
        if (editModal) editModal.classList.remove('active');
    }

    if (closeBtn) closeBtn.addEventListener('click', fecharModalCliente);
    if (editModal) {
        editModal.addEventListener('click', (e) => {
            if (e.target === editModal) fecharModalCliente();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            if (lightboxModal && lightboxModal.classList.contains('active')) {
                fecharLightbox();
            } else if (editModal && editModal.classList.contains('active')) {
                fecharModalCliente();
            } else {
                const mMerge = document.getElementById('modalMergeCliente');
                if (mMerge && mMerge.classList.contains('active')) {
                    if (typeof fecharModalMerge === 'function') fecharModalMerge();
                    else {
                        mMerge.classList.remove('active');
                        mMerge.style.display = 'none';
                    }
                }
            }
        }
    });

    function capitalizeWords(str) {
        if (!str) return '';
        return str.trim().replace(/\b([a-zÀ-ÿ])/g, char => char.toUpperCase());
    }

    const editNomeInput = document.getElementById('edit_nome');
    const editEndInput = document.getElementById('edit_endereco');

    if (editNomeInput) {
        editNomeInput.addEventListener('blur', () => {
            editNomeInput.value = capitalizeWords(editNomeInput.value);
        });
    }

    if (editEndInput) {
        editEndInput.addEventListener('blur', () => {
            editEndInput.value = capitalizeWords(editEndInput.value);
        });
    }

    const editForm = document.getElementById('editClientForm');
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('edit_id').value;
            const submitBtn = document.getElementById('btnSalvarCliente') || editForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn ? submitBtn.textContent : 'Save Changes';

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Saving...';
            }

            const data = new FormData();
            const editNomeVal = capitalizeWords(document.getElementById('edit_nome').value);
            const editEndVal = capitalizeWords(document.getElementById('edit_endereco').value);
            data.append('nome', editNomeVal);
            data.append('telefone', document.getElementById('edit_telefone').value.trim());
            data.append('email', document.getElementById('edit_email').value.trim());
            data.append('endereco', editEndVal);
            const txtNotas = document.getElementById('edit_notas_internas');
            if (txtNotas) {
                data.append('notas_internas', txtNotas.value.trim());
            }
            
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
            const compOptions = {
                maxSizeMB: 0.35,
                maxWidthOrHeight: 1600,
                useWebWorker: !isIOS,
                fileType: isIOS ? 'image/jpeg' : 'image/webp',
                initialQuality: 0.75
            };
            const extReplacement = isIOS ? '.jpg' : '.webp';
            
            const appendEditFile = async (fieldId, formKey) => {
                const input = document.getElementById(fieldId);
                if (input && input.files.length > 0) {
                    const file = input.files[0];
                    if (file.type.startsWith('image/')) {
                        try {
                            const compressedFile = await imageCompression(file, compOptions);
                            data.append(formKey, compressedFile, file.name.replace(/\.[^/.]+$/, extReplacement));
                        } catch (err) {
                            data.append(formKey, file);
                        }
                    } else {
                        data.append(formKey, file);
                    }
                }
            };

            await appendEditFile('edit_habilitacao', 'habilitacao');
            await appendEditFile('edit_habilitacao_verso', 'habilitacao_verso');
            await appendEditFile('edit_cbt', 'cbt');
            await appendEditFile('edit_comprovante_endereco', 'comprovante_endereco');
            
            try {
                const response = await fetch(`/api/clientes/${id}`, { method: 'PUT', body: data });
                if (response.ok) {
                    fecharModalCliente();
                    carregarClientes();
                } else {
                    const res = await response.json();
                    alert(res.error || res.erro || 'Error updating customer');
                }
            } catch(err) {
                alert('Server connection error. Please try again.');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalBtnText;
                }
            }
        });
    }

    // ==========================================
    // MERGE DUPLICATE CUSTOMERS CONTROLLER
    // ==========================================
    const modalMerge = document.getElementById('modalMergeCliente');
    const btnOpenMergeModal = document.getElementById('btnOpenMergeModal');
    const btnCloseMergeModal = document.getElementById('btnCloseMergeModal');
    const btnCancelMerge = document.getElementById('btnCancelMerge');
    const btnConfirmMerge = document.getElementById('btnConfirmMerge');
    const mergeSourceSelect = document.getElementById('mergeSourceSelect');
    const mergeTargetSelect = document.getElementById('mergeTargetSelect');
    const mergeSourceSearch = document.getElementById('mergeSourceSearch');
    const mergeTargetSearch = document.getElementById('mergeTargetSearch');
    const mergeSourcePreview = document.getElementById('mergeSourcePreview');
    const mergeTargetPreview = document.getElementById('mergeTargetPreview');
    const mergeImpactBanner = document.getElementById('mergeImpactBanner');
    const mergeReason = document.getElementById('mergeReason');
    const mergeFeedback = document.getElementById('mergeFeedback');
    const mergeSourceBadge = document.getElementById('mergeSourceBadge');
    const mergeTargetBadge = document.getElementById('mergeTargetBadge');

    let allMergeCustomers = [];

    async function carregarClientesParaMerge() {
        try {
            const res = await fetch('/api/clientes?limit=1000');
            const data = await res.json();
            allMergeCustomers = data.itens || [];
            popularSelectsMerge();
        } catch (err) {
            console.error('Failed to load customers for merge', err);
        }
    }

    function renderSelectOptions(selectEl, list, currentVal = '') {
        selectEl.innerHTML = '';
        const defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = list.length > 0 ? `-- Select Customer (${list.length}) --` : '-- No customers found --';
        selectEl.appendChild(defaultOpt);

        list.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            const phone = c.telefone ? ` • 📱 ${c.telefone}` : '';
            const active = (c.has_active_deal && c.active_deal) ? ` [⚡ Active: ${c.active_deal.placa}]` : '';
            opt.textContent = `${c.nome}${phone} (#${c.id})${active}`;
            selectEl.appendChild(opt);
        });

        if (currentVal && list.some(item => String(item.id) === String(currentVal))) {
            selectEl.value = currentVal;
        }
    }

    function popularSelectsMerge() {
        const srcVal = mergeSourceSelect ? mergeSourceSelect.value : '';
        const tgtVal = mergeTargetSelect ? mergeTargetSelect.value : '';
        if (mergeSourceSelect) renderSelectOptions(mergeSourceSelect, allMergeCustomers, srcVal);
        if (mergeTargetSelect) renderSelectOptions(mergeTargetSelect, allMergeCustomers, tgtVal);
        atualizarMergePreview();
    }

    function filterCustomerList(term) {
        if (!term) return allMergeCustomers;
        const cleanTerm = term.trim().toLowerCase();
        const digits = cleanTerm.replace(/\D/g, '');
        return allMergeCustomers.filter(c => {
            const nome = (c.nome || '').toLowerCase();
            const tel = (c.telefone || '').toLowerCase();
            const telDigits = (c.telefone || '').replace(/\D/g, '');
            const email = (c.email || '').toLowerCase();
            const idStr = String(c.id);

            return nome.includes(cleanTerm) ||
                   tel.includes(cleanTerm) ||
                   (digits && telDigits.includes(digits)) ||
                   email.includes(cleanTerm) ||
                   idStr === cleanTerm.replace('#', '');
        });
    }

    if (mergeSourceSearch && mergeSourceSelect) {
        mergeSourceSearch.addEventListener('input', (e) => {
            const filtered = filterCustomerList(e.target.value);
            renderSelectOptions(mergeSourceSelect, filtered, mergeSourceSelect.value);
            if (mergeSourceBadge) mergeSourceBadge.textContent = `${filtered.length} found`;
            atualizarMergePreview();
        });
    }

    if (mergeTargetSearch && mergeTargetSelect) {
        mergeTargetSearch.addEventListener('input', (e) => {
            const filtered = filterCustomerList(e.target.value);
            renderSelectOptions(mergeTargetSelect, filtered, mergeTargetSelect.value);
            if (mergeTargetBadge) mergeTargetBadge.textContent = `${filtered.length} found`;
            atualizarMergePreview();
        });
    }

    function renderCardPreview(containerEl, client) {
        if (!containerEl) return;
        if (!client) {
            containerEl.style.display = 'none';
            containerEl.innerHTML = '';
            return;
        }

        const docFront = client.has_licence_front ? '<span style="color:#4ade80;">✓ Licence (F)</span>' : '<span style="color:#f87171;">⚠️ No Licence (F)</span>';
        const docBack = client.has_licence_back ? '<span style="color:#4ade80;">✓ Licence (B)</span>' : '<span style="color:#f87171;">⚠️ No Licence (B)</span>';
        const docProof = client.has_proof_address ? '<span style="color:#4ade80;">✓ Proof</span>' : '<span style="color:#f87171;">⚠️ No Proof</span>';
        
        let activeTag = '<span style="color:var(--text-secondary);">No active agreements</span>';
        if (client.has_active_deal && client.active_deal) {
            activeTag = `<span style="color:#38bdf8; font-weight:700;">⚡ On Road: ${escapeHtml(client.active_deal.placa)} (${escapeHtml(client.active_deal.moto_modelo || '')})</span>`;
        }

        containerEl.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
                <div>
                    <div style="font-weight:700; color:var(--text-primary); font-size:0.85rem;">
                        ${escapeHtml(client.nome)} <span style="color:var(--accent); font-size:0.75rem;">#${client.id}</span>
                    </div>
                    <div style="color:var(--text-secondary); font-size:0.75rem; margin-top:2px;">
                        📱 ${escapeHtml(client.telefone || 'No phone')} ${client.email ? `• ✉️ ${escapeHtml(client.email)}` : ''}
                    </div>
                    ${client.endereco ? `<div style="color:var(--text-secondary); font-size:0.72rem; margin-top:1px;">🏠 ${escapeHtml(client.endereco)}</div>` : ''}
                    <div style="margin-top:4px; font-size:0.74rem;">${activeTag} • Total Agreements: <strong>${client.total_deals || 0}</strong></div>
                </div>
                <div style="display:flex; flex-direction:column; gap:2px; font-size:0.72rem; text-align:right;">
                    ${docFront}
                    ${docBack}
                    ${docProof}
                </div>
            </div>
        `;
        containerEl.style.display = 'block';
    }

    function atualizarMergePreview() {
        const srcId = parseInt(mergeSourceSelect?.value);
        const tgtId = parseInt(mergeTargetSelect?.value);

        const srcClient = allMergeCustomers.find(c => c.id === srcId);
        const tgtClient = allMergeCustomers.find(c => c.id === tgtId);

        renderCardPreview(mergeSourcePreview, srcClient);
        renderCardPreview(mergeTargetPreview, tgtClient);

        if (!btnConfirmMerge) return;

        if (!srcId || !tgtId) {
            btnConfirmMerge.disabled = true;
            if (mergeImpactBanner) mergeImpactBanner.style.display = 'none';
            return;
        }

        if (srcId === tgtId) {
            btnConfirmMerge.disabled = true;
            if (mergeImpactBanner) {
                mergeImpactBanner.style.display = 'block';
                mergeImpactBanner.style.background = 'rgba(239, 68, 68, 0.15)';
                mergeImpactBanner.style.borderColor = 'rgba(239, 68, 68, 0.35)';
                mergeImpactBanner.style.color = '#f87171';
                mergeImpactBanner.innerHTML = '❌ <strong>Error:</strong> Duplicate customer and primary customer cannot be the same record.';
            }
            return;
        }

        btnConfirmMerge.disabled = false;
        if (mergeImpactBanner) {
            mergeImpactBanner.style.display = 'block';
            mergeImpactBanner.style.background = 'rgba(245, 158, 11, 0.1)';
            mergeImpactBanner.style.borderColor = 'rgba(245, 158, 11, 0.3)';
            mergeImpactBanner.style.color = '#f59e0b';
            
            const numDeals = srcClient ? (srcClient.total_deals || 0) : 0;
            const activeNote = (srcClient && srcClient.has_active_deal) ? ' (including 1 active on-road agreement)' : '';
            const srcName = srcClient ? escapeHtml(srcClient.nome) : '';
            const tgtName = tgtClient ? escapeHtml(tgtClient.nome) : '';
            mergeImpactBanner.innerHTML = `
                ⚠️ <strong>Irreversible Operation:</strong> Customer <strong>#${srcId} (${srcName})</strong> will be permanently removed.
                <strong>${numDeals} agreement${numDeals === 1 ? '' : 's'}${activeNote}</strong> and any missing documents will be transferred into <strong>#${tgtId} (${tgtName})</strong>.
            `;
        }
    }

    if (mergeSourceSelect) mergeSourceSelect.addEventListener('change', atualizarMergePreview);
    if (mergeTargetSelect) mergeTargetSelect.addEventListener('change', atualizarMergePreview);

    function abrirModalMerge(sourceId = null, targetId = null) {
        const m = document.getElementById('modalMergeCliente');
        if (!m) return;
        m.classList.add('active');
        m.style.display = 'flex';

        if (mergeFeedback) {
            mergeFeedback.className = 'feedback-message hidden';
            mergeFeedback.style.display = 'none';
            mergeFeedback.textContent = '';
        }
        if (mergeReason) mergeReason.value = '';
        if (mergeSourceSearch) mergeSourceSearch.value = '';
        if (mergeTargetSearch) mergeTargetSearch.value = '';

        carregarClientesParaMerge().then(() => {
            if (sourceId && mergeSourceSelect) {
                mergeSourceSelect.value = String(sourceId);
            }
            if (targetId && mergeTargetSelect) {
                mergeTargetSelect.value = String(targetId);
            }
            atualizarMergePreview();
        });
    }

    function fecharModalMerge() {
        const m = document.getElementById('modalMergeCliente');
        if (!m) return;
        m.classList.remove('active');
        m.style.display = 'none';
    }

    if (btnOpenMergeModal) {
        btnOpenMergeModal.addEventListener('click', () => abrirModalMerge());
    }
    if (btnCloseMergeModal) {
        btnCloseMergeModal.addEventListener('click', fecharModalMerge);
    }
    if (btnCancelMerge) {
        btnCancelMerge.addEventListener('click', fecharModalMerge);
    }
    if (modalMerge) {
        modalMerge.addEventListener('click', (e) => {
            if (e.target === modalMerge) fecharModalMerge();
        });
    }

    // Expose abrirModalMerge and fecharModalMerge globally
    window.abrirModalMerge = abrirModalMerge;
    window.fecharModalMerge = fecharModalMerge;

    // Confirm merge submit
    if (btnConfirmMerge) {
        btnConfirmMerge.addEventListener('click', async () => {
            const srcId = parseInt(mergeSourceSelect?.value);
            const tgtId = parseInt(mergeTargetSelect?.value);
            const motivoVal = (mergeReason?.value || '').trim();

            if (!srcId || !tgtId || srcId === tgtId) {
                alert('Please select both a valid duplicate customer and a different primary customer.');
                return;
            }

            const srcClient = allMergeCustomers.find(c => c.id === srcId);
            const tgtClient = allMergeCustomers.find(c => c.id === tgtId);
            const confirmMsg = `Are you sure you want to permanently merge customer #${srcId} (${srcClient?.nome || ''}) into #${tgtId} (${tgtClient?.nome || ''})?\n\nThis cannot be undone.`;
            if (!confirm(confirmMsg)) return;

            btnConfirmMerge.disabled = true;
            const btnText = btnConfirmMerge.querySelector('.btn-text');
            const loader = btnConfirmMerge.querySelector('.loader');
            if (btnText) btnText.classList.add('hidden');
            if (loader) loader.classList.remove('hidden');

            try {
                const response = await fetch('/api/clientes/merge', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        source_id: srcId,
                        target_id: tgtId,
                        motivo: motivoVal
                    })
                });

                const data = await response.json();
                if (response.ok) {
                    if (mergeFeedback) {
                        mergeFeedback.className = 'feedback-message success';
                        mergeFeedback.style.display = 'block';
                        mergeFeedback.style.background = 'rgba(34, 197, 94, 0.15)';
                        mergeFeedback.style.borderColor = 'rgba(34, 197, 94, 0.35)';
                        mergeFeedback.style.color = '#4ade80';
                        mergeFeedback.textContent = `✓ ${data.message || 'Customers merged successfully!'} (${data.transferred_contracts} agreements transferred)`;
                    }
                    setTimeout(() => {
                        fecharModalMerge();
                        carregarClientes();
                    }, 1400);
                } else {
                    if (mergeFeedback) {
                        mergeFeedback.className = 'feedback-message error';
                        mergeFeedback.style.display = 'block';
                        mergeFeedback.style.background = 'rgba(239, 68, 68, 0.15)';
                        mergeFeedback.style.borderColor = 'rgba(239, 68, 68, 0.35)';
                        mergeFeedback.style.color = '#f87171';
                        mergeFeedback.textContent = data.error || data.erro || 'Failed to merge customers.';
                    }
                    btnConfirmMerge.disabled = false;
                }
            } catch (err) {
                alert('Connection error. Please try again.');
                btnConfirmMerge.disabled = false;
            } finally {
                if (btnText) btnText.classList.remove('hidden');
                if (loader) loader.classList.add('hidden');
            }
        });
    }
});
