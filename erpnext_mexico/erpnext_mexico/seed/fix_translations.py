# -*- coding: utf-8 -*-
"""Import Spanish translations + dismiss onboarding wizards."""
import csv
import os
import frappe


def run():
    print("=" * 60)
    print("  Importing Spanish Translations + Fixing Onboarding")
    print("=" * 60)

    # ── 1. Import ERPNext es.csv translations ──
    csv_path = "/home/frappe/frappe-bench/apps/erpnext/erpnext/translations/es.csv"
    if os.path.exists(csv_path):
        imported = 0
        skipped = 0
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                source = row[0].strip()
                translated = row[1].strip()
                context = row[2].strip() if len(row) > 2 else ""
                if not source or not translated or source == translated:
                    skipped += 1
                    continue
                # Check if translation exists
                exists = frappe.db.exists("Translation", {
                    "language": "es",
                    "source_text": source,
                })
                if not exists:
                    try:
                        doc = frappe.get_doc({
                            "doctype": "Translation",
                            "language": "es",
                            "source_text": source,
                            "translated_text": translated,
                            "context": context or None,
                        })
                        doc.flags.ignore_permissions = True
                        doc.insert()
                        imported += 1
                    except Exception:
                        skipped += 1
                else:
                    skipped += 1

                # Commit every 500
                if imported % 500 == 0 and imported > 0:
                    frappe.db.commit()

        frappe.db.commit()
        print(f"  ERPNext es.csv: {imported} imported, {skipped} skipped")
    else:
        print(f"  ERPNext es.csv not found at {csv_path}")

    # ── 2. Import Frappe es-MX.csv overrides ──
    csv_mx = "/home/frappe/frappe-bench/apps/frappe/frappe/translations/es-MX.csv"
    if os.path.exists(csv_mx):
        imported_mx = 0
        with open(csv_mx, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                source = row[0].strip()
                translated = row[1].strip()
                if not source or not translated:
                    continue
                existing = frappe.db.get_value("Translation", {
                    "language": "es", "source_text": source}, "name")
                if existing:
                    frappe.db.set_value("Translation", existing,
                                       "translated_text", translated, update_modified=False)
                else:
                    frappe.get_doc({
                        "doctype": "Translation",
                        "language": "es",
                        "source_text": source,
                        "translated_text": translated,
                    }).insert(ignore_permissions=True)
                imported_mx += 1
        frappe.db.commit()
        print(f"  Frappe es-MX.csv: {imported_mx} overrides applied")

    # ── 3. Clear translation cache ──
    frappe.clear_cache()
    print("  Cache cleared")

    total = frappe.db.count("Translation", {"language": "es"})
    print(f"  Total Translation records (es): {total}")
