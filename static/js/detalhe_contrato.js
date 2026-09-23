function formatWhatsAppNumber(phone) {
    if (!phone) return '';
    const raw = String(phone).trim();
    
    // 1. If it already starts with '+', keep country code (strip non-digits)
    if (raw.startsWith('+')) {
        return raw.replace(/\D/g, '');
    }
    
    // 2. If it starts with '00' (international prefix)
    if (raw.startsWith('00')) {
        return raw.replace(/\D/g, '').substring(2);
    }
    
    const digits = raw.replace(/\D/g, '');
    
    // 3. If UK number with leading 0 (e.g. 07360469902 -> 447360469902)
    if (digits.startsWith('0')) {
        return '44' + digits.substring(1);
    }
    
    // 4. If UK mobile without leading 0 (e.g. 7360469902 with 10 digits starting with 7 -> 447360469902)
    if (digits.startsWith('7') && digits.length === 10) {
        return '44' + digits;
    }
    
    // 5. If already has 44 prefix (e.g. 447360469902)
    if (digits.startsWith('44') && digits.length >= 11) {
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
                elTel.innerHTML = `
                    <a href="tel:${encodeURIComponent(telVal)}" style="color:var(--text-primary); text-decoration:none; display:inline-flex; align-items:center; gap:6px; transition:color 0.2s;" title="Click to call ${escapeHtml(telVal)}">
                        <span>📞</span> <span style="text-decoration:underline;">${escapeHtml(telVal)}</span>
                    </a>
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
            if (data.telefone) {
                const waNumber = formatWhatsAppNumber(data.telefone);
                const waLink = document.createElement('a');
                waLink.href = `https://wa.me/${waNumber}`;
                waLink.target = '_blank';
                waLink.className = 'btn-action';
                waLink.style.cssText = 'flex: 1; text-align: center; background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); font-size: 0.8rem; padding: 6px 10px; text-decoration: none; border-radius: 6px; display: inline-flex; align-items: center; justify-content: center; gap: 4px;';
                waLink.innerHTML = '<span>💬 WhatsApp</span>';
                linksCliente.appendChild(waLink);
            }
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
                        vencimento_tax: data.vencimento_tax
                    });
                }
            };
        }
        document.getElementById('info_modelo_cor').textContent = `${modeloVal} • ${corVal}`;
        
        if (data.data_retirada) {
            document.getElementById('info_data_retirada').textContent = 'Collection: ' + new Date(data.data_retirada).toLocaleDateString('en-GB');
        }

        // V5C & GPS Trackers Shortcuts
        const badgeV5C = document.getElementById('badge_v5c_count');
        if (badgeV5C) {
            badgeV5C.textContent = (data.v5c_count !== undefined && data.v5c_count !== null) ? data.v5c_count : 0;
        }
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
                        vencimento_tax: data.vencimento_tax
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
                        vencimento_tax: data.vencimento_tax
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
                    const bV5C = document.getElementById('badge_v5c_count');
                    const bTrk = document.getElementById('badge_trackers_count');
                    if (bV5C) bV5C.textContent = (d.v5c_arquivos || []).length;
                    if (bTrk) bTrk.textContent = (d.trackers || []).length;
                }
            } catch(err) {
                console.error('Error refreshing vehicle badges:', err);
            }
        };

        // Mileage Tracker
        const isVendaContrato = (data.tipo_contrato === 'Sale_Full' || data.tipo_contrato === 'Sale_Installment');
        const labelStartMileage = document.getElementById('label_milhagem_inicial');
        if (labelStartMileage) {
            labelStartMileage.textContent = isVendaContrato ? 'Sale Mileage:' : 'Start Mileage:';
        }
        const elStartMileage = document.getElementById('info_milhagem_inicial');
        if (elStartMileage) {
            elStartMileage.textContent = (data.milhagem_inicial !== undefined && data.milhagem_inicial !== null) ? `${data.milhagem_inicial.toLocaleString('en-GB')} miles` : '0 miles';
        }
        const rowEndMileage = document.getElementById('row_milhagem_final');
        const elEndMileage = document.getElementById('info_milhagem_final');
        if (rowEndMileage) {
            if (isVendaContrato) {
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
            if (!isVendaContrato && data.milhas_rodadas !== undefined && data.milhas_rodadas !== null) {
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
        const taxEval = evaluateCompliance(data.vencimento_tax);
        const motEval = evaluateCompliance(data.vencimento_mot);

        const motTaxBox = document.getElementById('info_mot_tax');
        if (motTaxBox) {
            motTaxBox.innerHTML = renderComplianceRow('Road Tax Expiry', taxEval) + renderComplianceRow('MOT Expiry', motEval);
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

            // Include Insurance status in top banner (only for rentals, sales don't monitor 15-day insurance)
            const isVendaContrato = (data.tipo_contrato === 'Sale_Full' || data.tipo_contrato === 'Sale_Installment');
            if (!isVendaContrato) {
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

        if (isVenda) {
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
                if (data.status_seguro === 'Cancelled') {
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
        
        if (data.tipo_contrato === 'Sale_Full') {
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
        const stLower = (data.status || '').toLowerCase();
        if (stLower === 'active' || stLower === 'ativo') statusBadge = '<span class="badge badge-success">ACTIVE</span>';
        else if (stLower === 'deposit_hold' || stLower === 'quarentena_deposito') statusBadge = '<span class="badge badge-warning">DEPOSIT HOLD</span>';
        else if (stLower === 'completed' || stLower === 'finalizado') statusBadge = '<span class="badge badge-secondary">COMPLETED</span>';
        else if (stLower === 'cancelled' || stLower === 'cancelado') statusBadge = '<span class="badge" style="background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); font-weight: 700;">CANCELLED</span>';
        else statusBadge = `<span class="badge badge-info">${(data.status || '').toUpperCase()}</span>`;
        document.getElementById('info_status').innerHTML = statusBadge;

        // isVenda already declared above
        const blocoAluguel = document.getElementById('bloco_termos_aluguel');
        const blocoVenda = document.getElementById('bloco_termos_venda');

        if (isVenda) {
            if (blocoAluguel) blocoAluguel.style.display = 'none';
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

            const valAluguel = data.valor_aluguel_semanal ? formatoMoeda.format(data.valor_aluguel_semanal) : '-';
            const elAluguel = document.getElementById('info_aluguel');
            if (elAluguel) elAluguel.textContent = `${valAluguel} / week`;

            const diaVencTexto = (data.dia_pagamento_semanal !== undefined && data.dia_pagamento_semanal !== null) 
                ? (diasSemana[data.dia_pagamento_semanal] || `Day ${data.dia_pagamento_semanal}`)
                : '-';
            const elDiaVenc = document.getElementById('info_dia_venc');
            if (elDiaVenc) elDiaVenc.textContent = diaVencTexto;
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
        
        // Button Complete Contract (Only for rentals, not sales)
        const btnFinalizar = document.getElementById('btnFinalizarContrato');
        if (btnFinalizar) {
            if ((stLower === 'active' || stLower === 'ativo') && !isVenda) {
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

        if (boxDep && depOriginal > 0) {
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
        if (isVenda) {
            if (contratoTituloTipo) contratoTituloTipo.textContent = '📄 Vehicle Sale Agreement & Signatures';
            if (labelSigIni) labelSigIni.textContent = '1. Buyer Agreement Signature';
        }

        const badgeSigIni = document.getElementById('badge_sig_inicial');
        const boxSigIniContent = document.getElementById('box_sig_inicial_content');
        const btnAssinarIni = document.getElementById('btnAssinarInicialTouch');

        if (data.assinatura_cliente_inicial) {
            if (badgeSigIni) {
                badgeSigIni.textContent = 'Signed';
                badgeSigIni.className = 'badge badge-success';
            }
            if (boxSigIniContent) {
                const dataAssina = data.data_assinatura_inicial_uk || data.data_assinatura_inicial || '';
                boxSigIniContent.innerHTML = `
                    <img src="${data.assinatura_cliente_inicial}" alt="Client Signature" style="max-height: 60px; max-width: 180px; object-fit: contain; margin-bottom: 4px;">
                    <span style="font-size: 0.72rem; color: #4ade80; font-weight: 600;">✓ Digitally Signed on ${dataAssina}</span>
                `;
            }
            if (btnAssinarIni) btnAssinarIni.style.display = 'none';
        } else {
            if (badgeSigIni) {
                badgeSigIni.textContent = 'Pending Signature';
                badgeSigIni.className = 'badge badge-warning';
            }
            if (boxSigIniContent) {
                boxSigIniContent.innerHTML = `
                    <span style="color: var(--text-secondary); font-size: 0.85rem;">Client signature pending for ${isVenda ? 'vehicle purchase agreement' : 'start of rental'}.</span>
                `;
            }
            if (btnAssinarIni) btnAssinarIni.style.display = 'inline-flex';
        }

        const cardSigDev = document.getElementById('card_sig_devolucao');
        if (cardSigDev) {
            cardSigDev.style.display = isVenda ? 'none' : 'block';
        }

        const badgeSigDev = document.getElementById('badge_sig_devolucao');
        const boxSigDevContent = document.getElementById('box_sig_devolucao_content');
        const btnAssinarDev = document.getElementById('btnAssinarDevolucaoTouch');

        if (data.assinatura_cliente_devolucao) {
            if (badgeSigDev) {
                badgeSigDev.textContent = 'Signed';
                badgeSigDev.className = 'badge badge-success';
            }
            if (boxSigDevContent) {
                const dataAssinaDev = data.data_assinatura_devolucao_uk || data.data_assinatura_devolucao || '';
                boxSigDevContent.innerHTML = `
                    <img src="${data.assinatura_cliente_devolucao}" alt="Return Signature" style="max-height: 60px; max-width: 180px; object-fit: contain; margin-bottom: 4px;">
                    <span style="font-size: 0.72rem; color: #4ade80; font-weight: 600;">✓ Return Signed on ${dataAssinaDev}</span>
                `;
            }
            if (btnAssinarDev) btnAssinarDev.style.display = 'none';
        } else {
            if (stLower === 'deposit_hold' || stLower === 'quarentena_deposito' || isCompleted) {
                if (badgeSigDev) {
                    badgeSigDev.textContent = 'Pending Return Signature';
                    badgeSigDev.className = 'badge badge-warning';
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
        const anexos = data.anexos || [];

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
        
        // 4. Financial Statement
        const tbody = document.querySelector('#extratoTable tbody');
        tbody.innerHTML = '';
        
        let totalPendente = 0;
        let totalPago = 0;

        if (!data.transacoes || data.transacoes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:2rem; color:var(--text-secondary);">No charges recorded for this contract.</td></tr>';
        } else {
            const hoje = new Date();
            hoje.setHours(0, 0, 0, 0);

            data.transacoes.forEach(t => {
                const tr = document.createElement('tr');
                
                const dataVencObj = t.data_vencimento ? new Date(t.data_vencimento) : null;
                const vencZero = dataVencObj ? new Date(dataVencObj.getFullYear(), dataVencObj.getMonth(), dataVencObj.getDate()) : null;
                const dataVenc = dataVencObj ? dataVencObj.toLocaleDateString('en-GB') : '-';
                
                const tStatusLower = (t.status || '').toLowerCase();
                const tipoLower = (t.tipo || '').toLowerCase();
                const isPaid = tStatusLower === 'paid' || tStatusLower === 'pago';
                const isPending = tStatusLower === 'pending' || tStatusLower === 'pendente';
                const isVencido = isPending && vencZero && vencZero < hoje;

                const dataPag = t.data_pagamento ? new Date(t.data_pagamento).toLocaleDateString('en-GB') : '-';
                
                if (isPaid && tipoLower !== 'deposit_refund' && tipoLower !== 'devolucao_deposito') {
                    totalPago += t.valor;
                } else if (isPending) {
                    totalPendente += t.valor;
                }

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
                else tipoBadge = `<span class="badge">${t.tipo}</span>`;

                let acoesHtml = '';
                if (isPending) {
                    acoesHtml = `
                        <div style="display:flex; gap:6px; justify-content:flex-end; align-items:center;">
                            <button class="btn-action btn-pagar" data-id="${t.id}" data-tipo="${t.tipo}" data-valor="${t.valor}" style="background:var(--success); padding:4px 10px; font-size:0.8rem;">
                                Pay
                            </button>
                            <button class="btn-action btn-remover" data-id="${t.id}" style="background:rgba(239, 68, 68, 0.15); color:#f87171; border:1px solid rgba(239, 68, 68, 0.3); padding:4px 8px; font-size:0.8rem;">
                                Delete
                            </button>
                        </div>
                    `;
                } else if (isPaid) {
                    const descFinal = t.descricao || formatarDescricaoTransacao(t.tipo);
                    acoesHtml = `
                        <div style="display:flex; gap:6px; justify-content:flex-end; align-items:center;">
                            <button class="btn-action btn-recibo" data-id="${t.id}" data-tipo="${t.tipo}" data-descricao="${descFinal}" data-valor="${t.valor.toFixed(2)}" data-forma="${t.forma_pagamento || '-'}" data-data="${t.data_pagamento || '-'}" style="background:rgba(255,255,255,0.06); border:1px solid var(--border-color); color:var(--text-primary); padding:4px 10px; font-size:0.8rem;" title="View Receipt">
                                🧾 Receipt
                            </button>
                            <button class="btn-action btn-reverter-pagamento" data-id="${t.id}" data-tipo="${t.tipo}" data-valor="${t.valor.toFixed(2)}" style="background:rgba(239, 68, 68, 0.12); border:1px solid rgba(239, 68, 68, 0.3); color:#f87171; padding:4px 9px; font-size:0.8rem; border-radius:6px; cursor:pointer;" title="Cancel payment and return to Pending">
                                ↩ Cancel / Revert
                            </button>
                        </div>
                    `;
                }

                let celulaPagamento = `<span style="color:var(--text-secondary); opacity:0.5;">-</span>`;
                if (isPaid) {
                    const isDepositDeduction = t.forma_pagamento === 'Deposit';
                    const formaLabel = isDepositDeduction ? 'Deposit (Deduction)' : (t.forma_pagamento || '');
                    const colorStyle = isDepositDeduction ? 'color:#60a5fa; font-weight:600;' : 'color:var(--text-secondary);';
                    const staffHtml = t.registrado_por_nome ? `<span style="display:block; font-size:0.7rem; color:#c084fc; margin-top:2px;">👤 ${escapeHtml(t.registrado_por_nome)}</span>` : '';
                    celulaPagamento = `<span>${dataPag} <small style="${colorStyle} display:block; font-size:0.75rem;">${escapeHtml(formaLabel)}</small>${staffHtml}</span>`;
                }

                let celulaVencimento = `<span>${dataVenc}</span>`;
                if (isVencido) {
                    celulaVencimento = `<span style="color:#f87171; font-weight:600;">${dataVenc} ⚠️</span>`;
                }

                tr.innerHTML = `
                    <td>${tipoBadge}</td>
                    <td style="font-weight:700; font-size:0.95rem; color:var(--text-primary);">${formatoMoeda.format(t.valor)}</td>
                    <td>${celulaVencimento}</td>
                    <td>${celulaPagamento}</td>
                    <td>${statusBadge}</td>
                    <td style="text-align: right; white-space: nowrap;">${acoesHtml}</td>
                `;
                tbody.appendChild(tr);
            });
            
            // Statement Summary Header
            const resumoExtrato = document.getElementById('resumoExtrato');
            if (resumoExtrato) {
                let depSummary = '';
                if (depOriginal > 0) {
                    depSummary = ` &bull; Deposit Balance: <strong style="color:${isCompleted ? 'var(--text-secondary)' : 'var(--success)'};">${formatoMoeda.format(depSaldo)}</strong>`;
                }
                resumoExtrato.innerHTML = `&bull; Pending: <strong style="color:${totalPendente > 0 ? '#f87171' : 'var(--text-primary)'};">${formatoMoeda.format(totalPendente)}</strong> &bull; Total Paid: <strong style="color:var(--success);">${formatoMoeda.format(totalPago)}</strong>${depSummary}`;
            }

            // Pay Modal Logic
            document.querySelectorAll('.btn-pagar').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const b = e.target.closest('button');
                    const cobId = b.getAttribute('data-id');
                    const tipo = b.getAttribute('data-tipo');
                    const valor = parseFloat(b.getAttribute('data-valor')) || 0;

                    document.getElementById('pag_cobranca_id').value = cobId;
                    document.getElementById('pag_desc_tipo').textContent = tipo;
                    document.getElementById('pag_desc_valor').textContent = formatoMoeda.format(valor);
                    abrirModal('pagamentoModal');
                });
            });
            
            // Receipt Modal Logic
            document.querySelectorAll('.btn-recibo').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const b = e.target.closest('button');
                    const id = b.getAttribute('data-id');
                    const tipo = b.getAttribute('data-tipo');
                    const descricao = b.getAttribute('data-descricao') || formatarDescricaoTransacao(tipo);
                    const valor = parseFloat(b.getAttribute('data-valor')) || 0;
                    const forma = b.getAttribute('data-forma') || 'Not specified';
                    const dataStr = b.getAttribute('data-data');

                    document.getElementById('rec_id').textContent = `#${id}`;
                    document.getElementById('rec_contrato_id').textContent = `Contract #${CONTRATO_ID}`;
                    document.getElementById('rec_cliente').textContent = data.cliente || '-';
                    document.getElementById('rec_placa').textContent = data.placa || '-';
                    document.getElementById('rec_tipo').textContent = descricao;
                    document.getElementById('rec_valor').textContent = formatoMoeda.format(valor);
                    document.getElementById('rec_forma').textContent = forma;
                    document.getElementById('rec_data').textContent = dataStr && dataStr !== '-' ? new Date(dataStr).toLocaleString('en-GB') : '-';

                    const recLink = document.getElementById('rec_link_page');
                    if (recLink) recLink.href = `/recibo/${id}`;

                    abrirModal('reciboModal');
                });
            });

            // Revert / Cancel Payment Logic
            document.querySelectorAll('.btn-reverter-pagamento').forEach(btn => {
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

            // Delete Charge Logic
            document.querySelectorAll('.btn-remover').forEach(btn => {
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
        }
        
        // 5. Recorded Inspections
        const vistContainer = document.getElementById('vistoriasList');
        vistContainer.innerHTML = '';
        
        if (!data.vistorias || data.vistorias.length === 0) {
            vistContainer.innerHTML = '<p style="color: var(--text-secondary); text-align: center; padding: 2rem 0;">No inspections recorded for this contract.</p>';
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

                const div = document.createElement('div');
                div.style.cssText = "background: rgba(15, 23, 42, 0.4); border: 1px solid var(--border-color); padding: 0.875rem 1rem; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; gap: 10px;";
                div.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 4px; min-width: 0;">
                        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                            ${tBadge}
                            <span style="font-size: 0.8rem; color: var(--text-secondary);">${dataVist}</span>
                            ${v.milhagem != null ? `<span style="font-size: 0.75rem; color: #fbbf24; font-weight: 600;">&bull; ⏱️ ${v.milhagem} mi</span>` : ''}
                            ${v.realizado_por_nome ? `<span style="font-size: 0.75rem; color: #c084fc;">&bull; 👤 ${escapeHtml(v.realizado_por_nome)}</span>` : ''}
                        </div>
                        <div style="font-size: 0.85rem; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px;">
                            ${escapeHtml(v.observacoes) || '<em style="opacity:0.5;">No notes</em>'}
                        </div>
                    </div>
                    <button class="btn-action btn-ver-foto" data-tipo="${escapeHtml(v.tipo)}" data-data="${dataVist}" data-foto="${v.foto_url || ''}" data-mil="${v.milhagem != null ? v.milhagem : ''}" data-obs="${escapeHtml(v.observacoes || 'No notes.')}" style="padding: 6px 12px; font-size: 0.8rem; white-space: nowrap;">
                        ${fotosLabel}
                    </button>
                `;
                vistContainer.appendChild(div);
            });
            
            // View Inspection Photos (Modal)
            document.querySelectorAll('.btn-ver-foto').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const b = e.target.closest('button');
                    const fotosCsv = b.getAttribute('data-foto');
                    const obs = b.getAttribute('data-obs');
                    const tipo = b.getAttribute('data-tipo');
                    const dataStr = b.getAttribute('data-data');
                    const milhagem = b.getAttribute('data-mil');
                    
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
        
        // 6. Setup forms and modals
        
        // Add Charge Form
        document.getElementById('btnLancCob')?.addEventListener('click', () => {
            document.getElementById('cob_data').value = new Date().toISOString().split('T')[0];
            abrirModal('cobrancaModal');
        });
        
        document.getElementById('cobrancaForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('btnSalvarCob');
            btn.disabled = true;
            btn.textContent = 'Adding...';

            const payload = {
                tipo: document.getElementById('cob_tipo').value,
                valor: document.getElementById('cob_valor').value,
                data_vencimento: document.getElementById('cob_data').value
            };
            try {
                const res = await fetch(`/api/contratos/${CONTRATO_ID}/cobrancas`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
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
                btn.textContent = 'Add Charge';
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

        function resetOcPhotos() {
            ocSelectedPhotos = [];
            if (ocCameraInput) ocCameraInput.value = '';
            if (ocGalleryInput) ocGalleryInput.value = '';
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

        // New Incident Button
        document.getElementById('btnNovaOcorr')?.addEventListener('click', () => {
            document.getElementById('ocorrenciaModalTitle').textContent = 'New Inspection (Incident)';
            document.getElementById('oc_tipo').value = 'Incident';
            resetOcPhotos();
            abrirModal('ocorrenciaModal');
        });

        // Submit Incident Form
        document.getElementById('ocorrenciaForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (ocSelectedPhotos.length === 0) {
                alert('Please take or select at least one vehicle photo.');
                return;
            }

            const btn = document.getElementById('btnSalvarOcorr');
            btn.disabled = true;
            btn.textContent = 'Processing photos...';

            const formData = new FormData();
            formData.append('id_contrato', CONTRATO_ID);
            formData.append('tipo', document.getElementById('oc_tipo').value);
            const ocMilhagem = document.getElementById('oc_milhagem');
            if (ocMilhagem && ocMilhagem.value) {
                formData.append('milhagem', ocMilhagem.value);
            }
            formData.append('observacoes', document.getElementById('oc_obs').value);
            
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
            const forma = document.getElementById('pag_forma').value;
            const btn = document.getElementById('btnSubmitPag');
            
            btn.disabled = true;
            btn.textContent = 'Processing...';

            try {
                const res = await fetch(`/api/financeiro/pagar/${cobId}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ forma_pagamento: forma })
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
                btn.textContent = 'Confirm Payment';
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
        ['closeOcorrenciaModal', 'ocorrenciaModal'],
        ['closePagamentoModal', 'pagamentoModal'],
        ['closeReciboModal', 'reciboModal'],
        ['closeDevolverDepositoModal', 'devolverDepositoModal'],
        ['closeAnexosModal', 'modalAnexosContrato'],
        ['closeDetalheSignatureModal', 'modalDetalheSignaturePad'],
        ['btnDetalheCancelSig', 'modalDetalheSignaturePad'],
        ['closeCancelarModal', 'modalCancelarContrato'],
        ['btnCancelDismiss', 'modalCancelarContrato']
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


