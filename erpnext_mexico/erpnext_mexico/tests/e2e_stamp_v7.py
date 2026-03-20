"""E2E v7: Fix nombre fiscal to 'ESCUELA KEMPER URGATE SA DE CV' (Finkok panel value)."""
import frappe
from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice, sign_cfdi, get_cfdi_xml_bytes
from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher


def run():
    print("=== E2E v7: Nombre con SA DE CV ===\n")

    # Fix Company — nombre completo como en panel Finkok
    company = frappe.get_doc("Company", "MD Consultoria TI")
    company.mx_nombre_fiscal = "ESCUELA KEMPER URGATE SA DE CV"
    company.mx_lugar_expedicion = "42501"
    company.save(ignore_permissions=True)

    # Fix Customer — same
    cust = frappe.get_doc("Customer", "Cliente Prueba MX")
    cust.mx_rfc = "EKU9003173C9"
    cust.mx_nombre_fiscal = "ESCUELA KEMPER URGATE SA DE CV"
    cust.mx_regimen_fiscal = "601"
    cust.mx_domicilio_fiscal_cp = "42501"
    cust.save(ignore_permissions=True)
    frappe.db.commit()

    print(f"Emisor: {company.mx_nombre_fiscal} CP={company.mx_lugar_expedicion}")
    print(f"Receptor: {cust.mx_nombre_fiscal} CP={cust.mx_domicilio_fiscal_cp}")

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

    try:
        comprobante = build_cfdi_from_sales_invoice(si)
        signed = sign_cfdi(comprobante, si.company)
        xml_bytes = get_cfdi_xml_bytes(signed)

        # Show Receptor node from XML
        import re
        xml_str = xml_bytes.decode("utf-8")
        receptor = re.search(r'<cfdi:Receptor[^/]*/>', xml_str)
        print(f"XML Receptor: {receptor.group() if receptor else 'NOT FOUND'}")

        pac = PACDispatcher.get_pac(si.company)
        result = pac.stamp(xml_str)

        if result.success and result.uuid:
            print(f"\n{'='*60}")
            print(f"  *** CFDI TIMBRADO EXITOSAMENTE ***")
            print(f"  UUID: {result.uuid}")
            print(f"  Fecha: {result.fecha_timbrado}")
            print(f"  Cert SAT: {result.no_certificado_sat}")
            print(f"{'='*60}")

            si.db_set("mx_cfdi_uuid", result.uuid)
            si.db_set("mx_cfdi_status", "Timbrado")
            frappe.db.commit()
        else:
            print(f"\nFAIL: {result.error_message}")
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
