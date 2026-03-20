"""Configure CFDI Settings completely for E2E testing."""
import frappe


def run():
    settings = frappe.get_doc("MX CFDI Settings")

    # Get PAC credentials name
    pac_name = frappe.db.get_value("MX PAC Credentials", {"pac_name": "Finkok"}, "name")
    cert_name = frappe.db.get_value("MX Digital Certificate", {"mx_rfc": "EKU9003173C9"}, "name")

    settings.company = "MD Consultoria TI"
    settings.pac_provider = "Finkok"
    settings.pac_environment = "Sandbox"
    settings.pac_credentials = pac_name
    settings.default_certificate = cert_name
    settings.auto_stamp_on_submit = 1
    settings.auto_cancel_on_cancel = 0
    settings.keep_xml_files = 1
    settings.save(ignore_permissions=True)
    frappe.db.commit()

    print(f"CFDI Settings configured:")
    print(f"  company: {settings.company}")
    print(f"  pac_provider: {settings.pac_provider}")
    print(f"  pac_environment: {settings.pac_environment}")
    print(f"  pac_credentials: {settings.pac_credentials}")
    print(f"  default_certificate: {settings.default_certificate}")
    print(f"  auto_stamp: {settings.auto_stamp_on_submit}")
