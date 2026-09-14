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
        
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
        const compOptions = {
            maxSizeMB: 0.35,
            maxWidthOrHeight: 1600,
            useWebWorker: !isIOS,
            fileType: isIOS ? 'image/jpeg' : 'image/webp',
            initialQuality: 0.75
        };
        const extReplacement = isIOS ? '.jpg' : '.webp';
        
        const appendFile = async (fieldId, formKey) => {
            const input = document.getElementById(fieldId);
            if (input && input.files.length > 0) {
                const file = input.files[0];
                if (file.type.startsWith('image/')) {
                    try {
                        const compressedFile = await imageCompression(file, compOptions);
                        formData.append(formKey, compressedFile, file.name.replace(/\.[^/.]+$/, extReplacement));
                    } catch (err) {
                        formData.append(formKey, file);
                    }
                } else {
                    formData.append(formKey, file);
                }
            }
        };

        await appendFile('habilitacao', 'habilitacao');
        await appendFile('habilitacao_verso', 'habilitacao_verso');
        await appendFile('cbt', 'cbt');
        await appendFile('comprovante_endereco', 'comprovante_endereco');

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


