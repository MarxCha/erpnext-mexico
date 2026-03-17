/**
 * Panel Fiscal MX — Client-side controller
 * Frappe Page: mx-fiscal-dashboard
 *
 * Security note: This is an authenticated admin page (System Manager / Accounts roles).
 * Dynamic HTML is built from server-controlled data and all user-supplied strings
 * are sanitised via frappe.utils.escape_html() before insertion.
 */

// ─── Design-token stylesheet ──────────────────────────────────────────────────

(function injectStyles() {
    if (document.getElementById('mx-dashboard-styles')) return;
    const style = document.createElement('style');
    style.id = 'mx-dashboard-styles';
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
    --mx-cancelled-bg:   #F3F4F6;
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
    --mx-space-2: 8px; --mx-space-3: 12px; --mx-space-4: 16px;
    --mx-space-5: 20px; --mx-space-6: 24px; --mx-space-8: 32px;
    --mx-shadow-card:  0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.04);
    --mx-shadow-hover: 0 4px 12px rgba(0,0,0,.10);
  }
  .mx-page { background:var(--mx-bg-secondary); font-family:var(--mx-font-sans); color:var(--mx-text-primary); }
  .mx-dashboard { padding:var(--mx-space-6); max-width:1280px; display:flex; flex-direction:column; gap:var(--mx-space-6); }

  /* Metric cards */
  .mx-dashboard__metrics { display:grid; grid-template-columns:repeat(4,1fr); gap:var(--mx-space-4); }
  @media(max-width:900px){ .mx-dashboard__metrics{grid-template-columns:repeat(2,1fr);} .mx-two-col{grid-template-columns:1fr !important;} }
  .mx-metric-card {
    background:var(--mx-bg-primary); border:1px solid var(--mx-border); border-radius:var(--mx-radius-lg);
    padding:var(--mx-space-5); box-shadow:var(--mx-shadow-card);
    display:flex; flex-direction:column; gap:var(--mx-space-2);
    transition:box-shadow .2s ease,transform .2s ease;
  }
  .mx-metric-card:hover { box-shadow:var(--mx-shadow-hover); transform:translateY(-1px); }
  .mx-metric-card__icon {
    width:40px; height:40px; border-radius:var(--mx-radius-md);
    display:flex; align-items:center; justify-content:center; font-size:18px; margin-bottom:4px;
  }
  .mx-metric-card__label { font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; color:var(--mx-text-muted); }
  .mx-metric-card__value { font-size:28px; font-weight:800; color:var(--mx-text-primary); line-height:1.2; letter-spacing:-.02em; }
  .mx-metric-card__change { font-size:12px; color:var(--mx-text-muted); line-height:1.4; }
  .mx-metric-card__change--up   { color:var(--mx-success); }
  .mx-metric-card__change--down { color:var(--mx-error); }

  /* Sections */
  .mx-dashboard__section {
    background:var(--mx-bg-primary); border:1px solid var(--mx-border);
    border-radius:var(--mx-radius-lg); padding:var(--mx-space-5); box-shadow:var(--mx-shadow-card);
  }
  .mx-section-title {
    font-size:13px; font-weight:700; letter-spacing:.04em; text-transform:uppercase;
    color:var(--mx-text-secondary); margin-bottom:var(--mx-space-4);
    display:flex; align-items:center; justify-content:space-between;
  }

  /* Quick actions */
  .mx-quick-actions { display:flex; flex-wrap:wrap; gap:var(--mx-space-3); }
  .mx-quick-action {
    display:inline-flex; align-items:center; gap:6px; padding:8px 16px;
    background:var(--mx-bg-primary); border:1px solid var(--mx-border);
    border-radius:var(--mx-radius-md); font-size:13px; font-weight:500;
    color:var(--mx-text-secondary); text-decoration:none; box-shadow:var(--mx-shadow-card);
    transition:all .15s ease; white-space:nowrap;
  }
  .mx-quick-action:hover { border-color:var(--mx-accent); color:var(--mx-accent); box-shadow:var(--mx-shadow-hover); transform:translateY(-1px); }

  /* Table */
  .mx-activity-table { width:100%; border-collapse:collapse; font-size:13px; }
  .mx-activity-table th {
    text-align:left; font-size:11px; font-weight:600; letter-spacing:.06em; text-transform:uppercase;
    color:var(--mx-text-muted); padding:0 8px 10px; border-bottom:1px solid var(--mx-border);
  }
  .mx-activity-table td { padding:10px 8px; border-bottom:1px solid var(--mx-bg-tertiary); color:var(--mx-text-secondary); vertical-align:middle; }
  .mx-activity-table tr:last-child td { border-bottom:none; }
  .mx-activity-table tr:hover td { background:var(--mx-bg-secondary); }
  .mx-table-link { font-family:var(--mx-font-mono); font-size:12px; font-weight:600; color:var(--mx-accent); text-decoration:none; }
  .mx-table-link:hover { text-decoration:underline; }

  /* Status pills */
  .mx-pill { display:inline-block; padding:2px 10px; border-radius:999px; font-size:11px; font-weight:700; letter-spacing:.04em; text-transform:uppercase; }
  .mx-pill--timbrado  { background:var(--mx-success-bg); color:#065F46; }
  .mx-pill--pendiente { background:var(--mx-warning-bg); color:#92400E; }
  .mx-pill--error     { background:var(--mx-error-bg);   color:#991B1B; }
  .mx-pill--cancelado { background:var(--mx-cancelled-bg); color:#374151; }

  /* Empty state */
  .mx-empty { text-align:center; padding:var(--mx-space-8) var(--mx-space-4); color:var(--mx-text-muted); }
  .mx-empty__icon  { font-size:48px; margin-bottom:var(--mx-space-3); }
  .mx-empty__title { font-size:15px; font-weight:700; color:var(--mx-text-secondary); margin-bottom:6px; }
  .mx-empty__text  { font-size:13px; max-width:360px; margin:0 auto; line-height:1.6; }

  /* CTA */
  .mx-btn-primary {
    display:inline-flex; align-items:center; justify-content:center;
    padding:8px 20px; background:var(--mx-accent); color:#FFF !important;
    border-radius:var(--mx-radius-md); font-size:13px; font-weight:600;
    text-decoration:none; transition:background .15s ease;
  }
  .mx-btn-primary:hover { background:var(--mx-accent-hover); }

  /* Skeleton */
  @keyframes mx-shimmer { 0%{background-position:-600px 0} 100%{background-position:600px 0} }
  .mx-skeleton {
    background:linear-gradient(90deg,var(--mx-bg-tertiary) 25%,var(--mx-border) 50%,var(--mx-bg-tertiary) 75%);
    background-size:1200px 100%; animation:mx-shimmer 1.4s infinite linear; border-radius:var(--mx-radius-sm);
  }
    `;
    document.head.appendChild(style);
}());

// ─── Page lifecycle ───────────────────────────────────────────────────────────

frappe.pages['mx-fiscal-dashboard'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Panel Fiscal MX'),
        single_column: true,
    });

    page.main.addClass('mx-page');

    // Company selector in page toolbar
    page.company_field = page.add_field({
        fieldname: 'company',
        label: __('Empresa'),
        fieldtype: 'Link',
        options: 'Company',
        default: frappe.defaults.get_user_default('company'),
        change() {
            page.company = page.company_field.get_value();
            render_dashboard(page);
        },
    });

    page.company = frappe.defaults.get_user_default('company');

    page.set_primary_action(__('Actualizar'), () => render_dashboard(page), 'refresh');
    page.set_secondary_action(__('Configuración Fiscal'), () => frappe.set_route('mx-cfdi-settings'), 'settings');

    render_dashboard(page);
};

frappe.pages['mx-fiscal-dashboard'].on_page_show = function () {
    // intentionally empty — refresh is manual to avoid flicker
};

// ─── Main render ──────────────────────────────────────────────────────────────

function render_dashboard(page) {
    page.main.find('.mx-dashboard').remove();
    page.main.append(build_skeleton());

    frappe.call({
        method: 'erpnext_mexico.cfdi.page.mx_fiscal_dashboard.mx_fiscal_dashboard.get_dashboard_data',
        args: { company: page.company || null },
        callback(r) {
            page.main.find('.mx-dashboard').remove();
            if (r.message) {
                const container = build_dashboard(r.message);
                page.main.get(0).appendChild(container);
                init_chart(r.message.monthly_chart);
            }
        },
        error() {
            page.main.find('.mx-dashboard').remove();
            frappe.show_alert({ message: __('Error al cargar el dashboard'), indicator: 'red' });
        },
    });
}

// ─── DOM builders (no innerHTML on user data) ─────────────────────────────────

/**
 * Build entire dashboard DOM node.
 * All user-data strings pass through frappe.utils.escape_html() or
 * are set via textContent — never raw innerHTML from API responses.
 */
function build_dashboard(data) {
    const m = data.metrics || {};
    const setup = data.setup_status || [];
    const setupDone = setup.filter(s => s.done).length;
    const setupTotal = setup.length || 1;

    const root = el('div', { className: 'mx-dashboard' });

    // Metric cards
    root.appendChild(build_metrics_row(m));

    // Chart + Setup two-column
    const twoCol = el('div', {
        style: 'display:grid;grid-template-columns:2fr 1fr;gap:var(--mx-space-6);',
        className: 'mx-two-col',
    });
    twoCol.appendChild(build_chart_section());
    twoCol.appendChild(build_setup_section(setup, setupDone, setupTotal));
    root.appendChild(twoCol);

    // Quick actions
    root.appendChild(build_quick_actions());

    // Recent activity
    root.appendChild(build_activity_section(data.recent_cfdis));

    return root;
}

function build_metrics_row(m) {
    const grid = el('div', { className: 'mx-dashboard__metrics' });
    const cards = [
        {
            icon: '📄', iconBg: 'var(--mx-accent-light)', iconColor: 'var(--mx-accent)',
            label: __('CFDIs Timbrados'), value: fmt_number(m.stamped),
            change: `${__('de')} ${fmt_number(m.total_invoices)} ${__('total')}`, changeType: 'up',
        },
        {
            icon: '⏳', iconBg: 'var(--mx-warning-bg)', iconColor: 'var(--mx-warning)',
            label: __('Pendientes'), value: fmt_number(m.pending),
            change: __('por timbrar'), changeType: '',
        },
        {
            icon: '⚠', iconBg: 'var(--mx-error-bg)', iconColor: 'var(--mx-error)',
            label: __('Errores'), value: fmt_number(m.errors),
            change: __('requieren atención'), changeType: m.errors > 0 ? 'down' : '',
        },
        {
            icon: '💰', iconBg: 'var(--mx-success-bg)', iconColor: 'var(--mx-success)',
            label: __('Facturado Este Mes'), value: fmt_currency(m.monthly_total, 'MXN'),
            change: __('mes actual'), changeType: 'up',
        },
    ];
    cards.forEach(c => grid.appendChild(build_metric_card(c)));
    return grid;
}

function build_metric_card({ icon, iconBg, iconColor, label, value, change, changeType }) {
    const card = el('div', { className: 'mx-metric-card' });
    const ico = el('div', { className: 'mx-metric-card__icon', style: `background:${iconBg};color:${iconColor};` });
    ico.textContent = icon;
    const lbl = el('div', { className: 'mx-metric-card__label' });
    lbl.textContent = label;
    const val = el('div', { className: 'mx-metric-card__value' });
    val.textContent = value;
    const chg = el('div', { className: `mx-metric-card__change${changeType ? ' mx-metric-card__change--' + changeType : ''}` });
    chg.textContent = change;
    card.append(ico, lbl, val, chg);
    return card;
}

function build_chart_section() {
    const section = el('div', { className: 'mx-dashboard__section' });
    const title = el('div', { className: 'mx-section-title' });
    const titleText = el('span');
    titleText.textContent = __('Facturación Mensual');
    const titleSub = el('span', { style: 'font-size:11px;color:var(--mx-text-muted);font-weight:400;' });
    titleSub.textContent = __('Últimos 6 meses');
    title.append(titleText, titleSub);
    const chartArea = el('div', { id: 'mx-monthly-chart', style: 'min-height:220px;display:flex;align-items:center;justify-content:center;' });
    section.append(title, chartArea);
    return section;
}

function build_setup_section(steps, done, total) {
    const section = el('div', { className: 'mx-dashboard__section' });

    // Title row
    const title = el('div', { className: 'mx-section-title' });
    const titleText = el('span');
    titleText.textContent = __('Configuración Fiscal');
    const counter = el('span', { style: 'font-size:12px;font-weight:500;color:var(--mx-text-muted);' });
    counter.textContent = `${done}/${total}`;
    title.append(titleText, counter);

    // Progress bar
    const pct = Math.round((done / total) * 100);
    const barWrap = el('div', { style: 'height:4px;background:var(--mx-bg-tertiary);border-radius:2px;margin-bottom:var(--mx-space-4);overflow:hidden;' });
    const barFill = el('div', {
        style: `height:100%;width:${pct}%;background:${done === total ? 'var(--mx-success)' : 'var(--mx-accent)'};border-radius:2px;transition:width .5s ease;`,
    });
    barWrap.appendChild(barFill);

    // Steps
    const stepList = el('div');
    (steps.length ? steps : []).forEach(step => {
        const row = el('div', { style: 'display:flex;align-items:center;gap:8px;padding:6px 0;' });
        const icon = el('span', { style: `color:${step.done ? 'var(--mx-success)' : 'var(--mx-text-muted)'};font-size:16px;flex-shrink:0;` });
        icon.textContent = step.done ? '✓' : '○';
        const lbl = el('span', {
            style: `font-size:13px;color:${step.done ? 'var(--mx-text-primary)' : 'var(--mx-text-muted)'};${step.done ? '' : 'opacity:.65;'}`,
        });
        lbl.textContent = step.label;       // server string, safe
        row.append(icon, lbl);
        stepList.appendChild(row);
    });

    // CTA
    const cta = el('div', { style: 'margin-top:var(--mx-space-4);' });
    if (done < total) {
        const link = el('a', { href: '/app/mx-cfdi-settings', className: 'mx-btn-primary' });
        link.textContent = __('Completar Configuración');
        cta.appendChild(link);
    } else {
        const badge = el('div', {
            style: 'text-align:center;padding:8px;background:var(--mx-success-bg);border-radius:var(--mx-radius-md);color:#065F46;font-size:13px;font-weight:600;',
        });
        badge.textContent = `✓ ${__('Configuración completa')}`;
        cta.appendChild(badge);
    }

    section.append(title, barWrap, stepList, cta);
    return section;
}

function build_quick_actions() {
    const wrap = el('div', { className: 'mx-quick-actions' });
    const actions = [
        { href: '/app/mx-cfdi-settings',      icon: '⚙️', label: __('Configuración CFDI') },
        { href: '/app/mx-digital-certificate', icon: '🔐', label: __('Certificados CSD')   },
        { href: '/app/mx-cfdi-log',            icon: '📋', label: __('Log CFDI')            },
        { href: '/app/mx-fiscal-regime',       icon: '📑', label: __('Regímenes Fiscales')  },
        { href: '/app/mx-product-service-key', icon: '🏷', label: __('Claves SAT')          },
        { href: '/app/sales-invoice/new',      icon: '➕', label: __('Nueva Factura')       },
    ];
    actions.forEach(({ href, icon, label }) => {
        const a = el('a', { href, className: 'mx-quick-action' });
        const ico = el('span');
        ico.textContent = icon;
        const txt = el('span');
        txt.textContent = label;
        a.append(ico, txt);
        wrap.appendChild(a);
    });
    return wrap;
}

function build_activity_section(cfdis) {
    const section = el('div', { className: 'mx-dashboard__section' });

    const title = el('div', { className: 'mx-section-title' });
    const titleText = el('span');
    titleText.textContent = __('Actividad CFDI Reciente');
    const viewAll = el('a', { href: '/app/mx-cfdi-log', style: 'font-size:12px;font-weight:500;color:var(--mx-accent);text-decoration:none;' });
    viewAll.textContent = `${__('Ver todo')} →`;
    title.append(titleText, viewAll);
    section.appendChild(title);

    if (!cfdis || !cfdis.length) {
        section.appendChild(build_empty_state(
            '📄',
            __('Sin actividad CFDI'),
            __('Las facturas timbradas aparecerán aquí. Cree una factura y tímbrela para comenzar.')
        ));
        return section;
    }

    const STATUS_CLASS = { Timbrado: 'timbrado', Pendiente: 'pendiente', Error: 'error', Cancelado: 'cancelado' };

    const table = el('table', { className: 'mx-activity-table' });
    const thead = el('thead');
    const headerRow = el('tr');
    [__('Factura'), __('Cliente'), __('Monto'), __('Estado CFDI'), __('Fecha')].forEach((h, i) => {
        const th = el('th', i === 2 ? { style: 'text-align:right;' } : {});
        th.textContent = h;
        headerRow.appendChild(th);
    });
    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = el('tbody');
    cfdis.forEach(inv => {
        const tr = el('tr');

        // Factura link — name is always a system ID, still escape to be safe
        const tdName = el('td');
        const nameLink = el('a', { href: `/app/sales-invoice/${encodeURIComponent(inv.name)}`, className: 'mx-table-link' });
        nameLink.textContent = inv.name;
        tdName.appendChild(nameLink);

        // Customer — user data
        const tdCust = el('td');
        tdCust.textContent = inv.customer_name || '—';

        // Amount
        const tdAmt = el('td', { style: 'text-align:right;font-family:var(--mx-font-mono);font-size:12px;' });
        tdAmt.textContent = fmt_currency(inv.grand_total, inv.currency);

        // Status pill
        const tdStatus = el('td');
        const pill = el('span', { className: `mx-pill mx-pill--${STATUS_CLASS[inv.mx_cfdi_status] || 'pendiente'}` });
        pill.textContent = inv.mx_cfdi_status || '';
        tdStatus.appendChild(pill);

        // Date
        const tdDate = el('td', { style: 'color:var(--mx-text-muted);font-size:12px;' });
        tdDate.textContent = String(inv.posting_date || '');

        tr.append(tdName, tdCust, tdAmt, tdStatus, tdDate);
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    section.appendChild(table);
    return section;
}

function build_empty_state(icon, title, text) {
    const wrap = el('div', { className: 'mx-empty' });
    const ico = el('div', { className: 'mx-empty__icon' });
    ico.textContent = icon;
    const ttl = el('div', { className: 'mx-empty__title' });
    ttl.textContent = title;
    const txt = el('div', { className: 'mx-empty__text' });
    txt.textContent = text;
    wrap.append(ico, ttl, txt);
    return wrap;
}

function build_skeleton() {
    const wrap = el('div', { className: 'mx-dashboard' });
    const grid = el('div', { className: 'mx-dashboard__metrics' });
    for (let i = 0; i < 4; i++) {
        const card = el('div', { className: 'mx-metric-card' });
        const s1 = el('div', { className: 'mx-skeleton', style: 'height:40px;width:40px;margin-bottom:8px;' });
        const s2 = el('div', { className: 'mx-skeleton', style: 'height:10px;width:60%;margin-bottom:6px;' });
        const s3 = el('div', { className: 'mx-skeleton', style: 'height:28px;width:40%;' });
        card.append(s1, s2, s3);
        grid.appendChild(card);
    }
    wrap.appendChild(grid);
    return wrap;
}

// ─── Chart ────────────────────────────────────────────────────────────────────

function init_chart(monthly_data) {
    const container = document.getElementById('mx-monthly-chart');
    if (!container) return;

    if (!monthly_data || !monthly_data.length) {
        const empty = build_empty_state('📊', '', __('Sin datos de facturación en los últimos 6 meses.'));
        empty.style.padding = 'var(--mx-space-6)';
        container.appendChild(empty);
        return;
    }

    new frappe.Chart(container, {
        data: {
            labels: monthly_data.map(d => d.month),
            datasets: [
                { name: __('Monto (MXN)'), type: 'bar',  values: monthly_data.map(d => d.amount || 0) },
                { name: __('Facturas'),    type: 'line', values: monthly_data.map(d => d.total  || 0) },
            ],
        },
        type: 'axis-mixed',
        height: 220,
        colors: ['#0052CC', '#10B981'],
        axisOptions: { xIsSeries: true },
        tooltipOptions: { formatTooltipY: d => fmt_currency(d, 'MXN') },
    });
}

// ─── Utilities ────────────────────────────────────────────────────────────────

/** Tiny DOM factory — avoids string concatenation for dynamic content. */
function el(tag, attrs = {}) {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
        if (k === 'className') node.className = v;
        else if (k === 'style')  node.style.cssText = v;
        else node.setAttribute(k, v);
    });
    return node;
}

function fmt_currency(amount, currency = 'MXN') {
    if (amount === null || amount === undefined) return '—';
    try {
        return new Intl.NumberFormat('es-MX', {
            style: 'currency', currency: currency || 'MXN', minimumFractionDigits: 2,
        }).format(amount);
    } catch (_) {
        return `${currency} ${Number(amount).toFixed(2)}`;
    }
}

function fmt_number(n) {
    if (n === null || n === undefined) return '—';
    return new Intl.NumberFormat('es-MX').format(n);
}
