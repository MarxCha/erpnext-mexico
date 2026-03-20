"""Security utilities — CSP headers and PII sanitization."""

import re

import frappe


# ═══════════════════════════════════════════════════════════
# CSP HEADERS — Content Security Policy para páginas CFDI
# ═══════════════════════════════════════════════════════════

def add_security_headers():
    """Add security headers to responses from ERPNext Mexico pages."""
    if not frappe.response or not hasattr(frappe.local, "request"):
        return

    path = frappe.local.request.path or ""
    # Apply CSP only to our pages
    mx_paths = ("/app/mx-", "/api/method/erpnext_mexico.")
    if not any(path.startswith(p) for p in mx_paths):
        return

    headers = frappe.local.response.headers if hasattr(frappe.local.response, "headers") else {}
    headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'self'"
    )
    headers["X-Content-Type-Options"] = "nosniff"
    headers["X-Frame-Options"] = "SAMEORIGIN"
    headers["Referrer-Policy"] = "strict-origin-when-cross-origin"


# ═══════════════════════════════════════════════════════════
# PII SANITIZATION — Mask RFCs and sensitive data in logs
# ═══════════════════════════════════════════════════════════

_RFC_PATTERN = re.compile(r"[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}")


def mask_rfc(rfc: str) -> str:
    """Mask RFC keeping first 3 chars and last 2: ABC******C9."""
    if not rfc or len(rfc) < 5:
        return "***"
    return rfc[:3] + "*" * (len(rfc) - 5) + rfc[-2:]


def sanitize_log_message(msg: str) -> str:
    """Replace any RFC patterns in a log message with masked versions."""
    if not msg:
        return msg
    return _RFC_PATTERN.sub(lambda m: mask_rfc(m.group()), str(msg))
