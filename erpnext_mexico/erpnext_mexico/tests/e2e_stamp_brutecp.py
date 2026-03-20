"""Try multiple CPs to find the one SAT accepts for EKU9003173C9."""
import frappe
from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice, sign_cfdi
from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher


def run():
    print("=== Brute-force CP for EKU9003173C9 ===\n")

    # Common test CPs reported in various sources
    test_cps = ["42501", "26015", "06000", "21000", "20000", "06300", "44100", "64000", "83000"]

    income_account = frappe.db.get_value("Account", {
        "company": "MD Consultoria TI", "root_type": "Income", "is_group": 0}, "name")

    pac = PACDispatcher.get_pac("MD Consultoria TI")

    for cp in test_cps:
        # Ensure CP exists
        if not frappe.db.exists("MX Postal Code", cp):
            frappe.get_doc({"doctype": "MX Postal Code", "code": cp, "description": f"Test {cp}"}).insert(ignore_permissions=True)
            frappe.db.commit()

        # Update company and customer
        company = frappe.get_doc("Company", "MD Consultoria TI")
        company.mx_lugar_expedicion = cp
        company.save(ignore_permissions=True)

        cust = frappe.get_doc("Customer", "Cliente Prueba MX")
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

        # Build and sign XML
        try:
            comprobante = build_cfdi_from_sales_invoice(si)
            signed = sign_cfdi(comprobante, si.company)

            # Send to PAC
            result = pac.stamp(signed)

            if result.uuid:
                print(f"CP {cp}: *** SUCCESS *** UUID={result.uuid}")
                # Save the result
                si.db_set("mx_cfdi_uuid", result.uuid)
                si.db_set("mx_cfdi_status", "Timbrado")
                frappe.db.commit()
                return  # Found it!
            else:
                error_short = (result.error_message or "Unknown")[:80]
                print(f"CP {cp}: FAIL — {error_short}")

        except Exception as e:
            error_str = str(e)[:80]
            print(f"CP {cp}: ERROR — {error_str}")

    print("\nNo CP worked. May need to check Finkok panel 'Preferencias Fiscales'.")
