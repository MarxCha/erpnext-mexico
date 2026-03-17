// MX Product Service Key — Enhanced List View
frappe.listview_settings['MX Product Service Key'] = {
    hide_name_column: true,

    formatters: {
        code(value) {
            return `<span style="font-family: var(--mx-font-mono, monospace); font-size: 12px; font-weight: 600; color: var(--mx-accent, #0052CC);">${value}</span>`;
        },
    },

    onload(listview) {
        listview.page.set_title(__('Catálogo SAT — Productos y Servicios'));
    },
};
