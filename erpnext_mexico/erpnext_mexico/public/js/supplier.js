// ERPNext México — Supplier form extension
// Datos fiscales del proveedor para DIOT

frappe.ui.form.on("Supplier", {
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

    mx_tipo_tercero_diot(frm) {
        // Mostrar/ocultar campos de extranjero
        const is_extranjero = frm.doc.mx_tipo_tercero_diot === "Extranjero";
        frm.toggle_reqd("mx_pais_residencia", is_extranjero);
    },
});
