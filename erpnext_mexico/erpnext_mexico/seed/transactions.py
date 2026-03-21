# -*- coding: utf-8 -*-
"""Fase 2: Transacciones — Sales/Purchase Invoices, Payment Entries, CFDI stamping."""
import json
import os
import time
from contextlib import contextmanager
import frappe
from frappe.utils import add_days

from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice, sign_cfdi
from erpnext_mexico.cfdi.payment_builder import build_payment_cfdi, sign_payment_cfdi
from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
from erpnext_mexico.cfdi.cfdi_helpers import save_cfdi_attachment, create_cfdi_log
from erpnext_mexico.seed.constants import COMPANY


@contextmanager
def _skip_due_date_validation():
    """Temporarily disable ERPNext due_date validation for backdated invoices."""
    from erpnext.accounts import party as _party_mod
    _orig = _party_mod.validate_due_date
    _party_mod.validate_due_date = lambda *a, **kw: None
    try:
        yield
    finally:
        _party_mod.validate_due_date = _orig

G = "\033[92m"
Y = "\033[93m"
RED = "\033[91m"
R = "\033[0m"
STAMP_DELAY = 2
STATE_FILE = "/tmp/seed_state.json"


def ok(msg):
    print(f"  {G}[OK]{R} {msg}")


def skip(msg):
    print(f"  {Y}[SKIP]{R} {msg}")


def fail(msg):
    print(f"  {RED}[FAIL]{R} {msg}")


def section(title):
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


def _get_accounts():
    income = frappe.db.get_value("Account", {
        "company": COMPANY, "account_name": "VENTAS NACIONALES", "is_group": 0}, "name")
    iva = frappe.db.get_value("Account", {
        "company": COMPANY, "account_name": ["like", "%IVA%"], "is_group": 0}, "name")
    debtors = frappe.db.get_value("Account", {
        "company": COMPANY, "account_type": "Receivable",
        "account_name": "CUENTAS POR COBRAR CLIENTES", "is_group": 0}, "name")
    if not debtors:
        debtors = frappe.db.get_value("Account", {
            "company": COMPANY, "account_type": "Receivable", "is_group": 0}, "name")
    bank = frappe.db.get_value("Account", {
        "company": COMPANY, "account_type": "Bank", "is_group": 0}, "name")
    expense = frappe.db.get_value("Account", {
        "company": COMPANY, "account_name": "COSTO DE VENTAS", "is_group": 0}, "name")
    if not expense:
        expense = frappe.db.get_value("Account", {
            "company": COMPANY, "root_type": "Expense", "is_group": 0}, "name")
    payable = frappe.db.get_value("Account", {
        "company": COMPANY, "account_name": "CUENTAS POR PAGAR PROVEEDORES", "is_group": 0}, "name")
    if not payable:
        payable = frappe.db.get_value("Account", {
            "company": COMPANY, "account_type": "Payable", "is_group": 0}, "name")
    return {"income": income, "iva": iva, "debtors": debtors,
            "bank": bank, "expense": expense, "payable": payable}


def _disable_auto_stamp():
    settings = frappe.get_single("MX CFDI Settings")
    old = settings.auto_stamp_on_submit
    if old:
        settings.auto_stamp_on_submit = 0
        settings.save(ignore_permissions=True)
        frappe.db.commit()
    return old


def _restore_auto_stamp(old_value):
    settings = frappe.get_single("MX CFDI Settings")
    settings.auto_stamp_on_submit = old_value
    settings.save(ignore_permissions=True)
    frappe.db.commit()


def _create_si(customer, items_data, posting_date, metodo_pago, forma_pago,
               uso_cfdi, accts, due_days=0, iva_rate=16):
    items = [{"item_code": ic, "qty": q, "rate": r, "income_account": accts["income"]}
             for ic, q, r in items_data]
    taxes = []
    if iva_rate > 0:
        taxes.append({"charge_type": "On Net Total", "account_head": accts["iva"],
                       "description": f"IVA {iva_rate}%", "rate": iva_rate})
    due_date = add_days(posting_date, max(due_days, 30))
    si = frappe.get_doc({
        "doctype": "Sales Invoice", "company": COMPANY, "customer": customer,
        "posting_date": posting_date, "due_date": due_date,
        "currency": "MXN", "conversion_rate": 1.0,
        "selling_price_list": "Standard Selling", "debit_to": accts["debtors"],
        "mx_uso_cfdi": uso_cfdi, "mx_metodo_pago": metodo_pago,
        "mx_forma_pago": forma_pago, "mx_exportacion": "01",
        "items": items, "taxes": taxes,
    })
    si.flags.ignore_permissions = True
    si.flags.ignore_mandatory = True
    with _skip_due_date_validation():
        si.insert()
    frappe.db.commit()
    return si


def _stamp_si(si):
    try:
        if si.docstatus == 0:
            si.flags.ignore_permissions = True
            with _skip_due_date_validation():
                si.submit()
            frappe.db.commit()
            si.reload()

        comprobante = build_cfdi_from_sales_invoice(si)

        customer_rfc = frappe.db.get_value("Customer", si.customer, "mx_rfc")
        if customer_rfc == "XAXX010101000":
            from satcfdi.create.cfd.cfdi40 import InformacionGlobal
            m = int(str(si.posting_date).split("-")[1])
            y = int(str(si.posting_date).split("-")[0])
            comprobante["InformacionGlobal"] = InformacionGlobal(
                periodicidad="04", meses=f"{m:02d}", ano=y)

        signed = sign_cfdi(comprobante, COMPANY)
        pac = PACDispatcher.get_pac(COMPANY)
        result = pac.stamp(signed)

        if not result.success:
            fail(f"Stamp failed {si.name}: {result.error_message}")
            return None

        xml_fn = f"CFDI_{si.name}_{result.uuid}.xml"
        xml_file = save_cfdi_attachment(si, xml_fn, result.xml_stamped, "text/xml")
        for field, val in [
            ("mx_cfdi_uuid", result.uuid), ("mx_cfdi_status", "Timbrado"),
            ("mx_xml_file", xml_file.file_url),
            ("mx_cfdi_fecha_timbrado", result.fecha_timbrado),
            ("mx_no_certificado_sat", getattr(result, "no_certificado_sat", "")),
            ("mx_sello_sat", getattr(result, "sello_sat", "")),
        ]:
            si.db_set(field, val, update_modified=False)
        frappe.db.commit()
        try:
            create_cfdi_log(si, result, "I")
            frappe.db.commit()
        except Exception:
            pass
        time.sleep(STAMP_DELAY)
        return result.uuid
    except Exception as e:
        fail(f"Error stamping {si.name}: {e}")
        import traceback; traceback.print_exc()
        return None


def _create_pe(customer, inv_name, amount, posting_date, ref_no, accts):
    pe = frappe.get_doc({
        "doctype": "Payment Entry", "payment_type": "Receive",
        "company": COMPANY, "party_type": "Customer", "party": customer,
        "paid_from": accts["debtors"], "paid_to": accts["bank"],
        "paid_amount": amount, "received_amount": amount,
        "source_exchange_rate": 1.0, "target_exchange_rate": 1.0,
        "posting_date": posting_date, "reference_no": ref_no, "reference_date": posting_date,
        "mx_forma_pago": "03",
        "references": [{"reference_doctype": "Sales Invoice",
                         "reference_name": inv_name, "allocated_amount": amount}],
    })
    pe.flags.ignore_permissions = True
    pe.flags.ignore_mandatory = True
    with _skip_due_date_validation():
        pe.insert()
    frappe.db.commit()
    return pe


def _stamp_pe(pe):
    try:
        comprobante = build_payment_cfdi(pe)
        signed = sign_payment_cfdi(comprobante, COMPANY)
        pac = PACDispatcher.get_pac(COMPANY)
        result = pac.stamp(signed)
        if not result.success:
            fail(f"Payment stamp failed {pe.name}: {result.error_message}")
            return None
        xml_fn = f"CFDI_Pago_{pe.name}_{result.uuid}.xml"
        xml_file = save_cfdi_attachment(pe, xml_fn, result.xml_stamped, "text/xml")
        pe.db_set("mx_pago_uuid", result.uuid, update_modified=False)
        pe.db_set("mx_pago_status", "Timbrado", update_modified=False)
        pe.db_set("mx_pago_xml", xml_file.file_url, update_modified=False)
        frappe.db.commit()
        try:
            create_cfdi_log(pe, result, "P")
            frappe.db.commit()
        except Exception:
            pass
        time.sleep(STAMP_DELAY)
        return result.uuid
    except Exception as e:
        fail(f"Error stamping payment {pe.name}: {e}")
        import traceback; traceback.print_exc()
        return None


def _create_pi(supplier, desc, rate, posting_date, accts, iva_rate=16, ret_isr=0, ret_iva=0):
    taxes = []
    if iva_rate > 0:
        taxes.append({"charge_type": "On Net Total", "account_head": accts["iva"],
                       "description": f"IVA {iva_rate}%", "rate": iva_rate,
                       "add_deduct_tax": "Add", "category": "Total"})
    if ret_isr > 0:
        isr_acct = frappe.db.get_value("Account", {
            "company": COMPANY, "account_name": ["like", "%ISR%RET%"], "is_group": 0}, "name") or accts["iva"]
        taxes.append({"charge_type": "On Net Total", "account_head": isr_acct,
                       "description": f"Ret ISR {ret_isr}%", "rate": -ret_isr,
                       "add_deduct_tax": "Deduct", "category": "Total"})
    if ret_iva > 0:
        riva_acct = frappe.db.get_value("Account", {
            "company": COMPANY, "account_name": ["like", "%IVA%RET%"], "is_group": 0}, "name") or accts["iva"]
        taxes.append({"charge_type": "On Net Total", "account_head": riva_acct,
                       "description": f"Ret IVA {ret_iva}%", "rate": -ret_iva,
                       "add_deduct_tax": "Deduct", "category": "Total"})

    pi = frappe.get_doc({
        "doctype": "Purchase Invoice", "company": COMPANY, "supplier": supplier,
        "posting_date": posting_date, "due_date": add_days(posting_date, 30),
        "currency": "MXN", "conversion_rate": 1.0,
        "buying_price_list": "Standard Buying", "credit_to": accts["payable"],
        "items": [{"item_code": "CONS-TI-001", "item_name": desc, "qty": 1,
                    "rate": rate, "expense_account": accts["expense"]}],
        "taxes": taxes,
    })
    pi.flags.ignore_permissions = True
    pi.flags.ignore_mandatory = True
    with _skip_due_date_validation():
        pi.insert()
    frappe.db.commit()
    return pi


def _load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def _save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def run():
    print("\n" + "=" * 60)
    print("  FASE 2: ERPNext Transactions")
    print("=" * 60)
    frappe.flags.ignore_permissions = True

    accts = _get_accounts()
    print(f"  income={accts['income']}, iva={accts['iva']}, bank={accts['bank']}")
    if not accts["bank"]:
        fail("No bank account. Run Phase 1 first.")
        return

    state = _load_state()
    old_auto = _disable_auto_stamp()

    try:
        # 2.1 PUE
        section("2.1 Sales Invoices PUE (6)")
        for label, cust, items, date, uso, forma, iva in [
            ("S1", "Grupo Financiero Banamex SA de CV", [("CONS-TI-001", 40, 1500)], "2026-01-15", "G03", "03", 16),
            ("S2", "Grupo Financiero Banamex SA de CV", [("DEV-SW-001", 80, 2000)], "2026-02-10", "G03", "03", 16),
            ("S3", "Universidad Nacional UNAM", [("CAPACIT-001", 2, 12000)], "2026-01-20", "G03", "03", 16),
            ("S4", "Publico en General", [("SOPORTE-001", 1, 8000)], "2026-03-05", "S01", "01", 16),
            ("S5", "John Smith (Extranjero)", [("CONS-TI-001", 10, 1500)], "2026-02-20", "S01", "03", 0),
            ("S6", "Grupo Financiero Banamex SA de CV", [("AUDIT-TI-001", 1, 25000)], "2026-03-10", "G03", "03", 16),
        ]:
            if state.get("invoices", {}).get(label):
                skip(f"{label}: UUID={state['invoices'][label]['uuid'][:8]}...")
                continue
            si = _create_si(cust, items, date, "PUE", forma, uso, accts, iva_rate=iva)
            uuid = _stamp_si(si)
            if uuid:
                state.setdefault("invoices", {})[label] = {
                    "name": si.name, "uuid": uuid, "total": float(si.grand_total), "customer": cust, "type": "PUE"}
                ok(f"{label}: {si.name} UUID={uuid[:12]}... (${si.grand_total:,.2f})")
            else:
                si.reload()
                state.setdefault("invoices", {})[label] = {
                    "name": si.name, "uuid": "", "total": float(si.grand_total or 0), "customer": cust, "type": "PUE"}
                ok(f"{label}: {si.name} (stamp pending)")
        _save_state(state)

        # 2.2 PPD
        section("2.2 Sales Invoices PPD (3)")
        for label, cust, items, date, uso, due in [
            ("P1", "Soluciones Cloud MX SA de CV", [("PROYECTO-001", 3, 15000)], "2026-02-01", "G03", 30),
            ("P2", "Soluciones Cloud MX SA de CV", [("LICENCIA-001", 10, 5000), ("SOPORTE-001", 6, 8000)], "2026-02-15", "G03", 60),
            ("P3", "Universidad Nacional UNAM", [("DEV-SW-001", 120, 2000)], "2026-01-25", "G03", 45),
        ]:
            if state.get("invoices", {}).get(label):
                skip(f"{label}: UUID={state['invoices'][label].get('uuid','?')[:8]}...")
                continue
            si = _create_si(cust, items, date, "PPD", "99", uso, accts, due_days=due)
            uuid = _stamp_si(si)
            if uuid:
                state.setdefault("invoices", {})[label] = {
                    "name": si.name, "uuid": uuid, "total": float(si.grand_total), "customer": cust, "type": "PPD"}
                ok(f"{label}: {si.name} UUID={uuid[:12]}... (${si.grand_total:,.2f})")
            else:
                state.setdefault("invoices", {})[label] = {
                    "name": si.name, "uuid": "", "total": float(si.grand_total), "customer": cust, "type": "PPD"}
        _save_state(state)

        # 2.3 Payments
        section("2.3 Payment Entries (4)")
        for label, inv_label, pct, date in [
            ("PE1", "P1", 1.0, "2026-02-16"),
            ("PE2a", "P2", 0.5, "2026-03-17"),
            ("PE2b", "P2", 0.5, "2026-04-15"),
            ("PE3a", "P3", 0.4, "2026-02-09"),
        ]:
            if state.get("payments", {}).get(label):
                skip(f"{label}: already done")
                continue
            inv = state.get("invoices", {}).get(inv_label)
            if not inv:
                fail(f"{label}: Invoice {inv_label} not in state")
                continue
            amount = round(inv["total"] * pct, 2)
            pe = _create_pe(inv["customer"], inv["name"], amount, date, f"SEED-{label}", accts)
            uuid = _stamp_pe(pe)
            if uuid:
                state.setdefault("payments", {})[label] = {
                    "name": pe.name, "uuid": uuid, "amount": amount,
                    "invoice": inv_label, "invoice_uuid": inv.get("uuid", "")}
                ok(f"{label}: {pe.name} UUID={uuid[:12]}... (${amount:,.2f})")
            else:
                state.setdefault("payments", {})[label] = {
                    "name": pe.name, "uuid": "", "amount": amount, "invoice": inv_label}
        _save_state(state)

        # 2.4 Purchase Invoices
        section("2.4 Purchase Invoices (8)")
        for label, sup, desc, rate, date, iva, isr, riva in [
            ("PI1", "Amazon Web Services Mexico", "Hosting AWS Enero", 15000, "2026-01-31", 16, 0, 0),
            ("PI2", "Deloitte Mexico SC", "Consultoria Legal", 30000, "2026-01-20", 16, 10, 10.6667),
            ("PI3", "Telmex SA de CV", "Internet Fibra Enero", 2500, "2026-01-31", 16, 0, 0),
            ("PI4", "Microsoft Corporation", "Office 365 Licenses", 8000, "2026-01-15", 0, 0, 0),
            ("PI5", "Papeleria LUMEN SA de CV", "Insumos Oficina", 3500, "2026-02-10", 16, 0, 0),
            ("PI6", "Amazon Web Services Mexico", "Hosting AWS Febrero", 15000, "2026-02-28", 16, 0, 0),
            ("PI7", "Telmex SA de CV", "Internet Fibra Febrero", 2500, "2026-02-28", 16, 0, 0),
            ("PI8", "Deloitte Mexico SC", "Auditoria Fiscal", 50000, "2026-03-15", 16, 10, 10.6667),
        ]:
            if state.get("purchase_invoices", {}).get(label):
                skip(f"{label}: exists")
                continue
            pi = _create_pi(sup, desc, rate, date, accts, iva_rate=iva, ret_isr=isr, ret_iva=riva)
            pi.flags.ignore_permissions = True
            with _skip_due_date_validation():
                pi.submit()
            frappe.db.commit()
            state.setdefault("purchase_invoices", {})[label] = {
                "name": pi.name, "total": float(pi.grand_total), "supplier": sup}
            ok(f"{label}: {pi.name} — {desc} (${pi.grand_total:,.2f})")
        _save_state(state)

    finally:
        _restore_auto_stamp(old_auto)

    print(f"\n{G}Fase 2 completa.{R}")
    print(f"  SI: {len(state.get('invoices', {}))}, PE: {len(state.get('payments', {}))}, PI: {len(state.get('purchase_invoices', {}))}")
