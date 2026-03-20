"""Fix fiscal data for E2E testing — use doc API for custom fields."""
import frappe


def run():
    # 1. Fix Company fiscal data via Doc API
    company = frappe.get_doc("Company", "MD Consultoria TI")
    company.mx_rfc = "EKU9003173C9"
    company.mx_nombre_fiscal = "ESCUELA KEMPER URGATE"
    # Need to set regimen fiscal — check if "601" exists
    regime = frappe.db.get_value("MX Fiscal Regime", {"code": "601"}, "name")
    if not regime:
        regime = frappe.db.get_value("MX Fiscal Regime", "601", "name")
    company.mx_regimen_fiscal = regime or "601"
    # Need lugar de expedicion — create a test postal code if needed
    if not frappe.db.exists("MX Postal Code", "06000"):
        frappe.get_doc({
            "doctype": "MX Postal Code",
            "code": "06000",
            "description": "Cuauhtémoc, Ciudad de México",
        }).insert(ignore_permissions=True)
    company.mx_lugar_expedicion = "06000"
    company.save(ignore_permissions=True)
    frappe.db.commit()

    # Verify
    rfc = frappe.db.get_value("Company", "MD Consultoria TI", "mx_rfc")
    print(f"Company mx_rfc: {rfc}")
    print(f"Company mx_nombre_fiscal: {company.mx_nombre_fiscal}")
    print(f"Company mx_regimen_fiscal: {company.mx_regimen_fiscal}")
    print(f"Company mx_lugar_expedicion: {company.mx_lugar_expedicion}")

    # 2. Fix Customer fiscal data
    cust = frappe.get_doc("Customer", "Cliente Prueba MX")
    cust.mx_rfc = "XAXX010101000"
    cust.mx_nombre_fiscal = "PUBLICO EN GENERAL"
    cust.mx_regimen_fiscal = regime or "601"
    cust.mx_domicilio_fiscal_cp = "06000"
    cust.mx_default_uso_cfdi = "G03"
    cust.mx_default_forma_pago = "01"
    cust.save(ignore_permissions=True)
    frappe.db.commit()

    rfc_c = frappe.db.get_value("Customer", "Cliente Prueba MX", "mx_rfc")
    print(f"\nCustomer mx_rfc: {rfc_c}")
    print(f"Customer mx_regimen_fiscal: {cust.mx_regimen_fiscal}")
    print(f"Customer mx_domicilio_fiscal_cp: {cust.mx_domicilio_fiscal_cp}")

    # 3. Verify is_mexico_company now works
    from erpnext_mexico.cfdi.cfdi_helpers import is_mexico_company
    print(f"\nis_mexico_company: {is_mexico_company('MD Consultoria TI')}")
    print("DONE!")
