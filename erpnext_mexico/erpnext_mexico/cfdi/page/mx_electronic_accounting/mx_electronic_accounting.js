/**
 * Contabilidad Electrónica MX — Client-side controller
 * Frappe Page: mx-electronic-accounting
 *
 * Generates and downloads Anexo 24 XML files:
 *   - Catálogo de Cuentas  (catalog_xml.generate_catalog_xml)
 *   - Balanza de Comprobación (balanza_xml.generate_balanza_xml)
 *   - Pólizas del Periodo   (polizas_xml.generate_polizas_xml)
 */

// ─── Design tokens (inline, self-contained) ──────────────────────────────────

(function injectStyles() {
    if (document.getElementById('mx-eac-styles')) return;
    const style = document.createElement('style');
    style.id = 'mx-eac-styles';
    style.textContent = `
  :root {
    --mx-accent:          #0052CC;
    --mx-accent-hover:    #0747A6;
    --mx-accent-light:    #DEEBFF;
    --mx-success:         #10B981;
    --mx-success-bg:      #D1FAE5;
    --mx-warning:         #F59E0B;
    --mx-warning-bg:      #FEF3C7;
    --mx-error:           #EF4444;
    --mx-error-bg:        #FEE2E2;
    --mx-bg-primary:      #FFFFFF;
    --mx-bg-secondary:    #F8FAFC;
    --mx-border:          #E2E8F0;
    --mx-text-primary:    #1A202C;
    --mx-text-secondary:  #4A5568;
    --mx-text-muted:      #718096;
    --mx-font-sans:       'DM Sans','Nunito',system-ui,sans-serif;
    --mx-font-mono:       'JetBrains Mono','Fira Code',monospace;
    --mx-radius-sm:       6px;
    --mx-radius-md:       8px;
    --mx-radius-lg:       12px;
    --mx-shadow-card:     0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.04);
    --mx-shadow-hover:    0 4px 12px rgba(0,0,0,.10);
  }

  /* Page wrapper */
  .mx-eac-page {
    background: var(--mx-bg-secondary);
    font-family: var(--mx-font-sans);
    color: var(--mx-text-primary);
    min-height: 100vh;
    padding: 32px;
  }

  /* Header */
  .mx-eac-header {
    margin-bottom: 32px;
  }
  .mx-eac-header h1 {
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1.2;
    color: var(--mx-text-primary);
    margin: 0 0 6px;
  }
  .mx-eac-header p {
    color: var(--mx-text-muted);
    font-size: 0.9rem;
    margin: 0;
  }

  /* Filter bar */
  .mx-eac-filters {
    background: var(--mx-bg-primary);
    border: 1px solid var(--mx-border);
    border-radius: var(--mx-radius-lg);
    padding: 24px;
    box-shadow: var(--mx-shadow-card);
    display: grid;
    grid-template-columns: 2fr 1fr 1fr;
    gap: 16px;
    margin-bottom: 32px;
    align-items: end;
  }
  @media (max-width: 768px) {
    .mx-eac-filters { grid-template-columns: 1fr; }
  }

  .mx-eac-field label {
    display: block;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--mx-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
  }
  .mx-eac-field select,
  .mx-eac-field input {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid var(--mx-border);
    border-radius: var(--mx-radius-md);
    font-size: 0.9rem;
    font-family: var(--mx-font-sans);
    color: var(--mx-text-primary);
    background: var(--mx-bg-primary);
    outline: none;
    transition: border-color .15s, box-shadow .15s;
    box-sizing: border-box;
  }
  .mx-eac-field select:focus,
  .mx-eac-field input:focus {
    border-color: var(--mx-accent);
    box-shadow: 0 0 0 3px var(--mx-accent-light);
  }

  /* Cards grid */
  .mx-eac-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
  }
  @media (max-width: 960px) {
    .mx-eac-cards { grid-template-columns: 1fr; }
  }

  /* XML type card */
  .mx-eac-card {
    background: var(--mx-bg-primary);
    border: 1px solid var(--mx-border);
    border-radius: var(--mx-radius-lg);
    box-shadow: var(--mx-shadow-card);
    padding: 28px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    transition: box-shadow .2s, transform .2s;
  }
  .mx-eac-card:hover {
    box-shadow: var(--mx-shadow-hover);
    transform: translateY(-2px);
  }

  .mx-eac-card__icon {
    width: 48px;
    height: 48px;
    border-radius: var(--mx-radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.4rem;
  }
  .mx-eac-card__icon--catalog  { background: #EFF6FF; color: #2563EB; }
  .mx-eac-card__icon--balanza  { background: #F0FDF4; color: #16A34A; }
  .mx-eac-card__icon--polizas  { background: #FFF7ED; color: #EA580C; }

  .mx-eac-card__title {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--mx-text-primary);
    margin: 0;
  }
  .mx-eac-card__desc {
    font-size: 0.85rem;
    color: var(--mx-text-secondary);
    line-height: 1.5;
    flex: 1;
  }
  .mx-eac-card__schema {
    font-family: var(--mx-font-mono);
    font-size: 0.72rem;
    color: var(--mx-text-muted);
    background: var(--mx-bg-secondary);
    border: 1px solid var(--mx-border);
    border-radius: var(--mx-radius-sm);
    padding: 6px 10px;
    word-break: break-all;
  }

  /* Extra fields (Pólizas) */
  .mx-eac-extra-fields {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  /* Download button */
  .mx-eac-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 10px 16px;
    border: none;
    border-radius: var(--mx-radius-md);
    font-family: var(--mx-font-sans);
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    transition: background .15s, transform .1s, box-shadow .15s;
    white-space: nowrap;
  }
  .mx-eac-btn:active { transform: scale(.98); }
  .mx-eac-btn--primary {
    background: var(--mx-accent);
    color: #fff;
  }
  .mx-eac-btn--primary:hover { background: var(--mx-accent-hover); box-shadow: 0 2px 8px rgba(0,82,204,.3); }
  .mx-eac-btn--primary:disabled { background: #94a3b8; cursor: not-allowed; }

  /* Spinner inside button */
  .mx-eac-spinner {
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255,255,255,.4);
    border-top-color: #fff;
    border-radius: 50%;
    animation: mx-spin .6s linear infinite;
  }
  @keyframes mx-spin { to { transform: rotate(360deg); } }

  /* Status badge */
  .mx-eac-status {
    font-size: 0.78rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
    display: inline-block;
    margin-top: 4px;
  }
  .mx-eac-status--success { background: var(--mx-success-bg); color: #065F46; }
  .mx-eac-status--error   { background: var(--mx-error-bg);   color: #991B1B; }
`;
    document.head.appendChild(style);
})();


// ─── Page controller ──────────────────────────────────────────────────────────

frappe.pages['mx-electronic-accounting'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('Contabilidad Electrónica MX'),
        single_column: true,
    });

    const ctrl = new ElectronicAccountingPage(page, wrapper);
    ctrl.init();
};


class ElectronicAccountingPage {
    constructor(page, wrapper) {
        this.page = page;
        this.wrapper = wrapper;
        this.$root = null;
        this.companies = [];
    }

    // ── Lifecycle ────────────────────────────────────────────────────────────

    async init() {
        this._render();
        await this._loadCompanies();
    }

    // ── Render ───────────────────────────────────────────────────────────────

    _render() {
        const now = new Date();
        const curYear = now.getFullYear();
        const curMonth = now.getMonth() + 1; // 1-based

        const months = [
            [1,'Enero'],[2,'Febrero'],[3,'Marzo'],[4,'Abril'],
            [5,'Mayo'],[6,'Junio'],[7,'Julio'],[8,'Agosto'],
            [9,'Septiembre'],[10,'Octubre'],[11,'Noviembre'],[12,'Diciembre'],
        ];
        const monthOptions = months
            .map(([v, l]) => `<option value="${v}"${v === curMonth ? ' selected' : ''}>${l}</option>`)
            .join('');

        const yearOptions = [curYear - 1, curYear, curYear + 1]
            .map(y => `<option value="${y}"${y === curYear ? ' selected' : ''}>${y}</option>`)
            .join('');

        // Security note: this template is safe because no user-supplied data is
        // interpolated — only __() translated strings, numeric year/month values
        // computed from `new Date()`, and static option labels are included.
        const html = `
<div class="mx-eac-page">
  <div class="mx-eac-header">
    <h1>Contabilidad Electrónica</h1>
    <p>Genera archivos XML del Anexo 24 del SAT para presentación fiscal mensual.</p>
  </div>

  <!-- Filters -->
  <div class="mx-eac-filters">
    <div class="mx-eac-field">
      <label>${__('Empresa')}</label>
      <select id="eac-company">
        <option value="">${__('Cargando...')}</option>
      </select>
    </div>
    <div class="mx-eac-field">
      <label>${__('Año')}</label>
      <select id="eac-year">${yearOptions}</select>
    </div>
    <div class="mx-eac-field">
      <label>${__('Mes')}</label>
      <select id="eac-month">${monthOptions}</select>
    </div>
  </div>

  <!-- XML type cards -->
  <div class="mx-eac-cards">

    <!-- Catálogo de Cuentas -->
    <div class="mx-eac-card">
      <div class="mx-eac-card__icon mx-eac-card__icon--catalog">📋</div>
      <p class="mx-eac-card__title">${__('Catálogo de Cuentas')}</p>
      <p class="mx-eac-card__desc">
        ${__('Listado de cuentas contables mapeadas a los códigos agrupadores del SAT. Se envía mensualmente junto con la balanza.')}
      </p>
      <div class="mx-eac-card__schema">CatalogoCuentas_1_3.xsd</div>
      <div id="eac-catalog-status"></div>
      <button class="mx-eac-btn mx-eac-btn--primary" id="eac-catalog-btn">
        <span>⬇</span> ${__('Descargar Catálogo XML')}
      </button>
    </div>

    <!-- Balanza de Comprobación -->
    <div class="mx-eac-card">
      <div class="mx-eac-card__icon mx-eac-card__icon--balanza">⚖️</div>
      <p class="mx-eac-card__title">${__('Balanza de Comprobación')}</p>
      <p class="mx-eac-card__desc">
        ${__('Saldos iniciales, movimientos del periodo y saldos finales por cuenta. Envío mensual obligatorio.')}
      </p>
      <div class="mx-eac-card__schema">BalanzaComprobacion_1_3.xsd</div>
      <div class="mx-eac-extra-fields">
        <div class="mx-eac-field">
          <label>${__('Tipo de Envío')}</label>
          <select id="eac-tipo-envio">
            <option value="N">${__('N — Normal')}</option>
            <option value="C">${__('C — Complementaria')}</option>
          </select>
        </div>
        <div class="mx-eac-field" id="eac-fecha-mod-wrap" style="display:none">
          <label>${__('Fecha Mod. Balanza')}</label>
          <input type="date" id="eac-fecha-mod-bal" />
        </div>
      </div>
      <div id="eac-balanza-status"></div>
      <button class="mx-eac-btn mx-eac-btn--primary" id="eac-balanza-btn">
        <span>⬇</span> ${__('Descargar Balanza XML')}
      </button>
    </div>

    <!-- Pólizas del Periodo -->
    <div class="mx-eac-card">
      <div class="mx-eac-card__icon mx-eac-card__icon--polizas">📁</div>
      <p class="mx-eac-card__title">${__('Pólizas del Periodo')}</p>
      <p class="mx-eac-card__desc">
        ${__('Detalle de asientos contables. Solo se envía por requerimiento expreso del SAT durante una auditoría.')}
      </p>
      <div class="mx-eac-card__schema">PolizasPeriodo_1_3.xsd</div>
      <div class="mx-eac-extra-fields">
        <div class="mx-eac-field">
          <label>${__('Tipo de Solicitud')}</label>
          <select id="eac-tipo-solicitud">
            <option value="AF">${__('AF — Acto de fiscalización')}</option>
            <option value="FC">${__('FC — Fiscalización compulsa')}</option>
            <option value="DE">${__('DE — Devolución')}</option>
            <option value="CO">${__('CO — Compensación')}</option>
          </select>
        </div>
        <div class="mx-eac-field" id="eac-num-orden-wrap">
          <label>${__('Número de Orden')}</label>
          <input type="text" id="eac-num-orden" placeholder="ABC1234567/12" maxlength="13" />
        </div>
        <div class="mx-eac-field" id="eac-num-tramite-wrap" style="display:none">
          <label>${__('Número de Trámite')}</label>
          <input type="text" id="eac-num-tramite" placeholder="12345678901234" maxlength="14" />
        </div>
      </div>
      <div id="eac-polizas-status"></div>
      <button class="mx-eac-btn mx-eac-btn--primary" id="eac-polizas-btn">
        <span>⬇</span> ${__('Descargar Pólizas XML')}
      </button>
    </div>

  </div>
</div>`;

        $(this.wrapper).find('.page-content').html(html);
        this.$root = $(this.wrapper).find('.mx-eac-page');

        this._bindEvents();
    }

    // ── Event binding ────────────────────────────────────────────────────────

    _bindEvents() {
        // Balanza: show/hide FechaModBal when Complementaria is selected
        this.$root.find('#eac-tipo-envio').on('change', (e) => {
            const show = e.target.value === 'C';
            this.$root.find('#eac-fecha-mod-wrap').toggle(show);
        });

        // Pólizas: show/hide NumOrden / NumTramite based on TipoSolicitud
        this.$root.find('#eac-tipo-solicitud').on('change', (e) => {
            const v = e.target.value;
            const isAudit = v === 'AF' || v === 'FC';
            this.$root.find('#eac-num-orden-wrap').toggle(isAudit);
            this.$root.find('#eac-num-tramite-wrap').toggle(!isAudit);
        });

        // Download buttons
        this.$root.find('#eac-catalog-btn').on('click', () => this._downloadCatalog());
        this.$root.find('#eac-balanza-btn').on('click', () => this._downloadBalanza());
        this.$root.find('#eac-polizas-btn').on('click', () => this._downloadPolizas());
    }

    // ── Data loading ─────────────────────────────────────────────────────────

    async _loadCompanies() {
        try {
            const r = await frappe.call({
                method: 'erpnext_mexico.cfdi.page.mx_electronic_accounting.mx_electronic_accounting.get_companies',
            });
            this.companies = (r && r.message) ? r.message : [];
        } catch (_e) {
            this.companies = [];
        }

        const $sel = this.$root.find('#eac-company');
        if (this.companies.length === 0) {
            $sel.html(`<option value="">${__('Sin empresas con RFC configurado')}</option>`);
            return;
        }

        const opts = this.companies.map(c =>
            `<option value="${frappe.utils.escape_html(c.name)}">`
            + `${frappe.utils.escape_html(c.company_name)} — ${frappe.utils.escape_html(c.mx_rfc)}`
            + `</option>`
        ).join('');
        $sel.html(opts);
    }

    // ── Download helpers ─────────────────────────────────────────────────────

    _getFilters() {
        return {
            company: this.$root.find('#eac-company').val(),
            year: parseInt(this.$root.find('#eac-year').val(), 10),
            month: parseInt(this.$root.find('#eac-month').val(), 10),
        };
    }

    _validateFilters(filters) {
        if (!filters.company) {
            frappe.msgprint(__('Selecciona una empresa.'));
            return false;
        }
        if (!filters.year || !filters.month) {
            frappe.msgprint(__('Selecciona año y mes.'));
            return false;
        }
        return true;
    }

    _setBusy(btnId, statusId, busy) {
        const $btn = this.$root.find(`#${btnId}`);
        if (busy) {
            $btn.prop('disabled', true)
                .html('<span class="mx-eac-spinner"></span> ' + __('Generando...'));
            this.$root.find(`#${statusId}`).html('');
        } else {
            const origLabels = {
                'eac-catalog-btn': `<span>⬇</span> ${__('Descargar Catálogo XML')}`,
                'eac-balanza-btn':  `<span>⬇</span> ${__('Descargar Balanza XML')}`,
                'eac-polizas-btn':  `<span>⬇</span> ${__('Descargar Pólizas XML')}`,
            };
            $btn.prop('disabled', false).html(origLabels[btnId] || __('Descargar'));
        }
    }

    _showStatus(statusId, success, message) {
        const cls = success ? 'mx-eac-status--success' : 'mx-eac-status--error';
        this.$root.find(`#${statusId}`).html(
            `<span class="mx-eac-status ${cls}">${frappe.utils.escape_html(message)}</span>`
        );
    }

    _triggerDownload(xmlString, filename) {
        const blob = new Blob([xmlString], { type: 'application/xml;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    _buildFilename(prefix, company, year, month) {
        const rfc = (this.companies.find(c => c.name === company) || {}).mx_rfc || 'RFC';
        return `${rfc}_${year}${String(month).padStart(2, '0')}_${prefix}.xml`;
    }

    // ── Catalog download ─────────────────────────────────────────────────────

    async _downloadCatalog() {
        const f = this._getFilters();
        if (!this._validateFilters(f)) return;

        this._setBusy('eac-catalog-btn', 'eac-catalog-status', true);
        try {
            const r = await frappe.call({
                method: 'erpnext_mexico.electronic_accounting.catalog_xml.generate_catalog_xml',
                args: { company: f.company, year: f.year, month: f.month },
            });
            if (r && r.message) {
                const fname = this._buildFilename('CT', f.company, f.year, f.month);
                this._triggerDownload(r.message, fname);
                this._showStatus('eac-catalog-status', true, `✓ ${fname}`);
            } else {
                this._showStatus('eac-catalog-status', false, __('Sin datos — no se generó XML.'));
            }
        } catch (err) {
            const msg = (err && err.message) ? err.message : __('Error al generar el catálogo.');
            this._showStatus('eac-catalog-status', false, msg);
        } finally {
            this._setBusy('eac-catalog-btn', 'eac-catalog-status', false);
        }
    }

    // ── Balanza download ─────────────────────────────────────────────────────

    async _downloadBalanza() {
        const f = this._getFilters();
        if (!this._validateFilters(f)) return;

        const tipoEnvio = this.$root.find('#eac-tipo-envio').val();
        const fechaMod = this.$root.find('#eac-fecha-mod-bal').val() || '';

        if (tipoEnvio === 'C' && !fechaMod) {
            frappe.msgprint(__('Indica la fecha de modificación de balanza para envío Complementario.'));
            return;
        }

        this._setBusy('eac-balanza-btn', 'eac-balanza-status', true);
        try {
            const r = await frappe.call({
                method: 'erpnext_mexico.electronic_accounting.balanza_xml.generate_balanza_xml',
                args: {
                    company: f.company,
                    year: f.year,
                    month: f.month,
                    tipo_envio: tipoEnvio,
                    fecha_mod_bal: fechaMod,
                },
            });
            if (r && r.message) {
                const suffix = tipoEnvio === 'C' ? 'BCC' : 'BC';
                const fname = this._buildFilename(suffix, f.company, f.year, f.month);
                this._triggerDownload(r.message, fname);
                this._showStatus('eac-balanza-status', true, `✓ ${fname}`);
            } else {
                this._showStatus('eac-balanza-status', false, __('Sin movimientos en el periodo.'));
            }
        } catch (err) {
            const msg = (err && err.message) ? err.message : __('Error al generar la balanza.');
            this._showStatus('eac-balanza-status', false, msg);
        } finally {
            this._setBusy('eac-balanza-btn', 'eac-balanza-status', false);
        }
    }

    // ── Pólizas download ─────────────────────────────────────────────────────

    async _downloadPolizas() {
        const f = this._getFilters();
        if (!this._validateFilters(f)) return;

        const tipoSol = this.$root.find('#eac-tipo-solicitud').val();
        const numOrden = this.$root.find('#eac-num-orden').val().trim();
        const numTramite = this.$root.find('#eac-num-tramite').val().trim();

        // Client-side validation mirrors server validation
        if ((tipoSol === 'AF' || tipoSol === 'FC') && !numOrden) {
            frappe.msgprint(__('El Número de Orden es requerido para {0}.').replace('{0}', tipoSol));
            return;
        }
        if ((tipoSol === 'DE' || tipoSol === 'CO') && !numTramite) {
            frappe.msgprint(__('El Número de Trámite es requerido para {0}.').replace('{0}', tipoSol));
            return;
        }

        this._setBusy('eac-polizas-btn', 'eac-polizas-status', true);
        try {
            const r = await frappe.call({
                method: 'erpnext_mexico.electronic_accounting.polizas_xml.generate_polizas_xml',
                args: {
                    company: f.company,
                    year: f.year,
                    month: f.month,
                    tipo_solicitud: tipoSol,
                    num_orden: numOrden,
                    num_tramite: numTramite,
                },
            });
            if (r && r.message) {
                const fname = this._buildFilename('PL', f.company, f.year, f.month);
                this._triggerDownload(r.message, fname);
                this._showStatus('eac-polizas-status', true, `✓ ${fname}`);
            } else {
                this._showStatus('eac-polizas-status', false, __('Sin pólizas en el periodo.'));
            }
        } catch (err) {
            const msg = (err && err.message) ? err.message : __('Error al generar las pólizas.');
            this._showStatus('eac-polizas-status', false, msg);
        } finally {
            this._setBusy('eac-polizas-btn', 'eac-polizas-status', false);
        }
    }
}
