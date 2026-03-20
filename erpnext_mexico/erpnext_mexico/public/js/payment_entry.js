// ERPNext México — Payment Entry form extension
// Complemento de Pagos 2.0

frappe.ui.form.on("Payment Entry", {
    refresh(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.mx_pago_status === "Timbrado") {
            frm.page.set_indicator(__("Complemento Timbrado"), "green");
        }

        // Botón de retry si hay error
        if (frm.doc.docstatus === 1 && frm.doc.mx_pago_status === "Error") {
            frm.add_custom_button(__("Reintentar Timbrado"), () => {
                frappe.call({
                    method: "erpnext_mexico.invoicing.overrides.payment_entry.retry_stamp_payment",
                    args: { docname: frm.doc.name },
                    callback: () => frm.reload_doc(),
                });
            }, __("CFDI"));
        }
    },
});
