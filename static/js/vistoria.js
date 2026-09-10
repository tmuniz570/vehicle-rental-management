document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('vistoriaForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const loader = submitBtn.querySelector('.loader');
    const feedbackMsg = document.getElementById('feedbackMessage');
    const idContratoInput = document.getElementById('id_contrato');
    const contratoSelect = document.getElementById('contrato_select');
    const contratoInfoFixed = document.getElementById('contratoInfoFixed');
    const selectTipo = document.getElementById('tipo');
    const fileInput = document.getElementById('fotos');
    const previewContainer = document.getElementById('previewContainer');

    // Pegar ID da URL se existir (ex: /vistorias/nova?id=1 ou ?tipo=Entrada)
    const urlParams = new URLSearchParams(window.location.search);
    const idUrl = urlParams.get('id') || urlParams.get('contrato_id');
    const tipoUrl = urlParams.get('tipo');

    if (tipoUrl) {
        selectTipo.value = tipoUrl;
    }

    if (idUrl) {
        idContratoInput.value = idUrl;
        if (contratoSelect) contratoSelect.style.display = 'none';
        if (contratoInfoFixed) {
            contratoInfoFixed.style.display = 'block';
            contratoInfoFixed.innerHTML = `Loading Contract #${idUrl}...`;
        }
        if (!tipoUrl) {
            selectTipo.value = 'Check-in'; // Default when returning a bike
        }

        // Update back navigation button
        const btnBack = document.getElementById('btnBackNav');
        if (btnBack) {
            btnBack.href = `/contratos/${idUrl}`;
            btnBack.innerHTML = `&larr; Back to Contract #${idUrl}`;
        }

        // Fetch contract details to show motorbike plate and customer
        fetch(`/api/contratos/${idUrl}`)
            .then(r => r.ok ? r.json() : null)
            .then(c => {
                if (c && contratoInfoFixed) {
                    const st = (c.status || '').toLowerCase();
                    const badgeClass = (st === 'active' || st === 'ativo') ? 'badge-success' : 'badge-warning';
                    contratoInfoFixed.innerHTML = `
                        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem;">
                            <span>Contract #${idUrl} &bull; <strong style="color: #60a5fa;">${c.placa || '-'}</strong> (${c.cliente || c.cliente_nome || '-'})</span>
                            <span class="badge ${badgeClass}">${c.status || ''}</span>
                        </div>
                    `;
                }
            })
            .catch(err => console.error("Error fetching contract info:", err));
    } else {
        // Load contracts
        try {
            const res = await fetch('/api/contratos?limit=100');
            const data = await res.json();
            const contratos = data.itens || [];

            if (contratos.length === 0) {
                contratoSelect.innerHTML = '<option value="">No contracts registered</option>';
            } else {
                contratoSelect.innerHTML = '<option value="">-- Select Contract --</option>';
                contratos.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.id;
                    opt.textContent = `Contract #${c.id} - ${c.placa} (${c.cliente_nome || c.cliente || ''}) [${c.status}]`;
                    contratoSelect.appendChild(opt);
                });
            }

            contratoSelect.addEventListener('change', () => {
                idContratoInput.value = contratoSelect.value;
            });
        } catch (err) {
            console.error("Error loading contracts:", err);
            contratoSelect.innerHTML = '<option value="">Failed to load contracts</option>';
        }
    }

    // Multi-photo accumulator for iPhone Camera & Gallery
    let selectedPhotos = [];
    const btnTakePhoto = document.getElementById('btnTakePhoto');
    const cameraInput = document.getElementById('cameraInput');
    const btnPickGallery = document.getElementById('btnPickGallery');
    const galleryInput = document.getElementById('galleryInput');
    const photoCountBadge = document.getElementById('photoCountBadge');

    if (btnTakePhoto && cameraInput) {
        btnTakePhoto.addEventListener('click', () => cameraInput.click());
        cameraInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                Array.from(e.target.files).forEach(file => selectedPhotos.push(file));
                cameraInput.value = '';
                renderPhotoPreviews();
            }
        });
    }

    if (btnPickGallery && galleryInput) {
        btnPickGallery.addEventListener('click', () => galleryInput.click());
        galleryInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                Array.from(e.target.files).forEach(file => selectedPhotos.push(file));
                galleryInput.value = '';
                renderPhotoPreviews();
            }
        });
    }

    function renderPhotoPreviews() {
        if (!previewContainer) return;
        previewContainer.innerHTML = '';
        
        if (photoCountBadge) {
            photoCountBadge.textContent = `${selectedPhotos.length} photo${selectedPhotos.length === 1 ? '' : 's'} added`;
            if (selectedPhotos.length > 0) {
                photoCountBadge.style.background = 'rgba(34, 197, 94, 0.15)';
                photoCountBadge.style.color = '#4ade80';
                photoCountBadge.style.borderColor = 'rgba(34, 197, 94, 0.3)';
            } else {
                photoCountBadge.style.background = 'rgba(255, 102, 0, 0.15)';
                photoCountBadge.style.color = 'var(--accent)';
                photoCountBadge.style.borderColor = 'rgba(255, 102, 0, 0.3)';
            }
        }

        if (selectedPhotos.length > 0) {
            previewContainer.style.display = 'grid';
            selectedPhotos.forEach((file, index) => {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const div = document.createElement('div');
                    div.className = 'photo-item';
                    div.style.aspectRatio = '1 / 1';
                    div.innerHTML = `
                        <span class="photo-badge-idx">#${index + 1}</span>
                        <button type="button" class="photo-remove-btn" title="Remove photo" onclick="removeVistoriaPhoto(${index})">&times;</button>
                        <img src="${e.target.result}" alt="Photo ${index + 1}">
                    `;
                    previewContainer.appendChild(div);
                };
                reader.readAsDataURL(file);
            });
        } else {
            previewContainer.style.display = 'none';
        }
    }

    window.removeVistoriaPhoto = function(index) {
        selectedPhotos.splice(index, 1);
        renderPhotoPreviews();
    };

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        feedbackMsg.classList.add('hidden');
        feedbackMsg.className = 'feedback-message hidden';
        
        const contratoId = idContratoInput.value.trim() || (contratoSelect ? contratoSelect.value.trim() : '');
        if (!contratoId) {
            showFeedback('Please select or specify a Contract.', 'error');
            return;
        }

        if (selectedPhotos.length === 0) {
            showFeedback('Please take or select at least one motorbike inspection photo.', 'error');
            return;
        }

        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');

        const formData = new FormData();
        formData.append('id_contrato', contratoId);
        formData.append('tipo', document.getElementById('tipo').value);
        formData.append('observacoes', document.getElementById('observacoes').value.trim());
        
        const options = {
            fileType: 'image/webp',
            maxSizeMB: 0.4,
            maxWidthOrHeight: 1920,
            useWebWorker: true
        };
        
        for (let i = 0; i < selectedPhotos.length; i++) {
            const file = selectedPhotos[i];
            if (file.type.startsWith('image/')) {
                try {
                    const compressedFile = await imageCompression(file, options);
                    formData.append('fotos', compressedFile, file.name.replace(/\.[^/.]+$/, ".webp"));
                } catch (err) {
                    formData.append('fotos', file);
                }
            } else {
                formData.append('fotos', file);
            }
        }

        try {
            const response = await fetch('/api/vistorias', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                showFeedback('Inspection saved successfully! Redirecting...', 'success');
                const redirectUrl = idUrl ? `/vistorias?contrato_id=${idUrl}` : '/vistorias';
                setTimeout(() => window.location.href = redirectUrl, 1500);
            } else {
                showFeedback(result.message || result.mensagem || result.error || result.erro || 'Failed to record inspection', 'error');
            }
        } catch (error) {
            showFeedback('Connection error with server.', 'error');
        } finally {
            submitBtn.disabled = false;
            btnText.classList.remove('hidden');
            loader.classList.add('hidden');
        }
    });

    function showFeedback(message, type) {
        feedbackMsg.textContent = message;
        feedbackMsg.classList.remove('hidden');
        feedbackMsg.className = `feedback-message feedback-${type}`;
    }
});

