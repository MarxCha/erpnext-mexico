"""
Override para Payment Entry — Complemento de Pagos 2.0.
Se ejecuta vía doc_events en hooks.py.
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
    Validación pre-submit del Payment Entry.

    - Verifica que las facturas PPD referenciadas tengan UUID CFDI
    - Emite advertencias (no detiene el guardado)
    """
    if not is_mexico_company(doc.company):
        return

    _check_ppd_invoices(doc)


def on_cancel(doc, method=None):
    """Al cancelar el Payment Entry: avisar sobre cancelación CFDI pendiente."""
    if not is_mexico_company(doc.company):
        return

    if doc.mx_pago_uuid and doc.mx_pago_status == "Timbrado":
        frappe.msgprint(
            _("El Complemento de Pago CFDI {0} debe cancelarse manualmente ante el SAT. "
              "Use el botón 'Cancelar Complemento' en el pago original.").format(doc.mx_pago_uuid),
            title=_("Cancelación CFDI pendiente"),
            indicator="orange",
        )


def on_submit(doc, method=None):
    """
    Al enviar el Payment Entry: genera y timbra el Complemento de Pagos CFDI
    si alguna factura referenciada usa método PPD.

    Comportamiento según configuración:
    - auto_stamp_on_submit=True  -> timbra automáticamente
    - auto_stamp_on_submit=False -> marca como 'Pendiente' para timbrado manual
    """
    if not is_mexico_company(doc.company):
        return

    if not _needs_payment_complement(doc):
        doc.db_set("mx_pago_status", "No aplica", update_modified=False)
        return

    settings = get_cfdi_settings()
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

        # 3. Timbrar con PAC — pasar Comprobante directo (no XML string)
        pac = PACDispatcher.get_pac(doc.company)
        result = pac.stamp(comprobante)

        if not result.success:
            handle_stamp_error(doc, "mx_pago_status", result.error_message)
            return

        # 4. Almacenar XML como adjunto privado
        xml_filename = f"CFDI_Pago_{doc.name}_{result.uuid}.xml"
        xml_file = save_cfdi_attachment(doc, xml_filename, result.xml_stamped, "text/xml")

        doc.db_set("mx_pago_uuid", result.uuid, update_modified=False)
        doc.db_set("mx_pago_status", "Timbrado", update_modified=False)
        doc.db_set("mx_pago_xml", xml_file.file_url, update_modified=False)

        # 5. Registrar en MX CFDI Log
        create_cfdi_log(doc, result, "P")

        frappe.msgprint(
            _("Complemento de Pago timbrado exitosamente.<br>UUID: <b>{0}</b>").format(result.uuid),
            title=_("Timbrado exitoso"),
            indicator="green",
        )

    except Exception as e:
        handle_stamp_error(doc, "mx_pago_status", str(e))


@frappe.whitelist()
def retry_stamp_payment(payment_entry_name: str) -> None:
    """
    Reintentar timbrado del Complemento de Pagos (llamado desde botón en UI).

    Args:
        payment_entry_name: Nombre del Payment Entry.
    """
    doc = frappe.get_doc("Payment Entry", payment_entry_name)
    doc.check_permission("submit")
    check_stamp_rate_limit(payment_entry_name)

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


