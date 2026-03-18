// ERPNext México — Delivery Note form extension
// Agrega botones de acción CFDI Carta Porte y visibilidad condicional de campos

frappe.ui.form.on("Delivery Note", {
    refresh(frm) {
        mx_add_carta_porte_buttons(frm);
        mx_update_carta_porte_indicator(frm);
    },

    mx_requires_carta_porte(frm) {
        // Mostrar/ocultar sección de datos de Carta Porte según el checkbox
        frm.trigger("toggle_carta_porte_fields");
    },

    toggle_carta_porte_fields(frm) {
        const requires = frm.doc.mx_requires_carta_porte;
        const cartaPorteFields = [
            "mx_cp_origen", "mx_estado_origen", "mx_municipio_origen",
            "mx_calle_origen", "mx_localidad_origen", "mx_referencia_origen",
            "mx_cp_destino", "mx_estado_destino", "mx_municipio_destino",
            "mx_calle_destino", "mx_localidad_destino", "mx_referencia_destino",
            "mx_distancia_recorrida", "mx_transp_internac",
            "mx_config_vehicular", "mx_placa_vehiculo", "mx_anio_modelo_vehiculo",
            "mx_perm_sct", "mx_num_permiso_sct",
            "mx_aseguradora_resp_civil", "mx_poliza_resp_civil",
            "mx_nombre_conductor", "mx_rfc_conductor", "mx_num_licencia_conductor",
        ];
        cartaPorteFields.forEach(f => frm.toggle_display(f, requires));
    },

    onload(frm) {
        if (frm.doc.mx_requires_carta_porte) {
            frm.trigger("toggle_carta_porte_fields");
        }
    }
});

function mx_add_carta_porte_buttons(frm) {
    if (!frm.doc.company) return;
    if (!frm.doc.mx_requires_carta_porte) return;

    // Botón "Timbrar Carta Porte" — solo si submitted y no timbrado
    if (frm.doc.docstatus === 1 && frm.doc.mx_carta_porte_status !== "Timbrado") {
        frm.add_custom_button(__("Timbrar Carta Porte"), () => {
            frappe.confirm(
                __("¿Desea timbrar la Carta Porte ante el SAT?"),
                () => {
                    frappe.call({
                        method: "erpnext_mexico.carta_porte.overrides.delivery_note.retry_stamp_carta_porte",
                        args: { delivery_note_name: frm.doc.name },
                        freeze: true,
                        freeze_message: __("Timbrando Carta Porte..."),
                        callback: () => frm.reload_doc()
                    });
                }
            );
        }, __("Carta Porte"));
    }

    // Botón "Descargar XML" — si hay XML adjunto
    if (frm.doc.mx_carta_porte_xml) {
        frm.add_custom_button(__("Descargar XML"), () => {
            window.open(frm.doc.mx_carta_porte_xml);
        }, __("Carta Porte"));
    }
}

function mx_update_carta_porte_indicator(frm) {
    if (!frm.doc.mx_requires_carta_porte) return;

    if (frm.doc.mx_carta_porte_status === "Timbrado") {
        frm.dashboard.add_indicator(
            __("Carta Porte Timbrada: {0}", [frm.doc.mx_carta_porte_uuid]),
            "green"
        );
    } else if (frm.doc.mx_carta_porte_status === "Error") {
        frm.dashboard.add_indicator(__("Error Carta Porte"), "red");
    } else if (frm.doc.mx_carta_porte_status === "Pendiente") {
        frm.dashboard.add_indicator(__("Carta Porte Pendiente"), "orange");
    }
}
