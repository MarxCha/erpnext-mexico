"""Setup E2E test data for ERPNext Mexico."""
import frappe
import os


def run():
    results = []

    # 1. Company fiscal data
    company = frappe.get_doc("Company", "MD Consultoria TI")
    company.tax_id = "EKU9003173C9"
    if hasattr(company, "mx_rfc") or frappe.db.exists("Custom Field", "Company-mx_rfc"):
        frappe.db.set_value("Company", company.name, "mx_rfc", "EKU9003173C9", update_modified=False)
        frappe.db.set_value("Company", company.name, "mx_nombre_fiscal", "ESCUELA KEMPER URGATE", update_modified=False)
    company.save(ignore_permissions=True)
    frappe.db.commit()
    results.append("OK: Company fiscal data configured")

    # 2. Check small catalogs
    for dt in ["MX Fiscal Regime", "MX Payment Form", "MX Payment Method", "MX CFDI Use",
               "MX Tax Object", "MX Export Type", "MX Cancellation Reason"]:
        count = frappe.db.count(dt)
        results.append(f"{'OK' if count > 0 else 'EMPTY'}: {dt} has {count} records")

    # 3. Create test Customer
    if not frappe.db.exists("Customer", "Cliente Prueba MX"):
        cust = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": "Cliente Prueba MX",
            "customer_type": "Company",
            "customer_group": "All Customer Groups",
            "territory": "All Territories",
        })
        cust.flags.ignore_permissions = True
        cust.flags.ignore_mandatory = True
        cust.insert()
        frappe.db.commit()
        frappe.db.set_value("Customer", cust.name, "mx_rfc", "XAXX010101000")
        frappe.db.set_value("Customer", cust.name, "mx_nombre_fiscal", "PUBLICO EN GENERAL")
        frappe.db.commit()
        results.append(f"OK: Customer created: {cust.name}")
    else:
        results.append("OK: Customer 'Cliente Prueba MX' exists")

    # 4. Create test Supplier
    if not frappe.db.exists("Supplier", "Proveedor Prueba MX"):
        sup = frappe.get_doc({
            "doctype": "Supplier",
            "supplier_name": "Proveedor Prueba MX",
            "supplier_group": "All Supplier Groups",
            "supplier_type": "Company",
        })
        sup.flags.ignore_permissions = True
        sup.flags.ignore_mandatory = True
        sup.insert()
        frappe.db.commit()
        frappe.db.set_value("Supplier", sup.name, "mx_rfc", "AAA010101AAA")
        frappe.db.set_value("Supplier", sup.name, "mx_tipo_tercero_diot", "Nacional")
        frappe.db.commit()
        results.append(f"OK: Supplier created: {sup.name}")
    else:
        results.append("OK: Supplier 'Proveedor Prueba MX' exists")

    # 5. Create test Item
    if not frappe.db.exists("Item", "Servicio Consultoria MX"):
        item = frappe.get_doc({
            "doctype": "Item",
            "item_code": "Servicio Consultoria MX",
            "item_name": "Servicio de Consultoría TI",
            "item_group": "Services",
            "stock_uom": "Nos",
            "is_stock_item": 0,
        })
        item.flags.ignore_permissions = True
        item.flags.ignore_mandatory = True
        item.insert()
        frappe.db.commit()
        frappe.db.set_value("Item", item.name, "mx_clave_prod_serv", "84111506")
        frappe.db.set_value("Item", item.name, "mx_clave_unidad", "E48")
        frappe.db.commit()
        results.append(f"OK: Item created: {item.name}")
    else:
        results.append("OK: Item 'Servicio Consultoria MX' exists")

    # 6. Verify settings
    settings = frappe.get_doc("MX CFDI Settings")
    results.append(f"OK: CFDI Settings — company={settings.company}")

    # 7. Verify PAC & Cert
    results.append(f"OK: PAC Credentials: {frappe.db.count('MX PAC Credentials')} configured")
    results.append(f"OK: Digital Certificates: {frappe.db.count('MX Digital Certificate')} configured")

    # 8. Custom fields count
    for dt in ["Company", "Customer", "Supplier", "Item", "Sales Invoice", "Payment Entry"]:
        cf = frappe.db.count("Custom Field", {"dt": dt, "fieldname": ["like", "mx_%"]})
        results.append(f"OK: {dt} has {cf} mx_* custom fields")

    print("\n=== E2E SETUP RESULTS ===")
    for r in results:
        print(r)
    print("=== DONE ===")
