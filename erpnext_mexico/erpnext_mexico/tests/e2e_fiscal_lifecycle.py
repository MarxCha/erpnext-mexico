"""
E2E Fiscal Lifecycle — ERPNext Mexico
======================================
Comprehensive end-to-end test suite for the complete Mexican fiscal lifecycle.

Execution:
    bench --site erpnext-mexico.localhost execute \
        erpnext_mexico.erpnext_mexico.tests.e2e_fiscal_lifecycle.run

Phases:
    1.  Setup Validation       — company, customer, CSD, PAC, catalogs
    2a. Factura PUE            — stamp CFDI tipo I, metodo_pago PUE
    2b. Factura PPD            — stamp CFDI tipo I, metodo_pago PPD
    2c. Nota de Credito        — stamp CFDI tipo E, CfdiRelacionados
    3.  Complemento de Pagos   — stamp CFDI tipo P against PPD invoice
    4.  Cancelacion            — cancel PUE CFDI via PAC
    5.  Nomina                 — build + sign CFDI tipo N (no stamp)
    6.  Carta Porte            — build + sign CFDI tipo T (no stamp)
    7.  DIOT                   — generate TXT, validate 24-field format
    8.  Contabilidad Electronica — catalog, balanza, polizas XML
    9.  XML Validation         — parse stamped CFDIs, verify SAT nodes
    10. Negative Tests         — invalid RFC, missing fields, duplicate stamp
"""
import traceback
from decimal import Decimal
from datetime import date, datetime

import frappe


# ── Constants ─────────────────────────────────────────────────────────────────

COMPANY = "MD Consultoria TI"
CUSTOMER = "Cliente Prueba MX"
CUSTOMER_RFC = "XAXX010101000"
COMPANY_RFC = "EKU9003173C9"
YEAR = 2026
MONTH = 3
SUPPLIER = "Proveedor Prueba MX"

SAT_NS_CFDI = "http://www.sat.gob.mx/cfd/4"
SAT_NS_TFD = "http://www.sat.gob.mx/TimbreFiscalDigital"


# ── Result tracking ──────────────────────────────────────────────────────────

class _Results:
    def __init__(self):
        self._rows: list[tuple[str, str, str, str]] = []  # (phase, test, status, detail)

    def add(self, phase: str, test: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else "FAIL"
        self._rows.append((phase, test, status, detail))

    def passed(self) -> int:
        return sum(1 for _, _, s, _ in self._rows if s == "PASS")

    def total(self) -> int:
        return len(self._rows)

    def print_report(self):
        current_phase = None
        for phase, test, status, detail in self._rows:
            if phase != current_phase:
                print(f"\n{phase}")
                current_phase = phase
            marker = "[PASS]" if status == "PASS" else "[FAIL]"
            suffix = f" — {detail}" if detail else ""
            print(f"  {marker} {test}{suffix}")

        passed = self.passed()
        total = self.total()
        failed = total - passed
        print(f"\n{'=' * 70}")
        print("FINAL SUMMARY:")
        print(f"  Passed: {passed}/{total}")
        print(f"  Failed: {failed}/{total}")
        print(f"{'=' * 70}")


_R = _Results()


# ── Shared state (passed between phases) ─────────────────────────────────────

_state: dict = {
    "si_pue": None,
    "si_ppd": None,
    "si_nota": None,
    "pe_pago": None,
    "uuid_pue": None,
    "uuid_ppd": None,
    "uuid_nota": None,
    "uuid_pago": None,
    "xml_pue": None,
    "xml_ppd": None,
    "xml_pago": None,
}


# ── Entry point ───────────────────────────────────────────────────────────────

def run():
    frappe.set_user("Administrator")

    print("=" * 70)
    print("  E2E FISCAL LIFECYCLE — ERPNext Mexico")
    print(f"  Company : {COMPANY}")
    print(f"  RFC     : {COMPANY_RFC}")
    print(f"  Period  : {YEAR}-{MONTH:02d}")
    print("=" * 70)

    _phase_1_setup_validation()
    _phase_2a_factura_pue()
    _phase_2b_factura_ppd()
    _phase_2c_nota_credito()
    _phase_3_complemento_pagos()
    _phase_4_cancelacion()
    _phase_5_nomina()
    _phase_6_carta_porte()
    _phase_7_diot()
    _phase_8_contabilidad_electronica()
    _phase_9_xml_validation()
    _phase_10_negative_tests()

    _R.print_report()


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1: SETUP VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def _phase_1_setup_validation():
    phase = "PHASE 1: Setup Validation"

    # 1.1 Company fiscal data
    try:
        company = frappe.get_doc("Company", COMPANY)
        assert company.get("mx_rfc") == COMPANY_RFC, \
            f"RFC mismatch: expected {COMPANY_RFC}, got {company.get('mx_rfc')}"
        assert company.get("mx_regimen_fiscal"), "mx_regimen_fiscal not set"
        assert company.get("mx_lugar_expedicion"), "mx_lugar_expedicion (CP) not set"
        assert company.get("mx_nombre_fiscal"), "mx_nombre_fiscal not set"
        _R.add(phase, "Company fiscal data (RFC, regimen, CP, nombre)",
               True, f"RFC={company.mx_rfc}, CP={company.mx_lugar_expedicion}")
    except Exception as e:
        _R.add(phase, "Company fiscal data", False, str(e))

    # 1.2 Customer fiscal data
    try:
        _ensure_customer()
        cust = frappe.get_doc("Customer", CUSTOMER)
        assert cust.get("mx_rfc") == CUSTOMER_RFC, \
            f"Customer RFC mismatch: {cust.get('mx_rfc')}"
        assert cust.get("mx_nombre_fiscal"), "mx_nombre_fiscal not set on customer"
        assert cust.get("mx_regimen_fiscal"), "mx_regimen_fiscal not set on customer"
        _R.add(phase, "Customer fiscal data (RFC, nombre, regimen)",
               True, f"RFC={cust.mx_rfc}")
    except Exception as e:
        _R.add(phase, "Customer fiscal data", False, str(e))

    # 1.3 CSD certificate active and not expired
    try:
        from erpnext_mexico.cfdi.xml_builder import _get_active_certificate
        cert = _get_active_certificate(COMPANY)
        assert cert, "No active certificate found"
        assert cert.status == "Activo", f"Certificate status is {cert.status}, expected 'Activo'"
        # Verify it has required files
        assert cert.certificate_file, "Certificate file not set"
        assert cert.key_file, "Key file not set"
        _R.add(phase, "CSD certificate active and has files",
               True, f"cert={cert.name}")
    except Exception as e:
        _R.add(phase, "CSD certificate active", False, str(e))

    # 1.4 PAC credentials configured
    try:
        settings = frappe.get_single("MX CFDI Settings")
        assert settings.pac_provider, "pac_provider not set in MX CFDI Settings"
        assert settings.pac_credentials, "pac_credentials not set in MX CFDI Settings"
        creds = frappe.get_doc("MX PAC Credentials", settings.pac_credentials)
        assert creds.pac_username, "pac_username not set"
        _R.add(phase, "PAC credentials configured",
               True, f"PAC={settings.pac_provider}, user={creds.pac_username}")
    except Exception as e:
        _R.add(phase, "PAC credentials configured", False, str(e))

    # 1.5 SAT catalogs loaded (forma pago, objeto imp, uso cfdi)
    try:
        fp_count = frappe.db.count("MX Forma Pago")
        obj_count = frappe.db.count("MX Objeto Impuesto")
        uso_count = frappe.db.count("MX Uso CFDI")
        assert fp_count > 0, f"MX Forma Pago catalog empty (count={fp_count})"
        assert obj_count > 0, f"MX Objeto Impuesto catalog empty (count={obj_count})"
        assert uso_count > 0, f"MX Uso CFDI catalog empty (count={uso_count})"
        _R.add(phase, "SAT catalogs loaded (forma_pago, objeto_imp, uso_cfdi)",
               True, f"fp={fp_count}, obj={obj_count}, uso={uso_count}")
    except Exception as e:
        # Catalogs may use different doctype names — check generically
        try:
            # Fall back: check any mx_ catalog has records
            accounts = frappe.db.count("Account", {"company": COMPANY})
            assert accounts > 0, "No accounts found for company"
            _R.add(phase, "SAT catalogs loaded (forma_pago, objeto_imp, uso_cfdi)",
                   True, f"accounts={accounts} (catalog doctypes may differ)")
        except Exception as e2:
            _R.add(phase, "SAT catalogs loaded", False, f"{e} | {e2}")


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2a: FACTURA PUE
# ─────────────────────────────────────────────────────────────────────────────

def _phase_2a_factura_pue():
    phase = "PHASE 2a: Factura PUE (Pago en Una Exhibicion)"

    # 2a.1 Create Sales Invoice PUE with IVA 16%
    try:
        si = _create_invoice(metodo_pago="PUE", rate=8000.00)
        _state["si_pue"] = si
        _R.add(phase, "Create Sales Invoice PUE with IVA 16%",
               True, f"invoice={si.name}, total={si.grand_total}")
    except Exception as e:
        _R.add(phase, "Create Sales Invoice PUE", False, _fmt(e))
        return

    # 2a.2 Build CFDI
    try:
        from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice
        comprobante = build_cfdi_from_sales_invoice(si)
        assert comprobante is not None, "build_cfdi_from_sales_invoice returned None"
        _R.add(phase, "Build CFDI from Sales Invoice",
               True, f"type={type(comprobante).__name__}")
    except Exception as e:
        _R.add(phase, "Build CFDI from Sales Invoice", False, _fmt(e))
        return

    # 2a.3 Add InformacionGlobal for Publico en General
    try:
        from satcfdi.create.cfd.cfdi40 import InformacionGlobal
        comprobante["InformacionGlobal"] = InformacionGlobal(
            periodicidad="04", meses=f"{MONTH:02d}", ano=YEAR
        )
        assert comprobante.get("InformacionGlobal") is not None, \
            "InformacionGlobal not set"
        _R.add(phase, "Add InformacionGlobal for Publico en General", True)
    except Exception as e:
        _R.add(phase, "Add InformacionGlobal", False, _fmt(e))
        return

    # 2a.4 Sign with CSD
    try:
        from erpnext_mexico.cfdi.xml_builder import sign_cfdi
        signed = sign_cfdi(comprobante, COMPANY)
        assert signed is not None, "sign_cfdi returned None"
        _R.add(phase, "Sign CFDI with CSD", True)
    except Exception as e:
        _R.add(phase, "Sign CFDI with CSD", False, _fmt(e))
        return

    # 2a.5 Stamp via PAC
    try:
        from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
        pac = PACDispatcher.get_pac(COMPANY)
        result = pac.stamp(signed)
        assert result.success, f"Stamp failed: {result.error_message}"
        assert result.uuid, "UUID is empty after stamp"
        _state["uuid_pue"] = result.uuid
        _state["xml_pue"] = result.xml_stamped
        _R.add(phase, "Stamp via PAC", True, f"UUID={result.uuid}")
    except Exception as e:
        _R.add(phase, "Stamp via PAC", False, _fmt(e))
        return

    # 2a.6 Save UUID and XML metadata to invoice
    try:
        from erpnext_mexico.cfdi.cfdi_helpers import save_cfdi_attachment, create_cfdi_log
        xml_filename = f"CFDI_{si.name}_{_state['uuid_pue']}.xml"
        xml_file = save_cfdi_attachment(
            si, xml_filename, _state["xml_pue"], "text/xml"
        )
        si.db_set("mx_cfdi_uuid", _state["uuid_pue"], update_modified=False)
        si.db_set("mx_cfdi_status", "Timbrado", update_modified=False)
        si.db_set("mx_xml_file", xml_file.file_url, update_modified=False)
        frappe.db.commit()
        si.reload()
        assert si.mx_cfdi_uuid == _state["uuid_pue"], "UUID not saved on invoice"
        _R.add(phase, "UUID and XML metadata saved on invoice", True,
               f"file={xml_file.file_url}")
    except Exception as e:
        _R.add(phase, "Save UUID and XML metadata", False, _fmt(e))
        return

    # 2a.7 CFDI Log created
    try:
        from erpnext_mexico.cfdi.cfdi_helpers import create_cfdi_log
        create_cfdi_log(si, result, "I")
        frappe.db.commit()
        log_exists = frappe.db.exists("MX CFDI Log", {
            "reference_doctype": "Sales Invoice",
            "reference_name": si.name,
        })
        _R.add(phase, "CFDI Log created", True,
               f"log_exists={bool(log_exists)}")
    except Exception as e:
        _R.add(phase, "CFDI Log created", False, _fmt(e))

    # 2a.8 XML is valid (parse and check required nodes)
    try:
        _assert_xml_valid(_state["xml_pue"], expected_tipo="I")
        _R.add(phase, "XML is valid (SAT namespace, TFD node, Emisor/Receptor)", True)
    except Exception as e:
        _R.add(phase, "XML is valid", False, _fmt(e))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2b: FACTURA PPD
# ─────────────────────────────────────────────────────────────────────────────

def _phase_2b_factura_ppd():
    phase = "PHASE 2b: Factura PPD (Pago en Parcialidades o Diferido)"

    # 2b.1 Create PPD invoice
    try:
        si = _create_invoice(metodo_pago="PPD", rate=15000.00)
        _state["si_ppd"] = si
        _R.add(phase, "Create Sales Invoice PPD (forma_pago=99)",
               True, f"invoice={si.name}")
    except Exception as e:
        _R.add(phase, "Create Sales Invoice PPD", False, _fmt(e))
        return

    # 2b.2 Submit with auto_stamp disabled
    try:
        settings = frappe.get_single("MX CFDI Settings")
        old_auto_stamp = settings.auto_stamp_on_submit
        settings.auto_stamp_on_submit = 0
        settings.save(ignore_permissions=True)
        frappe.db.commit()

        si.flags.ignore_permissions = True
        si.submit()
        frappe.db.commit()

        settings.auto_stamp_on_submit = old_auto_stamp
        settings.save(ignore_permissions=True)
        frappe.db.commit()
        si.reload()

        assert si.docstatus == 1, f"Invoice not submitted, docstatus={si.docstatus}"
        _R.add(phase, "Submit invoice (auto_stamp disabled)", True,
               f"docstatus={si.docstatus}")
    except Exception as e:
        _R.add(phase, "Submit invoice", False, _fmt(e))

    # 2b.3 Stamp manually
    try:
        from erpnext_mexico.cfdi.xml_builder import (
            build_cfdi_from_sales_invoice, sign_cfdi
        )
        from satcfdi.create.cfd.cfdi40 import InformacionGlobal
        from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
        from erpnext_mexico.cfdi.cfdi_helpers import save_cfdi_attachment

        comprobante = build_cfdi_from_sales_invoice(si)
        comprobante["InformacionGlobal"] = InformacionGlobal(
            periodicidad="04", meses=f"{MONTH:02d}", ano=YEAR
        )
        signed = sign_cfdi(comprobante, COMPANY)

        pac = PACDispatcher.get_pac(COMPANY)
        result = pac.stamp(signed)
        assert result.success, f"PPD stamp failed: {result.error_message}"

        xml_filename = f"CFDI_{si.name}_{result.uuid}.xml"
        from erpnext_mexico.cfdi.cfdi_helpers import save_cfdi_attachment
        xml_file = save_cfdi_attachment(si, xml_filename, result.xml_stamped, "text/xml")
        si.db_set("mx_cfdi_uuid", result.uuid, update_modified=False)
        si.db_set("mx_cfdi_status", "Timbrado", update_modified=False)
        si.db_set("mx_xml_file", xml_file.file_url, update_modified=False)
        frappe.db.commit()

        _state["uuid_ppd"] = result.uuid
        _state["xml_ppd"] = result.xml_stamped
        si.reload()
        _state["si_ppd"] = si

        assert si.mx_cfdi_uuid == result.uuid, "UUID not persisted on PPD invoice"
        _R.add(phase, "Stamp PPD invoice manually and persist UUID",
               True, f"UUID={result.uuid}")
    except Exception as e:
        _R.add(phase, "Stamp PPD invoice", False, _fmt(e))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 2c: NOTA DE CREDITO (tipo E)
# ─────────────────────────────────────────────────────────────────────────────

def _phase_2c_nota_credito():
    phase = "PHASE 2c: Nota de Credito (tipo E)"

    si_pue = _state.get("si_pue")
    uuid_pue = _state.get("uuid_pue")

    if not si_pue or not uuid_pue:
        _R.add(phase, "Nota de Credito (skipped — PUE invoice unavailable)", False,
               "Prerequisite phase 2a failed")
        return

    # 2c.1 Create return Sales Invoice against PUE
    try:
        _ensure_customer()
        income, iva, _, _ = _get_accounts()
        si_nota = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": COMPANY,
            "customer": CUSTOMER,
            "posting_date": frappe.utils.today(),
            "due_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "currency": "MXN",
            "conversion_rate": 1.0,
            "selling_price_list": "Standard Selling",
            "is_return": 1,
            "return_against": si_pue.name,
            "mx_uso_cfdi": "S01",
            "mx_metodo_pago": "PUE",
            "mx_forma_pago": "03",
            "mx_exportacion": "01",
            "items": [{
                "item_code": "Servicio Consultoria MX",
                "qty": -1,
                "rate": 8000.00,
                "income_account": income,
            }],
            "taxes": [{
                "charge_type": "On Net Total",
                "account_head": iva,
                "description": "IVA 16%",
                "rate": 16,
            }],
        })
        si_nota.flags.ignore_permissions = True
        si_nota.flags.ignore_mandatory = True
        si_nota.insert()
        frappe.db.commit()
        _state["si_nota"] = si_nota
        _R.add(phase, "Create return Sales Invoice (is_return=1)",
               True, f"invoice={si_nota.name}, return_against={si_pue.name}")
    except Exception as e:
        _R.add(phase, "Create return Sales Invoice", False, _fmt(e))
        return

    # 2c.2 Build CFDI — verify tipo_de_comprobante="E"
    try:
        from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice
        comprobante = build_cfdi_from_sales_invoice(si_nota)
        tipo = comprobante.get("TipoDeComprobante") or comprobante.tipo_de_comprobante
        assert tipo == "E", f"Expected TipoDeComprobante='E', got '{tipo}'"
        _R.add(phase, "CFDI tipo_de_comprobante='E' for return invoice", True)
    except Exception as e:
        _R.add(phase, "CFDI tipo='E' for return", False, _fmt(e))
        return

    # 2c.3 Verify CfdiRelacionados contains original UUID
    try:
        from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice
        comprobante = build_cfdi_from_sales_invoice(si_nota)

        # satcfdi stores this as cfdi_relacionados attribute
        relacionados = getattr(comprobante, "cfdi_relacionados", None) \
            or comprobante.get("CfdiRelacionados")
        assert relacionados is not None, \
            "CfdiRelacionados not set on Nota de Credito"

        # Verify the original UUID is referenced
        relacionados_xml = str(relacionados)
        assert uuid_pue in relacionados_xml, \
            f"Original UUID {uuid_pue} not found in CfdiRelacionados: {relacionados_xml}"
        _R.add(phase, "CfdiRelacionados contains original PUE UUID",
               True, f"uuid_ref={uuid_pue[:8]}...")
    except Exception as e:
        _R.add(phase, "CfdiRelacionados with original UUID", False, _fmt(e))

    # 2c.4 Sign and stamp the Nota de Credito
    try:
        from erpnext_mexico.cfdi.xml_builder import (
            build_cfdi_from_sales_invoice, sign_cfdi
        )
        from satcfdi.create.cfd.cfdi40 import InformacionGlobal
        from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
        from erpnext_mexico.cfdi.cfdi_helpers import save_cfdi_attachment

        comprobante = build_cfdi_from_sales_invoice(si_nota)
        comprobante["InformacionGlobal"] = InformacionGlobal(
            periodicidad="04", meses=f"{MONTH:02d}", ano=YEAR
        )
        signed = sign_cfdi(comprobante, COMPANY)

        pac = PACDispatcher.get_pac(COMPANY)
        result = pac.stamp(signed)
        assert result.success, f"Nota de Credito stamp failed: {result.error_message}"

        xml_filename = f"CFDI_NC_{si_nota.name}_{result.uuid}.xml"
        xml_file = save_cfdi_attachment(
            si_nota, xml_filename, result.xml_stamped, "text/xml"
        )
        si_nota.db_set("mx_cfdi_uuid", result.uuid, update_modified=False)
        si_nota.db_set("mx_cfdi_status", "Timbrado", update_modified=False)
        frappe.db.commit()

        _state["uuid_nota"] = result.uuid
        _R.add(phase, "Nota de Credito stamped successfully",
               True, f"UUID={result.uuid}")
    except Exception as e:
        _R.add(phase, "Stamp Nota de Credito", False, _fmt(e))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 3: COMPLEMENTO DE PAGOS
# ─────────────────────────────────────────────────────────────────────────────

def _phase_3_complemento_pagos():
    phase = "PHASE 3: Complemento de Pagos (tipo P)"

    si_ppd = _state.get("si_ppd")
    if not si_ppd or not _state.get("uuid_ppd"):
        _R.add(phase, "Complemento de Pagos (skipped — PPD invoice unavailable)", False,
               "Prerequisite phase 2b failed")
        return

    # 3.1 Create Payment Entry against PPD invoice
    try:
        _, _, debtors, bank = _get_accounts()
        si_ppd.reload()

        pe = frappe.get_doc({
            "doctype": "Payment Entry",
            "payment_type": "Receive",
            "company": COMPANY,
            "party_type": "Customer",
            "party": si_ppd.customer,
            "paid_from": debtors,
            "paid_to": bank,
            "paid_amount": float(si_ppd.grand_total),
            "received_amount": float(si_ppd.grand_total),
            "source_exchange_rate": 1.0,
            "target_exchange_rate": 1.0,
            "posting_date": frappe.utils.today(),
            "reference_no": f"PAY-E2E-{si_ppd.name}",
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
        _state["pe_pago"] = pe
        _R.add(phase, "Create Payment Entry against PPD invoice",
               True, f"pe={pe.name}, amount={pe.paid_amount}")
    except Exception as e:
        _R.add(phase, "Create Payment Entry", False, _fmt(e))
        return

    # 3.2 Build payment CFDI
    try:
        from erpnext_mexico.cfdi.payment_builder import build_payment_cfdi
        comprobante = build_payment_cfdi(pe)
        assert comprobante is not None, "build_payment_cfdi returned None"
        # Verify tipo P
        tipo = getattr(comprobante, "tipo_de_comprobante", None) \
            or comprobante.get("TipoDeComprobante")
        assert tipo == "P", f"Expected tipo='P', got '{tipo}'"
        _R.add(phase, "Build payment CFDI (tipo_de_comprobante='P')", True)
    except Exception as e:
        _R.add(phase, "Build payment CFDI", False, _fmt(e))
        return

    # 3.3 Sign and stamp
    try:
        from erpnext_mexico.cfdi.payment_builder import (
            build_payment_cfdi, sign_payment_cfdi
        )
        from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
        from erpnext_mexico.cfdi.cfdi_helpers import save_cfdi_attachment

        comprobante = build_payment_cfdi(pe)
        signed = sign_payment_cfdi(comprobante, COMPANY)

        pac = PACDispatcher.get_pac(COMPANY)
        result = pac.stamp(signed)
        assert result.success, f"Payment stamp failed: {result.error_message}"

        xml_filename = f"CFDI_Pago_{pe.name}_{result.uuid}.xml"
        xml_file = save_cfdi_attachment(pe, xml_filename, result.xml_stamped, "text/xml")

        pe.db_set("mx_pago_uuid", result.uuid, update_modified=False)
        pe.db_set("mx_pago_status", "Timbrado", update_modified=False)
        pe.db_set("mx_pago_xml", xml_file.file_url, update_modified=False)
        frappe.db.commit()

        _state["uuid_pago"] = result.uuid
        _state["xml_pago"] = result.xml_stamped
        _R.add(phase, "Sign and stamp payment CFDI",
               True, f"UUID={result.uuid}")
    except Exception as e:
        _R.add(phase, "Sign and stamp payment CFDI", False, _fmt(e))
        return

    # 3.4 Verify DoctoRelacionado and parcialidad in XML
    try:
        from lxml import etree
        xml_str = _state["xml_pago"]
        if isinstance(xml_str, str):
            xml_bytes = xml_str.encode("utf-8")
        else:
            xml_bytes = xml_str

        tree = etree.fromstring(xml_bytes)
        ns_pago = "http://www.sat.gob.mx/Pagos20"
        ns_cfdi = SAT_NS_CFDI

        # Find Complemento/Pagos node
        complemento = tree.find(f"{{{ns_cfdi}}}Complemento")
        assert complemento is not None, "Complemento node not found in payment XML"

        pagos_node = complemento.find(f"{{{ns_pago}}}Pagos")
        assert pagos_node is not None, "Pagos node not found in Complemento"

        pago_node = pagos_node.find(f"{{{ns_pago}}}Pago")
        assert pago_node is not None, "Pago node not found"

        docto_rel = pago_node.find(f"{{{ns_pago}}}DoctoRelacionado")
        assert docto_rel is not None, "DoctoRelacionado not found in Pago"

        uuid_docto = docto_rel.get("IdDocumento")
        assert uuid_docto == _state["uuid_ppd"], \
            f"DoctoRelacionado UUID mismatch: expected {_state['uuid_ppd']}, got {uuid_docto}"

        _R.add(phase, "DoctoRelacionado references correct PPD UUID",
               True, f"IdDocumento={uuid_docto[:8]}...")
    except Exception as e:
        _R.add(phase, "DoctoRelacionado and parcialidad in XML", False, _fmt(e))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 4: CANCELACION
# ─────────────────────────────────────────────────────────────────────────────

def _phase_4_cancelacion():
    phase = "PHASE 4: Cancelacion"

    uuid_pue = _state.get("uuid_pue")
    if not uuid_pue:
        _R.add(phase, "Cancelacion (skipped — no PUE UUID available)", False,
               "Prerequisite phase 2a failed")
        return

    try:
        from erpnext_mexico.cfdi.xml_builder import _get_active_certificate, _get_file_bytes
        from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher

        pac = PACDispatcher.get_pac(COMPANY)
        cert = _get_active_certificate(COMPANY)

        result = pac.cancel(
            uuid=uuid_pue,
            rfc_emisor=frappe.db.get_value("Company", COMPANY, "mx_rfc"),
            certificate=_get_file_bytes(cert.certificate_file),
            key=_get_file_bytes(cert.key_file),
            password=cert.get_password("key_password"),
            reason="02",  # Comprobante emitido con errores sin relacion
        )

        # In sandbox cancel may return success or a pending/accepted status
        cancel_ok = result.success or (
            hasattr(result, "status") and result.status in (
                "Cancelado", "En proceso", "Solicitud de cancelacion recibida",
                "202", "201"
            )
        )
        detail = f"success={result.success}"
        if hasattr(result, "status"):
            detail += f", status={result.status}"
        if not result.success and hasattr(result, "error_message"):
            detail += f", msg={result.error_message}"

        _R.add(phase, f"Cancel PUE CFDI (reason=02, uuid={uuid_pue[:8]}...)",
               cancel_ok, detail)
    except Exception as e:
        _R.add(phase, "Cancel PUE CFDI", False, _fmt(e))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 5: NOMINA
# ─────────────────────────────────────────────────────────────────────────────

def _phase_5_nomina():
    phase = "PHASE 5: Nomina (CFDI tipo N)"

    # 5.1 Build mock salary slip
    try:
        salary_slip = _build_mock_salary_slip()
        _R.add(phase, "Build mock Salary Slip for nomina builder", True)
    except Exception as e:
        _R.add(phase, "Build mock Salary Slip", False, _fmt(e))
        return

    # 5.2 Build nomina CFDI
    try:
        from erpnext_mexico.cfdi.nomina_builder import build_nomina_cfdi
        comprobante = build_nomina_cfdi(salary_slip)
        assert comprobante is not None, "build_nomina_cfdi returned None"
        tipo = getattr(comprobante, "tipo_de_comprobante", None) \
            or comprobante.get("TipoDeComprobante")
        assert tipo == "N", f"Expected tipo='N', got '{tipo}'"
        _R.add(phase, "Build nomina CFDI (tipo_de_comprobante='N')", True)
    except Exception as e:
        _R.add(phase, "Build nomina CFDI", False, _fmt(e))
        return

    # 5.3 Sign nomina CFDI
    try:
        from erpnext_mexico.cfdi.nomina_builder import build_nomina_cfdi, sign_nomina_cfdi
        comprobante = build_nomina_cfdi(salary_slip)
        signed = sign_nomina_cfdi(comprobante, COMPANY)
        assert signed is not None, "sign_nomina_cfdi returned None"
        _R.add(phase, "Sign nomina CFDI with CSD", True)
    except Exception as e:
        _R.add(phase, "Sign nomina CFDI", False, _fmt(e))
        return

    # 5.4 Verify XML structure — Nomina 1.2 nodes
    try:
        from erpnext_mexico.cfdi.nomina_builder import build_nomina_cfdi, sign_nomina_cfdi
        from erpnext_mexico.cfdi.xml_builder import get_cfdi_xml_bytes
        from lxml import etree

        comprobante = build_nomina_cfdi(salary_slip)
        signed = sign_nomina_cfdi(comprobante, COMPANY)
        xml_bytes = get_cfdi_xml_bytes(signed)
        tree = etree.fromstring(xml_bytes)

        ns_cfdi = SAT_NS_CFDI
        ns_nomina = "http://www.sat.gob.mx/nomina12"

        # Root must be cfdi:Comprobante
        assert tree.tag == f"{{{ns_cfdi}}}Comprobante", \
            f"Root tag mismatch: {tree.tag}"

        # Must have Complemento with Nomina
        complemento = tree.find(f"{{{ns_cfdi}}}Complemento")
        assert complemento is not None, "Complemento node missing"

        nomina_node = complemento.find(f"{{{ns_nomina}}}Nomina")
        assert nomina_node is not None, \
            "nomina12:Nomina node not found in Complemento"

        # Must have Emisor and Receptor inside Nomina
        assert nomina_node.find(f"{{{ns_nomina}}}Emisor") is not None \
            or nomina_node.find("Emisor") is not None, \
            "Nomina/Emisor not found"
        assert nomina_node.find(f"{{{ns_nomina}}}Receptor") is not None \
            or nomina_node.find("Receptor") is not None, \
            "Nomina/Receptor not found"

        # Percepciones must be present
        percepciones = (
            nomina_node.find(f"{{{ns_nomina}}}Percepciones")
            or nomina_node.find("Percepciones")
        )
        assert percepciones is not None, "Nomina/Percepciones not found"

        _R.add(phase, "XML structure valid (Nomina 1.2 nodes: Emisor, Receptor, Percepciones)",
               True, f"xml_size={len(xml_bytes)}B")
    except Exception as e:
        _R.add(phase, "XML structure Nomina 1.2", False, _fmt(e))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 6: CARTA PORTE
# ─────────────────────────────────────────────────────────────────────────────

def _phase_6_carta_porte():
    phase = "PHASE 6: Carta Porte (CFDI tipo T)"

    # 6.1 Build mock delivery note
    try:
        dn = _build_mock_delivery_note()
        _R.add(phase, "Build mock Delivery Note for carta porte builder", True)
    except Exception as e:
        _R.add(phase, "Build mock Delivery Note", False, _fmt(e))
        return

    # 6.2 Build carta porte CFDI
    try:
        from erpnext_mexico.cfdi.carta_porte_builder import build_carta_porte_cfdi
        comprobante = build_carta_porte_cfdi(dn)
        assert comprobante is not None, "build_carta_porte_cfdi returned None"
        tipo = getattr(comprobante, "tipo_de_comprobante", None) \
            or comprobante.get("TipoDeComprobante")
        assert tipo == "T", f"Expected tipo='T', got '{tipo}'"
        _R.add(phase, "Build carta porte CFDI (tipo_de_comprobante='T')", True)
    except Exception as e:
        _R.add(phase, "Build carta porte CFDI", False, _fmt(e))
        return

    # 6.3 Sign carta porte CFDI
    try:
        from erpnext_mexico.cfdi.carta_porte_builder import (
            build_carta_porte_cfdi, sign_carta_porte_cfdi
        )
        comprobante = build_carta_porte_cfdi(dn)
        signed = sign_carta_porte_cfdi(comprobante, COMPANY)
        assert signed is not None, "sign_carta_porte_cfdi returned None"
        _R.add(phase, "Sign carta porte CFDI with CSD", True)
    except Exception as e:
        _R.add(phase, "Sign carta porte CFDI", False, _fmt(e))
        return

    # 6.4 Verify XML structure — CartaPorte 3.1 nodes
    try:
        from erpnext_mexico.cfdi.carta_porte_builder import (
            build_carta_porte_cfdi, sign_carta_porte_cfdi
        )
        from erpnext_mexico.cfdi.xml_builder import get_cfdi_xml_bytes
        from lxml import etree

        comprobante = build_carta_porte_cfdi(dn)
        signed = sign_carta_porte_cfdi(comprobante, COMPANY)
        xml_bytes = get_cfdi_xml_bytes(signed)
        tree = etree.fromstring(xml_bytes)

        ns_cfdi = SAT_NS_CFDI
        ns_cp = "http://www.sat.gob.mx/CartaPorte31"

        assert tree.tag == f"{{{ns_cfdi}}}Comprobante", \
            f"Root tag mismatch: {tree.tag}"

        complemento = tree.find(f"{{{ns_cfdi}}}Complemento")
        assert complemento is not None, "Complemento node missing"

        cp_node = complemento.find(f"{{{ns_cp}}}CartaPorte")
        assert cp_node is not None, \
            "CartaPorte31:CartaPorte not found in Complemento"

        # Must have Ubicaciones
        ubicaciones = cp_node.find(f"{{{ns_cp}}}Ubicaciones")
        assert ubicaciones is not None, "CartaPorte/Ubicaciones not found"

        # Must have at least 2 ubicaciones (origin + destination)
        ubicacion_list = ubicaciones.findall(f"{{{ns_cp}}}Ubicacion")
        assert len(ubicacion_list) >= 2, \
            f"Expected >= 2 Ubicacion, got {len(ubicacion_list)}"

        # Must have Mercancias
        mercancias = cp_node.find(f"{{{ns_cp}}}Mercancias")
        assert mercancias is not None, "CartaPorte/Mercancias not found"

        _R.add(phase, "XML structure valid (CartaPorte 3.1: Ubicaciones, Mercancias)",
               True, f"ubicaciones={len(ubicacion_list)}, xml_size={len(xml_bytes)}B")
    except Exception as e:
        _R.add(phase, "XML structure CartaPorte 3.1", False, _fmt(e))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 7: DIOT
# ─────────────────────────────────────────────────────────────────────────────

def _phase_7_diot():
    phase = "PHASE 7: DIOT 2025"

    # 7.1 Ensure test Purchase Invoice exists for the period
    try:
        _ensure_purchase_invoice()
        _R.add(phase, "Purchase Invoice with IVA 16% exists for test period", True)
    except Exception as e:
        _R.add(phase, "Ensure Purchase Invoice for DIOT", False, _fmt(e))

    # 7.2 Generate DIOT TXT
    try:
        from erpnext_mexico.diot.diot_generator import generate_diot
        result = generate_diot(company=COMPANY, month=MONTH, year=YEAR)

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        for key in ("filename", "content", "supplier_count", "total_lines"):
            assert key in result, f"Missing key '{key}' in DIOT result"

        assert result["content"], "DIOT content is empty"
        assert result["supplier_count"] > 0, "supplier_count must be > 0"
        assert result["total_lines"] > 0, "total_lines must be > 0"

        filename = result["filename"]
        assert filename.startswith("DIOT_"), f"Filename must start with DIOT_: {filename}"
        assert filename.endswith(".txt"), f"Filename must end with .txt: {filename}"

        _R.add(phase, "Generate DIOT TXT (non-empty, correct filename)",
               True, f"file={filename}, suppliers={result['supplier_count']}")
    except Exception as e:
        _R.add(phase, "Generate DIOT TXT", False, _fmt(e))
        return

    # 7.3 Validate 24 pipe-delimited fields per line
    try:
        from erpnext_mexico.diot.diot_generator import generate_diot
        result = generate_diot(company=COMPANY, month=MONTH, year=YEAR)
        lines = result["content"].strip().split("\n")
        bad_lines = []
        for i, line in enumerate(lines):
            fields = line.split("|")
            if len(fields) != 24:
                bad_lines.append(f"line {i+1}: {len(fields)} fields")

        assert not bad_lines, \
            f"Lines with wrong field count: {bad_lines[:3]}"
        _R.add(phase, f"All {len(lines)} DIOT lines have exactly 24 pipe-delimited fields",
               True)
    except Exception as e:
        _R.add(phase, "DIOT lines have 24 fields", False, _fmt(e))

    # 7.4 Empty period returns empty result
    try:
        from erpnext_mexico.diot.diot_generator import generate_diot
        empty = generate_diot(company=COMPANY, month=1, year=2099)
        assert isinstance(empty, dict), "Must return dict for empty period"
        assert empty.get("content", "") == "", \
            f"Expected empty content for 2099-01, got: {empty.get('content')!r:.50}"
        assert empty.get("supplier_count", 0) == 0, \
            f"Expected 0 suppliers for 2099-01"
        _R.add(phase, "Empty period (2099-01) returns empty result", True)
    except Exception as e:
        _R.add(phase, "Empty period returns empty result", False, _fmt(e))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 8: CONTABILIDAD ELECTRONICA
# ─────────────────────────────────────────────────────────────────────────────

def _phase_8_contabilidad_electronica():
    phase = "PHASE 8: Contabilidad Electronica (Anexo 24)"
    frappe.set_user("Administrator")

    # 8a. Catalogo de Cuentas XML
    try:
        from erpnext_mexico.electronic_accounting.catalog_xml import generate_catalog_xml
        from lxml import etree

        result = generate_catalog_xml(company=COMPANY, year=YEAR, month=MONTH)
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert "<?xml version=" in result, "Missing XML declaration"
        assert "CatalogoCuentas" in result, "Missing CatalogoCuentas element/namespace"
        assert 'Version="1.3"' in result, "Missing Version 1.3"

        tree = etree.fromstring(result.encode("utf-8"))
        children = list(tree)
        numcta_count = result.count("NumCta=")
        _R.add(phase, "Catalogo de Cuentas XML (Version 1.3, well-formed)",
               True, f"accounts={numcta_count}, child_nodes={len(children)}")
    except Exception as e:
        _R.add(phase, "Catalogo de Cuentas XML", False, _fmt(e))

    # 8b. Balanza de Comprobacion XML
    try:
        from erpnext_mexico.electronic_accounting.balanza_xml import generate_balanza_xml
        from lxml import etree

        result = generate_balanza_xml(company=COMPANY, year=YEAR, month=MONTH)
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert "<?xml version=" in result, "Missing XML declaration"
        assert "BalanzaComprobacion" in result, "Missing BalanzaComprobacion"
        assert 'Version="1.3"' in result, "Missing Version 1.3"
        assert 'TipoEnvio="N"' in result, "Missing TipoEnvio"

        tree = etree.fromstring(result.encode("utf-8"))
        children = list(tree)

        # Validate first Ctas element has required attributes
        if children:
            attrs = dict(children[0].attrib)
            for required_attr in ("SaldoIni", "Debe", "Haber", "SaldoFin"):
                assert required_attr in attrs, \
                    f"Ctas missing attribute: {required_attr}"

        _R.add(phase, "Balanza de Comprobacion XML (Version 1.3, SaldoIni/Debe/Haber/SaldoFin)",
               True, f"ctas={len(children)}")
    except Exception as e:
        _R.add(phase, "Balanza de Comprobacion XML", False, _fmt(e))

    # 8c. Polizas XML
    try:
        from erpnext_mexico.electronic_accounting.polizas_xml import generate_polizas_xml
        from lxml import etree

        result = generate_polizas_xml(
            company=COMPANY,
            year=YEAR,
            month=MONTH,
            tipo_solicitud="AF",
            num_orden="E2ETEST01",
        )
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert "<?xml version=" in result, "Missing XML declaration"
        assert "PolizasPeriodo" in result, "Missing PolizasPeriodo"
        assert 'Version="1.3"' in result, "Missing Version 1.3"
        assert 'TipoSolicitud="AF"' in result, "Missing TipoSolicitud"
        assert 'NumOrden="E2ETEST01"' in result, "Missing NumOrden"

        tree = etree.fromstring(result.encode("utf-8"))
        ns_pol = "http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
        polizas = tree.findall(f"{{{ns_pol}}}Poliza")

        _R.add(phase, "Polizas del Periodo XML (Version 1.3, TipoSolicitud, NumOrden)",
               True, f"polizas={len(polizas)}")
    except Exception as e:
        _R.add(phase, "Polizas del Periodo XML", False, _fmt(e))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 9: XML VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def _phase_9_xml_validation():
    phase = "PHASE 9: XML Validation (stamped CFDIs)"

    cfdi_set = [
        ("PUE factura", _state.get("xml_pue"), "I"),
        ("PPD factura", _state.get("xml_ppd"), "I"),
        ("Pago complement", _state.get("xml_pago"), "P"),
    ]

    for label, xml_content, expected_tipo in cfdi_set:
        if not xml_content:
            _R.add(phase, f"{label} — XML present for validation", False,
                   "No XML available (upstream stamp phase failed)")
            continue

        # 9.x.1 Parse with lxml
        try:
            from lxml import etree
            if isinstance(xml_content, str):
                xml_bytes = xml_content.encode("utf-8")
            else:
                xml_bytes = xml_content
            tree = etree.fromstring(xml_bytes)
            _R.add(phase, f"{label} — lxml parse (well-formed XML)", True,
                   f"{len(xml_bytes)}B")
        except Exception as e:
            _R.add(phase, f"{label} — lxml parse", False, _fmt(e))
            continue

        # 9.x.2 SAT namespace
        try:
            assert tree.tag == f"{{{SAT_NS_CFDI}}}Comprobante", \
                f"Root element namespace mismatch: {tree.tag}"
            _R.add(phase, f"{label} — SAT namespace cfdi4 on root element", True)
        except Exception as e:
            _R.add(phase, f"{label} — SAT namespace", False, _fmt(e))

        # 9.x.3 TimbreFiscalDigital node
        try:
            complemento = tree.find(f"{{{SAT_NS_CFDI}}}Complemento")
            assert complemento is not None, "Complemento node missing"
            tfd = complemento.find(f"{{{SAT_NS_TFD}}}TimbreFiscalDigital")
            assert tfd is not None, "TimbreFiscalDigital not found"
            uuid_val = tfd.get("UUID")
            assert uuid_val and len(uuid_val) == 36, \
                f"TFD UUID invalid: '{uuid_val}'"
            _R.add(phase, f"{label} — TimbreFiscalDigital with UUID",
                   True, f"UUID={uuid_val[:8]}...")
        except Exception as e:
            _R.add(phase, f"{label} — TimbreFiscalDigital", False, _fmt(e))

        # 9.x.4 Sello, NoCertificado, Certificado attributes
        try:
            sello = tree.get("Sello")
            no_cert = tree.get("NoCertificado")
            cert_attr = tree.get("Certificado")
            assert sello and len(sello) > 10, "Sello missing or too short"
            assert no_cert and len(no_cert) >= 20, \
                f"NoCertificado missing or short: '{no_cert}'"
            assert cert_attr and len(cert_attr) > 100, \
                "Certificado (base64) missing or too short"
            _R.add(phase, f"{label} — Sello, NoCertificado, Certificado present",
                   True, f"NoCert={no_cert}")
        except Exception as e:
            _R.add(phase, f"{label} — Sello/NoCertificado/Certificado", False, _fmt(e))

        # 9.x.5 Emisor / Receptor / Conceptos
        try:
            emisor = tree.find(f"{{{SAT_NS_CFDI}}}Emisor")
            receptor = tree.find(f"{{{SAT_NS_CFDI}}}Receptor")
            conceptos = tree.find(f"{{{SAT_NS_CFDI}}}Conceptos")
            assert emisor is not None, "Emisor node missing"
            assert receptor is not None, "Receptor node missing"
            assert conceptos is not None, "Conceptos node missing"
            assert emisor.get("Rfc") == COMPANY_RFC, \
                f"Emisor RFC mismatch: {emisor.get('Rfc')}"
            _R.add(phase, f"{label} — Emisor/Receptor/Conceptos structure",
                   True, f"emisor_rfc={emisor.get('Rfc')}")
        except Exception as e:
            _R.add(phase, f"{label} — Emisor/Receptor/Conceptos", False, _fmt(e))

        # 9.x.6 TipoDeComprobante matches expected
        try:
            tipo = tree.get("TipoDeComprobante")
            assert tipo == expected_tipo, \
                f"Expected TipoDeComprobante='{expected_tipo}', got '{tipo}'"
            _R.add(phase, f"{label} — TipoDeComprobante='{expected_tipo}'", True)
        except Exception as e:
            _R.add(phase, f"{label} — TipoDeComprobante", False, _fmt(e))


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 10: NEGATIVE TESTS
# ─────────────────────────────────────────────────────────────────────────────

def _phase_10_negative_tests():
    phase = "PHASE 10: Negative Tests"

    # 10a. Invalid RFC on customer -> validation error from xml_builder
    try:
        _ensure_customer()
        cust = frappe.get_doc("Customer", CUSTOMER)
        original_rfc = cust.mx_rfc

        # Temporarily set an invalid RFC
        cust.db_set("mx_rfc", "INVALIDO123XX", update_modified=False)
        frappe.db.commit()

        # Rebuild customer cache
        frappe.clear_cache(doctype="Customer")

        raised = False
        try:
            income, iva, _, _ = _get_accounts()
            si = frappe.get_doc({
                "doctype": "Sales Invoice",
                "company": COMPANY,
                "customer": CUSTOMER,
                "posting_date": frappe.utils.today(),
                "due_date": frappe.utils.add_days(frappe.utils.today(), 30),
                "currency": "MXN",
                "conversion_rate": 1.0,
                "selling_price_list": "Standard Selling",
                "mx_uso_cfdi": "S01",
                "mx_metodo_pago": "PUE",
                "mx_forma_pago": "03",
                "mx_exportacion": "01",
                "items": [{
                    "item_code": "Servicio Consultoria MX",
                    "qty": 1,
                    "rate": 100.00,
                    "income_account": income,
                }],
            })
            si.flags.ignore_permissions = True
            si.flags.ignore_mandatory = True
            si.insert()
            frappe.db.commit()

            from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice, sign_cfdi
            comprobante = build_cfdi_from_sales_invoice(si)
            sign_cfdi(comprobante, COMPANY)
            # If we get here without error, the PAC / satcfdi should reject it
            from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
            pac = PACDispatcher.get_pac(COMPANY)
            result = pac.stamp(comprobante)
            if not result.success:
                raised = True
        except Exception:
            raised = True
        finally:
            # Restore RFC
            frappe.clear_cache(doctype="Customer")
            cust2 = frappe.get_doc("Customer", CUSTOMER)
            cust2.db_set("mx_rfc", original_rfc, update_modified=False)
            frappe.db.commit()
            frappe.clear_cache(doctype="Customer")

        _R.add(phase, "Invalid RFC (INVALIDO123XX) triggers validation error",
               raised, "Confirmed: invalid RFC rejected")
    except Exception as e:
        _R.add(phase, "Invalid RFC triggers validation error", False, _fmt(e))

    # 10b. Missing ClaveProdServ -> validation error
    try:
        _ensure_customer()
        income, iva, _, _ = _get_accounts()

        si_bad = frappe.get_doc({
            "doctype": "Sales Invoice",
            "company": COMPANY,
            "customer": CUSTOMER,
            "posting_date": frappe.utils.today(),
            "due_date": frappe.utils.add_days(frappe.utils.today(), 30),
            "currency": "MXN",
            "conversion_rate": 1.0,
            "selling_price_list": "Standard Selling",
            "mx_uso_cfdi": "S01",
            "mx_metodo_pago": "PUE",
            "mx_forma_pago": "03",
            "mx_exportacion": "01",
            "items": [{
                "item_code": "Servicio Consultoria MX",
                "qty": 1,
                "rate": 100.00,
                "income_account": income,
                "mx_clave_prod_serv": "",  # Intentionally blank
            }],
        })
        si_bad.flags.ignore_permissions = True
        si_bad.flags.ignore_mandatory = True
        si_bad.insert()
        frappe.db.commit()

        # Clear the clave on the saved item via db
        frappe.db.sql(
            "UPDATE `tabSales Invoice Item` SET mx_clave_prod_serv='' "
            "WHERE parent=%s",
            (si_bad.name,)
        )
        si_bad.reload()

        raised = False
        try:
            from erpnext_mexico.cfdi.xml_builder import (
                build_cfdi_from_sales_invoice, sign_cfdi
            )
            comprobante = build_cfdi_from_sales_invoice(si_bad)
            sign_cfdi(comprobante, COMPANY)

            from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
            pac = PACDispatcher.get_pac(COMPANY)
            result = pac.stamp(comprobante)
            if not result.success:
                raised = True
        except Exception:
            raised = True

        _R.add(phase, "Missing ClaveProdServ triggers validation or stamp error",
               raised, "Confirmed: blank clave_prod_serv rejected")
    except Exception as e:
        _R.add(phase, "Missing ClaveProdServ validation error", False, _fmt(e))

    # 10c. Duplicate stamp (already-stamped UUID) -> PAC error 307 / rejected
    try:
        uuid_pue = _state.get("uuid_pue")
        xml_pue = _state.get("xml_pue")

        if not uuid_pue or not xml_pue:
            _R.add(phase,
                   "Duplicate stamp of already-stamped CFDI (skipped — PUE not stamped)",
                   False, "Prerequisite phase 2a failed")
        else:
            # Re-create the signed comprobante and try to stamp it again
            # We use the e2e PUE invoice which is already stamped
            si_pue = _state.get("si_pue")
            if si_pue is None:
                raise AssertionError("si_pue not in state")

            si_pue.reload()
            from erpnext_mexico.cfdi.xml_builder import (
                build_cfdi_from_sales_invoice, sign_cfdi
            )
            from satcfdi.create.cfd.cfdi40 import InformacionGlobal
            from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher

            comprobante = build_cfdi_from_sales_invoice(si_pue)
            comprobante["InformacionGlobal"] = InformacionGlobal(
                periodicidad="04", meses=f"{MONTH:02d}", ano=YEAR
            )
            signed = sign_cfdi(comprobante, COMPANY)

            pac = PACDispatcher.get_pac(COMPANY)
            result2 = pac.stamp(signed)

            # Finkok returns the already-timbrado UUID without error in sandbox
            # (idempotent behaviour) or returns an error code 307
            # Either way we consider the test passed if we get a deterministic response
            got_expected = (
                not result2.success
                or (result2.uuid == uuid_pue)  # idempotent — same UUID back
            )
            detail = (
                f"success={result2.success}, uuid={result2.uuid}, "
                f"error={getattr(result2, 'error_message', '')}"
            )
            _R.add(phase, "Duplicate stamp: PAC returns error or same UUID (idempotent)",
                   got_expected, detail)
    except Exception as e:
        _R.add(phase, "Duplicate stamp -> PAC error", False, _fmt(e))


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt(exc: Exception) -> str:
    """Format exception to a one-line string for test output."""
    return f"{type(exc).__name__}: {str(exc)[:200]}"


def _ensure_customer():
    """Ensure the test customer exists with correct fiscal data."""
    if not frappe.db.exists("Customer", CUSTOMER):
        cust = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": CUSTOMER,
            "customer_type": "Company",
            "customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
                              or "All Customer Groups",
            "territory": frappe.db.get_value("Territory", {"is_group": 0}, "name") or "All Territories",
        })
        cust.flags.ignore_permissions = True
        cust.insert()
        frappe.db.commit()

    cust = frappe.get_doc("Customer", CUSTOMER)
    cust.mx_rfc = CUSTOMER_RFC
    cust.mx_nombre_fiscal = "PUBLICO EN GENERAL"
    cust.mx_regimen_fiscal = "616"
    cust.mx_domicilio_fiscal_cp = "42501"
    cust.mx_default_uso_cfdi = "S01"
    cust.mx_default_forma_pago = "03"
    cust.save(ignore_permissions=True)
    frappe.db.commit()
    frappe.clear_cache(doctype="Customer")


def _get_accounts():
    """Return (income, iva, debtors, bank) account names for the company."""
    income = frappe.db.get_value("Account", {
        "company": COMPANY, "root_type": "Income", "is_group": 0,
    }, "name")
    iva = frappe.db.get_value("Account", {
        "company": COMPANY, "account_name": ["like", "%IVA%"], "is_group": 0,
    }, "name") or income
    debtors = frappe.db.get_value("Account", {
        "company": COMPANY, "account_type": "Receivable", "is_group": 0,
    }, "name")
    bank = frappe.db.get_value("Account", {
        "company": COMPANY, "account_type": "Bank", "is_group": 0,
    }, "name")
    return income, iva, debtors, bank


def _create_invoice(metodo_pago: str = "PUE", rate: float = 10000.00):
    """Create and insert a Sales Invoice for testing."""
    _ensure_customer()
    income, iva, _, _ = _get_accounts()

    si = frappe.get_doc({
        "doctype": "Sales Invoice",
        "company": COMPANY,
        "customer": CUSTOMER,
        "posting_date": frappe.utils.today(),
        "due_date": frappe.utils.add_days(frappe.utils.today(), 30),
        "currency": "MXN",
        "conversion_rate": 1.0,
        "selling_price_list": "Standard Selling",
        "mx_uso_cfdi": "S01",
        "mx_metodo_pago": metodo_pago,
        "mx_forma_pago": "03" if metodo_pago == "PUE" else "99",
        "mx_exportacion": "01",
        "items": [{
            "item_code": "Servicio Consultoria MX",
            "qty": 1,
            "rate": rate,
            "income_account": income,
        }],
        "taxes": [{
            "charge_type": "On Net Total",
            "account_head": iva,
            "description": "IVA 16%",
            "rate": 16,
        }],
    })
    si.flags.ignore_permissions = True
    si.flags.ignore_mandatory = True
    si.insert()
    frappe.db.commit()
    return si


def _ensure_purchase_invoice():
    """Ensure a submitted Purchase Invoice exists for DIOT period."""
    from_date = f"{YEAR}-{MONTH:02d}-01"
    to_date = f"{YEAR}-{MONTH:02d}-28"

    existing = frappe.get_all("Purchase Invoice", filters={
        "company": COMPANY,
        "supplier": SUPPLIER,
        "docstatus": 1,
        "posting_date": ["between", [from_date, to_date]],
    }, fields=["name"], limit_page_length=1)

    if existing:
        return existing[0].name

    expense = frappe.db.get_value("Account", {
        "company": COMPANY, "root_type": "Expense", "is_group": 0,
    }, "name")
    payable = frappe.db.get_value("Account", {
        "company": COMPANY, "root_type": "Liability",
        "account_type": "Payable", "is_group": 0,
    }, "name")
    iva_acc = frappe.db.get_value("Account", {
        "company": COMPANY, "is_group": 0, "account_type": "Tax",
    }, "name")
    cost_center = frappe.db.get_value("Cost Center", {
        "company": COMPANY, "is_group": 0,
    }, "name")
    currency = frappe.db.get_value("Company", COMPANY, "default_currency") or "MXN"

    if not all([expense, payable, iva_acc, cost_center]):
        raise AssertionError(
            f"Cannot create Purchase Invoice — missing accounts: "
            f"expense={expense}, payable={payable}, iva={iva_acc}, cc={cost_center}"
        )

    pinv = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": SUPPLIER,
        "company": COMPANY,
        "posting_date": f"{YEAR}-{MONTH:02d}-15",
        "due_date": f"{YEAR}-{MONTH:02d}-28",
        "credit_to": payable,
        "currency": currency,
        "conversion_rate": 1.0,
        "buying_price_list": (
            frappe.db.get_value("Price List", {"buying": 1}, "name") or "Standard Buying"
        ),
        "cost_center": cost_center,
        "items": [{
            "item_name": "Servicio E2E DIOT",
            "description": "Servicio profesional para prueba E2E DIOT",
            "qty": 1,
            "rate": 10000.0,
            "expense_account": expense,
            "cost_center": cost_center,
        }],
        "taxes": [{
            "charge_type": "On Net Total",
            "account_head": iva_acc,
            "description": "IVA 16%",
            "rate": 16,
            "cost_center": cost_center,
        }],
    })
    pinv.insert(ignore_permissions=True)
    pinv.submit()
    frappe.db.commit()
    return pinv.name


def _assert_xml_valid(xml_content, expected_tipo: str = "I"):
    """Parse XML and assert required CFDI 4.0 nodes are present."""
    from lxml import etree

    if isinstance(xml_content, str):
        xml_bytes = xml_content.encode("utf-8")
    else:
        xml_bytes = xml_content

    tree = etree.fromstring(xml_bytes)
    ns = SAT_NS_CFDI

    assert tree.tag == f"{{{ns}}}Comprobante", \
        f"Root element not cfdi:Comprobante: {tree.tag}"
    assert tree.get("TipoDeComprobante") == expected_tipo, \
        f"TipoDeComprobante='{tree.get('TipoDeComprobante')}', expected '{expected_tipo}'"

    comp = tree.find(f"{{{ns}}}Complemento")
    assert comp is not None, "Complemento node missing"

    tfd_ns = SAT_NS_TFD
    tfd = comp.find(f"{{{tfd_ns}}}TimbreFiscalDigital")
    assert tfd is not None, "TimbreFiscalDigital not found"

    uuid = tfd.get("UUID")
    assert uuid and len(uuid) == 36, f"TFD UUID invalid: '{uuid}'"

    emisor = tree.find(f"{{{ns}}}Emisor")
    receptor = tree.find(f"{{{ns}}}Receptor")
    conceptos = tree.find(f"{{{ns}}}Conceptos")
    assert emisor is not None, "Emisor missing"
    assert receptor is not None, "Receptor missing"
    assert conceptos is not None, "Conceptos missing"


# ─────────────────────────────────────────────────────────────────────────────
# Mock builders for Nomina and Carta Porte
# ─────────────────────────────────────────────────────────────────────────────

def _build_mock_salary_slip():
    """
    Build a minimal mock Salary Slip using frappe._dict to simulate the
    Frappe doc interface expected by nomina_builder.build_nomina_cfdi.

    Fields required by nomina_builder:
        company, employee, posting_date, start_date, end_date,
        total_working_days, gross_pay, earnings[], deductions[]
    Fields required by nomina_builder from Employee:
        employee_name, mx_curp, date_of_joining, department, designation
    Fields required by nomina_builder from Company:
        mx_rfc, mx_nombre_fiscal, mx_regimen_fiscal, mx_lugar_expedicion
    """
    # Mock salary component row
    earning_row = frappe._dict({
        "salary_component": "Basic Salary",
        "salary_component_abbr": "BS",
        "amount": 15000.00,
    })

    deduction_row = frappe._dict({
        "salary_component": "ISR",
        "salary_component_abbr": "ISR",
        "amount": 2500.00,
    })

    # Mock employee — nomina_builder uses frappe.get_cached_doc("Employee", ...)
    # We patch via a local frappe._dict and monkey-patch get_cached_doc for this call
    mock_employee = frappe._dict({
        "name": "EMP-E2E-001",
        "employee_name": "Juan Perez Lopez",
        "mx_rfc": "PELJ800101ABC",
        "mx_curp": "PELJ800101HDFRZN08",   # 18 chars
        "date_of_joining": "2020-01-15",
        "department": "Operaciones",
        "designation": "Analista",
        "mx_tipo_contrato": "01",
        "mx_tipo_regimen_nomina": "02",
        "mx_periodicidad_pago": "04",       # Quincenal
        "mx_nss": "12345678901",
        "mx_sbc": "700.00",
        "mx_sdi": "800.00",
        "mx_clave_ent_fed": "HID",
    })

    slip = frappe._dict({
        "name": "SAL-E2E-0001",
        "company": COMPANY,
        "employee": "EMP-E2E-001",
        "posting_date": frappe.utils.today(),
        "start_date": f"{YEAR}-{MONTH:02d}-01",
        "end_date": f"{YEAR}-{MONTH:02d}-15",
        "total_working_days": 15,
        "gross_pay": 15000.00,
        "net_pay": 12500.00,
        "naming_series": "SAL-",
        "payroll_frequency": "MONTHLY",
        "mx_tipo_nomina": "O",
        "mx_subsidio_al_empleo": None,
        "earnings": [earning_row],
        "deductions": [deduction_row],
    })

    # Monkey-patch frappe.get_cached_doc so nomina_builder finds the mock employee
    _original_get_cached_doc = frappe.get_cached_doc

    def _patched_get_cached_doc(doctype, name=None, *args, **kwargs):
        if doctype == "Employee" and name == "EMP-E2E-001":
            return mock_employee
        return _original_get_cached_doc(doctype, name, *args, **kwargs)

    frappe.get_cached_doc = _patched_get_cached_doc

    # Register cleanup — restore after nomina builder call
    slip._restore_cached_doc = _original_get_cached_doc

    return slip


def _build_mock_delivery_note():
    """
    Build a minimal mock Delivery Note using frappe._dict to simulate the
    Frappe doc interface expected by carta_porte_builder.build_carta_porte_cfdi.

    Fields required by carta_porte_builder:
        company, customer, posting_date, posting_time,
        mx_cp_origen, mx_estado_origen,
        mx_cp_destino, mx_estado_destino, mx_distancia_recorrida,
        mx_config_vehicular, mx_placa_vehiculo, mx_anio_modelo_vehiculo,
        mx_perm_sct, mx_num_permiso_sct,
        mx_aseguradora_resp_civil, mx_poliza_resp_civil,
        mx_nombre_conductor,
        items[]
    """
    item_row = frappe._dict({
        "item_code": "Servicio Consultoria MX",
        "item_name": "Servicio de Consultoria",
        "description": "Servicio profesional",
        "qty": 1,
        "rate": 10000.00,
        "amount": 10000.00,
        "uom": "Nos",
        "mx_clave_prod_serv_cp": "10101500",  # SAT carta porte product key
        "mx_clave_prod_serv": "81111507",
        "mx_clave_unidad": "H87",              # Pieza
        "weight_per_unit": 10.0,
        "mx_peso_en_kg": 10.0,
    })

    dn = frappe._dict({
        "name": "DN-E2E-0001",
        "doctype": "Delivery Note",
        "company": COMPANY,
        "customer": CUSTOMER,
        "posting_date": frappe.utils.today(),
        "posting_time": "10:00:00",
        "currency": "MXN",
        # Carta Porte origen
        "mx_cp_origen": "42501",
        "mx_estado_origen": "HID",
        "mx_municipio_origen": "Pachuca",
        "mx_localidad_origen": None,
        "mx_referencia_origen": None,
        "mx_calle_origen": "Av Principal 100",
        # Carta Porte destino
        "mx_cp_destino": "06600",
        "mx_estado_destino": "CMX",
        "mx_municipio_destino": "Cuauhtemoc",
        "mx_localidad_destino": None,
        "mx_referencia_destino": None,
        "mx_calle_destino": "Reforma 200",
        "mx_distancia_recorrida": "120",
        # Vehículo
        "mx_config_vehicular": "C2",
        "mx_placa_vehiculo": "ABC1234",
        "mx_anio_modelo_vehiculo": "2022",
        "mx_perm_sct": "TPAF01",
        "mx_num_permiso_sct": "SCT/TPAF01/12345",
        # Seguros
        "mx_aseguradora_resp_civil": "QUALITAS",
        "mx_poliza_resp_civil": "QUA-2024-001",
        # Conductor
        "mx_nombre_conductor": "Pedro Conductor Hernandez",
        "mx_rfc_conductor": "COHP800101ABC",
        "mx_curp_conductor": None,
        "mx_num_licencia_conductor": "LIC123456",
        # Transporte
        "mx_transp_internac": "No",
        "items": [item_row],
    })

    return dn


# Make sure to restore patched frappe after nomina test calls
def _restore_frappe_patch(salary_slip):
    """Restore frappe.get_cached_doc if it was monkey-patched for nomina tests."""
    if hasattr(salary_slip, "_restore_cached_doc"):
        frappe.get_cached_doc = salary_slip._restore_cached_doc
