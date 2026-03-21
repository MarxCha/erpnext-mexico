# -*- coding: utf-8 -*-
"""
Stress Test ERP — Replica escenarios reales de CFDI-Motor en ERPNext.

Montos y estructuras copiados de facturas vigentes en CFDI-Motor (PostgreSQL).
Timbrado real vía Finkok sandbox con RFC EKU9003173C9.

Uso:
  bench --site erpnext-mexico.localhost execute erpnext_mexico.seed.stress_test.run
"""
import json
import os
import time
from contextlib import contextmanager
from decimal import Decimal

import frappe
from frappe.utils import add_days

from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice, sign_cfdi
from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
from erpnext_mexico.cfdi.cfdi_helpers import save_cfdi_attachment, create_cfdi_log
from erpnext_mexico.seed.constants import COMPANY

G = "\033[92m"
Y = "\033[93m"
RED = "\033[91m"
R = "\033[0m"
STAMP_DELAY = 2
STATE_FILE = "/tmp/stress_test_state.json"

# ── Datos reales de CFDI-Motor (facturas vigentes EKU9003173C9) ──

SALES_INVOICES = [
    # (label, subtotal, metodo_pago, posting_date, item_code, original_receptor)
    ("R1", 24255.39, "PUE", "2024-12-24", "CONS-TI-001", "Grupo Financiero Banamex"),
    ("R2", 10662.63, "PUE", "2024-12-17", "DEV-SW-001", "Amazon Web Services"),
    ("R3", 45398.37, "PPD", "2024-12-17", "PROYECTO-001", "Publico en General"),
    ("R4", 36363.30, "PUE", "2024-12-12", "DEV-SW-001", "Amazon Web Services"),
    ("R5", 4980.65, "PUE", "2024-12-10", "SOPORTE-001", "Amazon Web Services"),
    ("R6", 45735.69, "PUE", "2024-12-05", "AUDIT-TI-001", "UNAM"),
    ("R7", 14791.56, "PUE", "2024-12-04", "HOSTING-001", "Amazon Web Services"),
    ("R8", 16365.10, "PUE", "2024-12-02", "CONS-TI-001", "Publico en General"),
    ("R9", 6792.48, "PUE", "2024-11-29", "SOPORTE-001", "Telmex"),
    ("R10", 35605.35, "PUE", "2024-11-28", "DEV-SW-001", "Telmex"),
]

PURCHASE_INVOICES = [
    # (label, supplier, subtotal, posting_date, description)
    ("P1", "Amazon Web Services Mexico", 4261.21, "2024-12-24", "Hosting AWS Dic"),
    ("P2", "Telmex SA de CV", 3641.42, "2024-12-20", "Internet Dic"),
    ("P3", "Deloitte Mexico SC", 3156.67, "2024-12-19", "Consultoria Dic"),
    ("P4", "Papeleria LUMEN SA de CV", 8642.18, "2024-12-11", "Insumos Oficina Dic"),
    ("P5", "Telmex SA de CV", 16848.84, "2024-12-11", "Infraestructura Telecom"),
    ("P6", "Costco de Mexico SA de CV", 2521.41, "2024-11-16", "Insumos Nov"),
    ("P7", "Telmex SA de CV", 3562.60, "2024-11-14", "Internet Nov"),
    ("P8", "Deloitte Mexico SC", 2454.90, "2024-11-06", "Consultoria Nov"),
]

SAT_CODES = {
    "CONS-TI-001": "84111506", "DEV-SW-001": "81112100", "SOPORTE-001": "81112002",
    "HOSTING-001": "81112300", "CAPACIT-001": "86101700", "LICENCIA-001": "43231500",
    "AUDIT-TI-001": "84111507", "PROYECTO-001": "84111502",
}


def ok(msg):
    print(f"  {G}[OK]{R} {msg}")

def fail(msg):
    print(f"  {RED}[FAIL]{R} {msg}")

def skip(msg):
    print(f"  {Y}[SKIP]{R} {msg}")

def section(title):
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")


@contextmanager
def _skip_due_date_validation():
    from erpnext.accounts import party as _p
    _orig = _p.validate_due_date
    _p.validate_due_date = lambda *a, **kw: None
    try:
        yield
    finally:
        _p.validate_due_date = _orig


def _get_accounts():
    return {
        "income": frappe.db.get_value("Account", {"company": COMPANY, "account_name": "VENTAS NACIONALES", "is_group": 0}, "name"),
        "iva": frappe.db.get_value("Account", {"company": COMPANY, "account_name": ["like", "%IVA%"], "is_group": 0}, "name"),
        "debtors": frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Receivable", "account_name": "CUENTAS POR COBRAR CLIENTES", "is_group": 0}, "name") or frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Receivable", "is_group": 0}, "name"),
        "bank": frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Bank", "is_group": 0}, "name"),
        "expense": frappe.db.get_value("Account", {"company": COMPANY, "account_name": "COSTO DE VENTAS", "is_group": 0}, "name") or frappe.db.get_value("Account", {"company": COMPANY, "root_type": "Expense", "is_group": 0}, "name"),
        "payable": frappe.db.get_value("Account", {"company": COMPANY, "account_name": "CUENTAS POR PAGAR PROVEEDORES", "is_group": 0}, "name") or frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Payable", "is_group": 0}, "name"),
    }


def _ensure_costco():
    """Add Costco de Mexico if missing."""
    name = "Costco de Mexico SA de CV"
    if frappe.db.exists("Supplier", name):
        return
    doc = frappe.get_doc({
        "doctype": "Supplier", "supplier_name": name,
        "supplier_group": "Services", "supplier_type": "Company",
    })
    doc.flags.ignore_permissions = True
    doc.flags.ignore_mandatory = True
    doc.insert()
    frappe.db.commit()
    for f, v in {"mx_rfc": "CME910715UB9", "mx_tipo_tercero_diot": "Nacional", "mx_tipo_operacion_diot": "Otros"}.items():
        frappe.db.set_value("Supplier", doc.name, f, v, update_modified=False)
    frappe.db.commit()
    ok(f"Proveedor agregado: {name} (CME910715UB9)")


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


def _stamp_invoice(si):
    """Build, sign, stamp a submitted Sales Invoice. Returns UUID or None."""
    try:
        comprobante = build_cfdi_from_sales_invoice(si)
        # InformacionGlobal for XAXX010101000
        customer_rfc = frappe.db.get_value("Customer", si.customer, "mx_rfc")
        if customer_rfc == "XAXX010101000":
            from satcfdi.create.cfd.cfdi40 import InformacionGlobal
            m = int(str(si.posting_date).split("-")[1])
            y = int(str(si.posting_date).split("-")[0])
            comprobante["InformacionGlobal"] = InformacionGlobal(periodicidad="04", meses=f"{m:02d}", ano=y)

        signed = sign_cfdi(comprobante, COMPANY)
        pac = PACDispatcher.get_pac(COMPANY)
        result = pac.stamp(signed)
        if not result.success:
            return None, result.error_message

        xml_fn = f"CFDI_{si.name}_{result.uuid}.xml"
        xml_file = save_cfdi_attachment(si, xml_fn, result.xml_stamped, "text/xml")
        for f, v in [("mx_cfdi_uuid", result.uuid), ("mx_cfdi_status", "Timbrado"),
                      ("mx_xml_file", xml_file.file_url), ("mx_cfdi_fecha_timbrado", result.fecha_timbrado)]:
            si.db_set(f, v, update_modified=False)
        frappe.db.commit()
        try:
            create_cfdi_log(si, result, "I")
            frappe.db.commit()
        except Exception:
            pass
        time.sleep(STAMP_DELAY)
        return result.uuid, None
    except Exception as e:
        return None, str(e)[:200]


def phase_a_sales(accts, state):
    """Fase A: 10 Sales Invoices replicando datos reales de CFDI-Motor."""
    section("FASE A: 10 Sales Invoices (datos reales CFDI-Motor)")
    old_auto = _disable_auto_stamp()

    try:
        for label, subtotal, metodo, date, item_code, orig_receptor in SALES_INVOICES:
            if state.get("sales", {}).get(label, {}).get("uuid"):
                skip(f"{label}: ya timbrada")
                continue

            # Calculate qty and rate to match subtotal exactly
            # Use qty=1 and rate=subtotal for exact match
            forma = "03" if metodo == "PUE" else "99"
            si = frappe.get_doc({
                "doctype": "Sales Invoice", "company": COMPANY,
                "customer": "Publico en General",  # All go through Publico en General for sandbox
                "posting_date": date, "due_date": add_days(date, 30),
                "currency": "MXN", "conversion_rate": 1.0,
                "selling_price_list": "Standard Selling", "debit_to": accts["debtors"],
                "mx_uso_cfdi": "S01", "mx_metodo_pago": metodo,
                "mx_forma_pago": forma, "mx_exportacion": "01",
                "items": [{
                    "item_code": item_code, "qty": 1, "rate": subtotal,
                    "income_account": accts["income"],
                    "mx_clave_prod_serv": SAT_CODES.get(item_code, "84111506"),
                    "mx_clave_unidad": "E48",
                }],
                "taxes": [{"charge_type": "On Net Total", "account_head": accts["iva"],
                           "description": "IVA 16%", "rate": 16}],
            })
            si.flags.ignore_permissions = True
            si.flags.ignore_mandatory = True
            with _skip_due_date_validation():
                si.insert()
                si.submit()
            frappe.db.commit()
            si.reload()

            # Stamp
            uuid, err = _stamp_invoice(si)
            entry = {"name": si.name, "subtotal": float(si.net_total), "total": float(si.grand_total),
                     "metodo": metodo, "orig_receptor": orig_receptor, "uuid": uuid or ""}
            state.setdefault("sales", {})[label] = entry

            if uuid:
                ok(f"{label}: {si.name} UUID={uuid[:12]}... ${si.grand_total:,.2f} ({orig_receptor})")
            else:
                fail(f"{label}: {si.name} ${si.grand_total:,.2f} — {err}")
    finally:
        _restore_auto_stamp(old_auto)


def phase_b_purchases(accts, state):
    """Fase B: 8 Purchase Invoices replicando datos reales de CFDI-Motor."""
    section("FASE B: 8 Purchase Invoices (datos reales CFDI-Motor)")

    for label, supplier, subtotal, date, desc in PURCHASE_INVOICES:
        if state.get("purchases", {}).get(label):
            skip(f"{label}: ya existe")
            continue

        pi = frappe.get_doc({
            "doctype": "Purchase Invoice", "company": COMPANY,
            "supplier": supplier, "posting_date": date,
            "due_date": add_days(date, 30), "currency": "MXN", "conversion_rate": 1.0,
            "buying_price_list": "Standard Buying", "credit_to": accts["payable"],
            "items": [{"item_code": "CONS-TI-001", "item_name": desc, "qty": 1,
                       "rate": subtotal, "expense_account": accts["expense"]}],
            "taxes": [{"charge_type": "On Net Total", "account_head": accts["iva"],
                       "description": "IVA 16%", "rate": 16, "add_deduct_tax": "Add", "category": "Total"}],
        })
        pi.flags.ignore_permissions = True
        pi.flags.ignore_mandatory = True
        with _skip_due_date_validation():
            pi.insert()
            pi.submit()
        frappe.db.commit()

        state.setdefault("purchases", {})[label] = {
            "name": pi.name, "supplier": supplier, "total": float(pi.grand_total)}
        ok(f"{label}: {pi.name} — {desc} (${pi.grand_total:,.2f})")


def phase_c_payments(accts, state):
    """Fase C: Payment Entry para factura PPD (R3)."""
    section("FASE C: Payment Entry contra PPD")

    r3 = state.get("sales", {}).get("R3", {})
    if not r3.get("name"):
        fail("R3 no existe en state — no se puede crear pago")
        return

    label = "CP1"
    if state.get("payments", {}).get(label):
        skip(f"{label}: ya existe")
        return

    from erpnext_mexico.cfdi.payment_builder import build_payment_cfdi, sign_payment_cfdi

    # Get actual outstanding amount from the invoice
    si_doc = frappe.get_doc("Sales Invoice", r3["name"])
    outstanding = float(si_doc.outstanding_amount)
    if outstanding <= 0:
        skip(f"{label}: Factura R3 ya pagada (outstanding={outstanding})")
        return

    pe = frappe.get_doc({
        "doctype": "Payment Entry", "payment_type": "Receive",
        "company": COMPANY, "party_type": "Customer", "party": "Publico en General",
        "paid_from": accts["debtors"], "paid_to": accts["bank"],
        "paid_amount": outstanding, "received_amount": outstanding,
        "source_exchange_rate": 1.0, "target_exchange_rate": 1.0,
        "posting_date": "2025-01-15", "reference_no": f"STRESS-{label}",
        "reference_date": "2025-01-15", "mx_forma_pago": "03",
        "references": [{"reference_doctype": "Sales Invoice",
                        "reference_name": r3["name"], "allocated_amount": outstanding}],
    })
    pe.flags.ignore_permissions = True
    pe.flags.ignore_mandatory = True
    with _skip_due_date_validation():
        pe.insert()
    frappe.db.commit()

    # Stamp complemento de pagos
    uuid = None
    if r3.get("uuid"):
        try:
            comprobante = build_payment_cfdi(pe)
            signed = sign_payment_cfdi(comprobante, COMPANY)
            pac = PACDispatcher.get_pac(COMPANY)
            result = pac.stamp(signed)
            if result.success:
                xml_fn = f"CFDI_Pago_{pe.name}_{result.uuid}.xml"
                xml_file = save_cfdi_attachment(pe, xml_fn, result.xml_stamped, "text/xml")
                pe.db_set("mx_pago_uuid", result.uuid, update_modified=False)
                pe.db_set("mx_pago_status", "Timbrado", update_modified=False)
                pe.db_set("mx_pago_xml", xml_file.file_url, update_modified=False)
                frappe.db.commit()
                uuid = result.uuid
                try:
                    create_cfdi_log(pe, result, "P")
                    frappe.db.commit()
                except Exception:
                    pass
                time.sleep(STAMP_DELAY)
        except Exception as e:
            fail(f"Complemento Pagos: {str(e)[:150]}")

    state.setdefault("payments", {})[label] = {
        "name": pe.name, "amount": r3["total"], "uuid": uuid or "", "invoice": "R3"}

    if uuid:
        ok(f"{label}: {pe.name} UUID={uuid[:12]}... ${r3['total']:,.2f} (contra R3)")
    else:
        ok(f"{label}: {pe.name} ${r3['total']:,.2f} (timbrado pendiente)")


def phase_d_verify(state):
    """Fase D: Verificación."""
    section("FASE D: Verificacion")

    si_timbradas = sum(1 for v in state.get("sales", {}).values() if v.get("uuid"))
    si_total = len(state.get("sales", {}))
    pi_total = len(state.get("purchases", {}))
    pe_total = len(state.get("payments", {}))

    print(f"  Sales Invoices timbradas: {si_timbradas}/{si_total}")
    print(f"  Purchase Invoices: {pi_total}/8")
    print(f"  Payment Entries: {pe_total}")

    # Verify totals match CFDI-Motor
    total_ventas = sum(v.get("total", 0) for v in state.get("sales", {}).values())
    total_compras = sum(v.get("total", 0) for v in state.get("purchases", {}).values())
    print(f"\n  Total Ventas: ${total_ventas:,.2f}")
    print(f"  Total Compras: ${total_compras:,.2f}")

    # Compare with CFDI-Motor originals
    cfdi_motor_ventas = sum(s[1] * 1.16 for s in SALES_INVOICES)
    cfdi_motor_compras = sum(p[2] * 1.16 for p in PURCHASE_INVOICES)
    print(f"\n  CFDI-Motor Ventas (esperado): ${cfdi_motor_ventas:,.2f}")
    print(f"  CFDI-Motor Compras (esperado): ${cfdi_motor_compras:,.2f}")

    diff_v = abs(total_ventas - cfdi_motor_ventas)
    diff_c = abs(total_compras - cfdi_motor_compras)
    if diff_v < 10 and diff_c < 10:
        ok(f"Montos coinciden con CFDI-Motor (diff ventas=${diff_v:.2f}, compras=${diff_c:.2f})")
    else:
        fail(f"Diferencia significativa: ventas=${diff_v:.2f}, compras=${diff_c:.2f}")


def _load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def _save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def run():
    print("\n" + "#" * 60)
    print("  STRESS TEST ERP — Escenarios Reales CFDI-Motor")
    print("#" * 60)
    frappe.flags.ignore_permissions = True

    _ensure_costco()
    accts = _get_accounts()
    state = _load_state()

    phase_a_sales(accts, state)
    _save_state(state)

    phase_b_purchases(accts, state)
    _save_state(state)

    phase_c_payments(accts, state)
    _save_state(state)

    phase_d_verify(state)

    print(f"\n{G}Stress test completo.{R}")
    print(f"  State: {STATE_FILE}")
