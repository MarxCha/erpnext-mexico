# -*- coding: utf-8 -*-
"""Check recent CFDI errors."""
import frappe


def run():
    logs = frappe.get_all("MX CFDI Log", filters={"status": "Error"},
                          fields=["name", "reference_name", "error_message"],
                          order_by="creation desc", limit=5)
    if logs:
        print("CFDI Error Logs:")
        for l in logs:
            print(f"  {l.reference_name}: {(l.error_message or 'no msg')[:300]}")
    else:
        print("No CFDI error logs found")

    errs = frappe.get_all("Error Log", fields=["name", "error"],
                          order_by="creation desc", limit=3)
    if errs:
        print("\nError Logs:")
        for e in errs:
            print(f"  {e.name}: {(e.error or 'no error')[:300]}")
