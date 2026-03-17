"""Limpieza al desinstalar ERPNext México."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def before_uninstall():
    """Elimina custom fields y property setters creados por la app."""
    delete_custom_fields()

def delete_custom_fields():
    """Elimina todos los custom fields del módulo ERPNext Mexico."""
    custom_fields = frappe.get_all(
        "Custom Field",
        filters={"module": "ERPNext Mexico"},
        pluck="name",
    )
    for cf in custom_fields:
        frappe.delete_doc("Custom Field", cf, force=True)
    
    property_setters = frappe.get_all(
        "Property Setter",
        filters={"module": "ERPNext Mexico"},
        pluck="name",
    )
    for ps in property_setters:
        frappe.delete_doc("Property Setter", ps, force=True)
    
    frappe.db.commit()
