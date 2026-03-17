"""
DIOT 2025 Page — Server helpers.
The heavy lifting is in erpnext_mexico.diot.diot_generator; this module
only provides a thin bridge that the page JS can whitelist-call.
"""
# The @frappe.whitelist functions are defined in diot_generator.
# Import them here so Frappe's permission system resolves them through
# this page's module path as well.
from erpnext_mexico.diot.diot_generator import generate_diot, download_diot  # noqa: F401
