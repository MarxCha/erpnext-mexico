import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

@frappe.whitelist()
@rate_limit(limit=10, seconds=60)
def get_setup_data():
    """Get current setup state for the wizard."""
    frappe.only_for(["System Manager", "Accounts Manager"])

    companies = frappe.get_list("Company",
        filters={"country": ["in", ["Mexico", "México", ""]]},
        fields=["name", "abbr", "mx_rfc", "mx_nombre_fiscal", "mx_regimen_fiscal", "mx_lugar_expedicion"],
        order_by="creation",
    )

    if not companies:
        companies = frappe.get_list("Company",
            fields=["name", "abbr", "mx_rfc", "mx_nombre_fiscal", "mx_regimen_fiscal", "mx_lugar_expedicion"],
            order_by="creation",
            limit_page_length=5,
        )

    certificates = frappe.get_list("MX Digital Certificate",
        fields=["name", "mx_rfc", "certificate_number", "status", "valid_to"],
        order_by="creation desc",
    )

    settings = frappe.get_single("MX CFDI Settings")

    pac_credentials = frappe.get_list("MX PAC Credentials",
        fields=["name", "pac_name", "is_sandbox"],
    )

    fiscal_regimes = frappe.get_list("MX Fiscal Regime",
        fields=["code", "description", "persona_type"],
        order_by="code",
    )

    # Catalog count — used by verify step to warn if SAT catalogs are missing
    catalog_count = frappe.db.count("MX Product Service Key")

    return {
        "companies": companies,
        "certificates": certificates,
        "settings": {
            "pac_provider": settings.pac_provider,
            "pac_environment": settings.pac_environment,
            "pac_configured": bool(settings.pac_credentials),
            "certificate_configured": bool(settings.default_certificate),
        },
        "pac_credentials": pac_credentials,
        "fiscal_regimes": fiscal_regimes,
        "catalog_count": catalog_count,
    }

@frappe.whitelist()
@rate_limit(limit=5, seconds=60)
def save_company_fiscal(company, rfc, nombre_fiscal, regimen_fiscal, lugar_expedicion):
    """Save fiscal data for a company."""
    frappe.only_for(["System Manager", "Accounts Manager"])
    if not frappe.has_permission("Company", "write", company):
        frappe.throw(_("Sin permiso para modificar esta empresa"), frappe.PermissionError)

    # Validate RFC format server-side (M-20)
    if rfc:
        from erpnext_mexico.utils.rfc_validator import validate_rfc
        is_valid, msg = validate_rfc(rfc)
        if not is_valid:
            frappe.throw(msg, title="RFC inválido")

    doc = frappe.get_doc("Company", company)
    doc.mx_rfc = rfc
    doc.mx_nombre_fiscal = nombre_fiscal
    doc.mx_regimen_fiscal = regimen_fiscal
    doc.mx_lugar_expedicion = lugar_expedicion
    doc.save()
    frappe.db.commit()
    return {"success": True}

@frappe.whitelist()
@rate_limit(limit=5, seconds=60)
def save_pac_settings(pac_provider, pac_environment, pac_credentials=None):
    """Save PAC configuration."""
    frappe.only_for("System Manager")
    settings = frappe.get_single("MX CFDI Settings")
    settings.pac_provider = pac_provider
    settings.pac_environment = pac_environment
    if pac_credentials:
        settings.pac_credentials = pac_credentials
    settings.save()
    frappe.db.commit()
    return {"success": True}
