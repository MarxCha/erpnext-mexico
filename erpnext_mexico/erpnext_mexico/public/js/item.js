// ERPNext México — Item form extension
// Clasificación SAT (ClaveProdServ, ClaveUnidad)

frappe.ui.form.on("Item", {
    refresh(frm) {
        // Indicador si faltan claves SAT
        if (frm.doc.mx_clave_prod_serv && frm.doc.mx_clave_unidad) {
            frm.dashboard.set_headline(
                __("Clasificación SAT: {0} / {1}", [frm.doc.mx_clave_prod_serv, frm.doc.mx_clave_unidad])
            );
        }
    },
});
