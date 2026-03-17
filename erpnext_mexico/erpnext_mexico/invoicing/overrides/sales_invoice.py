"""
Override para Sales Invoice — timbrado CFDI al validar/enviar.
Se ejecuta vía doc_events en hooks.py.
"""

import frappe
from frappe import _


def validate(doc, method=None):
    """Validación pre-submit: verifica datos fiscales mínimos.
    
    Se ejecuta en validate de Sales Invoice.
    No detiene el guardado, solo marca warnings.
    """
    if not _is_mexico_company(doc.company):
        return

    # Auto-fill desde defaults del cliente
    if doc.customer and not doc.mx_uso_cfdi:
        doc.mx_uso_cfdi = frappe.db.get_value("Customer", doc.customer, "mx_default_uso_cfdi")
    
    if doc.customer and not doc.mx_forma_pago:
        doc.mx_forma_pago = frappe.db.get_value("Customer", doc.customer, "mx_default_forma_pago")

    # Auto-fill claves SAT desde Item master
    for item in doc.items:
        if not item.mx_clave_prod_serv and item.item_code:
            item.mx_clave_prod_serv = frappe.db.get_value("Item", item.item_code, "mx_clave_prod_serv")
        if not item.mx_clave_unidad and item.item_code:
            item.mx_clave_unidad = frappe.db.get_value("Item", item.item_code, "mx_clave_unidad")
        if not item.mx_objeto_imp:
            item.mx_objeto_imp = "02"  # Default: Sí objeto del impuesto


def on_submit(doc, method=None):
    """Al enviar la factura: generar, firmar y timbrar CFDI.
    
    Se ejecuta en on_submit de Sales Invoice.
    """
    if not _is_mexico_company(doc.company):
        return

    settings = _get_cfdi_settings(doc.company)

    if not settings or not settings.auto_stamp_on_submit:
        # Si auto-stamp está desactivado, solo marcar como pendiente
        doc.db_set("mx_cfdi_status", "Pendiente")
        return

    stamp_sales_invoice(doc)


def on_cancel(doc, method=None):
    """Al cancelar la factura en ERPNext: iniciar cancelación CFDI.
    
    Nota: La cancelación del CFDI ante el SAT puede requerir
    aceptación del receptor (para facturas > $1,000 MXN).
    """
    if not _is_mexico_company(doc.company):
        return

    if doc.mx_cfdi_uuid and doc.mx_cfdi_status == "Timbrado":
        # TODO: Implementar flujo de cancelación
        # Por ahora, solo marcar para cancelación manual
        frappe.msgprint(
            _("El CFDI {0} debe cancelarse manualmente ante el SAT. "
              "Use el botón 'Cancelar CFDI' en la factura.").format(doc.mx_cfdi_uuid),
            title=_("Cancelación CFDI pendiente"),
            indicator="orange",
        )


def stamp_sales_invoice(doc) -> None:
    """
    Proceso completo de timbrado de una Sales Invoice.
    
    1. Construir XML CFDI 4.0
    2. Firmar con CSD
    3. Enviar a PAC para timbrado
    4. Almacenar UUID, XML, PDF
    5. Registrar en MX CFDI Log
    """
    from erpnext_mexico.cfdi.xml_builder import build_cfdi_from_sales_invoice, sign_cfdi
    from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher

    try:
        # 1. Construir CFDI
        comprobante = build_cfdi_from_sales_invoice(doc)

        # 2. Firmar con CSD
        comprobante = sign_cfdi(comprobante, doc.company)

        # 3. Timbrar con PAC
        pac = PACDispatcher.get_pac(doc.company)
        result = pac.stamp(str(comprobante))

        if not result.success:
            _handle_stamp_error(doc, result.error_message)
            return

        # 4. Almacenar resultados
        xml_filename = f"CFDI_{doc.name}_{result.uuid}.xml"
        xml_file = _save_attachment(doc, xml_filename, result.xml_stamped, "text/xml")

        doc.db_set("mx_cfdi_uuid", result.uuid, update_modified=False)
        doc.db_set("mx_cfdi_status", "Timbrado", update_modified=False)
        doc.db_set("mx_xml_file", xml_file.file_url, update_modified=False)

        # 5. Registrar en log
        _create_cfdi_log(doc, result, "I")

        frappe.msgprint(
            _("CFDI timbrado exitosamente.<br>UUID: <b>{0}</b>").format(result.uuid),
            title=_("Timbrado exitoso"),
            indicator="green",
        )

    except Exception as e:
        _handle_stamp_error(doc, str(e))


@frappe.whitelist()
def retry_stamp(sales_invoice_name: str) -> None:
    """Reintentar timbrado (llamado desde botón en UI)."""
    doc = frappe.get_doc("Sales Invoice", sales_invoice_name)
    doc.check_permission("submit")

    if doc.mx_cfdi_status == "Timbrado":
        frappe.throw(_("Esta factura ya está timbrada (UUID: {0})").format(doc.mx_cfdi_uuid))

    stamp_sales_invoice(doc)


@frappe.whitelist()
def cancel_cfdi(sales_invoice_name: str, reason: str, substitute_uuid: str = "") -> None:
    """Cancelar CFDI ante el SAT."""
    doc = frappe.get_doc("Sales Invoice", sales_invoice_name)
    doc.check_permission("cancel")

    if doc.mx_cfdi_status != "Timbrado":
        frappe.throw(_("Solo se pueden cancelar CFDIs timbrados"))

    if reason == "01" and not substitute_uuid:
        frappe.throw(_("Motivo 01 requiere UUID del CFDI sustituto"))

    from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher
    from erpnext_mexico.cfdi.xml_builder import _get_active_certificate, _get_file_bytes

    try:
        pac = PACDispatcher.get_pac(doc.company)
        certificate = _get_active_certificate(doc.company)

        result = pac.cancel(
            uuid=doc.mx_cfdi_uuid,
            rfc_emisor=frappe.db.get_value("Company", doc.company, "mx_rfc"),
            certificate=_get_file_bytes(certificate.certificate_file),
            key=_get_file_bytes(certificate.key_file),
            password=certificate.get_password("key_password"),
            reason=reason,
            substitute_uuid=substitute_uuid if reason == "01" else None,
        )

        if result.success:
            doc.db_set("mx_cfdi_status", "Cancelado", update_modified=False)
            doc.db_set("mx_cancellation_reason", reason, update_modified=False)
            if substitute_uuid:
                doc.db_set("mx_substitute_uuid", substitute_uuid, update_modified=False)

            # Update CFDI Log
            log_name = frappe.db.get_value("MX CFDI Log", {"uuid": doc.mx_cfdi_uuid}, "name")
            if log_name:
                frappe.db.set_value("MX CFDI Log", log_name, {
                    "status": "Cancelled",
                    "cancelled_at": frappe.utils.now(),
                })

            frappe.msgprint(
                _("CFDI cancelado exitosamente."),
                title=_("Cancelación exitosa"),
                indicator="green",
            )
        else:
            frappe.throw(
                _("Error al cancelar CFDI: {0}").format(result.error_message),
                title=_("Error de cancelación"),
            )

    except Exception as e:
        frappe.log_error(f"Error cancelando CFDI {doc.mx_cfdi_uuid}: {e}")
        frappe.throw(_("Error al cancelar CFDI: {0}").format(str(e)))


# ── Helpers ──

def _is_mexico_company(company: str) -> bool:
    """Verifica si la empresa tiene configuración fiscal mexicana."""
    rfc = frappe.db.get_value("Company", company, "mx_rfc")
    return bool(rfc)


def _get_cfdi_settings(company: str):
    """Obtiene MX CFDI Settings (Single DocType), o None si no está configurado."""
    try:
        return frappe.get_single("MX CFDI Settings")
    except Exception:
        return None


def _handle_stamp_error(doc, error_message: str) -> None:
    """Maneja errores de timbrado."""
    doc.db_set("mx_cfdi_status", "Error", update_modified=False)
    frappe.log_error(
        message=error_message,
        title=f"Error timbrado CFDI: {doc.name}",
    )
    frappe.throw(
        _("Error al timbrar CFDI: {0}").format(error_message),
        title=_("Error de timbrado"),
    )


def _save_attachment(doc, filename: str, content: str, content_type: str):
    """Guarda un archivo como adjunto al documento."""
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


def _create_cfdi_log(doc, result, cfdi_type: str) -> None:
    """Crea registro en MX CFDI Log."""
    frappe.get_doc({
        "doctype": "MX CFDI Log",
        "reference_doctype": doc.doctype,
        "reference_name": doc.name,
        "cfdi_type": cfdi_type,
        "uuid": result.uuid,
        "status": "Stamped",
        "xml_stamped": result.xml_stamped,
        "pac_used": frappe.db.get_single_value("MX CFDI Settings", "pac_provider"),
        "stamped_at": result.fecha_timbrado,
    }).insert(ignore_permissions=True)
