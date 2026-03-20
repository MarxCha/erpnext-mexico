"""Security utilities — CSP headers for ERPNext Mexico pages."""

import frappe


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
