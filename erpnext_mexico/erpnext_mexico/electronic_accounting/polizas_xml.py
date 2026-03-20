"""
Generador de Pólizas del Periodo XML — Contabilidad Electrónica.
Esquema: PolizasPeriodo_1_3.xsd del SAT (Anexo 24)

Solo se envía por requerimiento de auditoría del SAT (no envío mensual).
Referencia: http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/
"""
import re
import frappe
from frappe import _
from frappe.utils import getdate, get_first_day, get_last_day
from frappe.rate_limiter import rate_limit
from lxml import etree


NAMESPACE = "http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = (
    "http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo "
    "http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo/PolizasPeriodo_1_3.xsd"
)

# Valid TipoSolicitud values per SAT specification
VALID_TIPO_SOLICITUD = {
    "AF": "Acto de fiscalización",
    "FC": "Fiscalización compulsa",
    "DE": "Devolución",
    "CO": "Compensación",
}

# Voucher type labels in Spanish for XML Concepto field
VOUCHER_TYPE_LABELS = {
    "Journal Entry": "Póliza de diario",
    "Sales Invoice": "Factura de venta",
    "Purchase Invoice": "Factura de compra",
    "Payment Entry": "Pago",
    "Purchase Order": "Orden de compra",
    "Sales Order": "Orden de venta",
    "Delivery Note": "Nota de entrega",
    "Purchase Receipt": "Recibo de compra",
    "Stock Entry": "Entrada de almacén",
    "Expense Claim": "Reembolso de gastos",
}


@frappe.whitelist()
@rate_limit(limit=5, seconds=60)
def generate_polizas_xml(
    company: str,
    year: int,
    month: int,
    tipo_solicitud: str = "AF",
    num_orden: str = "",
    num_tramite: str = "",
) -> str:
    """
    Generate Pólizas del Periodo XML (Anexo 24).

    Args:
        company: Company name.
        year: Fiscal year (e.g. 2025).
        month: Month number 1-12.
        tipo_solicitud: AF=Acto fiscalización, FC=Fiscalización compulsa,
                        DE=Devolución, CO=Compensación.
        num_orden: Número de orden de auditoría (required for AF and FC).
        num_tramite: Número de trámite (required for DE and CO).

    Returns:
        UTF-8 XML string conforming to PolizasPeriodo_1_3.xsd.
    """
    frappe.only_for(["System Manager", "Accounts Manager"])
    if not frappe.has_permission("Company", "read", company):
        frappe.throw(_("Sin permiso"), frappe.PermissionError)

    year = int(year)
    month = int(month)
    tipo_solicitud = (tipo_solicitud or "AF").upper()

    if num_orden and not re.match(r'^[A-Za-z0-9/]{1,13}$', num_orden):
        frappe.throw(_("NumOrden tiene formato inválido"))
    if num_tramite and not re.match(r'^[A-Za-z0-9/]{1,14}$', num_tramite):
        frappe.throw(_("NumTramite tiene formato inválido"))

    if tipo_solicitud not in VALID_TIPO_SOLICITUD:
        frappe.throw(
            _("TipoSolicitud inválido: {0}. Valores válidos: {1}").format(
                tipo_solicitud, ", ".join(VALID_TIPO_SOLICITUD.keys())
            )
        )

    # Validate required fields per tipo_solicitud
    if tipo_solicitud in ("AF", "FC") and not num_orden:
        frappe.throw(_("NumOrden es requerido para TipoSolicitud {0}.").format(tipo_solicitud))
    if tipo_solicitud in ("DE", "CO") and not num_tramite:
        frappe.throw(_("NumTramite es requerido para TipoSolicitud {0}.").format(tipo_solicitud))

    company_doc = frappe.get_cached_doc("Company", company)
    rfc = company_doc.get("mx_rfc")
    if not rfc:
        frappe.throw(_("RFC no configurado para {0}.").format(company))

    from_date = get_first_day(getdate(f"{year}-{month:02d}-01"))
    to_date = get_last_day(from_date)

    nsmap = {
        None: NAMESPACE,
        "xsi": XSI,
    }

    attrib = {
        "Version": "1.3",
        "RFC": rfc,
        "Mes": f"{month:02d}",
        "Anio": str(year),
        "TipoSolicitud": tipo_solicitud,
    }
    if num_orden:
        attrib["NumOrden"] = num_orden[:13]
    if num_tramite:
        attrib["NumTramite"] = num_tramite[:14]
    attrib[f"{{{XSI}}}schemaLocation"] = SCHEMA_LOCATION

    root = etree.Element(f"{{{NAMESPACE}}}Polizas", nsmap=nsmap, attrib=attrib)

    # Retrieve distinct vouchers that have GL activity in the period
    vouchers = frappe.db.sql(
        """
        SELECT DISTINCT
            gle.voucher_type,
            gle.voucher_no,
            gle.posting_date
        FROM `tabGL Entry` gle
        WHERE gle.company = %(company)s
          AND gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
          AND gle.is_cancelled = 0
        ORDER BY gle.posting_date, gle.voucher_no
        """,
        {"company": company, "from_date": from_date, "to_date": to_date},
        as_dict=True,
    )

    for voucher in vouchers:
        concepto = _build_concepto(voucher)

        poliza_el = etree.SubElement(
            root,
            f"{{{NAMESPACE}}}Poliza",
            attrib={
                "NumUnIdenPol": voucher.voucher_no[:50],
                "Fecha": str(voucher.posting_date),
                "Concepto": concepto,
            },
        )

        # GL entries for this specific voucher
        entries = frappe.db.sql(
            """
            SELECT
                gle.account,
                a.account_number,
                a.account_name,
                gle.debit,
                gle.credit,
                gle.remarks
            FROM `tabGL Entry` gle
            INNER JOIN `tabAccount` a ON a.name = gle.account
            WHERE gle.voucher_type = %(voucher_type)s
              AND gle.voucher_no   = %(voucher_no)s
              AND gle.company      = %(company)s
              AND gle.is_cancelled = 0
            ORDER BY a.account_number, gle.creation
            """,
            {"voucher_type": voucher.voucher_type, "voucher_no": voucher.voucher_no, "company": company},
            as_dict=True,
        )

        for entry in entries:
            num_cta = (entry.account_number or entry.account)[:20]
            des_cta = (entry.account_name or entry.account)[:100]
            entry_concepto = (entry.remarks or concepto)[:200]

            etree.SubElement(
                poliza_el,
                f"{{{NAMESPACE}}}Transaccion",
                attrib={
                    "NumCta": num_cta,
                    "DesCta": des_cta,
                    "Concepto": entry_concepto,
                    "Debe": f"{float(entry.debit or 0):.2f}",
                    "Haber": f"{float(entry.credit or 0):.2f}",
                },
            )

        # Add CompNal (Comprobante Nacional) if the voucher has a CFDI UUID
        _add_comp_nal(poliza_el, voucher, NAMESPACE)

    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    ).decode("utf-8")


# ─── Private helpers ────────────────────────────────────────────────────────


def _build_concepto(voucher: dict) -> str:
    """Build a readable concept string for a voucher (max 300 chars)."""
    label = VOUCHER_TYPE_LABELS.get(voucher.voucher_type, voucher.voucher_type)
    return f"{label}: {voucher.voucher_no}"[:300]


def _add_comp_nal(poliza_el, voucher: dict, namespace: str) -> None:
    """Add CompNal elements linking to CFDI UUIDs for the voucher.

    CompNal (Comprobante Nacional) is an optional child of Transaccion that
    links accounting vouchers to their CFDI timbrado UUID, required by SAT
    during audit reviews (PolizasPeriodo_1_3.xsd).
    """
    # Only Sales Invoice and Purchase Invoice have CFDI UUIDs
    uuid_field_map = {
        "Sales Invoice": "mx_cfdi_uuid",
        "Purchase Invoice": "mx_cfdi_uuid_proveedor",
    }

    uuid_field = uuid_field_map.get(voucher.voucher_type)
    if not uuid_field:
        return

    uuid_value = frappe.db.get_value(
        voucher.voucher_type, voucher.voucher_no, uuid_field
    )
    if not uuid_value:
        return

    # Get the RFC of the related party
    rfc = ""
    if voucher.voucher_type == "Sales Invoice":
        customer = frappe.db.get_value("Sales Invoice", voucher.voucher_no, "customer")
        if customer:
            rfc = frappe.db.get_value("Customer", customer, "mx_rfc") or ""
    elif voucher.voucher_type == "Purchase Invoice":
        supplier = frappe.db.get_value("Purchase Invoice", voucher.voucher_no, "supplier")
        if supplier:
            rfc = frappe.db.get_value("Supplier", supplier, "mx_rfc") or ""

    # Find all Transaccion elements under this Poliza and add CompNal to the first one
    transacciones = poliza_el.findall(f"{{{namespace}}}Transaccion")
    if transacciones:
        attrib = {"UUID_CFDI": uuid_value}
        if rfc:
            attrib["RFC"] = rfc
        # MontoTotal from the voucher
        total = frappe.db.get_value(
            voucher.voucher_type, voucher.voucher_no, "grand_total"
        )
        if total:
            attrib["MontoTotal"] = f"{float(total):.2f}"

        etree.SubElement(
            transacciones[0],
            f"{{{namespace}}}CompNal",
            attrib=attrib,
        )
