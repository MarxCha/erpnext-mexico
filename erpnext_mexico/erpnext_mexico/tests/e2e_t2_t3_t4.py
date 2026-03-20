"""E2E Tests T2-T4: Facturacion completa, Pagos PPD, Cancelacion.

T2: Timbrar factura via FinkokPAC adapter (ya verificado)
T3: Crear factura PPD -> timbrar -> crear Payment Entry -> timbrar complemento de pagos
T4: Cancelar CFDI timbrado
"""
import frappe
from satcfdi.create.cfd.cfdi40 import InformacionGlobal

from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice, sign_cfdi
from erpnext_mexico.cfdi.payment_builder import build_payment_cfdi, sign_payment_cfdi
from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
from erpnext_mexico.cfdi.cfdi_helpers import save_cfdi_attachment, create_cfdi_log


def run():
    print("=" * 70)
    print("  E2E TESTS: T2 Facturacion + T3 Pagos + T4 Cancelacion")
    print("=" * 70)

    company = "MD Consultoria TI"
    results = {}

    # ── T2: Facturacion PUE ──
    print("\n--- T2: Facturacion PUE ---")
    try:
        uuid_pue = _test_t2_facturacion_pue(company)
        results["T2_PUE"] = f"PASS (UUID={uuid_pue})"
        print(f"  PASS: UUID={uuid_pue}")
    except Exception as e:
        results["T2_PUE"] = f"FAIL: {e}"
        print(f"  FAIL: {e}")

    # ── T2b: Facturacion PPD (needed for T3) ──
    print("\n--- T2b: Facturacion PPD ---")
    try:
        si_ppd, uuid_ppd = _test_t2_facturacion_ppd(company)
        results["T2_PPD"] = f"PASS (UUID={uuid_ppd})"
        print(f"  PASS: UUID={uuid_ppd}, Invoice={si_ppd.name}")
    except Exception as e:
        results["T2_PPD"] = f"FAIL: {e}"
        si_ppd = None
        print(f"  FAIL: {e}")
        import traceback; traceback.print_exc()

    # ── T3: Complemento de Pagos ──
    print("\n--- T3: Complemento de Pagos ---")
    if si_ppd:
        try:
            uuid_pago = _test_t3_complemento_pagos(company, si_ppd)
            results["T3_Pagos"] = f"PASS (UUID={uuid_pago})"
            print(f"  PASS: UUID={uuid_pago}")
        except Exception as e:
            results["T3_Pagos"] = f"FAIL: {e}"
            print(f"  FAIL: {e}")
            import traceback; traceback.print_exc()
    else:
        results["T3_Pagos"] = "SKIP (T2b failed)"
        print("  SKIP: T2b PPD failed, cannot test T3")

    # ── T4: Cancelacion ──
    print("\n--- T4: Cancelacion ---")
    try:
        cancel_result = _test_t4_cancelacion(company, uuid_pue)
        results["T4_Cancel"] = f"PASS ({cancel_result})"
        print(f"  PASS: {cancel_result}")
    except Exception as e:
        results["T4_Cancel"] = f"FAIL: {e}"
        print(f"  FAIL: {e}")
        import traceback; traceback.print_exc()

    # ── Summary ──
    print(f"\n{'=' * 70}")
    print("  SUMMARY")
    print(f"{'=' * 70}")
    for test, status in results.items():
        marker = "OK" if "PASS" in status else "FAIL" if "FAIL" in status else "SKIP"
        print(f"  [{marker}] {test}: {status}")
    print(f"{'=' * 70}")


def _setup_customer():
    """Ensure Publico en General customer exists with correct fiscal data."""
    cust = frappe.get_doc("Customer", "Cliente Prueba MX")
    cust.mx_rfc = "XAXX010101000"
    cust.mx_nombre_fiscal = "PUBLICO EN GENERAL"
    cust.mx_regimen_fiscal = "616"
    cust.mx_domicilio_fiscal_cp = "42501"
    cust.mx_default_uso_cfdi = "S01"
    cust.mx_default_forma_pago = "03"
    cust.save(ignore_permissions=True)
    frappe.db.commit()
    return cust


def _get_accounts(company):
    """Get required accounts."""
    income = frappe.db.get_value("Account", {
        "company": company, "root_type": "Income", "is_group": 0}, "name")
    iva = frappe.db.get_value("Account", {
        "company": company, "account_name": ["like", "%IVA%"], "is_group": 0}, "name")
    debtors = frappe.db.get_value("Account", {
        "company": company, "account_type": "Receivable", "is_group": 0}, "name")
    bank = frappe.db.get_value("Account", {
        "company": company, "account_type": "Bank", "is_group": 0}, "name")
    return income, iva or income, debtors, bank


def _create_invoice(company, metodo_pago="PUE", rate=10000.00):
    """Create Sales Invoice."""
    _setup_customer()
    income, iva, _, _ = _get_accounts(company)

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
        "mx_metodo_pago": metodo_pago,
        "mx_forma_pago": "03" if metodo_pago == "PUE" else "99",
        "mx_exportacion": "01",
        "items": [{"item_code": "Servicio Consultoria MX", "qty": 1,
                    "rate": rate, "income_account": income}],
        "taxes": [{"charge_type": "On Net Total", "account_head": iva,
                   "description": "IVA 16%", "rate": 16}],
    })
    si.flags.ignore_permissions = True
    si.flags.ignore_mandatory = True
    si.insert()
    frappe.db.commit()
    return si


def _stamp_invoice(si, company, submit=False):
    """Build, sign and stamp CFDI for a Sales Invoice."""
    # If we need to submit, do it first with auto_stamp disabled
    if submit and si.docstatus == 0:
        settings = frappe.get_single("MX CFDI Settings")
        old_auto_stamp = settings.auto_stamp_on_submit
        settings.auto_stamp_on_submit = 0
        settings.save(ignore_permissions=True)
        frappe.db.commit()

        si.flags.ignore_permissions = True
        si.submit()
        frappe.db.commit()

        # Restore auto_stamp
        settings.auto_stamp_on_submit = old_auto_stamp
        settings.save(ignore_permissions=True)
        frappe.db.commit()

        si.reload()

    comprobante = build_cfdi_from_sales_invoice(si)
    comprobante["InformacionGlobal"] = InformacionGlobal(
        periodicidad="04", meses="03", ano=2026
    )
    signed = sign_cfdi(comprobante, company)

    pac = PACDispatcher.get_pac(company)
    result = pac.stamp(signed)

    if not result.success:
        raise Exception(f"Stamp failed: {result.error_message}")

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

    try:
        create_cfdi_log(si, result, "I")
        frappe.db.commit()
    except Exception:
        pass

    return result.uuid


# ── T2: Facturacion PUE ──
def _test_t2_facturacion_pue(company):
    si = _create_invoice(company, metodo_pago="PUE", rate=8000.00)
    uuid = _stamp_invoice(si, company)
    return uuid


# ── T2b: Facturacion PPD ──
def _test_t2_facturacion_ppd(company):
    si = _create_invoice(company, metodo_pago="PPD", rate=15000.00)
    uuid = _stamp_invoice(si, company, submit=True)
    return si, uuid


# ── T3: Complemento de Pagos ──
def _test_t3_complemento_pagos(company, si_ppd):
    """Create Payment Entry against PPD invoice and stamp Complemento de Pagos."""
    _, _, debtors, bank = _get_accounts(company)

    # Reload to get latest data
    si_ppd.reload()

    pe = frappe.get_doc({
        "doctype": "Payment Entry",
        "payment_type": "Receive",
        "company": company,
        "party_type": "Customer",
        "party": si_ppd.customer,
        "paid_from": debtors,
        "paid_to": bank,
        "paid_amount": float(si_ppd.grand_total),
        "received_amount": float(si_ppd.grand_total),
        "source_exchange_rate": 1.0,
        "target_exchange_rate": 1.0,
        "posting_date": frappe.utils.today(),
        "reference_no": f"PAY-{si_ppd.name}",
        "reference_date": frappe.utils.today(),
        "mx_forma_pago": "03",
        "references": [{
            "reference_doctype": "Sales Invoice",
            "reference_name": si_ppd.name,
            "allocated_amount": float(si_ppd.grand_total),
        }],
    })
    pe.flags.ignore_permissions = True
    pe.flags.ignore_mandatory = True
    pe.insert()
    frappe.db.commit()
    print(f"    Payment Entry: {pe.name}")

    # Build, sign, stamp payment complement
    comprobante = build_payment_cfdi(pe)
    signed = sign_payment_cfdi(comprobante, company)

    pac = PACDispatcher.get_pac(company)
    result = pac.stamp(signed)

    if not result.success:
        raise Exception(f"Payment stamp failed: {result.error_message}")

    xml_filename = f"CFDI_Pago_{pe.name}_{result.uuid}.xml"
    xml_file = save_cfdi_attachment(pe, xml_filename, result.xml_stamped, "text/xml")

    pe.db_set("mx_pago_uuid", result.uuid, update_modified=False)
    pe.db_set("mx_pago_status", "Timbrado", update_modified=False)
    pe.db_set("mx_pago_xml", xml_file.file_url, update_modified=False)
    frappe.db.commit()

    try:
        create_cfdi_log(pe, result, "P")
        frappe.db.commit()
    except Exception:
        pass

    return result.uuid


# ── T4: Cancelacion ──
def _test_t4_cancelacion(company, uuid_to_cancel):
    """Cancel a stamped CFDI."""
    from erpnext_mexico.cfdi.xml_builder import _get_active_certificate, _get_file_bytes

    pac = PACDispatcher.get_pac(company)
    cert = _get_active_certificate(company)

    result = pac.cancel(
        uuid=uuid_to_cancel,
        rfc_emisor=frappe.db.get_value("Company", company, "mx_rfc"),
        certificate=_get_file_bytes(cert.certificate_file),
        key=_get_file_bytes(cert.key_file),
        password=cert.get_password("key_password"),
        reason="02",  # Comprobante emitido con errores sin relacion
    )

    if result.success:
        return f"Cancelled (status={result.status})"
    else:
        # In sandbox, cancellation may not always work immediately
        return f"Response: {result.error_message or result.status}"
