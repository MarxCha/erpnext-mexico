"""E2E Test v6: Try CP 26015 (ReachCore source)."""
import frappe


def run():
    print("=== E2E Stamp Test v6 (CP=26015) ===\n")

    if not frappe.db.exists("MX Postal Code", "26015"):
        frappe.get_doc({"doctype": "MX Postal Code", "code": "26015",
                        "description": "Piedras Negras, Coahuila"}).insert(ignore_permissions=True)
        frappe.db.commit()

    # Fix Company
    company = frappe.get_doc("Company", "MD Consultoria TI")
    company.mx_lugar_expedicion = "26015"
    company.save(ignore_permissions=True)

    # Fix Customer
    cust = frappe.get_doc("Customer", "Cliente Prueba MX")
    cust.mx_domicilio_fiscal_cp = "26015"
    cust.save(ignore_permissions=True)
    frappe.db.commit()
    print(f"Company CP=26015, Customer CP=26015")

    income_account = frappe.db.get_value("Account", {
        "company": "MD Consultoria TI", "root_type": "Income", "is_group": 0}, "name")

    si = frappe.get_doc({
        "doctype": "Sales Invoice",
        "company": "MD Consultoria TI",
        "customer": "Cliente Prueba MX",
        "posting_date": "2026-03-19",
        "due_date": "2026-04-19",
        "currency": "MXN",
        "conversion_rate": 1.0,
        "selling_price_list": "Standard Selling",
        "mx_uso_cfdi": "G03",
        "mx_metodo_pago": "PUE",
        "mx_forma_pago": "03",
        "mx_exportacion": "01",
        "items": [{"item_code": "Servicio Consultoria MX", "qty": 1,
                    "rate": 10000.00, "income_account": income_account}],
    })
    si.flags.ignore_permissions = True
    si.flags.ignore_mandatory = True
    si.insert()
    frappe.db.commit()
    print(f"Invoice: {si.name}")

    print("Submitting...")
    try:
        si.submit()
        frappe.db.commit()
        si.reload()

        print(f"\n{'='*50}")
        print(f"  UUID:              {si.mx_cfdi_uuid or 'NOT SET'}")
        print(f"  Status:            {si.mx_cfdi_status or 'NOT SET'}")
        print(f"  XML File:          {si.mx_xml_file or 'NOT SET'}")
        print(f"  Fecha Timbrado:    {si.mx_cfdi_fecha_timbrado or 'NOT SET'}")
        print(f"  No. Cert Emisor:   {si.mx_no_certificado or 'NOT SET'}")
        print(f"  No. Cert SAT:      {si.mx_no_certificado_sat or 'NOT SET'}")
        print(f"{'='*50}")

        if si.mx_cfdi_uuid:
            print(f"\n*** EXITO: CFDI TIMBRADO ***")
            print(f"*** UUID: {si.mx_cfdi_uuid} ***")
        else:
            errors = frappe.get_all("Error Log", fields=["error"],
                                    limit=2, order_by="creation desc")
            for e in errors:
                print(f"\nPAC Error: {str(e.error)[:400]}")
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        errors = frappe.get_all("Error Log", fields=["error"],
                                limit=2, order_by="creation desc")
        for e in errors:
            print(f"PAC Error: {str(e.error)[:400]}")
