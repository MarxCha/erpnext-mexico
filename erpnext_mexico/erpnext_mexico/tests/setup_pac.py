"""Configure PAC credentials for testing."""
import os
import frappe


def run():
    if not frappe.db.exists("MX PAC Credentials", {"pac_name": "Finkok"}):
        doc = frappe.get_doc({
            "doctype": "MX PAC Credentials",
            "pac_name": "Finkok",
            "pac_username": os.environ.get("FINKOK_TEST_USER", ""),
            "pac_password": os.environ.get("FINKOK_TEST_PASS", ""),
            "is_sandbox": 1,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"Created PAC Credentials: {doc.name}")
    else:
        name = frappe.db.get_value("MX PAC Credentials", {"pac_name": "Finkok"}, "name")
        print(f"PAC Credentials already exists: {name}")
