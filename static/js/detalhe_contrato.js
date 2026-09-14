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
        document.getElementById('info_cliente').textContent = data.cliente || '-';
        
        const elTel = document.getElementById('info_tel');
        if (elTel) {
            if (data.telefone) {
                elTel.innerHTML = `
                    <a href="tel:${data.telefone}" style="color:var(--text-primary); text-decoration:none; display:inline-flex; align-items:center; gap:6px; transition:color 0.2s;" title="Click to call ${data.telefone}">
                        <span>📞</span> <span style="text-decoration:underline;">${data.telefone}</span>
                    </a>
                `;
            } else {
                elTel.innerHTML = '<span>📞 No phone</span>';
            }
        }
        
        const elEmail = document.getElementById('info_email');
        if (elEmail) {
            if (data.email) {
                elEmail.innerHTML = `
                    <a href="mailto:${data.email}" style="color:#60a5fa; text-decoration:underline; word-break:break-all; display:inline-flex; align-items:center; gap:6px;" title="Send email to ${data.email}">
                        <span>✉️</span> <span>${data.email}</span>
                    </a>
                `;
            } else {
                elEmail.innerHTML = '<span>✉️ No email</span>';
            }
        }
        
        const elEndereco = document.getElementById('info_endereco');
        if (elEndereco) {
            if (data.endereco) {
                const mapQuery = encodeURIComponent(data.endereco);
                elEndereco.innerHTML = `
                    <a href="https://www.google.com/maps/search/?api=1&query=${mapQuery}" target="_blank" style="color:var(--text-primary); text-decoration:none; display:flex; justify-content:space-between; align-items:flex-start; gap:8px;" title="Open in Google Maps">
                        <span>${escapeHtml(data.endereco)}</span>
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
        document.getElementById('info_placa').textContent = data.placa || '-';
        document.getElementById('info_modelo_cor').textContent = `${data.modelo || '-'} • ${data.cor || '-'}`;
        
        if (data.data_retirada) {
            document.getElementById('info_data_retirada').textContent = 'Collection: ' + new Date(data.data_retirada).toLocaleDateString('en-GB');
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

            // Include Insurance status in top banner
            if (data.status_seguro === 'Cancelled') {
                expiredList.push('Motor Insurance (FLAGGED CANCELLED ON askMID)');
            } else if (data.checagem_seguro_devida) {
                warningList.push(`15-day askMID Insurance Check Due (${data.dias_desde_checagem_seguro}d since last check)`);
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
        
        // 3. 15-Day askMID Insurance Compliance Rendering
        const badgeSeguro = document.getElementById('badge_status_seguro');
        const boxSeguro = document.getElementById('box_seguro_compliance');
        const dataVerifEl = document.getElementById('info_seguro_data_verif');
        const proxVerifEl = document.getElementById('info_seguro_proxima_verif');
        const verifPorEl = document.getElementById('info_seguro_verificado_por');
        const verifPorRow = document.getElementById('info_seguro_verif_por_row');

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

        const btnReportarSeguroCancelado = document.getElementById('btnReportarSeguroCancelado');
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
        
        const infoSeguro = document.getElementById('info_seguro');
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
        
        // 3. Contract Card
        let statusBadge = '';
        const stLower = (data.status || '').toLowerCase();
        if (stLower === 'active' || stLower === 'ativo') statusBadge = '<span class="badge badge-success">ACTIVE</span>';
        else if (stLower === 'deposit_hold' || stLower === 'quarentena_deposito') statusBadge = '<span class="badge badge-warning">DEPOSIT HOLD</span>';
        else if (stLower === 'completed' || stLower === 'finalizado') statusBadge = '<span class="badge badge-secondary">COMPLETED</span>';
        else statusBadge = `<span class="badge badge-info">${(data.status || '').toUpperCase()}</span>`;
        document.getElementById('info_status').innerHTML = statusBadge;

        const valAluguel = data.valor_aluguel_semanal ? formatoMoeda.format(data.valor_aluguel_semanal) : '-';
        document.getElementById('info_aluguel').textContent = `${valAluguel} / week`;

        const diaVencTexto = (data.dia_pagamento_semanal !== undefined && data.dia_pagamento_semanal !== null) 
            ? (diasSemana[data.dia_pagamento_semanal] || `Day ${data.dia_pagamento_semanal}`)
            : '-';
        document.getElementById('info_dia_venc').textContent = diaVencTexto;
        
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
        
        // Button Complete Contract
        const btnFinalizar = document.getElementById('btnFinalizarContrato');
        if (btnFinalizar) {
            if (stLower === 'active' || stLower === 'ativo') {
                btnFinalizar.style.display = 'inline-flex';
                btnFinalizar.addEventListener('click', () => {
                    document.getElementById('ocorrenciaModalTitle').textContent = 'Complete Contract (Check-in Inspection)';
                    document.getElementById('oc_tipo').value = 'Check-in';
                    if (typeof resetOcPhotos === 'function') resetOcPhotos();
                    abrirModal('ocorrenciaModal');
                });
            } else {
                btnFinalizar.style.display = 'none';
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
                const dataVenc = dataVencObj ? dataVencObj.toLocaleDateString('en-GB') : '-';
                
                const tStatusLower = (t.status || '').toLowerCase();
                const tipoLower = (t.tipo || '').toLowerCase();
                const isPaid = tStatusLower === 'paid' || tStatusLower === 'pago';
                const isPending = tStatusLower === 'pending' || tStatusLower === 'pendente';
                const isVencido = isPending && dataVencObj && dataVencObj < hoje;

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
                    acoesHtml = `
                        <div style="display:flex; gap:6px; justify-content:flex-end; align-items:center;">
                            <button class="btn-action btn-recibo" data-id="${t.id}" data-tipo="${t.tipo}" data-valor="${t.valor.toFixed(2)}" data-forma="${t.forma_pagamento || '-'}" data-data="${t.data_pagamento || '-'}" style="background:rgba(255,255,255,0.06); border:1px solid var(--border-color); color:var(--text-primary); padding:4px 10px; font-size:0.8rem;" title="View Receipt">
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
                    celulaPagamento = `<span>${dataPag} <small style="${colorStyle} display:block; font-size:0.75rem;">${formaLabel}</small>${staffHtml}</span>`;
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
                    const valor = parseFloat(b.getAttribute('data-valor')) || 0;
                    const forma = b.getAttribute('data-forma') || 'Not specified';
                    const dataStr = b.getAttribute('data-data');

                    document.getElementById('rec_id').textContent = `#${id}`;
                    document.getElementById('rec_contrato_id').textContent = `Contract #${CONTRATO_ID}`;
                    document.getElementById('rec_cliente').textContent = data.cliente || '-';
                    document.getElementById('rec_placa').textContent = data.placa || '-';
                    document.getElementById('rec_tipo').textContent = tipo;
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
                            ${v.realizado_por_nome ? `<span style="font-size: 0.75rem; color: #c084fc;">&bull; 👤 ${escapeHtml(v.realizado_por_nome)}</span>` : ''}
                        </div>
                        <div style="font-size: 0.85rem; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px;">
                            ${v.observacoes || '<em style="opacity:0.5;">No notes</em>'}
                        </div>
                    </div>
                    <button class="btn-action btn-ver-foto" data-tipo="${v.tipo}" data-data="${dataVist}" data-foto="${v.foto_url || ''}" data-obs="${v.observacoes || 'No notes.'}" style="padding: 6px 12px; font-size: 0.8rem; white-space: nowrap;">
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
                    
                    const tLower = (tipo || '').toLowerCase();
                    document.getElementById('modalVistoriaTipo').innerHTML = (
                        tLower === 'check-out' || tLower === 'saída' ? '<span class="badge badge-info">Check-out</span>' :
                        tLower === 'check-in' || tLower === 'entrada' ? '<span class="badge badge-warning">Check-in</span>' :
                        '<span class="badge badge-danger">Incident</span>'
                    );
                    document.getElementById('modalVistoriaData').textContent = dataStr;
                    document.getElementById('vistoria_obs').textContent = obs;
                    
                    const galeria = document.getElementById('vistoria_galeria');
                    galeria.innerHTML = '';
                    
                    if (fotosCsv) {
                        const fotos = fotosCsv.split(',').map(f => f.trim()).filter(Boolean);
                        if (fotos.length > 0) {
                            fotos.forEach((url, i) => {
                                const a = document.createElement('a');
                                a.href = url;
                                a.target = '_blank';
                                a.className = 'photo-item';
                                a.title = `Photo ${i + 1} - Click to enlarge`;
                                a.innerHTML = `<img src="${url}" alt="Photo ${i + 1}"><span class="photo-zoom-icon">&#x1F50D; Enlarge</span>`;
                                galeria.appendChild(a);
                            });
                        } else {
                            galeria.innerHTML = '<p style="color:var(--text-secondary); font-size:0.85rem; grid-column:1/-1;">No photos attached.</p>';
                        }
                    } else {
                        galeria.innerHTML = '<p style="color:var(--text-secondary); font-size:0.85rem; grid-column:1/-1;">No photos attached.</p>';
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
        ['closeDevolverDepositoModal', 'devolverDepositoModal']
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
});


