// MX Fiscal Regime — Enhanced List View
frappe.listview_settings['MX Fiscal Regime'] = {
    hide_name_column: true,

    formatters: {
        code(value) {
            return `<span style="font-family: var(--mx-font-mono, monospace); font-size: 13px; font-weight: 700; background: var(--mx-bg-tertiary, #F1F3F9); padding: 2px 8px; border-radius: 4px;">${value}</span>`;
        },
        persona_type(value) {
            const colors = {
                'Física': { bg: '#EFF6FF', color: '#1D4ED8' },
                'Moral': { bg: '#F0FDF4', color: '#166534' },
                'Ambas': { bg: '#FDF4FF', color: '#86198F' },
            };
            const c = colors[value] || { bg: '#F3F4F6', color: '#4B5563' };
            return value ? `<span style="display: inline-block; padding: 2px 10px; border-radius: 9999px; font-size: 11px; font-weight: 600; background: ${c.bg}; color: ${c.color};">${value}</span>` : '';
        },
    },
};
