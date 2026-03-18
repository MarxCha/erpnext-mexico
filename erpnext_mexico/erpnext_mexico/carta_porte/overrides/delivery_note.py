"""
Override para Delivery Note — CFDI tipo T con Complemento Carta Porte 3.1.
Se ejecuta vía doc_events en hooks.py.

Flujo:
1. on_submit detecta si es empresa mexicana y si el Delivery Note requiere Carta Porte
2. Si auto_stamp_on_submit está activo, llama a stamp_carta_porte()
3. stamp_carta_porte() construye → firma → timbra → guarda XML → crea log CFDI
4. retry_stamp_carta_porte() es la API pública para reintento manual desde la UI
"""

import frappe
from frappe import _


def on_submit(doc, method=None):
    """
    Al enviar el Delivery Note: genera, firma y timbra el CFDI Carta Porte.

    Solo actúa si:
    - La empresa tiene configuración fiscal mexicana (mx_rfc definido)
    - El campo mx_requires_carta_porte está marcado en el Delivery Note
    - auto_stamp_on_submit está activo en MX CFDI Settings
    """
    if not _is_mexico_company(doc.company):
        return

    if not getattr(doc, "mx_requires_carta_porte", None):
        return

    settings = _get_cfdi_settings()
    if not settings or not settings.auto_stamp_on_submit:
        doc.db_set("mx_carta_porte_status", "Pendiente", update_modified=False)
        frappe.msgprint(
            _("Carta Porte marcada como pendiente. Use el botón 'Timbrar Carta Porte' para timbrar manualmente."),
            indicator="blue",
            alert=True,
        )
        return

    stamp_carta_porte(doc)


def stamp_carta_porte(doc) -> None:
    """
    Proceso completo de timbrado del CFDI Carta Porte 3.1.

    1. Construir CFDI tipo T con complemento CartaPorte 3.1
    2. Firmar con CSD de la empresa
    3. Enviar a PAC para timbrado
    4. Almacenar UUID, XML como adjunto privado
    5. Registrar en MX CFDI Log

    Args:
        doc: Documento Delivery Note de ERPNext ya cargado.
    """
    from erpnext_mexico.cfdi.carta_porte_builder import build_carta_porte_cfdi, sign_carta_porte_cfdi
    from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
    from erpnext_mexico.cfdi.xml_builder import get_cfdi_xml_bytes

    try:
        # 1. Construir CFDI tipo T con complemento CartaPorte 3.1
        comprobante = build_carta_porte_cfdi(doc)

        # 2. Firmar con CSD
        comprobante = sign_carta_porte_cfdi(comprobante, doc.company)

        # 3. Timbrar con PAC
        pac = PACDispatcher.get_pac(doc.company)
        xml_bytes = get_cfdi_xml_bytes(comprobante)
        result = pac.stamp(xml_bytes.decode("utf-8"))

        if not result.success:
            _handle_stamp_error(doc, result.error_message)
            return

        # 4. Almacenar XML como adjunto privado
        xml_filename = f"CartaPorte_{doc.name}_{result.uuid}.xml"
        xml_file = _save_attachment(doc, xml_filename, result.xml_stamped, "text/xml")

        doc.db_set("mx_carta_porte_uuid", result.uuid, update_modified=False)
        doc.db_set("mx_carta_porte_status", "Timbrado", update_modified=False)
        doc.db_set("mx_carta_porte_xml", xml_file.file_url, update_modified=False)
        doc.db_set("mx_carta_porte_fecha_timbrado", result.fecha_timbrado, update_modified=False)

        # 5. Registrar en MX CFDI Log
        _create_cfdi_log(doc, result)

        frappe.msgprint(
            _("Carta Porte timbrada exitosamente.<br>UUID: <b>{0}</b>").format(result.uuid),
            title=_("Timbrado exitoso"),
            indicator="green",
        )

    except Exception as e:
        _handle_stamp_error(doc, str(e))


def on_cancel(doc, method=None):
    """
    Al cancelar el Delivery Note: avisar sobre cancelación CFDI pendiente.

    La cancelación del CFDI Carta Porte ante el SAT debe realizarse manualmente,
    ya que puede requerir aceptación del receptor según el monto de la mercancía.
    """
    if not _is_mexico_company(doc.company):
        return

    if getattr(doc, "mx_carta_porte_uuid", None) and doc.mx_carta_porte_status == "Timbrado":
        frappe.msgprint(
            _("El CFDI Carta Porte {0} debe cancelarse manualmente ante el SAT. "
              "Ingrese al portal del SAT o contacte a su PAC para realizar la cancelación.").format(
                doc.mx_carta_porte_uuid
            ),
            title=_("Cancelación CFDI Carta Porte pendiente"),
            indicator="orange",
        )


@frappe.whitelist()
def retry_stamp_carta_porte(delivery_note_name: str) -> None:
    """
    Reintentar timbrado de la Carta Porte (llamado desde botón en UI).

    Args:
        delivery_note_name: Nombre del Delivery Note.
    """
    doc = frappe.get_doc("Delivery Note", delivery_note_name)
    doc.check_permission("submit")

    if doc.mx_carta_porte_status == "Timbrado":
        frappe.throw(
            _("Esta Carta Porte ya está timbrada (UUID: {0})").format(doc.mx_carta_porte_uuid),
            title=_("Ya timbrado"),
        )

    if not getattr(doc, "mx_requires_carta_porte", None):
        frappe.throw(
            _("Este Delivery Note no tiene habilitada la Carta Porte (mx_requires_carta_porte no marcado)."),
            title=_("No aplica"),
        )

    stamp_carta_porte(doc)


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


def _handle_stamp_error(doc, error_message: str) -> None:
    """
    Registra el error de timbrado — persiste estado Error antes de lanzar excepción.
    Usa commit separado para asegurar que el estado Error persiste aunque throw revierta.
    """
    frappe.db.set_value(
        doc.doctype, doc.name, "mx_carta_porte_status", "Error", update_modified=False
    )
    frappe.db.commit()
    frappe.log_error(
        message=error_message,
        title=f"Error timbrado Carta Porte: {doc.name}",
    )
    frappe.throw(
        _("Error al timbrar Carta Porte: {0}").format(error_message),
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
    """Crea registro en MX CFDI Log para el CFDI Carta Porte."""
    frappe.get_doc({
        "doctype": "MX CFDI Log",
        "reference_doctype": "Delivery Note",
        "reference_name": doc.name,
        "cfdi_type": "T",
        "uuid": result.uuid,
        "status": "Stamped",
        "xml_stamped": result.xml_stamped,
        "pac_used": frappe.db.get_single_value("MX CFDI Settings", "pac_provider"),
        "stamped_at": result.fecha_timbrado,
    }).insert(ignore_permissions=True)
