"""E2E: Try stamping with different receptor RFC (not same as emisor)."""
import frappe
from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice, sign_cfdi, get_cfdi_xml_bytes
from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher


def run():
    print("=== E2E: Different receptor RFCs ===\n")

    # Test with several known test RFCs as receptor
    test_receptors = [
        ("IIA040805DZ4", "INDISTRIA ILUMINADORA DE ALMACENES", "601", "62661"),
        ("URE180429TM6", "UNIVERSIDAD ROBOTICA ESPAÑOLA", "601", "86991"),
        ("XIA190128J61", "XENON INDUSTRIAL ARTICLES", "601", "76343"),
    ]

    income_account = frappe.db.get_value("Account", {
        "company": "MD Consultoria TI", "root_type": "Income", "is_group": 0}, "name")

    # Reset company CP to 42501
    company = frappe.get_doc("Company", "MD Consultoria TI")
    if not frappe.db.exists("MX Postal Code", "42501"):
        frappe.get_doc({"doctype": "MX Postal Code", "code": "42501", "description": "Test"}).insert(ignore_permissions=True)
    company.mx_lugar_expedicion = "42501"
    company.save(ignore_permissions=True)
    frappe.db.commit()

    pac = PACDispatcher.get_pac("MD Consultoria TI")

    for rfc, nombre, regimen, cp in test_receptors:
        # Ensure CP exists
        if not frappe.db.exists("MX Postal Code", cp):
            frappe.get_doc({"doctype": "MX Postal Code", "code": cp, "description": f"Test {cp}"}).insert(ignore_permissions=True)
            frappe.db.commit()

        # Update customer
        cust = frappe.get_doc("Customer", "Cliente Prueba MX")
        cust.mx_rfc = rfc
        cust.mx_nombre_fiscal = nombre
        cust.mx_regimen_fiscal = regimen
        cust.mx_domicilio_fiscal_cp = cp
        cust.save(ignore_permissions=True)
        frappe.db.commit()

        # Create invoice
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

        try:
            comprobante = build_cfdi_from_sales_invoice(si)
            signed = sign_cfdi(comprobante, si.company)
            xml_bytes = get_cfdi_xml_bytes(signed)
            result = pac.stamp(xml_bytes.decode("utf-8"))

            if result.success and result.uuid:
                print(f"RFC {rfc} CP {cp}: *** SUCCESS *** UUID={result.uuid}")
                si.db_set("mx_cfdi_uuid", result.uuid)
                si.db_set("mx_cfdi_status", "Timbrado")
                frappe.db.commit()
                print(f"\n*** PRIMER CFDI TIMBRADO EXITOSAMENTE ***")
                return
            else:
                error_short = (result.error_message or "Unknown")[:100]
                print(f"RFC {rfc} CP {cp}: FAIL — {error_short}")

        except Exception as e:
            print(f"RFC {rfc} CP {cp}: ERROR — {str(e)[:100]}")

    print("\nNone worked. The SAT test environment may have different CPs than documented.")
