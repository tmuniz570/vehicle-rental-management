function formatWhatsAppNumber(phone) {
    if (!phone) return '';
    const raw = String(phone).trim();
    if (raw.startsWith('+')) return raw.replace(/\D/g, '');
    if (raw.startsWith('00')) return raw.replace(/\D/g, '').substring(2);
    const digits = raw.replace(/\D/g, '');
    if (digits.startsWith('0')) return '44' + digits.substring(1);
    if (digits.startsWith('7') && digits.length === 10) return '44' + digits;
    if (digits.startsWith('44') && digits.length >= 11) return digits;
    return digits;
}

let paginaAtual = 1;
let termoBusca = '';
let sortCol = 'id';
let sortOrder = 'desc';

async function carregarClientes() {
    const tbody = document.querySelector('#clientesTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    
    try {
        const res = await fetch(`/api/clientes?page=${paginaAtual}&limit=20&search=${encodeURIComponent(termoBusca)}&sort_by=${encodeURIComponent(sortCol)}&sort_order=${encodeURIComponent(sortOrder)}`);
        const data = await res.json();
        const clientes = data.itens || [];
        
        if (clientes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No customers found.</td></tr>';
            if(paginationInfo) paginationInfo.textContent = '';
            return;
        }
        
        tbody.innerHTML = '';
        clientes.forEach(c => {
            const tr = document.createElement('tr');
            
            const docs = [];
            if(c.url_habilitacao) docs.push(`<a href="${c.url_habilitacao}" target="_blank" style="color:var(--accent); text-decoration:none;" title="Driving Licence Front">🪪 Front</a>`);
            if(c.url_habilitacao_verso) docs.push(`<a href="${c.url_habilitacao_verso}" target="_blank" style="color:var(--accent); text-decoration:none;" title="Driving Licence Back">🪪 Back</a>`);
            if(c.url_cbt) docs.push(`<a href="${c.url_cbt}" target="_blank" style="color:var(--success); text-decoration:none;" title="CBT Certificate">📜 CBT</a>`);
            if(c.url_comprovante_endereco) docs.push(`<a href="${c.url_comprovante_endereco}" target="_blank" style="color:#c084fc; text-decoration:none;" title="Proof of Address">🏠 Address</a>`);
            const docsHtml = docs.length > 0 ? docs.join('<br>') : '-';
            
            const emailVal = c.email || '';
            const btnEdit = `<button class="btn-edit" data-id="${c.id}" data-nome="${escapeHtml(c.nome || '')}" data-tel="${escapeHtml(c.telefone || '')}" data-email="${escapeHtml(emailVal)}" data-endereco="${escapeHtml(c.endereco || '')}" style="background:transparent; color:var(--accent); border:1px solid var(--accent); padding:10px 15px; min-width:60px; min-height:44px; border-radius:6px; cursor:pointer;">Edit</button>`;
            
            const waNum = formatWhatsAppNumber(c.telefone);
            const telHtml = waNum 
                ? `<a href="https://wa.me/${waNum}" target="_blank" style="color:var(--text-primary); text-decoration:none; display:inline-flex; align-items:center; gap:5px;" title="Chat with ${escapeHtml(c.nome)} on WhatsApp">💬 ${escapeHtml(c.telefone)}</a>`
                : escapeHtml(c.telefone || '-');
            
            const emailHtml = c.email 
                ? `<a href="mailto:${encodeURIComponent(c.email)}" style="color:var(--text-primary); text-decoration:none;" title="Send email">${escapeHtml(c.email)}</a>`
                : `<span style="color:var(--text-secondary);">-</span>`;

            tr.innerHTML = `
                <td class="nowrap"><span style="font-weight:700; color:var(--accent); background:rgba(217,119,6,0.12); border:1px solid rgba(217,119,6,0.25); padding:3px 8px; border-radius:6px; font-size:0.85rem;">#${c.id}</span></td>
                <td><strong>${escapeHtml(c.nome)}</strong></td>
                <td class="nowrap">${telHtml}</td>
                <td>${emailHtml}</td>
                <td class="cell-wrap">${escapeHtml(c.endereco) || '-'}</td>
                <td>${docsHtml || '-'}</td>
                <td>${btnEdit}</td>
            `;
            tbody.appendChild(tr);
        });

        // Update pagination UI
        if(paginationInfo) {
            paginationInfo.textContent = `Page ${data.pagina_atual} of ${data.paginas} (${data.total} records)`;
        }
        const btnPrev = document.getElementById('btnPrevPage');
        const btnNext = document.getElementById('btnNextPage');
        if(btnPrev) btnPrev.disabled = data.pagina_atual <= 1;
        if(btnNext) btnNext.disabled = data.pagina_atual >= data.paginas;
        
        // Setup Edit Modal Events
        const modal = document.getElementById('editClientModal');
        document.querySelectorAll('.btn-edit').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetBtn = e.target.closest('.btn-edit');
                if (!targetBtn) return;
                document.getElementById('edit_id').value = targetBtn.getAttribute('data-id') || '';
                document.getElementById('edit_nome').value = targetBtn.getAttribute('data-nome') || '';
                document.getElementById('edit_telefone').value = targetBtn.getAttribute('data-tel') || '';
                document.getElementById('edit_email').value = targetBtn.getAttribute('data-email') || '';
                document.getElementById('edit_endereco').value = targetBtn.getAttribute('data-endereco') || '';
                
                // Clear file inputs
                ['edit_habilitacao', 'edit_habilitacao_verso', 'edit_cbt', 'edit_comprovante_endereco'].forEach(fId => {
                    const el = document.getElementById(fId);
                    if (el) el.value = '';
                });

                if (modal) modal.classList.add('active');
            });
        });
        if (typeof setTableSortIndicator === 'function') {
            setTableSortIndicator('clientesTable', sortCol, sortOrder);
        }
        
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--error);">Error loading customers.</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (typeof enableTableSorting === 'function') {
        enableTableSorting('clientesTable', (field, order) => {
            sortCol = field;
            sortOrder = order;
            paginaAtual = 1;
            carregarClientes();
        });
    }

    carregarClientes();
    
    // Pagination Buttons
    const btnPrev = document.getElementById('btnPrevPage');
    const btnNext = document.getElementById('btnNextPage');
    if(btnPrev) btnPrev.addEventListener('click', () => { paginaAtual--; carregarClientes(); });
    if(btnNext) btnNext.addEventListener('click', () => { paginaAtual++; carregarClientes(); });

    // Search logic with debounce
    const searchInput = document.getElementById('searchInput');
    let timeoutId;
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                termoBusca = e.target.value;
                paginaAtual = 1;
                carregarClientes();
            }, 500);
        });
    }

    const modal = document.getElementById('editClientModal');
    const closeBtn = document.getElementById('closeClientModal');
    
    function fecharModalCliente() {
        if (modal) modal.classList.remove('active');
    }

    if(closeBtn) closeBtn.addEventListener('click', fecharModalCliente);
    if(modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) fecharModalCliente();
        });
    }
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal && modal.classList.contains('active')) {
            fecharModalCliente();
        }
    });

    const editForm = document.getElementById('editClientForm');
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('edit_id').value;
            const submitBtn = document.getElementById('btnSalvarCliente') || editForm.querySelector('button[type="submit"]');
            const originalBtnText = submitBtn ? submitBtn.textContent : 'Save Changes';

            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Saving...';
            }

            const data = new FormData();
            data.append('nome', document.getElementById('edit_nome').value.trim());
            data.append('telefone', document.getElementById('edit_telefone').value.trim());
            data.append('email', document.getElementById('edit_email').value.trim());
            data.append('endereco', document.getElementById('edit_endereco').value.trim());
            
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
            const compOptions = {
                maxSizeMB: 0.35,
                maxWidthOrHeight: 1600,
                useWebWorker: !isIOS,
                fileType: isIOS ? 'image/jpeg' : 'image/webp',
                initialQuality: 0.75
            };
            const extReplacement = isIOS ? '.jpg' : '.webp';
            
            const appendEditFile = async (fieldId, formKey) => {
                const input = document.getElementById(fieldId);
                if (input && input.files.length > 0) {
                    const file = input.files[0];
                    if (file.type.startsWith('image/')) {
                        try {
                            const compressedFile = await imageCompression(file, compOptions);
                            data.append(formKey, compressedFile, file.name.replace(/\.[^/.]+$/, extReplacement));
                        } catch (err) {
                            data.append(formKey, file);
                        }
                    } else {
                        data.append(formKey, file);
                    }
                }
            };

            await appendEditFile('edit_habilitacao', 'habilitacao');
            await appendEditFile('edit_habilitacao_verso', 'habilitacao_verso');
            await appendEditFile('edit_cbt', 'cbt');
            await appendEditFile('edit_comprovante_endereco', 'comprovante_endereco');
            
            try {
                const response = await fetch(`/api/clientes/${id}`, { method: 'PUT', body: data });
                if (response.ok) {
                    fecharModalCliente();
                    carregarClientes();
                } else {
                    const res = await response.json();
                    alert(res.error || res.erro || 'Error updating customer');
                }
            } catch(err) {
                alert('Server connection error. Please try again.');
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalBtnText;
                }
            }
        });
    }
});

