/**
 * FF Motors - Shared Motorbike Management Modal (V5C Logbook & GPS Trackers)
 * Used across /motos and /contratos/<id>
 */

let currentMotoPlaca = null;
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

// Lightbox logic
function abrirLightbox(url, caption = '') {
    const modal = document.getElementById('lightboxModal');
    const img = document.getElementById('lightboxImg');
    const cap = document.getElementById('lightboxCaption');
    if (!modal || !img) return;
    img.src = url;
    if (cap) cap.textContent = caption;
    modal.classList.add('active');
}

function fecharLightbox() {
    const modal = document.getElementById('lightboxModal');
    if (modal) modal.classList.remove('active');
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

// Render V5C list
function renderV5CList(v5cList) {
    const container = document.getElementById('v5cListContainer');
    const countBadge = document.getElementById('badgeCountV5C');
    if (countBadge) countBadge.textContent = v5cList.length;

    if (!container) return;
    if (!v5cList || v5cList.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; color: var(--text-secondary); padding: 2rem 1rem; border: 1px dashed var(--border-color); border-radius: 12px; background: rgba(255,255,255,0.01);">
                <div style="font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.7;">📄</div>
                <div style="font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem;">No V5C Documents Attached</div>
                <div style="font-size: 0.8rem;">Attach photos of the V5C logbook pages or the digital PDF certificate above.</div>
            </div>
        `;
        return;
    }

    container.innerHTML = v5cList.map((doc, idx) => {
        const isPdf = doc.tipo_arquivo === 'pdf';
        const dateStr = doc.data_criacao ? doc.data_criacao.substring(0, 10) : '';
        const previewHtml = isPdf ? `
            <div style="height: 120px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: rgba(239,68,68,0.08); border-bottom: 1px solid var(--border-color);">
                <span style="font-size: 2.5rem;">📑</span>
                <span style="font-size: 0.75rem; font-weight: 700; color: #ef4444; margin-top: 4px;">PDF DOCUMENT</span>
            </div>
        ` : `
            <div style="height: 120px; overflow: hidden; background: #000; display: flex; align-items: center; justify-content: center; border-bottom: 1px solid var(--border-color); cursor: pointer;" onclick="abrirLightbox('${escapeHtml(doc.url_arquivo)}', 'V5C - ${escapeHtml(doc.nome_original || 'Page ' + (idx + 1))}')">
                <img src="${escapeHtml(doc.url_arquivo)}" alt="V5C Page" style="width: 100%; height: 100%; object-fit: cover; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
            </div>
        `;

        const viewAction = isPdf ? `
            <a href="${escapeHtml(doc.url_arquivo)}" target="_blank" rel="noopener" class="btn-secondary" style="padding: 0.35rem 0.65rem; font-size: 0.75rem; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">
                <span>↗ Open</span>
            </a>
        ` : `
            <button type="button" class="btn-secondary" style="padding: 0.35rem 0.65rem; font-size: 0.75rem; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;" onclick="abrirLightbox('${escapeHtml(doc.url_arquivo)}', 'V5C - ${escapeHtml(doc.nome_original || 'Page ' + (idx + 1))}')">
                <span>🔍 Zoom</span>
            </button>
        `;

        return `
            <div style="background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; overflow: hidden; display: flex; flex-direction: column;">
                ${previewHtml}
                <div style="padding: 0.75rem; flex: 1; display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="font-size: 0.82rem; font-weight: 600; color: var(--text-primary); word-break: break-all; margin-bottom: 4px;" title="${escapeHtml(doc.nome_original)}">
                            ${escapeHtml(doc.nome_original || `V5C Attachment #${doc.id}`)}
                        </div>
                        <div style="font-size: 0.72rem; color: var(--text-secondary);">
                            ${dateStr ? `Added ${dateStr}` : ''} ${doc.criado_por_nome ? `by ${escapeHtml(doc.criado_por_nome)}` : ''}
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
    }).join('');
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
                        <div style="position: relative; width: 75px; height: 75px; border-radius: 8px; overflow: hidden; border: 1px solid var(--border-color); cursor: pointer; background: #000;" onclick="abrirLightbox('${escapeHtml(pUrl)}', 'Tracker ${escapeHtml(t.numero)} - Photo ${pIdx + 1}')">
                            <img src="${escapeHtml(pUrl)}" alt="Tracker Photo" style="width: 100%; height: 100%; object-fit: cover; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.08)'" onmouseout="this.style.transform='scale(1)'">
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
        if (editTax) editTax.value = data.vencimento_tax || '';

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
        if (editTax) editTax.value = initialData.vencimento_tax || '';
    }
    
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
            <div style="position: relative; width: 70px; height: 70px; border-radius: 8px; overflow: hidden; border: 1px solid var(--accent);">
                <img src="${tempUrl}" alt="Preview" style="width: 100%; height: 100%; object-fit: cover;">
                <button type="button" onclick="removerFotoStaged(${idx})" style="position: absolute; top: 2px; right: 2px; background: rgba(0,0,0,0.75); color: #ef4444; border: none; border-radius: 50%; width: 20px; height: 20px; font-size: 12px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; line-height: 1;" title="Remove photo">&times;</button>
            </div>
        `;
    }).join('');
}

function removerFotoStaged(index) {
    selectedTrackerPhotos.splice(index, 1);
    renderTrackerPhotosPreview();
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

// Remove V5C
async function removerV5C(v5cId) {
    if (!confirm(`Are you sure you want to delete this V5C document from motorbike ${currentMotoPlaca}?`)) {
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
window.alternarAba = alternarAba;
window.removerV5C = removerV5C;
window.removerTracker = removerTracker;
window.removerFotoStaged = removerFotoStaged;

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

    // Lightbox Close
    const closeLightboxBtn = document.getElementById('closeLightboxBtn');
    const lightboxModal = document.getElementById('lightboxModal');
    if (closeLightboxBtn) closeLightboxBtn.addEventListener('click', fecharLightbox);
    if (lightboxModal) {
        lightboxModal.addEventListener('click', (e) => {
            if (e.target === lightboxModal) fecharLightbox();
        });
    }

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

            const data = {
                modelo: document.getElementById('edit_modelo').value,
                cor: document.getElementById('edit_cor').value,
                status: document.getElementById('edit_status').value,
                milhagem_atual: parseInt(document.getElementById('edit_milhagem').value || '0', 10),
                vencimento_mot: document.getElementById('edit_mot').value || null,
                vencimento_tax: document.getElementById('edit_tax').value || null
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

    // V5C File Selection & Upload
    const btnChooseV5CFiles = document.getElementById('btnChooseV5CFiles');
    const v5cFileInput = document.getElementById('v5cFileInput');
    const v5cSelectedCount = document.getElementById('v5cSelectedCount');
    const btnUploadV5C = document.getElementById('btnUploadV5C');
    const v5cUploadForm = document.getElementById('v5cUploadForm');

    if (btnChooseV5CFiles && v5cFileInput) {
        btnChooseV5CFiles.addEventListener('click', () => v5cFileInput.click());
        v5cFileInput.addEventListener('change', () => {
            const files = v5cFileInput.files;
            if (files && files.length > 0) {
                v5cSelectedCount.textContent = `${files.length} file(s) selected`;
                if (btnUploadV5C) btnUploadV5C.disabled = false;
            } else {
                v5cSelectedCount.textContent = 'No file chosen';
                if (btnUploadV5C) btnUploadV5C.disabled = true;
            }
        });
    }

    if (v5cUploadForm) {
        v5cUploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!v5cFileInput.files || v5cFileInput.files.length === 0) return;
            if (!currentMotoPlaca) return;

            const formData = new FormData();
            for (let i = 0; i < v5cFileInput.files.length; i++) {
                formData.append('v5c_arquivos', v5cFileInput.files[i]);
            }

            btnUploadV5C.disabled = true;
            btnUploadV5C.textContent = 'Uploading...';

            try {
                const res = await fetch(`/api/motos/${encodeURIComponent(currentMotoPlaca)}/v5c`, {
                    method: 'POST',
                    body: formData
                });
                const result = await res.json();
                if (res.ok) {
                    v5cFileInput.value = '';
                    v5cSelectedCount.textContent = 'No file chosen';
                    await carregarDetalhesMoto(currentMotoPlaca);
                    if (typeof window.onMotoModalUpdated === 'function') {
                        window.onMotoModalUpdated(currentMotoPlaca);
                    }
                } else {
                    alert(result.erro || result.error || 'Failed to upload V5C documents');
                }
            } catch(err) {
                alert('Connection error uploading V5C files');
            } finally {
                btnUploadV5C.disabled = false;
                btnUploadV5C.textContent = 'Upload to V5C';
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
