document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('motoForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const loader = submitBtn.querySelector('.loader');
    const feedbackMsg = document.getElementById('feedbackMessage');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        feedbackMsg.classList.add('hidden');
        feedbackMsg.className = 'feedback-message hidden';
        
        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');

        // Gather data
        const formData = {
            placa: document.getElementById('placa').value.trim().toUpperCase(),
            modelo: document.getElementById('modelo').value.trim(),
            cor: document.getElementById('cor').value.trim()
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

