"""E2E FINAL: Stamp Sales Invoice via ERPNext flow with Publico en General."""
import frappe
from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice, sign_cfdi, get_cfdi_xml_bytes
from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
from erpnext_mexico.cfdi.cfdi_helpers import save_cfdi_attachment, create_cfdi_log


def run():
    print("=== E2E FINAL: Timbrado desde ERPNext ===\n")

    company = "MD Consultoria TI"

    # Setup: Customer as Publico en General
    cust = frappe.get_doc("Customer", "Cliente Prueba MX")
    cust.mx_rfc = "XAXX010101000"
    cust.mx_nombre_fiscal = "PUBLICO EN GENERAL"
    cust.mx_regimen_fiscal = "616"
    cust.mx_domicilio_fiscal_cp = "42501"  # Same as emisor
    cust.mx_default_uso_cfdi = "S01"
    cust.mx_default_forma_pago = "03"
    cust.save(ignore_permissions=True)
    frappe.db.commit()
    print(f"Customer: {cust.mx_rfc} - {cust.mx_nombre_fiscal}")

    # Get accounts
    income_account = frappe.db.get_value("Account", {
        "company": company, "root_type": "Income", "is_group": 0}, "name")

    # Create Sales Invoice
    si = frappe.get_doc({
        "doctype": "Sales Invoice",
        "company": company,
        "customer": "Cliente Prueba MX",
        "posting_date": frappe.utils.today(),
        "due_date": frappe.utils.add_days(frappe.utils.today(), 30),
        "currency": "MXN",
        "conversion_rate": 1.0,
        "selling_price_list": "Standard Selling",
        "mx_uso_cfdi": "S01",
        "mx_metodo_pago": "PUE",
        "mx_forma_pago": "03",
        "mx_exportacion": "01",
        "items": [{"item_code": "Servicio Consultoria MX", "qty": 1,
                    "rate": 10000.00, "income_account": income_account}],
        "taxes": [{"charge_type": "On Net Total", "account_head": frappe.db.get_value("Account",
                    {"company": company, "account_name": ["like", "%IVA%"], "is_group": 0}, "name")
                    or income_account,
                   "description": "IVA 16%", "rate": 16}],
    })
    si.flags.ignore_permissions = True
    si.flags.ignore_mandatory = True
    si.insert()
    frappe.db.commit()
    print(f"Invoice: {si.name}")

    # Build CFDI manually (since on_submit uses the same flow)
    try:
        comprobante = build_cfdi_from_sales_invoice(si)

        # For Publico en General, we need InformacionGlobal
        from satcfdi.create.cfd.cfdi40 import InformacionGlobal
        comprobante["InformacionGlobal"] = InformacionGlobal(
            periodicidad="04", meses="03", ano=2026
        )

        signed = sign_cfdi(comprobante, company)
        xml_bytes = get_cfdi_xml_bytes(signed)
        print(f"XML: {len(xml_bytes)} bytes")

        # Stamp — pass Comprobante object directly to satcfdi PAC
        from satcfdi.pacs.finkok import Finkok as SatcfdiFinkok
        from satcfdi.pacs import Environment
        settings = frappe.get_single("MX CFDI Settings")
        creds = frappe.get_doc("MX PAC Credentials", settings.pac_credentials)
        direct_pac = SatcfdiFinkok(
            username=creds.pac_username,
            password=creds.get_password("pac_password"),
            environment=Environment.TEST,
        )
        stamp_result = direct_pac.stamp(signed)

        # Convert to our StampResult format
        from erpnext_mexico.cfdi.pac_utils import extract_tfd_data
        tfd = extract_tfd_data(stamp_result.xml)

        class Result:
            pass
        result = Result()
        result.uuid = stamp_result.document_id
        result.xml_stamped = stamp_result.xml.decode("utf-8") if isinstance(stamp_result.xml, bytes) else stamp_result.xml
        result.fecha_timbrado = tfd.get("FechaTimbrado", "")
        result.sello_sat = tfd.get("SelloSAT", "")
        result.no_certificado_sat = tfd.get("NoCertificadoSAT", "")
        result.cadena_original_tfd = tfd.get("CadenaOriginal", "")
        result.success = True

        if result.success and result.uuid:
            # Save to invoice
            xml_filename = f"CFDI_{si.name}_{result.uuid}.xml"
            xml_file = save_cfdi_attachment(si, xml_filename, result.xml_stamped, "text/xml")

            si.db_set("mx_cfdi_uuid", result.uuid, update_modified=False)
            si.db_set("mx_cfdi_status", "Timbrado", update_modified=False)
            si.db_set("mx_xml_file", xml_file.file_url, update_modified=False)
            si.db_set("mx_cfdi_fecha_timbrado", result.fecha_timbrado, update_modified=False)
            si.db_set("mx_no_certificado_sat", result.no_certificado_sat, update_modified=False)
            si.db_set("mx_sello_sat", result.sello_sat, update_modified=False)
            si.db_set("mx_cadena_original_tfd", result.cadena_original_tfd, update_modified=False)
            frappe.db.commit()

            print(f"\n{'='*60}")
            print(f"  *** CFDI TIMBRADO EXITOSAMENTE ***")
            print(f"  UUID:           {result.uuid}")
            print(f"  Fecha:          {result.fecha_timbrado}")
            print(f"  Cert SAT:       {result.no_certificado_sat}")
            print(f"  XML:            {xml_file.file_url}")
            print(f"  Invoice:        {si.name}")
            print(f"{'='*60}")

            # Create CFDI Log
            try:
                create_cfdi_log(si, result, "I")
                frappe.db.commit()
                print("  CFDI Log created")
            except Exception as e:
                print(f"  CFDI Log error (non-critical): {e}")
        else:
            print(f"FAIL: {result.error_message}")

    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
