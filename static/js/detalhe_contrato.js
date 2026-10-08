function formatWhatsAppNumber(phone) {
    if (typeof window.formatWhatsAppNumber === 'function' && window.formatWhatsAppNumber !== formatWhatsAppNumber) {
        return window.formatWhatsAppNumber(phone);
    }
    if (!phone) return '';
    const raw = String(phone).trim();
    if (!raw) return '';
    
    // 1. If it already starts with '+', keep country code (strip non-digits)
    if (raw.startsWith('+')) {
        let digits = raw.replace(/\D/g, '');
        if (digits.startsWith('440') && digits.length >= 12) digits = '44' + digits.substring(3);
        return digits;
    }
    
    // 2. If it starts with '00' (international prefix)
    if (raw.startsWith('00')) {
        let digits = raw.replace(/\D/g, '').substring(2);
        if (digits.startsWith('440') && digits.length >= 12) digits = '44' + digits.substring(3);
        return digits;
    }
    
    const digits = raw.replace(/\D/g, '');
    if (!digits) return '';
    
    // 3. If UK number with leading 0 (e.g. 07360469902 -> 447360469902)
    if (digits.startsWith('0')) {
        return '44' + digits.substring(1);
    }
    
    // 4. If UK mobile without leading 0 (e.g. 7360469902 with 10 digits starting with 7 -> 447360469902)
    if (digits.startsWith('7') && digits.length === 10) {
        return '44' + digits;
    }
    
    // 5. If already has 44 prefix (e.g. 447360469902)
    if (digits.startsWith('44')) {
        if (digits.startsWith('440') && digits.length >= 12) return '44' + digits.substring(3);
        return digits;
    }
    
    // 6. Otherwise (e.g. already has other country code like 5582999946121)
    return digits;
}

function formatarDescricaoTransacao(tipo) {
    if (!tipo) return '-';
    const t = tipo.toLowerCase();
    if (t === 'sale_full' || t === 'venda_vista') return 'Vehicle Sale - Full Payment';
    if (t === 'sale_deposit' || t === 'venda_entrada') return 'Vehicle Sale - Down Payment (Deposit)';
    if (t === 'sale_installment' || t === 'venda_parcela') return 'Vehicle Sale - Instalment Payment';
    if (t === 'rent' || t === 'aluguel') return 'Vehicle Rental Payment';
    if (t === 'deposit' || t === 'deposito') return 'Rental Security Deposit (Refundable)';
    if (t === 'deposit_refund' || t === 'devolucao_deposito') return 'Security Deposit Refund';
    if (t === 'fine' || t === 'multa') return 'Traffic / Parking Fine';
    if (t === 'damage' || t === 'dano') return 'Vehicle Damage Charge';
    if (t === 'other' || t === 'outro') return 'Additional Charge';
    return tipo.replace(/_/g, ' ');
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function copyToClipboard(text, triggerBtn) {
    if (!text || text === '-' || text === 'null') return;
    const cleanText = String(text).trim();
    if (!cleanText) return;

    function showSuccess() {
        if (!triggerBtn) return;
        const origHtml = triggerBtn.innerHTML;
        const origTitle = triggerBtn.title;
        triggerBtn.innerHTML = '<span style="color:#4ade80; font-weight:bold;">✓</span>';
        triggerBtn.title = 'Copied to clipboard!';
        triggerBtn.style.borderColor = 'rgba(74, 222, 128, 0.6)';
        triggerBtn.style.color = '#4ade80';
        triggerBtn.style.background = 'rgba(74, 222, 128, 0.15)';
        setTimeout(() => {
            triggerBtn.innerHTML = origHtml;
            triggerBtn.title = origTitle;
            triggerBtn.style.borderColor = '';
            triggerBtn.style.color = '';
            triggerBtn.style.background = '';
        }, 1800);
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(cleanText).then(showSuccess).catch(() => fallbackCopy(cleanText));
    } else {
        fallbackCopy(cleanText);
    }

    function fallbackCopy(str) {
        try {
            const temp = document.createElement('textarea');
            temp.value = str;
            temp.setAttribute('readonly', '');
            temp.style.position = 'fixed';
            temp.style.left = '-9999px';
            temp.style.top = '-9999px';
            document.body.appendChild(temp);
            temp.select();
            document.execCommand('copy');
            document.body.removeChild(temp);
            showSuccess();
        } catch (e) {
            console.error('Fallback copy failed:', e);
        }
    }
}

function sortExtrato(transacoes, field, order) {
    const list = [...transacoes];
    const mult = (order === 'asc') ? 1 : -1;
    const now = new Date();
    now.setHours(0, 0, 0, 0);

    list.sort((a, b) => {
        if (field === 'id') {
            const idA = parseInt(a.id, 10) || 0;
            const idB = parseInt(b.id, 10) || 0;
            return (idA - idB) * mult;
        }

        if (field === 'valor') {
            const vA = parseFloat(a.valor) || 0;
            const vB = parseFloat(b.valor) || 0;
            return (vA - vB) * mult;
        }

        if (field === 'data_vencimento' || field === 'data_pagamento') {
            const tA = a[field] ? new Date(a[field]).getTime() : 0;
            const tB = b[field] ? new Date(b[field]).getTime() : 0;
            if (!tA && !tB) return 0;
            if (!tA) return 1;
            if (!tB) return -1;
            return (tA - tB) * mult;
        }

        if (field === 'status') {
            const getRank = (item) => {
                const s = (item.status || '').toLowerCase();
                const isPaid = s === 'paid' || s === 'pago';
                const isPending = s === 'pending' || s === 'pendente';
                const dV = item.data_vencimento ? new Date(item.data_vencimento) : null;
                const isOverdue = isPending && dV && dV < now;
                if (isOverdue) return 1;
                if (isPending) return 2;
                if (isPaid) return 3;
                return 4;
            };
            const rA = getRank(a);
            const rB = getRank(b);
            if (rA !== rB) return (rA - rB) * mult;
            return ((b.id || 0) - (a.id || 0));
        }

        if (field === 'tipo') {
            const descA = (a.descricao || (typeof formatarDescricaoTransacao === 'function' ? formatarDescricaoTransacao(a.tipo) : a.tipo) || '').toLowerCase();
            const descB = (b.descricao || (typeof formatarDescricaoTransacao === 'function' ? formatarDescricaoTransacao(b.tipo) : b.tipo) || '').toLowerCase();
            return descA.localeCompare(descB) * mult;
        }

        const rawA = String(a[field] || '').toLowerCase();
        const rawB = String(b[field] || '').toLowerCase();
        return rawA.localeCompare(rawB) * mult;
    });

    return list;
}

document.addEventListener('DOMContentLoaded', async () => {
    const formatoMoeda = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });
    const diasSemana = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

    try {
        const response = await fetch(`/api/contratos/${CONTRATO_ID}`);
        if (!response.ok) {
            alert('Failed to load contract details.');
            return;
        }
        
        const data = await response.json();
        
        // Internal Notes
        const txtNotasContrato = document.getElementById('contrato_notas_internas');
        if (txtNotasContrato) {
            txtNotasContrato.value = data.notas_internas || '';
        }
        
        // 1. Customer Card
        const elClienteId = document.getElementById('info_cliente_id');
        if (elClienteId) {
            elClienteId.textContent = data.id_cliente ? `ID #${data.id_cliente}` : 'ID -';
        }
        const elCliente = document.getElementById('info_cliente');
        if (elCliente) {
            elCliente.textContent = data.cliente || data.cliente_nome || '-';
        }
        
        const elTel = document.getElementById('info_tel');
        const telVal = data.telefone || data.cliente_telefone;
        if (elTel) {
            if (telVal) {
                const waNum = formatWhatsAppNumber(telVal);
                const placaRef = (data.placa || data.moto_placa || '').trim();
                const bikeRef = (placaRef && placaRef !== '-') ? `regarding vehicle ${placaRef}` : 'regarding your vehicle';
                const waMsg = encodeURIComponent(`Hello ${data.cliente || data.cliente_nome || ''}, this is FF Motors ${bikeRef}: `);
                elTel.innerHTML = `
                    <div style="display:inline-flex; align-items:center; gap:8px; flex-wrap:wrap;">
                        <a href="tel:${encodeURIComponent(telVal)}" style="color:var(--text-primary); text-decoration:none; display:inline-flex; align-items:center; gap:6px; transition:color 0.2s;" title="Click to call ${escapeHtml(telVal)}">
                            <span>📞</span> <span style="text-decoration:underline;">${escapeHtml(telVal)}</span>
                        </a>
                        ${waNum ? `<a href="https://wa.me/${waNum}?text=${waMsg}" target="_blank" rel="noopener noreferrer" class="btn-action" style="padding:2px 8px; font-size:0.75rem; background:rgba(37,211,102,0.15); border:1px solid rgba(37,211,102,0.35); color:#25D366; border-radius:4px; text-decoration:none; display:inline-flex; align-items:center; gap:4px; font-weight:600;" title="Send WhatsApp Message">💬 WhatsApp</a>` : ''}
                    </div>
                `;
            } else {
                elTel.innerHTML = '<span>📞 No phone</span>';
            }
        }
        
        const elEmail = document.getElementById('info_email');
        const emailVal = data.email || data.cliente_email;
        if (elEmail) {
            if (emailVal) {
                elEmail.innerHTML = `
                    <a href="mailto:${encodeURIComponent(emailVal)}" style="color:#60a5fa; text-decoration:underline; word-break:break-all; display:inline-flex; align-items:center; gap:6px;" title="Send email to ${escapeHtml(emailVal)}">
                        <span>✉️</span> <span>${escapeHtml(emailVal)}</span>
                    </a>
                `;
            } else {
                elEmail.innerHTML = '<span>✉️ No email</span>';
            }
        }
        
        const elEndereco = document.getElementById('info_endereco');
        const endVal = data.endereco || data.cliente_endereco;
        if (elEndereco) {
            if (endVal) {
                const mapQuery = encodeURIComponent(endVal);
                elEndereco.innerHTML = `
                    <a href="https://www.google.com/maps/search/?api=1&query=${mapQuery}" target="_blank" style="color:var(--text-primary); text-decoration:none; display:flex; justify-content:space-between; align-items:flex-start; gap:8px;" title="Open in Google Maps">
                        <span>${escapeHtml(endVal)}</span>
                        <span style="color:var(--accent); font-size:0.75rem; font-weight:600; white-space:nowrap; background:rgba(217,119,6,0.1); border:1px solid rgba(217,119,6,0.25); padding:2px 6px; border-radius:4px;">Maps ↗</span>
                    </a>
                `;
            } else {
                elEndereco.textContent = 'No registered address';
            }
        }

        // Copy buttons for Customer Card
        const clienteNomeVal = data.cliente || data.cliente_nome || '';
        const btnCopyNome = document.getElementById('btnCopyClienteNome');
        if (btnCopyNome) {
            if (clienteNomeVal && clienteNomeVal !== '-') {
                btnCopyNome.onclick = (e) => {
                    e.stopPropagation();
                    copyToClipboard(clienteNomeVal, btnCopyNome);
                };
            } else {
                btnCopyNome.style.display = 'none';
            }
        }

        const btnCopyTel = document.getElementById('btnCopyClienteTel');
        if (btnCopyTel) {
            if (telVal && telVal !== '-') {
                btnCopyTel.onclick = (e) => {
                    e.stopPropagation();
                    copyToClipboard(telVal, btnCopyTel);
                };
            } else {
                btnCopyTel.style.display = 'none';
            }
        }

        const btnCopyEmail = document.getElementById('btnCopyClienteEmail');
        if (btnCopyEmail) {
            if (emailVal && emailVal !== '-') {
                btnCopyEmail.onclick = (e) => {
                    e.stopPropagation();
                    copyToClipboard(emailVal, btnCopyEmail);
                };
            } else {
                btnCopyEmail.style.display = 'none';
            }
        }

        const btnCopyEnd = document.getElementById('btnCopyClienteEndereco');
        if (btnCopyEnd) {
            if (endVal && endVal !== '-') {
                btnCopyEnd.onclick = (e) => {
                    e.stopPropagation();
                    copyToClipboard(endVal, btnCopyEnd);
                };
            } else {
                btnCopyEnd.style.display = 'none';
            }
        }

        const docsContainer = document.getElementById('info_cliente_docs');
        if (docsContainer) {
            let docsHtml = '';
            // Licence Front
            if (data.url_habilitacao) {
                docsHtml += `
                    <a href="${data.url_habilitacao}" target="_blank" class="btn-action" style="padding: 6px 10px; font-size: 0.78rem; text-decoration: none; display: flex; align-items: center; justify-content: space-between; background: rgba(59, 130, 246, 0.12); border: 1px solid rgba(59, 130, 246, 0.3); color: #60a5fa; border-radius: 6px;">
                        <span>🪪 Licence Front (DVLA)</span>
                        <span style="font-size: 0.75rem;">View ↗</span>
                    </a>
                `;
            } else {
                docsHtml += `
                    <div style="padding: 6px 10px; font-size: 0.78rem; display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.02); border: 1px dashed var(--border-color); color: var(--text-secondary); border-radius: 6px;">
                        <span>🪪 Licence Front</span>
                        <span style="font-size: 0.72rem; opacity: 0.6;">Not uploaded</span>
                    </div>
                `;
            }

            // Licence Back
            if (data.url_habilitacao_verso) {
                docsHtml += `
                    <a href="${data.url_habilitacao_verso}" target="_blank" class="btn-action" style="padding: 6px 10px; font-size: 0.78rem; text-decoration: none; display: flex; align-items: center; justify-content: space-between; background: rgba(59, 130, 246, 0.12); border: 1px solid rgba(59, 130, 246, 0.3); color: #60a5fa; border-radius: 6px;">
                        <span>🪪 Licence Back (DVLA)</span>
                        <span style="font-size: 0.75rem;">View ↗</span>
                    </a>
                `;
            } else {
                docsHtml += `
                    <div style="padding: 6px 10px; font-size: 0.78rem; display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.02); border: 1px dashed var(--border-color); color: var(--text-secondary); border-radius: 6px;">
                        <span>🪪 Licence Back</span>
                        <span style="font-size: 0.72rem; opacity: 0.6;">Not uploaded</span>
                    </div>
                `;
            }

            // CBT Certificate
            if (data.url_cbt) {
                docsHtml += `
                    <a href="${data.url_cbt}" target="_blank" class="btn-action" style="padding: 6px 10px; font-size: 0.78rem; text-decoration: none; display: flex; align-items: center; justify-content: space-between; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; border-radius: 6px;">
                        <span>📜 CBT Certificate</span>
                        <span style="font-size: 0.75rem;">View ↗</span>
                    </a>
                `;
            } else {
                docsHtml += `
                    <div style="padding: 6px 10px; font-size: 0.78rem; display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.02); border: 1px dashed var(--border-color); color: var(--text-secondary); border-radius: 6px;">
                        <span>📜 CBT Certificate</span>
                        <span style="font-size: 0.72rem; opacity: 0.6;">Not required / None</span>
                    </div>
                `;
            }

            // Proof of Address
            if (data.url_comprovante_endereco) {
                docsHtml += `
                    <a href="${data.url_comprovante_endereco}" target="_blank" class="btn-action" style="padding: 6px 10px; font-size: 0.78rem; text-decoration: none; display: flex; align-items: center; justify-content: space-between; background: rgba(168, 85, 247, 0.12); border: 1px solid rgba(168, 85, 247, 0.3); color: #c084fc; border-radius: 6px;">
                        <span>🏠 Proof of Address</span>
                        <span style="font-size: 0.75rem;">View ↗</span>
                    </a>
                `;
            } else {
                docsHtml += `
                    <div style="padding: 6px 10px; font-size: 0.78rem; display: flex; align-items: center; justify-content: space-between; background: rgba(255,255,255,0.02); border: 1px dashed var(--border-color); color: var(--text-secondary); border-radius: 6px;">
                        <span>🏠 Proof of Address</span>
                        <span style="font-size: 0.72rem; opacity: 0.6;">Not uploaded</span>
                    </div>
                `;
            }
            docsContainer.innerHTML = docsHtml;
        }

        const linksCliente = document.getElementById('info_cliente_links');
        if (linksCliente) {
            linksCliente.innerHTML = '';
            const clientProfileLink = document.createElement('a');
            clientProfileLink.href = `/clientes?search=${encodeURIComponent(data.id_cliente || data.cliente || '')}`;
            clientProfileLink.className = 'btn-action';
            clientProfileLink.style.cssText = 'flex: 1; text-align: center; font-size: 0.8rem; padding: 6px 10px; text-decoration: none; border-radius: 6px; display: inline-flex; align-items: center; justify-content: center; background: rgba(255,255,255,0.05); border: 1px solid var(--border-color); color: var(--text-primary);';
            clientProfileLink.innerHTML = '<span>👥 View Client</span>';
            linksCliente.appendChild(clientProfileLink);
        }
        
        // 2. Vehicle Card
        const placaVal = data.placa || data.moto_placa || '-';
        const modeloVal = data.modelo || data.moto_modelo || '-';
        const corVal = data.cor || data.moto_cor || '-';
        const elPlaca = document.getElementById('info_placa');
        elPlaca.textContent = placaVal;
        if (placaVal && placaVal !== '-') {
            elPlaca.style.cursor = 'pointer';
            elPlaca.title = 'Click to manage vehicle details, V5C and trackers';
            elPlaca.onclick = () => {
                if (typeof abrirModalMoto === 'function') {
                    abrirModalMoto(placaVal, 'tabInfo', {
                        modelo: modeloVal,
                        cor: corVal,
                        milhagem_atual: data.milhagem_atual_moto || data.milhagem_final || data.milhagem_inicial,
                        vencimento_mot: data.vencimento_mot,
                        vencimento_tax: data.vencimento_tax,
                        tax_sorn: data.tax_sorn
                    });
                }
            };
        }

        const btnCopyPlaca = document.getElementById('btnCopyPlaca');
        if (btnCopyPlaca) {
            if (placaVal && placaVal !== '-') {
                btnCopyPlaca.onclick = (e) => {
                    e.stopPropagation();
                    copyToClipboard(placaVal, btnCopyPlaca);
                };
            } else {
                btnCopyPlaca.style.display = 'none';
            }
        }

        document.getElementById('info_modelo_cor').textContent = `${modeloVal} • ${corVal}`;
        
        if (data.data_retirada) {
            document.getElementById('info_data_retirada').textContent = 'Collection: ' + new Date(data.data_retirada).toLocaleDateString('en-GB');
        }

        // V5C & GPS Trackers Shortcuts
        function updateV5CButtonState(v5cCount, transferCount) {
            const bV5C = document.getElementById('badge_v5c_count');
            const bBtn = document.getElementById('btnShortcutV5C');
            const cV5C = Number(v5cCount || 0);
            const cTransfer = Number(transferCount || 0);

            if (bV5C) {
                if (cV5C > 0) {
                    bV5C.textContent = cV5C;
                    bV5C.style.background = 'rgba(6, 182, 212, 0.25)';
                    bV5C.style.color = '#22d3ee';
                    bV5C.style.border = '1px solid rgba(6, 182, 212, 0.4)';
                } else if (cTransfer > 0) {
                    bV5C.textContent = '⏳ Slip';
                    bV5C.style.background = 'rgba(245, 158, 11, 0.25)';
                    bV5C.style.color = '#fbbf24';
                    bV5C.style.border = '1px solid rgba(245, 158, 11, 0.5)';
                } else {
                    bV5C.textContent = '0';
                    bV5C.style.background = 'rgba(239, 68, 68, 0.35)';
                    bV5C.style.color = '#fecaca';
                    bV5C.style.border = '1px solid rgba(239, 68, 68, 0.5)';
                }
            }
            if (bBtn) {
                if (cV5C > 0) {
                    bBtn.style.background = 'rgba(6, 182, 212, 0.12)';
                    bBtn.style.borderColor = 'rgba(6, 182, 212, 0.35)';
                    bBtn.style.color = '#22d3ee';
                    bBtn.title = `Official V5C Logbook on file (${cV5C} page(s))`;
                } else if (cTransfer > 0) {
                    bBtn.style.background = 'rgba(245, 158, 11, 0.12)';
                    bBtn.style.borderColor = 'rgba(245, 158, 11, 0.4)';
                    bBtn.style.color = '#fbbf24';
                    bBtn.title = '⏳ Transfer Slip on file - awaiting postal V5C from DVLA';
                } else {
                    bBtn.style.background = 'rgba(239, 68, 68, 0.12)';
                    bBtn.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                    bBtn.style.color = '#fca5a5';
                    bBtn.title = '⚠️ Missing V5C Logbook! Click to attach';
                }
            }
        }

        updateV5CButtonState(data.v5c_count, data.transfer_proof_count);

        const badgeTrk = document.getElementById('badge_trackers_count');
        if (badgeTrk) {
            badgeTrk.textContent = (data.trackers_count !== undefined && data.trackers_count !== null) ? data.trackers_count : 0;
        }

        const btnV5C = document.getElementById('btnShortcutV5C');
        if (btnV5C) {
            btnV5C.onclick = () => {
                if (placaVal && placaVal !== '-' && typeof abrirModalMoto === 'function') {
                    abrirModalMoto(placaVal, 'tabV5C', {
                        modelo: modeloVal,
                        cor: corVal,
                        milhagem_atual: data.milhagem_atual_moto || data.milhagem_final || data.milhagem_inicial,
                        vencimento_mot: data.vencimento_mot,
                        vencimento_tax: data.vencimento_tax,
                        tax_sorn: data.tax_sorn,
                        id_contrato: (typeof CONTRATO_ID !== 'undefined' ? CONTRATO_ID : data.id)
                    });
                } else if (!placaVal || placaVal === '-') {
                    alert('No vehicle registration plate linked to this contract.');
                }
            };
        }

        const btnTrk = document.getElementById('btnShortcutTrackers');
        if (btnTrk) {
            btnTrk.onclick = () => {
                if (placaVal && placaVal !== '-' && typeof abrirModalMoto === 'function') {
                    abrirModalMoto(placaVal, 'tabTrackers', {
                        modelo: modeloVal,
                        cor: corVal,
                        milhagem_atual: data.milhagem_atual_moto || data.milhagem_final || data.milhagem_inicial,
                        vencimento_mot: data.vencimento_mot,
                        vencimento_tax: data.vencimento_tax,
                        tax_sorn: data.tax_sorn
                    });
                } else if (!placaVal || placaVal === '-') {
                    alert('No vehicle registration plate linked to this contract.');
                }
            };
        }

        window.onMotoModalUpdated = async function(placa) {
            if (!placa) return;
            try {
                const res = await fetch(`/api/motos/${encodeURIComponent(placa)}/detalhes`);
                if (res.ok) {
                    const d = await res.json();
                    updateV5CButtonState(d.v5c_count, d.transfer_proof_count);
                    const bTrk = document.getElementById('badge_trackers_count');
                    if (bTrk) bTrk.textContent = (d.trackers || []).length;
                }
            } catch(err) {
                console.error('Error refreshing vehicle badges:', err);
            }
        };

        // Mileage Tracker
        const isPurchaseContrato = (data.tipo_contrato === 'Purchase');
        const isVendaContrato = (data.tipo_contrato === 'Sale_Full' || data.tipo_contrato === 'Sale_Installment');
        const labelStartMileage = document.getElementById('label_milhagem_inicial');
        if (labelStartMileage) {
            labelStartMileage.textContent = isPurchaseContrato ? 'Purchase Mileage:' : (isVendaContrato ? 'Sale Mileage:' : 'Start Mileage:');
        }
        const elStartMileage = document.getElementById('info_milhagem_inicial');
        if (elStartMileage) {
            if (isPurchaseContrato && data.milhagem_nao_verificada) {
                elStartMileage.textContent = 'Unverified (Non-runner)';
            } else {
                elStartMileage.textContent = (data.milhagem_inicial !== undefined && data.milhagem_inicial !== null) ? `${data.milhagem_inicial.toLocaleString('en-GB')} miles` : '0 miles';
            }
        }
        const rowEndMileage = document.getElementById('row_milhagem_final');
        const elEndMileage = document.getElementById('info_milhagem_final');
        if (rowEndMileage) {
            if (isVendaContrato || isPurchaseContrato) {
                rowEndMileage.style.display = 'none';
            } else {
                rowEndMileage.style.display = 'flex';
                if (elEndMileage) {
                    elEndMileage.textContent = (data.milhagem_final !== undefined && data.milhagem_final !== null) ? `${data.milhagem_final.toLocaleString('en-GB')} miles` : 'Pending return';
                }
            }
        }
        const rowDistance = document.getElementById('row_milhas_rodadas');
        const elDistance = document.getElementById('info_milhas_rodadas');
        if (rowDistance && elDistance) {
            if (!isVendaContrato && !isPurchaseContrato && data.milhas_rodadas !== undefined && data.milhas_rodadas !== null) {
                rowDistance.style.display = 'flex';
                elDistance.textContent = `${data.milhas_rodadas.toLocaleString('en-GB')} miles driven`;
            } else {
                rowDistance.style.display = 'none';
            }
        }

        // Helper for compliance date evaluation
        function evaluateCompliance(dateStr) {
            if (!dateStr) return { status: 'none', diffDays: null, formattedDate: '-' };
            const parts = dateStr.split('-');
            if (parts.length !== 3) return { status: 'none', diffDays: null, formattedDate: dateStr };
            const due = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const formattedDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
            const diffDays = Math.ceil((due - today) / (1000 * 60 * 60 * 24));
            
            if (diffDays < 0) return { status: 'expired', diffDays: Math.abs(diffDays), formattedDate };
            if (diffDays <= 30) return { status: 'warning', diffDays, formattedDate };
            return { status: 'valid', diffDays, formattedDate };
        }

        function renderComplianceRow(title, evalResult) {
            if (evalResult.status === 'expired') {
                return `
                    <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.45); border-radius: 8px; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem;">
                        <div>
                            <span style="color: var(--text-secondary); font-size: 0.72rem; text-transform: uppercase; font-weight: 600; display: block;">${title}</span>
                            <strong style="color: #f87171;">${evalResult.formattedDate}</strong>
                        </div>
                        <span class="badge badge-danger" style="font-weight: 700; font-size: 0.72rem; padding: 3px 8px; letter-spacing: 0.02em;">
                            🚨 EXPIRED (${evalResult.diffDays}d ago)
                        </span>
                    </div>
                `;
            } else if (evalResult.status === 'warning') {
                return `
                    <div style="background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.45); border-radius: 8px; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem;">
                        <div>
                            <span style="color: var(--text-secondary); font-size: 0.72rem; text-transform: uppercase; font-weight: 600; display: block;">${title}</span>
                            <strong style="color: #fbbf24;">${evalResult.formattedDate}</strong>
                        </div>
                        <span class="badge badge-warning" style="font-weight: 700; font-size: 0.72rem; padding: 3px 8px; letter-spacing: 0.02em;">
                            ⏳ Due in ${evalResult.diffDays}d
                        </span>
                    </div>
                `;
            } else if (evalResult.status === 'sorn') {
                return `
                    <div style="background: rgba(168, 85, 247, 0.12); border: 1px solid rgba(168, 85, 247, 0.35); border-radius: 8px; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem;">
                        <div>
                            <span style="color: var(--text-secondary); font-size: 0.72rem; text-transform: uppercase; font-weight: 600; display: block;">${title}</span>
                            <strong style="color: #c084fc;">Off Road (SORN)</strong>
                        </div>
                        <span class="badge" style="background: rgba(168,85,247,0.25); color: #c084fc; border: 1px solid rgba(168,85,247,0.45); font-weight: 700; font-size: 0.72rem; padding: 3px 8px;">
                            🛡️ SORN
                        </span>
                    </div>
                `;
            } else if (evalResult.status === 'valid') {
                return `
                    <div style="background: rgba(34, 197, 94, 0.08); border: 1px solid rgba(34, 197, 94, 0.25); border-radius: 8px; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem;">
                        <div>
                            <span style="color: var(--text-secondary); font-size: 0.72rem; text-transform: uppercase; font-weight: 600; display: block;">${title}</span>
                            <strong style="color: var(--text-primary);">${evalResult.formattedDate}</strong>
                        </div>
                        <span style="color: #4ade80; font-weight: 600; font-size: 0.75rem; display: inline-flex; align-items: center; gap: 4px;">
                            ✓ Valid
                        </span>
                    </div>
                `;
            } else {
                return `
                    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-color); border-radius: 8px; padding: 6px 10px; display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem;">
                        <div>
                            <span style="color: var(--text-secondary); font-size: 0.72rem; text-transform: uppercase; font-weight: 600; display: block;">${title}</span>
                            <span style="color: var(--text-secondary);">-</span>
                        </div>
                        <span style="color: var(--text-secondary); font-size: 0.75rem;">Not registered</span>
                    </div>
                `;
            }
        }

        // Road Tax evaluated first, then MOT
        const taxEval = data.tax_sorn
            ? { status: 'sorn', formattedDate: 'SORN (Off Road)', diffDays: 0 }
            : evaluateCompliance(data.vencimento_tax);
        const motEval = evaluateCompliance(data.vencimento_mot);

        const motTaxBox = document.getElementById('info_mot_tax');
        if (motTaxBox) {
            motTaxBox.innerHTML = renderComplianceRow(data.tax_sorn ? 'Road Tax Status' : 'Road Tax Expiry', taxEval) + renderComplianceRow('MOT Expiry', motEval);
        }

        window._contractData = data;
        const stLower = (data.status || '').toLowerCase();
        const isActiveContract = (stLower === 'active' || stLower === 'ativo');
        const hasCheckoutInsp = (data.vistorias || []).some(v => ['check-out', 'checkout', 'saída', 'saida'].includes((v.tipo || '').toLowerCase()));
        const hasInsuranceDoc = Boolean(data.url_seguro);
        const isPreReleasePending = !isPurchaseContrato && isActiveContract && (!hasCheckoutInsp || !hasInsuranceDoc);

        // Dynamic Pre-Delivery Compliance Alert Banner (Vehicle cannot leave premises without Check-out Inspection and Insurance) & Purchase V5C Required Alert
        const preBanner = document.getElementById('prerelease_alert_banner');
        if (preBanner) {
            if (isPurchaseContrato && isActiveContract && (Number(data.v5c_count || 0) === 0)) {
                preBanner.style.display = 'block';
                preBanner.innerHTML = `
                    <div style="background: rgba(6, 182, 212, 0.12); border: 1.5px solid rgba(6, 182, 212, 0.5); border-left: 6px solid #06b6d4; border-radius: 12px; padding: 1rem 1.25rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                        <div style="display: flex; align-items: center; gap: 14px;">
                            <span style="font-size: 2rem;">📑</span>
                            <div>
                                <strong style="color: #22d3ee; font-size: 1rem; display: block; letter-spacing: 0.02em;">
                                    LOGBOOK (V5C) REQUIRED: Purchase Agreement Incomplete
                                </strong>
                                <span style="color: var(--text-primary); font-size: 0.88rem; line-height: 1.4; display: block; margin-top: 2px;">
                                    This purchase contract for vehicle <strong>(${escapeHtml(data.placa)})</strong> cannot be finalized until the official vehicle Logbook (V5C) document is attached.
                                    ${Number(data.transfer_proof_count || 0) > 0 ? '<span style="display:block; margin-top:4px; font-size:0.8rem; color:#fbbf24; font-weight:600;">⏳ Transfer slip is on file. Awaiting official V5C logbook from DVLA to finalize purchase.</span>' : ''}
                                </span>
                            </div>
                        </div>
                        <div>
                            <button type="button" id="btnBannerUploadV5C" class="btn-primary" style="background: #06b6d4; color: #000; font-weight: 700; font-size: 0.82rem; padding: 7px 14px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; border: none; white-space: nowrap;">
                                <span>📄</span> Upload V5C Logbook
                            </button>
                        </div>
                    </div>
                `;

                const btnBannerV5C = document.getElementById('btnBannerUploadV5C');
                if (btnBannerV5C) {
                    btnBannerV5C.onclick = () => {
                        const btnV5C = document.getElementById('btnShortcutV5C');
                        if (btnV5C) {
                            btnV5C.click();
                        } else if (typeof window.abrirModalV5C === 'function') {
                            window.abrirModalV5C();
                        }
                    };
                }
            } else if (isPreReleasePending) {
                preBanner.style.display = 'block';
                const missingList = [];
                if (!hasCheckoutInsp) missingList.push('Initial Check-out Inspection Photos');
                if (!hasInsuranceDoc) missingList.push('Customer Insurance Certificate');

                let actionBtnsHtml = '<div style="display: flex; gap: 8px; flex-wrap: wrap;">';
                if (!hasCheckoutInsp) {
                    actionBtnsHtml += `
                        <button type="button" id="btnBannerTakeInspection" class="btn-primary" style="background: #f59e0b; color: #000; font-weight: 700; font-size: 0.82rem; padding: 7px 14px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; border: none; white-space: nowrap;">
                            <span>📸</span> Record Check-out Inspection
                        </button>
                    `;
                }
                if (!hasInsuranceDoc) {
                    actionBtnsHtml += `
                        <button type="button" id="btnBannerAttachInsurance" class="btn-primary" style="background: #3b82f6; color: #fff; font-weight: 700; font-size: 0.82rem; padding: 7px 14px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; border: none; white-space: nowrap;">
                            <span>🛡️</span> Upload Insurance Document
                        </button>
                    `;
                }
                actionBtnsHtml += '</div>';

                preBanner.innerHTML = `
                    <div style="background: rgba(245, 158, 11, 0.12); border: 1.5px solid rgba(245, 158, 11, 0.5); border-left: 6px solid #f59e0b; border-radius: 12px; padding: 1rem 1.25rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                        <div style="display: flex; align-items: center; gap: 14px;">
                            <span style="font-size: 2rem;">⚠️</span>
                            <div>
                                <strong style="color: #fbbf24; font-size: 1rem; display: block; letter-spacing: 0.02em;">
                                    VEHICLE PRE-DELIVERY PENDING: Cannot be released yet!
                                </strong>
                                <span style="color: var(--text-primary); font-size: 0.88rem; line-height: 1.4; display: block; margin-top: 2px;">
                                    This motorbike <strong>(${escapeHtml(data.placa)})</strong> cannot leave shop premises without: <strong style="color: #fde047;">${missingList.join(' and ')}</strong>.
                                </span>
                            </div>
                        </div>
                        ${actionBtnsHtml}
                    </div>
                `;

                const btnBInsp = document.getElementById('btnBannerTakeInspection');
                if (btnBInsp) {
                    btnBInsp.onclick = () => {
                        if (typeof window.abrirModalCheckOutVistoria === 'function') window.abrirModalCheckOutVistoria();
                    };
                }

                const btnBIns = document.getElementById('btnBannerAttachInsurance');
                if (btnBIns) {
                    btnBIns.onclick = () => {
                        const fileInput = document.getElementById('update_seguro_file');
                        if (fileInput) fileInput.click();
                    };
                }
            } else {
                preBanner.style.display = 'none';
                preBanner.innerHTML = '';
            }
        }

        // Top Compliance Warning Banner
        const compBanner = document.getElementById('compliance_alert_banner');
        if (compBanner) {
            const expiredList = [];
            const warningList = [];
            
            if (taxEval.status === 'expired') expiredList.push(`Road Tax (expired ${taxEval.diffDays}d ago on ${taxEval.formattedDate})`);
            else if (taxEval.status === 'warning') warningList.push(`Road Tax (due in ${taxEval.diffDays}d on ${taxEval.formattedDate})`);

            if (motEval.status === 'expired') expiredList.push(`MOT (expired ${motEval.diffDays}d ago on ${motEval.formattedDate})`);
            else if (motEval.status === 'warning') warningList.push(`MOT (due in ${motEval.diffDays}d on ${motEval.formattedDate})`);

            // Include Insurance status in top banner (only for rentals, sales and purchases don't monitor 15-day insurance)
            if (!isVendaContrato && !isPurchaseContrato) {
                if (data.status_seguro === 'Cancelled') {
                    expiredList.push('Motor Insurance (FLAGGED CANCELLED ON askMID)');
                } else if (data.checagem_seguro_devida) {
                    warningList.push(`15-day askMID Insurance Check Due (${data.dias_desde_checagem_seguro}d since last check)`);
                }
            }

            if (expiredList.length > 0) {
                compBanner.style.display = 'block';
                compBanner.innerHTML = `
                    <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid #ef4444; border-left: 5px solid #ef4444; border-radius: 10px; padding: 1rem 1.25rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-size: 1.75rem;">🚨</span>
                            <div>
                                <strong style="color: #f87171; font-size: 1rem; display: block;">URGENT FLEET COMPLIANCE ALERT</strong>
                                <span style="color: var(--text-primary); font-size: 0.88rem;">
                                    Vehicle <strong>${data.placa}</strong> has EXPIRED compliance: <strong>${expiredList.join(' • ')}</strong>. This motorbike cannot be legally ridden on UK roads!
                                </span>
                            </div>
                        </div>
                        <a href="/motos" class="btn-action" style="background: #ef4444; color: #fff; text-decoration: none; padding: 8px 16px; font-size: 0.85rem; font-weight: 600; border-radius: 6px; white-space: nowrap;">
                            Manage in Fleet &rarr;
                        </a>
                    </div>
                `;
            } else if (warningList.length > 0) {
                compBanner.style.display = 'block';
                compBanner.innerHTML = `
                    <div style="background: rgba(245, 158, 11, 0.12); border: 1px solid #f59e0b; border-left: 5px solid #f59e0b; border-radius: 10px; padding: 1rem 1.25rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <span style="font-size: 1.75rem;">⏳</span>
                            <div>
                                <strong style="color: #fbbf24; font-size: 1rem; display: block;">UPCOMING COMPLIANCE RENEWAL</strong>
                                <span style="color: var(--text-primary); font-size: 0.88rem;">
                                    Vehicle <strong>${data.placa}</strong> renewal due soon: <strong>${warningList.join(' • ')}</strong>.
                                </span>
                            </div>
                        </div>
                        <a href="/motos" class="btn-action" style="background: #f59e0b; color: #000; text-decoration: none; padding: 8px 16px; font-size: 0.85rem; font-weight: 600; border-radius: 6px; white-space: nowrap;">
                            Manage in Fleet &rarr;
                        </a>
                    </div>
                `;
            } else {
                compBanner.style.display = 'none';
                compBanner.innerHTML = '';
            }
        }
        
        // 3. Insurance Section Rendering
        const isVenda = (data.tipo_contrato === 'Sale_Full' || data.tipo_contrato === 'Sale_Installment');
        const titleSeguro = document.getElementById('title_seguro_section');
        const badgeSeguro = document.getElementById('badge_status_seguro');
        const boxSeguro = document.getElementById('box_seguro_compliance');
        const rowBotoesAskmid = document.getElementById('row_botoes_askmid');
        const btnReportarSeguroCancelado = document.getElementById('btnReportarSeguroCancelado');
        const dataVerifEl = document.getElementById('info_seguro_data_verif');
        const proxVerifEl = document.getElementById('info_seguro_proxima_verif');
        const verifPorEl = document.getElementById('info_seguro_verificado_por');
        const verifPorRow = document.getElementById('info_seguro_verif_por_row');
        const infoSeguro = document.getElementById('info_seguro');

        if (isPurchaseContrato) {
            const boxSeguroSection = document.getElementById('box_seguro_section');
            if (boxSeguroSection) boxSeguroSection.style.display = 'none';
            if (titleSeguro) {
                titleSeguro.innerHTML = '🛡️ Vehicle Acquisition Status';
            }
            if (badgeSeguro) {
                badgeSeguro.className = 'badge';
                badgeSeguro.innerHTML = '✓ Inventory Inward';
                badgeSeguro.style.cssText = 'background: rgba(6,182,212,0.15); color: #22d3ee; border: 1px solid rgba(6,182,212,0.3); font-weight:600;';
            }
            if (boxSeguro) boxSeguro.style.display = 'none';
            if (rowBotoesAskmid) rowBotoesAskmid.style.display = 'none';
            if (btnReportarSeguroCancelado) btnReportarSeguroCancelado.style.display = 'none';
            if (infoSeguro) infoSeguro.innerHTML = '';
        } else if (isVenda) {
            // Moto vendida: NÃO monitorar de 15 em 15 dias. Apenas armazenar e exibir o documento entregue na venda.
            if (titleSeguro) {
                titleSeguro.innerHTML = '🛡️ Motor Insurance Certificate';
            }
            if (badgeSeguro) {
                if (data.url_seguro) {
                    badgeSeguro.className = 'badge badge-success';
                    badgeSeguro.innerHTML = '✓ Document On File';
                    badgeSeguro.style.cssText = 'background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); font-weight:600;';
                } else {
                    badgeSeguro.className = 'badge badge-warning';
                    badgeSeguro.innerHTML = '⚠️ No Document';
                    badgeSeguro.style.cssText = 'background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.4); font-weight:600;';
                }
            }
            // Oculta caixa de compliance periódico de 15 dias
            if (boxSeguro) boxSeguro.style.display = 'none';
            // Oculta botões de rotina do askMID
            if (rowBotoesAskmid) rowBotoesAskmid.style.display = 'none';
            if (btnReportarSeguroCancelado) btnReportarSeguroCancelado.style.display = 'none';

            // Exibe botão em destaque para ver ou atualizar o documento
            if (infoSeguro) {
                if (data.url_seguro) {
                    infoSeguro.innerHTML = `
                        <a href="${data.url_seguro}" target="_blank" class="btn-action" style="font-size: 0.8rem; padding: 7px 10px; text-decoration: none; flex: 1; text-align: center; border-radius: 6px; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.35); color: #60a5fa; font-weight: 600;">📄 View Insurance Certificate</a>
                        <button class="btn-action btn-atualizar-seguro" style="font-size: 0.8rem; padding: 7px 10px; background: rgba(255,255,255,0.08); border: 1px solid var(--border-color); color: var(--text-primary); border-radius: 6px;">Update</button>
                    `;
                } else {
                    infoSeguro.innerHTML = `
                        <button class="btn-action btn-atualizar-seguro" style="font-size: 0.8rem; padding: 7px 10px; background: var(--accent); flex: 1; border-radius: 6px; font-weight: 600;">+ Attach Insurance Certificate</button>
                    `;
                }
            }
        } else {
            // Contrato de Aluguel (Rent): monitoramento padrão de 15 em 15 dias no askMID
            if (titleSeguro) {
                titleSeguro.innerHTML = '🛡️ Motor Insurance (askMID)';
            }
            if (boxSeguro) boxSeguro.style.display = 'block';
            if (rowBotoesAskmid) rowBotoesAskmid.style.display = 'flex';
            if (btnReportarSeguroCancelado) btnReportarSeguroCancelado.style.display = 'block';

            if (badgeSeguro) {
                if (!data.url_seguro) {
                    badgeSeguro.className = 'badge badge-warning';
                    badgeSeguro.innerHTML = '⚠️ No Document (Pre-Release)';
                    badgeSeguro.style.cssText = 'background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.4); font-weight:700;';
                    if (boxSeguro) {
                        boxSeguro.style.borderColor = 'rgba(245, 158, 11, 0.4)';
                        boxSeguro.style.background = 'rgba(245, 158, 11, 0.05)';
                    }
                } else if (data.status_seguro === 'Cancelled') {
                    badgeSeguro.className = 'badge badge-danger';
                    badgeSeguro.innerHTML = '🚨 CANCELLED / UNINSURED';
                    badgeSeguro.style.cssText = 'background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.4); font-weight:700;';
                    if (boxSeguro) {
                        boxSeguro.style.borderColor = 'rgba(239, 68, 68, 0.5)';
                        boxSeguro.style.background = 'rgba(239, 68, 68, 0.08)';
                    }
                } else if (data.checagem_seguro_devida) {
                    badgeSeguro.className = 'badge badge-warning';
                    badgeSeguro.innerHTML = `⏳ Check Due (${data.dias_desde_checagem_seguro}d ago)`;
                    badgeSeguro.style.cssText = 'background: rgba(245,158,11,0.2); color: #fbbf24; border: 1px solid rgba(245,158,11,0.4); font-weight:700;';
                    if (boxSeguro) {
                        boxSeguro.style.borderColor = 'rgba(245, 158, 11, 0.5)';
                        boxSeguro.style.background = 'rgba(245, 158, 11, 0.08)';
                    }
                } else {
                    badgeSeguro.className = 'badge badge-success';
                    badgeSeguro.innerHTML = '✓ Active on askMID';
                    badgeSeguro.style.cssText = 'background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); font-weight:600;';
                    if (boxSeguro) {
                        boxSeguro.style.borderColor = 'var(--border-color)';
                        boxSeguro.style.background = 'rgba(255,255,255,0.03)';
                    }
                }
            }

            if (dataVerifEl) {
                const dv = data.data_ultima_checagem_seguro ? new Date(data.data_ultima_checagem_seguro + 'T00:00:00').toLocaleDateString('en-GB') : '-';
                dataVerifEl.innerHTML = `${dv} <span style="color: var(--text-secondary); font-size: 0.75rem; font-weight: normal;">(${data.dias_desde_checagem_seguro || 0}d ago)</span>`;
            }

            if (proxVerifEl) {
                if (data.status_seguro === 'Cancelled') {
                    proxVerifEl.innerHTML = '<span style="color: #f87171; font-weight: 700;">UNINSURED ALERT</span>';
                } else if (data.checagem_seguro_devida) {
                    const overdue = (data.dias_desde_checagem_seguro || 15) - 15;
                    proxVerifEl.innerHTML = `<span style="color: #fbbf24; font-weight: 700;">CHECK DUE NOW (${overdue > 0 ? `${overdue}d overdue` : 'Today'})</span>`;
                } else {
                    proxVerifEl.innerHTML = `<span style="color: #4ade80;">Due in ${data.dias_para_proxima_checagem_seguro || 0} days</span>`;
                }
            }

            if (verifPorEl) {
                if (data.seguro_verificado_por) {
                    verifPorEl.textContent = data.seguro_verificado_por;
                    if (verifPorRow) verifPorRow.style.display = 'flex';
                } else {
                    if (verifPorRow) verifPorRow.style.display = 'none';
                }
            }

            if (infoSeguro) {
                if (data.url_seguro) {
                    infoSeguro.innerHTML = `
                        <a href="${data.url_seguro}" target="_blank" class="btn-action" style="font-size: 0.75rem; padding: 5px 8px; text-decoration: none; flex: 1; text-align: center; border-radius: 6px;">📄 Policy</a>
                        <button class="btn-action btn-atualizar-seguro" style="font-size: 0.75rem; padding: 5px 8px; background: rgba(255,255,255,0.08); border: 1px solid var(--border-color); color: var(--text-primary); border-radius: 6px;">Update</button>
                    `;
                } else {
                    infoSeguro.innerHTML = `
                        <button class="btn-action btn-atualizar-seguro" style="font-size: 0.75rem; padding: 5px 8px; background: var(--accent); flex: 1; border-radius: 6px;">+ Attach Policy</button>
                    `;
                }
            }
        }

        // Setup askMID check and verification buttons
        const btnCheckAskMid = document.getElementById('btnCheckAskMid');
        if (btnCheckAskMid) {
            btnCheckAskMid.onclick = () => {
                if (data.placa) {
                    navigator.clipboard.writeText(data.placa).then(() => {
                        alert(`Registration plate "${data.placa}" copied to clipboard!\n\nOpening official askMID.com database to verify vehicle insurance status...`);
                    }).catch(() => {
                        alert(`Opening askMID.com for plate: ${data.placa}`);
                    });
                }
                window.open('https://www.askmid.com/', '_blank');
            };
        }

        const btnConfirmarSeguroValido = document.getElementById('btnConfirmarSeguroValido');
        if (btnConfirmarSeguroValido) {
            btnConfirmarSeguroValido.onclick = async () => {
                if (!confirm(`Confirm that insurance for motorbike ${data.placa} is ACTIVE and VALID on askMID today?\n\nThis will record your staff verification and reset the 15-day check schedule.`)) {
                    return;
                }
                try {
                    const res = await fetch(`/api/contratos/${CONTRATO_ID}/verificar-seguro`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ status: 'Valid' })
                    });
                    const resData = await res.json();
                    if (res.ok) {
                        alert(resData.message || 'Insurance verified successfully!');
                        location.reload();
                    } else {
                        alert(resData.error || 'Failed to record verification');
                    }
                } catch (e) {
                    console.error('Error verifying insurance:', e);
                    alert('Connection error');
                }
            };
        }

        if (btnReportarSeguroCancelado) {
            btnReportarSeguroCancelado.onclick = async () => {
                if (!confirm(`🚨 CRITICAL WARNING:\n\nAre you sure you want to flag vehicle ${data.placa} as UNINSURED / CANCELLED?\n\nThis will trigger urgent compliance alerts across the dashboard and contract.`)) {
                    return;
                }
                try {
                    const res = await fetch(`/api/contratos/${CONTRATO_ID}/verificar-seguro`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ status: 'Cancelled' })
                    });
                    const resData = await res.json();
                    if (res.ok) {
                        alert(resData.message || 'Insurance cancellation recorded!');
                        location.reload();
                    } else {
                        alert(resData.error || 'Failed to record cancellation');
                    }
                } catch (e) {
                    console.error('Error reporting cancelled insurance:', e);
                    alert('Connection error');
                }
            };
        }
        
        // Upload Seguro
        const updateSeguroBtn = document.querySelector('.btn-atualizar-seguro');
        const updateSeguroInput = document.getElementById('update_seguro_file');
        if (updateSeguroBtn && updateSeguroInput) {
            updateSeguroBtn.addEventListener('click', () => updateSeguroInput.click());
            updateSeguroInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                
                const formData = new FormData();
                if (file.type.startsWith('image/')) {
                    try {
                        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
                        const compOptions = {
                            maxSizeMB: 0.35,
                            maxWidthOrHeight: 1600,
                            useWebWorker: !isIOS,
                            fileType: isIOS ? 'image/jpeg' : 'image/webp',
                            initialQuality: 0.75
                        };
                        const compressedFile = await imageCompression(file, compOptions);
                        formData.append('seguro', compressedFile, file.name.replace(/\.[^/.]+$/, isIOS ? '.jpg' : '.webp'));
                    } catch (err) {
                        formData.append('seguro', file);
                    }
                } else {
                    formData.append('seguro', file);
                }
                
                try {
                    const res = await fetch(`/api/contratos/${CONTRATO_ID}/seguro`, {
                        method: 'PUT',
                        body: formData
                    });
                    if (res.ok) {
                        alert('Insurance updated successfully!');
                        location.reload();
                    } else {
                        const resJson = await res.json();
                        alert(resJson.message || resJson.mensagem || resJson.error || resJson.erro || 'Failed to update insurance');
                    }
                } catch (err) {
                    alert('Connection error while updating insurance.');
                }
            });
        }
        
        // 3. Contract Card & Header Type Badges
        const elHeaderTipo = document.getElementById('header_tipo_badge');
        const elInfoTipo = document.getElementById('info_tipo_badge');
        
        if (data.tipo_contrato === 'Purchase') {
            if (elHeaderTipo) {
                elHeaderTipo.className = 'badge';
                elHeaderTipo.style.cssText = 'background: rgba(6, 182, 212, 0.2); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.4); font-weight: 700; font-size: 0.85rem; padding: 4px 12px; border-radius: 9999px;';
                elHeaderTipo.textContent = '🤝 Used Vehicle Purchase';
            }
            if (elInfoTipo) {
                elInfoTipo.className = 'badge';
                elInfoTipo.style.cssText = 'background: rgba(6, 182, 212, 0.15); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.35); font-weight: 700;';
                elInfoTipo.textContent = 'Vehicle Purchase';
            }
        } else if (data.tipo_contrato === 'Sale_Full') {
            if (elHeaderTipo) {
                elHeaderTipo.className = 'badge';
                elHeaderTipo.style.cssText = 'background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); font-weight: 700; font-size: 0.85rem; padding: 4px 12px; border-radius: 9999px;';
                elHeaderTipo.textContent = '💰 Sale: Full Payment';
            }
            if (elInfoTipo) {
                elInfoTipo.className = 'badge';
                elInfoTipo.style.cssText = 'background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); font-weight: 700;';
                elInfoTipo.textContent = 'Sale: Full Payment';
            }
        } else if (data.tipo_contrato === 'Sale_Installment') {
            if (elHeaderTipo) {
                elHeaderTipo.className = 'badge';
                elHeaderTipo.style.cssText = 'background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); font-weight: 700; font-size: 0.85rem; padding: 4px 12px; border-radius: 9999px;';
                elHeaderTipo.textContent = '📊 Sale: Instalment';
            }
            if (elInfoTipo) {
                elInfoTipo.className = 'badge';
                elInfoTipo.style.cssText = 'background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.35); font-weight: 700;';
                elInfoTipo.textContent = 'Sale: Instalment';
            }
        } else {
            if (elHeaderTipo) {
                elHeaderTipo.className = 'badge';
                elHeaderTipo.style.cssText = 'background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); font-weight: 700; font-size: 0.85rem; padding: 4px 12px; border-radius: 9999px;';
                elHeaderTipo.textContent = '🛵 Rental Agreement';
            }
            if (elInfoTipo) {
                elInfoTipo.className = 'badge';
                elInfoTipo.style.cssText = 'background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.35); font-weight: 700;';
                elInfoTipo.textContent = 'Rental Agreement';
            }
        }

        let statusBadge = '';
        if (stLower === 'active' || stLower === 'ativo') statusBadge = '<span class="badge badge-success">ACTIVE</span>';
        else if (stLower === 'deposit_hold' || stLower === 'quarentena_deposito') statusBadge = '<span class="badge badge-warning">DEPOSIT HOLD</span>';
        else if (stLower === 'completed' || stLower === 'finalizado') statusBadge = '<span class="badge badge-secondary">COMPLETED</span>';
        else if (stLower === 'cancelled' || stLower === 'cancelado') statusBadge = '<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); font-weight: 700;">CANCELLED</span>';
        else statusBadge = `<span class="badge badge-info">${(data.status || '').toUpperCase()}</span>`;
        document.getElementById('info_status').innerHTML = statusBadge;

        // isVenda and isPurchaseContrato already declared above
        const blocoAluguel = document.getElementById('bloco_termos_aluguel');
        const blocoVenda = document.getElementById('bloco_termos_venda');
        const blocoCompra = document.getElementById('bloco_termos_compra');

        if (isPurchaseContrato) {
            if (blocoAluguel) blocoAluguel.style.display = 'none';
            if (blocoVenda) blocoVenda.style.display = 'none';
            if (blocoCompra) {
                blocoCompra.style.display = 'block';
                const elValor = document.getElementById('info_compra_valor');
                const elMetodo = document.getElementById('info_compra_metodo');
                const elDetalhes = document.getElementById('info_compra_detalhes');
                const elCat = document.getElementById('info_compra_categoria');
                const elStatus = document.getElementById('info_compra_status_destino');

                if (elValor) elValor.textContent = formatoMoeda.format(data.valor_compra_veiculo || 0);
                if (elMetodo) elMetodo.textContent = data.metodo_pagamento_compra || '-';
                if (elDetalhes) elDetalhes.textContent = data.detalhes_pagamento_compra || '-';
                if (elCat) elCat.textContent = data.categoria_historico || 'Clear';
                if (elStatus) elStatus.textContent = data.status_moto_destino || 'Available';
            }
        } else if (isVenda) {
            if (blocoAluguel) blocoAluguel.style.display = 'none';
            if (blocoCompra) blocoCompra.style.display = 'none';
            if (blocoVenda) {
                blocoVenda.style.display = 'block';
                const elTotal = document.getElementById('info_venda_total');
                const elCat = document.getElementById('info_venda_categoria');
                const elPreco = document.getElementById('info_venda_preco');
                const elExtras = document.getElementById('info_venda_extras');
                const rowEntrada = document.getElementById('row_venda_entrada');
                const elEntrada = document.getElementById('info_venda_entrada');
                const rowSaldo = document.getElementById('row_venda_saldo');
                const elSaldo = document.getElementById('info_venda_saldo');

                if (elTotal) elTotal.textContent = formatoMoeda.format(data.valor_total_venda || 0);
                if (elCat) elCat.textContent = data.categoria_historico || 'Clear';
                if (elPreco) elPreco.textContent = formatoMoeda.format(data.valor_venda_veiculo || 0);
                
                let extrasStr = '-';
                if (data.acessorios_extras || data.valor_admin_fee) {
                    const parts = [];
                    if (data.acessorios_extras) parts.push(data.acessorios_extras);
                    if (data.valor_admin_fee) parts.push(`Admin Fee: ${formatoMoeda.format(data.valor_admin_fee)}`);
                    extrasStr = parts.join(' | ');
                }
                if (elExtras) elExtras.textContent = extrasStr;

                if (data.tipo_contrato === 'Sale_Installment') {
                    if (rowEntrada) rowEntrada.style.display = 'block';
                    if (elEntrada) elEntrada.textContent = formatoMoeda.format(data.valor_entrada || 0);
                    if (rowSaldo) rowSaldo.style.display = 'block';
                    if (elSaldo) elSaldo.textContent = formatoMoeda.format(data.saldo_devedor || 0);
                } else {
                    if (rowEntrada) rowEntrada.style.display = 'none';
                    if (rowSaldo) rowSaldo.style.display = 'none';
                }
            }

            // Sale contracts: tailor manual charges and inspection link
            const selectCobTipo = document.getElementById('cob_tipo');
            if (selectCobTipo) {
                selectCobTipo.innerHTML = `
                    <option value="Sale_Installment">Sale Instalment / Parcela de Venda</option>
                    <option value="Sale_Deposit">Sale Down Payment (Deposit) / Entrada de Venda</option>
                    <option value="Fine">Fine / Penalty</option>
                    <option value="Damage">Damage / Repair</option>
                    <option value="Other">Other</option>
                `;
            }
            const btnNovaVistoriaLink = document.getElementById('btnNovaVistoriaLink');
            if (btnNovaVistoriaLink) {
                btnNovaVistoriaLink.href = `/vistorias/nova?contrato_id=${CONTRATO_ID}&tipo=Incident`;
            }
        } else {
            const selectCobTipo = document.getElementById('cob_tipo');
            if (selectCobTipo) {
                selectCobTipo.innerHTML = `
                    <option value="Fine">Fine / Penalty</option>
                    <option value="Damage">Damage / Repair</option>
                    <option value="Rent">Extra Rent</option>
                    <option value="Deposit">Deposit</option>
                    <option value="Other">Other</option>
                `;
            }

            if (blocoAluguel) blocoAluguel.style.display = 'block';
            if (blocoVenda) blocoVenda.style.display = 'none';
            if (blocoCompra) blocoCompra.style.display = 'none';

            const valAluguel = data.valor_aluguel_semanal ? formatoMoeda.format(data.valor_aluguel_semanal) : '-';
            const elAluguel = document.getElementById('info_aluguel');
            if (elAluguel) elAluguel.textContent = `${valAluguel} / week`;

            const diaVencTexto = (data.dia_pagamento_semanal !== undefined && data.dia_pagamento_semanal !== null) 
                ? (diasSemana[data.dia_pagamento_semanal] || `Day ${data.dia_pagamento_semanal}`)
                : '-';
            const elDiaVenc = document.getElementById('info_dia_venc');
            if (elDiaVenc) {
                if (data.dia_pagamento_semanal_original !== undefined && data.dia_pagamento_semanal_original !== null && data.dia_pagamento_semanal_original !== data.dia_pagamento_semanal) {
                    const diaOriginalNome = diasSemana[data.dia_pagamento_semanal_original] || `Day ${data.dia_pagamento_semanal_original}`;
                    elDiaVenc.innerHTML = `${escapeHtml(diaVencTexto)} <span style="font-size:0.75rem; color:var(--text-secondary); font-weight:normal;" title="Originally signed in contract document as ${escapeHtml(diaOriginalNome)}">(Signed: ${escapeHtml(diaOriginalNome)})</span>`;
                } else {
                    elDiaVenc.textContent = diaVencTexto;
                }
            }

            // Toggle Change Due Day button for active rental agreements
            const btnAlterarDia = document.getElementById('btnAlterarDiaVenc');
            if (btnAlterarDia) {
                const isRental = (!data.tipo_contrato || data.tipo_contrato === 'Rent');
                const isActive = (data.status === 'Active' || data.status === 'Ativo');
                if (isRental && isActive) {
                    btnAlterarDia.style.display = 'inline-flex';
                    btnAlterarDia.dataset.currentDay = (data.dia_pagamento_semanal !== undefined && data.dia_pagamento_semanal !== null) ? data.dia_pagamento_semanal : 0;
                } else {
                    btnAlterarDia.style.display = 'none';
                }
            }
        }
        
        const boxCriado = document.getElementById('box_criado_por');
        const infoCriado = document.getElementById('info_criado_por');
        if (boxCriado && infoCriado) {
            if (data.criado_por_nome) {
                boxCriado.style.display = 'block';
                infoCriado.textContent = data.criado_por_nome;
            } else {
                boxCriado.style.display = 'none';
            }
        }
        
        // Button Complete Contract (Only for rentals, not sales or purchases)
        const btnFinalizar = document.getElementById('btnFinalizarContrato');
        if (btnFinalizar) {
            if ((stLower === 'active' || stLower === 'ativo') && !isVenda && !isPurchaseContrato) {
                btnFinalizar.style.display = 'inline-flex';
                btnFinalizar.onclick = () => {
                    document.getElementById('ocorrenciaModalTitle').textContent = 'Complete Contract (Check-in Inspection)';
                    document.getElementById('oc_tipo').value = 'Check-in';
                    if (typeof resetOcPhotos === 'function') resetOcPhotos();
                    abrirModal('ocorrenciaModal');
                };
            } else {
                btnFinalizar.style.display = 'none';
            }
        }

        // Button Cancel Contract
        const btnCancelar = document.getElementById('btnAbrirCancelarContrato');
        if (btnCancelar) {
            const canCancel = ['active', 'ativo', 'deposit_hold', 'quarentena_deposito'].includes(stLower);
            if (canCancel) {
                btnCancelar.style.display = 'inline-flex';
            } else {
                btnCancelar.style.display = 'none';
            }
        }
        
        // Deposit Accounting Details
        const boxDep = document.getElementById('box_deposito_info');
        const depOriginal = data.deposito_pago || 0;
        const depDeducoes = data.deducoes_deposito || 0;
        const isCompleted = stLower === 'completed' || stLower === 'finalizado';
        
        // After contract is completed/refunded, current balance is 0.00
        const depSaldo = isCompleted ? 0 : (data.saldo_deposito !== undefined ? data.saldo_deposito : Math.max(0, depOriginal - depDeducoes));
        const depRestituido = Math.max(0, depOriginal - depDeducoes);

        if (isVenda || isPurchaseContrato) {
            if (boxDep) boxDep.style.display = 'none';
        } else if (boxDep && depOriginal > 0) {
            boxDep.style.display = 'block';
            document.getElementById('dep_original_valor').textContent = formatoMoeda.format(depOriginal);
            
            const dedRow = document.getElementById('dep_deducoes_row');
            if (depDeducoes > 0) {
                dedRow.style.display = 'flex';
                document.getElementById('dep_deducoes_valor').textContent = `-${formatoMoeda.format(depDeducoes)}`;
            } else {
                dedRow.style.display = 'none';
            }

            const restRow = document.getElementById('dep_restituido_row');
            if (restRow) {
                if (isCompleted && depRestituido > 0) {
                    restRow.style.display = 'flex';
                    document.getElementById('dep_restituido_valor').textContent = formatoMoeda.format(depRestituido);
                } else {
                    restRow.style.display = 'none';
                }
            }
            
            const saldoLabel = document.getElementById('dep_saldo_label');
            if (saldoLabel) {
                saldoLabel.textContent = isCompleted ? 'Current Deposit Balance:' : 'Refundable Balance:';
            }

            const saldoValEl = document.getElementById('dep_saldo_valor');
            if (saldoValEl) {
                saldoValEl.textContent = formatoMoeda.format(depSaldo);
                saldoValEl.style.color = isCompleted ? 'var(--text-secondary)' : 'var(--success)';
            }
            
            const badgeStatus = document.getElementById('dep_badge_status');
            if (badgeStatus) {
                if (isCompleted) {
                    badgeStatus.textContent = 'Refunded/Closed';
                    badgeStatus.style.background = 'rgba(34, 197, 94, 0.15)';
                    badgeStatus.style.color = '#4ade80';
                    badgeStatus.style.borderColor = 'rgba(34, 197, 94, 0.3)';
                } else if (stLower === 'deposit_hold' || stLower === 'quarentena_deposito') {
                    badgeStatus.textContent = 'Deposit Hold';
                    badgeStatus.style.background = 'rgba(245, 158, 11, 0.15)';
                    badgeStatus.style.color = '#f59e0b';
                    badgeStatus.style.borderColor = 'rgba(245, 158, 11, 0.3)';
                } else {
                    badgeStatus.textContent = 'Active Held';
                    badgeStatus.style.background = 'rgba(59, 130, 246, 0.15)';
                    badgeStatus.style.color = '#60a5fa';
                    badgeStatus.style.borderColor = 'rgba(59, 130, 246, 0.3)';
                }
            }
        }

        // Release Deposit Hold
        const btnDevolverDeposito = document.getElementById('btnDevolverDeposito');
        if (btnDevolverDeposito) {
            if (stLower === 'deposit_hold' || stLower === 'quarentena_deposito') {
                btnDevolverDeposito.style.display = 'block';
                if (depSaldo > 0) {
                    btnDevolverDeposito.textContent = `Refund Deposit (${formatoMoeda.format(depSaldo)}) & Finalize`;
                    btnDevolverDeposito.style.background = 'var(--success)';
                } else {
                    btnDevolverDeposito.textContent = 'Finalize Contract (Deposit Fully Consumed)';
                    btnDevolverDeposito.style.background = '#475569';
                }
                btnDevolverDeposito.onclick = () => {
                    document.getElementById('modal_dep_orig').textContent = formatoMoeda.format(depOriginal);
                    const modalDedRow = document.getElementById('modal_dep_ded_row');
                    if (depDeducoes > 0) {
                        modalDedRow.style.display = 'flex';
                        document.getElementById('modal_dep_ded').textContent = `-${formatoMoeda.format(depDeducoes)}`;
                    } else {
                        modalDedRow.style.display = 'none';
                    }
                    document.getElementById('modal_dep_net').textContent = formatoMoeda.format(depSaldo);
                    abrirModal('devolverDepositoModal');
                };
            } else {
                btnDevolverDeposito.style.display = 'none';
            }
        }
        
        // 3. Agreement & Signatures Rendering
        const contratoTituloTipo = document.getElementById('contrato_titulo_tipo');
        const labelSigIni = document.getElementById('label_sig_inicial');
        if (isPurchaseContrato) {
            if (contratoTituloTipo) contratoTituloTipo.textContent = '📄 Used Vehicle Purchase Agreement & Signatures';
            if (labelSigIni) labelSigIni.textContent = 'Seller Agreement Signature';
        } else if (isVenda) {
            if (contratoTituloTipo) contratoTituloTipo.textContent = '📄 Vehicle Sale Agreement & Signatures';
            if (labelSigIni) labelSigIni.textContent = '1. Buyer Agreement Signature';
        } else {
            if (contratoTituloTipo) contratoTituloTipo.textContent = '📄 Agreement & Signatures';
            if (labelSigIni) labelSigIni.textContent = '1. Start of Rental Signature';
        }

        const anexos = data.anexos || [];
        const anexosIniciais = anexos.filter(a => a.tipo !== 'return_contract');
        const anexosRetorno = anexos.filter(a => a.tipo === 'return_contract');

        const badgeSigIni = document.getElementById('badge_sig_inicial');
        const boxSigIniContent = document.getElementById('box_sig_inicial_content');
        const btnAssinarIni = document.getElementById('btnAssinarInicialTouch');

        if (data.assinatura_cliente_inicial) {
            if (badgeSigIni) {
                badgeSigIni.textContent = 'Signed';
                badgeSigIni.className = 'badge badge-success';
                badgeSigIni.style.background = '';
                badgeSigIni.style.color = '';
                badgeSigIni.style.border = '';
            }
            if (boxSigIniContent) {
                const dataAssina = data.data_assinatura_inicial_uk || data.data_assinatura_inicial || '';
                const extraDocs = anexosIniciais.length > 0 ? `<div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 3px;">📁 ${anexosIniciais.length} physical scan(s) also on file</div>` : '';
                boxSigIniContent.innerHTML = `
                    <img src="${data.assinatura_cliente_inicial}" alt="Client Signature" style="max-height: 60px; max-width: 180px; object-fit: contain; margin-bottom: 4px;">
                    <span style="font-size: 0.72rem; color: #4ade80; font-weight: 600;">✓ Digitally Signed on ${dataAssina}</span>
                    ${extraDocs}
                `;
            }
            if (btnAssinarIni) btnAssinarIni.style.display = 'none';
        } else if (anexosIniciais.length > 0) {
            // Contrato assinado fisicamente no papel, impresso e anexado
            if (badgeSigIni) {
                badgeSigIni.textContent = 'Signed (Paper Scan)';
                badgeSigIni.className = 'badge';
                badgeSigIni.style.background = 'rgba(6, 182, 212, 0.15)';
                badgeSigIni.style.color = '#22d3ee';
                badgeSigIni.style.border = '1px solid rgba(6, 182, 212, 0.4)';
            }
            if (boxSigIniContent) {
                const dataAssina = data.data_assinatura_inicial_uk || data.data_assinatura_inicial || anexosIniciais[0].data_criacao || '';
                const firstDoc = anexosIniciais[0];
                boxSigIniContent.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 12px; width: 100%; justify-content: center; padding: 4px 0;">
                        <span style="font-size: 2rem;">📄</span>
                        <div style="text-align: left;">
                            <div style="font-size: 0.84rem; color: #4ade80; font-weight: 700;">
                                ✓ Physically Signed Agreement Attached
                            </div>
                            <div style="font-size: 0.74rem; color: var(--text-secondary); margin-top: 2px;">
                                ${anexosIniciais.length} scanned page(s) / PDF document on file ${dataAssina ? `• Attached on ${dataAssina}` : ''}
                            </div>
                            <div style="margin-top: 5px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                                <a href="${firstDoc.url_arquivo}" target="_blank" style="color: #60a5fa; text-decoration: none; font-size: 0.76rem; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">
                                    View Attached Document ↗
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            }
            if (btnAssinarIni) {
                btnAssinarIni.style.display = 'inline-flex';
                btnAssinarIni.textContent = '✍️ Sign on Screen Also';
                btnAssinarIni.title = 'Add digital touch signature in addition to attached paper scan';
            }
        } else {
            if (badgeSigIni) {
                badgeSigIni.textContent = 'Pending Signature';
                badgeSigIni.className = 'badge badge-warning';
                badgeSigIni.style.background = '';
                badgeSigIni.style.color = '';
                badgeSigIni.style.border = '';
            }
            if (boxSigIniContent) {
                const docName = isPurchaseContrato ? 'used vehicle purchase agreement' : (isVenda ? 'vehicle purchase agreement' : 'start of rental');
                boxSigIniContent.innerHTML = `
                    <div style="text-align: center;">
                        <span style="color: var(--text-secondary); font-size: 0.85rem; display: block; margin-bottom: 4px;">
                            Client signature pending for ${docName}.
                        </span>
                        <span style="font-size: 0.74rem; color: var(--text-secondary);">
                            Sign on screen below OR print, physically sign and click <strong>"Attach Scans / Photos"</strong>.
                        </span>
                    </div>
                `;
            }
            if (btnAssinarIni) {
                btnAssinarIni.style.display = 'inline-flex';
                btnAssinarIni.textContent = '✍️ Sign on Screen Now';
            }
        }

        const cardSigDev = document.getElementById('card_sig_devolucao');
        if (cardSigDev) {
            cardSigDev.style.display = (isVenda || isPurchaseContrato) ? 'none' : 'block';
        }

        const badgeSigDev = document.getElementById('badge_sig_devolucao');
        const boxSigDevContent = document.getElementById('box_sig_devolucao_content');
        const btnAssinarDev = document.getElementById('btnAssinarDevolucaoTouch');

        if (data.assinatura_cliente_devolucao) {
            if (badgeSigDev) {
                badgeSigDev.textContent = 'Signed';
                badgeSigDev.className = 'badge badge-success';
                badgeSigDev.style.background = '';
                badgeSigDev.style.color = '';
                badgeSigDev.style.border = '';
            }
            if (boxSigDevContent) {
                const dataAssinaDev = data.data_assinatura_devolucao_uk || data.data_assinatura_devolucao || '';
                const extraDocsDev = anexosRetorno.length > 0 ? `<div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 3px;">📁 ${anexosRetorno.length} return scan(s) also on file</div>` : '';
                boxSigDevContent.innerHTML = `
                    <img src="${data.assinatura_cliente_devolucao}" alt="Return Signature" style="max-height: 60px; max-width: 180px; object-fit: contain; margin-bottom: 4px;">
                    <span style="font-size: 0.72rem; color: #4ade80; font-weight: 600;">✓ Return Signed on ${dataAssinaDev}</span>
                    ${extraDocsDev}
                `;
            }
            if (btnAssinarDev) btnAssinarDev.style.display = 'none';
        } else if (anexosRetorno.length > 0) {
            if (badgeSigDev) {
                badgeSigDev.textContent = 'Signed (Paper Scan)';
                badgeSigDev.className = 'badge';
                badgeSigDev.style.background = 'rgba(6, 182, 212, 0.15)';
                badgeSigDev.style.color = '#22d3ee';
                badgeSigDev.style.border = '1px solid rgba(6, 182, 212, 0.4)';
            }
            if (boxSigDevContent) {
                const dataAssinaDev = data.data_assinatura_devolucao_uk || data.data_assinatura_devolucao || anexosRetorno[0].data_criacao || '';
                const firstDevDoc = anexosRetorno[0];
                boxSigDevContent.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 12px; width: 100%; justify-content: center; padding: 4px 0;">
                        <span style="font-size: 2rem;">📄</span>
                        <div style="text-align: left;">
                            <div style="font-size: 0.84rem; color: #4ade80; font-weight: 700;">
                                ✓ Physically Signed Return Term Attached
                            </div>
                            <div style="font-size: 0.74rem; color: var(--text-secondary); margin-top: 2px;">
                                ${anexosRetorno.length} return scan page(s) / PDF on file ${dataAssinaDev ? `• Attached on ${dataAssinaDev}` : ''}
                            </div>
                            <div style="margin-top: 5px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                                <a href="${firstDevDoc.url_arquivo}" target="_blank" style="color: #60a5fa; text-decoration: none; font-size: 0.76rem; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">
                                    View Return Document ↗
                                </a>
                            </div>
                        </div>
                    </div>
                `;
            }
            if (btnAssinarDev) {
                btnAssinarDev.style.display = 'inline-flex';
                btnAssinarDev.textContent = '✍️ Sign Return on Screen Also';
            }
        } else {
            if (stLower === 'deposit_hold' || stLower === 'quarentena_deposito' || isCompleted) {
                if (badgeSigDev) {
                    badgeSigDev.textContent = 'Pending Return Signature';
                    badgeSigDev.className = 'badge badge-warning';
                    badgeSigDev.style.background = '';
                    badgeSigDev.style.color = '';
                    badgeSigDev.style.border = '';
                }
                if (boxSigDevContent) {
                    boxSigDevContent.innerHTML = `
                        <span style="color: #f59e0b; font-size: 0.82rem;">Vehicle returned. Client return signature is pending.</span>
                    `;
                }
                if (btnAssinarDev) btnAssinarDev.style.display = 'inline-flex';
            } else {
                if (badgeSigDev) {
                    badgeSigDev.textContent = 'Waiting Vehicle Return';
                    badgeSigDev.className = 'badge';
                    badgeSigDev.style.background = 'rgba(255,255,255,0.05)';
                    badgeSigDev.style.color = 'var(--text-secondary)';
                    badgeSigDev.style.border = '';
                }
                if (boxSigDevContent) {
                    boxSigDevContent.innerHTML = `
                        <span style="color: var(--text-secondary); font-size: 0.8rem;">Will be collected upon vehicle return / check-in.</span>
                    `;
                }
                if (btnAssinarDev) btnAssinarDev.style.display = 'none';
            }
        }

        // Render Anexos de Contrato
        const anexosCount = document.getElementById('anexos_count');
        const anexosList = document.getElementById('anexos_list');

        if (anexosCount) anexosCount.textContent = anexos.length;
        if (anexosList) {
            if (anexos.length === 0) {
                anexosList.innerHTML = `<p style="color: var(--text-secondary); font-size: 0.82rem; margin: 0;">No scanned contract pages attached yet. Click "Attach Scans / Photos" to upload.</p>`;
            } else {
                anexosList.innerHTML = '';
                anexos.forEach((a, idx) => {
                    const item = document.createElement('div');
                    item.style.cssText = 'background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: 8px; padding: 0.6rem 0.85rem; display: flex; align-items: center; justify-content: space-between; gap: 10px; font-size: 0.82rem; min-width: 220px;';
                    
                    const isPdf = (a.url_arquivo || '').toLowerCase().endsWith('.pdf');
                    const icon = isPdf ? '📄' : '🖼️';
                    const tipoLabel = a.tipo === 'return_contract' ? 'Return Term' : 'Contract Page';

                    item.innerHTML = `
                        <div style="display: flex; align-items: center; gap: 8px; overflow: hidden;">
                            <span style="font-size: 1.2rem;">${icon}</span>
                            <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                <a href="${a.url_arquivo}" target="_blank" style="color: var(--text-primary); text-decoration: none; font-weight: 600;">
                                    ${tipoLabel} #${idx + 1}
                                </a>
                                <div style="font-size: 0.7rem; color: var(--text-secondary);">${a.data_criacao || ''}</div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <a href="${a.url_arquivo}" target="_blank" class="btn-action" style="padding: 4px 8px; font-size: 0.75rem; text-decoration: none; color: #60a5fa;">
                                View ↗
                            </a>
                            <button type="button" onclick="deletarAnexoContrato(${a.id})" style="background: transparent; border: none; color: #f87171; cursor: pointer; font-size: 1.1rem; padding: 0 4px;" title="Delete attachment">&times;</button>
                        </div>
                    `;
                    anexosList.appendChild(item);
                });
            }
        }

        const infoComp = document.getElementById('info_comprovante');
        if (infoComp) {
            if (data.url_comprovante_deposito) {
                infoComp.innerHTML = `
                    <a href="${data.url_comprovante_deposito}" target="_blank" style="color:var(--success); text-decoration:none; font-size:0.85rem; display:inline-flex; align-items:center; gap:4px; margin-top:4px;">
                        📄 Deposit Refund Proof &rarr;
                    </a>
                `;
            } else {
                infoComp.innerHTML = '';
            }
        }
        
        // 4. Financial Statement State & Logic
        const extratoState = {
            transacoes: data.transacoes || [],
            sortField: 'data_vencimento',
            sortOrder: 'desc',
            currentPage: 1,
            pageSize: 10,
            filterStatus: 'all',
            searchTerm: ''
        };

        function getFilteredExtrato() {
            let filtered = (extratoState.transacoes || []).slice();
            const statusF = extratoState.filterStatus || 'all';
            const term = (extratoState.searchTerm || '').trim().toLowerCase();
            const nowCheck = new Date();
            nowCheck.setHours(0, 0, 0, 0);

            if (statusF !== 'all') {
                filtered = filtered.filter(t => {
                    const s = (t.status || '').toLowerCase();
                    const isPaid = s === 'paid' || s === 'pago';
                    const isPending = s === 'pending' || s === 'pendente';
                    const isCancelled = s === 'cancelled' || s === 'cancelado';
                    const dV = t.data_vencimento ? new Date(t.data_vencimento) : null;
                    const dVZero = dV ? new Date(dV.getFullYear(), dV.getMonth(), dV.getDate()) : null;
                    const isOverdue = isPending && dVZero && dVZero < nowCheck;

                    if (statusF === 'pending') return isPending;
                    if (statusF === 'overdue') return isOverdue;
                    if (statusF === 'paid') return isPaid;
                    if (statusF === 'cancelled') return isCancelled;
                    return true;
                });
            }

            if (term) {
                filtered = filtered.filter(t => {
                    const idStr = String(t.id || '');
                    const tipoStr = String(t.tipo || '').toLowerCase();
                    const descStr = String(t.descricao || '').toLowerCase();
                    const notaStr = String(t.nota || '').toLowerCase();
                    const notaPagStr = String(t.nota_pagamento || '').toLowerCase();
                    const formaStr = String(t.forma_pagamento || '').toLowerCase();
                    const statusStr = String(t.status || '').toLowerCase();
                    const staffStr = String(t.registrado_por_nome || '').toLowerCase();
                    const valorStr = String(t.valor || '');
                    const origStr = String(t.id_transacao_origem || '');

                    return idStr.includes(term) ||
                           tipoStr.includes(term) ||
                           descStr.includes(term) ||
                           notaStr.includes(term) ||
                           notaPagStr.includes(term) ||
                           formaStr.includes(term) ||
                           statusStr.includes(term) ||
                           staffStr.includes(term) ||
                           valorStr.includes(term) ||
                           (origStr && origStr.includes(term));
                });
            }

            return filtered;
        }

        // Compute overall financial totals across all transactions
        let totalPendente = 0;
        let totalPago = 0;
        const hojeZero = new Date();
        hojeZero.setHours(0, 0, 0, 0);

        extratoState.transacoes.forEach(t => {
            const tStatusLower = (t.status || '').toLowerCase();
            const tipoLower = (t.tipo || '').toLowerCase();
            const isPaid = tStatusLower === 'paid' || tStatusLower === 'pago';
            const isPending = tStatusLower === 'pending' || tStatusLower === 'pendente';
            const tValor = parseFloat(t.valor) || 0;
            if (isPaid && tipoLower !== 'deposit_refund' && tipoLower !== 'devolucao_deposito') {
                totalPago += tValor;
            } else if (isPending) {
                totalPendente += tValor;
            }
        });

        const cardFinancialStatement = document.getElementById('card_financial_statement');
        if (cardFinancialStatement) {
            cardFinancialStatement.style.display = isPurchaseContrato ? 'none' : 'flex';
        }

        const navPillFin = document.getElementById('nav_pill_financial');
        if (navPillFin) {
            navPillFin.style.display = isPurchaseContrato ? 'none' : 'inline-flex';
        }

        function updateFinancialSummaryPanel() {
            const panel = document.getElementById('fin_summary_panel');
            if (!panel) return;
            if (isPurchaseContrato) {
                panel.style.display = 'none';
                return;
            }

            panel.style.display = 'block';
            const elTotal = document.getElementById('fin_stat_total');
            const elPaid = document.getElementById('fin_stat_paid');
            const elBalance = document.getElementById('fin_stat_balance');
            const lblTotal = document.getElementById('fin_stat_label_total');
            const lblBalance = document.getElementById('fin_stat_label_balance');
            const extraCol = document.getElementById('fin_stat_extra_col');
            const extraVal = document.getElementById('fin_stat_extra_val');
            const extraLbl = document.getElementById('fin_stat_extra_label');

            const progContainer = document.getElementById('fin_progression_container');
            const progPercent = document.getElementById('fin_progress_percent');
            const progBar = document.getElementById('fin_progress_bar');
            const progLabel = document.getElementById('fin_progress_label');
            const progDetails = document.getElementById('fin_progress_details');

            // Calculate current paid and pending from extratoState.transacoes
            let calcPago = 0;
            let calcPendente = 0;
            (extratoState.transacoes || []).forEach(t => {
                const s = (t.status || '').toLowerCase();
                const tip = (t.tipo || '').toLowerCase();
                const val = parseFloat(t.valor) || 0;
                if ((s === 'paid' || s === 'pago') && tip !== 'deposit_refund' && tip !== 'devolucao_deposito') {
                    calcPago += val;
                } else if (s === 'pending' || s === 'pendente' || s === 'overdue' || s === 'atrasado') {
                    calcPendente += val;
                }
            });

            let contractTotal = 0;
            let currentBalance = calcPendente;
            let currentPaid = calcPago;

            if (isVendaContrato) {
                contractTotal = parseFloat(data.valor_total_venda) || (calcPago + calcPendente);
                currentBalance = calcPendente;
                if (lblTotal) lblTotal.textContent = 'Vehicle Sale Total';
                if (lblBalance) lblBalance.textContent = 'Outstanding Balance';
            } else {
                contractTotal = (data.total_faturado !== undefined && data.total_faturado !== null) ? data.total_faturado : (calcPago + calcPendente);
                currentBalance = calcPendente;
                if (lblTotal) lblTotal.textContent = 'Total Invoiced';
                if (lblBalance) lblBalance.textContent = 'Balance Due';
            }

            if (elTotal) elTotal.textContent = formatoMoeda.format(contractTotal);
            if (elPaid) elPaid.textContent = formatoMoeda.format(currentPaid);
            if (elBalance) {
                elBalance.textContent = formatoMoeda.format(currentBalance);
                elBalance.style.color = currentBalance > 0 ? 'var(--text-primary)' : 'var(--text-secondary)';
            }

            // Security deposit indicator for rentals
            if (extraCol && extraVal) {
                if (!isVendaContrato && depOriginal > 0) {
                    extraCol.style.display = 'block';
                    if (extraLbl) extraLbl.textContent = isCompleted ? 'Deposit (Closed)' : 'Deposit Held';
                    extraVal.textContent = formatoMoeda.format(depSaldo);
                    extraVal.style.color = isCompleted ? 'var(--text-secondary)' : '#60a5fa';
                } else {
                    extraCol.style.display = 'none';
                }
            }

            // Installment & Settlement Progress
            if (progContainer && progPercent && progBar) {
                if (isVendaContrato && data.tipo_contrato === 'Sale_Installment') {
                    progContainer.style.display = 'block';
                    const allParcelas = (extratoState.transacoes || []).filter(t => {
                        const tp = (t.tipo || '').toLowerCase();
                        return tp === 'sale_installment' || tp === 'venda_parcela';
                    });
                    const paidParcelas = allParcelas.filter(t => {
                        const st = (t.status || '').toLowerCase();
                        return st === 'paid' || st === 'pago';
                    });

                    const totalCount = allParcelas.length;
                    const paidCount = paidParcelas.length;
                    const pct = contractTotal > 0 ? Math.min(100, Math.round((currentPaid / contractTotal) * 100)) : (totalCount > 0 ? Math.round((paidCount / totalCount) * 100) : 0);

                    if (progLabel) progLabel.textContent = `Instalment Settlement (${paidCount} of ${totalCount} paid)`;
                    progPercent.textContent = `${pct}%`;
                    progBar.style.width = `${pct}%`;

                    if (progDetails) {
                        const isSettled = pct >= 100 || currentBalance <= 0;
                        if (isSettled) {
                            progDetails.innerHTML = `
                                <span style="color:#4ade80; font-weight:700;">🎉 Contract fully paid and settled!</span>
                                <span class="badge badge-success" style="font-size:0.72rem; padding: 2px 8px;">SETTLED</span>
                            `;
                        } else {
                            const pendingSorted = allParcelas.filter(t => {
                                const st = (t.status || '').toLowerCase();
                                return st === 'pending' || st === 'pendente' || st === 'overdue' || st === 'atrasado';
                            }).sort((a,b) => (new Date(a.data_vencimento || 0) - new Date(b.data_vencimento || 0)));

                            let nextText = '';
                            if (pendingSorted.length > 0) {
                                const nextDue = pendingSorted[0].data_vencimento ? new Date(pendingSorted[0].data_vencimento).toLocaleDateString('en-GB') : '-';
                                nextText = `Next instalment: <strong>${formatoMoeda.format(pendingSorted[0].valor)}</strong> due on <strong>${nextDue}</strong>`;
                            }
                            progDetails.innerHTML = `
                                <span>${nextText}</span>
                                <span>${totalCount - paidCount} instalment(s) remaining</span>
                            `;
                        }
                    }
                } else if (isVendaContrato && data.tipo_contrato === 'Sale_Full') {
                    progContainer.style.display = 'block';
                    const isSettled = currentBalance <= 0;
                    const pct = isSettled ? 100 : Math.min(100, Math.round((currentPaid / (contractTotal || 1)) * 100));
                    if (progLabel) progLabel.textContent = 'Sale Payment Status';
                    progPercent.textContent = `${pct}%`;
                    progBar.style.width = `${pct}%`;
                    if (progDetails) {
                        progDetails.innerHTML = isSettled 
                            ? `<span style="color:#4ade80; font-weight:700;">✓ Full vehicle sale payment received and cleared.</span><span class="badge badge-success" style="font-size:0.72rem; padding: 2px 8px;">CLEARED</span>`
                            : `<span>Pending full payment clearance</span>`;
                    }
                } else {
                    progContainer.style.display = 'none';
                }
            }
        }

        // Setup smooth scroll for quick navigation pills
        document.querySelectorAll('.nav-pill-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetId = btn.getAttribute('href');
                if (targetId && targetId.startsWith('#')) {
                    const targetEl = document.querySelector(targetId);
                    if (targetEl && targetEl.style.display !== 'none') {
                        e.preventDefault();
                        targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
            });
        });

        updateFinancialSummaryPanel();

        let splitPaymentMgrContract = null;

        function renderExtrato() {
            updateFinancialSummaryPanel();
            const tbody = document.querySelector('#extratoTable tbody');
            if (!tbody) return;
            tbody.innerHTML = '';

            const paginationContainer = document.getElementById('extratoPaginationContainer');
            const paginationInfo = document.getElementById('extratoPaginationInfo');
            const btnPrev = document.getElementById('btnExtratoPrev');
            const btnNext = document.getElementById('btnExtratoNext');
            const tfoot = document.getElementById('extratoTableFooter');
            const elFooterCount = document.getElementById('extratoFooterCountText');
            const elFooterAmount = document.getElementById('extratoFooterTotalAmount');
            const elFooterSummary = document.getElementById('extratoFooterSummaryText');
            const btnClearFilter = document.getElementById('btnExtratoClearFilter');

            const statusF = extratoState.filterStatus || 'all';
            const term = (extratoState.searchTerm || '').trim().toLowerCase();
            const isFilterActive = (statusF !== 'all' || term.length > 0);

            if (btnClearFilter) {
                btnClearFilter.style.display = isFilterActive ? 'inline-block' : 'none';
            }

            if (!extratoState.transacoes || extratoState.transacoes.length === 0) {
                if (isPurchaseContrato) {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:2rem; color:var(--text-secondary);"><span style="color:#22d3ee; font-weight:700;">🤝 Used Vehicle Purchase:</span> Vehicle acquisition payment was settled upon agreement completion as agreed. No ongoing rental or sales charges.</td></tr>';
                } else {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:2rem; color:var(--text-secondary);">No charges recorded for this contract.</td></tr>';
                }
                if (paginationContainer) paginationContainer.style.display = 'none';
                if (tfoot) tfoot.style.display = 'none';
                return;
            }

            // 1. Filter transactions
            const filtered = getFilteredExtrato();

            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:2rem; color:var(--text-secondary);">No charges match the selected filter.</td></tr>';
                if (paginationContainer) paginationContainer.style.display = 'none';
                if (tfoot) tfoot.style.display = 'none';
                return;
            }

            if (paginationContainer) paginationContainer.style.display = 'flex';

            // 2. Sort transactions
            const sorted = sortExtrato(filtered, extratoState.sortField, extratoState.sortOrder);

            // Update Header sort indicators
            const headers = document.querySelectorAll('#extratoTable thead th[data-sort-field]');
            headers.forEach(th => {
                const f = th.getAttribute('data-sort-field');
                const ind = th.querySelector('.sort-indicator');
                if (f === extratoState.sortField) {
                    th.classList.remove('sorted-asc', 'sorted-desc');
                    th.classList.add(extratoState.sortOrder === 'desc' ? 'sorted-desc' : 'sorted-asc');
                    if (ind) ind.textContent = extratoState.sortOrder === 'desc' ? '▼' : '▲';
                } else {
                    th.classList.remove('sorted-asc', 'sorted-desc');
                    if (ind) ind.textContent = '⇅';
                }
            });

            // 3. Paginate transactions
            const totalItems = sorted.length;
            const pageSizeNum = extratoState.pageSize === 'all' ? totalItems : parseInt(extratoState.pageSize, 10);
            const totalPages = Math.max(1, Math.ceil(totalItems / pageSizeNum));

            if (extratoState.currentPage > totalPages) extratoState.currentPage = totalPages;
            if (extratoState.currentPage < 1) extratoState.currentPage = 1;

            const startIdx = (extratoState.currentPage - 1) * pageSizeNum;
            const endIdx = Math.min(startIdx + pageSizeNum, totalItems);
            const pageItems = sorted.slice(startIdx, endIdx);

            if (paginationInfo) {
                const startLabel = totalItems > 0 ? (startIdx + 1) : 0;
                paginationInfo.textContent = `Showing ${startLabel} to ${endIdx} of ${totalItems} charges (Page ${extratoState.currentPage} of ${totalPages})`;
            }

            if (btnPrev) btnPrev.disabled = (extratoState.currentPage <= 1);
            if (btnNext) btnNext.disabled = (extratoState.currentPage >= totalPages);

            // 4. Update Footer Summary (tfoot)
            if (tfoot) {
                tfoot.style.display = '';
                let somaFiltrada = 0;
                let paidCount = 0;
                let pendingCount = 0;
                filtered.forEach(item => {
                    somaFiltrada += (parseFloat(item.valor) || 0);
                    const s = (item.status || '').toLowerCase();
                    if (s === 'paid' || s === 'pago') paidCount++;
                    else if (s === 'pending' || s === 'pendente') pendingCount++;
                });
                if (elFooterAmount) elFooterAmount.textContent = formatoMoeda.format(somaFiltrada);
                if (elFooterCount) {
                    elFooterCount.textContent = `Showing ${filtered.length} charges (${paidCount} paid, ${pendingCount} pending)`;
                }
                if (elFooterSummary) {
                    elFooterSummary.textContent = isFilterActive ? 'Filtered View Sum' : 'Current View Sum';
                }
            }

            // 5. Render rows for current page
            pageItems.forEach(t => {
                const tr = document.createElement('tr');

                const dataVencObj = t.data_vencimento ? new Date(t.data_vencimento) : null;
                const vencZero = dataVencObj ? new Date(dataVencObj.getFullYear(), dataVencObj.getMonth(), dataVencObj.getDate()) : null;
                const dataVenc = dataVencObj ? dataVencObj.toLocaleDateString('en-GB') : '-';

                const tStatusLower = (t.status || '').toLowerCase();
                const tipoLower = (t.tipo || '').toLowerCase();
                const isPaid = tStatusLower === 'paid' || tStatusLower === 'pago';
                const isPending = tStatusLower === 'pending' || tStatusLower === 'pendente';
                const isVencido = isPending && vencZero && vencZero < hojeZero;

                const dataPag = t.data_pagamento ? new Date(t.data_pagamento).toLocaleDateString('en-GB') : '-';

                let statusBadge = '';
                if (isPaid) statusBadge = '<span class="badge badge-success">PAID</span>';
                else if (isVencido) statusBadge = '<span class="badge badge-danger">OVERDUE</span>';
                else statusBadge = '<span class="badge badge-warning">PENDING</span>';

                // Type Badges
                let tipoBadge = '';
                if (tipoLower === 'rent' || tipoLower === 'aluguel') tipoBadge = '<span class="badge badge-info">Rent</span>';
                else if (tipoLower === 'deposit' || tipoLower === 'deposito') tipoBadge = '<span class="badge" style="background:rgba(168, 85, 247, 0.2); color:#c084fc;">Deposit</span>';
                else if (tipoLower === 'sale_full') tipoBadge = '<span class="badge" style="background:rgba(16, 185, 129, 0.2); color:#34d399; border:1px solid rgba(16, 185, 129, 0.4);">Sale: Full Payment</span>';
                else if (tipoLower === 'sale_deposit') tipoBadge = '<span class="badge" style="background:rgba(217, 119, 6, 0.2); color:#fbbf24; border:1px solid rgba(217, 119, 6, 0.4);">Sale: Down Payment</span>';
                else if (tipoLower === 'sale_installment') tipoBadge = '<span class="badge" style="background:rgba(59, 130, 246, 0.2); color:#60a5fa; border:1px solid rgba(59, 130, 246, 0.4);">Sale: Installment</span>';
                else if (tipoLower === 'fine' || tipoLower === 'multa') tipoBadge = '<span class="badge badge-danger">Fine</span>';
                else if (tipoLower === 'damage' || tipoLower === 'dano') tipoBadge = '<span class="badge badge-warning">Damage</span>';
                else if (tipoLower === 'deposit_refund' || tipoLower === 'devolucao_deposito') tipoBadge = '<span class="badge badge-success">Deposit Refund</span>';
                else tipoBadge = `<span class="badge">${escapeHtml(t.tipo)}</span>`;

                // Partial Split Balance Badge Indicator
                const balanceBadgeHtml = t.id_transacao_origem ? `<span style="display:inline-block; font-size:0.68rem; color:#f59e0b; font-weight:700; background:rgba(245, 158, 11, 0.15); border:1px solid rgba(245, 158, 11, 0.35); border-radius:3px; padding:0 4px;" title="Remaining balance from partial payment #${t.id_transacao_origem}">⚡ Bal #${t.id_transacao_origem}</span>` : '';

                // Reference & Attachments & Linked Inspection
                let refNotaHtml = '';
                if (t.nota) {
                    refNotaHtml = `<span style="display:block; font-size:0.75rem; color:#cbd5e1; margin-top:3px; word-break:break-word; max-width:260px;" title="${escapeHtml(t.nota)}">📝 <strong style="color:#e2e8f0;">${escapeHtml(t.nota)}</strong></span>`;
                }

                let anexoBadgeHtml = '';
                if (t.url_anexos) {
                    const urls = t.url_anexos.split(',').map(u => u.trim()).filter(Boolean);
                    if (urls.length > 0) {
                        anexoBadgeHtml = `<button type="button" class="btn-ver-anexo" data-urls="${escapeHtml(JSON.stringify(urls))}" data-ref="${escapeHtml(t.nota || t.tipo)}" style="background:rgba(59, 130, 246, 0.15); color:#60a5fa; border:1px solid rgba(59, 130, 246, 0.35); font-size:0.72rem; padding:2px 7px; border-radius:6px; margin-top:3px; cursor:pointer; display:inline-flex; align-items:center; gap:4px; font-weight:600;" title="Click to view attached documents/photos">📎 Proof (${urls.length})</button>`;
                    }
                }

                let vistoriaLinkHtml = '';
                if (t.id_vistoria) {
                    vistoriaLinkHtml = `<a href="#inspection-item-${t.id_vistoria}" onclick="highlightInspection(${t.id_vistoria})" class="badge" style="background:rgba(239, 68, 68, 0.15); color:#fca5a5; border:1px solid rgba(239, 68, 68, 0.35); font-size:0.7rem; padding:2px 6px; border-radius:6px; margin-top:3px; text-decoration:none; display:inline-flex; align-items:center; gap:3px; cursor:pointer;" title="Go to Inspection #${t.id_vistoria}">🔍 Inspection #${t.id_vistoria}</a>`;
                }

                // WhatsApp reminder button & aesthetic chip
                const formatLembrete = (typeof window.formatarLembreteEstetico === 'function') ? window.formatarLembreteEstetico : ((iso, st) => '');
                const reminderChipHtml = `<span id="reminder-container-${t.id}">${formatLembrete(t.ultimo_lembrete, t.ultimo_lembrete_por)}</span>`;

                let acoesHtml = '';
                if (isPending) {
                    let waBtnHtml = '';
                    const telVal = data.telefone || data.cliente_telefone;
                    if (telVal) {
                        const waTel = (typeof formatWhatsAppNumber === 'function')
                            ? formatWhatsAppNumber(telVal)
                            : (() => {
                                let w = telVal.replace(/\D/g, '');
                                if (w.startsWith('0')) w = '44' + w.substring(1);
                                return w;
                            })();
                        const bikeRef = (data.placa && data.placa !== '-') ? `for vehicle ${data.placa}` : 'with FF Motors';
                        const descFinal = t.descricao || (typeof formatarDescricaoTransacao === 'function' ? formatarDescricaoTransacao(t.tipo) : t.tipo);
                        const waMsg = encodeURIComponent(`Hi ${data.cliente || data.cliente_nome || 'there'}, this is FF Motors Birmingham. Just a friendly reminder regarding your pending ${descFinal} payment of ${formatoMoeda.format(t.valor)} ${bikeRef}. If you have already made this payment, please disregard this note. Thank you!`);
                        const waLink = waTel ? `https://wa.me/${waTel}?text=${waMsg}` : '#';
                        waBtnHtml = `<a href="${waLink}" target="_blank" rel="noopener noreferrer" class="btn-action btn-wa-reminder" data-id="${t.id}" style="background:rgba(37,211,102,0.15); border:1px solid rgba(37,211,102,0.35); color:#25d366; padding:4px 8px; font-size:0.8rem; text-decoration:none; display:inline-flex; align-items:center; gap:3px; border-radius:6px; font-weight:600;" title="Send WhatsApp payment reminder">💬 Remind</a>`;
                    }

                    acoesHtml = `
                        <div style="display:flex; flex-direction:column; align-items:flex-end; gap:3px;">
                            <div style="display:flex; gap:6px; justify-content:flex-end; align-items:center; flex-wrap:nowrap;">
                                ${waBtnHtml}
                                <button class="btn-action btn-pagar" data-id="${t.id}" data-tipo="${t.tipo}" data-valor="${t.valor}" style="background:var(--success); padding:4px 10px; font-size:0.8rem;">
                                    Pay
                                </button>
                                <button class="btn-action btn-remover" data-id="${t.id}" style="background:rgba(239, 68, 68, 0.15); color:#f87171; border:1px solid rgba(239, 68, 68, 0.3); padding:4px 8px; font-size:0.8rem;">
                                    Delete
                                </button>
                            </div>
                            ${reminderChipHtml}
                        </div>
                    `;
                } else if (isPaid) {
                    const descFinal = t.descricao || (typeof formatarDescricaoTransacao === 'function' ? formatarDescricaoTransacao(t.tipo) : t.tipo);
                    acoesHtml = `
                        <div style="display:flex; gap:6px; justify-content:flex-end; align-items:center;">
                            <button class="btn-action btn-recibo" data-id="${t.id}" data-tipo="${t.tipo}" data-descricao="${descFinal}" data-valor="${parseFloat(t.valor).toFixed(2)}" data-forma="${t.forma_pagamento || '-'}" data-data="${t.data_pagamento || '-'}" data-nota="${escapeHtml(t.nota_pagamento || '')}" data-ref="${escapeHtml(t.nota || '')}" style="background:rgba(255,255,255,0.06); border:1px solid var(--border-color); color:var(--text-primary); padding:4px 10px; font-size:0.8rem;" title="View Receipt">
                                🧾 Receipt
                            </button>
                            <button class="btn-action btn-reverter-pagamento" data-id="${t.id}" data-tipo="${t.tipo}" data-valor="${parseFloat(t.valor).toFixed(2)}" style="background:rgba(239, 68, 68, 0.12); border:1px solid rgba(239, 68, 68, 0.3); color:#f87171; padding:4px 9px; font-size:0.8rem; border-radius:6px; cursor:pointer;" title="Cancel payment and return to Pending">
                                ↩ Cancel / Revert
                            </button>
                        </div>
                    `;
                }

                let celulaPagamento = `<span style="color:var(--text-secondary); opacity:0.5;">-</span>`;
                if (isPaid) {
                    const isDepositDeduction = t.forma_pagamento === 'Deposit';
                    const isExchange = t.forma_pagamento && t.forma_pagamento.includes('Exchange');
                    const formaLabel = isDepositDeduction ? 'Deposit (Deduction)' : (t.forma_pagamento || '');
                    let colorStyle = 'color:var(--text-secondary);';
                    if (isDepositDeduction) colorStyle = 'color:#60a5fa; font-weight:600;';
                    else if (isExchange) colorStyle = 'color:#34d399; font-weight:600;';
                    const staffHtml = t.registrado_por_nome ? `<span style="display:block; font-size:0.7rem; color:#c084fc; margin-top:2px;">👤 ${escapeHtml(t.registrado_por_nome)}</span>` : '';
                    const notaHtml = t.nota_pagamento ? `<span style="display:block; font-size:0.73rem; color:#cbd5e1; background:rgba(255,255,255,0.06); border-left:2px solid var(--accent, #ff6b00); padding:2px 6px; border-radius:3px; margin-top:3px; word-break:break-word;" title="Payment note">📝 ${escapeHtml(t.nota_pagamento)}</span>` : '';
                    celulaPagamento = `<span>${dataPag} <small style="${colorStyle} display:block; font-size:0.75rem;">${escapeHtml(formaLabel)}</small>${staffHtml}${notaHtml}</span>`;
                }

                let celulaVencimento = `<span>${dataVenc}</span>`;
                if (isVencido) {
                    const diffTime = Math.max(0, hojeZero.getTime() - vencZero.getTime());
                    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
                    let lateText = `${diffDays}d late`;
                    if (diffDays === 0 || diffDays === 1) {
                        lateText = '1d late';
                    } else if (diffDays >= 14) {
                        const weeks = Math.floor(diffDays / 7);
                        lateText = `${weeks}w (${diffDays}d)`;
                    }
                    celulaVencimento = `
                        <div style="line-height: 1.2;">
                            <span style="color:#f87171; font-weight:600; font-size:0.85rem;" title="Charge overdue!">${dataVenc}</span>
                            <span style="font-size: 0.68rem; color: #fca5a5; font-weight: 700; background: rgba(239, 68, 68, 0.15); padding: 1px 5px; border-radius: 4px; border: 1px solid rgba(239, 68, 68, 0.3); display: inline-block; white-space: nowrap; margin-top: 2px;">${lateText}</span>
                        </div>
                    `;
                }

                tr.innerHTML = `
                    <td style="font-weight:700; font-size:0.82rem; color:var(--text-secondary); white-space:nowrap;">
                        #${t.id}
                    </td>
                    <td>
                        <div style="line-height:1.25;">
                            <div style="display:flex; align-items:center; gap:4px; flex-wrap:wrap;">
                                ${tipoBadge}
                                ${balanceBadgeHtml}
                            </div>
                            ${refNotaHtml}
                            <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:3px;">
                                ${anexoBadgeHtml}
                                ${vistoriaLinkHtml}
                            </div>
                        </div>
                    </td>
                    <td style="font-weight:700; font-size:0.95rem; color:var(--text-primary); white-space:nowrap;">${formatoMoeda.format(t.valor)}</td>
                    <td>${celulaVencimento}</td>
                    <td>${celulaPagamento}</td>
                    <td>${statusBadge}</td>
                    <td style="text-align: right; white-space: nowrap;">${acoesHtml}</td>
                `;
                tbody.appendChild(tr);
            });

            // Bind WhatsApp Reminder Buttons for current page
            tbody.querySelectorAll('.btn-wa-reminder').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const id = btn.getAttribute('data-id');
                    if (!id) return;
                    try {
                        const res = await fetch(`/api/financeiro/${id}/lembrete`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' }
                        });
                        if (res.ok) {
                            const resJson = await res.json();
                            const container = document.getElementById(`reminder-container-${id}`);
                            const formatLembrete = (typeof window.formatarLembreteEstetico === 'function') ? window.formatarLembreteEstetico : ((iso, st) => '');
                            if (container) {
                                container.innerHTML = formatLembrete(resJson.ultimo_lembrete || new Date().toISOString(), resJson.ultimo_lembrete_por || 'You');
                            }
                            const item = (extratoState.transacoes || []).find(x => String(x.id) === String(id));
                            if (item) {
                                item.ultimo_lembrete = resJson.ultimo_lembrete || new Date().toISOString();
                                item.ultimo_lembrete_por = resJson.ultimo_lembrete_por || 'You';
                            }
                        }
                    } catch(err) {
                        console.error('Error recording reminder:', err);
                    }
                });
            });

            // Bind Pay Buttons for current page
            tbody.querySelectorAll('.btn-pagar').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const b = e.target.closest('button');
                    const cobId = b.getAttribute('data-id');
                    const tipo = b.getAttribute('data-tipo');
                    const valor = parseFloat(b.getAttribute('data-valor')) || 0;

                    if (!splitPaymentMgrContract) {
                        splitPaymentMgrContract = createSplitPaymentManager({ btnSubmitId: 'btnSubmitPag', formatoMoeda });
                        window._splitPaymentMgrContract = splitPaymentMgrContract;
                    }

                    document.getElementById('pag_cobranca_id').value = cobId;
                    document.getElementById('pag_desc_tipo').textContent = typeof formatarDescricaoTransacao === 'function' ? formatarDescricaoTransacao(tipo) : tipo;
                    document.getElementById('pag_desc_valor').textContent = formatoMoeda.format(valor);

                    splitPaymentMgrContract.open(valor, 'Cash');
                    abrirModal('pagamentoModal');
                });
            });

            // Bind Receipt Buttons for current page
            tbody.querySelectorAll('.btn-recibo').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const b = e.target.closest('button');
                    const id = b.getAttribute('data-id');
                    const tipo = b.getAttribute('data-tipo');
                    const descricao = b.getAttribute('data-descricao') || (typeof formatarDescricaoTransacao === 'function' ? formatarDescricaoTransacao(tipo) : tipo);
                    const valor = parseFloat(b.getAttribute('data-valor')) || 0;
                    const forma = b.getAttribute('data-forma') || 'Not specified';
                    const dataStr = b.getAttribute('data-data');
                    const nota = b.getAttribute('data-nota') || '';
                    const ref = b.getAttribute('data-ref') || '';

                    document.getElementById('rec_id').textContent = `#${id}`;
                    document.getElementById('rec_contrato_id').textContent = `Contract #${CONTRATO_ID}`;
                    document.getElementById('rec_cliente').textContent = data.cliente || '-';
                    document.getElementById('rec_placa').textContent = data.placa || '-';
                    document.getElementById('rec_tipo').textContent = descricao;
                    document.getElementById('rec_valor').textContent = formatoMoeda.format(valor);
                    document.getElementById('rec_forma').textContent = forma;
                    document.getElementById('rec_data').textContent = dataStr && dataStr !== '-' ? new Date(dataStr).toLocaleString('en-GB') : '-';

                    const rowRef = document.getElementById('rec_row_ref');
                    const elRef = document.getElementById('rec_ref');
                    if (rowRef && elRef) {
                        if (ref) {
                            elRef.textContent = ref;
                            rowRef.style.display = 'flex';
                        } else {
                            rowRef.style.display = 'none';
                        }
                    }

                    const rowNota = document.getElementById('rec_row_nota');
                    const elNota = document.getElementById('rec_nota');
                    if (rowNota && elNota) {
                        if (nota) {
                            elNota.textContent = nota;
                            rowNota.style.display = 'flex';
                        } else {
                            rowNota.style.display = 'none';
                        }
                    }

                    const recLink = document.getElementById('rec_link_page');
                    if (recLink) recLink.href = `/recibo/${id}`;

                    abrirModal('reciboModal');
                });
            });

            // Bind Revert Buttons for current page
            tbody.querySelectorAll('.btn-reverter-pagamento').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const b = e.target.closest('button');
                    const cobId = b.getAttribute('data-id');
                    const tipo = b.getAttribute('data-tipo');
                    const valor = parseFloat(b.getAttribute('data-valor')) || 0;

                    const confirmar = confirm(`Are you sure you want to CANCEL this completed payment?\n\n• Transaction: #${cobId} (${tipo})\n• Amount: £${valor.toFixed(2)}\n\nThis will reset the transaction back to PENDING and record this cancellation in the audit trail.`);
                    if (!confirmar) return;

                    b.disabled = true;
                    b.textContent = 'Reverting...';
                    try {
                        const res = await fetch(`/api/financeiro/${cobId}/reverter`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' }
                        });
                        const resJson = await res.json();
                        if (!res.ok) {
                            alert(resJson.error || resJson.erro || 'Failed to revert payment.');
                            b.disabled = false;
                            b.textContent = '↩ Cancel / Revert';
                            return;
                        }
                        location.reload();
                    } catch (err) {
                        console.error('Error reverting payment:', err);
                        alert('Connection error while cancelling payment.');
                        b.disabled = false;
                        b.textContent = '↩ Cancel / Revert';
                    }
                });
            });

            // Bind Delete Buttons for current page
            tbody.querySelectorAll('.btn-remover').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const tid = e.target.closest('button').dataset.id;
                    if (confirm('Are you sure you want to delete this charge?')) {
                        try {
                            const r = await fetch(`/api/financeiro/${tid}`, { method: 'DELETE' });
                            if (r.ok) location.reload();
                            else {
                                const d = await r.json();
                                alert(d.message || d.mensagem || d.error || d.erro || 'Failed to remove charge');
                            }
                        } catch(err) {
                            alert('Request failed');
                        }
                    }
                });
            });

            // Bind Attachment View Buttons for current page
            tbody.querySelectorAll('.btn-ver-anexo').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const b = e.target.closest('button');
                    try {
                        const urls = JSON.parse(b.getAttribute('data-urls') || '[]');
                        const ref = b.getAttribute('data-ref') || '';
                        window.openCobrancaAnexoModal(urls, ref);
                    } catch(err) {
                        console.error("Error opening attachments modal:", err);
                    }
                });
            });
        }

        window.openCobrancaAnexoModal = function(urls, ref) {
            const modal = document.getElementById('cobrancaAnexoModal');
            const title = document.getElementById('cobrancaAnexoModalTitle');
            const body = document.getElementById('cobrancaAnexoModalBody');
            if (!modal || !body) return;

            if (title) title.textContent = ref ? `Proof / Attachment: ${ref}` : 'Charge Proof & Attachments';
            body.innerHTML = '';

            const grid = document.createElement('div');
            grid.style.display = 'grid';
            grid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(200px, 1fr))';
            grid.style.gap = '14px';
            grid.style.padding = '0.5rem';

            urls.forEach((url, i) => {
                const isPdf = url.toLowerCase().endsWith('.pdf');
                const card = document.createElement('div');
                card.style.background = 'rgba(15, 23, 42, 0.6)';
                card.style.border = '1px solid var(--border-color)';
                card.style.borderRadius = '12px';
                card.style.padding = '12px';
                card.style.textAlign = 'center';

                if (isPdf) {
                    card.innerHTML = `
                        <div style="font-size:2.8rem; margin-bottom:8px;">📄</div>
                        <div style="font-size:0.8rem; font-weight:600; color:var(--text-primary); margin-bottom:8px;">Document #${i+1}</div>
                        <a href="${url}" target="_blank" class="btn-primary" style="font-size:0.8rem; padding:6px 12px; display:inline-flex; align-items:center; gap:6px; text-decoration:none; margin:0 auto;">
                            <span>👁️</span> Open PDF
                        </a>
                    `;
                } else {
                    card.innerHTML = `
                        <a href="${url}" target="_blank" style="display:block; border-radius:8px; overflow:hidden; margin-bottom:8px;">
                            <img src="${url}" alt="Attachment ${i+1}" style="width:100%; height:160px; object-fit:cover; display:block; border-radius:6px; transition:transform 0.2s ease;">
                        </a>
                        <a href="${url}" target="_blank" class="btn-secondary" style="font-size:0.75rem; padding:4px 10px; display:inline-flex; align-items:center; gap:4px; text-decoration:none; margin:0 auto;">
                            🔍 View Full Image
                        </a>
                    `;
                }
                grid.appendChild(card);
            });

            body.appendChild(grid);
            abrirModal('cobrancaAnexoModal');
        };

        // Setup Header Sort Click Handlers
        const extratoHeaders = document.querySelectorAll('#extratoTable thead th[data-sort-field]');
        extratoHeaders.forEach(th => {
            th.addEventListener('click', () => {
                const field = th.getAttribute('data-sort-field');
                if (extratoState.sortField === field) {
                    extratoState.sortOrder = extratoState.sortOrder === 'asc' ? 'desc' : 'asc';
                } else {
                    extratoState.sortField = field;
                    extratoState.sortOrder = (field === 'valor' || field.includes('data')) ? 'desc' : 'asc';
                }
                extratoState.currentPage = 1;
                renderExtrato();
            });
        });

        // Setup Pagination Controls
        const btnExtratoPrev = document.getElementById('btnExtratoPrev');
        if (btnExtratoPrev) {
            btnExtratoPrev.addEventListener('click', () => {
                if (extratoState.currentPage > 1) {
                    extratoState.currentPage--;
                    renderExtrato();
                }
            });
        }

        const btnExtratoNext = document.getElementById('btnExtratoNext');
        if (btnExtratoNext) {
            btnExtratoNext.addEventListener('click', () => {
                const filteredCount = getFilteredExtrato().length;
                const pageSizeNum = extratoState.pageSize === 'all' ? filteredCount : parseInt(extratoState.pageSize, 10);
                const totalPages = Math.max(1, Math.ceil(filteredCount / pageSizeNum));
                if (extratoState.currentPage < totalPages) {
                    extratoState.currentPage++;
                    renderExtrato();
                }
            });
        }

        const selectPageSize = document.getElementById('selectExtratoPageSize');
        if (selectPageSize) {
            selectPageSize.addEventListener('change', () => {
                extratoState.pageSize = selectPageSize.value;
                extratoState.currentPage = 1;
                renderExtrato();
            });
        }

        // Setup Filter & Search Listeners
        const extratoSearchInput = document.getElementById('extratoSearchInput');
        if (extratoSearchInput) {
            extratoSearchInput.addEventListener('input', (e) => {
                extratoState.searchTerm = e.target.value;
                extratoState.currentPage = 1;
                renderExtrato();
            });
        }

        const extratoFilterStatus = document.getElementById('extratoFilterStatus');
        if (extratoFilterStatus) {
            extratoFilterStatus.addEventListener('change', (e) => {
                extratoState.filterStatus = e.target.value;
                extratoState.currentPage = 1;
                renderExtrato();
            });
        }

        const btnExtratoClearFilter = document.getElementById('btnExtratoClearFilter');
        if (btnExtratoClearFilter) {
            btnExtratoClearFilter.addEventListener('click', () => {
                extratoState.searchTerm = '';
                extratoState.filterStatus = 'all';
                if (extratoSearchInput) extratoSearchInput.value = '';
                if (extratoFilterStatus) extratoFilterStatus.value = 'all';
                extratoState.currentPage = 1;
                renderExtrato();
            });
        }

        // Initial render of Financial Statement table
        renderExtrato();
        
        // 5. Recorded Inspections
        const vistContainer = document.getElementById('vistoriasList');
        vistContainer.innerHTML = '';
        
        if (!hasCheckoutInsp && isActiveContract && !isPurchaseContrato) {
            const checkoutPrompt = document.createElement('div');
            checkoutPrompt.style.cssText = "background: rgba(245, 158, 11, 0.12); border: 1px dashed rgba(245, 158, 11, 0.45); border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.85rem; display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap;";
            checkoutPrompt.innerHTML = `
                <div>
                    <strong style="color: #fbbf24; font-size: 0.85rem; display: block;">⚠️ Check-out Inspection Pending</strong>
                    <span style="color: var(--text-secondary); font-size: 0.78rem;">Take initial photos before vehicle collection / release.</span>
                </div>
                <button type="button" class="btn-action btn-trigger-checkout-insp" style="background: #f59e0b; color: #000; font-weight: 700; font-size: 0.78rem; padding: 6px 12px; border-radius: 6px; cursor: pointer; border: none;">
                    📸 Take Photos Now
                </button>
            `;
            vistContainer.appendChild(checkoutPrompt);
            checkoutPrompt.querySelector('.btn-trigger-checkout-insp').onclick = () => {
                if (typeof window.abrirModalCheckOutVistoria === 'function') window.abrirModalCheckOutVistoria();
            };
        }
        
        if (!data.vistorias || data.vistorias.length === 0) {
            const noInspMsg = document.createElement('p');
            noInspMsg.style.cssText = 'color: var(--text-secondary); text-align: center; padding: 1.5rem 0; font-size: 0.85rem;';
            noInspMsg.textContent = 'No inspections recorded for this contract.';
            vistContainer.appendChild(noInspMsg);
        } else {
            data.vistorias.forEach(v => {
                const dataVist = v.data_vistoria ? new Date(v.data_vistoria).toLocaleString('en-GB') : '-';
                
                let tBadge = '';
                const tipoV = (v.tipo || '').toLowerCase();
                if (tipoV === 'check-out' || tipoV === 'saída') tBadge = '<span class="badge badge-info">Check-out</span>';
                else if (tipoV === 'check-in' || tipoV === 'entrada') tBadge = '<span class="badge badge-warning">Check-in</span>';
                else tBadge = '<span class="badge badge-danger">Incident</span>';
                
                const fotosCount = v.foto_url ? v.foto_url.split(',').filter(Boolean).length : 0;
                const fotosLabel = fotosCount > 0 ? `📷 ${fotosCount}` : `View`;
                const idBadge = `<span class="badge" style="background: rgba(255, 255, 255, 0.08); color: var(--text-primary); border: 1px solid var(--border-color); font-weight: 700; font-size: 0.75rem;">#${v.id}</span>`;

                const div = document.createElement('div');
                div.id = `inspection-item-${v.id}`;
                div.style.cssText = "background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-color); padding: 0.875rem 1rem; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; gap: 10px; transition: all 0.3s ease;";
                div.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 4px; min-width: 0;">
                        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            ${idBadge}
                            ${tBadge}
                            <span style="font-size: 0.8rem; color: var(--text-secondary);">${dataVist}</span>
                            ${v.milhagem != null ? `<span style="font-size: 0.75rem; color: #fbbf24; font-weight: 600;">&bull; ⏱️ ${v.milhagem} mi</span>` : ''}
                            ${v.realizado_por_nome ? `<span style="font-size: 0.75rem; color: #c084fc;">&bull; 👤 ${escapeHtml(v.realizado_por_nome)}</span>` : ''}
                        </div>
                        <div style="font-size: 0.85rem; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px;">
                            ${escapeHtml(v.observacoes) || '<em style="opacity:0.5;">No notes</em>'}
                        </div>
                    </div>
                    <button class="btn-action btn-ver-foto" data-id="${v.id}" data-tipo="${escapeHtml(v.tipo)}" data-data="${dataVist}" data-foto="${v.foto_url || ''}" data-mil="${v.milhagem != null ? v.milhagem : ''}" data-obs="${escapeHtml(v.observacoes || 'No notes.')}" style="padding: 6px 12px; font-size: 0.8rem; white-space: nowrap;">
                        ${fotosLabel}
                    </button>
                `;
                vistContainer.appendChild(div);
            });
            
            // View Inspection Photos (Modal)
            document.querySelectorAll('.btn-ver-foto').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const b = e.target.closest('button');
                    const inspId = b.getAttribute('data-id');
                    const fotosCsv = b.getAttribute('data-foto');
                    const obs = b.getAttribute('data-obs');
                    const tipo = b.getAttribute('data-tipo');
                    const dataStr = b.getAttribute('data-data');
                    const milhagem = b.getAttribute('data-mil');
                    
                    if (document.getElementById('modalVistoriaTitle')) {
                        document.getElementById('modalVistoriaTitle').textContent = inspId ? `Inspection #${inspId} Details` : 'Inspection Details';
                    }
                    if (document.getElementById('modalVistoriaId')) {
                        document.getElementById('modalVistoriaId').textContent = inspId ? `#${inspId}` : '-';
                    }

                    const tLower = (tipo || '').toLowerCase();
                    document.getElementById('modalVistoriaTipo').innerHTML = (
                        tLower === 'check-out' || tLower === 'saída' ? '<span class="badge badge-info">Check-out</span>' :
                        tLower === 'check-in' || tLower === 'entrada' ? '<span class="badge badge-warning">Check-in</span>' :
                        '<span class="badge badge-danger">Incident</span>'
                    );
                    document.getElementById('modalVistoriaData').textContent = dataStr;
                    document.getElementById('vistoria_obs').textContent = obs;

                    const rowMilhagem = document.getElementById('modalVistoriaMilhagemRow');
                    if (rowMilhagem) {
                        if (milhagem) {
                            rowMilhagem.style.display = 'flex';
                            document.getElementById('modalVistoriaMilhagem').textContent = `${milhagem} mi`;
                        } else {
                            rowMilhagem.style.display = 'none';
                        }
                    }
                    
                    const galeria = document.getElementById('vistoria_galeria');
                    if (typeof renderInspectionCarousel === 'function') {
                        renderInspectionCarousel(galeria, fotosCsv);
                    }
                    
                    abrirModal('viewVistoriaModal');
                });
            });
        }
        
        window.highlightInspection = function(id) {
            const el = document.getElementById('inspection-item-' + id);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                el.style.borderColor = '#ef4444';
                el.style.boxShadow = '0 0 16px rgba(239, 68, 68, 0.45)';
                el.style.background = 'rgba(239, 68, 68, 0.12)';
                setTimeout(() => {
                    el.style.borderColor = 'var(--border-color)';
                    el.style.boxShadow = 'none';
                    el.style.background = 'rgba(15, 23, 42, 0.4)';
                }, 3000);
            }
        };
        
        // 6. Setup forms and modals
        
        // Charge Photo / Document Accumulator
        let cobSelectedPhotos = [];
        const btnCobTakePhoto = document.getElementById('btnCobTakePhoto');
        const cobCameraInput = document.getElementById('cobCameraInput');
        const btnCobPickGallery = document.getElementById('btnCobPickGallery');
        const cobGalleryInput = document.getElementById('cobGalleryInput');
        const cobPreview = document.getElementById('cob_preview');
        const cobPhotoCountBadge = document.getElementById('cobPhotoCountBadge');

        function resetCobPhotos() {
            cobSelectedPhotos = [];
            if (cobCameraInput) cobCameraInput.value = '';
            if (cobGalleryInput) cobGalleryInput.value = '';
            const refInput = document.getElementById('cob_referencia');
            if (refInput) refInput.value = '';
            renderCobPreviews();
        }

        if (btnCobTakePhoto && cobCameraInput) {
            btnCobTakePhoto.addEventListener('click', () => cobCameraInput.click());
            cobCameraInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    Array.from(e.target.files).forEach(file => cobSelectedPhotos.push(file));
                    cobCameraInput.value = '';
                    renderCobPreviews();
                }
            });
        }

        if (btnCobPickGallery && cobGalleryInput) {
            btnCobPickGallery.addEventListener('click', () => cobGalleryInput.click());
            cobGalleryInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    Array.from(e.target.files).forEach(file => cobSelectedPhotos.push(file));
                    cobGalleryInput.value = '';
                    renderCobPreviews();
                }
            });
        }

        function renderCobPreviews() {
            if (!cobPreview) return;
            cobPreview.innerHTML = '';

            if (cobPhotoCountBadge) {
                cobPhotoCountBadge.textContent = `${cobSelectedPhotos.length} attached`;
                if (cobSelectedPhotos.length > 0) {
                    cobPhotoCountBadge.style.background = 'rgba(34, 197, 94, 0.15)';
                    cobPhotoCountBadge.style.color = '#4ade80';
                    cobPhotoCountBadge.style.borderColor = 'rgba(34, 197, 94, 0.3)';
                } else {
                    cobPhotoCountBadge.style.background = 'rgba(255, 102, 0, 0.15)';
                    cobPhotoCountBadge.style.color = 'var(--accent)';
                    cobPhotoCountBadge.style.borderColor = 'rgba(255, 102, 0, 0.3)';
                }
            }

            if (cobSelectedPhotos.length > 0) {
                cobPreview.style.display = 'grid';
                cobSelectedPhotos.forEach((file, index) => {
                    const div = document.createElement('div');
                    div.className = 'photo-item';
                    div.style.aspectRatio = '1 / 1';
                    
                    if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
                        div.innerHTML = `
                            <span class="photo-badge-idx">#${index + 1}</span>
                            <button type="button" class="photo-remove-btn" title="Remove" onclick="removeCobPhoto(${index})">&times;</button>
                            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; font-size:0.75rem; color:#fca5a5; padding:4px;">
                                <span style="font-size:1.8rem;">📄</span>
                                <span style="overflow:hidden; text-overflow:ellipsis; width:100%; text-align:center;">PDF</span>
                            </div>
                        `;
                    } else {
                        const reader = new FileReader();
                        reader.onload = (e) => {
                            div.innerHTML = `
                                <span class="photo-badge-idx">#${index + 1}</span>
                                <button type="button" class="photo-remove-btn" title="Remove" onclick="removeCobPhoto(${index})">&times;</button>
                                <img src="${e.target.result}" alt="Preview ${index + 1}">
                            `;
                        };
                        reader.readAsDataURL(file);
                    }
                    cobPreview.appendChild(div);
                });
            } else {
                cobPreview.style.display = 'none';
            }
        }

        window.removeCobPhoto = function(index) {
            cobSelectedPhotos.splice(index, 1);
            renderCobPreviews();
        };

        // Add Charge Form
        document.getElementById('btnLancCob')?.addEventListener('click', () => {
            document.getElementById('cob_data').value = new Date().toISOString().split('T')[0];
            resetCobPhotos();
            abrirModal('cobrancaModal');
        });
        
        document.getElementById('cobrancaForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('btnSalvarCob');
            btn.disabled = true;
            btn.textContent = 'Processing...';

            const tipoVal = document.getElementById('cob_tipo').value;
            const valorVal = document.getElementById('cob_valor').value;
            const dataVal = document.getElementById('cob_data').value;
            const refVal = (document.getElementById('cob_referencia')?.value || '').trim();

            const formData = new FormData();
            formData.append('tipo', tipoVal);
            formData.append('valor', valorVal);
            formData.append('data_vencimento', dataVal);
            if (refVal) formData.append('referencia', refVal);

            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
            const compOptions = {
                maxSizeMB: 0.35,
                maxWidthOrHeight: 1600,
                useWebWorker: !isIOS,
                fileType: isIOS ? 'image/jpeg' : 'image/webp',
                initialQuality: 0.75
            };
            const extReplacement = isIOS ? '.jpg' : '.webp';

            for (let i = 0; i < cobSelectedPhotos.length; i++) {
                const file = cobSelectedPhotos[i];
                if (file.type && file.type.startsWith('image/')) {
                    try {
                        const compressed = await imageCompression(file, compOptions);
                        formData.append('fotos', compressed, file.name.replace(/\.[^/.]+$/, extReplacement));
                    } catch (err) {
                        formData.append('fotos', file);
                    }
                } else {
                    formData.append('fotos', file);
                }
            }

            try {
                btn.textContent = 'Saving charge...';
                const res = await fetch(`/api/contratos/${CONTRATO_ID}/cobrancas`, {
                    method: 'POST',
                    body: formData
                });
                if (res.ok) {
                    location.reload();
                } else {
                    const resJson = await res.json();
                    alert(resJson.message || resJson.mensagem || resJson.error || resJson.erro || 'Failed to add charge');
                }
            } catch(e) {
                alert('Connection error');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Create Charge';
            }
        });
        
        // Incident Photo Accumulator for iPhone Camera & Gallery
        let ocSelectedPhotos = [];
        const btnOcTakePhoto = document.getElementById('btnOcTakePhoto');
        const ocCameraInput = document.getElementById('ocCameraInput');
        const btnOcPickGallery = document.getElementById('btnOcPickGallery');
        const ocGalleryInput = document.getElementById('ocGalleryInput');
        const ocPreview = document.getElementById('oc_preview');
        const ocPhotoCountBadge = document.getElementById('ocPhotoCountBadge');
        const ocGerarCobrancaCheck = document.getElementById('oc_gerar_cobranca');
        const ocCobrancaFields = document.getElementById('oc_cobranca_fields');
        const ocCobVencimento = document.getElementById('oc_cob_vencimento');

        if (ocGerarCobrancaCheck && ocCobrancaFields) {
            ocGerarCobrancaCheck.addEventListener('change', () => {
                ocCobrancaFields.style.display = ocGerarCobrancaCheck.checked ? 'block' : 'none';
                if (ocGerarCobrancaCheck.checked && ocCobVencimento && !ocCobVencimento.value) {
                    ocCobVencimento.value = new Date().toISOString().split('T')[0];
                }
            });
        }

        function resetOcPhotos() {
            ocSelectedPhotos = [];
            if (ocCameraInput) ocCameraInput.value = '';
            if (ocGalleryInput) ocGalleryInput.value = '';
            if (ocGerarCobrancaCheck) {
                ocGerarCobrancaCheck.checked = false;
                if (ocCobrancaFields) ocCobrancaFields.style.display = 'none';
            }
            const ocCobVal = document.getElementById('oc_cob_valor');
            if (ocCobVal) ocCobVal.value = '';
            const ocCobRef = document.getElementById('oc_cob_referencia');
            if (ocCobRef) ocCobRef.value = '';
            renderOcPreviews();
        }

        if (btnOcTakePhoto && ocCameraInput) {
            btnOcTakePhoto.addEventListener('click', () => ocCameraInput.click());
            ocCameraInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    Array.from(e.target.files).forEach(file => ocSelectedPhotos.push(file));
                    ocCameraInput.value = '';
                    renderOcPreviews();
                }
            });
        }

        if (btnOcPickGallery && ocGalleryInput) {
            btnOcPickGallery.addEventListener('click', () => ocGalleryInput.click());
            ocGalleryInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    Array.from(e.target.files).forEach(file => ocSelectedPhotos.push(file));
                    ocGalleryInput.value = '';
                    renderOcPreviews();
                }
            });
        }

        function renderOcPreviews() {
            if (!ocPreview) return;
            ocPreview.innerHTML = '';

            if (ocPhotoCountBadge) {
                ocPhotoCountBadge.textContent = `${ocSelectedPhotos.length} photo${ocSelectedPhotos.length === 1 ? '' : 's'} added`;
                if (ocSelectedPhotos.length > 0) {
                    ocPhotoCountBadge.style.background = 'rgba(34, 197, 94, 0.15)';
                    ocPhotoCountBadge.style.color = '#4ade80';
                    ocPhotoCountBadge.style.borderColor = 'rgba(34, 197, 94, 0.3)';
                } else {
                    ocPhotoCountBadge.style.background = 'rgba(255, 102, 0, 0.15)';
                    ocPhotoCountBadge.style.color = 'var(--accent)';
                    ocPhotoCountBadge.style.borderColor = 'rgba(255, 102, 0, 0.3)';
                }
            }

            if (ocSelectedPhotos.length > 0) {
                ocPreview.style.display = 'grid';
                ocSelectedPhotos.forEach((file, index) => {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        const div = document.createElement('div');
                        div.className = 'photo-item';
                        div.style.aspectRatio = '1 / 1';
                        div.innerHTML = `
                            <span class="photo-badge-idx">#${index + 1}</span>
                            <button type="button" class="photo-remove-btn" title="Remove photo" onclick="removeOcPhoto(${index})">&times;</button>
                            <img src="${e.target.result}" alt="Preview ${index + 1}">
                        `;
                        ocPreview.appendChild(div);
                    };
                    reader.readAsDataURL(file);
                });
            } else {
                ocPreview.style.display = 'none';
            }
        }

        window.removeOcPhoto = function(index) {
            ocSelectedPhotos.splice(index, 1);
            renderOcPreviews();
        };

        function abrirModalCheckOutVistoria() {
            document.getElementById('ocorrenciaModalTitle').textContent = 'Pre-Delivery Check-out Inspection';
            document.getElementById('oc_tipo').value = 'Check-out';
            const ocObs = document.getElementById('oc_obs');
            if (ocObs) {
                ocObs.placeholder = 'Initial check-out condition, tyre notes, pre-existing scratches (optional)...';
            }
            const ocMilhagem = document.getElementById('oc_milhagem');
            if (ocMilhagem && (!ocMilhagem.value || ocMilhagem.value == '0') && (window._contractData && window._contractData.milhagem_inicial)) {
                ocMilhagem.value = window._contractData.milhagem_inicial;
            }
            resetOcPhotos();
            abrirModal('ocorrenciaModal');
        }
        window.abrirModalCheckOutVistoria = abrirModalCheckOutVistoria;

        // New Incident Button
        document.getElementById('btnNovaOcorr')?.addEventListener('click', () => {
            document.getElementById('ocorrenciaModalTitle').textContent = 'New Inspection (Incident)';
            document.getElementById('oc_tipo').value = 'Incident';
            const ocObs = document.getElementById('oc_obs');
            if (ocObs) {
                ocObs.placeholder = 'Describe damages, reason for incident...';
            }
            resetOcPhotos();
            abrirModal('ocorrenciaModal');
        });

        const btnNovaVistoriaLink = document.getElementById('btnNovaVistoriaLink');
        if (btnNovaVistoriaLink && !hasCheckoutInsp && isActiveContract) {
            btnNovaVistoriaLink.onclick = (e) => {
                e.preventDefault();
                abrirModalCheckOutVistoria();
            };
        }

        // Submit Inspection Form
        document.getElementById('ocorrenciaForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (ocSelectedPhotos.length === 0) {
                alert('Please take or select at least one vehicle photo.');
                return;
            }

            const ocTipoVal = document.getElementById('oc_tipo').value;
            const ocObsVal = (document.getElementById('oc_obs').value || '').trim();
            if (ocTipoVal !== 'Check-out' && !ocObsVal) {
                alert('Please describe damage observations or reason for incident.');
                return;
            }

            const btn = document.getElementById('btnSalvarOcorr');
            btn.disabled = true;
            btn.textContent = 'Processing photos...';

            const formData = new FormData();
            formData.append('id_contrato', CONTRATO_ID);
            formData.append('tipo', ocTipoVal);
            const ocMilhagem = document.getElementById('oc_milhagem');
            if (ocMilhagem && ocMilhagem.value) {
                formData.append('milhagem', ocMilhagem.value);
            }
            formData.append('observacoes', ocObsVal);

            if (ocGerarCobrancaCheck && ocGerarCobrancaCheck.checked) {
                const ocCobVal = document.getElementById('oc_cob_valor')?.value;
                if (!ocCobVal || parseFloat(ocCobVal) <= 0) {
                    alert('Please enter a valid repair/charge amount (£) or uncheck the charge option.');
                    btn.disabled = false;
                    btn.textContent = 'Save Inspection';
                    return;
                }
                formData.append('gerar_cobranca', '1');
                formData.append('cobranca_valor', ocCobVal);
                const ocCobVenc = document.getElementById('oc_cob_vencimento')?.value;
                if (ocCobVenc) formData.append('cobranca_vencimento', ocCobVenc);
                const ocCobRef = (document.getElementById('oc_cob_referencia')?.value || '').trim();
                if (ocCobRef) formData.append('cobranca_referencia', ocCobRef);
            }
            
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
            const compOptions = {
                maxSizeMB: 0.35,
                maxWidthOrHeight: 1600,
                useWebWorker: !isIOS,
                fileType: isIOS ? 'image/jpeg' : 'image/webp',
                initialQuality: 0.75
            };
            const extReplacement = isIOS ? '.jpg' : '.webp';

            for (let i = 0; i < ocSelectedPhotos.length; i++) {
                const file = ocSelectedPhotos[i];
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
            
            try {
                btn.textContent = 'Uploading to server...';
                const res = await fetch(`/api/vistorias`, {
                    method: 'POST',
                    body: formData
                });
                if (res.ok) {
                    location.reload();
                } else {
                    const resJson = await res.json();
                    alert(resJson.message || resJson.mensagem || resJson.error || resJson.erro || 'Failed to record inspection');
                }
            } catch(e) {
                alert('Connection error while saving inspection.');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Save Inspection';
            }
        });

        // Submit Payment Form
        document.getElementById('pagamentoForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const cobId = document.getElementById('pag_cobranca_id').value;
            const btn = document.getElementById('btnSubmitPag');
            
            const mgr = window._splitPaymentMgrContract || createSplitPaymentManager({ btnSubmitId: 'btnSubmitPag', formatoMoeda });
            const payload = mgr.getPayload();
            if (payload.valor_pago <= 0) {
                alert('Please enter a valid payment amount greater than zero.');
                return;
            }

            btn.disabled = true;
            btn.textContent = 'Processing...';

            try {
                const res = await fetch(`/api/financeiro/pagar/${cobId}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                if (res.ok) {
                    location.reload();
                } else {
                    const resJson = await res.json();
                    alert(resJson.message || resJson.mensagem || resJson.error || resJson.erro || 'Failed to record payment');
                }
            } catch(err) {
                alert('Connection error');
            } finally {
                btn.disabled = false;
                mgr.recalculate();
            }
        });

        // Submit Deposit Release Form
        document.getElementById('formDevolverDeposito')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('btnConfirmarDevolucao');
            btn.disabled = true;
            btn.textContent = 'Submitting...';

            const formData = new FormData();
            const fileInput = document.getElementById('comprovante_deposito');
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                if (file.type.startsWith('image/')) {
                    try {
                        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
                        const compOptions = {
                            maxSizeMB: 0.35,
                            maxWidthOrHeight: 1600,
                            useWebWorker: !isIOS,
                            fileType: isIOS ? 'image/jpeg' : 'image/webp',
                            initialQuality: 0.75
                        };
                        const compressedFile = await imageCompression(file, compOptions);
                        formData.append('comprovante', compressedFile, file.name.replace(/\.[^/.]+$/, isIOS ? '.jpg' : '.webp'));
                    } catch (err) {
                        formData.append('comprovante', file);
                    }
                } else {
                    formData.append('comprovante', file);
                }
            }
            
            try {
                const res = await fetch(`/api/contratos/${CONTRATO_ID}/finalizar-quarentena`, {
                    method: 'POST',
                    body: formData
                });
                if (res.ok) {
                    alert('Deposit Hold released and deposit refund recorded successfully!');
                    location.reload();
                } else {
                    const d = await res.json();
                    alert(d.message || d.mensagem || d.error || d.erro || 'Failed to release deposit hold');
                }
            } catch (err) {
                alert('Connection error while releasing deposit hold.');
            } finally {
                btn.disabled = false;
                btn.textContent = 'Confirm Refund';
            }
        });
        
    } catch(err) {
        console.error("General error in detalhe_contrato:", err);
    }

    // Funções utilitárias de modal
    function abrirModal(id) {
        const m = document.getElementById(id);
        if (m) m.classList.add('active');
    }

    function fecharModal(id) {
        const m = document.getElementById(id);
        if (m) m.classList.remove('active');
    }

    // Fechar botões de modal
    const closeMapping = [
        ['closeViewModal', 'viewVistoriaModal'],
        ['closeCobrancaModal', 'cobrancaModal'],
        ['closeCobrancaAnexoModal', 'cobrancaAnexoModal'],
        ['closeOcorrenciaModal', 'ocorrenciaModal'],
        ['closePagamentoModal', 'pagamentoModal'],
        ['closeReciboModal', 'reciboModal'],
        ['closeDevolverDepositoModal', 'devolverDepositoModal'],
        ['closeAnexosModal', 'modalAnexosContrato'],
        ['closeDetalheSignatureModal', 'modalDetalheSignaturePad'],
        ['btnDetalheCancelSig', 'modalDetalheSignaturePad'],
        ['closeCancelarModal', 'modalCancelarContrato'],
        ['btnCancelDismiss', 'modalCancelarContrato'],
        ['closeDiaVencModal', 'modalAlterarDiaVenc'],
        ['btnDismissDiaVenc', 'modalAlterarDiaVenc']
    ];

    closeMapping.forEach(([btnId, modalId]) => {
        const btn = document.getElementById(btnId);
        if (btn) btn.addEventListener('click', () => fecharModal(modalId));
        
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) fecharModal(modalId);
            });
        }
    });

    // --- Modal de Anexos (Upload de Fotos / Scans do Contrato Físico) ---
    let anexoSelectedFiles = [];
    const btnAnexoTakePhoto = document.getElementById('btnAnexoTakePhoto');
    const anexoCameraInput = document.getElementById('anexoCameraInput');
    const btnAnexoPickGallery = document.getElementById('btnAnexoPickGallery');
    const anexoGalleryInput = document.getElementById('anexoGalleryInput');
    const anexoPreview = document.getElementById('anexo_preview');
    const anexoPhotoCountBadge = document.getElementById('anexoPhotoCountBadge');

    function resetAnexoFiles() {
        anexoSelectedFiles = [];
        if (anexoCameraInput) anexoCameraInput.value = '';
        if (anexoGalleryInput) anexoGalleryInput.value = '';
        renderAnexoPreviews();
    }

    if (btnAnexoTakePhoto && anexoCameraInput) {
        btnAnexoTakePhoto.addEventListener('click', () => anexoCameraInput.click());
        anexoCameraInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                Array.from(e.target.files).forEach(file => anexoSelectedFiles.push(file));
                anexoCameraInput.value = '';
                renderAnexoPreviews();
            }
        });
    }

    if (btnAnexoPickGallery && anexoGalleryInput) {
        btnAnexoPickGallery.addEventListener('click', () => anexoGalleryInput.click());
        anexoGalleryInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                Array.from(e.target.files).forEach(file => anexoSelectedFiles.push(file));
                anexoGalleryInput.value = '';
                renderAnexoPreviews();
            }
        });
    }

    window.removeAnexoFile = function(index) {
        anexoSelectedFiles.splice(index, 1);
        renderAnexoPreviews();
    };

    function renderAnexoPreviews() {
        if (!anexoPreview) return;
        anexoPreview.innerHTML = '';

        if (anexoPhotoCountBadge) {
            anexoPhotoCountBadge.textContent = `${anexoSelectedFiles.length} item${anexoSelectedFiles.length === 1 ? '' : 's'} added`;
            if (anexoSelectedFiles.length > 0) {
                anexoPhotoCountBadge.style.background = 'rgba(34, 197, 94, 0.15)';
                anexoPhotoCountBadge.style.color = '#4ade80';
                anexoPhotoCountBadge.style.borderColor = 'rgba(34, 197, 94, 0.3)';
            } else {
                anexoPhotoCountBadge.style.background = 'rgba(255, 102, 0, 0.15)';
                anexoPhotoCountBadge.style.color = 'var(--accent)';
                anexoPhotoCountBadge.style.borderColor = 'rgba(255, 102, 0, 0.3)';
            }
        }

        if (anexoSelectedFiles.length > 0) {
            anexoPreview.style.display = 'grid';
            anexoSelectedFiles.forEach((file, index) => {
                const div = document.createElement('div');
                div.className = 'photo-item';
                div.style.aspectRatio = '1 / 1';
                div.style.position = 'relative';

                if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) {
                    div.innerHTML = `
                        <span class="photo-badge-idx">#${index + 1}</span>
                        <button type="button" class="photo-remove-btn" title="Remove file" onclick="removeAnexoFile(${index})">&times;</button>
                        <div style="width:100%; height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; background:rgba(15,23,42,0.8); padding:8px; text-align:center;">
                            <span style="font-size:2rem;">📄</span>
                            <span style="font-size:0.7rem; color:var(--text-secondary); margin-top:4px; max-width:90%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(file.name)}</span>
                        </div>
                    `;
                } else {
                    let objectUrl = '';
                    try {
                        objectUrl = URL.createObjectURL(file);
                    } catch (e) {
                        objectUrl = '';
                    }
                    div.innerHTML = `
                        <span class="photo-badge-idx">#${index + 1}</span>
                        <button type="button" class="photo-remove-btn" title="Remove photo" onclick="removeAnexoFile(${index})">&times;</button>
                        <img src="${objectUrl}" alt="Page ${index + 1}" style="width:100%; height:100%; object-fit:cover;">
                    `;
                }
                anexoPreview.appendChild(div);
            });
        } else {
            anexoPreview.style.display = 'none';
        }
    }

    const btnAbrirAnexar = document.getElementById('btnAbrirAnexarContrato');
    if (btnAbrirAnexar) {
        btnAbrirAnexar.addEventListener('click', () => {
            const formAnexos = document.getElementById('formUploadAnexos');
            if (formAnexos) formAnexos.reset();
            resetAnexoFiles();
            abrirModal('modalAnexosContrato');
        });
    }

    const formUploadAnexos = document.getElementById('formUploadAnexos');
    if (formUploadAnexos) {
        formUploadAnexos.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (anexoSelectedFiles.length === 0) {
                alert('Please take or select at least one photo or PDF document.');
                return;
            }

            const btn = document.getElementById('btnSalvarAnexos');
            const originalText = btn ? btn.textContent : 'Upload Attachments';
            if (btn) {
                btn.disabled = true;
                btn.textContent = `Optimizing & uploading ${anexoSelectedFiles.length} file(s)...`;
            }

            const formData = new FormData();
            formData.append('tipo', document.getElementById('anexo_tipo').value);

            // Obter token CSRF com múltiplos fallbacks
            const csrfInput = document.querySelector('#formUploadAnexos input[name="csrf_token"]');
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            const csrfToken = (csrfInput && csrfInput.value) || (csrfMeta ? csrfMeta.getAttribute('content') : '');
            if (csrfToken) {
                formData.append('csrf_token', csrfToken);
            }

            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
            const compOptions = {
                maxSizeMB: 0.45,
                maxWidthOrHeight: 1800,
                useWebWorker: !isIOS,
                fileType: isIOS ? 'image/jpeg' : 'image/webp',
                initialQuality: 0.8
            };
            const extReplacement = isIOS ? '.jpg' : '.webp';

            for (let i = 0; i < anexoSelectedFiles.length; i++) {
                const file = anexoSelectedFiles[i];
                let safeName = file.name || `doc_${i + 1}`;
                if (file.type.startsWith('image/')) {
                    if (safeName.includes('.')) {
                        safeName = safeName.replace(/\.[^/.]+$/, extReplacement);
                    } else {
                        safeName = `${safeName}${extReplacement}`;
                    }
                    try {
                        const compressed = await imageCompression(file, compOptions);
                        formData.append('arquivos', compressed, safeName);
                    } catch (err) {
                        formData.append('arquivos', file, safeName);
                    }
                } else {
                    if (!safeName.toLowerCase().endsWith('.pdf') && !safeName.includes('.')) {
                        safeName = `${safeName}.pdf`;
                    }
                    formData.append('arquivos', file, safeName);
                }
            }

            try {
                const headers = {};
                if (csrfToken) {
                    headers['X-CSRFToken'] = csrfToken;
                }

                const res = await fetch(`/api/contratos/${CONTRATO_ID}/anexos`, {
                    method: 'POST',
                    body: formData,
                    headers: headers
                });

                let data = null;
                const contentType = res.headers.get('content-type') || '';
                if (contentType.includes('application/json')) {
                    data = await res.json();
                } else {
                    const text = await res.text();
                    data = { error: `Server error (${res.status}): ${text.substring(0, 150)}` };
                }

                if (res.ok && data && data.success) {
                    fecharModal('modalAnexosContrato');
                    resetAnexoFiles();
                    if (typeof carregarDetalhesContrato === 'function') {
                        carregarDetalhesContrato();
                    } else {
                        location.reload();
                    }
                } else {
                    const msg = (data && (data.message || data.error || data.erro)) || `Upload failed (Status ${res.status}).`;
                    alert(msg);
                }
            } catch (err) {
                console.error('Error uploading attachments:', err);
                alert('Upload error: ' + (err.message || 'Connection interrupted. Please try again.'));
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = originalText;
                }
            }
        });
    }

    window.deletarAnexoContrato = async function(anexoId) {
        if (!confirm('Are you sure you want to delete this contract attachment?')) return;

        const csrfInput = document.querySelector('#formUploadAnexos input[name="csrf_token"]') || document.querySelector('input[name="csrf_token"]');
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = (csrfInput && csrfInput.value) || (csrfMeta ? csrfMeta.getAttribute('content') : '');

        try {
            const headers = {};
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const res = await fetch(`/api/contratos/anexos/${anexoId}`, { 
                method: 'DELETE',
                headers: headers
            });

            let data = null;
            const contentType = res.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                data = await res.json();
            }

            if (res.ok) {
                if (typeof carregarDetalhesContrato === 'function') {
                    carregarDetalhesContrato();
                } else {
                    location.reload();
                }
            } else {
                const msg = (data && (data.message || data.error || data.erro)) || `Failed to delete attachment (Status ${res.status}).`;
                alert(msg);
            }
        } catch (e) {
            console.error('Error deleting attachment:', e);
            alert('Connection error while deleting attachment.');
        }
    };

    // --- Cancel Contract Modal & Action ---
    const btnAbrirCancelar = document.getElementById('btnAbrirCancelarContrato');
    const formCancelarContrato = document.getElementById('formCancelarContrato');
    const btnConfirmarCancelar = document.getElementById('btnConfirmarCancelar');
    const cancelMotivoInput = document.getElementById('cancel_motivo');
    const cancelMotivoError = document.getElementById('cancel_motivo_error');

    if (btnAbrirCancelar) {
        btnAbrirCancelar.addEventListener('click', () => {
            if (formCancelarContrato) formCancelarContrato.reset();
            if (cancelMotivoInput) cancelMotivoInput.style.borderColor = 'var(--input-border)';
            if (cancelMotivoError) cancelMotivoError.style.display = 'none';
            abrirModal('modalCancelarContrato');
        });
    }

    if (cancelMotivoInput) {
        cancelMotivoInput.addEventListener('input', () => {
            if (cancelMotivoInput.value.trim().length > 0) {
                cancelMotivoInput.style.borderColor = 'var(--input-border)';
                if (cancelMotivoError) cancelMotivoError.style.display = 'none';
            }
        });
    }

    async function executarCancelamentoContrato() {
        const motivo = cancelMotivoInput ? cancelMotivoInput.value.trim() : '';
        if (!motivo) {
            if (cancelMotivoInput) {
                cancelMotivoInput.style.borderColor = '#ef4444';
                cancelMotivoInput.focus();
            }
            if (cancelMotivoError) cancelMotivoError.style.display = 'block';
            return;
        }

        const btnConfirm = document.getElementById('btnConfirmarCancelar');
        const origText = btnConfirm ? btnConfirm.textContent : 'Confirm Cancellation';
        if (btnConfirm) {
            btnConfirm.disabled = true;
            btnConfirm.textContent = 'Cancelling...';
        }

        const csrfInput = document.querySelector('#formCancelarContrato input[name="csrf_token"]') || document.querySelector('input[name="csrf_token"]');
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = (csrfInput && csrfInput.value) || (csrfMeta ? csrfMeta.getAttribute('content') : '');

        try {
            const headers = { 'Content-Type': 'application/json' };
            if (csrfToken) headers['X-CSRFToken'] = csrfToken;

            const res = await fetch(`/api/contratos/${CONTRATO_ID}/cancelar`, {
                method: 'POST',
                headers: headers,
                body: JSON.stringify({ motivo: motivo, csrf_token: csrfToken })
            });

            let data = null;
            const contentType = res.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                data = await res.json();
            }

            if (res.ok && data && data.success) {
                fecharModal('modalCancelarContrato');
                alert(`Contract #${CONTRATO_ID} has been successfully cancelled.`);
                location.reload();
            } else {
                const msg = (data && (data.message || data.error || data.erro)) || `Failed to cancel contract (Status ${res.status}).`;
                alert(msg);
            }
        } catch (err) {
            console.error('Error cancelling contract:', err);
            alert('Connection error while cancelling contract.');
        } finally {
            if (btnConfirm) {
                btnConfirm.disabled = false;
                btnConfirm.textContent = origText;
            }
        }
    }

    if (btnConfirmarCancelar) {
        btnConfirmarCancelar.addEventListener('click', (e) => {
            e.preventDefault();
            executarCancelamentoContrato();
        });
    }

    if (formCancelarContrato) {
        formCancelarContrato.addEventListener('submit', (e) => {
            e.preventDefault();
            executarCancelamentoContrato();
        });
    }

    // Change Weekly Payment Due Day modal logic
    const btnAlterarDiaVenc = document.getElementById('btnAlterarDiaVenc');
    const selectNovoDia = document.getElementById('select_novo_dia_venc');
    const formAlterarDiaVenc = document.getElementById('formAlterarDiaVenc');

    if (btnAlterarDiaVenc) {
        btnAlterarDiaVenc.addEventListener('click', () => {
            const currentDay = btnAlterarDiaVenc.dataset.currentDay !== undefined ? btnAlterarDiaVenc.dataset.currentDay : '0';
            if (selectNovoDia) selectNovoDia.value = currentDay;
            abrirModal('modalAlterarDiaVenc');
        });
    }

    if (formAlterarDiaVenc) {
        formAlterarDiaVenc.addEventListener('submit', async (e) => {
            e.preventDefault();
            const novoDia = selectNovoDia ? selectNovoDia.value : '0';
            const checkAjustar = document.getElementById('check_ajustar_pendentes');
            const ajustar = checkAjustar ? checkAjustar.checked : false;
            const btnSalvar = document.getElementById('btnSalvarDiaVenc');
            const origText = btnSalvar ? btnSalvar.textContent : 'Save Changes';

            const csrfInput = document.querySelector('#formAlterarDiaVenc input[name="csrf_token"]') || document.querySelector('input[name="csrf_token"]');
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            const csrfToken = (csrfInput && csrfInput.value) || (csrfMeta ? csrfMeta.getAttribute('content') : '');

            const headers = { 'Content-Type': 'application/json' };
            if (csrfToken) headers['X-CSRFToken'] = csrfToken;

            if (btnSalvar) {
                btnSalvar.disabled = true;
                btnSalvar.textContent = 'Saving...';
            }

            try {
                const res = await fetch(`/api/contratos/${CONTRATO_ID}/dia-pagamento`, {
                    method: 'PUT',
                    headers: headers,
                    body: JSON.stringify({
                        dia_pagamento_semanal: parseInt(novoDia, 10),
                        ajustar_pendentes: ajustar,
                        csrf_token: csrfToken
                    })
                });

                const data = await res.json();
                if (res.ok) {
                    fecharModal('modalAlterarDiaVenc');
                    alert(data.mensagem || data.message || 'Weekly payment due day updated successfully.');
                    window.location.reload();
                } else {
                    alert(data.erro || data.error || 'Failed to update weekly payment due day.');
                }
            } catch (err) {
                console.error('Error updating payment due day:', err);
                alert('Connection error updating payment due day.');
            } finally {
                if (btnSalvar) {
                    btnSalvar.disabled = false;
                    btnSalvar.textContent = origText;
                }
            }
        });
    }

    // --- Modal de Assinatura Digital Touch (Detalhe Contrato) ---
    let detalheSignaturePad = null;
    const canvasDetalhe = document.getElementById('detalheSignatureCanvas');
    const btnAssinarIniTouch = document.getElementById('btnAssinarInicialTouch');
    const btnAssinarDevTouch = document.getElementById('btnAssinarDevolucaoTouch');
    const inputSigTipo = document.getElementById('detalhe_sig_tipo');
    const titleSig = document.getElementById('detalheSignatureTitle');
    const subTitleSig = document.getElementById('detalheSignatureSubtitle');
    const btnClearDetalheSig = document.getElementById('btnDetalheClearSig');
    const btnSaveDetalheSig = document.getElementById('btnDetalheSaveSig');

    function initDetalheSignaturePad() {
        if (!canvasDetalhe) return;
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        canvasDetalhe.width = canvasDetalhe.offsetWidth * ratio;
        canvasDetalhe.height = canvasDetalhe.offsetHeight * ratio;
        canvasDetalhe.getContext("2d").scale(ratio, ratio);

        if (!detalheSignaturePad && typeof SignaturePad !== 'undefined') {
            detalheSignaturePad = new SignaturePad(canvasDetalhe, {
                backgroundColor: 'rgb(255, 255, 255)',
                penColor: 'rgb(15, 23, 42)',
                minWidth: 1.5,
                maxWidth: 3.5
            });
        } else if (detalheSignaturePad) {
            detalheSignaturePad.clear();
        }
    }

    function abrirAssinaturaTouch(tipo) {
        if (inputSigTipo) inputSigTipo.value = tipo;
        if (tipo === 'devolucao') {
            if (titleSig) titleSig.textContent = 'Return Signature';
            if (subTitleSig) subTitleSig.textContent = 'Sign to confirm motorbike return and deposit hold terms.';
        } else {
            if (titleSig) titleSig.textContent = 'Agreement Signature';
            if (subTitleSig) subTitleSig.textContent = 'Sign to confirm and vehicle collection.';
        }
        abrirModal('modalDetalheSignaturePad');
        setTimeout(() => initDetalheSignaturePad(), 50);
    }

    if (btnAssinarIniTouch) {
        btnAssinarIniTouch.addEventListener('click', () => abrirAssinaturaTouch('inicial'));
    }
    if (btnAssinarDevTouch) {
        btnAssinarDevTouch.addEventListener('click', () => abrirAssinaturaTouch('devolucao'));
    }
    if (btnClearDetalheSig) {
        btnClearDetalheSig.addEventListener('click', () => {
            if (detalheSignaturePad) detalheSignaturePad.clear();
        });
    }

    if (btnSaveDetalheSig) {
        btnSaveDetalheSig.addEventListener('click', async () => {
            if (!detalheSignaturePad || detalheSignaturePad.isEmpty()) {
                alert('Please sign before confirming.');
                return;
            }

            const tipo = inputSigTipo ? inputSigTipo.value : 'inicial';
            const dataUrl = detalheSignaturePad.toDataURL('image/png');
            btnSaveDetalheSig.disabled = true;
            btnSaveDetalheSig.textContent = 'Saving signature...';

            try {
                const res = await fetch(`/api/contratos/${CONTRATO_ID}/assinar`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tipo: tipo,
                        assinatura: dataUrl
                    })
                });

                if (res.ok) {
                    alert('Signature recorded successfully!');
                    window.location.href = window.location.pathname; // Strips ?assinar=1 to prevent reopening
                } else {
                    const d = await res.json();
                    alert(d.message || d.error || 'Failed to save signature.');
                    btnSaveDetalheSig.disabled = false;
                    btnSaveDetalheSig.textContent = '✓ Confirm Signature';
                }
            } catch (err) {
                alert('Connection error while saving signature.');
                btnSaveDetalheSig.disabled = false;
                btnSaveDetalheSig.textContent = '✓ Confirm Signature';
            }
        });
    }

    function imprimirReciboDireto(url) {
        if (!url || url === '#' || url.endsWith('#')) {
            window.print();
            return;
        }

        let iframe = document.getElementById('reciboPrintFrame');
        if (!iframe) {
            iframe = document.createElement('iframe');
            iframe.id = 'reciboPrintFrame';
            iframe.style.position = 'fixed';
            iframe.style.top = '-9999px';
            iframe.style.left = '-9999px';
            iframe.style.width = '10px';
            iframe.style.height = '10px';
            iframe.style.border = 'none';
            iframe.style.opacity = '0';
            iframe.style.pointerEvents = 'none';
            document.body.appendChild(iframe);
        }

        iframe.onload = function() {
            setTimeout(() => {
                try {
                    iframe.contentWindow.focus();
                    iframe.contentWindow.print();
                } catch (err) {
                    console.warn('Iframe direct print failed, opening fallback window:', err);
                    window.open(`${url}?autoprint=1`, '_blank');
                }
            }, 250);
        };

        iframe.src = url;
    }

    const btnPrintRec = document.getElementById('btnPrintReciboContrato');
    if (btnPrintRec) {
        btnPrintRec.addEventListener('click', () => {
            const recLink = document.getElementById('rec_link_page');
            if (recLink && recLink.href && recLink.href !== '#' && !recLink.href.endsWith('#')) {
                imprimirReciboDireto(recLink.href);
            } else {
                window.print();
            }
        });
    }

    // Save Internal Notes Button
    const btnSalvarNotas = document.getElementById('btnSalvarNotasContrato');
    const txtNotas = document.getElementById('contrato_notas_internas');
    const statusNotas = document.getElementById('status_salvar_notas');
    if (btnSalvarNotas && txtNotas) {
        btnSalvarNotas.addEventListener('click', async () => {
            btnSalvarNotas.disabled = true;
            const originalHtml = btnSalvarNotas.innerHTML;
            btnSalvarNotas.innerHTML = '<span>Saving...</span>';
            if (statusNotas) statusNotas.style.display = 'none';

            try {
                const res = await fetch(`/api/contratos/${CONTRATO_ID}/notas`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ notas_internas: txtNotas.value.trim() })
                });
                const resData = await res.json().catch(() => ({}));
                if (res.ok) {
                    if (statusNotas) {
                        statusNotas.textContent = '✓ Internal notes saved successfully!';
                        statusNotas.style.color = '#4ade80';
                        statusNotas.style.display = 'block';
                        setTimeout(() => {
                            if (statusNotas) statusNotas.style.display = 'none';
                        }, 3500);
                    }
                } else {
                    alert(resData.error || resData.erro || 'Failed to update internal notes');
                }
            } catch (err) {
                console.error('Error saving contract notes:', err);
                alert('Connection error. Please try again.');
            } finally {
                btnSalvarNotas.disabled = false;
                btnSalvarNotas.innerHTML = originalHtml;
            }
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeMapping.forEach(([_, modalId]) => fecharModal(modalId));
        }
    });

    // Auto-open signature pad if redirected after contract creation (?assinar=1)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('assinar') === '1') {
        setTimeout(() => {
            abrirAssinaturaTouch('inicial');
        }, 400);
    }
});


