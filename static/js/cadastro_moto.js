document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('motoForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const loader = submitBtn.querySelector('.loader');
    const feedbackMsg = document.getElementById('feedbackMessage');
    const placaInput = document.getElementById('placa');

    if (placaInput) {
        // Disallow pressing the Spacebar
        placaInput.addEventListener('keydown', (e) => {
            if (e.key === ' ' || e.code === 'Space') {
                e.preventDefault();
            }
        });
        // Automatically sanitize spaces and convert to uppercase in real time
        placaInput.addEventListener('input', () => {
            placaInput.value = placaInput.value.replace(/\s+/g, '').toUpperCase();
        });
        // Handle paste events to strip any spaces copied from elsewhere
        placaInput.addEventListener('paste', () => {
            setTimeout(() => {
                placaInput.value = placaInput.value.replace(/\s+/g, '').toUpperCase();
            }, 0);
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        feedbackMsg.classList.add('hidden');
        feedbackMsg.className = 'feedback-message hidden';
        
        const cleanPlaca = (document.getElementById('placa').value || '').replace(/\s+/g, '').toUpperCase();
        if (!cleanPlaca) {
            showFeedback('Please provide a valid registration plate without spaces.', 'error');
            return;
        }

        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');

        // Gather data
        const formData = {
            placa: cleanPlaca,
            modelo: document.getElementById('modelo').value.trim(),
            cor: document.getElementById('cor').value.trim(),
            milhagem_atual: document.getElementById('milhagem_atual') ? parseInt(document.getElementById('milhagem_atual').value || '0', 10) : 0,
            vencimento_mot: document.getElementById('vencimento_mot') ? document.getElementById('vencimento_mot').value || null : null,
            vencimento_tax: document.getElementById('vencimento_tax') ? document.getElementById('vencimento_tax').value || null : null
        };

        try {
            const response = await fetch('/api/motos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (response.ok) {
                showFeedback('Motorbike registered successfully!', 'success');
                form.reset();
            } else {
                showFeedback(result.error || result.erro || 'Error registering motorbike', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showFeedback('Server connection error. Please try again.', 'error');
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

