"""
Generador de DIOT 2025 — Declaración Informativa de Operaciones con Terceros.
Genera archivo TXT pipe-delimited para carga en portal del SAT.

Formato: 24 campos separados por pipe (|)
Referencia: Anexo 1 de la Resolución Miscelánea Fiscal 2025
Campo 1:  Tipo de tercero (04=Nacional, 05=Extranjero, 15=Global)
Campo 2:  Tipo de operación (85=Servicios prof., 06=Arrendamiento, 03=Otros)
Campo 3:  RFC del proveedor (13 chars para moral, 12 para física — left-justified, space-padded to 13)
Campo 4:  Número de Identificación Tributaria (extranjero)
Campo 5:  Nombre o razón social (solo extranjero)
Campo 6:  País de residencia (solo extranjero)
Campo 7:  Nacionalidad (solo extranjero)
Campos 8-20: Importes (enteros, sin decimales)
Campos 21-24: Vacíos (padding)
"""
import frappe
from frappe import _
from frappe.utils import getdate, get_last_day


# ──────────────────────────────────────────────────────────────────────────────
# Constantes de formato
# ──────────────────────────────────────────────────────────────────────────────

TIPO_TERCERO_MAP = {
    "Nacional": "04",
    "Extranjero": "05",
    "Global": "15",
}

# Tipo de operación predeterminado — se puede extender con campo mx_tipo_operacion_diot
TIPO_OPERACION_DEFAULT = "03"  # Otros
TIPO_OPERACION_MAP = {
    "Servicios Profesionales": "85",
    "Arrendamiento": "06",
    "Otros": "03",
}

# Número total de campos en cada línea DIOT
DIOT_FIELD_COUNT = 24

# Longitud estándar de RFC (personas morales 12 + dígito verificador = 13)
RFC_FIELD_WIDTH = 13


# ──────────────────────────────────────────────────────────────────────────────
# API pública
# ──────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def generate_diot(company: str, month: int, year: int) -> dict:
    """
    Generate DIOT TXT content for a given company/month/year.

    Args:
        company: Company name (docname)
        month:   Month number 1–12
        year:    Four-digit year (e.g. 2026)

    Returns:
        dict with keys:
            filename       – suggested filename for download
            content        – full TXT content (pipe-delimited lines)
            supplier_count – number of unique suppliers included
            total_lines    – number of data lines generated
    """
    month = int(month)
    year = int(year)

    if not 1 <= month <= 12:
        frappe.throw(_("Mes inválido: debe estar entre 1 y 12"))
    if year < 2000 or year > 2099:
        frappe.throw(_("Año inválido"))

    from_date = getdate(f"{year}-{month:02d}-01")
    to_date = get_last_day(from_date)

    # Fetch all submitted Purchase Invoices in the period
    invoices = frappe.get_all(
        "Purchase Invoice",
        filters={
            "company": company,
            "docstatus": 1,
            "posting_date": ["between", [from_date, to_date]],
        },
        fields=[
            "name",
            "supplier",
            "net_total",
            "grand_total",
            "total_taxes_and_charges",
            "posting_date",
        ],
    )

    if not invoices:
        frappe.msgprint(
            _("No hay facturas de compra en el periodo {0}/{1}").format(month, year)
        )
        return {"filename": "", "content": "", "supplier_count": 0, "total_lines": 0}

    supplier_totals = _aggregate_by_supplier(invoices)

    lines = [_build_diot_line(data) for data in supplier_totals.values()]
    content = "\n".join(lines)
    filename = f"DIOT_{_safe_name(company)}_{year}{month:02d}.txt"

    return {
        "filename": filename,
        "content": content,
        "supplier_count": len(supplier_totals),
        "total_lines": len(lines),
    }


@frappe.whitelist()
def download_diot(company: str, month: int, year: int):
    """
    Generate DIOT and stream as a file download response.

    Raises frappe.throw if no data exists for the period.
    """
    result = generate_diot(company, int(month), int(year))
    if not result.get("content"):
        frappe.throw(_("No hay datos para generar el archivo DIOT del periodo indicado"))

    frappe.response["filename"] = result["filename"]
    frappe.response["filecontent"] = result["content"].encode("utf-8")
    frappe.response["type"] = "download"


# ──────────────────────────────────────────────────────────────────────────────
# Funciones internas
# ──────────────────────────────────────────────────────────────────────────────

def _aggregate_by_supplier(invoices: list) -> dict:
    """
    Group Purchase Invoice records by supplier and accumulate DIOT amounts.

    Returns a dict keyed by supplier name, each value being a data dict
    ready for _build_diot_line().
    """
    supplier_totals: dict = {}

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

    for inv in invoices:
        supplier = inv.supplier
        if not supplier:
            continue

        if supplier not in supplier_totals:
            supplier_totals[supplier] = _init_supplier_entry(supplier)

        tax_detail = _classify_taxes_from_list(all_taxes.get(inv.name, []), float(inv.net_total or 0))

        supplier_totals[supplier]["valor_16"] += tax_detail["base_16"]
        supplier_totals[supplier]["valor_8"] += tax_detail["base_8"]
        supplier_totals[supplier]["valor_0"] += tax_detail["base_0"]
        supplier_totals[supplier]["valor_exento"] += tax_detail["base_exento"]
        supplier_totals[supplier]["iva_retenido"] += tax_detail["iva_retenido"]

    return supplier_totals


def _init_supplier_entry(supplier: str) -> dict:
    """
    Fetch supplier master data and return a zeroed accumulator dict.
    Gracefully handles missing custom fields by defaulting safely.
    """
    supplier_data = frappe.db.get_value(
        "Supplier",
        supplier,
        ["mx_rfc", "mx_tipo_tercero_diot", "mx_tipo_operacion_diot",
         "supplier_name", "mx_nit_extranjero", "mx_pais_residencia", "mx_nacionalidad"],
        as_dict=True,
    ) or {}

    return {
        "supplier": supplier,
        "rfc": (supplier_data.get("mx_rfc") or "").strip().upper(),
        "tipo_tercero": supplier_data.get("mx_tipo_tercero_diot") or "Nacional",
        "tipo_operacion": supplier_data.get("mx_tipo_operacion_diot") or "Otros",
        "nombre": supplier_data.get("supplier_name") or supplier,
        "nit": supplier_data.get("mx_nit_extranjero") or "",
        "pais_residencia": supplier_data.get("mx_pais_residencia") or "",
        "nacionalidad": supplier_data.get("mx_nacionalidad") or "",
        "valor_16": 0.0,
        "valor_8": 0.0,
        "valor_0": 0.0,
        "valor_exento": 0.0,
        "iva_retenido": 0.0,
    }


def _classify_taxes_from_list(taxes: list, net_total: float) -> dict:
    """Classify taxes from a list of tax row dicts (batch-fetched).

    Returns:
        dict with keys: base_16, base_8, base_0, base_exento, iva_retenido
    """
    result = {
        "base_16": 0.0,
        "base_8": 0.0,
        "base_0": 0.0,
        "base_exento": 0.0,
        "iva_retenido": 0.0,
    }

    has_iva_16 = False
    has_iva_8 = False
    has_iva_0 = False
    iva_retenido_total = 0.0

    for tax in taxes:
        rate = abs(float(tax.get("rate") or 0))
        amount = float(tax.get("tax_amount") or 0)
        description = (tax.get("description") or "").upper()
        account = (tax.get("account_head") or "").upper()

        is_iva = "IVA" in description or "IVA" in account or "VALOR AGREGADO" in description
        if not is_iva:
            continue

        charge_type = tax.get("charge_type") or ""

        # Retención de IVA: amount is negative on the invoice, or description says retenido.
        # Avoid over-broad "RET" which matches unrelated words like "RETIRO" or "DIRECTA".
        is_retencion = (
            amount < 0
            or "RETENCION" in description
            or "RETENIDO" in description
            or "RETENCIÓN" in description
        )

        if is_retencion and charge_type == "On Net Total":
            iva_retenido_total += abs(amount)
            continue

        # Positive IVA — classify by rate
        if charge_type == "On Net Total":
            if rate == 16:
                has_iva_16 = True
            elif rate == 8:
                has_iva_8 = True
            elif rate == 0:
                has_iva_0 = True

    result["iva_retenido"] = iva_retenido_total

    # Assign the full net_total to the most specific IVA rate bucket found.
    # Priority: 16% > 8% > 0% > exento
    if has_iva_16:
        result["base_16"] = net_total
    elif has_iva_8:
        result["base_8"] = net_total
    elif has_iva_0:
        result["base_0"] = net_total
    else:
        result["base_exento"] = net_total

    return result


def _classify_taxes(inv_doc) -> dict:
    """Classify taxes from a Purchase Invoice document.

    Wrapper around _classify_taxes_from_list for callers that have a full doc.

    Returns:
        dict with keys: base_16, base_8, base_0, base_exento, iva_retenido
    """
    taxes = []
    for tax in (getattr(inv_doc, "taxes", []) or []):
        taxes.append({
            "charge_type": tax.charge_type,
            "rate": tax.rate,
            "tax_amount": tax.tax_amount,
            "description": tax.description,
            "account_head": tax.account_head,
        })
    return _classify_taxes_from_list(taxes, float(inv_doc.net_total or 0))


def _build_diot_line(data: dict) -> str:
    """
    Construct a single DIOT TXT line: 24 fields separated by pipe (|).

    Field widths and rules per Anexo 1 RMF 2025:
    - Amounts: integers (no decimals, no commas)
    - RFC field: left-justified, space-padded to 13 characters for nacionales
    - Extranjero fields: NIT, nombre, país, nacionalidad populated only for tipo 05
    """
    tipo_tercero = TIPO_TERCERO_MAP.get(data.get("tipo_tercero", "Nacional"), "04")
    tipo_operacion = TIPO_OPERACION_MAP.get(data.get("tipo_operacion", "Otros"), TIPO_OPERACION_DEFAULT)

    is_nacional = (tipo_tercero == "04")
    is_global = (tipo_tercero == "15")
    is_extranjero = (tipo_tercero == "05")

    # Field 3: RFC — left-justified, padded to 13 for nacionales; blank for extranjero/global
    rfc_field = ""
    if is_nacional or is_global:
        rfc_raw = data.get("rfc", "")
        # RFC must not exceed 13 chars; shorter ones are left-justified with trailing spaces
        rfc_field = rfc_raw[:RFC_FIELD_WIDTH].ljust(RFC_FIELD_WIDTH) if rfc_raw else " " * RFC_FIELD_WIDTH

    # Fields 4-7: Only for extranjero (tipo 05)
    nit = data.get("nit", "") if is_extranjero else ""
    nombre_extranjero = data.get("nombre", "") if is_extranjero else ""
    pais_residencia = data.get("pais_residencia", "") if is_extranjero else ""
    nacionalidad = data.get("nacionalidad", "") if is_extranjero else ""

    fields = [
        tipo_tercero,                               # 1
        tipo_operacion,                             # 2
        rfc_field,                                  # 3
        nit,                                        # 4
        nombre_extranjero,                          # 5
        pais_residencia,                            # 6
        nacionalidad,                               # 7
        _fmt_amount(data.get("valor_16", 0)),       # 8  Valor actos 16%
        "0",                                        # 9  IVA 16% no acreditable
        "0",                                        # 10 Valor 16% no pagados
        _fmt_amount(data.get("valor_8", 0)),        # 11 Valor actos 8%
        "0",                                        # 12 IVA 8% no acreditable
        "0",                                        # 13 Valor 8% no pagados
        "0",                                        # 14 Importación 16%
        "0",                                        # 15 Importación 8%
        "0",                                        # 16 Importación exenta
        _fmt_amount(data.get("valor_0", 0)),        # 17 Valor actos 0%
        _fmt_amount(data.get("valor_exento", 0)),   # 18 Valor actos exentos
        _fmt_amount(data.get("iva_retenido", 0)),   # 19 IVA retenido
        "0",                                        # 20 Devoluciones IVA
        "",                                         # 21 (padding)
        "",                                         # 22 (padding)
        "",                                         # 23 (padding)
        "",                                         # 24 (padding)
    ]

    assert len(fields) == DIOT_FIELD_COUNT, (
        f"DIOT line must have {DIOT_FIELD_COUNT} fields, got {len(fields)}"
    )

    return "|".join(fields)


def _fmt_amount(value) -> str:
    """
    Format a monetary value for DIOT output.
    - Returns integer string (no decimals, no commas)
    - Zero or None → "0"
    - Negative values are truncated to 0 (DIOT does not accept negatives in amount fields)
    """
    try:
        int_value = int(round(float(value or 0)))
        return str(max(0, int_value))
    except (TypeError, ValueError):
        return "0"


def _safe_name(text: str) -> str:
    """Strip characters unsafe for filenames, keeping alphanumeric and underscores."""
    import re
    return re.sub(r"[^A-Za-z0-9_\-]", "_", text or "company")
