/**
 * FF Motors - Shared Motorbike Management Modal (V5C Logbook & GPS Trackers)
 * Used across /motos and /contratos/<id>
 */

let currentMotoPlaca = null;
let currentContratoId = null;
let selectedV5CFiles = []; // Accumulator for V5C document/page photos (camera + gallery)
let selectedTrackerPhotos = []; // Accumulator for tracker photos (camera + gallery)

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Quick DVLA check helper
window.copiarPlacaDVLA = window.copiarPlacaDVLA || function(event, placa) {
    if (event) event.stopPropagation();
    if (!placa) {
        placa = document.getElementById('edit_placa')?.value || document.getElementById('placa')?.value || currentMotoPlaca || '';
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

// Lightbox logic
let lightboxIsZoomed = false;

function abrirLightbox(url, caption = '') {
    const modal = document.getElementById('lightboxModal');
    const img = document.getElementById('lightboxImg');
    const viewport = document.getElementById('lightboxViewport');
    const openFullBtn = document.getElementById('lightboxOpenFullBtn');
    const cap = document.getElementById('lightboxCaption');
    if (!modal || !img) return;

    img.src = url;
    if (openFullBtn) openFullBtn.href = url;
    if (cap) cap.textContent = caption || 'Document Preview';

    lightboxIsZoomed = false;
    img.style.maxWidth = '100%';
    img.style.maxHeight = 'calc(82vh - 120px)';
    img.style.width = 'auto';
    img.style.height = 'auto';
    img.style.cursor = 'zoom-in';

    if (viewport) {
        viewport.scrollTop = 0;
        viewport.scrollLeft = 0;
        viewport.style.alignItems = 'center';
        viewport.style.justifyContent = 'center';
    }

    const zoomBtn = document.getElementById('lightboxToggleZoomBtn');
    if (zoomBtn) zoomBtn.innerHTML = '<span>🔎 Zoom 2x</span>';

    modal.classList.add('active');
}

function fecharLightbox() {
    const modal = document.getElementById('lightboxModal');
    if (modal) modal.classList.remove('active');
    const img = document.getElementById('lightboxImg');
    const viewport = document.getElementById('lightboxViewport');
    if (img) {
        img.src = '';
        img.style.maxWidth = '100%';
        img.style.maxHeight = 'calc(82vh - 120px)';
        img.style.width = 'auto';
        img.style.height = 'auto';
    }
    if (viewport) {
        viewport.style.alignItems = 'center';
        viewport.style.justifyContent = 'center';
    }
    lightboxIsZoomed = false;
}

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
        img.style.width = '180%';
        img.style.height = 'auto';
        img.style.cursor = 'zoom-out';
        if (zoomBtn) zoomBtn.innerHTML = '<span>🔍 Fit Screen</span>';
        if (viewport) {
            viewport.style.alignItems = 'flex-start';
            viewport.style.justifyContent = 'flex-start';
        }
    } else {
        img.style.maxWidth = '100%';
        img.style.maxHeight = 'calc(82vh - 120px)';
        img.style.width = 'auto';
        img.style.height = 'auto';
        img.style.cursor = 'zoom-in';
        if (zoomBtn) zoomBtn.innerHTML = '<span>🔎 Zoom 2x</span>';
        if (viewport) {
            viewport.style.alignItems = 'center';
            viewport.style.justifyContent = 'center';
        }
    }
}

// Tab navigation within Moto Manage Modal
function alternarAba(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        const isCurrent = btn.getAttribute('data-tab') === tabId;
        if (isCurrent) {
            btn.classList.add('active');
            btn.style.color = 'var(--text-primary)';
            btn.style.borderBottom = '2px solid var(--accent)';
            btn.style.fontWeight = '600';
        } else {
            btn.classList.remove('active');
            btn.style.color = 'var(--text-secondary)';
            btn.style.borderBottom = '2px solid transparent';
            btn.style.fontWeight = '500';
        }
    });

    document.querySelectorAll('.tab-pane').forEach(pane => {
        if (pane.id === tabId) {
            pane.style.display = 'block';
        } else {
            pane.style.display = 'none';
        }
    });
}

// Helper to render individual V5C or Transfer Proof card
function renderV5CCard(doc, idx) {
    const isPdf = doc.tipo_arquivo === 'pdf';
    const isTransfer = (doc.categoria_doc || 'v5c') === 'transfer_proof';
    const dateStr = doc.data_criacao ? doc.data_criacao.substring(0, 10) : '';
    const catBadge = isTransfer
        ? `<span class="badge" style="background: rgba(245,158,11,0.18); color: #fbbf24; border: 1px solid rgba(245,158,11,0.4); font-size: 0.68rem; font-weight: 700;">📋 Transfer Slip (Provisional)</span>`
        : `<span class="badge" style="background: rgba(6,182,212,0.18); color: #22d3ee; border: 1px solid rgba(6,182,212,0.4); font-size: 0.68rem; font-weight: 700;">✓ Official V5C Logbook</span>`;

    const previewHtml = isPdf ? `
        <div style="height: 120px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(239,68,68,0.08); border-bottom: 1px solid var(--border-color);">
            <span style="font-size: 2.5rem;">📑</span>
            <span style="font-size: 0.75rem; font-weight: 700; color: #ef4444; margin-top: 4px;">PDF DOCUMENT</span>
        </div>
    ` : `
        <div style="height: 120px; overflow: hidden; background: #000; position: relative; display: flex; align-items: center; justify-content: center; border-bottom: 1px solid var(--border-color); cursor: pointer;" onclick="abrirLightbox('${escapeHtml(doc.url_arquivo)}', '${isTransfer ? 'Transfer Slip' : 'V5C Logbook'} - ${escapeHtml(doc.nome_original || 'Doc ' + (idx + 1))}')" title="Click to enlarge & zoom">
            <img src="${escapeHtml(doc.url_arquivo)}" alt="Document Page" style="width: 100%; height: 100%; object-fit: cover; transition: transform 0.25s;" onmouseover="this.style.transform='scale(1.06)'" onmouseout="this.style.transform='scale(1)'">
            <span style="position: absolute; bottom: 6px; right: 6px; background: rgba(0,0,0,0.75); backdrop-filter: blur(4px); color: #fff; font-size: 0.7rem; font-weight: 600; padding: 2px 7px; border-radius: 999px; pointer-events: none; border: 1px solid rgba(255,255,255,0.25);">🔍 Enlarge</span>
        </div>
    `;

    const viewAction = isPdf ? `
        <a href="${escapeHtml(doc.url_arquivo)}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="padding: 0.35rem 0.65rem; font-size: 0.75rem; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;" title="Open PDF in new tab">
            <span>↗ Open</span>
        </a>
    ` : `
        <div style="display: inline-flex; gap: 4px;">
            <button type="button" class="btn-secondary" style="padding: 0.35rem 0.65rem; font-size: 0.75rem; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;" onclick="abrirLightbox('${escapeHtml(doc.url_arquivo)}', '${isTransfer ? 'Transfer Slip' : 'V5C Logbook'} - ${escapeHtml(doc.nome_original || 'Doc ' + (idx + 1))}')" title="Zoom & inspect inside modal">
                <span>🔍 Zoom</span>
            </button>
            <a href="${escapeHtml(doc.url_arquivo)}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="padding: 0.35rem 0.65rem; font-size: 0.75rem; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;" title="Open full resolution in new tab (pinch-to-zoom)">
                <span>↗ Full</span>
            </a>
        </div>
    `;

    return `
        <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; overflow: hidden; display: flex; flex-direction: column;">
            ${previewHtml}
            <div style="padding: 0.75rem; flex: 1; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div style="margin-bottom: 6px;">
                        ${catBadge}
                    </div>
                    <div style="font-size: 0.82rem; font-weight: 600; color: var(--text-primary); word-break: break-all; margin-bottom: 4px;" title="${escapeHtml(doc.nome_original)}">
                        ${escapeHtml(doc.nome_original || `Attachment #${doc.id}`)}
                    </div>
                    <div style="font-size: 0.72rem; color: var(--text-secondary); display: flex; flex-wrap: wrap; gap: 4px; align-items: center;">
                        <span>${dateStr ? `Added ${dateStr}` : ''} ${doc.criado_por_nome ? `by ${escapeHtml(doc.criado_por_nome)}` : ''}</span>
                        ${doc.id_contrato ? `<span class="badge" style="background: rgba(255,255,255,0.06); color: #94a3b8; font-size: 0.68rem; padding: 1px 5px;">Deal #${doc.id_contrato}</span>` : ''}
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.75rem; pt: 0.5rem; border-top: 1px solid rgba(255,255,255,0.05);">
                    ${viewAction}
                    <button type="button" class="btn-danger" style="padding: 0.35rem 0.65rem; font-size: 0.75rem; cursor: pointer; background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); border-radius: 6px;" onclick="removerV5C(${doc.id})">
                        <span>🗑️ Remove</span>
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Render V5C & Transfer Proof documents list
function renderV5CList(v5cList) {
    const container = document.getElementById('v5cListContainer');
    const countBadge = document.getElementById('badgeCountV5C');

    const list = v5cList || [];
    const transferSlips = list.filter(d => (d.categoria_doc || 'v5c') === 'transfer_proof');
    const officialV5Cs = list.filter(d => (d.categoria_doc || 'v5c') === 'v5c');

    if (countBadge) {
        if (officialV5Cs.length > 0) {
            countBadge.textContent = `${officialV5Cs.length} V5C`;
            countBadge.style.background = 'rgba(6,182,212,0.2)';
            countBadge.style.color = '#22d3ee';
        } else if (transferSlips.length > 0) {
            countBadge.textContent = `Slip (${transferSlips.length})`;
            countBadge.style.background = 'rgba(245,158,11,0.2)';
            countBadge.style.color = '#fbbf24';
        } else {
            countBadge.textContent = '0';
            countBadge.style.background = 'rgba(239,68,68,0.2)';
            countBadge.style.color = '#fca5a5';
        }
    }

    if (!container) return;

    if (list.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; color: var(--text-secondary); padding: 2rem 1rem; border: 1px dashed var(--border-color); border-radius: 12px; background: rgba(255,255,255,0.01);">
                <div style="font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.7;">📄</div>
                <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem;">No Registration Documents Attached</div>
                <div style="font-size: 0.8rem;">Attach the provisional transfer slip (while waiting for DVLA) or the official V5C logbook above.</div>
            </div>
        `;
        return;
    }

    container.innerHTML = `
        <!-- Section 1: Transfer Proof (Provisional) -->
        <div style="margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.65rem; flex-wrap: wrap; gap: 0.4rem;">
                <h4 style="margin: 0; font-size: 0.88rem; font-weight: 700; color: #fbbf24; display: flex; align-items: center; gap: 6px;">
                    <span>📋</span> DVLA Transfer Slip / Proof (Provisional)
                    <span class="badge" style="background: rgba(245,158,11,0.15); color: #fbbf24; font-size: 0.72rem; padding: 1px 6px;">${transferSlips.length}</span>
                </h4>
                ${transferSlips.length > 0 
                    ? `<span style="font-size: 0.74rem; color: #fbbf24; font-weight: 600; background: rgba(245,158,11,0.1); border: 1px solid rgba(245,158,11,0.3); padding: 2px 8px; border-radius: 4px;">⏳ Proof on File - Waiting for Official V5C</span>` 
                    : ''}
            </div>
            ${transferSlips.length > 0 ? `
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.85rem;">
                    ${transferSlips.map(renderV5CCard).join('')}
                </div>
            ` : `
                <div style="padding: 0.75rem 1rem; border: 1px dashed rgba(255,255,255,0.1); border-radius: 8px; font-size: 0.78rem; color: var(--text-secondary); background: rgba(0,0,0,0.15); display: flex; align-items: center; gap: 8px;">
                    <span>ℹ️</span> No provisional transfer slip attached. You can attach the New Keeper Slip (V5C/2) or DVLA confirmation above.
                </div>
            `}
        </div>

        <!-- Section 2: Official V5C Logbook (Final DVLA Document) -->
        <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.65rem; flex-wrap: wrap; gap: 0.4rem;">
                <h4 style="margin: 0; font-size: 0.88rem; font-weight: 700; color: #22d3ee; display: flex; align-items: center; gap: 6px;">
                    <span>📄</span> Official V5C Logbook (Final DVLA Document)
                    <span class="badge" style="background: rgba(6,182,212,0.15); color: #22d3ee; font-size: 0.72rem; padding: 1px 6px;">${officialV5Cs.length}</span>
                </h4>
                ${officialV5Cs.length > 0 
                    ? `<span style="font-size: 0.74rem; color: #4ade80; font-weight: 600; background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); padding: 2px 8px; border-radius: 4px;">✓ Logbook Received &amp; Verified</span>` 
                    : `<span style="font-size: 0.74rem; color: #f87171; font-weight: 600; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); padding: 2px 8px; border-radius: 4px;">⚠️ Official Logbook Not on File</span>`}
            </div>
            ${officialV5Cs.length > 0 ? `
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.85rem;">
                    ${officialV5Cs.map(renderV5CCard).join('')}
                </div>
            ` : `
                <div style="padding: 0.75rem 1rem; border: 1px dashed rgba(239,68,68,0.3); border-radius: 8px; font-size: 0.78rem; color: #fca5a5; background: rgba(239,68,68,0.06); display: flex; align-items: center; gap: 8px;">
                    <span>⚠️</span> Official V5C Logbook not yet received from DVLA. Missing V5C alert remains active until uploaded.
                </div>
            `}
        </div>
    `;
}

// Render Trackers list
function renderTrackersList(trackersList) {
    const container = document.getElementById('trackersListContainer');
    const countBadge = document.getElementById('badgeCountTrackers');
    const headerCount = document.getElementById('trackersCountHeader');
    
    const count = trackersList ? trackersList.length : 0;
    if (countBadge) countBadge.textContent = count;
    if (headerCount) headerCount.textContent = count;

    if (!container) return;
    if (!trackersList || trackersList.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; color: var(--text-secondary); padding: 1.5rem 1rem; border: 1px dashed var(--border-color); border-radius: 12px; background: rgba(255,255,255,0.01);">
                <div style="font-size: 1.8rem; margin-bottom: 0.4rem; opacity: 0.7;">📡</div>
                <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem;">No GPS Trackers Installed</div>
                <div style="font-size: 0.8rem;">You can register multiple trackers (Company or Customer owned) below with photos of the IMEI / serial sticker.</div>
            </div>
        `;
        return;
    }

    container.innerHTML = trackersList.map((t) => {
        const isCompany = (t.tipo_propriedade || '').toLowerCase() === 'company';
        const ownershipBadge = isCompany ? `
            <span class="badge" style="background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.35); font-weight: 600; font-size: 0.78rem;">
                🏢 FF Motors (Nosso Tracker)
            </span>
        ` : `
            <span class="badge" style="background: rgba(168,85,247,0.15); color: #c084fc; border: 1px solid rgba(168,85,247,0.35); font-weight: 600; font-size: 0.78rem;">
                👤 Customer (Do Cliente)
            </span>
        `;

        const dateStr = t.data_instalacao ? t.data_instalacao.substring(0, 10) : '';

        // Photos gallery
        const photos = t.fotos || [];
        const photosHtml = photos.length > 0 ? `
            <div style="margin-top: 0.75rem;">
                <div style="font-size: 0.75rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.4rem;">
                    📸 Tracker Serial &amp; Fitting Photos (${photos.length}):
                </div>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    ${photos.map((pUrl, pIdx) => `
                        <div style="position: relative; width: 75px; height: 75px; border-radius: 8px; overflow: hidden; border: 1px solid var(--border-color); cursor: pointer; background: #000;" onclick="abrirLightbox('${escapeHtml(pUrl)}', 'Tracker ${escapeHtml(t.numero)} - Photo ${pIdx + 1}')" title="Click to enlarge & zoom photo">
                            <img src="${escapeHtml(pUrl)}" alt="Tracker Photo" style="width: 100%; height: 100%; object-fit: cover; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.08)'" onmouseout="this.style.transform='scale(1)'">
                            <span style="position: absolute; bottom: 3px; right: 3px; background: rgba(0,0,0,0.75); backdrop-filter: blur(3px); color: #fff; font-size: 0.6rem; padding: 1px 4px; border-radius: 4px; pointer-events: none; border: 1px solid rgba(255,255,255,0.2);">🔍</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        ` : `
            <div style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--text-secondary); font-style: italic;">
                No serial photos attached for this tracker.
            </div>
        `;

        return `
            <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 1.1rem; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.5rem;">
                    <div>
                        <div style="display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;">
                            <span style="font-size: 1.1rem;">📡</span>
                            <span style="font-size: 1rem; font-weight: 700; color: var(--text-primary); font-family: monospace; letter-spacing: 0.5px;">
                                ${escapeHtml(t.numero)}
                            </span>
                            ${ownershipBadge}
                        </div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.3rem;">
                            ${dateStr ? `Registered on ${dateStr}` : ''} ${t.instalado_por_nome ? `by ${escapeHtml(t.instalado_por_nome)}` : ''}
                        </div>
                    </div>

                    <button type="button" class="btn-danger" style="padding: 0.4rem 0.8rem; font-size: 0.78rem; cursor: pointer; background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); border-radius: 6px; display: inline-flex; align-items: center; gap: 4px;" onclick="removerTracker(${t.id}, '${escapeHtml(t.numero)}')">
                        <span>🗑️ Remove Tracker</span>
                    </button>
                </div>

                ${t.observacoes ? `
                    <div style="margin-top: 0.65rem; padding: 0.55rem 0.75rem; background: rgba(255,255,255,0.02); border-left: 3px solid var(--accent); border-radius: 4px; font-size: 0.82rem; color: var(--text-primary);">
                        <strong>Notes:</strong> ${escapeHtml(t.observacoes)}
                    </div>
                ` : ''}

                ${photosHtml}
            </div>
        `;
    }).join('');
}

// Load Moto Details (Info + V5C + Trackers)
async function carregarDetalhesMoto(placa) {
    try {
        const res = await fetch(`/api/motos/${encodeURIComponent(placa)}/detalhes`);
        if (!res.ok) throw new Error('Failed to fetch details');
        const data = await res.json();
        
        // Update basic form values if fields exist
        const editPlaca = document.getElementById('edit_placa');
        if (editPlaca) editPlaca.value = data.placa;
        const dispPlaca = document.getElementById('modalDisplayPlaca');
        if (dispPlaca) dispPlaca.textContent = data.placa;
        const dispModelo = document.getElementById('modalDisplayModelo');
        if (dispModelo) dispModelo.textContent = data.modelo || '';
        
        const editModelo = document.getElementById('edit_modelo');
        if (editModelo) editModelo.value = data.modelo || '';
        const editCor = document.getElementById('edit_cor');
        if (editCor) editCor.value = data.cor || '';
        const editMilhagem = document.getElementById('edit_milhagem');
        if (editMilhagem) editMilhagem.value = data.milhagem_atual || '0';
        const editStatus = document.getElementById('edit_status');
        if (editStatus) editStatus.value = data.status || 'Available';
        const editMot = document.getElementById('edit_mot');
        if (editMot) editMot.value = data.vencimento_mot || '';
        const editTax = document.getElementById('edit_tax');
        const editTaxSorn = document.getElementById('edit_tax_sorn');
        if (editTaxSorn) {
            editTaxSorn.checked = !!data.tax_sorn;
            updateModalTaxSornState();
        }
        if (!data.tax_sorn && editTax) {
            editTax.value = data.vencimento_tax || '';
        }
        const editNotas = document.getElementById('edit_moto_notas');
        if (editNotas) editNotas.value = data.notas_internas || '';

        renderV5CList(data.v5c_arquivos || []);
        renderTrackersList(data.trackers || []);
    } catch(err) {
        console.error('Error loading moto details:', err);
    }
}

// Open Manage Modal
async function abrirModalMoto(placa, activeTab = 'tabInfo', initialData = null) {
    if (!placa || placa === '-') {
        alert('No motorbike registration plate available for this action.');
        return;
    }
    
    currentMotoPlaca = placa;
    currentContratoId = (initialData && initialData.id_contrato) ? initialData.id_contrato : null;
    
    // Fill basic details from initialData or cache if available
    const dispPlaca = document.getElementById('modalDisplayPlaca');
    if (dispPlaca) dispPlaca.textContent = placa;
    const editPlaca = document.getElementById('edit_placa');
    if (editPlaca) editPlaca.value = placa;
    
    if (initialData) {
        const dispModelo = document.getElementById('modalDisplayModelo');
        if (dispModelo) dispModelo.textContent = initialData.modelo || '';
        const editModelo = document.getElementById('edit_modelo');
        if (editModelo) editModelo.value = initialData.modelo || '';
        const editCor = document.getElementById('edit_cor');
        if (editCor) editCor.value = initialData.cor || '';
        const editMilhagem = document.getElementById('edit_milhagem');
        if (editMilhagem) editMilhagem.value = initialData.milhagem_atual || '0';
        const editStatus = document.getElementById('edit_status');
        if (editStatus) editStatus.value = initialData.status || 'Available';
        const editMot = document.getElementById('edit_mot');
        if (editMot) editMot.value = initialData.vencimento_mot || '';
        const editTax = document.getElementById('edit_tax');
        const editTaxSorn = document.getElementById('edit_tax_sorn');
        if (editTaxSorn) {
            editTaxSorn.checked = !!(initialData && initialData.tax_sorn);
            updateModalTaxSornState();
        }
        if (!(initialData && initialData.tax_sorn) && editTax) {
            editTax.value = (initialData && initialData.vencimento_tax) || '';
        }
        const editNotas = document.getElementById('edit_moto_notas');
        if (editNotas) editNotas.value = (initialData && initialData.notas_internas) || '';
    }
    
    // Reset V5C staged accumulator
    selectedV5CFiles = [];
    const radioV5C = document.getElementById('docTypeV5C');
    if (radioV5C) radioV5C.checked = true;
    updateV5CDocCategoryUI();
    renderV5CStagedPreview();
    const v5cStatus = document.getElementById('v5cUploadStatus');
    if (v5cStatus) v5cStatus.style.display = 'none';

    // Reset tracker photo accumulator
    selectedTrackerPhotos = [];
    renderTrackerPhotosPreview();
    const trackerForm = document.getElementById('addTrackerForm');
    if (trackerForm) trackerForm.reset();
    
    // Switch to desired tab
    alternarAba(activeTab);

    // Show modal using .active CSS class (mandatory for .modal-overlay)
    const modal = document.getElementById('motoManageModal');
    if (modal) {
        modal.classList.add('active');
    }

    // Fetch full details (V5C + Trackers)
    await carregarDetalhesMoto(placa);
}

function fecharModalMoto() {
    const modal = document.getElementById('motoManageModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// Tracker photo accumulator UI
function renderTrackerPhotosPreview() {
    const container = document.getElementById('trackerPhotosPreview');
    if (!container) return;

    if (selectedTrackerPhotos.length === 0) {
        container.innerHTML = '<span style="font-size: 0.75rem; color: var(--text-secondary); font-style: italic;">No photos staged. You can take multiple photos or pick from gallery.</span>';
        return;
    }

    container.innerHTML = selectedTrackerPhotos.map((file, idx) => {
        const tempUrl = URL.createObjectURL(file);
        return `
            <div style="position: relative; width: 70px; height: 70px; border-radius: 8px; overflow: hidden; border: 1px solid var(--accent); cursor: pointer;" onclick="abrirLightbox('${tempUrl}', 'Staged Tracker Photo ${idx + 1}')" title="Click to preview & zoom">
                <img src="${tempUrl}" alt="Preview" style="width: 100%; height: 100%; object-fit: cover;">
                <span style="position: absolute; bottom: 2px; right: 2px; background: rgba(0,0,0,0.75); color: #fff; font-size: 0.55rem; padding: 1px 3px; border-radius: 3px; pointer-events: none;">🔍</span>
                <button type="button" onclick="event.stopPropagation(); removerFotoStaged(${idx});" style="position: absolute; top: 2px; right: 2px; background: rgba(0,0,0,0.75); color: #ef4444; border: none; border-radius: 50%; width: 20px; height: 20px; font-size: 12px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; line-height: 1; z-index: 2;" title="Remove photo">&times;</button>
            </div>
        `;
    }).join('');
}

function removerFotoStaged(index) {
    selectedTrackerPhotos.splice(index, 1);
    renderTrackerPhotosPreview();
}

// SORN Toggle UI State helper for Moto Modal
function updateModalTaxSornState() {
    const editTax = document.getElementById('edit_tax');
    const editTaxSorn = document.getElementById('edit_tax_sorn');
    const editTaxHelp = document.getElementById('edit_tax_help_text');
    if (!editTax || !editTaxSorn) return;

    if (editTaxSorn.checked) {
        editTax.disabled = true;
        editTax.value = '';
        editTax.style.opacity = '0.4';
        if (editTaxHelp) editTaxHelp.innerHTML = '<span style="color:#c084fc; font-weight:600;">🛡️ SORN (Off Road) - No road tax expiry required</span>';
    } else {
        editTax.disabled = false;
        editTax.style.opacity = '1';
        if (editTaxHelp) editTaxHelp.textContent = 'UK DVLA Road Tax (VED)';
    }
}

// Helper to get selected V5C / Transfer Proof document category
function getSelectedV5CCategory() {
    const radio = document.querySelector('input[name="v5cDocCategory"]:checked');
    return radio ? radio.value : 'v5c';
}

function updateV5CDocCategoryUI() {
    const isTransfer = getSelectedV5CCategory() === 'transfer_proof';
    const lblV5C = document.getElementById('lblDocTypeV5C');
    const lblTransfer = document.getElementById('lblDocTypeTransfer');
    const hint = document.getElementById('v5cUploadHint');
    const btnUpload = document.getElementById('btnUploadV5C');
    const stagedTitle = document.getElementById('v5cStagedTitle');
    const count = selectedV5CFiles.length;

    if (lblV5C && lblTransfer) {
        if (isTransfer) {
            lblTransfer.style.borderColor = '#fbbf24';
            lblTransfer.style.background = 'rgba(245,158,11,0.14)';
            lblV5C.style.borderColor = 'rgba(255,255,255,0.1)';
            lblV5C.style.background = 'rgba(255,255,255,0.02)';
        } else {
            lblV5C.style.borderColor = '#22d3ee';
            lblV5C.style.background = 'rgba(6,182,212,0.12)';
            lblTransfer.style.borderColor = 'rgba(255,255,255,0.1)';
            lblTransfer.style.background = 'rgba(255,255,255,0.02)';
        }
    }

    if (hint) {
        if (isTransfer) {
            hint.style.borderLeftColor = '#fbbf24';
            hint.textContent = 'Attach photo of the Green New Keeper Slip (V5C/2) or DVLA Online Transfer PDF. The system stores proof of ownership while keeping the "Waiting for V5C" alert active until the postal logbook arrives.';
        } else {
            hint.style.borderLeftColor = '#22d3ee';
            hint.textContent = 'Attach photos of the official V5C logbook pages or digital PDF certificate. Uploading this completes registration compliance and clears the missing V5C alert.';
        }
    }

    if (stagedTitle) {
        const docLabel = isTransfer ? 'Transfer Slip Files' : 'Official V5C Pages';
        stagedTitle.innerHTML = `Queued ${docLabel} (<span id="v5cStagedCount">${count}</span>):`;
    }

    if (btnUpload) {
        const docTarget = isTransfer ? 'Transfer Proof' : 'Official V5C';
        btnUpload.innerHTML = count > 0 
            ? `<span>⬆️</span> Upload to ${docTarget} (${count} file${count > 1 ? 's' : ''})`
            : `<span>⬆️</span> Upload to ${docTarget} (0 files)`;
    }
}

// Format bytes helper for V5C staged files
function formatV5CFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// V5C Staged pages preview UI (Multi-shot camera accumulator)
function renderV5CStagedPreview() {
    const container = document.getElementById('v5cStagedContainer');
    const previewGrid = document.getElementById('v5cStagedPreview');
    const stagedCount = document.getElementById('v5cStagedCount');
    const btnUpload = document.getElementById('btnUploadV5C');
    const btnClear = document.getElementById('btnClearV5CStaged');

    if (!container || !previewGrid || !btnUpload) return;

    const count = selectedV5CFiles.length;
    if (stagedCount) stagedCount.textContent = count;

    const isTransfer = getSelectedV5CCategory() === 'transfer_proof';
    const docTarget = isTransfer ? 'Transfer Proof' : 'Official V5C';

    if (count === 0) {
        container.style.display = 'none';
        previewGrid.innerHTML = '';
        if (btnClear) btnClear.style.display = 'none';
        btnUpload.disabled = true;
        btnUpload.innerHTML = `<span>⬆️</span> Upload to ${docTarget} (0 files)`;
        return;
    }

    container.style.display = 'block';
    if (btnClear) btnClear.style.display = 'inline-flex';
    btnUpload.disabled = false;
    btnUpload.innerHTML = `<span>⬆️</span> Upload to ${docTarget} (${count} file${count > 1 ? 's' : ''})`;

    previewGrid.innerHTML = selectedV5CFiles.map((file, idx) => {
        const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
        const sizeStr = formatV5CFileSize(file.size);
        const pageLabel = `Page ${idx + 1}`;
        const tempUrl = isPdf ? null : URL.createObjectURL(file);

        const visual = isPdf ? `
            <div style="width: 80px; height: 80px; background: rgba(239,68,68,0.12); display: flex; flex-direction: column; align-items: center; justify-content: center; border-radius: 8px; border: 1px solid rgba(239,68,68,0.3);">
                <span style="font-size: 1.8rem;">📑</span>
                <span style="font-size: 0.65rem; font-weight: 700; color: #ef4444; margin-top: 2px;">PDF</span>
            </div>
        ` : `
            <div style="width: 80px; height: 80px; background: #000; border-radius: 8px; overflow: hidden; border: 1px solid var(--accent); position: relative; cursor: pointer;" onclick="abrirLightbox('${tempUrl}', 'Staged ${escapeHtml(file.name)}')" title="Click to preview & zoom">
                <img src="${tempUrl}" alt="${pageLabel}" style="width: 100%; height: 100%; object-fit: cover;">
                <span style="position: absolute; bottom: 2px; right: 2px; background: rgba(0,0,0,0.75); color: #fff; font-size: 0.55rem; padding: 1px 3px; border-radius: 3px; pointer-events: none;">🔍</span>
            </div>
        `;

        return `
            <div style="position: relative; display: flex; flex-direction: column; align-items: center; width: 84px; text-align: center; background: rgba(255,255,255,0.03); padding: 4px; border-radius: 10px; border: 1px solid var(--border-color);">
                ${visual}
                <button type="button" onclick="removerV5CStaged(${idx})" style="position: absolute; top: 1px; right: 1px; background: rgba(0,0,0,0.85); color: #ef4444; border: 1px solid rgba(239,68,68,0.5); border-radius: 50%; width: 22px; height: 22px; font-size: 13px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; line-height: 1; z-index: 2;" title="Remove this page">&times;</button>
                <div style="font-size: 0.72rem; font-weight: 600; color: var(--text-primary); margin-top: 4px; width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(file.name)}">
                    ${pageLabel}
                </div>
                <div style="font-size: 0.65rem; color: var(--text-secondary);">
                    ${sizeStr}
                </div>
            </div>
        `;
    }).join('');
}

function removerV5CStaged(index) {
    selectedV5CFiles.splice(index, 1);
    renderV5CStagedPreview();
}

function limparV5CStaged() {
    selectedV5CFiles = [];
    renderV5CStagedPreview();
}

// Remove Tracker
async function removerTracker(trackerId, numero) {
    if (!confirm(`Are you sure you want to remove tracker #${numero} from motorbike ${currentMotoPlaca}?\n\nThis will also permanently delete any serial and fitting photos associated with this tracker.`)) {
        return;
    }

    try {
        const res = await fetch(`/api/motos/${encodeURIComponent(currentMotoPlaca)}/trackers/${trackerId}`, {
            method: 'DELETE'
        });
        const result = await res.json();
        if (res.ok) {
            await carregarDetalhesMoto(currentMotoPlaca);
            if (typeof window.onMotoModalUpdated === 'function') {
                window.onMotoModalUpdated(currentMotoPlaca);
            }
        } else {
            alert(result.erro || result.error || 'Failed to remove tracker');
        }
    } catch(err) {
        alert('Network error while removing tracker');
    }
}

// Remove V5C or Transfer Proof document
async function removerV5C(v5cId) {
    if (!confirm(`Are you sure you want to delete this document from motorbike ${currentMotoPlaca}?`)) {
        return;
    }

    try {
        const res = await fetch(`/api/motos/${encodeURIComponent(currentMotoPlaca)}/v5c/${v5cId}`, {
            method: 'DELETE'
        });
        const result = await res.json();
        if (res.ok) {
            await carregarDetalhesMoto(currentMotoPlaca);
            if (typeof window.onMotoModalUpdated === 'function') {
                window.onMotoModalUpdated(currentMotoPlaca);
            }
        } else {
            alert(result.erro || result.error || 'Failed to remove V5C document');
        }
    } catch(err) {
        alert('Network error while removing V5C');
    }
}

// Bind global functions to window
window.abrirModalMoto = abrirModalMoto;
window.fecharModalMoto = fecharModalMoto;
window.abrirLightbox = abrirLightbox;
window.fecharLightbox = fecharLightbox;
window.toggleLightboxZoom = toggleLightboxZoom;
window.alternarAba = alternarAba;
window.removerV5C = removerV5C;
window.removerTracker = removerTracker;
window.removerFotoStaged = removerFotoStaged;
window.removerV5CStaged = removerV5CStaged;
window.limparV5CStaged = limparV5CStaged;
window.updateModalTaxSornState = updateModalTaxSornState;

// Global initializer for modal DOM elements
document.addEventListener('DOMContentLoaded', () => {
    // Modal Close
    const modal = document.getElementById('motoManageModal');
    const closeBtn = document.getElementById('closeMotoModal');
    if (closeBtn) closeBtn.addEventListener('click', fecharModalMoto);
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) fecharModalMoto();
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

    // Keyboard ESC listener for Lightbox
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' || e.key === 'Esc') {
            const lb = document.getElementById('lightboxModal');
            if (lb && lb.classList.contains('active')) {
                fecharLightbox();
            }
        }
    });

    // Tab Buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            alternarAba(targetTab);
        });
    });

    // Save Moto Basic Info Form
    const editMotoForm = document.getElementById('editMotoForm');
    if (editMotoForm) {
        editMotoForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const placa = document.getElementById('edit_placa').value;
            const btnSave = document.getElementById('btnSaveMotoInfo');
            if (btnSave) btnSave.disabled = true;

            const editTaxSorn = document.getElementById('edit_tax_sorn');
            const isSorn = editTaxSorn ? editTaxSorn.checked : false;

            const data = {
                modelo: document.getElementById('edit_modelo').value,
                cor: document.getElementById('edit_cor').value,
                status: document.getElementById('edit_status').value,
                milhagem_atual: parseInt(document.getElementById('edit_milhagem').value || '0', 10),
                vencimento_mot: document.getElementById('edit_mot').value || null,
                vencimento_tax: isSorn ? null : (document.getElementById('edit_tax').value || null),
                tax_sorn: isSorn,
                notas_internas: document.getElementById('edit_moto_notas') ? document.getElementById('edit_moto_notas').value.trim() : null
            };
            
            try {
                const response = await fetch(`/api/motos/${encodeURIComponent(placa)}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (response.ok) {
                    fecharModalMoto();
                    if (typeof window.onMotoModalUpdated === 'function') {
                        window.onMotoModalUpdated(placa);
                    }
                } else {
                    const res = await response.json();
                    alert(res.message || res.mensagem || res.erro || res.error || 'Failed to update motorbike');
                }
            } catch(err) {
                alert('Connection error');
            } finally {
                if (btnSave) btnSave.disabled = false;
            }
        });
    }

    // SORN Checkbox Handler
    const editTaxSorn = document.getElementById('edit_tax_sorn');
    if (editTaxSorn) {
        editTaxSorn.addEventListener('change', updateModalTaxSornState);
    }

    // V5C Camera & Gallery Multi-Shot Handlers (Accumulator)
    const btnV5CCamera = document.getElementById('btnV5CCamera');
    const v5cCameraInput = document.getElementById('v5cCameraInput');
    const btnV5CGallery = document.getElementById('btnV5CGallery');
    const v5cGalleryInput = document.getElementById('v5cGalleryInput');
    const btnClearV5CStaged = document.getElementById('btnClearV5CStaged');
    const btnUploadV5C = document.getElementById('btnUploadV5C');
    const v5cUploadForm = document.getElementById('v5cUploadForm');
    const v5cUploadStatus = document.getElementById('v5cUploadStatus');

    if (btnV5CCamera && v5cCameraInput) {
        btnV5CCamera.addEventListener('click', () => v5cCameraInput.click());
        v5cCameraInput.addEventListener('change', () => {
            if (v5cCameraInput.files && v5cCameraInput.files.length > 0) {
                for (let i = 0; i < v5cCameraInput.files.length; i++) {
                    selectedV5CFiles.push(v5cCameraInput.files[i]);
                }
                v5cCameraInput.value = ''; // Reset so iPhone camera can take multiple page photos consecutively
                renderV5CStagedPreview();
            }
        });
    }

    if (btnV5CGallery && v5cGalleryInput) {
        btnV5CGallery.addEventListener('click', () => v5cGalleryInput.click());
        v5cGalleryInput.addEventListener('change', () => {
            if (v5cGalleryInput.files && v5cGalleryInput.files.length > 0) {
                for (let i = 0; i < v5cGalleryInput.files.length; i++) {
                    selectedV5CFiles.push(v5cGalleryInput.files[i]);
                }
                v5cGalleryInput.value = '';
                renderV5CStagedPreview();
            }
        });
    }

    if (btnClearV5CStaged) {
        btnClearV5CStaged.addEventListener('click', limparV5CStaged);
    }

    // V5C Document Category radio selection listener
    document.querySelectorAll('input[name="v5cDocCategory"]').forEach(radio => {
        radio.addEventListener('change', () => {
            updateV5CDocCategoryUI();
            renderV5CStagedPreview();
        });
    });

    if (v5cUploadForm) {
        v5cUploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!selectedV5CFiles || selectedV5CFiles.length === 0) return;
            if (!currentMotoPlaca) return;

            const count = selectedV5CFiles.length;
            const catDoc = getSelectedV5CCategory();
            const isTransfer = catDoc === 'transfer_proof';
            const catLabel = isTransfer ? 'Transfer Slip' : 'Official V5C';

            const formData = new FormData();
            formData.append('categoria_doc', catDoc);
            if (currentContratoId) {
                formData.append('id_contrato', currentContratoId);
            }
            selectedV5CFiles.forEach(file => {
                formData.append('v5c_arquivos', file);
            });

            if (btnUploadV5C) {
                btnUploadV5C.disabled = true;
                btnUploadV5C.innerHTML = `<span>⏳</span> Uploading ${count} ${catLabel} page(s)...`;
            }
            if (v5cUploadStatus) {
                v5cUploadStatus.style.display = 'block';
                v5cUploadStatus.style.color = isTransfer ? '#fbbf24' : '#22d3ee';
                v5cUploadStatus.textContent = `Uploading ${count} ${catLabel} file(s) to motorbike ${currentMotoPlaca}...`;
            }

            try {
                const res = await fetch(`/api/motos/${encodeURIComponent(currentMotoPlaca)}/v5c`, {
                    method: 'POST',
                    body: formData
                });
                const result = await res.json();
                if (res.ok) {
                    selectedV5CFiles = [];
                    updateV5CDocCategoryUI();
                    renderV5CStagedPreview();
                    if (v5cUploadStatus) {
                        v5cUploadStatus.style.color = '#4ade80';
                        v5cUploadStatus.textContent = result.message || result.mensagem || `${count} ${catLabel} file(s) uploaded successfully!`;
                        setTimeout(() => {
                            if (v5cUploadStatus) v5cUploadStatus.style.display = 'none';
                        }, 4000);
                    }
                    await carregarDetalhesMoto(currentMotoPlaca);
                    if (typeof window.onMotoModalUpdated === 'function') {
                        window.onMotoModalUpdated(currentMotoPlaca);
                    }
                } else {
                    const errMsg = result.erro || result.error || 'Failed to upload document(s)';
                    if (v5cUploadStatus) {
                        v5cUploadStatus.style.color = '#ef4444';
                        v5cUploadStatus.textContent = errMsg;
                    }
                    alert(errMsg);
                }
            } catch(err) {
                if (v5cUploadStatus) {
                    v5cUploadStatus.style.color = '#ef4444';
                    v5cUploadStatus.textContent = 'Connection error uploading files';
                }
                alert('Connection error uploading files');
            } finally {
                if (btnUploadV5C) {
                    const remaining = selectedV5CFiles.length;
                    const curCat = getSelectedV5CCategory();
                    const docTarget = curCat === 'transfer_proof' ? 'Transfer Proof' : 'Official V5C';
                    btnUploadV5C.disabled = remaining === 0;
                    btnUploadV5C.innerHTML = remaining > 0
                        ? `<span>⬆️</span> Upload to ${docTarget} (${remaining} page${remaining > 1 ? 's' : ''})`
                        : `<span>⬆️</span> Upload to ${docTarget} (0 files)`;
                }
            }
        });
    }

    // Tracker Camera & Gallery Handlers (Accumulator)
    const btnTrackerCamera = document.getElementById('btnTrackerCamera');
    const trackerCameraInput = document.getElementById('trackerCameraInput');
    const btnTrackerGallery = document.getElementById('btnTrackerGallery');
    const trackerGalleryInput = document.getElementById('trackerGalleryInput');

    if (btnTrackerCamera && trackerCameraInput) {
        btnTrackerCamera.addEventListener('click', () => trackerCameraInput.click());
        trackerCameraInput.addEventListener('change', () => {
            if (trackerCameraInput.files && trackerCameraInput.files.length > 0) {
                for (let i = 0; i < trackerCameraInput.files.length; i++) {
                    selectedTrackerPhotos.push(trackerCameraInput.files[i]);
                }
                trackerCameraInput.value = ''; // Reset so mobile camera can be used repeatedly
                renderTrackerPhotosPreview();
            }
        });
    }

    if (btnTrackerGallery && trackerGalleryInput) {
        btnTrackerGallery.addEventListener('click', () => trackerGalleryInput.click());
        trackerGalleryInput.addEventListener('change', () => {
            if (trackerGalleryInput.files && trackerGalleryInput.files.length > 0) {
                for (let i = 0; i < trackerGalleryInput.files.length; i++) {
                    selectedTrackerPhotos.push(trackerGalleryInput.files[i]);
                }
                trackerGalleryInput.value = '';
                renderTrackerPhotosPreview();
            }
        });
    }

    // Toggle Add Tracker Box
    const btnToggleAddTracker = document.getElementById('btnToggleAddTracker');
    const boxAddTracker = document.getElementById('boxAddTracker');
    if (btnToggleAddTracker && boxAddTracker) {
        btnToggleAddTracker.addEventListener('click', () => {
            const isHidden = boxAddTracker.style.display === 'none';
            boxAddTracker.style.display = isHidden ? 'block' : 'none';
            btnToggleAddTracker.textContent = isHidden ? '- Hide Tracker Form' : '+ Add Another Tracker';
        });
    }

    // Add Tracker Form Submission
    const addTrackerForm = document.getElementById('addTrackerForm');
    const btnSubmitTracker = document.getElementById('btnSubmitTracker');
    if (addTrackerForm) {
        addTrackerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!currentMotoPlaca) return;

            const numero = document.getElementById('tracker_numero').value.trim();
            const propriedade = document.getElementById('tracker_propriedade').value;
            const observacoes = document.getElementById('tracker_observacoes').value.trim();

            if (!numero) {
                alert('Please provide the tracker serial number or IMEI.');
                return;
            }

            const formData = new FormData();
            formData.append('numero', numero);
            formData.append('tipo_propriedade', propriedade);
            formData.append('observacoes', observacoes);

            // Append all accumulated tracker photos
            selectedTrackerPhotos.forEach(file => {
                formData.append('fotos', file);
            });

            if (btnSubmitTracker) {
                btnSubmitTracker.disabled = true;
                btnSubmitTracker.textContent = 'Saving Tracker...';
            }

            try {
                const res = await fetch(`/api/motos/${encodeURIComponent(currentMotoPlaca)}/trackers`, {
                    method: 'POST',
                    body: formData
                });
                const result = await res.json();
                if (res.ok) {
                    addTrackerForm.reset();
                    selectedTrackerPhotos = [];
                    renderTrackerPhotosPreview();
                    await carregarDetalhesMoto(currentMotoPlaca);
                    if (typeof window.onMotoModalUpdated === 'function') {
                        window.onMotoModalUpdated(currentMotoPlaca);
                    }
                } else {
                    const numInput = document.getElementById('tracker_numero');
                    if (numInput) {
                        numInput.style.borderColor = '#ef4444';
                        numInput.focus();
                    }
                    alert(result.erro || result.error || 'Failed to register tracker');
                }
            } catch(err) {
                alert('Connection error registering tracker');
            } finally {
                if (btnSubmitTracker) {
                    btnSubmitTracker.disabled = false;
                    btnSubmitTracker.textContent = 'Save Tracker on Motorbike';
                }
            }
        });
    }
});
