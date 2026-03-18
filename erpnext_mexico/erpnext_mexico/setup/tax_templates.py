"""
Creación de plantillas de impuestos mexicanos.
Se ejecuta durante la instalación de la app.
"""

import frappe


SALES_TAX_TEMPLATES = [
    {
        "title": "IVA 16% Trasladado",
        "tax_category": "",
        "taxes": [
            {
                "charge_type": "On Net Total",
                "account_head": "IVA Trasladado - {abbr}",
                "description": "IVA 16%",
                "rate": 16,
            }
        ],
    },
    {
        "title": "IVA 0% Trasladado",
        "tax_category": "",
        "taxes": [
            {
                "charge_type": "On Net Total",
                "account_head": "IVA Trasladado - {abbr}",
                "description": "IVA 0%",
                "rate": 0,
            }
        ],
    },
    {
        "title": "IVA Exento",
        "tax_category": "",
        "taxes": [],
    },
    {
        "title": "IVA 16% + ISR Retenido 10%",
        "tax_category": "",
        "taxes": [
            {
                "charge_type": "On Net Total",
                "account_head": "IVA Trasladado - {abbr}",
                "description": "IVA 16%",
                "rate": 16,
            },
            {
                "charge_type": "On Net Total",
                "account_head": "ISR Retenido por Pagar - {abbr}",
                "description": "ISR Retenido 10%",
                "rate": -10,
            },
        ],
    },
    {
        "title": "IVA 16% + IVA Retenido 10.6667%",
        "tax_category": "",
        "taxes": [
            {
                "charge_type": "On Net Total",
                "account_head": "IVA Trasladado - {abbr}",
                "description": "IVA 16%",
                "rate": 16,
            },
            {
                "charge_type": "On Net Total",
                "account_head": "IVA Retenido por Pagar - {abbr}",
                "description": "IVA Retenido 2/3",
                "rate": -10.6667,
            },
        ],
    },
    {
        "title": "IVA 16% + ISR 10% + IVA Retenido 10.6667%",
        "tax_category": "",
        "taxes": [
            {
                "charge_type": "On Net Total",
                "account_head": "IVA Trasladado - {abbr}",
                "description": "IVA 16%",
                "rate": 16,
            },
            {
                "charge_type": "On Net Total",
                "account_head": "ISR Retenido por Pagar - {abbr}",
                "description": "ISR Retenido 10%",
                "rate": -10,
            },
            {
                "charge_type": "On Net Total",
                "account_head": "IVA Retenido por Pagar - {abbr}",
                "description": "IVA Retenido 2/3",
                "rate": -10.6667,
            },
        ],
    },
]


PURCHASE_TAX_TEMPLATES = [
    {
        "title": "IVA 16% Acreditable",
        "tax_category": "",
        "taxes": [
            {
                "charge_type": "On Net Total",
                "account_head": "IVA Acreditable - {abbr}",
                "description": "IVA 16%",
                "rate": 16,
            }
        ],
    },
    {
        "title": "IVA 0% Acreditable",
        "tax_category": "",
        "taxes": [
            {
                "charge_type": "On Net Total",
                "account_head": "IVA Acreditable - {abbr}",
                "description": "IVA 0%",
                "rate": 0,
            }
        ],
    },
    {
        "title": "IVA 16% + ISR Retenido (Compras)",
        "tax_category": "",
        "taxes": [
            {
                "charge_type": "On Net Total",
                "account_head": "IVA Acreditable - {abbr}",
                "description": "IVA 16%",
                "rate": 16,
            },
            {
                "charge_type": "On Net Total",
                "account_head": "ISR Retenido por Pagar - {abbr}",
                "description": "ISR Retenido 10%",
                "rate": -10,
            },
        ],
    },
]


def create_tax_templates(company: str | None = None):
    """Crea plantillas de impuestos para una empresa mexicana."""
    if company:
        companies = [frappe.get_doc("Company", company)]
    else:
        companies = frappe.get_all(
            "Company", filters={"country": "Mexico"}, fields=["name", "abbr"]
        )
        companies = [frappe.get_doc("Company", c.name) for c in companies]

    for comp in companies:
        abbr = comp.abbr
        for template_def in SALES_TAX_TEMPLATES:
            title = f"{template_def['title']} - {abbr}"
            if frappe.db.exists("Sales Taxes and Charges Template", title):
                continue

            doc = frappe.new_doc("Sales Taxes and Charges Template")
            doc.title = title
            doc.company = comp.name
            doc.tax_category = template_def.get("tax_category", "")

            for tax in template_def["taxes"]:
                doc.append("taxes", {
                    "charge_type": tax["charge_type"],
                    "account_head": tax["account_head"].format(abbr=abbr),
                    "description": tax["description"],
                    "rate": tax["rate"],
                })

            try:
                doc.flags.ignore_permissions = True
                doc.insert()
            except Exception as e:
                frappe.log_error(
                    f"Error creando template {title}: {e}",
                    title="Tax Template Creation Error",
                )

        for template_def in PURCHASE_TAX_TEMPLATES:
            title = f"{template_def['title']} - {abbr}"
            if frappe.db.exists("Purchase Taxes and Charges Template", title):
                continue

            doc = frappe.new_doc("Purchase Taxes and Charges Template")
            doc.title = title
            doc.company = comp.name
            doc.tax_category = template_def.get("tax_category", "")

            for tax in template_def["taxes"]:
                doc.append("taxes", {
                    "charge_type": tax["charge_type"],
                    "account_head": tax["account_head"].format(abbr=abbr),
                    "description": tax["description"],
                    "rate": tax["rate"],
                })

            try:
                doc.flags.ignore_permissions = True
                doc.insert()
            except Exception as e:
                frappe.log_error(
                    f"Error creando template {title}: {e}",
                    title="Purchase Tax Template Creation Error",
                )

    frappe.db.commit()
