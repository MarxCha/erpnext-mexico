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
        dict(
            fieldname="mx_registro_patronal",
            label="Registro Patronal IMSS",
            fieldtype="Data",
            insert_after="mx_lugar_expedicion",
            description="Número de registro patronal ante el IMSS",
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
        dict(
            fieldname="mx_tipo_operacion_diot",
            label="Tipo Operación (DIOT)",
            fieldtype="Select",
            options="\nServicios Profesionales\nArrendamiento\nOtros",
            insert_after="mx_tipo_tercero_diot",
            default="Otros",
        ),
        dict(
            fieldname="mx_nit_extranjero",
            label="NIT (Extranjero)",
            fieldtype="Data",
            insert_after="mx_tipo_operacion_diot",
            depends_on="eval:doc.mx_tipo_tercero_diot=='Extranjero'",
            description="Número de Identificación Tributaria del proveedor extranjero",
        ),
        dict(
            fieldname="mx_pais_residencia",
            label="País de Residencia (Extranjero)",
            fieldtype="Data",
            insert_after="mx_nit_extranjero",
            depends_on="eval:doc.mx_tipo_tercero_diot=='Extranjero'",
        ),
        dict(
            fieldname="mx_nacionalidad",
            label="Nacionalidad (Extranjero)",
            fieldtype="Data",
            insert_after="mx_pais_residencia",
            depends_on="eval:doc.mx_tipo_tercero_diot=='Extranjero'",
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
        # ── Timbre Fiscal Digital (datos del PAC) ──
        dict(
            fieldname="mx_cfdi_fecha_timbrado",
            label="Fecha de Timbrado",
            fieldtype="Datetime",
            read_only=1,
            insert_after="mx_substitute_uuid",
        ),
        dict(
            fieldname="mx_no_certificado",
            label="No. Certificado Emisor",
            fieldtype="Data",
            read_only=1,
            insert_after="mx_cfdi_fecha_timbrado",
        ),
        dict(
            fieldname="mx_no_certificado_sat",
            label="No. Certificado SAT",
            fieldtype="Data",
            read_only=1,
            insert_after="mx_no_certificado",
        ),
        dict(
            fieldname="mx_sello_cfdi",
            label="Sello Digital CFDI",
            fieldtype="Long Text",
            read_only=1,
            insert_after="mx_no_certificado_sat",
        ),
        dict(
            fieldname="mx_sello_sat",
            label="Sello SAT",
            fieldtype="Long Text",
            read_only=1,
            insert_after="mx_sello_cfdi",
        ),
        dict(
            fieldname="mx_cadena_original_tfd",
            label="Cadena Original del TFD",
            fieldtype="Long Text",
            read_only=1,
            insert_after="mx_sello_sat",
        ),
        dict(
            fieldname="mx_serie",
            label="Serie CFDI",
            fieldtype="Data",
            length=25,
            insert_after="mx_cadena_original_tfd",
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
            fieldname="mx_forma_pago",
            label="Forma de Pago SAT",
            fieldtype="Link",
            options="MX Payment Form",
            insert_after="mx_payment_cfdi_section",
            description="Catálogo c_FormaPago del SAT. Requerido para el Complemento de Pagos 2.0",
        ),
        dict(
            fieldname="mx_pago_uuid",
            label="UUID Complemento de Pago",
            fieldtype="Data",
            read_only=1,
            insert_after="mx_forma_pago",
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
            label="Estado Complemento",
            fieldtype="Select",
            options="\nPendiente\nTimbrado\nError\nNo aplica",
            read_only=1,
            insert_after="mx_pago_xml",
        ),
    ],
    # ── Delivery Note ──
    "Delivery Note": [
        # ── Carta Porte Section ──
        dict(fieldname="mx_carta_porte_section", label="Carta Porte", fieldtype="Section Break", insert_after="amended_from"),
        dict(fieldname="mx_requires_carta_porte", label="Requiere Carta Porte", fieldtype="Check", insert_after="mx_carta_porte_section", default=0, description="Marcar si este envío requiere complemento Carta Porte"),
        dict(fieldname="mx_transp_internac", label="Transporte Internacional", fieldtype="Select", options="\nNo\nSí", insert_after="mx_requires_carta_porte", default="No"),
        # Origin
        dict(fieldname="mx_origen_section", label="Origen", fieldtype="Section Break", insert_after="mx_transp_internac", depends_on="mx_requires_carta_porte"),
        dict(fieldname="mx_rfc_remitente", label="RFC Remitente", fieldtype="Data", insert_after="mx_origen_section"),
        dict(fieldname="mx_estado_origen", label="Estado Origen", fieldtype="Data", insert_after="mx_rfc_remitente"),
        dict(fieldname="mx_cp_origen", label="CP Origen", fieldtype="Data", insert_after="mx_estado_origen"),
        dict(fieldname="mx_calle_origen", label="Calle Origen", fieldtype="Data", insert_after="mx_cp_origen"),
        dict(fieldname="mx_column_break_origen", fieldtype="Column Break", insert_after="mx_calle_origen"),
        # Destination
        dict(fieldname="mx_rfc_destinatario", label="RFC Destinatario", fieldtype="Data", insert_after="mx_column_break_origen"),
        dict(fieldname="mx_estado_destino", label="Estado Destino", fieldtype="Data", insert_after="mx_rfc_destinatario"),
        dict(fieldname="mx_cp_destino", label="CP Destino", fieldtype="Data", insert_after="mx_estado_destino"),
        dict(fieldname="mx_calle_destino", label="Calle Destino", fieldtype="Data", insert_after="mx_cp_destino"),
        dict(fieldname="mx_distancia_recorrida", label="Distancia (km)", fieldtype="Float", insert_after="mx_destino_calle"),
        # Vehicle
        dict(fieldname="mx_vehiculo_section", label="Vehículo y Operador", fieldtype="Section Break", insert_after="mx_distancia_recorrida", depends_on="mx_requires_carta_porte"),
        dict(fieldname="mx_perm_sct", label="Permiso SCT", fieldtype="Data", insert_after="mx_vehiculo_section", description="Tipo de permiso SCT"),
        dict(fieldname="mx_num_permiso_sct", label="No. Permiso SCT", fieldtype="Data", insert_after="mx_perm_sct"),
        dict(fieldname="mx_config_vehicular", label="Config. Vehicular", fieldtype="Data", insert_after="mx_num_permiso_sct"),
        dict(fieldname="mx_placa_vehiculo", label="Placa", fieldtype="Data", insert_after="mx_config_vehicular"),
        dict(fieldname="mx_anio_modelo_vehiculo", label="Año Modelo", fieldtype="Int", insert_after="mx_placa_vehiculo"),
        dict(fieldname="mx_peso_bruto_vehicular", label="Peso Bruto Vehicular (ton)", fieldtype="Float", insert_after="mx_anio_modelo_vehiculo"),
        dict(fieldname="mx_column_break_vehiculo", fieldtype="Column Break", insert_after="mx_peso_bruto_vehicular"),
        dict(fieldname="mx_aseguradora_resp_civil", label="Aseguradora Resp. Civil", fieldtype="Data", insert_after="mx_column_break_vehiculo"),
        dict(fieldname="mx_poliza_resp_civil", label="Póliza Resp. Civil", fieldtype="Data", insert_after="mx_aseguradora_resp_civil"),
        dict(fieldname="mx_nombre_conductor", label="Nombre Conductor", fieldtype="Data", insert_after="mx_poliza_resp_civil"),
        dict(fieldname="mx_rfc_conductor", label="RFC Conductor", fieldtype="Data", insert_after="mx_nombre_conductor"),
        dict(fieldname="mx_num_licencia_conductor", label="No. Licencia Conductor", fieldtype="Data", insert_after="mx_rfc_conductor"),
        # CFDI status
        dict(fieldname="mx_cp_cfdi_section", label="CFDI Carta Porte", fieldtype="Section Break", insert_after="mx_num_licencia_conductor", collapsible=1),
        dict(fieldname="mx_carta_porte_uuid", label="UUID Carta Porte", fieldtype="Data", read_only=1, insert_after="mx_cp_cfdi_section"),
        dict(fieldname="mx_carta_porte_status", label="Estado Carta Porte", fieldtype="Select", options="\nPendiente\nTimbrado\nError\nNo aplica", read_only=1, insert_after="mx_carta_porte_uuid"),
        dict(fieldname="mx_carta_porte_xml", label="XML Carta Porte", fieldtype="Attach", read_only=1, insert_after="mx_carta_porte_status"),
    ],
    # ── Delivery Note Item ──
    "Delivery Note Item": [
        dict(
            fieldname="mx_clave_prod_serv_cp",
            label="Clave SAT Carta Porte",
            fieldtype="Data",
            insert_after="item_code",
            description="Clave de producto/servicio para Carta Porte (c_BienesTransp). Sobreescribe mx_clave_prod_serv para transporte.",
        ),
        dict(
            fieldname="mx_peso_en_kg",
            label="Peso (KG)",
            fieldtype="Float",
            insert_after="mx_clave_prod_serv_cp",
            description="Peso de la mercancía en kilogramos para la Carta Porte.",
        ),
    ],
    # ── Salary Slip ──
    "Salary Slip": [
        dict(fieldname="mx_nomina_section", label="CFDI Nómina", fieldtype="Section Break", insert_after="amended_from"),
        dict(fieldname="mx_tipo_nomina", label="Tipo Nómina", fieldtype="Select", options="\nO\nE", insert_after="mx_nomina_section", default="O", description="O=Ordinaria, E=Extraordinaria"),
        dict(fieldname="mx_nomina_uuid", label="UUID Nómina", fieldtype="Data", read_only=1, insert_after="mx_tipo_nomina"),
        dict(fieldname="mx_nomina_status", label="Estado CFDI Nómina", fieldtype="Select", options="\nPendiente\nTimbrado\nError\nNo aplica", read_only=1, insert_after="mx_nomina_uuid"),
        dict(fieldname="mx_nomina_xml", label="XML Nómina", fieldtype="Attach", read_only=1, insert_after="mx_nomina_status"),
        dict(fieldname="mx_nomina_fecha_timbrado", label="Fecha de Timbrado", fieldtype="Datetime", read_only=1, insert_after="mx_nomina_xml"),
        dict(fieldname="mx_subsidio_al_empleo", label="Subsidio al Empleo", fieldtype="Currency", insert_after="mx_nomina_fecha_timbrado", description="Importe del subsidio al empleo aplicable (OtroPago tipo 002 en CFDI)."),
    ],
    # ── Salary Component ──
    "Salary Component": [
        dict(fieldname="mx_sat_section", label="Clasificación SAT Nómina", fieldtype="Section Break", insert_after="description"),
        dict(fieldname="mx_tipo_percepcion_sat", label="Tipo Percepción SAT", fieldtype="Data", insert_after="mx_sat_section", description="Clave SAT: 001=Sueldos, 002=Gratificación, etc."),
        dict(fieldname="mx_tipo_deduccion_sat", label="Tipo Deducción SAT", fieldtype="Data", insert_after="mx_tipo_percepcion_sat", description="Clave SAT: 001=Seguridad Social, 002=ISR, etc."),
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
    # Filter out custom fields for DocTypes that don't exist (e.g., Salary Slip without HRMS)
    safe_fields = {}
    for dt, fields in CUSTOM_FIELDS.items():
        if frappe.db.exists("DocType", dt):
            safe_fields[dt] = fields
        else:
            frappe.logger().warning(
                f"Skipping custom fields for {dt} — DocType not found (install HRMS for payroll fields)"
            )
    create_custom_fields(safe_fields, update=True)
    setup_tax_templates()
    import_small_catalogs()
    install_print_formats()
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


def install_print_formats():
    """Instala print formats CFDI desde fixtures JSON.
    Lee todos los archivos print_formats/**/*.json y crea/actualiza
    los registros de Print Format en la base de datos.
    """
    import json
    import os

    pf_base = os.path.join(os.path.dirname(__file__), "setup", "print_formats")
    if not os.path.exists(pf_base):
        return

    for root, _dirs, files in os.walk(pf_base):
        for filename in files:
            if not filename.endswith(".json") or filename.startswith("_"):
                continue
            filepath = os.path.join(root, filename)
            with open(filepath) as f:
                records = json.load(f)

            if not isinstance(records, list):
                records = [records]

            for rec in records:
                if rec.get("doctype") != "Print Format":
                    continue
                name = rec.get("name")
                if not name:
                    continue
                try:
                    if frappe.db.exists("Print Format", name):
                        doc = frappe.get_doc("Print Format", name)
                        doc.update(rec)
                        doc.save(ignore_permissions=True)
                    else:
                        doc = frappe.get_doc(rec)
                        doc.flags.ignore_permissions = True
                        doc.insert()
                    frappe.db.commit()
                except Exception as e:
                    frappe.log_error(
                        f"Error installing Print Format '{name}': {e}",
                        title="Print Format Install Error",
                    )


def create_payroll_custom_fields():
    """Crea custom fields para nómina electrónica CFDI 1.2 Rev E (solo si HRMS está instalado)."""
    payroll_fields = {
        # ── Employee — datos fiscales y laborales para nómina ──
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
                description="Clave Única de Registro de Población (18 caracteres). Obligatorio para CFDI Nómina.",
            ),
            dict(
                fieldname="mx_nss",
                label="NSS (Número Seguridad Social)",
                fieldtype="Data",
                length=11,
                insert_after="mx_curp",
                description="Número de Seguridad Social IMSS (11 dígitos).",
            ),
            dict(
                fieldname="mx_rfc",
                label="RFC",
                fieldtype="Data",
                length=13,
                insert_after="mx_nss",
                description="RFC del empleado (13 caracteres). Requerido para CFDI Nómina.",
            ),
            dict(
                fieldname="mx_sbc",
                label="Salario Base de Cotización",
                fieldtype="Currency",
                insert_after="mx_rfc",
                description="Salario Base de Cotización IMSS (SBC).",
            ),
            dict(
                fieldname="mx_sdi",
                label="Salario Diario Integrado",
                fieldtype="Currency",
                insert_after="mx_sbc",
                description="Salario Diario Integrado IMSS (SDI).",
            ),
            dict(
                fieldname="mx_employee_laboral_section",
                label="Datos Laborales CFDI",
                fieldtype="Section Break",
                insert_after="mx_sdi",
                collapsible=1,
            ),
            dict(
                fieldname="mx_tipo_contrato",
                label="Tipo de Contrato (SAT)",
                fieldtype="Select",
                options="\n01\n02\n03\n04\n05\n06\n07\n08\n09\n10\n11\n12\n13\n99",
                insert_after="mx_employee_laboral_section",
                default="01",
                description="Catálogo c_TipoContrato SAT. 01=Indefinido, 02=Obra/Tiempo determinado, etc.",
            ),
            dict(
                fieldname="mx_tipo_regimen_nomina",
                label="Tipo Régimen Nómina (SAT)",
                fieldtype="Select",
                options="\n02\n03\n04\n05\n06\n07\n08\n09\n10\n11\n12\n13\n99",
                insert_after="mx_tipo_contrato",
                default="02",
                description="Catálogo c_TipoRegimen SAT. 02=Sueldos, 03=Jubilados, etc.",
            ),
            dict(
                fieldname="mx_periodicidad_pago",
                label="Periodicidad de Pago (SAT)",
                fieldtype="Select",
                options="\n01\n02\n03\n04\n05\n06\n07\n08\n09\n10\n99",
                insert_after="mx_tipo_regimen_nomina",
                default="04",
                description="Catálogo c_PeriodicidadPago. 01=Diario, 02=Semanal, 03=Catorcenal, 04=Quincenal, 05=Mensual.",
            ),
            dict(
                fieldname="mx_tipo_jornada",
                label="Tipo de Jornada (SAT)",
                fieldtype="Select",
                options="\n01\n02\n03\n04\n05\n06\n07\n08\n99",
                insert_after="mx_periodicidad_pago",
                description="Catálogo c_TipoJornada SAT. 01=Diurna, 02=Nocturna, 03=Mixta, etc.",
            ),
            dict(
                fieldname="mx_riesgo_puesto",
                label="Riesgo de Puesto (IMSS)",
                fieldtype="Select",
                options="\n1\n2\n3\n4\n5\n6\n99",
                insert_after="mx_tipo_jornada",
                description="Clase de riesgo IMSS del puesto. 1=Mínimo, 5=Máximo.",
            ),
            dict(
                fieldname="mx_clave_ent_fed",
                label="Estado donde Trabaja",
                fieldtype="Data",
                length=3,
                insert_after="mx_riesgo_puesto",
                description="Clave del estado SAT (c_Estado). Ej: MEX, JAL, NLE.",
            ),
            dict(
                fieldname="mx_employee_banking_section",
                label="Datos Bancarios CFDI",
                fieldtype="Section Break",
                insert_after="mx_clave_ent_fed",
                collapsible=1,
            ),
            dict(
                fieldname="mx_banco_sat",
                label="Banco (Catálogo SAT)",
                fieldtype="Data",
                length=3,
                insert_after="mx_employee_banking_section",
                description="Clave de banco catálogo c_Banco SAT. Ej: 002=BANAMEX, 006=BANCOMEXT.",
            ),
            dict(
                fieldname="mx_cuenta_clabe",
                label="CLABE Interbancaria",
                fieldtype="Data",
                length=18,
                insert_after="mx_banco_sat",
                description="CLABE interbancaria de 18 dígitos para pago de nómina.",
            ),
        ],
        # ── Salary Slip — campos CFDI nómina ──
        "Salary Slip": [
            dict(
                fieldname="mx_nomina_cfdi_section",
                label="CFDI Nómina",
                fieldtype="Section Break",
                insert_after="amended_from",
            ),
            dict(
                fieldname="mx_nomina_uuid",
                label="UUID CFDI Nómina",
                fieldtype="Data",
                read_only=1,
                insert_after="mx_nomina_cfdi_section",
                bold=1,
                in_list_view=1,
            ),
            dict(
                fieldname="mx_nomina_status",
                label="Estado CFDI Nómina",
                fieldtype="Select",
                options="\nPendiente\nTimbrado\nCancelado\nError",
                read_only=1,
                insert_after="mx_nomina_uuid",
                in_list_view=1,
            ),
            dict(
                fieldname="mx_nomina_xml",
                label="XML Nómina Timbrado",
                fieldtype="Attach",
                read_only=1,
                insert_after="mx_nomina_status",
            ),
            dict(
                fieldname="mx_tipo_nomina",
                label="Tipo de Nómina",
                fieldtype="Select",
                options="\nO\nE",
                insert_after="mx_nomina_xml",
                default="O",
                description="O=Ordinaria (quincena/semana regular), E=Extraordinaria (aguinaldo, liquidación).",
            ),
        ],
        # ── Salary Component — mapeo a catálogos SAT ──
        "Salary Component": [
            dict(
                fieldname="mx_sat_section",
                label="Clasificación SAT (CFDI Nómina)",
                fieldtype="Section Break",
                insert_after="statistical_component",
                collapsible=1,
            ),
            dict(
                fieldname="mx_tipo_percepcion_sat",
                label="Tipo Percepción SAT",
                fieldtype="Data",
                length=3,
                insert_after="mx_sat_section",
                description=(
                    "Catálogo c_TipoPercepcion SAT. "
                    "001=Sueldos, 002=Gratificación, 005=Prima Vacacional, "
                    "010=Comisiones, 019=Horas Extra, 047=Otros. "
                    "Usar 'subsidio' para subsidio al empleo (OtroPago 002)."
                ),
                depends_on="eval:doc.type=='Earning'",
            ),
            dict(
                fieldname="mx_tipo_deduccion_sat",
                label="Tipo Deducción SAT",
                fieldtype="Data",
                length=3,
                insert_after="mx_tipo_percepcion_sat",
                description=(
                    "Catálogo c_TipoDeduccion SAT. "
                    "001=Seguridad Social (IMSS), 002=ISR, 003=INFONAVIT, "
                    "007=Otras deducciones."
                ),
                depends_on="eval:doc.type=='Deduction'",
            ),
            dict(
                fieldname="mx_pct_exento",
                label="Porcentaje Exento (%)",
                fieldtype="Float",
                precision=2,
                insert_after="mx_tipo_deduccion_sat",
                default=0,
                description=(
                    "Porcentaje del importe exento de ISR para esta percepción. "
                    "Ej: 50 = 50% exento (prima vacacional hasta el límite SAT). "
                    "0 = todo gravado (default)."
                ),
                depends_on="eval:doc.type=='Earning'",
            ),
        ],
        # ── Company — datos patronales adicionales para nómina ──
        "Company": [
            dict(
                fieldname="mx_registro_patronal",
                label="Registro Patronal IMSS",
                fieldtype="Data",
                length=11,
                insert_after="mx_lugar_expedicion",
                description="Número de Registro Patronal ante el IMSS (e01 campo en CFDI Nómina).",
            ),
        ],
    }
    create_custom_fields(payroll_fields, update=True)
