"""Debug: Generate XML and show it before sending to PAC."""
import frappe
from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice, sign_cfdi


def run():
    print("=== Debug XML Generation ===\n")

    income_account = frappe.db.get_value("Account", {
        "company": "MD Consultoria TI", "root_type": "Income", "is_group": 0}, "name")

    si = frappe.get_doc({
        "doctype": "Sales Invoice",
        "company": "MD Consultoria TI",
        "customer": "Cliente Prueba MX",
        "posting_date": "2026-03-19",
        "due_date": "2026-04-19",
        "currency": "MXN",
        "conversion_rate": 1.0,
        "selling_price_list": "Standard Selling",
        "mx_uso_cfdi": "G03",
        "mx_metodo_pago": "PUE",
        "mx_forma_pago": "03",
        "mx_exportacion": "01",
        "items": [{"item_code": "Servicio Consultoria MX", "qty": 1,
                    "rate": 10000.00, "income_account": income_account}],
    })
    si.flags.ignore_permissions = True
    si.flags.ignore_mandatory = True
    si.insert()
    frappe.db.commit()
    print(f"Invoice: {si.name}")

    # Build XML
    try:
        comprobante = build_cfdi_from_sales_invoice(si)
        print(f"\nXML built successfully")
        print(f"Type: {type(comprobante)}")

        # Sign
        signed = sign_cfdi(comprobante, si.company)
        print(f"XML signed successfully")

        # Get XML string
        if hasattr(signed, 'xml_bytes'):
            xml_str = signed.xml_bytes().decode('utf-8')
        elif hasattr(signed, 'to_xml'):
            xml_str = signed.to_xml()
        elif hasattr(signed, '__str__'):
            xml_str = str(signed)
        else:
            xml_str = repr(signed)

        print(f"\n=== XML Content (first 2000 chars) ===")
        print(xml_str[:2000])

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
