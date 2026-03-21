# -*- coding: utf-8 -*-
"""Verificacion de seed data en ERPNext."""
import frappe

G = "\033[92m"
RED = "\033[91m"
R = "\033[0m"


def _check(label, actual, expected):
    status = G + "PASS" if actual >= expected else RED + "FAIL"
    print(f"  [{status}{R}] {label}: {actual} (expected >= {expected})")
    return actual >= expected


def run():
    print("\n" + "=" * 60)
    print("  VERIFICACION ERPNext")
    print("=" * 60)

    ok = True
    ok &= _check("Customers", frappe.db.count("Customer"), 5)
    ok &= _check("Suppliers", frappe.db.count("Supplier"), 5)
    ok &= _check("Items", frappe.db.count("Item"), 8)
    ok &= _check("Employees", frappe.db.count("Employee"), 2)

    timbradas = frappe.db.count("Sales Invoice", {"mx_cfdi_status": "Timbrado"})
    ok &= _check("Sales Invoices Timbradas", timbradas, 9)
    ok &= _check("Purchase Invoices (submitted)", frappe.db.count("Purchase Invoice", {"docstatus": 1}), 8)
    ok &= _check("Payment Entries", frappe.db.count("Payment Entry"), 4)

    rfc_set = frappe.db.count("Customer", {"mx_rfc": ["is", "set"]})
    _check("Customers with RFC", rfc_set, 5)
    diot_set = frappe.db.count("Supplier", {"mx_tipo_tercero_diot": ["is", "set"]})
    _check("Suppliers with DIOT type", diot_set, 5)

    print(f"\n  {'VERIFICACION OK' if ok else 'CON ERRORES'}")
