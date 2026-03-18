"""
DIOT Preview Report — Reporte de previsualización antes de generar el TXT.

Script Report que muestra el desglose por proveedor de los importes
que se incluirán en la DIOT, clasificados por tasa de IVA.

Filtros requeridos:
    company   — Empresa
    from_date — Inicio del periodo
    to_date   — Fin del periodo
"""
import frappe
from frappe import _
from frappe.utils import flt

from erpnext_mexico.diot.diot_generator import _classify_taxes_from_list, _init_supplier_entry


def execute(filters=None):
    """Entry point for Frappe Script Report."""
    columns = get_columns()
    data = get_data(filters or {})
    return columns, data


def get_columns() -> list:
    return [
        {
            "label": _("Proveedor"),
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 220,
        },
        {
            "label": _("RFC"),
            "fieldname": "rfc",
            "fieldtype": "Data",
            "width": 140,
        },
        {
            "label": _("Tipo Tercero"),
            "fieldname": "tipo_tercero",
            "fieldtype": "Data",
            "width": 110,
        },
        {
            "label": _("Tipo Operación"),
            "fieldname": "tipo_operacion",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": _("Base IVA 16%"),
            "fieldname": "valor_16",
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "label": _("Base IVA 8%"),
            "fieldname": "valor_8",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("Base IVA 0%"),
            "fieldname": "valor_0",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("Exentos"),
            "fieldname": "valor_exento",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("IVA Retenido"),
            "fieldname": "iva_retenido",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("Total Compras"),
            "fieldname": "total_compras",
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "label": _("No. Facturas"),
            "fieldname": "invoice_count",
            "fieldtype": "Int",
            "width": 100,
        },
    ]


def get_data(filters: dict) -> list:
    company = filters.get("company")
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")

    if not (company and from_date and to_date):
        return []

    # Fetch submitted Purchase Invoices in the period
    invoices = frappe.get_all(
        "Purchase Invoice",
        filters={
            "company": company,
            "docstatus": 1,
            "posting_date": ["between", [from_date, to_date]],
        },
        fields=["name", "supplier", "net_total", "grand_total", "posting_date"],
    )

    if not invoices:
        return []

    # Batch load taxes for all invoices at once (avoids N+1 queries)
    inv_names = [inv.name for inv in invoices]
    all_taxes: dict = {}
    if inv_names:
        taxes_data = frappe.get_all(
            "Purchase Taxes and Charges",
            filters={"parent": ["in", inv_names]},
            fields=["parent", "charge_type", "rate", "tax_amount", "description", "account_head"],
        )
        for tax in taxes_data:
            all_taxes.setdefault(tax.parent, []).append(tax)

    # Aggregate by supplier — reuse generator logic for consistency
    supplier_totals: dict = {}

    for inv in invoices:
        supplier = inv.supplier
        if not supplier:
            continue

        if supplier not in supplier_totals:
            entry = _init_supplier_entry(supplier)
            entry["invoice_count"] = 0
            entry["total_compras"] = 0.0
            supplier_totals[supplier] = entry

        tax_detail = _classify_taxes_from_list(all_taxes.get(inv.name, []), float(inv.net_total or 0))

        supplier_totals[supplier]["valor_16"] += tax_detail["base_16"]
        supplier_totals[supplier]["valor_8"] += tax_detail["base_8"]
        supplier_totals[supplier]["valor_0"] += tax_detail["base_0"]
        supplier_totals[supplier]["valor_exento"] += tax_detail["base_exento"]
        supplier_totals[supplier]["iva_retenido"] += tax_detail["iva_retenido"]
        supplier_totals[supplier]["total_compras"] += flt(inv.grand_total)
        supplier_totals[supplier]["invoice_count"] += 1

    # Build report rows sorted by RFC
    rows = []
    for data in sorted(supplier_totals.values(), key=lambda d: d.get("rfc", "")):
        rows.append({
            "supplier": data["supplier"],
            "rfc": data.get("rfc", ""),
            "tipo_tercero": data.get("tipo_tercero", "Nacional"),
            "tipo_operacion": data.get("tipo_operacion", "Otros"),
            "valor_16": flt(data.get("valor_16", 0), 2),
            "valor_8": flt(data.get("valor_8", 0), 2),
            "valor_0": flt(data.get("valor_0", 0), 2),
            "valor_exento": flt(data.get("valor_exento", 0), 2),
            "iva_retenido": flt(data.get("iva_retenido", 0), 2),
            "total_compras": flt(data.get("total_compras", 0), 2),
            "invoice_count": data.get("invoice_count", 0),
        })

    # Summary row
    if rows:
        rows.append({
            "supplier": f"<b>{_('TOTAL')}</b>",
            "rfc": "",
            "tipo_tercero": "",
            "tipo_operacion": "",
            "valor_16": sum(r["valor_16"] for r in rows),
            "valor_8": sum(r["valor_8"] for r in rows),
            "valor_0": sum(r["valor_0"] for r in rows),
            "valor_exento": sum(r["valor_exento"] for r in rows),
            "iva_retenido": sum(r["iva_retenido"] for r in rows),
            "total_compras": sum(r["total_compras"] for r in rows),
            "invoice_count": sum(r["invoice_count"] for r in rows),
        })

    return rows
