// MX CFDI Settings — Enhanced Form
frappe.ui.form.on('MX CFDI Settings', {
    refresh(frm) {
        // Add dashboard link
        frm.add_custom_button(__('Panel Fiscal'), () => {
            frappe.set_route('mx-fiscal-dashboard');
        }, __('Ir a'));

        frm.add_custom_button(__('Wizard de Configuración'), () => {
            frappe.set_route('mx-setup-wizard');
        }, __('Ir a'));

        // Show setup progress
        mx_show_setup_banner(frm);
    },

    pac_provider(frm) {
        if (frm.doc.pac_provider) {
            frappe.show_alert({
                message: __('PAC seleccionado: {0}', [frm.doc.pac_provider]),
                indicator: 'blue'
            });
        }
    },
});

function mx_show_setup_banner(frm) {
    const checks = [
        { label: 'PAC', done: !!frm.doc.pac_provider },
        { label: 'Credenciales', done: !!frm.doc.pac_credentials },
        { label: 'Certificado', done: !!frm.doc.default_certificate },
    ];

    const done = checks.filter(c => c.done).length;
    const total = checks.length;

    if (done < total) {
        const pending = checks.filter(c => !c.done).map(c => c.label).join(', ');
        frm.dashboard.set_headline_alert(
            `<div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-weight: 600;">Configuración ${done}/${total}</span>
                <span style="color: var(--text-muted);">— Pendiente: ${pending}</span>
            </div>`
        );
    } else {
        frm.dashboard.set_headline_alert(
            `<div style="color: var(--green-600); font-weight: 600;">
                ✓ Configuración CFDI completa
            </div>`
        );
    }
}
