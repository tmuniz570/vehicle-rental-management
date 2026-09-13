// FF Motors - User Management Scripts
let listaUsuarios = [];
let usuarioLogadoId = null;
let abaAtual = 'users';
let auditPaginaAtual = 1;
let auditTermoBusca = '';
let auditAcaoFiltro = '';
let auditDataFiltro = '';

document.addEventListener('DOMContentLoaded', () => {
    carregarUsuarios();

    const searchInput = document.getElementById('userSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', filtrarUsuarios);
    }

    const btnOpenNew = document.getElementById('btnOpenNewUserModal');
    if (btnOpenNew) {
        btnOpenNew.addEventListener('click', abrirModalNovoUsuario);
    }

    const formNovo = document.getElementById('formNovoUsuario');
    if (formNovo) {
        formNovo.addEventListener('submit', handleNovoUsuarioSubmit);
    }

    const formEdit = document.getElementById('formEditUsuario');
    if (formEdit) {
        formEdit.addEventListener('submit', handleEditUsuarioSubmit);
    }

    // Audit Log Controls
    const auditSearch = document.getElementById('auditSearchInput');
    let searchTimeout;
    if (auditSearch) {
        auditSearch.addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                auditTermoBusca = e.target.value.trim();
                auditPaginaAtual = 1;
                carregarAuditoria();
            }, 300);
        });
    }

    const auditAcao = document.getElementById('auditAcaoFilter');
    if (auditAcao) {
        auditAcao.addEventListener('change', (e) => {
            auditAcaoFiltro = e.target.value;
            auditPaginaAtual = 1;
            carregarAuditoria();
        });
    }

    const auditDate = document.getElementById('auditDateFilter');
    const btnClearAuditDate = document.getElementById('btnClearAuditDate');
    if (auditDate) {
        auditDate.addEventListener('change', (e) => {
            auditDataFiltro = e.target.value;
            if (btnClearAuditDate) {
                btnClearAuditDate.style.display = auditDataFiltro ? 'inline-block' : 'none';
            }
            auditPaginaAtual = 1;
            carregarAuditoria();
        });
    }

    if (btnClearAuditDate) {
        btnClearAuditDate.addEventListener('click', () => {
            if (auditDate) auditDate.value = '';
            auditDataFiltro = '';
            btnClearAuditDate.style.display = 'none';
            auditPaginaAtual = 1;
            carregarAuditoria();
        });
    }

    const btnRefreshAudit = document.getElementById('btnRefreshAudit');
    if (btnRefreshAudit) {
        btnRefreshAudit.addEventListener('click', () => {
            carregarAuditoria();
        });
    }

    const btnPrevAudit = document.getElementById('btnPrevAuditPage');
    if (btnPrevAudit) {
        btnPrevAudit.addEventListener('click', () => {
            if (auditPaginaAtual > 1) {
                auditPaginaAtual--;
                carregarAuditoria();
            }
        });
    }

    const btnNextAudit = document.getElementById('btnNextAuditPage');
    if (btnNextAudit) {
        btnNextAudit.addEventListener('click', () => {
            auditPaginaAtual++;
            carregarAuditoria();
        });
    }
});

function switchTab(tab) {
    abaAtual = tab;
    const tabUsers = document.getElementById('tabContentUsers');
    const tabAudit = document.getElementById('tabContentAudit');
    const btnUsers = document.getElementById('tabBtnUsers');
    const btnAudit = document.getElementById('tabBtnAudit');

    if (tab === 'users') {
        if (tabUsers) tabUsers.style.display = 'block';
        if (tabAudit) tabAudit.style.display = 'none';
        if (btnUsers) {
            btnUsers.style.background = 'var(--accent)';
            btnUsers.style.color = 'white';
            btnUsers.style.border = 'none';
        }
        if (btnAudit) {
            btnAudit.style.background = 'rgba(255,255,255,0.03)';
            btnAudit.style.color = 'var(--text-secondary)';
            btnAudit.style.border = '1px solid var(--border-color)';
        }
    } else {
        if (tabUsers) tabUsers.style.display = 'none';
        if (tabAudit) tabAudit.style.display = 'block';
        if (btnAudit) {
            btnAudit.style.background = 'var(--accent)';
            btnAudit.style.color = 'white';
            btnAudit.style.border = 'none';
        }
        if (btnUsers) {
            btnUsers.style.background = 'rgba(255,255,255,0.03)';
            btnUsers.style.color = 'var(--text-secondary)';
            btnUsers.style.border = '1px solid var(--border-color)';
        }
        carregarAuditoria();
    }
}

async function carregarUsuarios() {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;

    try {
        const response = await fetch('/api/usuarios');
        if (!response.ok) {
            if (response.status === 403) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#f87171; padding:2rem;">Access Denied. Administrator privileges required.</td></tr>';
                return;
            }
            throw new Error('Failed to fetch users');
        }

        const data = await response.json();
        listaUsuarios = data.usuarios || [];
        usuarioLogadoId = data.current_user_id || null;

        atualizarEstatisticas(listaUsuarios);
        renderizarTabela(listaUsuarios);
    } catch (error) {
        console.error('Error loading users:', error);
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#f87171; padding:2rem;">Error loading accounts. Please refresh the page.</td></tr>';
    }
}

function atualizarEstatisticas(usuarios) {
    const total = usuarios.length;
    const ativos = usuarios.filter(u => u.ativo).length;
    const admins = usuarios.filter(u => u.role === 'admin').length;
    const staff = usuarios.filter(u => u.role !== 'admin').length;

    const elTotal = document.getElementById('statTotalUsers');
    const elAtivos = document.getElementById('statActiveUsers');
    const elAdmins = document.getElementById('statAdminUsers');
    const elStaff = document.getElementById('statStaffUsers');

    if (elTotal) elTotal.textContent = total;
    if (elAtivos) elAtivos.textContent = ativos;
    if (elAdmins) elAdmins.textContent = admins;
    if (elStaff) elStaff.textContent = staff;
}

function filtrarUsuarios() {
    const termo = (document.getElementById('userSearchInput').value || '').toLowerCase().trim();
    if (!termo) {
        renderizarTabela(listaUsuarios);
        return;
    }

    const filtrados = listaUsuarios.filter(u => 
        (u.nome && u.nome.toLowerCase().includes(termo)) ||
        (u.email && u.email.toLowerCase().includes(termo)) ||
        (u.role && u.role.toLowerCase().includes(termo))
    );
    renderizarTabela(filtrados);
}

function renderizarTabela(usuarios) {
    const tbody = document.getElementById('usersTableBody');
    if (!tbody) return;

    if (usuarios.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:2rem; color:var(--text-secondary);">No user accounts found.</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    usuarios.forEach(user => {
        const tr = document.createElement('tr');
        
        // Initial letter
        const inicial = user.nome ? user.nome.charAt(0).toUpperCase() : 'U';
        const isCurrent = user.id === usuarioLogadoId;

        // Role badge
        let roleBadge = '';
        if (user.role === 'admin') {
            roleBadge = '<span class="badge" style="background:rgba(168,85,247,0.15); color:#c084fc; border:1px solid rgba(168,85,247,0.3);">Administrator</span>';
        } else {
            roleBadge = '<span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3);">Yard Staff</span>';
        }

        // Status badge
        let statusBadge = user.ativo 
            ? '<span class="badge badge-success">Active</span>'
            : '<span class="badge badge-danger">Suspended</span>';

        // Creation Date
        const dataFormatada = user.data_criacao ? user.data_criacao.substring(0, 10) : '-';

        tr.innerHTML = `
            <td>
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 38px; height: 38px; border-radius: 50%; background: ${user.role === 'admin' ? 'var(--accent-gradient)' : 'linear-gradient(135deg, #2563eb, #1d4ed8)'}; display: flex; align-items: center; justify-content: center; font-weight: 700; color: white; font-size: 0.95rem; flex-shrink: 0;">
                        ${inicial}
                    </div>
                    <div>
                        <div style="font-weight: 600; color: var(--text-primary);">
                            ${escapeHtml(user.nome)}
                            ${isCurrent ? '<span style="font-size:0.7rem; margin-left:6px; padding:2px 6px; border-radius:6px; background:rgba(255,102,0,0.15); color:var(--accent); font-weight:700;">YOU</span>' : ''}
                        </div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary); display: md-none;">
                            ID: #${user.id}
                        </div>
                    </div>
                </div>
            </td>
            <td style="color: var(--text-secondary); font-family: monospace; font-size: 0.875rem;">
                ${escapeHtml(user.email)}
            </td>
            <td>${roleBadge}</td>
            <td>${statusBadge}</td>
            <td style="color: var(--text-secondary); font-size: 0.85rem;">${dataFormatada}</td>
            <td style="text-align: right;">
                <div style="display: inline-flex; align-items: center; gap: 8px;">
                    <button type="button" class="btn-secondary" onclick="abrirModalEditUsuario(${user.id})" title="Edit User or Password" style="padding: 6px 12px; font-size: 0.8rem; width: auto;">
                        ✏️ Edit / Password
                    </button>
                    ${!isCurrent ? `
                    <button type="button" class="btn-secondary" onclick="toggleStatusUsuario(${user.id}, ${!user.ativo})" title="${user.ativo ? 'Suspend User' : 'Activate User'}" style="padding: 6px 10px; font-size: 0.8rem; width: auto; color: ${user.ativo ? '#f87171' : '#10b981'}; border-color: ${user.ativo ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'};">
                        ${user.ativo ? 'Suspend' : 'Activate'}
                    </button>
                    <button type="button" class="btn-secondary" onclick="deletarUsuario(${user.id}, '${escapeHtml(user.nome)}')" title="Delete Account" style="padding: 6px 10px; font-size: 0.8rem; width: auto; color: #f87171; border-color: rgba(239,68,68,0.3);">
                        🗑️
                    </button>
                    ` : ''}
                </div>
            </td>
        `;

        tbody.appendChild(tr);
    });

    if (typeof enableTableSorting === 'function') {
        enableTableSorting('usersTable');
    }
}

// --- Modal Handlers ---
function abrirModalNovoUsuario() {
    const form = document.getElementById('formNovoUsuario');
    if (form) form.reset();
    const modal = document.getElementById('modalNewUser');
    if (modal) modal.style.display = 'flex';
}

function fecharModalNovoUsuario() {
    const modal = document.getElementById('modalNewUser');
    if (modal) modal.style.display = 'none';
}

function abrirModalEditUsuario(userId) {
    const user = listaUsuarios.find(u => u.id === userId);
    if (!user) return;

    document.getElementById('edit_user_id').value = user.id;
    document.getElementById('edit_nome').value = user.nome || '';
    document.getElementById('edit_email').value = user.email || '';
    document.getElementById('edit_role').value = user.role || 'staff';
    document.getElementById('edit_ativo').value = user.ativo ? 'true' : 'false';
    document.getElementById('edit_password').value = '';

    const isCurrent = user.id === usuarioLogadoId;
    const selectAtivo = document.getElementById('edit_ativo');
    const selectRole = document.getElementById('edit_role');
    
    // Prevent self-lockout
    if (isCurrent) {
        selectAtivo.disabled = true;
        selectRole.disabled = true;
        document.getElementById('editUserSubtitle').textContent = 'Editing your own profile. (Status & Role locked to prevent lockout)';
    } else {
        selectAtivo.disabled = false;
        selectRole.disabled = false;
        document.getElementById('editUserSubtitle').textContent = 'Modify permissions, role, and credentials.';
    }

    const modal = document.getElementById('modalEditUser');
    if (modal) modal.style.display = 'flex';
}

function fecharModalEditUsuario() {
    const modal = document.getElementById('modalEditUser');
    if (modal) modal.style.display = 'none';
}

// --- Form Actions ---
async function handleNovoUsuarioSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSalvarNovoUsuario');
    if (btn) btn.disabled = true;

    const payload = {
        nome: document.getElementById('novo_nome').value.trim(),
        email: document.getElementById('novo_email').value.trim().toLowerCase(),
        role: document.getElementById('novo_role').value,
        password: document.getElementById('novo_password').value
    };

    try {
        const response = await fetch('/api/usuarios', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const res = await response.json();
        if (!response.ok) {
            alert(res.error || res.message || 'Error creating user');
            return;
        }

        fecharModalNovoUsuario();
        await carregarUsuarios();
        alert('User created successfully!');
    } catch (error) {
        console.error('Error:', error);
        alert('Network or server error creating user');
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function handleEditUsuarioSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSalvarEditUsuario');
    if (btn) btn.disabled = true;

    const userId = document.getElementById('edit_user_id').value;
    const payload = {
        nome: document.getElementById('edit_nome').value.trim(),
        role: document.getElementById('edit_role').value,
        ativo: document.getElementById('edit_ativo').value === 'true',
        password: document.getElementById('edit_password').value
    };

    try {
        const response = await fetch(`/api/usuarios/${userId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const res = await response.json();
        if (!response.ok) {
            alert(res.error || res.message || 'Error updating user');
            return;
        }

        fecharModalEditUsuario();
        await carregarUsuarios();
        alert('Account updated successfully!');
    } catch (error) {
        console.error('Error:', error);
        alert('Network or server error updating user');
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function toggleStatusUsuario(userId, novoStatus) {
    const acao = novoStatus ? 'activate' : 'suspend';
    if (!confirm(`Are you sure you want to ${acao} this user account?`)) return;

    try {
        const response = await fetch(`/api/usuarios/${userId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ativo: novoStatus })
        });

        const res = await response.json();
        if (!response.ok) {
            alert(res.error || res.message || 'Error changing status');
            return;
        }

        await carregarUsuarios();
    } catch (error) {
        console.error('Error:', error);
        alert('Error updating status');
    }
}

async function deletarUsuario(userId, nome) {
    if (!confirm(`CAUTION: Are you sure you want to permanently delete user "${nome}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/usuarios/${userId}`, {
            method: 'DELETE'
        });

        const res = await response.json();
        if (!response.ok) {
            alert(res.error || res.message || 'Error deleting user');
            return;
        }

        await carregarUsuarios();
        alert('User account deleted.');
    } catch (error) {
        console.error('Error:', error);
        alert('Error deleting user');
    }
}

// --- Utilities ---
function gerarSenhaAleatoria() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%&*';
    let pass = 'FF';
    for (let i = 0; i < 8; i++) {
        pass += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    const input = document.getElementById('novo_password');
    if (input) {
        input.value = pass;
        input.type = 'text'; // Show generated password immediately
    }
}

function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function carregarAuditoria() {
    const tbody = document.getElementById('auditTableBody');
    const paginationInfo = document.getElementById('auditPaginationInfo');
    if (!tbody) return;

    try {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:2rem; color:var(--text-secondary);">Loading activity log...</td></tr>';

        const params = new URLSearchParams({
            page: auditPaginaAtual,
            limit: 20,
            search: auditTermoBusca,
            acao: auditAcaoFiltro,
            data: auditDataFiltro
        });

        const res = await fetch(`/api/auditoria?${params.toString()}`);
        if (!res.ok) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#f87171; padding:2rem;">Error loading audit trail.</td></tr>';
            return;
        }

        const data = await res.json();
        const logs = data.itens || [];

        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:2rem; color:var(--text-secondary);">No activity recorded with current filters.</td></tr>';
            if (paginationInfo) paginationInfo.textContent = '';
            const btnPrev = document.getElementById('btnPrevAuditPage');
            const btnNext = document.getElementById('btnNextAuditPage');
            if (btnPrev) btnPrev.disabled = true;
            if (btnNext) btnNext.disabled = true;
            return;
        }

        tbody.innerHTML = '';
        logs.forEach(log => {
            const tr = document.createElement('tr');
            const dataFmt = log.data_hora ? new Date(log.data_hora).toLocaleString('en-GB') : '-';

            // Action Badge
            let acaoBadge = '';
            const a = log.acao || '';
            if (a.includes('CANCEL')) {
                acaoBadge = '<span class="badge badge-danger">Cancelled</span>';
            } else if (a.includes('PAYMENT')) {
                acaoBadge = '<span class="badge badge-success">Payment</span>';
            } else if (a.includes('CONTRACT')) {
                acaoBadge = '<span class="badge badge-info">Contract</span>';
            } else if (a.includes('INSPECTION') || a.includes('RETURN')) {
                acaoBadge = '<span class="badge badge-warning">Inspection</span>';
            } else if (a.includes('USER')) {
                acaoBadge = '<span class="badge" style="background:rgba(168,85,247,0.15); color:#c084fc;">User</span>';
            } else if (a.includes('MOTO')) {
                acaoBadge = '<span class="badge" style="background:rgba(245,158,11,0.15); color:#f59e0b;">Vehicle</span>';
            } else {
                acaoBadge = `<span class="badge">${escapeHtml(a)}</span>`;
            }

            const targetTxt = log.entidade ? `${log.entidade} ${log.entidade_id ? '#' + log.entidade_id : ''}` : '-';

            tr.innerHTML = `
                <td data-sort="${log.data_hora || ''}" style="font-size:0.85rem; color:var(--text-secondary); white-space:nowrap;">${dataFmt}</td>
                <td data-sort="${escapeHtml(log.usuario_nome || 'System')}" style="font-weight:600; color:var(--text-primary); white-space:nowrap;">
                    👤 ${escapeHtml(log.usuario_nome || 'System')}
                </td>
                <td data-sort="${escapeHtml(log.acao || '')}" class="nowrap">${acaoBadge}</td>
                <td data-sort="${escapeHtml(log.descricao || '')}" style="font-size:0.9rem; color:var(--text-primary); max-width:380px;">
                    ${escapeHtml(log.descricao)}
                </td>
                <td data-sort="${escapeHtml(targetTxt)}" style="font-family:monospace; font-size:0.82rem; color:var(--text-secondary); white-space:nowrap;">
                    ${escapeHtml(targetTxt)}
                </td>
                <td data-sort="${escapeHtml(log.ip_origem || '')}" style="font-size:0.8rem; color:var(--text-secondary); opacity:0.7; white-space:nowrap;">
                    ${escapeHtml(log.ip_origem || '-')}
                </td>
            `;
            tbody.appendChild(tr);
        });

        if (typeof enableTableSorting === 'function') {
            enableTableSorting('auditTable');
        }

        if (paginationInfo) {
            paginationInfo.textContent = `Page ${data.pagina_atual} of ${data.paginas || 1} (${data.total} events)`;
        }

        const btnPrev = document.getElementById('btnPrevAuditPage');
        const btnNext = document.getElementById('btnNextAuditPage');
        if (btnPrev) btnPrev.disabled = data.pagina_atual <= 1;
        if (btnNext) btnNext.disabled = data.pagina_atual >= (data.paginas || 1);
    } catch (e) {
        console.error('Audit load error:', e);
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#f87171; padding:2rem;">Network error loading activity log.</td></tr>';
    }
}
