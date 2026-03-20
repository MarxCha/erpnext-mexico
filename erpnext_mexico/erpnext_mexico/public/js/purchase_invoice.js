// ERPNext México — Purchase Invoice form extension
// Campos mx_* para recepción y validación de CFDI de proveedores

frappe.ui.form.on("Purchase Invoice", {
    refresh(frm) {
        // Indicador de validación SAT
        if (frm.doc.mx_sat_validation_status === "Vigente") {
            frm.page.set_indicator(__("CFDI Vigente"), "green");
        } else if (frm.doc.mx_sat_validation_status === "Cancelado") {
            frm.page.set_indicator(__("CFDI Cancelado"), "red");
        }
    },
});
