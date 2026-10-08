// FF Motors - User Management Scripts
let listaUsuarios = [];
let usuarioLogadoId = null;
let abaAtual = 'users';

// Audit Trail State
let auditPaginaAtual = 1;
let auditTermoBusca = '';
let auditAcaoFiltro = '';
let auditUsuarioFiltro = '';
let auditModuloFiltro = '';
let auditDataInicio = '';
let auditDataFim = '';
let auditLimit = 50;
let auditSortBy = 'data_hora';
let auditSortOrder = 'desc';
let auditLogsCache = [];
let auditUsersPopulated = false;

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

    // --- Audit Log Controls ---
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

    const auditUser = document.getElementById('auditUserFilter');
    if (auditUser) {
        auditUser.addEventListener('change', (e) => {
            auditUsuarioFiltro = e.target.value;
            auditPaginaAtual = 1;
            carregarAuditoria();
        });
    }

    const auditModule = document.getElementById('auditModuleFilter');
    if (auditModule) {
        auditModule.addEventListener('change', (e) => {
            auditModuloFiltro = e.target.value;
            auditPaginaAtual = 1;
            carregarAuditoria();
        });
    }

    const auditLimitSelect = document.getElementById('auditLimitSelect');
    if (auditLimitSelect) {
        auditLimitSelect.addEventListener('change', (e) => {
            auditLimit = parseInt(e.target.value, 10) || 50;
            auditPaginaAtual = 1;
            carregarAuditoria();
        });
    }

    const dateFrom = document.getElementById('auditDateFrom');
    const dateTo = document.getElementById('auditDateTo');
    if (dateFrom) {
        dateFrom.addEventListener('change', (e) => {
            auditDataInicio = e.target.value;
            syncPresetPillButtons('');
            auditPaginaAtual = 1;
            carregarAuditoria();
        });
    }
    if (dateTo) {
        dateTo.addEventListener('change', (e) => {
            auditDataFim = e.target.value;
            syncPresetPillButtons('');
            auditPaginaAtual = 1;
            carregarAuditoria();
        });
    }

    // Quick Date Presets
    const presetsContainer = document.getElementById('auditDatePresets');
    if (presetsContainer) {
        presetsContainer.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-preset');
            if (!btn) return;
            const preset = btn.getAttribute('data-preset');
            aplicarPresetData(preset);
        });
    }

    const btnClearAuditFilters = document.getElementById('btnClearAuditFilters');
    if (btnClearAuditFilters) {
        btnClearAuditFilters.addEventListener('click', resetAuditFilters);
    }

    const btnRefreshAudit = document.getElementById('btnRefreshAudit');
    if (btnRefreshAudit) {
        btnRefreshAudit.addEventListener('click', () => {
            carregarAuditoria();
        });
    }

    const btnExportAuditCsv = document.getElementById('btnExportAuditCsv');
    if (btnExportAuditCsv) {
        btnExportAuditCsv.addEventListener('click', exportarAuditCsv);
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

    // Enable True Server-Side Sorting on auditTable
    if (typeof enableTableSorting === 'function') {
        enableTableSorting('auditTable', (field, order) => {
            auditSortBy = field;
            auditSortOrder = order;
            auditPaginaAtual = 1;
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
            if (response.status === 401) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#f87171; padding:2rem;">Your session has expired. <a href="/login" style="color:var(--accent); text-decoration:underline; font-weight:600;">Sign in again</a>.</td></tr>';
                return;
            }
            if (response.status === 403) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#f87171; padding:2rem;">Access Denied. Administrator privileges required.</td></tr>';
                return;
            }
            throw new Error(`Server returned HTTP ${response.status}`);
        }

        const data = await response.json();
        listaUsuarios = data.usuarios || [];
        usuarioLogadoId = data.current_user_id || null;

        atualizarEstatisticas(listaUsuarios);
        renderizarTabela(listaUsuarios);
    } catch (error) {
        console.error('Error loading users:', error);
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:#f87171; padding:2rem;">
            Error loading accounts: ${escapeHtml(error.message || 'Please refresh the page.')}<br>
            <button type="button" onclick="carregarUsuarios()" class="btn-secondary" style="margin-top:0.75rem; padding:6px 14px; font-size:0.85rem; width:auto;">🔄 Try Again</button>
        </td></tr>`;
    }
}

function atualizarEstatisticas(usuarios) {
    const total = usuarios.length;
    const ativos = usuarios.filter(u => u.ativo).length;
    const admins = usuarios.filter(u => u.is_admin || u.role === 'admin').length;
    const staff = usuarios.filter(u => !u.is_admin && u.role !== 'admin').length;

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

const MASTER_ADMIN_EMAIL = 'tmuniz570@gmail.com';

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
        const isMaster = (user.email && user.email.toLowerCase() === MASTER_ADMIN_EMAIL);

        // Role & Permissions badge
        let roleBadge = '';
        if (isMaster) {
            roleBadge = '<span class="badge" style="background:linear-gradient(135deg, rgba(245,158,11,0.2), rgba(239,68,68,0.2)); color:#fbbf24; border:1px solid rgba(245,158,11,0.4); font-weight:700;">👑 Root Administrator</span>';
        } else if (user.is_admin) {
            roleBadge = '<span class="badge" style="background:rgba(168,85,247,0.15); color:#c084fc; border:1px solid rgba(168,85,247,0.3);">Administrator</span>';
        } else {
            const perms = [];
            if (user.perm_alugueis) {
                if (user.perm_financeiro !== false) {
                    perms.push('Aluguel / Venda');
                } else {
                    perms.push('Aluguel (Sem Fin)');
                }
            }
            if (user.perm_claims) perms.push('Claims');
            const permText = perms.length > 0 ? perms.join(' + ') : 'Sem Acesso';
            roleBadge = `<span class="badge" style="background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3);">${escapeHtml(permText)}</span>`;
        }

        // Status badge
        let statusBadge = user.ativo 
            ? '<span class="badge badge-success">Active</span>'
            : '<span class="badge badge-danger">Suspended</span>';

        // Creation Date
        const dataFormatada = user.data_criacao ? user.data_criacao.substring(0, 10) : '-';

        // Actions
        let actionButtons = `
            <button class="btn-secondary" onclick="abrirModalEditUsuario(${user.id})" style="padding: 6px 12px; font-size: 0.8rem; margin-right: 6px;">
                Edit
            </button>
        `;

        if (isMaster) {
            actionButtons += `
                <span class="badge" style="padding: 6px 10px; font-size: 0.75rem; background: rgba(255,255,255,0.05); color: #94a3b8; border: 1px solid rgba(255,255,255,0.12); cursor: not-allowed; display: inline-flex; align-items: center; gap: 4px;" title="Root administrator account cannot be deleted or suspended">
                    🔒 Protected
                </span>
            `;
        } else if (!isCurrent) {
            actionButtons += `
                <button class="btn-secondary" onclick="confirmarExclusaoUsuario(${user.id}, '${escapeHtml(user.nome)}')" style="padding: 6px 12px; font-size: 0.8rem; color: #f87171; border-color: rgba(239, 68, 68, 0.2);">
                    Delete
                </button>
            `;
        }

        tr.innerHTML = `
            <td>
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="width: 38px; height: 38px; border-radius: 50%; background: ${isMaster ? 'linear-gradient(135deg, #f59e0b, #ef4444)' : (user.is_admin ? 'var(--accent-gradient)' : 'linear-gradient(135deg, #2563eb, #1d4ed8)')}; display: flex; align-items: center; justify-content: center; font-weight: 700; color: white; font-size: 0.95rem; flex-shrink: 0;">
                        ${inicial}
                    </div>
                    <div>
                        <div style="font-weight: 600; color: var(--text-primary);">
                            ${escapeHtml(user.nome)}
                            ${isMaster ? '<span style="font-size:0.7rem; margin-left:6px; padding:2px 6px; border-radius:6px; background:rgba(245,158,11,0.2); color:#fbbf24; font-weight:700;">ROOT</span>' : (isCurrent ? '<span style="font-size:0.7rem; margin-left:6px; padding:2px 6px; border-radius:6px; background:rgba(255,102,0,0.15); color:var(--accent); font-weight:700;">YOU</span>' : '')}
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
                ${actionButtons}
            </td>
        `;
        tbody.appendChild(tr);
    });

    if (typeof enableTableSorting === 'function') {
        enableTableSorting('usersTable');
    }
}

// --- Modals ---
function abrirModalNovoUsuario() {
    document.getElementById('formNovoUsuario').reset();
    document.getElementById('novo_perm_alugueis').checked = true;
    const chkFin = document.getElementById('novo_perm_financeiro');
    if (chkFin) chkFin.checked = true;
    document.getElementById('novo_perm_claims').checked = false;
    document.getElementById('novo_is_admin').checked = false;
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
    document.getElementById('edit_perm_alugueis').checked = !!user.perm_alugueis;
    const chkFin = document.getElementById('edit_perm_financeiro');
    if (chkFin) chkFin.checked = user.perm_financeiro !== false;
    document.getElementById('edit_perm_claims').checked = !!user.perm_claims;
    document.getElementById('edit_is_admin').checked = !!user.is_admin;
    document.getElementById('edit_ativo').value = user.ativo ? 'true' : 'false';
    document.getElementById('edit_password').value = '';

    const isCurrent = user.id === usuarioLogadoId;
    const isMaster = user.email && user.email.toLowerCase() === MASTER_ADMIN_EMAIL;
    const selectAtivo = document.getElementById('edit_ativo');
    const chkAdmin = document.getElementById('edit_is_admin');
    const chkAlugueis = document.getElementById('edit_perm_alugueis');
    const chkClaims = document.getElementById('edit_perm_claims');
    const inputEmail = document.getElementById('edit_email');
    
    if (isMaster) {
        selectAtivo.disabled = true;
        chkAdmin.disabled = true;
        chkAlugueis.disabled = true;
        if (chkFin) chkFin.disabled = true;
        chkClaims.disabled = true;
        if (inputEmail) inputEmail.disabled = true;
        document.getElementById('editUserSubtitle').innerHTML = '<span style="color:#fbbf24; font-weight:600;">👑 Root Administrator Account</span> — Protected against demotion, suspension, or deletion. You may update display name or password.';
    } else if (isCurrent) {
        selectAtivo.disabled = true;
        chkAdmin.disabled = true;
        chkAlugueis.disabled = false;
        if (chkFin) chkFin.disabled = false;
        chkClaims.disabled = false;
        if (inputEmail) inputEmail.disabled = false;
        document.getElementById('editUserSubtitle').textContent = 'Editing your own profile. (Status & Admin locked to prevent lockout)';
    } else {
        selectAtivo.disabled = false;
        chkAdmin.disabled = false;
        chkAlugueis.disabled = false;
        if (chkFin) chkFin.disabled = false;
        chkClaims.disabled = false;
        if (inputEmail) inputEmail.disabled = false;
        document.getElementById('editUserSubtitle').textContent = 'Modify permissions, modules, and credentials.';
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

    const elFin = document.getElementById('novo_perm_financeiro');
    const payload = {
        nome: document.getElementById('novo_nome').value.trim(),
        email: document.getElementById('novo_email').value.trim().toLowerCase(),
        perm_alugueis: document.getElementById('novo_perm_alugueis').checked,
        perm_financeiro: elFin ? elFin.checked : true,
        perm_claims: document.getElementById('novo_perm_claims').checked,
        is_admin: document.getElementById('novo_is_admin').checked,
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

    const userId = parseInt(document.getElementById('edit_user_id').value, 10);
    const user = listaUsuarios.find(u => u.id === userId);
    const isMaster = user && user.email && user.email.toLowerCase() === MASTER_ADMIN_EMAIL;
    const elFin = document.getElementById('edit_perm_financeiro');

    const payload = {
        nome: document.getElementById('edit_nome').value.trim(),
        perm_alugueis: isMaster ? true : document.getElementById('edit_perm_alugueis').checked,
        perm_financeiro: isMaster ? true : (elFin ? elFin.checked : true),
        perm_claims: isMaster ? true : document.getElementById('edit_perm_claims').checked,
        is_admin: isMaster ? true : document.getElementById('edit_is_admin').checked,
        ativo: isMaster ? true : (document.getElementById('edit_ativo').value === 'true'),
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
    const targetUser = listaUsuarios.find(u => u.id === userId);
    if (targetUser && targetUser.email && targetUser.email.toLowerCase() === MASTER_ADMIN_EMAIL) {
        alert('Security Alert: The root administrator account cannot be suspended.');
        return;
    }

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

async function confirmarExclusaoUsuario(userId, nome) {
    return deletarUsuario(userId, nome);
}

async function deletarUsuario(userId, nome) {
    const targetUser = listaUsuarios.find(u => u.id === userId);
    if (targetUser && targetUser.email && targetUser.email.toLowerCase() === MASTER_ADMIN_EMAIL) {
        alert('Security Alert: The root administrator account (tmuniz570@gmail.com) is permanently protected and cannot be deleted.');
        return;
    }

    if (!confirm(`CAUTION: Are you sure you want to permanently delete user "${nome}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
        const response = await fetch(`/api/usuarios/${userId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken,
                'X-CSRF-Token': csrfToken,
                'Content-Type': 'application/json'
            }
        });

        const res = await response.json();
        if (!response.ok) {
            alert(res.error || res.message || 'Error deleting user');
            return;
        }

        await carregarUsuarios();
        alert('User account deleted.');
    } catch (error) {
        console.error('Error deleting user:', error);
        alert('Error deleting user. Please check server logs.');
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
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:2.5rem; color:var(--text-secondary);">Loading activity log...</td></tr>';

        const params = new URLSearchParams({
            page: auditPaginaAtual,
            limit: auditLimit,
            search: auditTermoBusca,
            acao: auditAcaoFiltro,
            usuario: auditUsuarioFiltro,
            entidade: auditModuloFiltro,
            data_inicio: auditDataInicio,
            data_fim: auditDataFim,
            sort_by: auditSortBy,
            sort_order: auditSortOrder
        });

        const res = await fetch(`/api/auditoria?${params.toString()}`);
        if (!res.ok) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#f87171; padding:2rem;">Error loading audit trail.</td></tr>';
            return;
        }

        const data = await res.json();
        const logs = data.itens || [];
        auditLogsCache = logs;

        // Update live KPI cards
        if (data.stats) {
            const elToday = document.getElementById('statAuditToday');
            const elStaff = document.getElementById('statAuditStaff');
            const elFinance = document.getElementById('statAuditFinance');
            const elSecurity = document.getElementById('statAuditSecurity');
            if (elToday) elToday.textContent = data.stats.hoje ?? 0;
            if (elStaff) elStaff.textContent = data.stats.operadores_hoje ?? 0;
            if (elFinance) elFinance.textContent = data.stats.financeiro_hoje ?? 0;
            if (elSecurity) elSecurity.textContent = data.stats.seguranca_hoje ?? 0;
        }

        // Populate User Filter options dynamically once
        popularAuditUserFilter();

        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:2.5rem; color:var(--text-secondary);">No activity recorded with current filters.</td></tr>';
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
            tr.style.cursor = 'pointer';
            tr.className = 'audit-row';
            tr.title = 'Click to inspect full event details';

            const dt = log.data_hora ? new Date(log.data_hora) : null;
            const dataFmt = dt ? dt.toLocaleString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '-';

            // Action Badge
            let acaoBadge = '';
            const a = log.acao || '';
            const aUpper = a.toUpperCase();
            if (aUpper.includes('CANCEL') || aUpper.includes('DELETE') || aUpper.includes('FAILED')) {
                acaoBadge = `<span class="badge badge-danger" title="${escapeHtml(a)}">${escapeHtml(a.replace(/_/g, ' '))}</span>`;
            } else if (aUpper.includes('PAYMENT') || aUpper.includes('SUCCESS') || aUpper.includes('COMPLETED') || aUpper.includes('VERIFIED')) {
                acaoBadge = `<span class="badge badge-success" title="${escapeHtml(a)}">${escapeHtml(a.replace(/_/g, ' '))}</span>`;
            } else if (aUpper.includes('CONTRACT') || aUpper.includes('SIGNED') || aUpper.includes('DUE_DAY') || aUpper.includes('ATTACHMENT')) {
                acaoBadge = `<span class="badge badge-info" title="${escapeHtml(a)}">${escapeHtml(a.replace(/_/g, ' '))}</span>`;
            } else if (aUpper.includes('INSPECTION') || aUpper.includes('RETURN') || aUpper.includes('QUARANTINE')) {
                acaoBadge = `<span class="badge badge-warning" title="${escapeHtml(a)}">${escapeHtml(a.replace(/_/g, ' '))}</span>`;
            } else if (aUpper.includes('USER') || aUpper.includes('PASSWORD') || aUpper.includes('LOGIN') || aUpper.includes('LOGOUT')) {
                acaoBadge = `<span class="badge" style="background:rgba(168,85,247,0.18); color:#c084fc; border:1px solid rgba(168,85,247,0.3);" title="${escapeHtml(a)}">${escapeHtml(a.replace(/_/g, ' '))}</span>`;
            } else if (aUpper.includes('MOTO') || aUpper.includes('TRACKER') || aUpper.includes('V5C')) {
                acaoBadge = `<span class="badge" style="background:rgba(245,158,11,0.18); color:#f59e0b; border:1px solid rgba(245,158,11,0.3);" title="${escapeHtml(a)}">${escapeHtml(a.replace(/_/g, ' '))}</span>`;
            } else if (aUpper.includes('CLIENT')) {
                acaoBadge = `<span class="badge" style="background:rgba(14,165,233,0.18); color:#38bdf8; border:1px solid rgba(14,165,233,0.3);" title="${escapeHtml(a)}">${escapeHtml(a.replace(/_/g, ' '))}</span>`;
            } else if (aUpper.includes('CLAIM')) {
                acaoBadge = `<span class="badge" style="background:rgba(236,72,153,0.18); color:#f472b6; border:1px solid rgba(236,72,153,0.3);" title="${escapeHtml(a)}">${escapeHtml(a.replace(/_/g, ' '))}</span>`;
            } else if (aUpper === 'CLEANUP_UPLOADS') {
                acaoBadge = `<span class="badge" style="background:rgba(20,184,166,0.18); color:#2dd4bf; border:1px solid rgba(20,184,166,0.35); font-weight:600;" title="Automated Orphan Uploads Cleanup">🧹 ${escapeHtml(a.replace(/_/g, ' '))}</span>`;
            } else if (aUpper.includes('JOB') || aUpper.includes('CLEANUP') || aUpper.includes('CLOSING') || aUpper.includes('CHARGE')) {
                acaoBadge = `<span class="badge" style="background:rgba(100,116,139,0.25); color:#cbd5e1; border:1px solid rgba(100,116,139,0.35);" title="${escapeHtml(a)}">${escapeHtml(a.replace(/_/g, ' '))}</span>`;
            } else {
                acaoBadge = `<span class="badge" title="${escapeHtml(a)}">${escapeHtml(a.replace(/_/g, ' '))}</span>`;
            }

            const targetTxt = log.entidade ? `${log.entidade} ${log.entidade_id ? '#' + log.entidade_id : ''}` : '-';

            tr.innerHTML = `
                <td style="font-size:0.85rem; color:var(--text-secondary); white-space:nowrap;">
                    ${dataFmt}
                </td>
                <td style="font-weight:600; color:var(--text-primary); white-space:nowrap;">
                    👤 ${escapeHtml(log.usuario_nome || 'System')}
                </td>
                <td class="nowrap">${acaoBadge}</td>
                <td style="font-size:0.9rem; color:var(--text-primary); max-width:420px; line-height:1.4;">
                    ${escapeHtml(log.descricao)}
                </td>
                <td style="font-family:monospace; font-size:0.85rem; color:var(--text-secondary); white-space:nowrap;">
                    ${escapeHtml(targetTxt)}
                </td>
                <td style="font-size:0.82rem; font-family:monospace; color:var(--text-secondary); opacity:0.85; white-space:nowrap;">
                    ${escapeHtml(log.ip_origem || '-')}
                </td>
                <td style="text-align:center;">
                    <button type="button" class="btn-secondary btn-inspect-audit" data-id="${log.id}" style="padding: 4px 8px; font-size: 0.8rem; border-radius: 8px; width: auto;" title="View details">👁️</button>
                </td>
            `;

            // Clicking anywhere on row opens details
            tr.addEventListener('click', (e) => {
                if (e.target.closest('a')) return;
                abrirModalAuditDetail(log.id);
            });

            tbody.appendChild(tr);
        });

        // Visually update the active sort indicator (arrow & classes)
        if (typeof setTableSortIndicator === 'function') {
            setTableSortIndicator('auditTable', auditSortBy, auditSortOrder);
        }

        if (paginationInfo) {
            const inicioItem = (data.pagina_atual - 1) * auditLimit + 1;
            const fimItem = Math.min(data.pagina_atual * auditLimit, data.total);
            paginationInfo.textContent = data.total > 0
                ? `Showing ${inicioItem}–${fimItem} of ${data.total} activities (Page ${data.pagina_atual} of ${data.paginas || 1})`
                : '';
        }

        const btnPrev = document.getElementById('btnPrevAuditPage');
        const btnNext = document.getElementById('btnNextAuditPage');
        if (btnPrev) btnPrev.disabled = data.pagina_atual <= 1;
        if (btnNext) btnNext.disabled = data.pagina_atual >= (data.paginas || 1);
    } catch (e) {
        console.error('Audit load error:', e);
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:#f87171; padding:2rem;">Network error loading activity log.</td></tr>';
    }
}

function popularAuditUserFilter() {
    const userSelect = document.getElementById('auditUserFilter');
    if (!userSelect || auditUsersPopulated) return;

    const currentValue = userSelect.value;
    const usersMap = new Map();
    usersMap.set('System', 'System (Automated)');

    if (Array.isArray(listaUsuarios) && listaUsuarios.length > 0) {
        listaUsuarios.forEach(u => {
            if (u.nome) usersMap.set(u.nome, u.nome + (u.is_admin ? ' (Admin)' : ''));
        });
    }

    userSelect.innerHTML = '<option value="">All Staff / Operators</option>';
    usersMap.forEach((label, val) => {
        const opt = document.createElement('option');
        opt.value = val;
        opt.textContent = label;
        if (val === currentValue) opt.selected = true;
        userSelect.appendChild(opt);
    });

    auditUsersPopulated = true;
}

function aplicarPresetData(preset) {
    const dateFrom = document.getElementById('auditDateFrom');
    const dateTo = document.getElementById('auditDateTo');

    const hoje = new Date();
    const formatYMD = (d) => {
        const y = d.getFullYear();
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${y}-${m}-${day}`;
    };

    if (preset === 'all') {
        auditDataInicio = '';
        auditDataFim = '';
        if (dateFrom) dateFrom.value = '';
        if (dateTo) dateTo.value = '';
    } else if (preset === 'today') {
        const str = formatYMD(hoje);
        auditDataInicio = str;
        auditDataFim = str;
        if (dateFrom) dateFrom.value = str;
        if (dateTo) dateTo.value = str;
    } else if (preset === 'yesterday') {
        const ontem = new Date();
        ontem.setDate(hoje.getDate() - 1);
        const str = formatYMD(ontem);
        auditDataInicio = str;
        auditDataFim = str;
        if (dateFrom) dateFrom.value = str;
        if (dateTo) dateTo.value = str;
    } else if (preset === 'week') {
        const semanaAtras = new Date();
        semanaAtras.setDate(hoje.getDate() - 6);
        auditDataInicio = formatYMD(semanaAtras);
        auditDataFim = formatYMD(hoje);
        if (dateFrom) dateFrom.value = auditDataInicio;
        if (dateTo) dateTo.value = auditDataFim;
    } else if (preset === 'month') {
        const inicioMes = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
        auditDataInicio = formatYMD(inicioMes);
        auditDataFim = formatYMD(hoje);
        if (dateFrom) dateFrom.value = auditDataInicio;
        if (dateTo) dateTo.value = auditDataFim;
    }

    syncPresetPillButtons(preset);
    auditPaginaAtual = 1;
    carregarAuditoria();
}

function syncPresetPillButtons(activePreset) {
    const presetsContainer = document.getElementById('auditDatePresets');
    if (!presetsContainer) return;

    presetsContainer.querySelectorAll('.btn-preset').forEach(btn => {
        const p = btn.getAttribute('data-preset');
        if (p === activePreset) {
            btn.classList.add('active');
            btn.style.background = 'var(--accent)';
            btn.style.color = 'white';
            btn.style.borderColor = 'var(--accent)';
            btn.style.fontWeight = '600';
        } else {
            btn.classList.remove('active');
            btn.style.background = 'var(--card-bg)';
            btn.style.color = 'var(--text-secondary)';
            btn.style.borderColor = 'var(--border-color)';
            btn.style.fontWeight = '500';
        }
    });
}

function resetAuditFilters() {
    auditTermoBusca = '';
    auditAcaoFiltro = '';
    auditUsuarioFiltro = '';
    auditModuloFiltro = '';
    auditDataInicio = '';
    auditDataFim = '';
    auditLimit = 50;
    auditSortBy = 'data_hora';
    auditSortOrder = 'desc';
    auditPaginaAtual = 1;

    const s = document.getElementById('auditSearchInput');
    const a = document.getElementById('auditAcaoFilter');
    const u = document.getElementById('auditUserFilter');
    const m = document.getElementById('auditModuleFilter');
    const df = document.getElementById('auditDateFrom');
    const dt = document.getElementById('auditDateTo');
    const l = document.getElementById('auditLimitSelect');

    if (s) s.value = '';
    if (a) a.value = '';
    if (u) u.value = '';
    if (m) m.value = '';
    if (df) df.value = '';
    if (dt) dt.value = '';
    if (l) l.value = '50';

    syncPresetPillButtons('all');
    carregarAuditoria();
}

function exportarAuditCsv() {
    const params = new URLSearchParams({
        search: auditTermoBusca,
        acao: auditAcaoFiltro,
        usuario: auditUsuarioFiltro,
        entidade: auditModuloFiltro,
        data_inicio: auditDataInicio,
        data_fim: auditDataFim,
        sort_by: auditSortBy,
        sort_order: auditSortOrder
    });

    window.location.href = `/api/auditoria/exportar-csv?${params.toString()}`;
}

function abrirModalAuditDetail(logId) {
    const log = (auditLogsCache || []).find(l => l.id === logId);
    if (!log) return;

    const modal = document.getElementById('modalAuditDetail');
    if (!modal) return;

    const elTitle = document.getElementById('modalAuditTitle');
    const elDate = document.getElementById('modalAuditDateTime');
    const elOp = document.getElementById('modalAuditOperator');
    const elAction = document.getElementById('modalAuditAction');
    const elTarget = document.getElementById('modalAuditTarget');
    const elIp = document.getElementById('modalAuditIp');
    const elDesc = document.getElementById('modalAuditDescription');

    if (elTitle) elTitle.textContent = `Audit Event #${log.id}`;
    if (elDate) {
        const dt = log.data_hora ? new Date(log.data_hora) : null;
        elDate.textContent = dt ? dt.toLocaleString('en-GB') : '-';
    }
    if (elOp) elOp.textContent = log.usuario_nome || 'System';
    if (elAction) {
        elAction.innerHTML = `<span class="badge" style="background:rgba(255,102,0,0.15); color:var(--accent); border:1px solid rgba(255,102,0,0.3); font-weight:700;">${escapeHtml(log.acao || '')}</span>`;
    }
    if (elTarget) {
        elTarget.textContent = log.entidade ? `${log.entidade} ${log.entidade_id ? '#' + log.entidade_id : ''}` : 'N/A';
    }
    if (elIp) {
        elIp.textContent = log.ip_origem ? `${log.ip_origem}` : 'Unknown IP';
    }
    if (elDesc) {
        elDesc.textContent = log.descricao || 'No description provided.';
    }

    modal.style.display = 'flex';
}

function fecharModalAuditDetail() {
    const modal = document.getElementById('modalAuditDetail');
    if (modal) modal.style.display = 'none';
}
