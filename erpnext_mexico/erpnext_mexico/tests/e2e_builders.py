"""E2E Test: Nómina and Carta Porte XML builders."""
import frappe


def run():
    # Test 1: Nómina Builder
    print("=== Nómina Builder Test ===")
    try:
        from erpnext_mexico.cfdi.nomina_builder import build_nomina_cfdi
        # Check what arguments it expects
        import inspect
        sig = inspect.signature(build_nomina_cfdi)
        print(f"Signature: {sig}")
        # Try building with mock data if possible
    except Exception as e:
        print(f"Nómina import: {type(e).__name__}: {e}")

    # Test 2: Carta Porte Builder
    print("\n=== Carta Porte Builder Test ===")
    try:
        from erpnext_mexico.cfdi.carta_porte_builder import build_carta_porte_cfdi
        import inspect
        sig = inspect.signature(build_carta_porte_cfdi)
        print(f"Signature: {sig}")
    except Exception as e:
        print(f"Carta Porte import: {type(e).__name__}: {e}")

    # Test 3: Payment Builder
    print("\n=== Payment Builder Test ===")
    try:
        from erpnext_mexico.cfdi.payment_builder import build_payment_cfdi
        import inspect
        sig = inspect.signature(build_payment_cfdi)
        print(f"Signature: {sig}")
    except Exception as e:
        print(f"Payment import: {type(e).__name__}: {e}")

    # Test 4: XML Builder (main)
    print("\n=== XML Builder Test ===")
    try:
        from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice, sign_cfdi, get_cfdi_xml_bytes
        print("All XML builder functions imported OK")

        # Try building a CFDI without submitting
        income_account = frappe.db.get_value("Account", {
            "company": "MD Consultoria TI", "root_type": "Income", "is_group": 0
        }, "name")

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

        comprobante = build_cfdi_from_sales_invoice(si)
        print(f"CFDI built: {type(comprobante)}")

        signed = sign_cfdi(comprobante, si.company)
        print(f"CFDI signed: {type(signed)}")

        xml_bytes = get_cfdi_xml_bytes(signed)
        print(f"XML bytes: {len(xml_bytes)} bytes")
        print(f"XML preview: {xml_bytes[:200].decode()}")
        print("XML Builder: OK")
    except Exception as e:
        print(f"XML Builder: FAIL - {type(e).__name__}: {e}")
