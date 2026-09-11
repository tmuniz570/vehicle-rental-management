/**
 * FF Motors - Shared UI Utilities
 * - Interactive Table Column Sorting
 * - Smart History Back Navigation
 */

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

function enableTableSorting(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;

    const thead = table.querySelector('thead');
    if (!thead) return;

    const headers = thead.querySelectorAll('th');
    headers.forEach((th, index) => {
        const title = th.textContent.trim().toLowerCase();
        // Ignore action / non-sortable columns
        if (title.includes('action') || title === 'actions' || title === 'edit' || title.includes('view') || title === 'documents' || title === 'doc' || title === 'docs') {
            return;
        }

        th.classList.add('sortable-th');
        th.setAttribute('title', 'Click to sort');
        if (!th.querySelector('.sort-indicator')) {
            const indicator = document.createElement('span');
            indicator.className = 'sort-indicator';
            indicator.textContent = '⇅';
            th.appendChild(indicator);
        }

        if (th._hasSortListener) return;
        th._hasSortListener = true;

        th.addEventListener('click', () => {
            sortTableByColumn(table, index);
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
    ['motosTable', 'clientesTable', 'contratosTable', 'vistoriasTable', 'financeiroTable', 'usersTable'].forEach(id => {
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
