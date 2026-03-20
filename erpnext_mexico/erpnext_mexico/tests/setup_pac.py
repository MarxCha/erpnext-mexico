"""Configure PAC credentials for testing."""
import frappe


def run():
    if not frappe.db.exists("MX PAC Credentials", {"pac_name": "Finkok"}):
        doc = frappe.get_doc({
            "doctype": "MX PAC Credentials",
            "pac_name": "Finkok",
            "pac_username": "marx_chavez@yahoo.com",
            "pac_password": "fantok-cimde8-zofhyG",
            "is_sandbox": 1,
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"Created PAC Credentials: {doc.name}")
    else:
        name = frappe.db.get_value("MX PAC Credentials", {"pac_name": "Finkok"}, "name")
        print(f"PAC Credentials already exists: {name}")
