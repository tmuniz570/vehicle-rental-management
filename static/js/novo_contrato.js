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
                const milhas = m.milhagem_atual !== undefined ? m.milhagem_atual : 0;
                selectMoto.innerHTML += `<option value="${m.placa}" data-mileage="${milhas}">${m.placa} - ${m.modelo} (${milhas} mi)</option>`;
            }
        });

        // Preencher milhagem inicial ao selecionar a moto
        selectMoto.addEventListener('change', () => {
            const opt = selectMoto.options[selectMoto.selectedIndex];
            const inputMilhagem = document.getElementById('milhagem_inicial');
            if (opt && opt.dataset.mileage && inputMilhagem) {
                inputMilhagem.value = opt.dataset.mileage;
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

    // --- Gestão de Tipo de Contrato (Rent, Sale_Full, Sale_Installment) ---
    const radioTipos = document.querySelectorAll('input[name="tipo_contrato"]');
    const blocoAluguel = document.getElementById('blocoAluguel');
    const blocoVenda = document.getElementById('blocoVenda');
    const blocoParcelamento = document.getElementById('blocoParcelamento');
    const blocoVendaVista = document.getElementById('blocoVendaVista');

    const inputDiaPagamento = document.getElementById('dia_pagamento_semanal');
    const inputValorAluguel = document.getElementById('valor_aluguel_semanal');
    const inputValorDeposito = document.getElementById('valor_deposito');

    const inputValorVenda = document.getElementById('valor_venda_veiculo');
    const inputAdminFee = document.getElementById('valor_admin_fee');
    const inputValorEntrada = document.getElementById('valor_entrada');
    const lblTotalPurchase = document.getElementById('lblTotalPurchasePrice');
    const hiddenTotalVenda = document.getElementById('valor_total_venda');
    const lblOutstanding = document.getElementById('lblOutstandingBalance');
    const hiddenSaldoDevedor = document.getElementById('saldo_devedor');
    const lblFullTotal = document.getElementById('lblFullPaymentTotal');

    const scheduleContainer = document.getElementById('scheduleContainer');
    const btnGenerateSchedule = document.getElementById('btnGenerateSchedule');
    const btnAddInstallment = document.getElementById('btnAddInstallmentRow');
    const quickNumInstallments = document.getElementById('quickNumInstallments');
    const quickInterval = document.getElementById('quickInterval');
    const validationSummary = document.getElementById('scheduleValidationSummary');
    const hiddenCronograma = document.getElementById('cronograma_parcelas');

    let scheduleItems = []; // [{ numero: 1, valor: 300.00, vencimento: '2026-10-20' }]

    function getSelectedContractType() {
        const checked = document.querySelector('input[name="tipo_contrato"]:checked');
        return checked ? checked.value : 'Rent';
    }

    function updateContractTypeUI() {
        const type = getSelectedContractType();

        // Atualiza bordas e estilos dos cards de seleção
        radioTipos.forEach(radio => {
            const card = radio.closest('.contract-type-card');
            if (card) {
                if (radio.checked) {
                    card.style.borderColor = 'var(--accent)';
                    card.style.background = 'rgba(255, 102, 0, 0.08)';
                } else {
                    card.style.borderColor = 'var(--input-border)';
                    card.style.background = 'var(--card-bg)';
                }
            }
        });

        if (type === 'Rent') {
            if (blocoAluguel) blocoAluguel.style.display = 'block';
            if (blocoVenda) blocoVenda.style.display = 'none';
            if (blocoParcelamento) blocoParcelamento.style.display = 'none';
            if (blocoVendaVista) blocoVendaVista.style.display = 'none';

            if (inputDiaPagamento) inputDiaPagamento.required = true;
            if (inputValorAluguel) inputValorAluguel.required = true;
            if (inputValorDeposito) inputValorDeposito.required = true;

            if (inputValorVenda) inputValorVenda.required = false;
            if (inputValorEntrada) inputValorEntrada.required = false;
        } else if (type === 'Sale_Full') {
            if (blocoAluguel) blocoAluguel.style.display = 'none';
            if (blocoVenda) blocoVenda.style.display = 'block';
            if (blocoParcelamento) blocoParcelamento.style.display = 'none';
            if (blocoVendaVista) blocoVendaVista.style.display = 'block';

            if (inputDiaPagamento) inputDiaPagamento.required = false;
            if (inputValorAluguel) inputValorAluguel.required = false;
            if (inputValorDeposito) inputValorDeposito.required = false;

            if (inputValorVenda) inputValorVenda.required = true;
            if (inputValorEntrada) inputValorEntrada.required = false;
            recalculateSaleTotals();
        } else if (type === 'Sale_Installment') {
            if (blocoAluguel) blocoAluguel.style.display = 'none';
            if (blocoVenda) blocoVenda.style.display = 'block';
            if (blocoParcelamento) blocoParcelamento.style.display = 'block';
            if (blocoVendaVista) blocoVendaVista.style.display = 'none';

            if (inputDiaPagamento) inputDiaPagamento.required = false;
            if (inputValorAluguel) inputValorAluguel.required = false;
            if (inputValorDeposito) inputValorDeposito.required = false;

            if (inputValorVenda) inputValorVenda.required = true;
            if (inputValorEntrada) inputValorEntrada.required = true;
            recalculateSaleTotals();
        }
    }

    radioTipos.forEach(radio => {
        radio.addEventListener('change', updateContractTypeUI);
    });

    // --- Accessories & Extras Dynamic Builder ---
    const extrasContainer = document.getElementById('extrasItemsContainer');
    const badgeTotalExtras = document.getElementById('badgeTotalExtras');
    const btnAddExtraRow = document.getElementById('btnAddExtraRow');
    const extrasStringPreview = document.getElementById('extrasStringPreview');
    const hiddenAcessoriosExtras = document.getElementById('acessorios_extras');
    const hiddenValorTotalExtras = document.getElementById('valor_total_extras');
    const quickChips = document.querySelectorAll('.btn-extra-chip');

    let extrasItems = []; // [{ desc: 'Easyblok', price: 180 }]

    function getExtrasTotal() {
        return extrasItems.reduce((acc, it) => acc + (parseFloat(it.price) || 0), 0);
    }

    function formatExtrasString() {
        if (!extrasItems || extrasItems.length === 0) return 'None';
        const parts = [];
        extrasItems.forEach(it => {
            const desc = (it.desc || '').trim();
            const val = parseFloat(it.price || 0);
            if (desc || val > 0) {
                const formattedVal = (val % 1 === 0) ? val.toFixed(0) : val.toFixed(2);
                parts.push(`£${formattedVal} ${desc}`.trim());
            }
        });
        return parts.length > 0 ? parts.join(', ') : 'None';
    }

    function updateExtrasOutput() {
        const total = getExtrasTotal();
        const str = formatExtrasString();

        if (badgeTotalExtras) badgeTotalExtras.textContent = `Total Extras: £${total.toFixed(2)}`;
        if (extrasStringPreview) extrasStringPreview.textContent = str;
        if (hiddenAcessoriosExtras) hiddenAcessoriosExtras.value = str;
        if (hiddenValorTotalExtras) hiddenValorTotalExtras.value = total.toFixed(2);

        recalculateSaleTotals();
    }

    function renderExtrasTable() {
        if (!extrasContainer) return;
        extrasContainer.innerHTML = '';

        if (extrasItems.length === 0) {
            const emptyNotice = document.createElement('div');
            emptyNotice.style.cssText = 'padding: 10px 14px; font-size: 0.8rem; color: var(--text-secondary); background: rgba(255,255,255,0.02); border-radius: 8px; border: 1px dashed var(--input-border); text-align: center;';
            emptyNotice.textContent = 'No extra accessories added yet. Click "+ Easyblok", "+ Leg Cover", etc. above or "+ Add Custom Extra".';
            extrasContainer.appendChild(emptyNotice);
            updateExtrasOutput();
            return;
        }

        extrasItems.forEach((item, index) => {
            const row = document.createElement('div');
            row.style.cssText = 'display: grid; grid-template-columns: 1fr 120px 36px; gap: 8px; align-items: center; background: rgba(255,255,255,0.02); padding: 6px 10px; border-radius: 8px; border: 1px solid var(--border-color);';
            row.innerHTML = `
                <div>
                    <input type="text" class="extra-desc-input" data-idx="${index}" value="${escapeHtml(item.desc || '')}" placeholder="Description (e.g. Easyblok)" style="width: 100%; padding: 6px 10px; border-radius: 6px; border: 1px solid var(--input-border); background: var(--input-bg); color: var(--text-primary); font-size: 0.85rem;">
                </div>
                <div>
                    <input type="number" step="0.01" class="extra-price-input" data-idx="${index}" value="${parseFloat(item.price || 0)}" placeholder="Price (£)" style="width: 100%; padding: 6px 10px; border-radius: 6px; border: 1px solid var(--input-border); background: var(--input-bg); color: var(--text-primary); font-size: 0.85rem;">
                </div>
                <div style="text-align: center;">
                    <button type="button" class="btn-remove-extra" data-idx="${index}" title="Remove Extra" style="background: transparent; border: none; color: #ef4444; font-size: 1.25rem; cursor: pointer; padding: 2px 6px; line-height: 1;">&times;</button>
                </div>
            `;
            extrasContainer.appendChild(row);
        });

        extrasContainer.querySelectorAll('.extra-desc-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const idx = parseInt(e.target.dataset.idx);
                extrasItems[idx].desc = e.target.value;
                updateExtrasOutput();
            });
        });

        extrasContainer.querySelectorAll('.extra-price-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const idx = parseInt(e.target.dataset.idx);
                extrasItems[idx].price = parseFloat(e.target.value || 0);
                updateExtrasOutput();
            });
        });

        extrasContainer.querySelectorAll('.btn-remove-extra').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(e.target.dataset.idx);
                extrasItems.splice(idx, 1);
                renderExtrasTable();
            });
        });

        updateExtrasOutput();
    }

    if (btnAddExtraRow) {
        btnAddExtraRow.addEventListener('click', () => {
            extrasItems.push({ desc: '', price: 0 });
            renderExtrasTable();
            setTimeout(() => {
                const inputs = extrasContainer.querySelectorAll('.extra-desc-input');
                if (inputs.length > 0) inputs[inputs.length - 1].focus();
            }, 50);
        });
    }

    quickChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const desc = chip.dataset.desc;
            const price = parseFloat(chip.dataset.price || 0);
            extrasItems.push({ desc: desc, price: price });
            renderExtrasTable();
        });
    });

    function escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // Cálculos em tempo real de Venda
    function recalculateSaleTotals() {
        const preco = parseFloat(inputValorVenda?.value || 0);
        const adminFee = parseFloat(inputAdminFee?.value || 0);
        const entrada = parseFloat(inputValorEntrada?.value || 0);
        const totalExtras = getExtrasTotal();

        const totalVenda = preco + adminFee + totalExtras;
        const saldoDevedor = Math.max(0, totalVenda - entrada);

        if (lblTotalPurchase) lblTotalPurchase.textContent = `£${totalVenda.toFixed(2)}`;
        if (hiddenTotalVenda) hiddenTotalVenda.value = totalVenda.toFixed(2);
        if (lblOutstanding) lblOutstanding.textContent = `£${saldoDevedor.toFixed(2)}`;
        if (hiddenSaldoDevedor) hiddenSaldoDevedor.value = saldoDevedor.toFixed(2);
        
        const totalVendaVista = preco + totalExtras;
        if (lblFullTotal) lblFullTotal.textContent = `£${totalVendaVista.toFixed(2)}`;

        const type = getSelectedContractType();
        if (type === 'Sale_Full') {
            if (hiddenTotalVenda) hiddenTotalVenda.value = totalVendaVista.toFixed(2);
        }

        validateScheduleSum();
    }

    if (inputValorVenda) inputValorVenda.addEventListener('input', recalculateSaleTotals);
    if (inputAdminFee) inputAdminFee.addEventListener('input', recalculateSaleTotals);
    if (inputValorEntrada) inputValorEntrada.addEventListener('input', recalculateSaleTotals);

    // Construtor e Validador de Parcelas
    function renderScheduleTable() {
        if (!scheduleContainer) return;
        scheduleContainer.innerHTML = '';

        scheduleItems.forEach((item, index) => {
            const row = document.createElement('div');
            row.className = 'schedule-installment-card';
            row.style.background = 'rgba(255, 255, 255, 0.03)';
            row.style.border = '1px solid rgba(255, 255, 255, 0.08)';
            row.style.borderRadius = '10px';
            row.style.padding = '10px 12px';
            row.style.marginBottom = '8px';
            row.style.display = 'flex';
            row.style.flexDirection = 'column';
            row.style.gap = '8px';

            row.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-weight: 700; font-size: 0.85rem; color: var(--text-primary); display: flex; align-items: center; gap: 6px;">
                        <span style="background: rgba(255, 102, 0, 0.15); color: var(--accent); border: 1px solid rgba(255, 102, 0, 0.3); border-radius: 6px; padding: 2px 8px; font-size: 0.75rem; font-weight: 700;">
                            #${index + 1}
                        </span>
                        <span>Installment</span>
                    </div>
                    <button type="button" class="btn-remove-installment" data-idx="${index}" title="Remove" style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.25); color: #ef4444; border-radius: 6px; padding: 4px 8px; font-size: 0.8rem; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; line-height: 1;">
                        <span style="font-size: 1rem; font-weight: bold; line-height: 1;">&times;</span> Remove
                    </button>
                </div>
                <div style="display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr); gap: 10px; align-items: end;">
                    <div>
                        <label style="display: block; font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 4px; font-weight: 600;">Amount (£)</label>
                        <div style="position: relative;">
                            <span style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-secondary); font-size: 0.9rem; pointer-events: none; font-weight: 600;">£</span>
                            <input type="number" step="0.01" value="${parseFloat(item.valor || 0).toFixed(2)}" class="schedule-amount-input" data-idx="${index}" placeholder="0.00" style="width: 100%; box-sizing: border-box; padding: 8px 10px 8px 24px; border-radius: 8px; border: 1px solid var(--input-border); background: var(--input-bg); color: var(--text-primary); font-size: 16px; font-weight: 600; min-width: 0;">
                        </div>
                    </div>
                    <div>
                        <label style="display: block; font-size: 0.75rem; color: var(--text-secondary); margin-bottom: 4px; font-weight: 600;">Due Date</label>
                        <input type="date" value="${item.vencimento || ''}" class="schedule-date-input" data-idx="${index}" style="width: 100%; box-sizing: border-box; padding: 8px 10px; border-radius: 8px; border: 1px solid var(--input-border); background: var(--input-bg); color: var(--text-primary); font-size: 16px; min-width: 0;">
                    </div>
                </div>
            `;
            scheduleContainer.appendChild(row);
        });

        // Listeners para edição inline
        scheduleContainer.querySelectorAll('.schedule-amount-input').forEach(input => {
            input.addEventListener('input', (e) => {
                const idx = parseInt(e.target.dataset.idx);
                scheduleItems[idx].valor = parseFloat(e.target.value || 0);
                validateScheduleSum();
            });
        });

        scheduleContainer.querySelectorAll('.schedule-date-input').forEach(input => {
            input.addEventListener('change', (e) => {
                const idx = parseInt(e.target.dataset.idx);
                scheduleItems[idx].vencimento = e.target.value;
                validateScheduleSum();
            });
        });

        scheduleContainer.querySelectorAll('.btn-remove-installment').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(e.target.dataset.idx);
                scheduleItems.splice(idx, 1);
                scheduleItems.forEach((it, i) => it.numero = i + 1);
                renderScheduleTable();
                validateScheduleSum();
            });
        });

        validateScheduleSum();
    }

    function validateScheduleSum() {
        const saldo = parseFloat(hiddenSaldoDevedor?.value || 0);
        const sum = scheduleItems.reduce((acc, cur) => acc + parseFloat(cur.valor || 0), 0);
        const diff = Math.abs(sum - saldo);

        if (hiddenCronograma) {
            hiddenCronograma.value = JSON.stringify(scheduleItems);
        }

        if (!validationSummary) return;

        if (scheduleItems.length === 0) {
            validationSummary.innerHTML = '<span style="color: var(--text-secondary);">No installments generated yet</span>';
            return;
        }

        if (diff < 0.05) {
            validationSummary.innerHTML = `<span style="color: #4ade80;">✓ Total: £${sum.toFixed(2)} (Matches 100%)</span>`;
        } else {
            validationSummary.innerHTML = `<span style="color: #f87171;">⚠️ Total: £${sum.toFixed(2)} / Expected: £${saldo.toFixed(2)} (Diff: £${(saldo - sum).toFixed(2)})</span>`;
        }
    }

    if (btnGenerateSchedule) {
        btnGenerateSchedule.addEventListener('click', () => {
            const saldo = parseFloat(hiddenSaldoDevedor?.value || 0);
            const num = Math.max(1, parseInt(quickNumInstallments?.value || 3));
            const daysInterval = parseInt(quickInterval?.value || 30);

            if (saldo <= 0) {
                showFeedback('Please set the Vehicle Price and Deposit before generating installments.', 'error');
                return;
            }

            const baseAmount = Math.floor((saldo / num) * 100) / 100;
            const remainder = Math.round((saldo - (baseAmount * num)) * 100) / 100;

            scheduleItems = [];
            const today = new Date();

            for (let i = 1; i <= num; i++) {
                const dueDate = new Date(today);
                dueDate.setDate(dueDate.getDate() + (daysInterval * i));
                const yyyy = dueDate.getFullYear();
                const mm = String(dueDate.getMonth() + 1).padStart(2, '0');
                const dd = String(dueDate.getDate()).padStart(2, '0');

                let amount = baseAmount;
                if (i === num) {
                    amount = Math.round((amount + remainder) * 100) / 100;
                }

                scheduleItems.push({
                    numero: i,
                    valor: amount,
                    vencimento: `${yyyy}-${mm}-${dd}`
                });
            }

            renderScheduleTable();
        });
    }

    if (btnAddInstallment) {
        btnAddInstallment.addEventListener('click', () => {
            const nextIdx = scheduleItems.length + 1;
            const today = new Date();
            today.setDate(today.getDate() + (30 * nextIdx));
            const yyyy = today.getFullYear();
            const mm = String(today.getMonth() + 1).padStart(2, '0');
            const dd = String(today.getDate()).padStart(2, '0');

            scheduleItems.push({
                numero: nextIdx,
                valor: 0.00,
                vencimento: `${yyyy}-${mm}-${dd}`
            });
            renderScheduleTable();
        });
    }

    // Inicialização do estado de UI
    renderExtrasTable();
    updateContractTypeUI();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        feedbackMsg.classList.add('hidden');
        feedbackMsg.className = 'feedback-message hidden';

        const contractType = getSelectedContractType();

        if (contractType === 'Sale_Installment') {
            const saldo = parseFloat(hiddenSaldoDevedor?.value || 0);
            if (scheduleItems.length === 0 && saldo > 0) {
                showFeedback('Please generate or add the installment schedule for this sale.', 'error');
                return;
            }
            const sum = scheduleItems.reduce((acc, cur) => acc + parseFloat(cur.valor || 0), 0);
            if (Math.abs(sum - saldo) > 0.05) {
                showFeedback(`Installment schedule sum (£${sum.toFixed(2)}) must equal the Outstanding Balance (£${saldo.toFixed(2)}).`, 'error');
                return;
            }
        }
        
        submitBtn.disabled = true;
        btnText.classList.add('hidden');
        loader.classList.remove('hidden');

        const formData = new FormData();
        formData.append('id_cliente', document.getElementById('id_cliente').value);
        formData.append('placa', document.getElementById('placa').value);
        formData.append('milhagem_inicial', document.getElementById('milhagem_inicial').value || '0');
        formData.append('tipo_contrato', contractType);
        
        if (contractType === 'Rent') {
            formData.append('dia_pagamento_semanal', document.getElementById('dia_pagamento_semanal').value);
            formData.append('valor_aluguel_semanal', document.getElementById('valor_aluguel_semanal').value);
            formData.append('valor_deposito', document.getElementById('valor_deposito').value);
        } else {
            formData.append('categoria_historico', document.getElementById('categoria_historico').value);
            formData.append('valor_venda_veiculo', document.getElementById('valor_venda_veiculo').value);
            formData.append('acessorios_extras', document.getElementById('acessorios_extras').value);
            formData.append('valor_total_extras', document.getElementById('valor_total_extras')?.value || '0.00');
            
            if (contractType === 'Sale_Installment') {
                formData.append('valor_admin_fee', document.getElementById('valor_admin_fee').value || '0.00');
                formData.append('valor_total_venda', document.getElementById('valor_total_venda').value);
                formData.append('valor_entrada', document.getElementById('valor_entrada').value || '0.00');
                formData.append('saldo_devedor', document.getElementById('saldo_devedor').value || '0.00');
                formData.append('cronograma_parcelas', JSON.stringify(scheduleItems));
            } else {
                formData.append('valor_total_venda', document.getElementById('valor_total_venda')?.value || document.getElementById('valor_venda_veiculo').value);
            }
        }
        
        // Check-out inspection
        formData.append('observacoes', document.getElementById('observacoes').value);
        
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
        const compOptions = {
            maxSizeMB: 0.35,
            maxWidthOrHeight: 1600,
            useWebWorker: !isIOS,
            fileType: isIOS ? 'image/jpeg' : 'image/webp',
            initialQuality: 0.75
        };
        const extReplacement = isIOS ? '.jpg' : '.webp';
        
        for (let i = 0; i < selectedPhotos.length; i++) {
            const file = selectedPhotos[i];
            if (file.type.startsWith('image/')) {
                try {
                    const compressedFile = await imageCompression(file, compOptions);
                    formData.append('fotos', compressedFile, file.name.replace(/\.[^/.]+$/, extReplacement));
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
                    const compressedFile = await imageCompression(file, compOptions);
                    formData.append('seguro', compressedFile, file.name.replace(/\.[^/.]+$/, extReplacement));
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
                const novoContratoId = result.id;
                // Redireciona diretamente para a tela do contrato gerado para colher a assinatura
                window.location.href = `/contratos/${novoContratoId}?assinar=1`;
                return;
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

    // --- Modal Pós Criação e Signature Pad ---
    let activeContractId = null;
    let signaturePadInstance = null;

    const modalPosCriacao = document.getElementById('modalPosCriacaoContrato');
    const createdIdText = document.getElementById('createdContractIdText');
    const btnImprimir = document.getElementById('btnImprimirContratoCriado');
    const btnIrDetalhes = document.getElementById('btnIrParaDetalhesCriado');
    const btnAssinarAgora = document.getElementById('btnAssinarAgoraModal');

    const modalSig = document.getElementById('modalSignaturePad');
    const canvas = document.getElementById('signatureCanvas');
    const btnClearSig = document.getElementById('btnClearSignature');
    const btnCancelSig = document.getElementById('btnCancelSignature');
    const btnCloseSig = document.getElementById('btnCloseSignatureModal');
    const btnSaveSig = document.getElementById('btnSaveSignature');

    function showPostCreationModal(id) {
        activeContractId = id;
        if (createdIdText) createdIdText.textContent = id;
        if (btnImprimir) btnImprimir.href = `/contratos/${id}/imprimir`;
        if (btnIrDetalhes) btnIrDetalhes.href = `/contratos/${id}`;
        if (modalPosCriacao) modalPosCriacao.style.display = 'flex';
    }

    function initSignaturePad() {
        if (!canvas) return;
        
        // Resize canvas for device pixel ratio
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        canvas.width = canvas.offsetWidth * ratio;
        canvas.height = canvas.offsetHeight * ratio;
        canvas.getContext("2d").scale(ratio, ratio);

        if (!signaturePadInstance && typeof SignaturePad !== 'undefined') {
            signaturePadInstance = new SignaturePad(canvas, {
                backgroundColor: 'rgb(255, 255, 255)',
                penColor: 'rgb(15, 23, 42)',
                minWidth: 1.5,
                maxWidth: 3.5
            });
        } else if (signaturePadInstance) {
            signaturePadInstance.clear();
        }
    }

    if (btnAssinarAgora) {
        btnAssinarAgora.addEventListener('click', () => {
            if (modalPosCriacao) modalPosCriacao.style.display = 'none';
            if (modalSig) {
                modalSig.style.display = 'flex';
                setTimeout(() => initSignaturePad(), 50);
            }
        });
    }

    function fecharModalAssinatura() {
        if (modalSig) modalSig.style.display = 'none';
        if (activeContractId) {
            window.location.href = `/contratos/${activeContractId}`;
        } else {
            window.location.href = '/contratos';
        }
    }

    if (btnCancelSig) btnCancelSig.addEventListener('click', fecharModalAssinatura);
    if (btnCloseSig) btnCloseSig.addEventListener('click', fecharModalAssinatura);

    if (btnClearSig) {
        btnClearSig.addEventListener('click', () => {
            if (signaturePadInstance) signaturePadInstance.clear();
        });
    }

    if (btnSaveSig) {
        btnSaveSig.addEventListener('click', async () => {
            if (!signaturePadInstance || signaturePadInstance.isEmpty()) {
                alert('Please provide a signature before confirming.');
                return;
            }

            const dataUrl = signaturePadInstance.toDataURL('image/png');
            btnSaveSig.disabled = true;
            btnSaveSig.textContent = 'Saving signature...';

            try {
                const res = await fetch(`/api/contratos/${activeContractId}/assinar`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tipo: 'inicial',
                        assinatura: dataUrl
                    })
                });

                if (res.ok) {
                    alert('Signature saved successfully! Opening contract agreement...');
                    window.location.href = `/contratos/${activeContractId}/imprimir`;
                } else {
                    const d = await res.json();
                    alert(d.message || d.mensagem || d.error || 'Failed to save signature.');
                    btnSaveSig.disabled = false;
                    btnSaveSig.textContent = '✓ Confirm Signature';
                }
            } catch (err) {
                alert('Error connecting to server.');
                btnSaveSig.disabled = false;
                btnSaveSig.textContent = '✓ Confirm Signature';
            }
        });
    }
});

