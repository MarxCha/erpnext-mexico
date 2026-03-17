/**
 * DIOT 2025 — Client-side controller
 * Frappe Page: mx-diot-report
 *
 * Provides:
 *   1. Empresa / Mes / Año selectors
 *   2. Preview table — calls generate_diot API and renders supplier breakdown
 *   3. Download TXT button — triggers file download via download_diot API
 *
 * Security: all user-supplied and API-returned strings are set via
 * textContent only — never via raw dynamic markup injection.
 */

// ─── Design tokens (shared palette with mx-fiscal-dashboard) ─────────────────

(function injectStyles() {
    if (document.getElementById('mx-diot-styles')) return;
    const style = document.createElement('style');
    style.id = 'mx-diot-styles';
    style.textContent = `
  :root {
    --mx-accent:         #0052CC;
    --mx-accent-hover:   #0747A6;
    --mx-accent-light:   #DEEBFF;
    --mx-success:        #10B981;
    --mx-success-bg:     #D1FAE5;
    --mx-warning:        #F59E0B;
    --mx-warning-bg:     #FEF3C7;
    --mx-error:          #EF4444;
    --mx-error-bg:       #FEE2E2;
    --mx-bg-primary:     #FFFFFF;
    --mx-bg-secondary:   #F8FAFC;
    --mx-bg-tertiary:    #EDF2F7;
    --mx-border:         #E2E8F0;
    --mx-text-primary:   #1A202C;
    --mx-text-secondary: #4A5568;
    --mx-text-muted:     #718096;
    --mx-font-sans:      'DM Sans','Nunito',system-ui,sans-serif;
    --mx-font-mono:      'JetBrains Mono','Fira Code',monospace;
    --mx-radius-sm:      6px;
    --mx-radius-md:      8px;
    --mx-radius-lg:      12px;
    --mx-space-2:  8px;
    --mx-space-3: 12px;
    --mx-space-4: 16px;
    --mx-space-5: 20px;
    --mx-space-6: 24px;
    --mx-space-8: 32px;
    --mx-shadow-card:  0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.04);
    --mx-shadow-hover: 0 4px 12px rgba(0,0,0,.10);
  }

  .mx-diot-page { background:var(--mx-bg-secondary); font-family:var(--mx-font-sans); color:var(--mx-text-primary); }
  .mx-diot-body { padding:var(--mx-space-6); max-width:1280px; display:flex; flex-direction:column; gap:var(--mx-space-6); }

  .mx-diot-filters {
    background:var(--mx-bg-primary); border:1px solid var(--mx-border);
    border-radius:var(--mx-radius-lg); padding:var(--mx-space-5);
    box-shadow:var(--mx-shadow-card); display:flex; flex-wrap:wrap;
    align-items:flex-end; gap:var(--mx-space-4);
  }
  .mx-diot-filter-group { display:flex; flex-direction:column; gap:6px; min-width:180px; }
  .mx-diot-filter-group label {
    font-size:11px; font-weight:600; letter-spacing:.06em;
    text-transform:uppercase; color:var(--mx-text-muted);
  }
  .mx-diot-filter-group select,
  .mx-diot-filter-group input {
    border:1px solid var(--mx-border); border-radius:var(--mx-radius-md);
    padding:7px 10px; font-size:13px; font-family:var(--mx-font-sans);
    color:var(--mx-text-primary); background:var(--mx-bg-primary);
    outline:none; transition:border-color .15s;
  }
  .mx-diot-filter-group select:focus,
  .mx-diot-filter-group input:focus { border-color:var(--mx-accent); }

  .mx-diot-actions { display:flex; gap:var(--mx-space-3); flex-wrap:wrap; align-items:center; margin-top:4px; }
  .mx-btn {
    display:inline-flex; align-items:center; gap:6px;
    padding:8px 18px; border-radius:var(--mx-radius-md);
    font-size:13px; font-weight:600; font-family:var(--mx-font-sans);
    cursor:pointer; border:none; transition:all .15s ease;
    text-decoration:none; white-space:nowrap;
  }
  .mx-btn:disabled { opacity:.5; cursor:not-allowed; }
  .mx-btn--primary { background:var(--mx-accent); color:#fff; }
  .mx-btn--primary:hover:not(:disabled) { background:var(--mx-accent-hover); }
  .mx-btn--secondary {
    background:var(--mx-bg-primary); color:var(--mx-text-secondary);
    border:1px solid var(--mx-border); box-shadow:var(--mx-shadow-card);
  }
  .mx-btn--secondary:hover:not(:disabled) {
    border-color:var(--mx-accent); color:var(--mx-accent);
    box-shadow:var(--mx-shadow-hover);
  }
  .mx-btn--success { background:var(--mx-success); color:#fff; }
  .mx-btn--success:hover:not(:disabled) { background:#059669; }

  .mx-diot-summary {
    display:grid; grid-template-columns:repeat(4,1fr); gap:var(--mx-space-4);
  }
  @media(max-width:900px) { .mx-diot-summary { grid-template-columns:repeat(2,1fr); } }
  .mx-sum-card {
    background:var(--mx-bg-primary); border:1px solid var(--mx-border);
    border-radius:var(--mx-radius-lg); padding:var(--mx-space-5);
    box-shadow:var(--mx-shadow-card);
  }
  .mx-sum-card__label {
    font-size:11px; font-weight:600; letter-spacing:.06em;
    text-transform:uppercase; color:var(--mx-text-muted); margin-bottom:6px;
  }
  .mx-sum-card__value {
    font-size:22px; font-weight:800; color:var(--mx-text-primary);
    line-height:1.2; letter-spacing:-.02em; font-family:var(--mx-font-mono);
  }

  .mx-diot-table-card {
    background:var(--mx-bg-primary); border:1px solid var(--mx-border);
    border-radius:var(--mx-radius-lg); padding:var(--mx-space-5);
    box-shadow:var(--mx-shadow-card); overflow-x:auto;
  }
  .mx-section-title {
    font-size:13px; font-weight:700; letter-spacing:.04em;
    text-transform:uppercase; color:var(--mx-text-secondary);
    margin-bottom:var(--mx-space-4);
    display:flex; align-items:center; justify-content:space-between;
  }
  .mx-diot-table { width:100%; border-collapse:collapse; font-size:13px; min-width:900px; }
  .mx-diot-table th {
    text-align:left; font-size:11px; font-weight:600; letter-spacing:.06em;
    text-transform:uppercase; color:var(--mx-text-muted);
    padding:0 10px 10px; border-bottom:2px solid var(--mx-border);
    white-space:nowrap;
  }
  .mx-diot-table th.num { text-align:right; }
  .mx-diot-table td {
    padding:10px; border-bottom:1px solid var(--mx-bg-tertiary);
    color:var(--mx-text-secondary); vertical-align:middle;
  }
  .mx-diot-table td.num {
    text-align:right; font-family:var(--mx-font-mono); font-size:12px;
  }
  .mx-diot-table tr:last-child td { border-bottom:none; font-weight:700; color:var(--mx-text-primary); }
  .mx-diot-table tr:not(:last-child):hover td { background:var(--mx-bg-secondary); }
  .mx-rfc-cell { font-family:var(--mx-font-mono); font-size:12px; font-weight:600; letter-spacing:.05em; }

  .mx-badge {
    display:inline-block; padding:2px 8px; border-radius:999px;
    font-size:10px; font-weight:700; letter-spacing:.06em; text-transform:uppercase;
  }
  .mx-badge--nacional   { background:var(--mx-accent-light); color:#0747A6; }
  .mx-badge--extranjero { background:var(--mx-warning-bg);   color:#92400E; }
  .mx-badge--global     { background:var(--mx-bg-tertiary);  color:#374151; }

  .mx-empty {
    text-align:center; padding:var(--mx-space-8) var(--mx-space-4);
    color:var(--mx-text-muted);
  }
  .mx-empty__icon  { font-size:48px; margin-bottom:var(--mx-space-3); }
  .mx-empty__title { font-size:15px; font-weight:700; color:var(--mx-text-secondary); margin-bottom:6px; }
  .mx-empty__text  { font-size:13px; max-width:360px; margin:0 auto; line-height:1.6; }

  @keyframes mx-shimmer {
    0%   { background-position:-600px 0 }
    100% { background-position:600px 0  }
  }
  .mx-skeleton {
    background:linear-gradient(90deg,var(--mx-bg-tertiary) 25%,var(--mx-border) 50%,var(--mx-bg-tertiary) 75%);
    background-size:1200px 100%; animation:mx-shimmer 1.4s infinite linear;
    border-radius:var(--mx-radius-sm);
  }

  .mx-info-banner {
    background:var(--mx-accent-light); border:1px solid #B3D4FF;
    border-radius:var(--mx-radius-md); padding:var(--mx-space-3) var(--mx-space-4);
    font-size:13px; color:#0747A6; display:flex; align-items:flex-start; gap:8px;
  }
    `;
    document.head.appendChild(style);
}());

// ─── Page lifecycle ────────────────────────────────────────────────────────────

frappe.pages['mx-diot-report'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('DIOT 2025 — Declaración Informativa de Operaciones con Terceros'),
        single_column: true,
    });

    page.main.addClass('mx-diot-page');
    page._diot_state = { data: null, loading: false };

    render_page(page);
};

frappe.pages['mx-diot-report'].on_page_show = function () {
    // Intentionally empty — refresh is manual
};

// ─── Main page render ──────────────────────────────────────────────────────────

function render_page(page) {
    page.main.empty();

    const body = el('div', { className: 'mx-diot-body' });

    body.appendChild(build_info_banner());
    body.appendChild(build_filters(page));

    const resultsArea = el('div', { id: 'mx-diot-results' });
    body.appendChild(resultsArea);

    page.main.get(0).appendChild(body);
    page._results_area = resultsArea;
}

// ─── Info banner ───────────────────────────────────────────────────────────────

function build_info_banner() {
    const banner = el('div', { className: 'mx-info-banner' });
    const icon = el('span');
    icon.textContent = 'i';
    const text = el('span');
    text.textContent = __(
        'La DIOT se presenta mensualmente ante el SAT a más tardar el día 17 del mes siguiente. ' +
        'Genere el archivo TXT y súbalo al portal declarasat.sat.gob.mx.'
    );
    banner.append(icon, text);
    return banner;
}

// ─── Filter card ───────────────────────────────────────────────────────────────

function build_filters(page) {
    const card = el('div', { className: 'mx-diot-filters' });

    // Company selector
    const companyGroup = el('div', { className: 'mx-diot-filter-group' });
    const companyLabel = el('label');
    companyLabel.textContent = __('Empresa');
    companyLabel.setAttribute('for', 'mx-diot-company');
    const companySelect = el('select', { id: 'mx-diot-company' });
    const companyPlaceholder = el('option', { value: '' });
    companyPlaceholder.textContent = __('Seleccionar empresa...');
    companySelect.appendChild(companyPlaceholder);
    companyGroup.append(companyLabel, companySelect);
    card.appendChild(companyGroup);

    // Month selector
    const monthGroup = el('div', { className: 'mx-diot-filter-group' });
    const monthLabel = el('label');
    monthLabel.textContent = __('Mes');
    monthLabel.setAttribute('for', 'mx-diot-month');
    const monthSelect = el('select', { id: 'mx-diot-month' });
    const MONTHS = [
        __('Enero'), __('Febrero'), __('Marzo'), __('Abril'),
        __('Mayo'), __('Junio'), __('Julio'), __('Agosto'),
        __('Septiembre'), __('Octubre'), __('Noviembre'), __('Diciembre'),
    ];
    MONTHS.forEach((name, i) => {
        const opt = el('option', { value: String(i + 1) });
        opt.textContent = name;
        if (i + 1 === new Date().getMonth() + 1) opt.selected = true;
        monthSelect.appendChild(opt);
    });
    monthGroup.append(monthLabel, monthSelect);
    card.appendChild(monthGroup);

    // Year selector
    const yearGroup = el('div', { className: 'mx-diot-filter-group' });
    const yearLabel = el('label');
    yearLabel.textContent = __('Año');
    yearLabel.setAttribute('for', 'mx-diot-year');
    const yearInput = el('input', {
        type: 'number',
        id: 'mx-diot-year',
        min: '2020',
        max: '2099',
        value: String(new Date().getFullYear()),
        style: 'width:100px;',
    });
    yearGroup.append(yearLabel, yearInput);
    card.appendChild(yearGroup);

    // Action buttons
    const actionsGroup = el('div', { className: 'mx-diot-actions' });

    const previewBtn = el('button', { className: 'mx-btn mx-btn--primary', id: 'mx-diot-preview-btn' });
    previewBtn.textContent = __('Vista Previa');
    previewBtn.addEventListener('click', () => {
        on_preview_click(page, companySelect, monthSelect, yearInput);
    });

    const downloadBtn = el('button', {
        className: 'mx-btn mx-btn--success',
        id: 'mx-diot-download-btn',
    });
    downloadBtn.textContent = __('Descargar TXT');
    downloadBtn.disabled = true;
    downloadBtn.addEventListener('click', () => {
        on_download_click(page, companySelect, monthSelect, yearInput);
    });

    actionsGroup.append(previewBtn, downloadBtn);
    card.appendChild(actionsGroup);

    populate_companies(companySelect);

    return card;
}

// ─── Populate companies ────────────────────────────────────────────────────────

function populate_companies(select) {
    frappe.db.get_list('Company', { fields: ['name'], limit: 100 })
        .then(companies => {
            const defaultCompany = frappe.defaults.get_user_default('company');
            companies.forEach(c => {
                const opt = el('option', { value: c.name });
                opt.textContent = c.name;
                if (c.name === defaultCompany) opt.selected = true;
                select.appendChild(opt);
            });
        })
        .catch(() => {
            frappe.show_alert({ message: __('Error al cargar empresas'), indicator: 'red' });
        });
}

// ─── Preview action ────────────────────────────────────────────────────────────

function on_preview_click(page, companySelect, monthSelect, yearInput) {
    const company = companySelect.value;
    const month   = monthSelect.value;
    const year    = yearInput.value;

    if (!company) {
        frappe.show_alert({ message: __('Seleccione una empresa'), indicator: 'orange' });
        return;
    }
    if (!year || parseInt(year) < 2020 || parseInt(year) > 2099) {
        frappe.show_alert({ message: __('Ingrese un año válido (2020-2099)'), indicator: 'orange' });
        return;
    }

    const resultsArea = page._results_area;
    clear_el(resultsArea);
    resultsArea.appendChild(build_skeleton());

    const previewBtn  = document.getElementById('mx-diot-preview-btn');
    const downloadBtn = document.getElementById('mx-diot-download-btn');
    if (previewBtn)  previewBtn.disabled = true;
    if (downloadBtn) downloadBtn.disabled = true;

    frappe.call({
        method: 'erpnext_mexico.diot.diot_generator.generate_diot',
        args: { company, month: parseInt(month), year: parseInt(year) },
        callback(r) {
            if (previewBtn) previewBtn.disabled = false;
            clear_el(resultsArea);

            if (!r.message || !r.message.content) {
                resultsArea.appendChild(build_empty_state(
                    __('Sin datos'),
                    __('No se encontraron facturas de compra en el periodo seleccionado.')
                ));
                return;
            }

            page._diot_state.data = r.message;
            if (downloadBtn) downloadBtn.disabled = false;

            const rows = parse_diot_content(r.message.content);
            resultsArea.appendChild(build_summary_cards(rows, r.message));
            resultsArea.appendChild(build_preview_table(rows));
        },
        error() {
            if (previewBtn) previewBtn.disabled = false;
            clear_el(resultsArea);
            resultsArea.appendChild(build_empty_state(
                __('Error'),
                __('Ocurrió un error al generar la vista previa. Verifique la consola para más detalles.')
            ));
        },
    });
}

// ─── Download action ───────────────────────────────────────────────────────────

function on_download_click(page, companySelect, monthSelect, yearInput) {
    const company = companySelect.value;
    const month   = monthSelect.value;
    const year    = yearInput.value;

    if (!company) {
        frappe.show_alert({ message: __('Seleccione una empresa'), indicator: 'orange' });
        return;
    }

    const params = new URLSearchParams({
        cmd: 'erpnext_mexico.diot.diot_generator.download_diot',
        company,
        month,
        year,
    });

    const link = document.createElement('a');
    link.href = `/api/method/erpnext_mexico.diot.diot_generator.download_diot?${params.toString()}`;
    link.download = `DIOT_${encodeURIComponent(company)}_${year}${String(month).padStart(2, '0')}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    frappe.show_alert({ message: __('Descargando archivo DIOT...'), indicator: 'green' });
}

// ─── Summary cards ─────────────────────────────────────────────────────────────

function build_summary_cards(rows, meta) {
    const grid = el('div', { className: 'mx-diot-summary' });

    const totals = rows.reduce(
        (acc, r) => {
            acc.base_16  += parse_field_amount(r[7]);   // field 8: valor 16%
            acc.base_0   += parse_field_amount(r[16]);  // field 17: valor 0%
            acc.exento   += parse_field_amount(r[17]);  // field 18: exento
            acc.retenido += parse_field_amount(r[18]);  // field 19: retenido
            return acc;
        },
        { base_16: 0, base_0: 0, exento: 0, retenido: 0 }
    );

    const cards = [
        { label: __('Proveedores'),           value: String(meta.supplier_count || rows.length) },
        { label: __('Base IVA 16%'),          value: fmt_currency(totals.base_16)               },
        { label: __('Base IVA 0% + Exento'),  value: fmt_currency(totals.base_0 + totals.exento)},
        { label: __('IVA Retenido'),          value: fmt_currency(totals.retenido)               },
    ];

    cards.forEach(({ label, value }) => {
        const card = el('div', { className: 'mx-sum-card' });
        const lbl = el('div', { className: 'mx-sum-card__label' });
        lbl.textContent = label;
        const val = el('div', { className: 'mx-sum-card__value' });
        val.textContent = value;
        card.append(lbl, val);
        grid.appendChild(card);
    });

    return grid;
}

// ─── Preview table ─────────────────────────────────────────────────────────────

function build_preview_table(rows) {
    const card = el('div', { className: 'mx-diot-table-card' });

    const titleRow = el('div', { className: 'mx-section-title' });
    const titleText = el('span');
    titleText.textContent = __('Detalle por Proveedor');
    const rowCount = el('span', { style: 'font-size:12px;font-weight:500;color:var(--mx-text-muted);' });
    rowCount.textContent = `${rows.length} ${__('proveedores')}`;
    titleRow.append(titleText, rowCount);
    card.appendChild(titleRow);

    if (!rows.length) {
        card.appendChild(build_empty_state('', __('No hay datos que mostrar.')));
        return card;
    }

    const table = el('table', { className: 'mx-diot-table' });

    // Table header
    const thead = el('thead');
    const headerRow = el('tr');
    const headers = [
        { label: __('Tipo'),         num: false },
        { label: __('RFC'),          num: false },
        { label: __('Operacion'),    num: false },
        { label: __('Base 16%'),     num: true  },
        { label: __('Base 8%'),      num: true  },
        { label: __('Base 0%'),      num: true  },
        { label: __('Exento'),       num: true  },
        { label: __('IVA Retenido'), num: true  },
    ];
    headers.forEach(({ label, num }) => {
        const th = el('th', num ? { className: 'num' } : {});
        th.textContent = label;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Table body
    const tbody = el('tbody');
    rows.forEach(fields => {
        const tr = el('tr');

        // Tipo tercero badge
        const tdTipo = el('td');
        const tipoCode = fields[0] || '';
        const TIPO_LABELS   = { '04': __('Nacional'), '05': __('Extranjero'), '15': __('Global') };
        const TIPO_CLASSES  = { '04': 'nacional',     '05': 'extranjero',     '15': 'global'     };
        const badge = el('span', { className: `mx-badge mx-badge--${TIPO_CLASSES[tipoCode] || 'nacional'}` });
        badge.textContent = TIPO_LABELS[tipoCode] || tipoCode;
        tdTipo.appendChild(badge);

        // RFC (or foreign name for tipo 05)
        const tdRfc = el('td', { className: 'mx-rfc-cell' });
        const rfcVal = (fields[2] || '').trim();
        tdRfc.textContent = rfcVal || (fields[4] || '—');

        // Tipo operacion
        const tdOp = el('td');
        const OP_LABELS = { '85': __('Servicios Prof.'), '06': __('Arrendamiento'), '03': __('Otros') };
        tdOp.textContent = OP_LABELS[fields[1]] || fields[1] || '—';

        // Amount columns: fields at indices 7 (16%), 10 (8%), 16 (0%), 17 (exento), 18 (retenido)
        [7, 10, 16, 17, 18].forEach(idx => {
            const td = el('td', { className: 'num' });
            const val = parse_field_amount(fields[idx]);
            td.textContent = val > 0 ? fmt_currency(val) : '—';
            tr.appendChild(td);
        });

        tr.prepend(tdTipo, tdRfc, tdOp);
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    card.appendChild(table);
    return card;
}

// ─── Skeleton loader ───────────────────────────────────────────────────────────

function build_skeleton() {
    const wrap = el('div', { style: 'display:flex;flex-direction:column;gap:var(--mx-space-4);' });

    const sumGrid = el('div', { className: 'mx-diot-summary' });
    for (let i = 0; i < 4; i++) {
        const card = el('div', { className: 'mx-sum-card' });
        const s1 = el('div', { className: 'mx-skeleton', style: 'height:10px;width:50%;margin-bottom:8px;' });
        const s2 = el('div', { className: 'mx-skeleton', style: 'height:22px;width:70%;' });
        card.append(s1, s2);
        sumGrid.appendChild(card);
    }
    wrap.appendChild(sumGrid);

    const tableCard = el('div', { className: 'mx-diot-table-card' });
    for (let i = 0; i < 6; i++) {
        const row = el('div', { className: 'mx-skeleton', style: `height:14px;width:${85 + (i % 3) * 5}%;margin-bottom:10px;` });
        tableCard.appendChild(row);
    }
    wrap.appendChild(tableCard);
    return wrap;
}

// ─── Empty state ───────────────────────────────────────────────────────────────

function build_empty_state(title, text) {
    const wrap = el('div', { className: 'mx-empty' });
    const ico = el('div', { className: 'mx-empty__icon' });
    ico.textContent = '[]';
    const ttl = el('div', { className: 'mx-empty__title' });
    ttl.textContent = title;
    const txt = el('div', { className: 'mx-empty__text' });
    txt.textContent = text;
    wrap.append(ico, ttl, txt);
    return wrap;
}

// ─── Utilities ─────────────────────────────────────────────────────────────────

/**
 * Parse the pipe-delimited DIOT content string back into an array of field arrays.
 * Each element is an array of 24 strings.
 */
function parse_diot_content(content) {
    if (!content) return [];
    return content
        .split('\n')
        .filter(line => line.trim())
        .map(line => line.split('|'));
}

function parse_field_amount(val) {
    const n = parseInt(val, 10);
    return isNaN(n) ? 0 : n;
}

function fmt_currency(amount) {
    if (amount === null || amount === undefined) return '—';
    try {
        return new Intl.NumberFormat('es-MX', {
            style: 'currency', currency: 'MXN', minimumFractionDigits: 2,
        }).format(amount);
    } catch (_) {
        return '$' + Number(amount).toFixed(2);
    }
}

/** Minimal DOM factory — avoids string concatenation for dynamic content. */
function el(tag, attrs) {
    const node = document.createElement(tag);
    if (!attrs) return node;
    Object.entries(attrs).forEach(([k, v]) => {
        if (k === 'className') node.className = v;
        else if (k === 'style') node.style.cssText = v;
        else node.setAttribute(k, v);
    });
    return node;
}

/** Remove all child nodes from a DOM element safely. */
function clear_el(node) {
    while (node.firstChild) {
        node.removeChild(node.firstChild);
    }
}
