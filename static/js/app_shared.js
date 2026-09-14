/**
 * FF Motors - Shared UI Utilities
 * - Automatic CSRF Token Injection for all fetch requests
 * - Interactive Table Column Sorting
 * - Smart History Back Navigation
 */

// Universal CSRF Token Injection for all fetch mutations
(function() {
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {}) {
        options = options || {};
        const method = (options.method || 'GET').toUpperCase();
        if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            const token = csrfMeta ? csrfMeta.getAttribute('content') : '';
            if (token) {
                if (!options.headers) {
                    options.headers = {};
                }
                if (options.headers instanceof Headers) {
                    if (!options.headers.has('X-CSRFToken') && !options.headers.has('X-CSRF-Token')) {
                        options.headers.append('X-CSRFToken', token);
                    }
                } else if (typeof options.headers === 'object') {
                    if (!options.headers['X-CSRFToken'] && !options.headers['X-CSRF-Token']) {
                        options.headers['X-CSRFToken'] = token;
                    }
                }
            }
        }
        return originalFetch.call(this, url, options);
    };
})();

// 1. Smart History Back Button
document.addEventListener('DOMContentLoaded', () => {
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.btn-back, [data-back="true"]');
        if (btn) {
            const hasReferrer = document.referrer && 
                                document.referrer.startsWith(window.location.origin) && 
                                !document.referrer.endsWith(window.location.pathname) &&
                                document.referrer !== window.location.href;
            if (hasReferrer && window.history.length > 1) {
                e.preventDefault();
                window.history.back();
            }
        }
    });
});

// 2. Universal Table Sorting
function parseSortVal(val) {
    if (!val || val === '-' || val === 'N/A') return { type: 0, val: '' };

    // UK Date format DD/MM/YYYY with optional time
    const dateMatch = val.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{1,2}))?/);
    if (dateMatch) {
        const d = dateMatch[1].padStart(2, '0');
        const m = dateMatch[2].padStart(2, '0');
        const y = dateMatch[3];
        const hh = dateMatch[4] ? dateMatch[4].padStart(2, '0') : '00';
        const mm = dateMatch[5] ? dateMatch[5].padStart(2, '0') : '00';
        const ts = new Date(`${y}-${m}-${d}T${hh}:${mm}:00`).getTime();
        return { type: 1, val: isNaN(ts) ? 0 : ts };
    }

    // Currency or Number / ID (#123, £450.00, 1500)
    const cleanNum = val.replace(/^[£$€#]\s*/, '').replace(/,/g, '');
    if (!isNaN(cleanNum) && cleanNum.trim() !== '') {
        return { type: 1, val: parseFloat(cleanNum) };
    }

    return { type: 2, val: val.toLowerCase() };
}

function deriveSortField(text) {
    if (!text) return '';
    const clean = text.replace(/[^a-zA-Z0-9]/g, ' ').trim().toLowerCase();
    if (clean === 'id' || clean.startsWith('id ')) return 'id';
    if (clean.includes('customer') || clean.includes('name') || clean.includes('cliente')) return 'cliente';
    if (clean.includes('plate') || clean.includes('placa') || clean.includes('reg') || clean.includes('motorbike')) return 'placa';
    if (clean.includes('due date') || clean.includes('vencimento')) return 'data_vencimento';
    if (clean.includes('payment') || clean.includes('pagamento')) return 'data_pagamento';
    if (clean.includes('mot')) return 'vencimento_mot';
    if (clean.includes('tax')) return 'vencimento_tax';
    if (clean.includes('amount') || clean.includes('valor')) return 'valor';
    if (clean.includes('rent')) return 'valor_aluguel_semanal';
    if (clean.includes('collection') || clean.includes('start')) return 'data_retirada';
    if (clean.includes('return')) return 'data_devolucao';
    if (clean.includes('date') || clean.includes('data')) return 'data';
    if (clean.includes('status')) return 'status';
    if (clean.includes('type') || clean.includes('tipo')) return 'tipo';
    if (clean.includes('model') || clean.includes('modelo')) return 'modelo';
    if (clean.includes('colour') || clean.includes('color') || clean.includes('cor')) return 'cor';
    if (clean.includes('phone') || clean.includes('telefone')) return 'telefone';
    if (clean.includes('email')) return 'email';
    if (clean.includes('address') || clean.includes('endereco')) return 'endereco';
    return clean.replace(/\s+/g, '_');
}

function setTableSortIndicator(tableId, field, order) {
    const table = document.getElementById(tableId);
    if (!table) return;
    const thead = table.querySelector('thead');
    if (!thead) return;
    const ths = thead.querySelectorAll('th');
    ths.forEach(th => {
        const thField = th.getAttribute('data-sort-field') || deriveSortField(th.textContent);
        if (thField === field) {
            th.classList.remove('sorted-asc', 'sorted-desc');
            th.classList.add(order === 'desc' ? 'sorted-desc' : 'sorted-asc');
            const ind = th.querySelector('.sort-indicator');
            if (ind) ind.textContent = (order === 'desc') ? '▼' : '▲';
        } else {
            th.classList.remove('sorted-asc', 'sorted-desc');
            const ind = th.querySelector('.sort-indicator');
            if (ind) ind.textContent = '⇅';
        }
    });
}

function enableTableSorting(tableId, onSortCallback) {
    const table = document.getElementById(tableId);
    if (!table) return;

    if (typeof onSortCallback === 'function') {
        table._onSortCallback = onSortCallback;
    }

    const thead = table.querySelector('thead');
    if (!thead) return;

    const headers = thead.querySelectorAll('th');
    headers.forEach((th, index) => {
        const title = th.textContent.trim().toLowerCase();
        // Ignore action / non-sortable columns
        if (title.includes('action') || title === 'actions' || title === 'edit' || title.includes('view') || title === 'documents' || title === 'doc' || title === 'docs' || title === 'photos' || title === 'observations') {
            return;
        }

        th.classList.add('sortable-th');
        th.setAttribute('title', 'Click to sort entire table');
        if (!th.querySelector('.sort-indicator')) {
            const indicator = document.createElement('span');
            indicator.className = 'sort-indicator';
            indicator.textContent = '⇅';
            th.appendChild(indicator);
        }

        if (th._hasSortListener) return;
        th._hasSortListener = true;

        th.addEventListener('click', () => {
            const sortField = th.getAttribute('data-sort-field') || deriveSortField(th.textContent);
            const isAsc = th.classList.contains('sorted-asc');
            const newOrder = isAsc ? 'desc' : 'asc';

            // Reset other headers
            headers.forEach(h => {
                h.classList.remove('sorted-asc', 'sorted-desc');
                const ind = h.querySelector('.sort-indicator');
                if (ind) ind.textContent = '⇅';
            });

            th.classList.add(newOrder === 'desc' ? 'sorted-desc' : 'sorted-asc');
            const activeInd = th.querySelector('.sort-indicator');
            if (activeInd) activeInd.textContent = (newOrder === 'desc') ? '▼' : '▲';

            // Server-side sort callback prioritized
            if (typeof table._onSortCallback === 'function') {
                table._onSortCallback(sortField, newOrder);
            } else if (typeof window[`onSort_${tableId}`] === 'function') {
                window[`onSort_${tableId}`](sortField, newOrder);
            } else {
                // Client-side fallback if no server callback attached
                sortTableByColumn(table, index);
            }
        });
    });
}

function sortTableByColumn(table, colIndex) {
    const tbody = table.querySelector('tbody');
    if (!tbody) return;

    const rows = Array.from(tbody.querySelectorAll('tr'));
    if (rows.length <= 1) return;

    // Check if empty message
    if (rows.length === 1 && rows[0].querySelectorAll('td').length <= 1) return;

    const thead = table.querySelector('thead');
    const ths = thead.querySelectorAll('th');
    const targetTh = ths[colIndex];
    if (!targetTh) return;

    const currentAsc = targetTh.classList.contains('sorted-asc');
    const newAsc = !currentAsc;

    // Reset other headers
    ths.forEach(th => {
        th.classList.remove('sorted-asc', 'sorted-desc');
        const ind = th.querySelector('.sort-indicator');
        if (ind) ind.textContent = '⇅';
    });

    targetTh.classList.add(newAsc ? 'sorted-asc' : 'sorted-desc');
    const activeInd = targetTh.querySelector('.sort-indicator');
    if (activeInd) activeInd.textContent = newAsc ? '▲' : '▼';

    rows.sort((rowA, rowB) => {
        const cellA = rowA.children[colIndex];
        const cellB = rowB.children[colIndex];
        const rawA = cellA ? (cellA.getAttribute('data-sort') || cellA.textContent.trim()) : '';
        const rawB = cellB ? (cellB.getAttribute('data-sort') || cellB.textContent.trim()) : '';

        const parsedA = parseSortVal(rawA);
        const parsedB = parseSortVal(rawB);

        // Put empty values at the bottom
        if (parsedA.type === 0 && parsedB.type !== 0) return 1;
        if (parsedB.type === 0 && parsedA.type !== 0) return -1;
        if (parsedA.type === 0 && parsedB.type === 0) return 0;

        let res = 0;
        if (parsedA.type === 1 && parsedB.type === 1) {
            res = parsedA.val - parsedB.val;
        } else {
            res = String(parsedA.val).localeCompare(String(parsedB.val), undefined, { numeric: true, sensitivity: 'base' });
        }

        return newAsc ? res : -res;
    });

    rows.forEach(r => tbody.appendChild(r));
}

// Auto-initialize sortable tables on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    ['motosTable', 'clientesTable', 'contratosTable', 'vistoriasTable', 'financeiroTable', 'usersTable', 'auditTable'].forEach(id => {
        enableTableSorting(id);
    });
});

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
