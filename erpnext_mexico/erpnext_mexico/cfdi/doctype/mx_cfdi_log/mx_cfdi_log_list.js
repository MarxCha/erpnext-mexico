// MX CFDI Log — Enhanced List View with Status Pills
frappe.listview_settings['MX CFDI Log'] = {
    get_indicator: function(doc) {
        const status_map = {
            'Pending': [__('Pendiente'), 'orange', 'status,=,Pending'],
            'Stamped': [__('Timbrado'), 'green', 'status,=,Stamped'],
            'Cancelled': [__('Cancelado'), 'grey', 'status,=,Cancelled'],
            'Error': [__('Error'), 'red', 'status,=,Error'],
        };
        return status_map[doc.status] || [__('Desconocido'), 'grey', ''];
    },

    formatters: {
        uuid(value) {
            if (!value) return '';
            // Frappe list view escapes HTML — return plain text only
            if (value.length > 16) {
                return value.substring(0, 8) + '...' + value.substring(value.length - 4);
            }
            return value;
        },
        cfdi_type(value) {
            const type_labels = {
                'I': 'Ingreso',
                'E': 'Egreso',
                'T': 'Traslado',
                'N': 'Nomina',
                'P': 'Pago',
            };
            return type_labels[value] || value;
        },
    },

    onload(listview) {
        // Add custom filters
        listview.page.add_inner_button(__('Solo Errores'), () => {
            listview.filter_area.add([[listview.doctype, 'status', '=', 'Error']]);
        });
        listview.page.add_inner_button(__('Solo Timbrados'), () => {
            listview.filter_area.add([[listview.doctype, 'status', '=', 'Stamped']]);
        });
    },
};
