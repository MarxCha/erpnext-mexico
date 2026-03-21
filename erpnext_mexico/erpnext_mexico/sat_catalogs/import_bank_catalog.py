"""Import MX Bank SAT catalog from JSON fixture."""
import json
import os
import frappe


def run():
    fixture_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "fixtures", "mx_bank_sat.json"
    )
    with open(fixture_path, "r") as f:
        banks = json.load(f)

    count = 0
    for bank in banks:
        if not frappe.db.exists("MX Bank SAT", bank["code"]):
            frappe.get_doc({
                "doctype": "MX Bank SAT",
                "code": bank["code"],
                "description": bank["description"],
                "razon_social": bank.get("razon_social", ""),
            }).insert(ignore_permissions=True)
            count += 1

    frappe.db.commit()
    print(f"MX Bank SAT: {count} banks imported ({frappe.db.count('MX Bank SAT')} total)")
