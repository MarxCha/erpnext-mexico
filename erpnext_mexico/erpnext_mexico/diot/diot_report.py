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

from erpnext_mexico.diot.diot_generator import _classify_taxes, _init_supplier_entry


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
            "fieldname": "base_16",
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "label": _("Base IVA 8%"),
            "fieldname": "base_8",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("Base IVA 0%"),
            "fieldname": "base_0",
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "label": _("Exentos"),
            "fieldname": "exento",
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

        inv_doc = frappe.get_doc("Purchase Invoice", inv.name)
        tax_detail = _classify_taxes(inv_doc)

        supplier_totals[supplier]["base_16"] = (
            supplier_totals[supplier].get("base_16", 0) + tax_detail["base_16"]
        )
        supplier_totals[supplier]["base_8"] = (
            supplier_totals[supplier].get("base_8", 0) + tax_detail["base_8"]
        )
        supplier_totals[supplier]["base_0"] = (
            supplier_totals[supplier].get("base_0", 0) + tax_detail["base_0"]
        )
        supplier_totals[supplier]["exento"] = (
            supplier_totals[supplier].get("exento", 0) + tax_detail["base_exento"]
        )
        supplier_totals[supplier]["iva_retenido"] = (
            supplier_totals[supplier].get("iva_retenido", 0) + tax_detail["iva_retenido"]
        )
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
            "base_16": flt(data.get("base_16", 0), 2),
            "base_8": flt(data.get("base_8", 0), 2),
            "base_0": flt(data.get("base_0", 0), 2),
            "exento": flt(data.get("exento", 0), 2),
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
            "base_16": sum(r["base_16"] for r in rows),
            "base_8": sum(r["base_8"] for r in rows),
            "base_0": sum(r["base_0"] for r in rows),
            "exento": sum(r["exento"] for r in rows),
            "iva_retenido": sum(r["iva_retenido"] for r in rows),
            "total_compras": sum(r["total_compras"] for r in rows),
            "invoice_count": sum(r["invoice_count"] for r in rows),
        })

    return rows
