frappe.pages['mx-setup-wizard'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Configuración Fiscal MX',
        single_column: true
    });

    page.main.addClass('mx-page');

    const wizard = new MXSetupWizard(page);
    wizard.init();
};

class MXSetupWizard {
    constructor(page) {
        this.page = page;
        this.current_step = 0;
        this.data = {};
        this.selected_company = null;
        this.steps = [
            { label: 'Empresa', icon: '🏢' },
            { label: 'RFC', icon: '📋' },
            { label: 'Certificado', icon: '🔐' },
            { label: 'PAC', icon: '🌐' },
            { label: 'Verificar', icon: '✓' },
        ];
    }

    async init() {
        const r = await frappe.call({
            method: 'erpnext_mexico.cfdi.page.mx_setup_wizard.mx_setup_wizard.get_setup_data',
        });
        this.data = r.message;
        this.render();
    }

    render() {
        this.page.main.find('.mx-wizard').remove();

        const html = `
        <div class="mx-wizard">
            ${this.render_progress()}
            <div class="mx-wizard__content">
                ${this.render_step()}
            </div>
            <div class="mx-wizard__actions">
                ${this.current_step > 0 ?
                    `<button class="btn-mx-secondary mx-wizard-prev">← Anterior</button>` :
                    `<a href="/app/mx-fiscal-dashboard" class="btn-mx-secondary" style="text-decoration: none;">← Dashboard</a>`
                }
                ${this.current_step < this.steps.length - 1 ?
                    `<button class="btn-mx-primary mx-wizard-next">Siguiente →</button>` :
                    `<button class="btn-mx-primary mx-wizard-finish">Completar ✓</button>`
                }
            </div>
        </div>
        `;

        this.page.main.append(html);
        this.bind_events();
    }

    render_progress() {
        let stepsHtml = '';
        this.steps.forEach((step, i) => {
            let cls = '';
            if (i < this.current_step) cls = 'mx-wizard__step--complete';
            else if (i === this.current_step) cls = 'mx-wizard__step--active';

            stepsHtml += `
                <div class="mx-wizard__step ${cls}">
                    <div class="mx-wizard__step-number">
                        ${i < this.current_step ? '✓' : i + 1}
                    </div>
                    <div class="mx-wizard__step-label">${step.label}</div>
                </div>
            `;
        });

        return `<div class="mx-wizard__progress">${stepsHtml}</div>`;
    }

    render_step() {
        switch (this.current_step) {
            case 0: return this.step_company();
            case 1: return this.step_rfc();
            case 2: return this.step_certificate();
            case 3: return this.step_pac();
            case 4: return this.step_verify();
        }
    }

    step_company() {
        const companies = this.data.companies || [];
        let options = companies.map(c =>
            `<option value="${c.name}" ${c.name === this.selected_company ? 'selected' : ''}>${c.name} (${c.abbr})</option>`
        ).join('');

        return `
            <h3 style="font-family: var(--mx-font-heading); font-size: 20px; font-weight: 700; margin-bottom: 8px;">
                Selecciona tu Empresa
            </h3>
            <p style="font-family: var(--mx-font-body); color: var(--mx-text-secondary); margin-bottom: 24px;">
                Elige la empresa que deseas configurar para facturación electrónica mexicana.
            </p>
            <div style="margin-bottom: 16px;">
                <label style="display: block; font-size: 13px; font-weight: 600; color: var(--mx-text-primary); margin-bottom: 6px;">Empresa</label>
                <select id="mx-wiz-company" style="width: 100%; padding: 10px 12px; border: 1px solid var(--mx-border); border-radius: var(--mx-radius-md); font-size: 14px; background: var(--mx-bg-secondary); color: var(--mx-text-primary);">
                    <option value="">-- Selecciona --</option>
                    ${options}
                </select>
            </div>
            ${companies.length === 0 ? `
                <div style="padding: 16px; background: var(--mx-warning-bg); border-radius: var(--mx-radius-md); color: #92400E; font-size: 13px;">
                    No se encontraron empresas. Crea una empresa primero en ERPNext.
                </div>
            ` : ''}
        `;
    }

    step_rfc() {
        const company = this.data.companies?.find(c => c.name === this.selected_company) || {};
        const regimes = this.data.fiscal_regimes || [];

        let regimeOptions = regimes.map(r =>
            `<option value="${r.code}" ${company.mx_regimen_fiscal === r.code ? 'selected' : ''}>${r.code} - ${r.description}</option>`
        ).join('');

        return `
            <h3 style="font-family: var(--mx-font-heading); font-size: 20px; font-weight: 700; margin-bottom: 8px;">
                Datos Fiscales
            </h3>
            <p style="font-family: var(--mx-font-body); color: var(--mx-text-secondary); margin-bottom: 24px;">
                Ingresa los datos fiscales de <strong>${this.selected_company}</strong> tal como aparecen en tu Constancia de Situación Fiscal del SAT.
            </p>
            <div style="display: grid; gap: 16px;">
                <div>
                    <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px;">RFC</label>
                    <input id="mx-wiz-rfc" type="text" value="${company.mx_rfc || ''}" maxlength="13"
                        placeholder="Ej: EKU9003173C9"
                        style="width: 100%; padding: 10px 12px; border: 1px solid var(--mx-border); border-radius: var(--mx-radius-md); font-size: 14px; font-family: var(--mx-font-mono); text-transform: uppercase;">
                </div>
                <div>
                    <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px;">Nombre / Razón Social (como aparece en el SAT)</label>
                    <input id="mx-wiz-nombre" type="text" value="${company.mx_nombre_fiscal || ''}"
                        placeholder="Nombre fiscal exacto"
                        style="width: 100%; padding: 10px 12px; border: 1px solid var(--mx-border); border-radius: var(--mx-radius-md); font-size: 14px;">
                </div>
                <div>
                    <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px;">Régimen Fiscal</label>
                    <select id="mx-wiz-regimen" style="width: 100%; padding: 10px 12px; border: 1px solid var(--mx-border); border-radius: var(--mx-radius-md); font-size: 14px;">
                        <option value="">-- Selecciona --</option>
                        ${regimeOptions}
                    </select>
                </div>
                <div>
                    <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px;">Código Postal (Domicilio Fiscal)</label>
                    <input id="mx-wiz-cp" type="text" value="${company.mx_lugar_expedicion || ''}" maxlength="5"
                        placeholder="Ej: 06600"
                        style="width: 100%; padding: 10px 12px; border: 1px solid var(--mx-border); border-radius: var(--mx-radius-md); font-size: 14px; font-family: var(--mx-font-mono);">
                </div>
            </div>
        `;
    }

    step_certificate() {
        const certs = this.data.certificates || [];

        let certList = '';
        if (certs.length) {
            certs.forEach(c => {
                const statusClass = c.status === 'Activo' ? 'timbrado' : 'error';
                certList += `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border: 1px solid var(--mx-border-light); border-radius: var(--mx-radius-md); margin-bottom: 8px;">
                        <div>
                            <div style="font-weight: 600; font-size: 14px;">${c.mx_rfc}</div>
                            <div style="font-size: 12px; color: var(--mx-text-muted); font-family: var(--mx-font-mono);">No. ${c.certificate_number || 'Sin parsear'}</div>
                        </div>
                        <span class="mx-status-pill mx-status-pill--${statusClass}">${c.status || 'Sin status'}</span>
                    </div>
                `;
            });
        }

        return `
            <h3 style="font-family: var(--mx-font-heading); font-size: 20px; font-weight: 700; margin-bottom: 8px;">
                Certificado de Sello Digital (CSD)
            </h3>
            <p style="font-family: var(--mx-font-body); color: var(--mx-text-secondary); margin-bottom: 24px;">
                El CSD es necesario para firmar tus facturas electrónicas. Necesitas el archivo .cer, el .key y la contraseña.
            </p>
            ${certList || `
                <div style="padding: 20px; background: var(--mx-bg-tertiary); border-radius: var(--mx-radius-md); text-align: center; margin-bottom: 16px;">
                    <div style="font-size: 32px; margin-bottom: 8px;">🔐</div>
                    <div style="font-size: 14px; color: var(--mx-text-secondary);">No hay certificados cargados</div>
                </div>
            `}
            <a href="/app/mx-digital-certificate/new" target="_blank" class="btn-mx-primary" style="display: inline-block; text-decoration: none; margin-top: 8px;">
                + Cargar Certificado CSD
            </a>
            <p style="font-size: 12px; color: var(--mx-text-muted); margin-top: 12px;">
                RFC de prueba SAT: EKU9003173C9 | Contraseña: 12345678a
            </p>
        `;
    }

    step_pac() {
        const settings = this.data.settings || {};
        const pacs = this.data.pac_credentials || [];

        let pacList = '';
        pacs.forEach(p => {
            pacList += `<option value="${p.name}" ${settings.pac_credentials === p.name ? 'selected' : ''}>${p.pac_name} ${p.is_sandbox ? '(Sandbox)' : '(Producción)'}</option>`;
        });

        return `
            <h3 style="font-family: var(--mx-font-heading); font-size: 20px; font-weight: 700; margin-bottom: 8px;">
                Proveedor de Certificación (PAC)
            </h3>
            <p style="font-family: var(--mx-font-body); color: var(--mx-text-secondary); margin-bottom: 24px;">
                Selecciona tu PAC para timbrar facturas. Recomendamos iniciar con Sandbox para pruebas.
            </p>
            <div style="display: grid; gap: 16px;">
                <div>
                    <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px;">PAC</label>
                    <select id="mx-wiz-pac" style="width: 100%; padding: 10px 12px; border: 1px solid var(--mx-border); border-radius: var(--mx-radius-md); font-size: 14px;">
                        <option value="">-- Selecciona --</option>
                        <option value="Finkok" ${settings.pac_provider === 'Finkok' ? 'selected' : ''}>Finkok / Quadrum</option>
                        <option value="SW Sapien" ${settings.pac_provider === 'SW Sapien' ? 'selected' : ''}>SW Sapien</option>
                    </select>
                </div>
                <div>
                    <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px;">Ambiente</label>
                    <select id="mx-wiz-env" style="width: 100%; padding: 10px 12px; border: 1px solid var(--mx-border); border-radius: var(--mx-radius-md); font-size: 14px;">
                        <option value="Sandbox" ${settings.pac_environment === 'Sandbox' ? 'selected' : ''}>🧪 Sandbox (Pruebas)</option>
                        <option value="Production" ${settings.pac_environment === 'Production' ? 'selected' : ''}>🚀 Producción</option>
                    </select>
                </div>
                <div>
                    <label style="display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px;">Credenciales PAC</label>
                    ${pacs.length ? `
                        <select id="mx-wiz-pac-cred" style="width: 100%; padding: 10px 12px; border: 1px solid var(--mx-border); border-radius: var(--mx-radius-md); font-size: 14px;">
                            <option value="">-- Selecciona --</option>
                            ${pacList}
                        </select>
                    ` : `
                        <a href="/app/mx-pac-credentials/new" target="_blank" class="btn-mx-secondary" style="display: inline-block; text-decoration: none;">
                            + Crear Credenciales PAC
                        </a>
                    `}
                </div>
            </div>
            <div style="margin-top: 16px; padding: 12px; background: var(--mx-info-bg); border-radius: var(--mx-radius-md); font-size: 12px; color: #1E40AF;">
                <strong>Sandbox Finkok:</strong> demo-facturacion.finkok.com<br>
                <strong>Sandbox SW Sapien:</strong> api.test.sw.com.mx
            </div>
        `;
    }

    step_verify() {
        const company = this.data.companies?.find(c => c.name === this.selected_company) || {};
        const certs = this.data.certificates || [];
        const settings = this.data.settings || {};

        const checks = [
            { label: 'RFC configurado', done: !!company.mx_rfc, detail: company.mx_rfc || '—' },
            { label: 'Razón Social', done: !!company.mx_nombre_fiscal, detail: company.mx_nombre_fiscal || '—' },
            { label: 'Régimen Fiscal', done: !!company.mx_regimen_fiscal, detail: company.mx_regimen_fiscal || '—' },
            { label: 'Código Postal', done: !!company.mx_lugar_expedicion, detail: company.mx_lugar_expedicion || '—' },
            { label: 'CSD Activo', done: certs.some(c => c.status === 'Activo'), detail: certs.length ? `${certs.length} certificado(s)` : '—' },
            { label: 'PAC Configurado', done: !!settings.pac_provider, detail: settings.pac_provider ? `${settings.pac_provider} (${settings.pac_environment})` : '—' },
        ];

        const allDone = checks.every(c => c.done);

        let checkRows = checks.map(c => `
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--mx-border-light);">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 18px;">${c.done ? '✅' : '⬜'}</span>
                    <span style="font-size: 14px; font-weight: ${c.done ? '600' : '400'}; color: ${c.done ? 'var(--mx-text-primary)' : 'var(--mx-text-muted)'};">${c.label}</span>
                </div>
                <span style="font-size: 13px; color: var(--mx-text-secondary); font-family: var(--mx-font-mono);">${c.detail}</span>
            </div>
        `).join('');

        return `
            <h3 style="font-family: var(--mx-font-heading); font-size: 20px; font-weight: 700; margin-bottom: 8px;">
                Verificación Final
            </h3>
            <p style="font-family: var(--mx-font-body); color: var(--mx-text-secondary); margin-bottom: 24px;">
                Revisa que todos los datos estén correctos antes de finalizar.
            </p>
            ${checkRows}
            ${allDone ? `
                <div style="margin-top: 24px; padding: 16px; background: var(--mx-success-bg); border-radius: var(--mx-radius-lg); text-align: center;">
                    <div style="font-size: 32px; margin-bottom: 8px;">🎉</div>
                    <div style="font-size: 16px; font-weight: 700; color: #065F46;">¡Configuración completa!</div>
                    <div style="font-size: 13px; color: #065F46; margin-top: 4px;">Tu empresa está lista para emitir CFDI.</div>
                </div>
            ` : `
                <div style="margin-top: 24px; padding: 16px; background: var(--mx-warning-bg); border-radius: var(--mx-radius-lg); text-align: center;">
                    <div style="font-size: 14px; color: #92400E;">Algunos pasos están pendientes. Completa la configuración para comenzar a facturar.</div>
                </div>
            `}
        `;
    }

    bind_events() {
        const self = this;

        this.page.main.find('.mx-wizard-next').on('click', () => {
            if (self.validate_step()) {
                self.save_step().then(() => {
                    self.current_step++;
                    self.render();
                });
            }
        });

        this.page.main.find('.mx-wizard-prev').on('click', () => {
            self.current_step--;
            self.render();
        });

        this.page.main.find('.mx-wizard-finish').on('click', () => {
            frappe.set_route('mx-fiscal-dashboard');
            frappe.show_alert({
                message: __('Configuración fiscal guardada'),
                indicator: 'green'
            });
        });

        // Step 0: company selection
        this.page.main.find('#mx-wiz-company').on('change', function() {
            self.selected_company = $(this).val();
        });
    }

    validate_step() {
        switch (this.current_step) {
            case 0:
                if (!this.selected_company) {
                    frappe.show_alert({message: __('Selecciona una empresa'), indicator: 'orange'});
                    return false;
                }
                return true;
            case 1:
                const rfc = this.page.main.find('#mx-wiz-rfc').val();
                if (!rfc || rfc.length < 12) {
                    frappe.show_alert({message: __('RFC inválido (12-13 caracteres)'), indicator: 'orange'});
                    return false;
                }
                return true;
            default:
                return true;
        }
    }

    async save_step() {
        switch (this.current_step) {
            case 1:
                await frappe.call({
                    method: 'erpnext_mexico.cfdi.page.mx_setup_wizard.mx_setup_wizard.save_company_fiscal',
                    args: {
                        company: this.selected_company,
                        rfc: this.page.main.find('#mx-wiz-rfc').val().toUpperCase(),
                        nombre_fiscal: this.page.main.find('#mx-wiz-nombre').val(),
                        regimen_fiscal: this.page.main.find('#mx-wiz-regimen').val(),
                        lugar_expedicion: this.page.main.find('#mx-wiz-cp').val(),
                    }
                });
                // Refresh data
                const r = await frappe.call({
                    method: 'erpnext_mexico.cfdi.page.mx_setup_wizard.mx_setup_wizard.get_setup_data',
                });
                this.data = r.message;
                break;
            case 3:
                const pac = this.page.main.find('#mx-wiz-pac').val();
                const env = this.page.main.find('#mx-wiz-env').val();
                const cred = this.page.main.find('#mx-wiz-pac-cred').val();
                if (pac) {
                    await frappe.call({
                        method: 'erpnext_mexico.cfdi.page.mx_setup_wizard.mx_setup_wizard.save_pac_settings',
                        args: {
                            pac_provider: pac,
                            pac_environment: env,
                            pac_credentials: cred || null,
                        }
                    });
                    const r2 = await frappe.call({
                        method: 'erpnext_mexico.cfdi.page.mx_setup_wizard.mx_setup_wizard.get_setup_data',
                    });
                    this.data = r2.message;
                }
                break;
        }
    }
}
