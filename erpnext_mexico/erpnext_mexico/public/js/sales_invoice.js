// ERPNext México — Sales Invoice form extension
// Agrega botones de acción CFDI y visibilidad condicional de campos

frappe.ui.form.on("Sales Invoice", {
    refresh(frm) {
        mx_add_cfdi_buttons(frm);
        mx_update_cfdi_indicator(frm);
    },

    customer(frm) {
        // Auto-fill fiscal defaults del cliente
        if (frm.doc.customer) {
            frappe.db.get_value("Customer", frm.doc.customer, [
                "mx_default_uso_cfdi", "mx_default_forma_pago"
            ]).then(r => {
                if (r.message) {
                    if (r.message.mx_default_uso_cfdi && !frm.doc.mx_uso_cfdi) {
                        frm.set_value("mx_uso_cfdi", r.message.mx_default_uso_cfdi);
                    }
                    if (r.message.mx_default_forma_pago && !frm.doc.mx_forma_pago) {
                        frm.set_value("mx_forma_pago", r.message.mx_default_forma_pago);
                    }
                }
            });
        }
    },

    mx_metodo_pago(frm) {
        // Si es PPD, forzar FormaPago = 99
        if (frm.doc.mx_metodo_pago === "PPD") {
            frm.set_value("mx_forma_pago", "99");
        }
    }
});

function mx_add_cfdi_buttons(frm) {
    if (!frm.doc.mx_rfc_company()) return;

    // Botón "Timbrar CFDI" — solo si submitted y no timbrado
    if (frm.doc.docstatus === 1 && frm.doc.mx_cfdi_status !== "Timbrado") {
        frm.add_custom_button(__("Timbrar CFDI"), () => {
            frappe.confirm(
                __("¿Desea timbrar esta factura ante el SAT?"),
                () => {
                    frappe.call({
                        method: "erpnext_mexico.invoicing.overrides.sales_invoice.retry_stamp",
                        args: { sales_invoice_name: frm.doc.name },
                        freeze: true,
                        freeze_message: __("Timbrando CFDI..."),
                        callback: () => frm.reload_doc()
                    });
                }
            );
        }, __("CFDI"));
    }

    // Botón "Cancelar CFDI" — solo si timbrado
    if (frm.doc.docstatus === 1 && frm.doc.mx_cfdi_status === "Timbrado") {
        frm.add_custom_button(__("Cancelar CFDI"), () => {
            mx_show_cancel_dialog(frm);
        }, __("CFDI"));
    }

    // Botón "Descargar XML" — si hay XML
    if (frm.doc.mx_xml_file) {
        frm.add_custom_button(__("Descargar XML"), () => {
            window.open(frm.doc.mx_xml_file);
        }, __("CFDI"));
    }

    // Botón "Descargar PDF" — si hay PDF
    if (frm.doc.mx_pdf_file) {
        frm.add_custom_button(__("Descargar PDF CFDI"), () => {
            window.open(frm.doc.mx_pdf_file);
        }, __("CFDI"));
    }
}

function mx_update_cfdi_indicator(frm) {
    if (frm.doc.mx_cfdi_status === "Timbrado") {
        frm.dashboard.add_indicator(
            __("CFDI Timbrado: {0}", [frm.doc.mx_cfdi_uuid]),
            "green"
        );
    } else if (frm.doc.mx_cfdi_status === "Error") {
        frm.dashboard.add_indicator(__("Error CFDI"), "red");
    } else if (frm.doc.mx_cfdi_status === "Cancelado") {
        frm.dashboard.add_indicator(__("CFDI Cancelado"), "orange");
    }
}

function mx_show_cancel_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __("Cancelar CFDI"),
        fields: [
            {
                label: __("Motivo de Cancelación"),
                fieldname: "reason",
                fieldtype: "Select",
                options: [
                    { value: "01", label: "01 - Comprobante emitido con errores con relación" },
                    { value: "02", label: "02 - Comprobante emitido con errores sin relación" },
                    { value: "03", label: "03 - No se llevó a cabo la operación" },
                    { value: "04", label: "04 - Operación nominativa relacionada en factura global" },
                ],
                reqd: 1,
            },
            {
                label: __("UUID del CFDI Sustituto"),
                fieldname: "substitute_uuid",
                fieldtype: "Data",
                depends_on: "eval:doc.reason==='01'",
                mandatory_depends_on: "eval:doc.reason==='01'",
                description: __("Solo para motivo 01: UUID del nuevo CFDI que sustituye a este"),
            },
        ],
        primary_action_label: __("Cancelar CFDI"),
        primary_action(values) {
            frappe.call({
                method: "erpnext_mexico.invoicing.overrides.sales_invoice.cancel_cfdi",
                args: {
                    sales_invoice_name: frm.doc.name,
                    reason: values.reason,
                    substitute_uuid: values.substitute_uuid || "",
                },
                freeze: true,
                freeze_message: __("Cancelando CFDI ante el SAT..."),
                callback: () => {
                    d.hide();
                    frm.reload_doc();
                }
            });
        }
    });
    d.show();
}

// Helper: verificar si la empresa tiene RFC configurado
frappe.ui.form.on("Sales Invoice", {
    mx_rfc_company() {
        return frappe.db.get_value("Company", cur_frm.doc.company, "mx_rfc")
            .then(r => !!r.message?.mx_rfc);
    }
});
