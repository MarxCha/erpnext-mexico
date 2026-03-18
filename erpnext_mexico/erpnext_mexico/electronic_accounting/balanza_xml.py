"""
Generador de Balanza de Comprobación XML — Contabilidad Electrónica.
Esquema: BalanzaComprobacion_1_3.xsd del SAT (Anexo 24)

Referencia: http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/BalanzaComprobacion/
"""
import frappe
from frappe import _
from frappe.utils import getdate, get_first_day, get_last_day
from lxml import etree


NAMESPACE = "http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/BalanzaComprobacion"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = (
    "http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/BalanzaComprobacion "
    "http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/BalanzaComprobacion/BalanzaComprobacion_1_3.xsd"
)

# Valid values for TipoEnvio per SAT specification
VALID_TIPO_ENVIO = ("N", "C")


@frappe.whitelist()
def generate_balanza_xml(
    company: str,
    year: int,
    month: int,
    tipo_envio: str = "N",
    fecha_mod_bal: str = "",
) -> str:
    """
    Generate Balanza de Comprobación XML (Anexo 24).

    Args:
        company: Company name.
        year: Fiscal year (e.g. 2025).
        month: Month number 1-12.
        tipo_envio: "N" (Normal) or "C" (Complementaria).
        fecha_mod_bal: Required when tipo_envio="C". Format YYYY-MM-DD.

    Returns:
        UTF-8 XML string conforming to BalanzaComprobacion_1_3.xsd.
    """
    frappe.only_for(["System Manager", "Accounts Manager"])
    if not frappe.has_permission("Company", "read", company):
        frappe.throw(_("Sin permiso"), frappe.PermissionError)

    year = int(year)
    month = int(month)
    tipo_envio = (tipo_envio or "N").upper()

    if tipo_envio not in VALID_TIPO_ENVIO:
        frappe.throw(_("TipoEnvio inválido: {0}. Use N o C.").format(tipo_envio))

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
    root = etree.Element(f"{{{NAMESPACE}}}Balanza", nsmap=nsmap)
    root.set("Version", "1.3")
    root.set("RFC", rfc)
    root.set("Mes", f"{month:02d}")
    root.set("Anio", str(year))
    root.set("TipoEnvio", tipo_envio)
    if tipo_envio == "C":
        if not fecha_mod_bal:
            frappe.throw(
                _("FechaModBal es requerida cuando TipoEnvio es 'C' (Complementaria).")
            )
        root.set("FechaModBal", fecha_mod_bal)
    root.set(f"{{{XSI}}}schemaLocation", SCHEMA_LOCATION)

    # Compute trial balance per account using GL Entries.
    # SaldoIni = sum of all movements BEFORE from_date (opening balance).
    # Debe / Haber = sum of debits / credits WITHIN the period.
    # SaldoFin = SaldoIni + Debe - Haber (signed; we report absolute value).
    balances = frappe.db.sql(
        """
        SELECT
            gle.account,
            a.account_number,
            a.account_name,
            a.root_type,
            SUM(
                CASE WHEN gle.posting_date < %(from_date)s
                     THEN gle.debit - gle.credit
                     ELSE 0
                END
            ) AS opening_balance,
            SUM(
                CASE WHEN gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
                     THEN gle.debit
                     ELSE 0
                END
            ) AS period_debit,
            SUM(
                CASE WHEN gle.posting_date BETWEEN %(from_date)s AND %(to_date)s
                     THEN gle.credit
                     ELSE 0
                END
            ) AS period_credit
        FROM `tabGL Entry` gle
        INNER JOIN `tabAccount` a ON a.name = gle.account
        WHERE gle.company = %(company)s
          AND gle.posting_date <= %(to_date)s
          AND gle.is_cancelled = 0
        GROUP BY gle.account, a.account_number, a.account_name, a.root_type
        HAVING opening_balance <> 0
            OR period_debit    <> 0
            OR period_credit   <> 0
        ORDER BY a.account_number, gle.account
        """,
        {
            "company": company,
            "from_date": from_date,
            "to_date": to_date,
        },
        as_dict=True,
    )

    for bal in balances:
        opening = float(bal.opening_balance or 0)
        debit = float(bal.period_debit or 0)
        credit = float(bal.period_credit or 0)
        closing = opening + debit - credit

        num_cta = (bal.account_number or bal.account)[:20]

        etree.SubElement(
            root,
            f"{{{NAMESPACE}}}Ctas",
            attrib={
                "NumCta": num_cta,
                "SaldoIni": f"{opening:.2f}",
                "Debe": f"{debit:.2f}",
                "Haber": f"{credit:.2f}",
                "SaldoFin": f"{closing:.2f}",
            },
        )

    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    ).decode("utf-8")
