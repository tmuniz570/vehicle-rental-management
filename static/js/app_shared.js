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
        // Ignore non-sortable columns unless explicitly marked with data-sort-field
        const title = th.textContent.trim().toLowerCase();
        const hasExplicitSortField = th.hasAttribute('data-sort-field');
        if (!hasExplicitSortField && (title.includes('action') || title === 'actions' || title === 'edit' || title.includes('view') || title === 'documents' || title === 'doc' || title === 'docs' || title === 'photos' || title === 'observations')) {
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
        { value: 'Exchange', label: 'Exchange (Vehicle Trade-in)' },
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
        const elNota = document.getElementById('pag_nota');
        if (elNota) elNota.value = '';
        updateRemoveButtons();
        recalculate();
    }

    function getPayload() {
        if (!container) return { metodos_pagamento: [], valor_pago: 0, is_partial: false, saldo_restante: 0, nota: '' };
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
        const elNota = document.getElementById('pag_nota');
        const nota = elNota ? elNota.value.trim() : '';

        return {
            metodos_pagamento: metodos,
            valor_pago: totalPaid,
            is_partial: isPartial,
            saldo_restante: Math.max(0, Math.round((currentTotalDue - totalPaid) * 100) / 100),
            nota: nota
        };
    }

    return {
        open,
        addRow,
        recalculate,
        getPayload
    };
}

/**
 * Universal WhatsApp Number Formatter for UK & International
 * Formats any phone input into a valid E.164 string without '+' or leading zeros,
 * ensuring seamless https://wa.me/<digits> deep-linking across the entire app.
 */
function formatWhatsAppNumber(phone) {
    if (!phone) return '';
    const raw = String(phone).trim();
    if (!raw) return '';

    // If starts with + (international format)
    if (raw.startsWith('+')) {
        let digits = raw.replace(/\D/g, '');
        // UK fix: if typed as +44 07..., strip the extra zero after 44
        if (digits.startsWith('440') && digits.length >= 12) {
            digits = '44' + digits.substring(3);
        }
        return digits;
    }

    // If starts with 00 (international dialing prefix)
    if (raw.startsWith('00')) {
        let digits = raw.replace(/\D/g, '').substring(2);
        if (digits.startsWith('440') && digits.length >= 12) {
            digits = '44' + digits.substring(3);
        }
        return digits;
    }

    const digits = raw.replace(/\D/g, '');
    if (!digits) return '';

    // Standard UK mobile: 07xxx xxx xxx (or any UK number starting with 0)
    if (digits.startsWith('0')) {
        return '44' + digits.substring(1);
    }

    // UK 10 digits without leading 0: 7xxx xxx xxx
    if (digits.startsWith('7') && digits.length === 10) {
        return '44' + digits;
    }

    // Already prefixed with 44
    if (digits.startsWith('44')) {
        if (digits.startsWith('440') && digits.length >= 12) {
            return '44' + digits.substring(3);
        }
        return digits;
    }

    return digits;
}
window.formatWhatsAppNumber = formatWhatsAppNumber;

/**
 * Universal Sleek Reminder Chip Formatter
 * Displays relative or timestamp badge for payment reminders sent via WhatsApp.
 */
function formatarLembreteEstetico(isoStr, staff) {
    if (!isoStr) return '';
    try {
        const d = new Date(isoStr);
        const now = new Date();
        const diffMs = now - d;
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

        let relText = '';
        if (diffMins < 2) {
            relText = 'Just now';
        } else if (diffMins < 60) {
            relText = `${diffMins}m ago`;
        } else if (diffHours < 24 && d.getDate() === now.getDate()) {
            relText = `Today ${d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}`;
        } else {
            relText = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });
        }

        const safeStaff = staff ? String(staff).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;') : '';
        const staffStr = safeStaff ? ` by ${safeStaff}` : '';
        const fullDateStr = d.toLocaleDateString('en-GB') + ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
        const title = `WhatsApp reminder recorded${staffStr} on ${fullDateStr}`;

        return `<span class="badge-reminded-pill" title="${title}" style="display:inline-flex; align-items:center; gap:2px; font-size:0.65rem; font-weight:600; color:#34d399; background:rgba(16, 185, 129, 0.12); border:1px solid rgba(16, 185, 129, 0.28); border-radius:10px; padding:0 5px; letter-spacing:0.2px; white-space:nowrap; line-height:1.2;">
            <span style="font-size:0.62rem;">✓</span>
            <span>${relText}</span>
        </span>`;
    } catch(e) {
        return '';
    }
}
window.formatarLembreteEstetico = formatarLembreteEstetico;

/**
 * Universal HTML Escape Helper
 */
if (typeof window.escapeHtml !== 'function') {
    window.escapeHtml = function(str) {
        if (str == null) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    };
}

/**
 * Universal Currency Formatter (GBP)
 */
if (typeof window.formatoMoeda === 'undefined') {
    window.formatoMoeda = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });
}

/**
 * Universal Quick Lookup Search (Navbar & Dashboard)
 */
function initQuickLookup() {
    const searchInput = document.getElementById('dashQuickSearch');
    const resultsBox = document.getElementById('dashSearchResults');
    const clearBtn = document.getElementById('dashQuickSearchClear');
    const kbdHint = document.getElementById('dashQuickSearchKbd');

    if (!searchInput || !resultsBox) return;

    let searchDebounceTimeout = null;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        if (clearBtn) clearBtn.style.display = query ? 'block' : 'none';
        if (kbdHint) kbdHint.style.display = query ? 'none' : 'block';

        if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);
        if (!query || query.length < 2) {
            resultsBox.style.display = 'none';
            resultsBox.innerHTML = '';
            return;
        }

        searchDebounceTimeout = setTimeout(async () => {
            try {
                resultsBox.innerHTML = '<div style="padding: 0.75rem; text-align: center; color: var(--text-secondary); font-size: 0.85rem;">Searching...</div>';
                resultsBox.style.display = 'block';

                const res = await fetch(`/api/busca-rapida?q=${encodeURIComponent(query)}`);
                if (!res.ok) {
                    if (res.status === 403) {
                        resultsBox.style.display = 'none';
                        return;
                    }
                    throw new Error(`HTTP ${res.status}`);
                }
                const data = await res.json();

                const motos = data.motos || [];
                const clientes = data.clientes || [];
                const contratos = data.contratos || [];

                if (motos.length === 0 && clientes.length === 0 && contratos.length === 0) {
                    resultsBox.innerHTML = '<div style="padding: 0.85rem; text-align: center; color: var(--text-secondary); font-size: 0.85rem;">No motorbikes, customers, or contracts found.</div>';
                    return;
                }

                let outHtml = '';

                // 1. Motorbikes Section
                if (motos.length > 0) {
                    outHtml += `<div class="search-section-title" style="color: var(--accent);">🛵 Motorbikes (${motos.length})</div>`;
                    motos.forEach(m => {
                        let statusColor = 'var(--text-secondary)';
                        if (m.status === 'Available') statusColor = 'var(--success)';
                        else if (m.status === 'Rented') statusColor = 'var(--accent)';
                        else if (m.status === 'Maintenance') statusColor = '#f59e0b';
                        else if (m.status === 'Pound') statusColor = '#ef4444';
                        else if (m.status === 'Sold') statusColor = '#94a3b8';

                        const motoFleetUrl = `/motos?search=${encodeURIComponent(m.placa)}&status=all`;
                        const agreementId = m.contract_id || m.contrato_ativo_id;

                        const hirerTel = m.hirer_telefone || '';
                        const hirerWaNum = (hirerTel && typeof formatWhatsAppNumber === 'function') ? formatWhatsAppNumber(hirerTel) : '';
                        const hirerWaMsg = encodeURIComponent(`Hello ${m.hirer_name || m.cliente_atual || ''}, this is FF Motors regarding motorbike ${m.placa || ''}: `);
                        const hirerWaBtn = hirerWaNum ? `<a href="https://wa.me/${hirerWaNum}?text=${hirerWaMsg}" target="_blank" rel="noopener noreferrer" style="text-decoration:none; margin-left:4px; font-size:0.82rem;" title="WhatsApp ${escapeHtml(m.hirer_name || m.cliente_atual)}" onclick="event.stopPropagation();">💬</a>` : '';

                        outHtml += `
                            <div class="search-result-card">
                                <a href="${motoFleetUrl}" class="search-card-main">
                                    <div class="search-card-header">
                                        <span class="badge" style="font-family: monospace; font-weight: 700; font-size: 0.85rem; padding: 2px 6px; background: rgba(255,255,255,0.08); color: var(--text-primary); border: 1px solid var(--border-color);">
                                            ${escapeHtml(m.placa)}
                                        </span>
                                        <strong style="font-size: 0.88rem; color: var(--text-primary);">
                                            ${escapeHtml(m.modelo)}
                                        </strong>
                                        <small style="color: var(--text-secondary);">(${escapeHtml(m.cor || 'Bike')})</small>
                                        <span style="font-size: 0.75rem; font-weight: 600; color: ${statusColor}; margin-left: auto;">● ${escapeHtml(m.status)}</span>
                                    </div>
                                    <div class="search-card-details">
                                        ${(m.hirer_name || m.cliente_atual) ? `<span>👤 Driver: <strong style="color: var(--text-primary);">${escapeHtml(m.hirer_name || m.cliente_atual)}</strong>${hirerWaBtn}</span>` : `<span style="color: var(--text-secondary);">No active driver</span>`}
                                        ${m.milhagem ? `<span style="margin-left: 8px;">• ${Number(m.milhagem).toLocaleString()} miles</span>` : ''}
                                    </div>
                                </a>
                                <div class="search-card-actions">
                                    ${agreementId ? `
                                        <a href="/contratos/${agreementId}" class="dash-search-btn accent" title="Open Contract #${agreementId}">
                                            Agreement #${agreementId} ↗
                                        </a>
                                    ` : ''}
                                    <a href="${motoFleetUrl}" class="dash-search-btn" title="View Motorbike in Fleet">
                                        Fleet ↗
                                    </a>
                                </div>
                            </div>
                        `;
                    });
                }

                // 2. Customers Section
                if (clientes.length > 0) {
                    if (motos.length > 0) outHtml += `<div style="height: 1px; background: var(--border-color); margin: 6px 0;"></div>`;
                    outHtml += `<div class="search-section-title" style="color: #60a5fa;">👤 Customers (${clientes.length})</div>`;
                    clientes.forEach(c => {
                        const clientUrl = `/clientes?search=${encodeURIComponent(c.nome)}`;
                        const agreementId = c.contract_id || c.contrato_ativo_id;

                        let typeBadge = '';
                        if (c.contract_type) {
                            let typeName = c.contract_type;
                            if (typeName === 'Sale_Installment') typeName = 'Financed';
                            else if (typeName === 'Sale_Full') typeName = 'Sale';
                            else if (typeName === 'Rent') typeName = 'Rental';
                            typeBadge = `<span class="badge" style="font-size: 0.7rem; padding: 1px 6px; background: rgba(59,130,246,0.14); color: #60a5fa; border: 1px solid rgba(59,130,246,0.28); flex-shrink: 0; font-weight: 600;">${escapeHtml(typeName)}</span>`;
                        }

                        const waNum = (c.telefone && typeof formatWhatsAppNumber === 'function') ? formatWhatsAppNumber(c.telefone) : '';
                        const custWaMsg = encodeURIComponent(`Hello ${c.nome || ''}, this is FF Motors: `);
                        const waBtn = waNum ? `<a href="https://wa.me/${waNum}?text=${custWaMsg}" target="_blank" rel="noopener noreferrer" style="text-decoration:none; margin-left:4px; font-size:0.85rem;" title="Chat with ${escapeHtml(c.nome)} on WhatsApp" onclick="event.stopPropagation();">💬</a>` : '';

                        outHtml += `
                            <div class="search-result-card">
                                <a href="${clientUrl}" class="search-card-main">
                                    <div class="search-card-header">
                                        <span style="font-size: 0.95rem; flex-shrink: 0;">👤</span>
                                        <strong style="font-size: 0.88rem; color: var(--text-primary);">
                                            ${escapeHtml(c.nome)}
                                        </strong>
                                        ${typeBadge}
                                    </div>
                                    <div class="search-card-details">
                                        ${c.moto_placa ? `<span style="color: var(--accent); font-weight: 600; flex-shrink: 0;">🛵 ${escapeHtml(c.moto_placa)}</span>` : ''}
                                        ${c.telefone ? `<span style="display:inline-flex; align-items:center;">📞 ${escapeHtml(c.telefone)}${waBtn}</span>` : ''}
                                        ${c.email ? `<span style="margin-left: 6px;">✉️ ${escapeHtml(c.email)}</span>` : ''}
                                        ${(!c.telefone && !c.email && !c.moto_placa) ? `<span>No active contract or contact info</span>` : ''}
                                    </div>
                                </a>
                                <div class="search-card-actions">
                                    ${agreementId ? `
                                        <a href="/contratos/${agreementId}" class="dash-search-btn green" title="Open Agreement #${agreementId}">
                                            Agreement #${agreementId} ↗
                                        </a>
                                    ` : ''}
                                    <a href="${clientUrl}" class="dash-search-btn" title="View Customer Profile">
                                        Customer ↗
                                    </a>
                                </div>
                            </div>
                        `;
                    });
                }

                // 3. Contracts Section
                if (contratos.length > 0) {
                    if (motos.length > 0 || clientes.length > 0) outHtml += `<div style="height: 1px; background: var(--border-color); margin: 6px 0;"></div>`;
                    outHtml += `<div class="search-section-title" style="color: #c084fc;">📄 Agreements & Contracts (${contratos.length})</div>`;
                    contratos.forEach(ct => {
                        const contractUrl = `/contratos/${ct.id}`;
                        let typeBadgeClr = 'background: rgba(255,102,0,0.15); color: var(--accent); border: 1px solid rgba(255,102,0,0.3);';
                        if (ct.tipo === 'Sale_Installment' || ct.tipo === 'Sale_Full') {
                            typeBadgeClr = 'background: rgba(59,130,246,0.15); color: #60a5fa; border: 1px solid rgba(59,130,246,0.3);';
                        } else if (ct.tipo === 'Purchase') {
                            typeBadgeClr = 'background: rgba(6,182,212,0.15); color: #22d3ee; border: 1px solid rgba(6,182,212,0.3);';
                        }

                        const curFmt = (typeof formatoMoeda !== 'undefined') ? formatoMoeda : new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });

                        outHtml += `
                            <div class="search-result-card">
                                <a href="${contractUrl}" class="search-card-main">
                                    <div class="search-card-header">
                                        <span class="badge" style="font-family: monospace; font-weight: 700; font-size: 0.85rem; padding: 2px 6px; background: rgba(255,255,255,0.08); color: var(--text-primary); border: 1px solid var(--border-color);">
                                            #${ct.id}
                                        </span>
                                        <span class="badge" style="${typeBadgeClr} font-size: 0.72rem; padding: 1px 6px;">
                                            ${escapeHtml(ct.tipo)}
                                        </span>
                                        <span style="font-family: monospace; font-weight: 600; font-size: 0.82rem; color: var(--text-primary);">
                                            ${escapeHtml(ct.placa)}
                                        </span>
                                        <span class="badge" style="font-size: 0.7rem; padding: 1px 6px; background: rgba(255,255,255,0.05); color: var(--text-secondary); margin-left: auto;">
                                            ${escapeHtml(ct.status)}
                                        </span>
                                    </div>
                                    <div class="search-card-details">
                                        <span>👤 Customer: <strong style="color: var(--text-primary);">${escapeHtml(ct.cliente)}</strong></span>
                                        ${ct.valor ? `<span style="margin-left: 8px;">• ${curFmt.format(Number(ct.valor))}</span>` : ''}
                                    </div>
                                </a>
                                <div class="search-card-actions">
                                    <a href="${contractUrl}" class="dash-search-btn accent" title="Open Contract #${ct.id}">
                                        Open ↗
                                    </a>
                                </div>
                            </div>
                        `;
                    });
                }

                resultsBox.innerHTML = outHtml;
            } catch (err) {
                console.error('Quick lookup error:', err);
                resultsBox.innerHTML = '<div style="padding: 0.75rem; text-align: center; color: #f87171; font-size: 0.85rem;">Error searching records.</div>';
            }
        }, 220);
    });

    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeQuickLookupModal();
        }
    });

    // Global keyboard shortcut: Ctrl+K, Cmd+K, or '/' (when not typing in other inputs)
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            const modal = document.getElementById('quickLookupModal');
            if (modal && modal.style.display !== 'none') {
                closeQuickLookupModal();
            } else {
                openQuickLookupModal();
            }
        } else if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
            e.preventDefault();
            openQuickLookupModal();
        } else if (e.key === 'Escape') {
            closeQuickLookupModal();
        }
    });
}

function openQuickLookupModal() {
    const modal = document.getElementById('quickLookupModal');
    const searchInput = document.getElementById('dashQuickSearch');
    if (!modal) return;
    modal.style.display = 'flex';
    document.body.classList.add('quick-lookup-open');
    if (searchInput) {
        setTimeout(() => {
            searchInput.focus();
            searchInput.select();
        }, 50);
    }
}
window.openQuickLookupModal = openQuickLookupModal;

function closeQuickLookupModal() {
    const modal = document.getElementById('quickLookupModal');
    const searchInput = document.getElementById('dashQuickSearch');
    if (!modal) return;
    modal.style.display = 'none';
    document.body.classList.remove('quick-lookup-open');
    if (searchInput) {
        searchInput.blur();
    }
}
window.closeQuickLookupModal = closeQuickLookupModal;

function handleQuickLookupBackdropClick(e) {
    if (e.target && e.target.id === 'quickLookupModal') {
        closeQuickLookupModal();
    }
}
window.handleQuickLookupBackdropClick = handleQuickLookupBackdropClick;

function clearQuickSearch() {
    const searchInput = document.getElementById('dashQuickSearch');
    const resultsBox = document.getElementById('dashSearchResults');
    const clearBtn = document.getElementById('dashQuickSearchClear');

    if (searchInput) {
        searchInput.value = '';
        searchInput.focus();
    }
    if (clearBtn) clearBtn.style.display = 'none';
    if (resultsBox) {
        resultsBox.style.display = 'none';
        resultsBox.innerHTML = '';
    }
}
window.clearQuickSearch = clearQuickSearch;

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initQuickLookup);
} else {
    initQuickLookup();
}




