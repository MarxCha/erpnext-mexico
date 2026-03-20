"""Shared helpers for CFDI override modules."""
import frappe
from frappe import _
from erpnext_mexico.utils.sanitize import sanitize_log_message as _sanitize


def is_mexico_company(company: str) -> bool:
    """Check if company has Mexican fiscal configuration."""
    return bool(frappe.db.get_value("Company", company, "mx_rfc"))


def get_cfdi_settings():
    """Get MX CFDI Settings singleton, or None if not configured."""
    try:
        return frappe.get_single("MX CFDI Settings")
    except Exception:
        return None


def save_cfdi_attachment(doc, filename: str, content: str, content_type: str):
    """Save a CFDI file as a private attachment."""
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


def create_cfdi_log(doc, result, cfdi_type: str) -> None:
    """Create MX CFDI Log entry."""
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


def check_stamp_rate_limit(document_name: str, max_attempts: int = 10, window_seconds: int = 3600) -> None:
    """Rate limit stamp attempts per document and per user. Max 10/hour per document, 30/hour per user."""
    cache_key = f"cfdi_stamp_attempts:{document_name}"
    attempts = int(frappe.cache().get(cache_key) or 0)
    if attempts >= max_attempts:
        frappe.throw(
            _("Demasiados intentos de timbrado para {0}. Máximo {1} por hora.").format(
                document_name, max_attempts
            )
        )
    frappe.cache().set(cache_key, attempts + 1, expires_in_sec=window_seconds)

    user_key = f"cfdi_stamp_user:{frappe.session.user}"
    user_attempts = int(frappe.cache().get(user_key) or 0)
    if user_attempts >= 30:  # max 30 PAC calls per user per hour
        frappe.throw(
            _("Límite de intentos por usuario excedido. Intente más tarde."),
            title=_("Rate limit"),
        )
    frappe.cache().set(user_key, user_attempts + 1, expires_in_sec=window_seconds)


def validate_company_fiscal_data(company) -> None:
    """Valida datos fiscales mínimos de la empresa para generar cualquier CFDI.

    Consolidated from payment_builder, carta_porte_builder, nomina_builder.
    """
    errors = []
    if not company.mx_rfc:
        errors.append(_("RFC de la empresa no configurado"))
    if not company.mx_nombre_fiscal:
        errors.append(_("Nombre fiscal de la empresa no configurado"))
    if not company.mx_regimen_fiscal:
        errors.append(_("Régimen fiscal de la empresa no configurado"))
    if not company.mx_lugar_expedicion:
        errors.append(_("Lugar de expedición (CP) no configurado"))
    if errors:
        frappe.throw("<br>".join(errors), title=_("Datos fiscales incompletos"))


def sign_any_cfdi(comprobante, company: str):
    """Firma cualquier CFDI (I, E, P, N, T) con el CSD activo de la empresa.

    Consolidated from payment_builder.sign_payment_cfdi,
    carta_porte_builder.sign_carta_porte_cfdi, nomina_builder.sign_nomina_cfdi.
    """
    from erpnext_mexico.cfdi.xml_builder import _get_active_certificate, _get_file_bytes
    from satcfdi.models import Signer

    certificate = _get_active_certificate(company)
    signer = Signer.load(
        certificate=_get_file_bytes(certificate.certificate_file),
        key=_get_file_bytes(certificate.key_file),
        password=certificate.get_password("key_password"),
    )
    comprobante.sign(signer)
    return comprobante


def handle_stamp_error(doc, status_field: str, error_message: str) -> None:
    """Handle stamping errors — log and throw with generic message.

    NOTE: Do NOT call frappe.db.commit() here. This runs inside a
    lifecycle hook transaction. The error status is logged but may not
    persist if the transaction rolls back. Use the Error Log for tracking.
    """
    frappe.log_error(
        message=_sanitize(error_message),
        title=f"Error timbrado CFDI: {doc.name}",
    )
    frappe.throw(
        _("Error al timbrar CFDI. Consulte el registro de errores. Referencia: {0}").format(doc.name),
        title=_("Error de timbrado"),
    )
