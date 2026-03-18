"""Limpieza al desinstalar ERPNext México."""
import frappe


def before_uninstall():
    """Elimina custom fields y property setters creados por la app."""
    delete_custom_fields()


def delete_custom_fields():
    """Elimina todos los custom fields con prefijo mx_ creados por ERPNext Mexico."""
    custom_fields = frappe.get_all(
        "Custom Field",
        filters={"fieldname": ["like", "mx_%"]},
        pluck="name",
    )
    for cf in custom_fields:
        frappe.delete_doc("Custom Field", cf, force=True)

    property_setters = frappe.get_all(
        "Property Setter",
        filters={"name": ["like", "%mx_%"]},
        pluck="name",
    )
    for ps in property_setters:
        frappe.delete_doc("Property Setter", ps, force=True)

    frappe.db.commit()
