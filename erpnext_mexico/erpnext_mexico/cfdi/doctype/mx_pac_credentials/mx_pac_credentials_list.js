// MX PAC Credentials — Enhanced List View
frappe.listview_settings['MX PAC Credentials'] = {
    get_indicator: function(doc) {
        if (doc.is_sandbox) return [__('Sandbox'), 'orange', 'is_sandbox,=,1'];
        return [__('Producción'), 'green', 'is_sandbox,=,0'];
    },
};
