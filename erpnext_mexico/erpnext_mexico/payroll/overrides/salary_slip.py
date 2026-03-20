"""
Override para Salary Slip — nómina electrónica CFDI 1.2 Rev E.
Se ejecuta vía doc_events en hooks.py.

Flujo:
1. validate: verifica datos fiscales mínimos del empleado (RFC, CURP)
2. on_submit: si empresa mexicana y auto_stamp_on_submit, timbra automáticamente
3. stamp_nomina: build → sign → stamp PAC → save XML → CFDI log
"""

import frappe
from frappe import _
from erpnext_mexico.cfdi.cfdi_helpers import (
    is_mexico_company,
    get_cfdi_settings,
    save_cfdi_attachment,
    create_cfdi_log,
    handle_stamp_error,
    check_stamp_rate_limit,
)


def validate(doc, method=None):
    """
    Validación pre-submit del Salary Slip.

    - Verifica que la empresa sea mexicana
    - Verifica que el empleado tenga mx_rfc y mx_curp configurados
    - Emite warnings si faltan datos opcionales (NSS, SBC, SDI)
    """
    if not is_mexico_company(doc.company):
        return

    _validate_employee_fiscal_fields(doc)


def on_cancel(doc, method=None):
    """
    Al cancelar el Salary Slip: avisar sobre cancelación CFDI pendiente si aplica.

    La cancelación del CFDI nómina ante el SAT debe hacerse manualmente
    o mediante el botón 'Cancelar CFDI Nómina' disponible en el formulario.
    """
    if not is_mexico_company(doc.company):
        return

    if getattr(doc, "mx_nomina_uuid", None) and doc.mx_nomina_status == "Timbrado":
        frappe.msgprint(
            _("El CFDI Nómina {0} debe cancelarse manualmente ante el SAT. "
              "Use el botón 'Cancelar CFDI Nómina' en el recibo de nómina.").format(
                doc.mx_nomina_uuid
            ),
            title=_("Cancelación CFDI Nómina pendiente"),
            indicator="orange",
        )


def on_submit(doc, method=None):
    """
    Al enviar el Salary Slip: genera y timbra el CFDI tipo N (Nómina 1.2 Rev E)
    si la empresa es mexicana.

    Comportamiento según configuración:
    - auto_stamp_on_submit=True  → timbra automáticamente
    - auto_stamp_on_submit=False → marca como 'Pendiente' para timbrado manual
    """
    if not is_mexico_company(doc.company):
        return

    settings = get_cfdi_settings()
    if not settings or not settings.auto_stamp_on_submit:
        doc.db_set("mx_nomina_status", "Pendiente", update_modified=False)
        return

    stamp_nomina(doc)


def stamp_nomina(doc) -> None:
    """
    Proceso completo de timbrado del CFDI Nómina 1.2 Rev E.

    1. Construir CFDI tipo N con complemento nomina12 usando satcfdi
    2. Firmar con CSD de la empresa
    3. Enviar a PAC para timbrado
    4. Almacenar UUID y XML como adjunto privado
    5. Registrar en MX CFDI Log

    Args:
        doc: Documento Salary Slip de ERPNext ya cargado.
    """
    from erpnext_mexico.cfdi.nomina_builder import build_nomina_cfdi, sign_nomina_cfdi
    from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher

    try:
        # 1. Construir CFDI tipo N
        comprobante = build_nomina_cfdi(doc)

        # 2. Firmar con CSD de la empresa
        comprobante = sign_nomina_cfdi(comprobante, doc.company)

        # 3. Timbrar con PAC — pasar Comprobante directo (no XML string)
        pac = PACDispatcher.get_pac(doc.company)
        result = pac.stamp(comprobante)

        if not result.success:
            handle_stamp_error(doc, "mx_nomina_status", result.error_message)
            return

        # 4. Almacenar XML como adjunto privado
        xml_filename = f"CFDI_Nomina_{doc.name}_{result.uuid}.xml"
        xml_file = save_cfdi_attachment(doc, xml_filename, result.xml_stamped, "text/xml")

        doc.db_set("mx_nomina_uuid", result.uuid, update_modified=False)
        doc.db_set("mx_nomina_status", "Timbrado", update_modified=False)
        doc.db_set("mx_nomina_xml", xml_file.file_url, update_modified=False)
        doc.db_set("mx_nomina_fecha_timbrado", result.fecha_timbrado, update_modified=False)

        # 5. Registrar en MX CFDI Log
        create_cfdi_log(doc, result, "N")

        frappe.msgprint(
            _("CFDI Nómina timbrado exitosamente.<br>UUID: <b>{0}</b>").format(result.uuid),
            title=_("Timbrado exitoso"),
            indicator="green",
        )

    except Exception as e:
        handle_stamp_error(doc, "mx_nomina_status", str(e))


@frappe.whitelist()
def retry_stamp_nomina(salary_slip_name: str) -> None:
    """
    Reintentar timbrado del CFDI Nómina (llamado desde botón en UI).

    Args:
        salary_slip_name: Nombre del Salary Slip.
    """
    doc = frappe.get_doc("Salary Slip", salary_slip_name)
    doc.check_permission("submit")
    check_stamp_rate_limit(salary_slip_name)

    if doc.mx_nomina_status == "Timbrado":
        frappe.throw(
            _("Este recibo de nómina ya está timbrado (UUID: {0})").format(doc.mx_nomina_uuid),
            title=_("Ya timbrado"),
        )

    if not is_mexico_company(doc.company):
        frappe.throw(
            _("La empresa {0} no tiene configuración fiscal mexicana (RFC no definido).").format(
                doc.company
            ),
            title=_("No aplica"),
        )

    stamp_nomina(doc)


# ── Helpers privados ──────────────────────────────────────────────────────────

def _validate_employee_fiscal_fields(doc) -> None:
    """
    Verifica datos fiscales del empleado.
    RFC y CURP son obligatorios para CFDI nómina.
    NSS, SBC, SDI son opcionales pero se avisa si faltan.
    """
    employee_data = frappe.db.get_value(
        "Employee",
        doc.employee,
        ["mx_rfc", "mx_curp", "mx_nss", "mx_sbc", "mx_sdi"],
        as_dict=True,
    )

    if not employee_data:
        return

    errors = []
    warnings = []

    # RFC — requerido para CFDI
    if not employee_data.mx_rfc:
        errors.append(
            _("El empleado <b>{0}</b> no tiene RFC configurado. "
              "Configúrelo en la sección 'Datos Fiscales Empleado'.").format(doc.employee)
        )

    # CURP — obligatorio en complemento nomina12
    if not employee_data.mx_curp:
        errors.append(
            _("El empleado <b>{0}</b> no tiene CURP configurado. "
              "Configúrelo en la sección 'Datos Fiscales Empleado'.").format(doc.employee)
        )

    # NSS — opcional pero necesario para IMSS
    if not employee_data.mx_nss:
        warnings.append(
            _("El empleado {0} no tiene NSS (Número de Seguridad Social) configurado. "
              "Recomendado para nómina electrónica.").format(doc.employee)
        )

    # SBC y SDI — opcionales pero recomendados
    if not employee_data.mx_sbc or not employee_data.mx_sdi:
        warnings.append(
            _("El empleado {0} no tiene SBC/SDI configurados. "
              "Necesarios para declaración IMSS.").format(doc.employee)
        )

    if errors:
        frappe.throw("<br>".join(errors), title=_("Datos fiscales de empleado incompletos"))

    for warning in warnings:
        frappe.msgprint(warning, indicator="orange", alert=True)


