// MX Digital Certificate — Enhanced List View
frappe.listview_settings['MX Digital Certificate'] = {
    get_indicator: function(doc) {
        if (doc.status === 'Activo') return [__('Activo'), 'green', 'status,=,Activo'];
        if (doc.status === 'Expirado') return [__('Expirado'), 'red', 'status,=,Expirado'];
        if (doc.status === 'Revocado') return [__('Revocado'), 'grey', 'status,=,Revocado'];
        return [__('Sin Status'), 'grey', ''];
    },

    formatters: {
        certificate_number(value) {
            if (!value) return '<span style="color: var(--text-muted);">Sin parsear</span>';
            return `<span style="font-family: var(--mx-font-mono, monospace); font-size: 12px;">${value}</span>`;
        },
    },
};
