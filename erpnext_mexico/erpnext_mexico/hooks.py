app_name = "erpnext_mexico"
app_title = "ERPNext Mexico"
app_publisher = "MD Consultoría SC"
app_description = "Localización fiscal mexicana para ERPNext: CFDI 4.0, Complemento de Pagos 2.0, DIOT, Contabilidad Electrónica"
app_email = "contacto@mdconsultoria-ti.com"
app_license = "GPL-3.0"
app_logo_url = "/assets/erpnext_mexico/images/logo.png"

required_apps = ["frappe/erpnext"]

# ─────────────────────────────────────────────
# Static assets — CSS / JS incluidos globalmente
# ─────────────────────────────────────────────
app_include_css = "/assets/erpnext_mexico/css/erpnext_mexico.css"

# ─────────────────────────────────────────────
# Lifecycle hooks
# ─────────────────────────────────────────────
after_install = "erpnext_mexico.install.after_install"
before_uninstall = "erpnext_mexico.uninstall.before_uninstall"

# Condicional: si HRMS está instalado, crear campos de nómina
after_app_install = "erpnext_mexico.install.after_app_install"

# ─────────────────────────────────────────────
# Doc Events — hooks en DocTypes de ERPNext
# ─────────────────────────────────────────────
doc_events = {
    "Sales Invoice": {
        "validate": "erpnext_mexico.invoicing.overrides.sales_invoice.validate",
        "on_submit": "erpnext_mexico.invoicing.overrides.sales_invoice.on_submit",
        "on_cancel": "erpnext_mexico.invoicing.overrides.sales_invoice.on_cancel",
    },
    "Payment Entry": {
        "validate": "erpnext_mexico.invoicing.overrides.payment_entry.validate",
        "on_submit": "erpnext_mexico.invoicing.overrides.payment_entry.on_submit",
        "on_cancel": "erpnext_mexico.invoicing.overrides.payment_entry.on_cancel",
    },
    "Purchase Invoice": {
        "validate": "erpnext_mexico.invoicing.overrides.purchase_invoice.validate",
    },
    "Salary Slip": {
        "validate": "erpnext_mexico.payroll.overrides.salary_slip.validate",
        "on_submit": "erpnext_mexico.payroll.overrides.salary_slip.on_submit",
        "on_cancel": "erpnext_mexico.payroll.overrides.salary_slip.on_cancel",
    },
    "Delivery Note": {
        "on_submit": "erpnext_mexico.carta_porte.overrides.delivery_note.on_submit",
        "on_cancel": "erpnext_mexico.carta_porte.overrides.delivery_note.on_cancel",
    },
}

# ─────────────────────────────────────────────
# DocType JS — extensiones de formulario
# ─────────────────────────────────────────────
doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
    "Purchase Invoice": "public/js/purchase_invoice.js",
    "Payment Entry": "public/js/payment_entry.js",
    "Customer": "public/js/customer.js",
    "Supplier": "public/js/supplier.js",
    "Item": "public/js/item.js",
    "Company": "public/js/company.js",
    "Employee": "public/js/employee.js",
    "Delivery Note": "public/js/delivery_note.js",
    "Salary Slip": "public/js/salary_slip.js",
}

# ─────────────────────────────────────────────
# Fixtures — datos que se exportan/importan con la app
# ─────────────────────────────────────────────
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["fieldname", "like", "mx_%"]],
    },
    {
        "dt": "Property Setter",
        "filters": [["name", "like", "%mx_%"]],
    },
    {
        "dt": "Print Format",
        "filters": [["module", "=", "ERPNext Mexico"]],
    },
]

# ─────────────────────────────────────────────
# Scheduler events — tareas programadas
# ─────────────────────────────────────────────
scheduler_events = {
    "hourly": [
        "erpnext_mexico.cfdi.tasks.check_cancellation_status",
    ],
    "daily": [
        "erpnext_mexico.cfdi.tasks.check_certificate_expiry",
    ],
}

# ─────────────────────────────────────────────
# Jinja methods — helpers para print formats
# ─────────────────────────────────────────────
jinja = {
    "methods": [
        "erpnext_mexico.utils.jinja_methods.amount_to_words_mx",
        "erpnext_mexico.utils.jinja_methods.format_rfc",
        "erpnext_mexico.utils.jinja_methods.get_qr_code_data_uri",
    ],
}

# ─────────────────────────────────────────────
# Accounting (Chart of Accounts, Tax Templates)
# ─────────────────────────────────────────────
regional_overrides = {
    "Mexico": {
        "erpnext.controllers.taxes_and_totals.get_regional_address_details": (
            "erpnext_mexico.utils.regional.get_regional_address_details"
        ),
    },
}
