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

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        feedbackMsg.classList.add('hidden');
        feedbackMsg.className = 'feedback-message hidden';
        
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
        
        const fotosInput = document.getElementById('fotos');
        for (let i = 0; i < fotosInput.files.length; i++) {
            const file = fotosInput.files[i];
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

