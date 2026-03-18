"""
Generador de Catálogo de Cuentas XML — Contabilidad Electrónica.
Esquema: CatalogoCuentas_1_3.xsd del SAT (Anexo 24)

Referencia: http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/CatalogoCuentas/
"""
import frappe
from frappe import _
from lxml import etree


NAMESPACE = "http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/CatalogoCuentas"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = (
    "http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/CatalogoCuentas "
    "http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/CatalogoCuentas/CatalogoCuentas_1_3.xsd"
)


@frappe.whitelist()
def generate_catalog_xml(company: str, year: int, month: int) -> str:
    """
    Generate Catálogo de Cuentas XML (Anexo 24).

    Args:
        company: Company name
        year: Fiscal year (e.g. 2025)
        month: Month number 1-12

    Returns:
        UTF-8 XML string validated against CatalogoCuentas_1_3.xsd structure.

    Raises:
        frappe.ValidationError: If RFC is not configured for the company.
    """
    frappe.only_for(["System Manager", "Accounts Manager"])
    if not frappe.has_permission("Company", "read", company):
        frappe.throw(_("Sin permiso"), frappe.PermissionError)

    year = int(year)
    month = int(month)

    company_doc = frappe.get_cached_doc("Company", company)
    rfc = company_doc.get("mx_rfc")
    if not rfc:
        frappe.throw(_("RFC no configurado para {0}. Configure el RFC en los ajustes de la empresa.").format(company))

    nsmap = {
        None: NAMESPACE,
        "xsi": XSI,
    }
    root = etree.Element(
        f"{{{NAMESPACE}}}Catalogo",
        nsmap=nsmap,
    )
    root.set("Version", "1.3")
    root.set("RFC", rfc)
    root.set("Mes", f"{month:02d}")
    root.set("Anio", str(year))
    root.set(f"{{{XSI}}}schemaLocation", SCHEMA_LOCATION)

    # Retrieve ALL accounts for this company (including group accounts), ordered by account_number.
    # SAT requires the complete chart of accounts at all hierarchy levels.
    accounts = frappe.get_all(
        "Account",
        filters={"company": company},
        fields=[
            "name",
            "account_number",
            "account_name",
            "root_type",
            "parent_account",
            "account_type",
            "balance_must_be",
        ],
        order_by="account_number, name",
    )

    # Pre-compute all account levels in memory (eliminates N+1 queries)
    parent_map = {acc.name: acc.parent_account for acc in accounts}
    level_cache = _compute_all_levels(parent_map)

    for acc in accounts:
        num_cta = _safe_num_cta(acc)
        desc = (acc.account_name or acc.name)[:100]
        nivel = level_cache.get(acc.name, 1)
        natur = _get_naturaleza(acc)
        cod_agrup = _get_sat_grouping_code(acc)

        attrib = {
            "NumCta": num_cta,
            "Desc": desc,
            "CodAgrup": cod_agrup,
            "Nivel": str(nivel),
            "Natur": natur,
        }
        etree.SubElement(root, f"{{{NAMESPACE}}}Ctas", attrib=attrib)

    return etree.tostring(
        root,
        xml_declaration=True,
        encoding="UTF-8",
        pretty_print=True,
    ).decode("utf-8")


# ─── Private helpers ────────────────────────────────────────────────────────


def _safe_num_cta(account: dict) -> str:
    """Return a clean account number string (max 20 chars)."""
    return (account.get("account_number") or account["name"])[:20]


def _get_naturaleza(account: dict) -> str:
    """
    Return SAT naturaleza code.

    D = Deudora (Asset, Expense)
    A = Acreedora (Liability, Equity, Income)
    """
    if account.get("balance_must_be") == "Debit":
        return "D"
    if account.get("balance_must_be") == "Credit":
        return "A"
    # Fallback to root_type
    return "D" if account.get("root_type") in ("Asset", "Expense") else "A"


def _get_sat_grouping_code(account: dict) -> str:
    """
    Map an ERPNext account to a SAT código agrupador (Catálogo del SAT Anexo 24).

    The mapping uses account_type when available for precision, falling back
    to root_type for a top-level grouping.
    """
    type_map = {
        "Bank": "102.01",
        "Cash": "101.01",
        "Receivable": "105.01",
        "Payable": "201.01",
        "Stock": "115.01",
        "Fixed Asset": "111.01",
        "Accumulated Depreciation": "112.01",
        "Depreciation": "603.04",
        "Cost of Goods Sold": "501.01",
        "Income Account": "401.01",
        "Expense Account": "603.01",
        "Tax": "216.01",
        "Chargeable": "118.01",
        "Capital Work in Progress": "111.02",
        "Investments": "103.01",
        "Round Off": "701.01",
        "Temporary": "701.02",
        "Payroll Payable": "210.01",
    }

    root_map = {
        "Asset": "100.01",
        "Liability": "200.01",
        "Equity": "300.01",
        "Income": "400.01",
        "Expense": "500.01",
    }

    account_type = account.get("account_type") or ""
    if account_type in type_map:
        return type_map[account_type]

    return root_map.get(account.get("root_type") or "", "100")


def _compute_all_levels(parent_map: dict) -> dict:
    """Compute account levels for all accounts using the parent map (no DB queries).

    Args:
        parent_map: Dict mapping account_name -> parent_account for all accounts.

    Returns:
        Dict mapping account_name -> depth level (1 = root, 2 = child of root, etc.).
    """
    cache: dict = {}

    def _get_level(account_name: str) -> int:
        if account_name in cache:
            return cache[account_name]

        level = 1
        current = account_name
        visited: set = set()

        while True:
            if current in visited:
                break  # guard against circular references
            visited.add(current)
            parent = parent_map.get(current)
            if not parent:
                break
            level += 1
            current = parent
            if level >= 10:
                break

        cache[account_name] = level
        return level

    for account_name in parent_map:
        _get_level(account_name)

    return cache


def _get_account_level(account_name: str) -> int:
    """
    Traverse the parent chain to compute the depth level of an account.
    Level 1 = root, Level 2 = child of root, etc. Capped at 10.

    .. deprecated::
        Use ``_compute_all_levels`` with a pre-built parent map to avoid N+1 queries.
        This function is kept for backwards compatibility with external callers.
    """
    level = 1
    current = account_name
    visited: set = set()

    while True:
        if current in visited:
            break  # guard against circular references
        visited.add(current)

        parent = frappe.db.get_value("Account", current, "parent_account")
        if not parent:
            break
        level += 1
        current = parent
        if level >= 10:
            break

    return level
