document.addEventListener('DOMContentLoaded', async () => {
    const form = document.getElementById('contratoForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const loader = submitBtn.querySelector('.loader');
    const feedbackMsg = document.getElementById('feedbackMessage');

    const selectCliente = document.getElementById('id_cliente');
    const selectMoto = document.getElementById('placa');

    // Carregar Clientes e Motos
    try {
        const [resClientes, resMotos] = await Promise.all([
            fetch('/api/clientes?limit=1000'),
            fetch('/api/motos?limit=1000')
        ]);
        const dataClientes = await resClientes.json();
        const dataMotos = await resMotos.json();
        
        const clientes = dataClientes.itens || [];
        const motos = dataMotos.itens || [];

        selectCliente.innerHTML = '<option value="">-- Select Customer --</option>';
        clientes.forEach(c => {
            selectCliente.innerHTML += `<option value="${c.id}">${c.nome} (ID: ${c.id})</option>`;
        });

        selectMoto.innerHTML = '<option value="">-- Select Motorbike --</option>';
        motos.forEach(m => {
            const st = (m.status || '').toLowerCase();
            if (st === 'available' || st === 'disponível') {
                selectMoto.innerHTML += `<option value="${m.placa}">${m.placa} - ${m.modelo}</option>`;
            }
        });

    } catch (e) {
        showFeedback('Failed to load data. Please refresh the page.', 'error');
    }

    // Multi-photo accumulator for iPhone Camera & Gallery
    let selectedPhotos = [];
    const btnTakePhoto = document.getElementById('btnTakePhoto');
    const cameraInput = document.getElementById('cameraInput');
    const btnPickGallery = document.getElementById('btnPickGallery');
    const galleryInput = document.getElementById('galleryInput');
    const previewContainer = document.getElementById('previewContainer');
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
                        <button type="button" class="photo-remove-btn" title="Remove photo" onclick="removeNovoContratoPhoto(${index})">&times;</button>
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

    window.removeNovoContratoPhoto = function(index) {
        selectedPhotos.splice(index, 1);
        renderPhotoPreviews();
    };

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        feedbackMsg.classList.add('hidden');
        feedbackMsg.className = 'feedback-message hidden';

        if (selectedPhotos.length === 0) {
            showFeedback('Please take or select at least one check-out photo of the motorbike.', 'error');
            return;
        }
        
        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');

        const formData = new FormData();
        formData.append('id_cliente', document.getElementById('id_cliente').value);
        formData.append('placa', document.getElementById('placa').value);
        formData.append('dia_pagamento_semanal', document.getElementById('dia_pagamento_semanal').value);
        formData.append('valor_aluguel_semanal', document.getElementById('valor_aluguel_semanal').value);
        formData.append('valor_deposito', document.getElementById('valor_deposito').value);
        
        // Check-out inspection
        formData.append('observacoes', document.getElementById('observacoes').value);
        
        for (let i = 0; i < selectedPhotos.length; i++) {
            const file = selectedPhotos[i];
            if (file.type.startsWith('image/')) {
                try {
                    const compressedFile = await imageCompression(file, { maxSizeMB: 0.3, maxWidthOrHeight: 1920, useWebWorker: true, fileType: 'image/webp' });
                    formData.append('fotos', compressedFile, file.name.replace(/\.[^/.]+$/, ".webp"));
                } catch (err) {
                    formData.append('fotos', file);
                }
            } else {
                formData.append('fotos', file);
            }
        }
        
        const seguroInput = document.getElementById('seguro');
        if (seguroInput.files.length > 0) {
            const file = seguroInput.files[0];
            if (file.type.startsWith('image/')) {
                try {
                    const compressedFile = await imageCompression(file, { maxSizeMB: 0.3, maxWidthOrHeight: 1920, useWebWorker: true, fileType: 'image/webp' });
                    formData.append('seguro', compressedFile, file.name.replace(/\.[^/.]+$/, ".webp"));
                } catch (err) {
                    formData.append('seguro', file);
                }
            } else {
                formData.append('seguro', file);
            }
        }

        try {
            const response = await fetch('/api/contratos', {
                method: 'POST',
                body: formData // fetch adjusts headers for multipart automatically
            });

            const result = await response.json();

            if (response.ok) {
                showFeedback('Contract created successfully! Security deposit transaction generated.', 'success');
                setTimeout(() => window.location.href = '/contratos', 2000);
            } else {
                showFeedback(result.message || result.mensagem || result.error || result.erro || 'Failed to create contract', 'error');
            }
        } catch (error) {
            showFeedback('Connection error', 'error');
        } finally {
            submitBtn.disabled = false;
            btnText.classList.remove('hidden');
            loader.classList.add('hidden');
        }
    });

    function showFeedback(message, type) {
        feedbackMsg.textContent = message;
        feedbackMsg.classList.remove('hidden');
        feedbackMsg.classList.add(`feedback-${type}`);
    }
});

