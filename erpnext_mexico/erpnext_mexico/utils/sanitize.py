"""PII sanitization for log messages.

Masks Registro Federal de Contribuyentes (RFC) values and other
sensitive identifiers before they are written to Frappe error logs
or frappe.logger() output.

Usage:
    from erpnext_mexico.utils.sanitize import sanitize_log_message, mask_rfc

    frappe.log_error(
        title="Some Error",
        message=sanitize_log_message(str(e)),
    )
"""
import re

# Matches both 12-char (personas morales) and 13-char (personas físicas) RFCs.
# Pattern: 3-4 uppercase letters/Ñ/& + 6 digits (YYMMDD) + 3 alphanumeric homoclave.
_RFC_PATTERN = re.compile(r'\b[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}\b')

# CURP: 18-char identifier for natural persons.
_CURP_PATTERN = re.compile(r'\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b')


def mask_rfc(rfc: str) -> str:
    """Mask an RFC keeping first 3 chars and last 2: e.g. EKU*******C9.

    Args:
        rfc: The RFC string to mask (12 or 13 characters).

    Returns:
        Masked RFC. Returns "***" for values too short to mask safely.
    """
    if not rfc or len(rfc) < 5:
        return "***"
    return rfc[:3] + "*" * (len(rfc) - 5) + rfc[-2:]


def mask_curp(curp: str) -> str:
    """Mask a CURP keeping first 4 chars and last 2: e.g. GOMA**********A5.

    Args:
        curp: The 18-character CURP to mask.

    Returns:
        Masked CURP.
    """
    if not curp or len(curp) < 6:
        return "***"
    return curp[:4] + "*" * (len(curp) - 6) + curp[-2:]


def sanitize_log_message(msg: str) -> str:
    """Replace RFC and CURP patterns in a log message with masked versions.

    Designed to be used as a thin wrapper around any string passed to
    frappe.log_error() or frappe.logger() so that PII does not persist
    in the Frappe Error Log DocType.

    Args:
        msg: The raw log message that may contain PII.

    Returns:
        The same message with all detected RFC/CURP values masked.
    """
    if not msg:
        return msg
    # Apply CURP first (longer pattern, subset characters overlap with RFC)
    msg = _CURP_PATTERN.sub(lambda m: mask_curp(m.group()), msg)
    msg = _RFC_PATTERN.sub(lambda m: mask_rfc(m.group()), msg)
    return msg
