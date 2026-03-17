"""
Override para Payment Entry — Complemento de Pagos 2.0.
Se ejecuta vía doc_events en hooks.py.
"""

import frappe
from frappe import _


def validate(doc, method=None):
    """
    Validación pre-submit del Payment Entry.

    - Verifica que las facturas PPD referenciadas tengan UUID CFDI
    - Emite advertencias (no detiene el guardado)
    """
    if not _is_mexico_company(doc.company):
        return

    _check_ppd_invoices(doc)


def on_submit(doc, method=None):
    """
    Al enviar el Payment Entry: genera y timbra el Complemento de Pagos CFDI
    si alguna factura referenciada usa método PPD.

    Comportamiento según configuración:
    - auto_stamp_on_submit=True  -> timbra automáticamente
    - auto_stamp_on_submit=False -> marca como 'Pendiente' para timbrado manual
    """
    if not _is_mexico_company(doc.company):
        return

    if not _needs_payment_complement(doc):
        doc.db_set("mx_pago_status", "No aplica", update_modified=False)
        return

    settings = _get_cfdi_settings()
    if not settings or not settings.auto_stamp_on_submit:
        doc.db_set("mx_pago_status", "Pendiente", update_modified=False)
        return

    stamp_payment_complement(doc)


def stamp_payment_complement(doc) -> None:
    """
    Proceso completo de timbrado del Complemento de Pagos 2.0.

    1. Construir CFDI tipo P con satcfdi
    2. Firmar con CSD de la empresa
    3. Enviar a PAC para timbrado
    4. Almacenar UUID, XML como adjunto
    5. Registrar en MX CFDI Log

    Args:
        doc: Documento Payment Entry de ERPNext ya cargado.
    """
    from erpnext_mexico.cfdi.payment_builder import build_payment_cfdi, sign_payment_cfdi
    from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher

    try:
        # 1. Construir CFDI tipo P
        comprobante = build_payment_cfdi(doc)

        # 2. Firmar con CSD
        comprobante = sign_payment_cfdi(comprobante, doc.company)

        # 3. Timbrar con PAC
        pac = PACDispatcher.get_pac(doc.company)
        result = pac.stamp(str(comprobante))

        if not result.success:
            _handle_stamp_error(doc, result.error_message)
            return

        # 4. Almacenar XML como adjunto privado
        xml_filename = f"CFDI_Pago_{doc.name}_{result.uuid}.xml"
        xml_file = _save_attachment(doc, xml_filename, result.xml_stamped, "text/xml")

        doc.db_set("mx_pago_uuid", result.uuid, update_modified=False)
        doc.db_set("mx_pago_status", "Timbrado", update_modified=False)
        doc.db_set("mx_pago_xml", xml_file.file_url, update_modified=False)

        # 5. Registrar en MX CFDI Log
        _create_cfdi_log(doc, result)

        frappe.msgprint(
            _("Complemento de Pago timbrado exitosamente.<br>UUID: <b>{0}</b>").format(result.uuid),
            title=_("Timbrado exitoso"),
            indicator="green",
        )

    except Exception as e:
        _handle_stamp_error(doc, str(e))


@frappe.whitelist()
def retry_stamp_payment(payment_entry_name: str) -> None:
    """
    Reintentar timbrado del Complemento de Pagos (llamado desde botón en UI).

    Args:
        payment_entry_name: Nombre del Payment Entry.
    """
    doc = frappe.get_doc("Payment Entry", payment_entry_name)
    doc.check_permission("submit")

    if doc.mx_pago_status == "Timbrado":
        frappe.throw(
            _("Este pago ya está timbrado (UUID: {0})").format(doc.mx_pago_uuid),
            title=_("Ya timbrado"),
        )

    if not _needs_payment_complement(doc):
        frappe.throw(
            _("Este pago no requiere Complemento de Pagos CFDI (ninguna factura PPD vinculada)."),
            title=_("No aplica"),
        )

    stamp_payment_complement(doc)


# ── Helpers privados ──────────────────────────────────────────────────────────

def _is_mexico_company(company: str) -> bool:
    """Verifica si la empresa tiene configuración fiscal mexicana (RFC definido)."""
    return bool(frappe.db.get_value("Company", company, "mx_rfc"))


def _get_cfdi_settings():
    """Obtiene MX CFDI Settings (Single DocType), o None si no está configurado."""
    try:
        return frappe.get_single("MX CFDI Settings")
    except Exception:
        return None


def _needs_payment_complement(doc) -> bool:
    """
    Determina si el pago requiere Complemento de Pagos CFDI.
    Retorna True si alguna factura Sales Invoice referenciada usa método PPD.
    """
    for ref in doc.references:
        if ref.reference_doctype == "Sales Invoice":
            metodo = frappe.db.get_value(
                "Sales Invoice", ref.reference_name, "mx_metodo_pago"
            )
            if metodo == "PPD":
                return True
    return False


def _check_ppd_invoices(doc) -> None:
    """
    Emite advertencias si facturas PPD referenciadas no tienen UUID CFDI.
    No detiene el guardado — solo informa al usuario.
    """
    for ref in doc.references:
        if ref.reference_doctype != "Sales Invoice":
            continue
        inv_data = frappe.db.get_value(
            "Sales Invoice",
            ref.reference_name,
            ["mx_metodo_pago", "mx_cfdi_uuid"],
            as_dict=True,
        )
        if inv_data and inv_data.mx_metodo_pago == "PPD" and not inv_data.mx_cfdi_uuid:
            frappe.msgprint(
                _(
                    "Factura <b>{0}</b> usa método PPD pero no tiene UUID CFDI. "
                    "El complemento de pago no se podrá generar hasta que la factura esté timbrada."
                ).format(ref.reference_name),
                indicator="orange",
                alert=True,
            )


def _handle_stamp_error(doc, error_message: str) -> None:
    """Registra el error de timbrado y lanza excepción al usuario."""
    doc.db_set("mx_pago_status", "Error", update_modified=False)
    frappe.log_error(
        message=error_message,
        title=f"Error timbrado complemento pago: {doc.name}",
    )
    frappe.throw(
        _("Error al timbrar Complemento de Pago: {0}").format(error_message),
        title=_("Error de timbrado"),
    )


def _save_attachment(doc, filename: str, content: str, content_type: str):
    """Guarda un archivo como adjunto privado al documento."""
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "attached_to_doctype": doc.doctype,
        "attached_to_name": doc.name,
        "content": content,
        "is_private": 1,
    })
    file_doc.save(ignore_permissions=True)
    return file_doc


def _create_cfdi_log(doc, result) -> None:
    """Crea registro en MX CFDI Log para el complemento de pago."""
    frappe.get_doc({
        "doctype": "MX CFDI Log",
        "reference_doctype": "Payment Entry",
        "reference_name": doc.name,
        "cfdi_type": "P",
        "uuid": result.uuid,
        "status": "Stamped",
        "xml_stamped": result.xml_stamped,
        "pac_used": frappe.db.get_single_value("MX CFDI Settings", "pac_provider"),
        "stamped_at": result.fecha_timbrado,
    }).insert(ignore_permissions=True)
