# -*- coding: utf-8 -*-
"""Fase 1: Master Data — Company, Customers, Suppliers, Items, Employees, Bank Account."""
import frappe
from erpnext_mexico.seed.constants import (
    COMPANY, CUSTOMERS, SUPPLIERS, ITEMS, EMPLOYEES,
)

G = "\033[92m"
Y = "\033[93m"
R = "\033[0m"


def ok(msg):
    print(f"  {G}[OK]{R} {msg}")


def skip(msg):
    print(f"  {Y}[SKIP]{R} {msg}")


def section(title):
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def _set_values(doctype, name, field_map):
    for field, value in field_map.items():
        frappe.db.set_value(doctype, name, field, value, update_modified=False)
    frappe.db.commit()


def _safe_link(doctype, value):
    """Return value only if the linked record exists."""
    return value if frappe.db.exists(doctype, value) else None


def seed_company():
    section("1.1 Company Fiscal Data")
    frappe.db.set_value("Company", COMPANY, "tax_id", "EKU9003173C9", update_modified=False)
    mx = {"mx_rfc": "EKU9003173C9", "mx_nombre_fiscal": "ESCUELA KEMPER URGATE"}
    if _safe_link("MX Fiscal Regime", "601"):
        mx["mx_regimen_fiscal"] = "601"
    if _safe_link("MX Postal Code", "42501"):
        mx["mx_lugar_expedicion"] = "42501"
    _set_values("Company", COMPANY, mx)

    # Better default accounts
    _set_values("Company", COMPANY, {
        "default_receivable_account": "CUENTAS POR COBRAR CLIENTES - MCT",
        "default_payable_account": "CUENTAS POR PAGAR PROVEEDORES - MCT",
        "default_income_account": "VENTAS NACIONALES - MCT",
    })
    ok("Company fiscal data + default accounts updated")


def seed_bank_account():
    section("1.1b Bank Account")
    acct_name = "BANCO DEMO - MCT"
    if not frappe.db.exists("Account", acct_name):
        parent = frappe.db.get_value("Account", {
            "company": COMPANY, "account_name": "BANCOS", "is_group": 1}, "name")
        if not parent:
            parent = frappe.db.get_value("Account", {
                "company": COMPANY, "root_type": "Asset", "is_group": 1}, "name")
        frappe.get_doc({
            "doctype": "Account",
            "account_name": "BANCO DEMO",
            "parent_account": parent,
            "company": COMPANY,
            "account_type": "Bank",
            "account_currency": "MXN",
        }).insert(ignore_permissions=True)
        frappe.db.commit()
        ok(f"Bank account: {acct_name}")
    else:
        skip(f"Bank account exists: {acct_name}")

    if not frappe.db.exists("Mode of Payment", "Transferencia"):
        frappe.get_doc({
            "doctype": "Mode of Payment",
            "mode_of_payment": "Transferencia",
            "type": "Bank",
            "accounts": [{"company": COMPANY, "default_account": acct_name}],
        }).insert(ignore_permissions=True)
        frappe.db.commit()
        ok("Mode of Payment 'Transferencia'")


def seed_customers():
    section("1.2 Customers (5)")
    for c in CUSTOMERS:
        if frappe.db.exists("Customer", c["name"]):
            skip(f"{c['name']}")
            continue
        doc = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": c["name"],
            "customer_type": c["customer_type"],
            "customer_group": "Commercial" if c["customer_type"] == "Company" else "Individual",
            "territory": "Mexico",
        })
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.insert()
        frappe.db.commit()

        mx = {"mx_rfc": c["rfc"], "mx_nombre_fiscal": c["nombre_fiscal"]}
        for field, dt, val in [
            ("mx_regimen_fiscal", "MX Fiscal Regime", c["regimen"]),
            ("mx_domicilio_fiscal_cp", "MX Postal Code", c["cp"]),
            ("mx_default_uso_cfdi", "MX CFDI Use", c["uso_cfdi"]),
            ("mx_default_forma_pago", "MX Payment Form", c["forma_pago"]),
        ]:
            if _safe_link(dt, val):
                mx[field] = val
        _set_values("Customer", doc.name, mx)
        ok(f"{c['name']} (RFC {c['rfc']})")


def seed_suppliers():
    section("1.3 Suppliers (5)")
    for s in SUPPLIERS:
        if frappe.db.exists("Supplier", s["name"]):
            skip(f"{s['name']}")
            continue
        doc = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": s["name"],
            "supplier_group": "Services",
            "supplier_type": "Company",
        })
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.insert()
        frappe.db.commit()

        mx = {
            "mx_rfc": s["rfc"],
            "mx_tipo_tercero_diot": s["tipo_tercero"],
            "mx_tipo_operacion_diot": s["tipo_operacion"],
        }
        if s["tipo_tercero"] == "Extranjero":
            mx.update({
                "mx_nit_extranjero": s.get("nit_extranjero", ""),
                "mx_pais_residencia": s.get("pais_residencia", ""),
                "mx_nacionalidad": s.get("nacionalidad", ""),
            })
        _set_values("Supplier", doc.name, mx)
        ok(f"{s['name']} (RFC {s['rfc']}, DIOT: {s['tipo_tercero']}/{s['tipo_operacion']})")


def seed_items():
    section("1.4 Items (8)")
    for item in ITEMS:
        if frappe.db.exists("Item", item["item_code"]):
            skip(f"{item['item_code']}")
            continue
        doc = frappe.get_doc({
            "doctype": "Item",
            "item_code": item["item_code"],
            "item_name": item["item_name"],
            "item_group": "Services",
            "stock_uom": item["uom"],
            "is_stock_item": 0,
            "is_sales_item": 1,
            "is_purchase_item": 1,
        })
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.insert()
        frappe.db.commit()

        # Item Price
        if not frappe.db.exists("Item Price", {"item_code": item["item_code"], "selling": 1}):
            frappe.get_doc({
                "doctype": "Item Price",
                "item_code": item["item_code"],
                "price_list": "Standard Selling",
                "price_list_rate": item["rate"],
                "currency": "MXN",
            }).insert(ignore_permissions=True)
            frappe.db.commit()

        # SAT classification
        mx = {}
        if _safe_link("MX Product Service Key", item["clave_prod_serv"]):
            mx["mx_clave_prod_serv"] = item["clave_prod_serv"]
        if _safe_link("MX Unit Key", item["clave_unidad"]):
            mx["mx_clave_unidad"] = item["clave_unidad"]
        if mx:
            _set_values("Item", item["item_code"], mx)
        ok(f"{item['item_code']} — {item['item_name']} (SAT: {item['clave_prod_serv']})")


def seed_employees():
    section("1.5 Employees (2)")
    for emp in EMPLOYEES:
        if frappe.db.exists("Employee", {"employee_name": emp["employee_name"]}):
            skip(f"{emp['employee_name']}")
            continue
        if not frappe.db.exists("Designation", emp["designation"]):
            frappe.get_doc({"doctype": "Designation", "designation": emp["designation"]}).insert(ignore_permissions=True)
            frappe.db.commit()
        doc = frappe.get_doc({
            "doctype": "Employee",
            "first_name": emp["first_name"],
            "last_name": emp["last_name"],
            "employee_name": emp["employee_name"],
            "company": COMPANY,
            "date_of_birth": emp["date_of_birth"],
            "date_of_joining": emp["date_of_joining"],
            "gender": emp["gender"],
            "designation": emp["designation"],
            "status": "Active",
        })
        doc.flags.ignore_permissions = True
        doc.flags.ignore_mandatory = True
        doc.insert()
        frappe.db.commit()
        # mx_rfc only exists if Employee custom fields were created (requires HRMS or manual setup)
        if frappe.db.exists("Custom Field", "Employee-mx_rfc"):
            _set_values("Employee", doc.name, {"mx_rfc": emp["rfc"]})
        ok(f"{emp['employee_name']} (RFC {emp['rfc']})")


def run():
    print("\n" + "=" * 60)
    print("  FASE 1: ERPNext Master Data")
    print("=" * 60)
    frappe.flags.ignore_permissions = True
    seed_company()
    seed_bank_account()
    seed_customers()
    seed_suppliers()
    seed_items()
    seed_employees()
    print(f"\n{G}Fase 1 completa.{R}")
