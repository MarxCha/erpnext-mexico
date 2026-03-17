"""
Instalación y configuración de ERPNext México.
Crea custom fields, carga catálogos y configura templates fiscales.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


# ═══════════════════════════════════════════════════════════
# CUSTOM FIELDS — Prefijo mx_ en todos los campos
# ═══════════════════════════════════════════════════════════

CUSTOM_FIELDS = {
    # ── Company ──
    "Company": [
        dict(
            fieldname="mx_fiscal_section",
            label="Datos Fiscales México",
            fieldtype="Section Break",
            insert_after="tax_id",
        ),
        dict(
            fieldname="mx_rfc",
            label="RFC",
            fieldtype="Data",
            length=13,
            insert_after="mx_fiscal_section",
            description="Registro Federal de Contribuyentes (12 o 13 caracteres)",
        ),
        dict(
            fieldname="mx_nombre_fiscal",
            label="Nombre / Razón Social (SAT)",
            fieldtype="Data",
            insert_after="mx_rfc",
            description="Debe coincidir exactamente con el registro del SAT",
        ),
        dict(
            fieldname="mx_regimen_fiscal",
            label="Régimen Fiscal",
            fieldtype="Link",
            options="MX Fiscal Regime",
            insert_after="mx_nombre_fiscal",
        ),
        dict(
            fieldname="mx_lugar_expedicion",
            label="Lugar de Expedición (CP)",
            fieldtype="Link",
            options="MX Postal Code",
            insert_after="mx_regimen_fiscal",
            description="Código postal del domicilio fiscal del emisor",
        ),
    ],
    # ── Customer ──
    "Customer": [
        dict(
            fieldname="mx_fiscal_section",
            label="Datos Fiscales México",
            fieldtype="Section Break",
            insert_after="tax_id",
        ),
        dict(
            fieldname="mx_rfc",
            label="RFC",
            fieldtype="Data",
            length=13,
            insert_after="mx_fiscal_section",
        ),
        dict(
            fieldname="mx_nombre_fiscal",
            label="Nombre Fiscal (SAT)",
            fieldtype="Data",
            insert_after="mx_rfc",
            description="Debe coincidir exactamente con el registro del SAT",
        ),
        dict(
            fieldname="mx_regimen_fiscal",
            label="Régimen Fiscal",
            fieldtype="Link",
            options="MX Fiscal Regime",
            insert_after="mx_nombre_fiscal",
        ),
        dict(
            fieldname="mx_domicilio_fiscal_cp",
            label="Domicilio Fiscal (CP)",
            fieldtype="Link",
            options="MX Postal Code",
            insert_after="mx_regimen_fiscal",
            description="Código postal del domicilio fiscal del receptor",
        ),
        dict(
            fieldname="mx_default_uso_cfdi",
            label="Uso CFDI (por defecto)",
            fieldtype="Link",
            options="MX CFDI Use",
            insert_after="mx_domicilio_fiscal_cp",
        ),
        dict(
            fieldname="mx_default_forma_pago",
            label="Forma de Pago (por defecto)",
            fieldtype="Link",
            options="MX Payment Form",
            insert_after="mx_default_uso_cfdi",
        ),
    ],
    # ── Supplier ──
    "Supplier": [
        dict(
            fieldname="mx_fiscal_section",
            label="Datos Fiscales México",
            fieldtype="Section Break",
            insert_after="tax_id",
        ),
        dict(
            fieldname="mx_rfc",
            label="RFC",
            fieldtype="Data",
            length=13,
            insert_after="mx_fiscal_section",
        ),
        dict(
            fieldname="mx_tipo_tercero_diot",
            label="Tipo Tercero (DIOT)",
            fieldtype="Select",
            options="\nNacional\nExtranjero\nGlobal",
            insert_after="mx_rfc",
            default="Nacional",
        ),
    ],
    # ── Item ──
    "Item": [
        dict(
            fieldname="mx_sat_section",
            label="Clasificación SAT",
            fieldtype="Section Break",
            insert_after="description",
        ),
        dict(
            fieldname="mx_clave_prod_serv",
            label="Clave Producto/Servicio SAT",
            fieldtype="Link",
            options="MX Product Service Key",
            insert_after="mx_sat_section",
            description="Catálogo c_ClaveProdServ del SAT (Anexo 20)",
        ),
        dict(
            fieldname="mx_clave_unidad",
            label="Clave Unidad SAT",
            fieldtype="Link",
            options="MX Unit Key",
            insert_after="mx_clave_prod_serv",
            description="Catálogo c_ClaveUnidad del SAT",
        ),
    ],
    # ── Sales Invoice ──
    "Sales Invoice": [
        dict(
            fieldname="mx_cfdi_section",
            label="CFDI",
            fieldtype="Section Break",
            insert_after="amended_from",
        ),
        dict(
            fieldname="mx_uso_cfdi",
            label="Uso CFDI",
            fieldtype="Link",
            options="MX CFDI Use",
            insert_after="mx_cfdi_section",
            fetch_from="customer.mx_default_uso_cfdi",
        ),
        dict(
            fieldname="mx_metodo_pago",
            label="Método de Pago",
            fieldtype="Link",
            options="MX Payment Method",
            insert_after="mx_uso_cfdi",
            description="PUE = Pago en Una Exhibición, PPD = Pago en Parcialidades o Diferido",
        ),
        dict(
            fieldname="mx_forma_pago",
            label="Forma de Pago",
            fieldtype="Link",
            options="MX Payment Form",
            insert_after="mx_metodo_pago",
            fetch_from="customer.mx_default_forma_pago",
        ),
        dict(
            fieldname="mx_exportacion",
            label="Exportación",
            fieldtype="Link",
            options="MX Export Type",
            insert_after="mx_forma_pago",
            default="01",
            description="01 = No aplica",
        ),
        dict(
            fieldname="mx_column_break_cfdi",
            fieldtype="Column Break",
            insert_after="mx_exportacion",
        ),
        dict(
            fieldname="mx_cfdi_uuid",
            label="UUID (Folio Fiscal)",
            fieldtype="Data",
            read_only=1,
            insert_after="mx_column_break_cfdi",
            bold=1,
            in_list_view=1,
        ),
        dict(
            fieldname="mx_cfdi_status",
            label="Estado CFDI",
            fieldtype="Select",
            options="\nPendiente\nTimbrado\nCancelado\nError",
            read_only=1,
            insert_after="mx_cfdi_uuid",
            in_list_view=1,
        ),
        dict(
            fieldname="mx_cfdi_files_section",
            label="Archivos CFDI",
            fieldtype="Section Break",
            insert_after="mx_cfdi_status",
            collapsible=1,
        ),
        dict(
            fieldname="mx_xml_file",
            label="XML Timbrado",
            fieldtype="Attach",
            read_only=1,
            insert_after="mx_cfdi_files_section",
        ),
        dict(
            fieldname="mx_pdf_file",
            label="PDF CFDI",
            fieldtype="Attach",
            read_only=1,
            insert_after="mx_xml_file",
        ),
        dict(
            fieldname="mx_cancellation_reason",
            label="Motivo Cancelación",
            fieldtype="Link",
            options="MX Cancellation Reason",
            insert_after="mx_pdf_file",
            depends_on="eval:doc.mx_cfdi_status=='Cancelado'",
        ),
        dict(
            fieldname="mx_substitute_uuid",
            label="UUID Sustituto",
            fieldtype="Data",
            insert_after="mx_cancellation_reason",
            depends_on="eval:doc.mx_cancellation_reason=='01'",
        ),
    ],
    # ── Sales Invoice Item ──
    "Sales Invoice Item": [
        dict(
            fieldname="mx_clave_prod_serv",
            label="Clave SAT",
            fieldtype="Link",
            options="MX Product Service Key",
            insert_after="item_code",
            fetch_from="item_code.mx_clave_prod_serv",
            in_list_view=1,
            columns=2,
        ),
        dict(
            fieldname="mx_clave_unidad",
            label="Unidad SAT",
            fieldtype="Link",
            options="MX Unit Key",
            insert_after="mx_clave_prod_serv",
            fetch_from="item_code.mx_clave_unidad",
        ),
        dict(
            fieldname="mx_objeto_imp",
            label="Objeto Impuesto",
            fieldtype="Link",
            options="MX Tax Object",
            insert_after="mx_clave_unidad",
            default="02",
            description="02 = Sí objeto del impuesto",
        ),
    ],
    # ── Payment Entry ──
    "Payment Entry": [
        dict(
            fieldname="mx_payment_cfdi_section",
            label="Complemento de Pago CFDI",
            fieldtype="Section Break",
            insert_after="amended_from",
        ),
        dict(
            fieldname="mx_pago_uuid",
            label="UUID Complemento de Pago",
            fieldtype="Data",
            read_only=1,
            insert_after="mx_payment_cfdi_section",
        ),
        dict(
            fieldname="mx_pago_xml",
            label="XML Complemento",
            fieldtype="Attach",
            read_only=1,
            insert_after="mx_pago_uuid",
        ),
        dict(
            fieldname="mx_pago_status",
            label="Estado",
            fieldtype="Select",
            options="\nPendiente\nTimbrado\nError\nNo aplica",
            read_only=1,
            insert_after="mx_pago_xml",
        ),
    ],
    # ── Purchase Invoice ──
    "Purchase Invoice": [
        dict(
            fieldname="mx_purchase_cfdi_section",
            label="CFDI del Proveedor",
            fieldtype="Section Break",
            insert_after="amended_from",
        ),
        dict(
            fieldname="mx_cfdi_uuid_proveedor",
            label="UUID CFDI del Proveedor",
            fieldtype="Data",
            insert_after="mx_purchase_cfdi_section",
        ),
        dict(
            fieldname="mx_xml_recibido",
            label="XML Recibido",
            fieldtype="Attach",
            insert_after="mx_cfdi_uuid_proveedor",
        ),
        dict(
            fieldname="mx_sat_validation_status",
            label="Validación SAT",
            fieldtype="Select",
            options="\nNo validado\nVigente\nCancelado\nNo encontrado",
            read_only=1,
            insert_after="mx_xml_recibido",
        ),
    ],
}


# ═══════════════════════════════════════════════════════════
# INSTALLATION
# ═══════════════════════════════════════════════════════════

def after_install():
    """Se ejecuta después de instalar la app."""
    create_custom_fields(CUSTOM_FIELDS, update=True)
    setup_tax_templates()
    import_small_catalogs()
    frappe.db.commit()
    frappe.msgprint("ERPNext México instalado correctamente. Configure su PAC en MX CFDI Settings.")


def after_app_install(app_name: str):
    """Se ejecuta cuando cualquier app se instala en el sitio.
    Útil para crear campos de nómina si HRMS está presente.
    """
    if app_name == "hrms":
        create_payroll_custom_fields()


def setup_tax_templates():
    """Crea templates de impuestos mexicanos si no existen."""
    from erpnext_mexico.setup.tax_templates import create_tax_templates
    create_tax_templates()


def import_small_catalogs():
    """Importa catálogos SAT pequeños desde fixtures JSON.
    Los catálogos pesados (c_ClaveProdServ, c_CodigoPostal) se importan
    con: bench execute erpnext_mexico.sat_catalogs.catalog_importer.import_all
    """
    import json
    import os

    fixtures_dir = os.path.join(
        os.path.dirname(__file__), "sat_catalogs", "fixtures"
    )
    if not os.path.exists(fixtures_dir):
        return

    for filename in sorted(os.listdir(fixtures_dir)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(fixtures_dir, filename)
        with open(filepath) as f:
            records = json.load(f)

        if not records:
            continue

        doctype = records[0].get("doctype")
        if not doctype:
            continue

        existing = frappe.db.count(doctype)
        if existing > 0:
            continue

        for rec in records:
            try:
                doc = frappe.get_doc(rec)
                doc.flags.ignore_permissions = True
                doc.insert()
            except frappe.DuplicateEntryError:
                pass
            except Exception as e:
                frappe.log_error(
                    f"Error loading {rec.get('code', '?')} into {doctype}: {e}",
                    title="Catalog Fixture Import Error",
                )

        frappe.db.commit()


def create_payroll_custom_fields():
    """Crea custom fields para nómina (solo si HRMS está instalado)."""
    payroll_fields = {
        "Employee": [
            dict(
                fieldname="mx_employee_fiscal_section",
                label="Datos Fiscales Empleado",
                fieldtype="Section Break",
                insert_after="company_email",
            ),
            dict(
                fieldname="mx_curp",
                label="CURP",
                fieldtype="Data",
                length=18,
                insert_after="mx_employee_fiscal_section",
            ),
            dict(
                fieldname="mx_nss",
                label="NSS (Número Seguridad Social)",
                fieldtype="Data",
                length=11,
                insert_after="mx_curp",
            ),
            dict(
                fieldname="mx_rfc",
                label="RFC",
                fieldtype="Data",
                length=13,
                insert_after="mx_nss",
            ),
            dict(
                fieldname="mx_sbc",
                label="Salario Base de Cotización",
                fieldtype="Currency",
                insert_after="mx_rfc",
            ),
            dict(
                fieldname="mx_sdi",
                label="Salario Diario Integrado",
                fieldtype="Currency",
                insert_after="mx_sbc",
            ),
        ],
    }
    create_custom_fields(payroll_fields, update=True)
