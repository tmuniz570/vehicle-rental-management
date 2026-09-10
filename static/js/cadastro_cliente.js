document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('clientForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const loader = submitBtn.querySelector('.loader');
    const feedbackMsg = document.getElementById('feedbackMessage');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Hide previous feedback
        feedbackMsg.classList.add('hidden');
        feedbackMsg.className = 'feedback-message hidden';
        
        // Set loading state
        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');

        // Gather data via FormData
        const formData = new FormData();
        formData.append('nome', document.getElementById('nome').value.trim());
        formData.append('telefone', document.getElementById('telefone').value.trim());
        formData.append('email', document.getElementById('email').value.trim());
        formData.append('endereco', document.getElementById('endereco').value.trim());
        
        const habInput = document.getElementById('habilitacao');
        if (habInput.files.length > 0) {
            const file = habInput.files[0];
            if (file.type.startsWith('image/')) {
                try {
                    const compressedFile = await imageCompression(file, { maxSizeMB: 0.3, maxWidthOrHeight: 1920, useWebWorker: true, fileType: 'image/webp' });
                    formData.append('habilitacao', compressedFile, file.name.replace(/\.[^/.]+$/, ".webp"));
                } catch (err) {
                    formData.append('habilitacao', file);
                }
            } else {
                formData.append('habilitacao', file);
            }
        }
        
        const compEndInput = document.getElementById('comprovante_endereco');
        if (compEndInput && compEndInput.files.length > 0) {
            const file = compEndInput.files[0];
            if (file.type.startsWith('image/')) {
                try {
                    const compressedFile = await imageCompression(file, { maxSizeMB: 0.3, maxWidthOrHeight: 1920, useWebWorker: true, fileType: 'image/webp' });
                    formData.append('comprovante_endereco', compressedFile, file.name.replace(/\.[^/.]+$/, ".webp"));
                } catch (err) {
                    formData.append('comprovante_endereco', file);
                }
            } else {
                formData.append('comprovante_endereco', file);
            }
        }

        try {
            const response = await fetch('/api/clientes', {
                method: 'POST',
                body: formData // fetch adjusts headers automatically for multipart/form-data
            });

            const result = await response.json();

            if (response.ok) {
                showFeedback('Customer registered successfully!', 'success');
                form.reset();
            } else {
                showFeedback(result.error || result.erro || 'Error registering customer', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showFeedback('Server connection error. Please try again.', 'error');
        } finally {
            // Restore button state
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


