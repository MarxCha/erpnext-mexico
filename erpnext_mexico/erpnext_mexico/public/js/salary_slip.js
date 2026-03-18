// ERPNext México — Salary Slip form extension
// Agrega botones de acción CFDI Nómina 1.2 Rev E

frappe.ui.form.on("Salary Slip", {
    refresh(frm) {
        mx_add_nomina_buttons(frm);
        mx_update_nomina_indicator(frm);
    }
});

function mx_add_nomina_buttons(frm) {
    if (!frm.doc.company) return;

    // Solo mostrar botones si la empresa es mexicana (tiene RFC configurado)
    frappe.db.get_value("Company", frm.doc.company, "mx_rfc").then(r => {
        if (!r.message || !r.message.mx_rfc) return;

        // Botón "Timbrar CFDI Nómina" — solo si submitted y no timbrado
        if (frm.doc.docstatus === 1 && frm.doc.mx_nomina_status !== "Timbrado") {
            frm.add_custom_button(__("Timbrar CFDI Nómina"), () => {
                frappe.confirm(
                    __("¿Desea timbrar este recibo de nómina ante el SAT?"),
                    () => {
                        frappe.call({
                            method: "erpnext_mexico.payroll.overrides.salary_slip.retry_stamp_nomina",
                            args: { salary_slip_name: frm.doc.name },
                            freeze: true,
                            freeze_message: __("Timbrando CFDI Nómina..."),
                            callback: () => frm.reload_doc()
                        });
                    }
                );
            }, __("CFDI Nómina"));
        }

        // Botón "Descargar XML" — si hay XML timbrado
        if (frm.doc.mx_nomina_xml) {
            frm.add_custom_button(__("Descargar XML Nómina"), () => {
                window.open(frm.doc.mx_nomina_xml);
            }, __("CFDI Nómina"));
        }
    });
}

function mx_update_nomina_indicator(frm) {
    if (frm.doc.mx_nomina_status === "Timbrado") {
        frm.dashboard.add_indicator(
            __("CFDI Nómina: {0}", [frm.doc.mx_nomina_uuid]),
            "green"
        );
    } else if (frm.doc.mx_nomina_status === "Error") {
        frm.dashboard.add_indicator(__("Error CFDI Nómina"), "red");
    } else if (frm.doc.mx_nomina_status === "Pendiente") {
        frm.dashboard.add_indicator(__("CFDI Nómina Pendiente"), "orange");
    } else if (frm.doc.mx_nomina_status === "Cancelado") {
        frm.dashboard.add_indicator(__("CFDI Nómina Cancelado"), "grey");
    }
}
