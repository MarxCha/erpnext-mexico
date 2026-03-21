# -*- coding: utf-8 -*-
"""Re-stamp invoices and payments that failed initial stamping."""
import json
import os
import time
import frappe
from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice, sign_cfdi
from erpnext_mexico.cfdi.payment_builder import build_payment_cfdi, sign_payment_cfdi
from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
from erpnext_mexico.cfdi.cfdi_helpers import save_cfdi_attachment, create_cfdi_log
from erpnext_mexico.seed.constants import COMPANY

STATE_FILE = "/tmp/seed_state.json"
G = "\033[92m"
RED = "\033[91m"
Y = "\033[93m"
R = "\033[0m"
ITEMS_MAP = {
    "CONS-TI-001": ("84111506", "E48"), "DEV-SW-001": ("81112100", "E48"),
    "SOPORTE-001": ("81112002", "E48"), "HOSTING-001": ("81112300", "E48"),
    "CAPACIT-001": ("86101700", "E48"), "LICENCIA-001": ("43231500", "E48"),
    "AUDIT-TI-001": ("84111507", "E48"), "PROYECTO-001": ("84111502", "E48"),
}


def _fix_si_items(si):
    """Ensure SI Item rows have SAT codes."""
    for item in si.items:
        if not item.mx_clave_prod_serv:
            c, u = ITEMS_MAP.get(item.item_code, (None, None))
            if c:
                frappe.db.set_value("Sales Invoice Item", item.name,
                                    "mx_clave_prod_serv", c, update_modified=False)
                frappe.db.set_value("Sales Invoice Item", item.name,
                                    "mx_clave_unidad", u, update_modified=False)
    frappe.db.commit()
    si.reload()


def _stamp_invoice(si):
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
        return None, result.error_message

    xml_fn = f"CFDI_{si.name}_{result.uuid}.xml"
    xml_file = save_cfdi_attachment(si, xml_fn, result.xml_stamped, "text/xml")
    si.db_set("mx_cfdi_uuid", result.uuid, update_modified=False)
    si.db_set("mx_cfdi_status", "Timbrado", update_modified=False)
    si.db_set("mx_xml_file", xml_file.file_url, update_modified=False)
    si.db_set("mx_cfdi_fecha_timbrado", result.fecha_timbrado, update_modified=False)
    frappe.db.commit()
    try:
        create_cfdi_log(si, result, "I")
        frappe.db.commit()
    except Exception:
        pass
    return result.uuid, None


def _stamp_payment(pe):
    comprobante = build_payment_cfdi(pe)
    signed = sign_payment_cfdi(comprobante, COMPANY)
    pac = PACDispatcher.get_pac(COMPANY)
    result = pac.stamp(signed)
    if not result.success:
        return None, result.error_message

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
    return result.uuid, None


def run():
    if not os.path.exists(STATE_FILE):
        print("No state file found. Run transactions first.")
        return

    with open(STATE_FILE) as f:
        state = json.load(f)

    print(f"\n{'=' * 60}\n  RE-STAMP: Sales Invoices\n{'=' * 60}")
    for label, inv in state.get("invoices", {}).items():
        if inv.get("uuid"):
            print(f"  {Y}[SKIP]{R} {label}: UUID={inv['uuid'][:12]}...")
            continue
        si = frappe.get_doc("Sales Invoice", inv["name"])
        _fix_si_items(si)
        try:
            uuid, err = _stamp_invoice(si)
            if uuid:
                inv["uuid"] = uuid
                inv["total"] = float(si.grand_total)
                print(f"  {G}[OK]{R} {label}: UUID={uuid[:12]}...")
                time.sleep(2)
            else:
                print(f"  {RED}[FAIL]{R} {label}: {err}")
        except Exception as e:
            print(f"  {RED}[FAIL]{R} {label}: {e}")

    # Save before payments
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

    print(f"\n{'=' * 60}\n  RE-STAMP: Payment Entries\n{'=' * 60}")
    for label, pay in state.get("payments", {}).items():
        if pay.get("uuid"):
            print(f"  {Y}[SKIP]{R} {label}")
            continue
        inv_label = pay.get("invoice")
        inv = state.get("invoices", {}).get(inv_label, {})
        if not inv.get("uuid"):
            print(f"  {Y}[SKIP]{R} {label}: invoice {inv_label} not stamped yet")
            continue
        pe = frappe.get_doc("Payment Entry", pay["name"])
        try:
            uuid, err = _stamp_payment(pe)
            if uuid:
                pay["uuid"] = uuid
                pay["invoice_uuid"] = inv["uuid"]
                print(f"  {G}[OK]{R} {label}: UUID={uuid[:12]}...")
                time.sleep(2)
            else:
                print(f"  {RED}[FAIL]{R} {label}: {err}")
        except Exception as e:
            print(f"  {RED}[FAIL]{R} {label}: {e}")

    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

    stamped_si = sum(1 for v in state.get("invoices", {}).values() if v.get("uuid"))
    stamped_pe = sum(1 for v in state.get("payments", {}).values() if v.get("uuid"))
    total_si = len(state.get("invoices", {}))
    total_pe = len(state.get("payments", {}))
    print(f"\n  SI: {stamped_si}/{total_si} stamped")
    print(f"  PE: {stamped_pe}/{total_pe} stamped")
