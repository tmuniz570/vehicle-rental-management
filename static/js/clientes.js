let paginaAtual = 1;
let termoBusca = '';

async function carregarClientes() {
    const tbody = document.querySelector('#clientesTable tbody');
    const paginationInfo = document.getElementById('paginationInfo');
    
    try {
        const res = await fetch(`/api/clientes?page=${paginaAtual}&limit=20&search=${encodeURIComponent(termoBusca)}`);
        const data = await res.json();
        const clientes = data.itens || [];
        
        if (clientes.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No customers found.</td></tr>';
            if(paginationInfo) paginationInfo.textContent = '';
            return;
        }
        
        tbody.innerHTML = '';
        clientes.forEach(c => {
            const tr = document.createElement('tr');
            
            let docsHtml = '';
            if(c.url_habilitacao) docsHtml += `<a href="${c.url_habilitacao}" target="_blank" style="color:var(--accent);margin-right:10px;">Driving Licence</a>`;
            if(c.url_comprovante_endereco) docsHtml += `<br><a href="${c.url_comprovante_endereco}" target="_blank" style="color:var(--accent);margin-right:10px;">Proof of Address</a>`;
            
            const btnEdit = `<button class="btn-edit" data-id="${c.id}" data-nome="${c.nome}" data-tel="${c.telefone}" data-email="${c.email}" data-endereco="${c.endereco || ''}" style="background:transparent; color:var(--accent); border:1px solid var(--accent); padding:10px 15px; min-width:60px; min-height:44px; border-radius:6px; cursor:pointer;">Edit</button>`;
            
            tr.innerHTML = `
                <td><strong>${c.nome}</strong></td>
                <td class="nowrap">${c.telefone}</td>
                <td>${c.email}</td>
                <td class="cell-wrap">${c.endereco || '-'}</td>
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
                document.getElementById('edit_id').value = e.target.getAttribute('data-id');
                document.getElementById('edit_nome').value = e.target.getAttribute('data-nome');
                document.getElementById('edit_telefone').value = e.target.getAttribute('data-tel');
                document.getElementById('edit_email').value = e.target.getAttribute('data-email');
                document.getElementById('edit_endereco').value = e.target.getAttribute('data-endereco');
                modal.style.display = 'flex';
            });
        });
        
    } catch(e) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--error);">Error loading customers.</td></tr>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
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
    if(closeBtn) closeBtn.addEventListener('click', () => { modal.style.display = 'none'; });

    document.getElementById('editClientForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('edit_id').value;
        const data = new FormData();
        data.append('nome', document.getElementById('edit_nome').value);
        data.append('telefone', document.getElementById('edit_telefone').value);
        data.append('email', document.getElementById('edit_email').value);
        data.append('endereco', document.getElementById('edit_endereco').value);
        
        const hFile = document.getElementById('edit_habilitacao').files[0];
        if(hFile) {
            if (hFile.type.startsWith('image/')) {
                try {
                    const compressedFile = await imageCompression(hFile, { maxSizeMB: 0.3, maxWidthOrHeight: 1920, useWebWorker: true, fileType: 'image/webp' });
                    data.append('habilitacao', compressedFile, hFile.name.replace(/\.[^/.]+$/, ".webp"));
                } catch (err) {
                    data.append('habilitacao', hFile);
                }
            } else {
                data.append('habilitacao', hFile);
            }
        }
        
        const ceFile = document.getElementById('edit_comprovante_endereco').files[0];
        if(ceFile) {
            if (ceFile.type.startsWith('image/')) {
                try {
                    const compressedFile = await imageCompression(ceFile, { maxSizeMB: 0.3, maxWidthOrHeight: 1920, useWebWorker: true, fileType: 'image/webp' });
                    data.append('comprovante_endereco', compressedFile, ceFile.name.replace(/\.[^/.]+$/, ".webp"));
                } catch (err) {
                    data.append('comprovante_endereco', ceFile);
                }
            } else {
                data.append('comprovante_endereco', ceFile);
            }
        }
        
        try {
            const response = await fetch(`/api/clientes/${id}`, { method: 'PUT', body: data });
            if (response.ok) {
                modal.style.display = 'none';
                carregarClientes();
            } else {
                const res = await response.json();
                alert(res.error || res.erro || 'Error updating customer');
            }
        } catch(err) {
            alert('Server connection error. Please try again.');
        }
    });
});

