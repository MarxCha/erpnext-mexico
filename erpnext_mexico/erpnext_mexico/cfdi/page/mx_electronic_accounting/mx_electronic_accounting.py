"""
Contabilidad Electrónica MX — Server-side page controller.
Exposes whitelisted API methods for the download page.

Individual XML generators live in:
  erpnext_mexico.electronic_accounting.catalog_xml
  erpnext_mexico.electronic_accounting.balanza_xml
  erpnext_mexico.electronic_accounting.polizas_xml
"""
import frappe
from frappe import _


@frappe.whitelist()
def get_companies() -> list[dict]:
    """Return active companies that have mx_rfc configured."""
    frappe.only_for(["System Manager", "Accounts Manager", "Accounts User"])

    return frappe.get_all(
        "Company",
        filters={"mx_rfc": ["!=", ""]},
        fields=["name", "company_name", "mx_rfc"],
        order_by="company_name",
    )
