// ERPNext México — Company form extension
// Datos fiscales del emisor

frappe.ui.form.on("Company", {
    mx_rfc(frm) {
        const rfc = frm.doc.mx_rfc;
        if (rfc && rfc.length >= 12) {
            const pattern = /^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$/;
            if (!pattern.test(rfc.toUpperCase())) {
                frappe.show_alert({
                    message: __("El RFC no tiene un formato válido"),
                    indicator: "orange",
                });
            }
        }
    },
});
