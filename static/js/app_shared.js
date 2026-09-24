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

/**
 * Universal Inspection Photo Carousel Component
 * @param {HTMLElement|string} container - The DOM element or ID where the carousel will be rendered
 * @param {Array<string>|string} photos - Array of image URLs or comma-separated string
 */
function renderInspectionCarousel(container, photos) {
    const el = typeof container === 'string' ? document.getElementById(container) : container;
    if (!el) return;
    el.innerHTML = '';

    const photosList = Array.isArray(photos) 
        ? photos.map(p => String(p).trim()).filter(Boolean)
        : (photos ? String(photos).split(',').map(p => p.trim()).filter(Boolean) : []);

    if (photosList.length === 0) {
        el.innerHTML = `
            <div class="carousel-empty-state">
                <span style="font-size: 2rem; display: block; margin-bottom: 0.5rem; opacity: 0.7;">📷</span>
                <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">No photos attached to this inspection.</p>
            </div>
        `;
        return;
    }

    let currentIndex = 0;
    const total = photosList.length;

    const wrapper = document.createElement('div');
    wrapper.className = 'inspection-carousel';

    // Main Stage
    const stage = document.createElement('div');
    stage.className = 'carousel-stage';

    const link = document.createElement('a');
    link.className = 'carousel-main-link';
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.title = 'Click to open in full resolution (opens in new tab)';

    const img = document.createElement('img');
    img.className = 'carousel-main-img';
    img.loading = 'lazy';
    link.appendChild(img);

    const zoomHint = document.createElement('span');
    zoomHint.className = 'carousel-zoom-hint';
    zoomHint.innerHTML = '🔍 Enlarge';
    link.appendChild(zoomHint);

    stage.appendChild(link);

    // Counter Badge
    const counterBadge = document.createElement('div');
    counterBadge.className = 'carousel-counter-badge';
    stage.appendChild(counterBadge);

    // Prev / Next buttons (only if multiple photos)
    let btnPrev = null;
    let btnNext = null;
    if (total > 1) {
        btnPrev = document.createElement('button');
        btnPrev.type = 'button';
        btnPrev.className = 'carousel-nav-btn carousel-prev';
        btnPrev.setAttribute('aria-label', 'Previous photo');
        btnPrev.innerHTML = '&#10094;';

        btnNext = document.createElement('button');
        btnNext.type = 'button';
        btnNext.className = 'carousel-nav-btn carousel-next';
        btnNext.setAttribute('aria-label', 'Next photo');
        btnNext.innerHTML = '&#10095;';

        stage.appendChild(btnPrev);
        stage.appendChild(btnNext);
    }

    wrapper.appendChild(stage);

    // Thumbnails Track (only if multiple photos)
    const thumbElements = [];
    if (total > 1) {
        const thumbsTrack = document.createElement('div');
        thumbsTrack.className = 'carousel-thumbs-track';

        photosList.forEach((url, idx) => {
            const thumb = document.createElement('button');
            thumb.type = 'button';
            thumb.className = `carousel-thumb ${idx === 0 ? 'active' : ''}`;
            thumb.setAttribute('aria-label', `Go to photo ${idx + 1}`);
            thumb.innerHTML = `<img src="${url}" alt="Thumbnail ${idx + 1}" loading="lazy">`;
            thumb.addEventListener('click', (e) => {
                e.preventDefault();
                goToSlide(idx);
            });
            thumbsTrack.appendChild(thumb);
            thumbElements.push(thumb);
        });

        wrapper.appendChild(thumbsTrack);
    }

    function updateSlide() {
        const url = photosList[currentIndex];
        img.src = url;
        img.alt = `Inspection Photo ${currentIndex + 1} of ${total}`;
        link.href = url;
        counterBadge.textContent = `Photo ${currentIndex + 1} / ${total}`;

        if (thumbElements.length > 0) {
            thumbElements.forEach((t, i) => {
                if (i === currentIndex) {
                    t.classList.add('active');
                    t.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
                } else {
                    t.classList.remove('active');
                }
            });
        }
    }

    function goToSlide(index) {
        currentIndex = (index + total) % total;
        updateSlide();
    }

    if (btnPrev) {
        btnPrev.addEventListener('click', (e) => {
            e.preventDefault();
            goToSlide(currentIndex - 1);
        });
    }

    if (btnNext) {
        btnNext.addEventListener('click', (e) => {
            e.preventDefault();
            goToSlide(currentIndex + 1);
        });
    }

    // Touch Swipe on mobile
    let touchStartX = 0;
    let touchStartY = 0;
    stage.addEventListener('touchstart', (e) => {
        if (e.touches && e.touches.length === 1) {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        }
    }, { passive: true });

    stage.addEventListener('touchend', (e) => {
        if (total <= 1 || !e.changedTouches || e.changedTouches.length === 0) return;
        const diffX = e.changedTouches[0].clientX - touchStartX;
        const diffY = e.changedTouches[0].clientY - touchStartY;
        if (Math.abs(diffX) > 40 && Math.abs(diffX) > Math.abs(diffY) * 1.5) {
            if (diffX < 0) {
                goToSlide(currentIndex + 1);
            } else {
                goToSlide(currentIndex - 1);
            }
        }
    }, { passive: true });

    // Keyboard Arrow Keys navigation
    const keyHandler = (e) => {
        if (total <= 1) return;
        const modal = el.closest('.modal-overlay');
        if (!modal || !modal.classList.contains('active')) return;
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            goToSlide(currentIndex - 1);
        } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            goToSlide(currentIndex + 1);
        }
    };
    document.addEventListener('keydown', keyHandler);

    updateSlide();
    el.appendChild(wrapper);
}

/**
 * 4. Universal Split & Partial Payment Modal Manager
 * Manages dynamic payment method rows, real-time balance calculations,
 * and payload formatting for mark payment modals.
 */
function createSplitPaymentManager({
    containerId = 'paymentMethodsList',
    btnAddId = 'btnAddPaymentMethod',
    sumPayingId = 'sumPayingNow',
    sumRemainingId = 'sumRemaining',
    badgeId = 'paymentStatusBadge',
    btnSubmitId = 'btnConfirmarPag',
    formatoMoeda = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' })
} = {}) {
    let currentTotalDue = 0;
    const container = document.getElementById(containerId);
    const btnAdd = document.getElementById(btnAddId);
    const elSumPaying = document.getElementById(sumPayingId);
    const elSumRemaining = document.getElementById(sumRemainingId);
    const elBadge = document.getElementById(badgeId);
    const btnSubmit = document.getElementById(btnSubmitId);

    const PAYMENT_METHODS = [
        { value: 'Cash', label: 'Cash' },
        { value: 'Card', label: 'Card' },
        { value: 'Bank Transfer', label: 'Bank Transfer' },
        { value: 'Deposit', label: 'Deposit (Deducted)' },
        { value: 'Other', label: 'Other' }
    ];

    function renderRow(method = 'Cash', amount = 0) {
        const row = document.createElement('div');
        row.className = 'payment-method-row';
        row.style.cssText = 'display: grid; grid-template-columns: 1fr 130px 36px; gap: 8px; align-items: center;';

        const optionsHtml = PAYMENT_METHODS.map(m => 
            `<option value="${m.value}" ${m.value === method ? 'selected' : ''}>${m.label}</option>`
        ).join('');

        row.innerHTML = `
            <select class="pag-method-select" style="background: var(--input-bg); color: var(--text-primary); border: 1px solid var(--input-border); padding: 0.65rem 0.75rem; border-radius: 10px; font-size: 0.9rem; outline: none; width: 100%;">
                ${optionsHtml}
            </select>
            <div style="position: relative; width: 100%;">
                <span style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: var(--text-secondary); font-size: 0.9rem; pointer-events: none;">£</span>
                <input type="number" step="0.01" min="0.01" class="pag-amount-input" value="${amount > 0 ? amount.toFixed(2) : ''}" placeholder="0.00" style="background: var(--input-bg); color: var(--text-primary); border: 1px solid var(--input-border); padding: 0.65rem 0.65rem 0.65rem 1.6rem; border-radius: 10px; font-size: 0.95rem; font-weight: 600; width: 100%; box-sizing: border-box; outline: none;">
            </div>
            <button type="button" class="btn-remove-method" title="Remove method" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; width: 36px; height: 38px; border-radius: 8px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s ease;">
                <svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
            </button>
        `;

        const amountInput = row.querySelector('.pag-amount-input');
        const methodSelect = row.querySelector('.pag-method-select');
        const btnRemove = row.querySelector('.btn-remove-method');

        amountInput.addEventListener('input', recalculate);
        methodSelect.addEventListener('change', recalculate);
        btnRemove.addEventListener('click', () => {
            row.remove();
            updateRemoveButtons();
            recalculate();
        });

        return row;
    }

    function updateRemoveButtons() {
        if (!container) return;
        const rows = container.querySelectorAll('.payment-method-row');
        rows.forEach(r => {
            const btnRemove = r.querySelector('.btn-remove-method');
            if (btnRemove) {
                btnRemove.style.visibility = rows.length > 1 ? 'visible' : 'hidden';
            }
        });
    }

    function recalculate() {
        if (!container) return;
        const rows = container.querySelectorAll('.payment-method-row');
        let totalPaid = 0;

        rows.forEach(r => {
            const input = r.querySelector('.pag-amount-input');
            const val = parseFloat(input?.value) || 0;
            totalPaid += val;
        });

        totalPaid = Math.round(totalPaid * 100) / 100;
        const remaining = Math.max(0, Math.round((currentTotalDue - totalPaid) * 100) / 100);

        if (elSumPaying) elSumPaying.textContent = formatoMoeda.format(totalPaid);
        if (elSumRemaining) elSumRemaining.textContent = formatoMoeda.format(remaining);

        if (elBadge && btnSubmit) {
            const diff = Math.round((currentTotalDue - totalPaid) * 100) / 100;
            if (totalPaid <= 0) {
                elBadge.innerHTML = `<span style="color:var(--text-secondary);">Enter valid payment amount(s)</span>`;
                elBadge.style.background = 'rgba(255,255,255,0.04)';
                elBadge.style.border = '1px solid var(--border-color)';
                btnSubmit.disabled = true;
                btnSubmit.textContent = 'Confirm Payment';
            } else if (diff < -0.009) {
                elBadge.innerHTML = `<span style="color:#f87171;">✕ Paid amount (${formatoMoeda.format(totalPaid)}) exceeds total due (${formatoMoeda.format(currentTotalDue)})</span>`;
                elBadge.style.background = 'rgba(239, 68, 68, 0.15)';
                elBadge.style.border = '1px solid rgba(239, 68, 68, 0.3)';
                btnSubmit.disabled = true;
                btnSubmit.textContent = 'Amount Exceeds Due';
            } else if (diff > 0.009) {
                elBadge.innerHTML = `<span style="color:#fbbf24;">⚠️ Partial Payment: ${formatoMoeda.format(remaining)} will remain Pending</span>`;
                elBadge.style.background = 'rgba(245, 158, 11, 0.15)';
                elBadge.style.border = '1px solid rgba(245, 158, 11, 0.3)';
                btnSubmit.disabled = false;
                btnSubmit.textContent = `Confirm Partial Payment (${formatoMoeda.format(totalPaid)})`;
            } else {
                elBadge.innerHTML = `<span style="color:#34d399;">✓ Full Settlement (${formatoMoeda.format(totalPaid)})</span>`;
                elBadge.style.background = 'rgba(16, 185, 129, 0.15)';
                elBadge.style.border = '1px solid rgba(16, 185, 129, 0.3)';
                btnSubmit.disabled = false;
                btnSubmit.textContent = `Confirm Payment (${formatoMoeda.format(totalPaid)})`;
            }
        }
    }

    function addRow(suggestedAmount = null, defaultMethod = 'Card') {
        if (!container) return;
        if (suggestedAmount === null) {
            let currentPaid = 0;
            container.querySelectorAll('.pag-amount-input').forEach(inp => {
                currentPaid += parseFloat(inp.value) || 0;
            });
            const rem = Math.max(0, Math.round((currentTotalDue - currentPaid) * 100) / 100);
            suggestedAmount = rem > 0 ? rem : 0;
        }

        const newRow = renderRow(defaultMethod, suggestedAmount);
        container.appendChild(newRow);
        updateRemoveButtons();
        recalculate();
        const inp = newRow.querySelector('.pag-amount-input');
        if (inp) {
            inp.focus();
            inp.select();
        }
    }

    if (btnAdd) {
        btnAdd.addEventListener('click', (e) => {
            e.preventDefault();
            let usedMethods = [];
            if (container) {
                container.querySelectorAll('.pag-method-select').forEach(s => usedMethods.push(s.value));
            }
            let nextMethod = 'Card';
            if (usedMethods.includes('Cash') && !usedMethods.includes('Card')) nextMethod = 'Card';
            else if (usedMethods.includes('Card') && !usedMethods.includes('Bank Transfer')) nextMethod = 'Bank Transfer';
            else if (usedMethods.includes('Bank Transfer') && !usedMethods.includes('Cash')) nextMethod = 'Cash';

            addRow(null, nextMethod);
        });
    }

    function open(totalDue, defaultMethod = 'Cash') {
        currentTotalDue = parseFloat(totalDue) || 0;
        if (container) {
            container.innerHTML = '';
            container.appendChild(renderRow(defaultMethod, currentTotalDue));
        }
        updateRemoveButtons();
        recalculate();
    }

    function getPayload() {
        if (!container) return { metodos_pagamento: [], valor_pago: 0, is_partial: false, saldo_restante: 0 };
        const rows = container.querySelectorAll('.payment-method-row');
        const metodos = [];
        let totalPaid = 0;

        rows.forEach(r => {
            const forma = r.querySelector('.pag-method-select')?.value || 'Cash';
            const val = parseFloat(r.querySelector('.pag-amount-input')?.value) || 0;
            if (forma && val > 0) {
                metodos.push({ forma, valor: val });
                totalPaid += val;
            }
        });

        totalPaid = Math.round(totalPaid * 100) / 100;
        const isPartial = (currentTotalDue - totalPaid) > 0.009;

        return {
            metodos_pagamento: metodos,
            valor_pago: totalPaid,
            is_partial: isPartial,
            saldo_restante: Math.max(0, Math.round((currentTotalDue - totalPaid) * 100) / 100)
        };
    }

    return {
        open,
        addRow,
        recalculate,
        getPayload
    };
}

