"""Tareas programadas para CFDI."""
import frappe
from frappe import _
from frappe.utils import add_days, now_datetime


def check_cancellation_status():
    """Verifica estado de cancelaciones pendientes (hourly).

    Busca CFDIs con status 'Stamped' cuyo documento de referencia ya fue
    cancelado en ERPNext (docstatus=2) pero el CFDI sigue vigente en el SAT.
    """
    pending = frappe.get_all(
        "MX CFDI Log",
        filters={"status": "Stamped"},
        fields=["name", "uuid", "reference_doctype", "reference_name"],
        limit=50,
    )

    if not pending:
        return

    for log in pending:
        if not log.reference_doctype or not log.reference_name:
            continue

        doc_status = frappe.db.get_value(
            log.reference_doctype, log.reference_name, "docstatus"
        )
        # docstatus 2 = cancelled in ERPNext
        if doc_status == 2:
            status_field_map = {
                "Sales Invoice": "mx_cfdi_status",
                "Payment Entry": "mx_pago_status",
                "Delivery Note": "mx_carta_porte_status",
                "Salary Slip": "mx_nomina_status",
            }
            cfdi_status_field = status_field_map.get(log.reference_doctype)
            if not cfdi_status_field:
                continue
            current_status = frappe.db.get_value(
                log.reference_doctype, log.reference_name, cfdi_status_field
            )
            if current_status == "Timbrado":
                frappe.log_error(
                    title="CFDI sin cancelar en SAT",
                    message=_(
                        "El documento {0} {1} fue cancelado en ERPNext pero el CFDI {2} "
                        "sigue vigente en el SAT. Cancele manualmente."
                    ).format(log.reference_doctype, log.reference_name, log.uuid),
                )


def check_certificate_expiry():
    """Alerta sobre certificados próximos a expirar (daily).

    Registra un error por cada certificado activo que expire dentro de 30 días
    y marca automáticamente como 'Expirado' los que ya superaron su fecha de validez.
    """
    threshold = add_days(now_datetime(), 30)

    expiring = frappe.get_all(
        "MX Digital Certificate",
        filters={
            "status": "Activo",
            "valid_to": ["<=", threshold],
        },
        fields=["name", "mx_rfc", "valid_to", "certificate_owner"],
    )

    for cert in expiring:
        frappe.log_error(
            title=_("Certificado CSD próximo a expirar"),
            message=_(
                "El certificado CSD {0} (RFC: {1}) expira el {2}. "
                "Renuévelo antes de esa fecha para evitar interrupciones en el timbrado."
            ).format(cert.name, cert.mx_rfc, cert.valid_to),
        )

    # Auto-expire certificates past their valid_to date
    expired = frappe.get_all(
        "MX Digital Certificate",
        filters={
            "status": "Activo",
            "valid_to": ["<", now_datetime()],
        },
        pluck="name",
    )
    for cert_name in expired:
        frappe.db.set_value("MX Digital Certificate", cert_name, "status", "Expirado")

    if expired:
        frappe.db.commit()
