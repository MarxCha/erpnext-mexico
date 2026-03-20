"""Load minimal SAT catalog records needed for E2E testing."""
import frappe


def run():
    records = [
        # MX Product Service Key — just the ones we need for testing
        {"doctype": "MX Product Service Key", "code": "84111506", "description": "Servicios de consultoría de negocios y administración corporativa"},
        {"doctype": "MX Product Service Key", "code": "01010101", "description": "No existe en el catálogo"},
        # MX Unit Key
        {"doctype": "MX Unit Key", "code": "E48", "description": "Unidad de servicio"},
        {"doctype": "MX Unit Key", "code": "H87", "description": "Pieza"},
        {"doctype": "MX Unit Key", "code": "KGM", "description": "Kilogramo"},
        # MX CFDI Use - verify G03 exists
        {"doctype": "MX CFDI Use", "code": "G03", "description": "Gastos en general"},
        # MX Payment Method
        {"doctype": "MX Payment Method", "code": "PUE", "description": "Pago en una sola exhibición"},
        {"doctype": "MX Payment Method", "code": "PPD", "description": "Pago en parcialidades o diferido"},
        # MX Payment Form
        {"doctype": "MX Payment Form", "code": "01", "description": "Efectivo"},
        {"doctype": "MX Payment Form", "code": "03", "description": "Transferencia electrónica de fondos"},
        {"doctype": "MX Payment Form", "code": "99", "description": "Por definir"},
        # MX Export Type
        {"doctype": "MX Export Type", "code": "01", "description": "No aplica"},
        # MX Cancellation Reason
        {"doctype": "MX Cancellation Reason", "code": "01", "description": "Comprobante emitido con errores con relación"},
        {"doctype": "MX Cancellation Reason", "code": "02", "description": "Comprobante emitido con errores sin relación"},
        # MX Tax Object
        {"doctype": "MX Tax Object", "code": "02", "description": "Sí objeto del impuesto"},
        # MX Fiscal Regime — common ones for testing
        {"doctype": "MX Fiscal Regime", "code": "601", "description": "General de Ley Personas Morales"},
        {"doctype": "MX Fiscal Regime", "code": "616", "description": "Sin obligaciones fiscales"},
    ]

    created = 0
    skipped = 0
    for rec in records:
        dt = rec["doctype"]
        code = rec["code"]
        # Check by code field — name might be different
        if frappe.db.exists(dt, {"code": code}):
            skipped += 1
            continue
        # Also check if name IS code
        if frappe.db.exists(dt, code):
            skipped += 1
            continue
        try:
            doc = frappe.get_doc(rec)
            doc.flags.ignore_permissions = True
            doc.flags.ignore_mandatory = True
            doc.insert()
            created += 1
        except frappe.DuplicateEntryError:
            skipped += 1
        except Exception as e:
            print(f"ERROR: {dt} {code}: {e}")

    frappe.db.commit()
    print(f"Catalog records: {created} created, {skipped} skipped (already exist)")
