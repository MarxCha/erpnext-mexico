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
            // Show first 8 and last 4 chars
            if (value.length > 16) {
                return `<span style="font-family: var(--mx-font-mono, monospace); font-size: 12px; color: var(--mx-accent, #0052CC);">${value.substring(0, 8)}...${value.substring(value.length - 4)}</span>`;
            }
            return `<span style="font-family: monospace; font-size: 12px;">${value}</span>`;
        },
        cfdi_type(value) {
            const type_labels = {
                'I': '📄 Ingreso',
                'E': '📤 Egreso',
                'T': '🚚 Traslado',
                'N': '💰 Nómina',
                'P': '💳 Pago',
            };
            return type_labels[value] || value;
        },
        status(value) {
            const classes = {
                'Pending': 'pendiente',
                'Stamped': 'timbrado',
                'Cancelled': 'cancelado',
                'Error': 'error',
            };
            const labels = {
                'Pending': 'Pendiente',
                'Stamped': 'Timbrado',
                'Cancelled': 'Cancelado',
                'Error': 'Error',
            };
            const cls = classes[value] || 'pendiente';
            const label = labels[value] || value;
            return `<span class="mx-status-pill mx-status-pill--${cls}">${label}</span>`;
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
