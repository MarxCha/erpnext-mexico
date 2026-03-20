// ERPNext México — Employee form extension
// Datos fiscales y laborales para nómina CFDI

frappe.ui.form.on("Employee", {
    mx_curp(frm) {
        const curp = frm.doc.mx_curp;
        if (curp && curp.length === 18) {
            const pattern = /^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$/;
            if (!pattern.test(curp.toUpperCase())) {
                frappe.show_alert({
                    message: __("La CURP no tiene un formato válido"),
                    indicator: "orange",
                });
            }
        }
    },

    mx_nss(frm) {
        const nss = frm.doc.mx_nss;
        if (nss && nss.length !== 11) {
            frappe.show_alert({
                message: __("El NSS debe tener 11 dígitos"),
                indicator: "orange",
            });
        }
    },
});
