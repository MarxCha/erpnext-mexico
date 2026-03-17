"""
Panel Fiscal MX — Server-side API
Provee métricas, actividad reciente y estado de configuración fiscal.
"""

import frappe
from frappe import _
from frappe.utils import getdate, get_first_day, get_last_day, fmt_money


@frappe.whitelist()
def get_dashboard_data(company=None):
    """Returns all dashboard metrics and data."""
    return {
        "metrics": get_metrics(company),
        "recent_cfdis": get_recent_cfdis(company),
        "monthly_chart": get_monthly_data(company),
        "setup_status": get_setup_status(company),
    }


def get_metrics(company: str | None = None) -> dict:
    """Get CFDI metric counts and monthly total."""
    base_filters = {"docstatus": 1}
    if company:
        base_filters["company"] = company

    total_invoices = frappe.db.count("Sales Invoice", base_filters) or 0

    stamped = (
        frappe.db.count(
            "Sales Invoice", {**base_filters, "mx_cfdi_status": "Timbrado"}
        )
        or 0
    )
    pending = (
        frappe.db.count(
            "Sales Invoice", {**base_filters, "mx_cfdi_status": "Pendiente"}
        )
        or 0
    )
    errors = (
        frappe.db.count(
            "Sales Invoice", {**base_filters, "mx_cfdi_status": "Error"}
        )
        or 0
    )
    cancelled = (
        frappe.db.count(
            "Sales Invoice", {**base_filters, "mx_cfdi_status": "Cancelado"}
        )
        or 0
    )

    today = getdate()
    first_day = get_first_day(today)
    company_filter = f"AND company = %(company)s" if company else ""

    monthly_result = frappe.db.sql(
        f"""
        SELECT COALESCE(SUM(grand_total), 0) AS total
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND posting_date >= %(first_day)s
          AND posting_date <= %(today)s
          {company_filter}
        """,
        {"first_day": first_day, "today": today, "company": company},
        as_dict=True,
    )
    monthly_total = monthly_result[0].total if monthly_result else 0

    return {
        "total_invoices": total_invoices,
        "stamped": stamped,
        "pending": pending,
        "errors": errors,
        "cancelled": cancelled,
        "monthly_total": float(monthly_total),
    }


def get_recent_cfdis(company: str | None = None, limit: int = 10) -> list:
    """Get the most recent CFDI-stamped Sales Invoices."""
    filters = {"docstatus": 1, "mx_cfdi_status": ["!=", ""]}
    if company:
        filters["company"] = company

    return frappe.get_list(
        "Sales Invoice",
        filters=filters,
        fields=[
            "name",
            "customer_name",
            "grand_total",
            "currency",
            "mx_cfdi_uuid",
            "mx_cfdi_status",
            "posting_date",
        ],
        order_by="posting_date desc, creation desc",
        limit_page_length=limit,
    )


def get_monthly_data(company: str | None = None) -> list:
    """Get monthly CFDI counts for the last 6 months (for chart)."""
    company_filter = "AND company = %(company)s" if company else ""

    data = frappe.db.sql(
        f"""
        SELECT
            DATE_FORMAT(posting_date, '%%Y-%%m')                                    AS month,
            COUNT(*)                                                                  AS total,
            SUM(CASE WHEN mx_cfdi_status = 'Timbrado' THEN 1 ELSE 0 END)            AS stamped,
            COALESCE(SUM(grand_total), 0)                                            AS amount
        FROM `tabSales Invoice`
        WHERE docstatus = 1
          AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
          {company_filter}
        GROUP BY DATE_FORMAT(posting_date, '%%Y-%%m')
        ORDER BY month
        """,
        {"company": company},
        as_dict=True,
    )
    # Ensure numeric types are JSON-safe
    for row in data:
        row["total"] = int(row["total"] or 0)
        row["stamped"] = int(row["stamped"] or 0)
        row["amount"] = float(row["amount"] or 0)

    return data


def get_setup_status(company: str | None = None) -> list:
    """
    Check completeness of fiscal setup.
    Returns a list of steps with their completion status.
    """
    steps = []

    if company:
        rfc = frappe.db.get_value("Company", company, "mx_rfc")
        steps.append({"label": _("RFC Configurado"), "done": bool(rfc)})

        regimen = frappe.db.get_value("Company", company, "mx_regimen_fiscal")
        steps.append({"label": _("Régimen Fiscal"), "done": bool(regimen)})

        cp = frappe.db.get_value("Company", company, "mx_lugar_expedicion")
        steps.append({"label": _("Código Postal"), "done": bool(cp)})
    else:
        steps = [
            {"label": _("RFC Configurado"), "done": False},
            {"label": _("Régimen Fiscal"), "done": False},
            {"label": _("Código Postal"), "done": False},
        ]

    # CSD active
    has_cert = False
    if frappe.db.table_exists("MX Digital Certificate"):
        has_cert = (
            frappe.db.count("MX Digital Certificate", {"status": "Activo"}) > 0
        )
    steps.append({"label": _("CSD Activo"), "done": has_cert})

    # PAC configured
    has_pac = False
    if frappe.db.table_exists("MX CFDI Settings"):
        try:
            settings = frappe.get_single("MX CFDI Settings")
            has_pac = bool(
                getattr(settings, "pac_provider", None)
                and getattr(settings, "pac_credentials", None)
            )
        except Exception:
            has_pac = False
    steps.append({"label": _("PAC Configurado"), "done": has_pac})

    return steps
