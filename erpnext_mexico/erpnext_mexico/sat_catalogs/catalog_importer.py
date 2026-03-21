"""
Importador de catálogos SAT desde satcfdi.catalogs.
Uso: bench --site dev.localhost execute erpnext_mexico.sat_catalogs.catalog_importer.import_all
"""

import frappe


# ═══════════════════════════════════════════════════════════
# Mapeo: nombre catálogo satcfdi → DocType destino
# ═══════════════════════════════════════════════════════════

SMALL_CATALOGS = {
    "c_RegimenFiscal": {
        "doctype": "MX Fiscal Regime",
        "fields": {"code": "c_RegimenFiscal", "description": "Descripcion"},
        "extra": {"persona_type": lambda r: _persona_type(r)},
    },
    "c_FormaPago": {
        "doctype": "MX Payment Form",
        "fields": {"code": "c_FormaPago", "description": "Descripcion"},
    },
    "c_MetodoPago": {
        "doctype": "MX Payment Method",
        "fields": {"code": "c_MetodoPago", "description": "Descripcion"},
    },
    "c_UsoCFDI": {
        "doctype": "MX CFDI Use",
        "fields": {"code": "c_UsoCFDI", "description": "Descripcion"},
        "extra": {
            "persona_fisica": lambda r: 1 if r.get("Fisica", "Sí") == "Sí" else 0,
            "persona_moral": lambda r: 1 if r.get("Moral", "Sí") == "Sí" else 0,
        },
    },
    "c_ObjetoImp": {
        "doctype": "MX Tax Object",
        "fields": {"code": "c_ObjetoImp", "description": "Descripcion"},
    },
    "c_Exportacion": {
        "doctype": "MX Export Type",
        "fields": {"code": "c_Exportacion", "description": "Descripcion"},
    },
    "c_MotivosCancelacion": {
        "doctype": "MX Cancellation Reason",
        "fields": {"code": "Clave", "description": "Descripcion"},
    },
    "c_TipoRelacion": {
        "doctype": "MX Relation Type",
        "fields": {"code": "c_TipoRelacion", "description": "Descripcion"},
    },
    "c_TipoDeComprobante": {
        "doctype": "MX Voucher Type",
        "fields": {"code": "c_TipoDeComprobante", "description": "Descripcion"},
    },
    "c_Impuesto": {
        "doctype": "MX Tax Type",
        "fields": {"code": "c_Impuesto", "description": "Descripcion"},
    },
    "c_TipoFactor": {
        "doctype": "MX Tax Factor Type",
        "fields": {"code": "c_TipoFactor", "description": "Descripcion"},
    },
    "c_Banco": {
        "doctype": "MX Bank SAT",
        "fields": {"code": "code", "description": "description"},
        "extra": {"razon_social": lambda r: r.get("razon_social", "")},
        "source": "json",  # Loaded from JSON fixture, not SAT Excel
    },
}

HEAVY_CATALOGS = {
    "c_ClaveProdServ": {
        "doctype": "MX Product Service Key",
        "fields": {"code": "c_ClaveProdServ", "description": "Descripcion"},
        "extra": {
            "includes_iva_transfer": lambda r: 1 if r.get("IVATraslado") else 0,
            "includes_ieps_transfer": lambda r: 1 if r.get("IEPSTraslado") else 0,
            "complement": lambda r: r.get("Complemento", ""),
        },
    },
    "c_ClaveUnidad": {
        "doctype": "MX Unit Key",
        "fields": {"code": "c_ClaveUnidad", "description": "Nombre"},
        "extra": {
            "symbol": lambda r: r.get("Simbolo", ""),
        },
    },
    "c_CodigoPostal": {
        "doctype": "MX Postal Code",
        "fields": {"code": "c_CodigoPostal", "description": "c_CodigoPostal"},
        "extra": {
            "state": lambda r: r.get("c_Estado", ""),
            "municipality": lambda r: r.get("c_Municipio", ""),
            "locality": lambda r: r.get("c_Localidad", ""),
        },
    },
    "c_Moneda": {
        "doctype": "MX Currency SAT",
        "fields": {"code": "c_Moneda", "description": "Descripcion"},
        "extra": {
            "decimals": lambda r: int(r.get("Decimales", 2)) if r.get("Decimales") else 2,
            "exchange_variation": lambda r: r.get("PorcentajeVariacion", ""),
        },
    },
}


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def _persona_type(row: dict) -> str:
    """Determina tipo de persona para régimen fiscal."""
    fisica = row.get("Fisica", "")
    moral = row.get("Moral", "")
    if fisica == "Sí" and moral == "Sí":
        return "Ambas"
    elif fisica == "Sí":
        return "Física"
    elif moral == "Sí":
        return "Moral"
    return ""


def _get_catalog_data(catalog_name: str) -> list[dict]:
    """Obtiene datos del catálogo desde satcfdi."""
    try:
        from satcfdi import catalogs
        rows = catalogs.select(catalog_name)
        if rows is None:
            frappe.log_error(f"Catálogo {catalog_name} no encontrado en satcfdi")
            return []
        return list(rows) if not isinstance(rows, list) else rows
    except ImportError:
        frappe.throw("satcfdi no está instalado. Ejecute: pip install satcfdi")
    except Exception as e:
        frappe.log_error(f"Error leyendo catálogo {catalog_name}: {e}")
        return []


def _build_record(row: dict, config: dict) -> dict:
    """Construye un registro para insertar en Frappe."""
    field_map = config["fields"]
    record = {
        "doctype": config["doctype"],
        "code": str(row.get(field_map["code"], "")),
        "description": str(row.get(field_map["description"], "")),
    }
    for field_name, extractor in config.get("extra", {}).items():
        record[field_name] = extractor(row)
    return record


def _import_catalog(
    catalog_name: str,
    config: dict,
    chunk_size: int = 5000,
    force_update: bool = False,
) -> int:
    """Importa un catálogo SAT al DocType correspondiente.

    Args:
        catalog_name: Nombre del catálogo en satcfdi (e.g. ``c_RegimenFiscal``).
        config: Configuración de mapeo de campos del catálogo.
        chunk_size: Número de registros por lote antes de hacer commit.
        force_update: Si es True, actualiza registros existentes en lugar de saltarlos.

    Returns:
        Número total de registros en el DocType tras la importación.
    """
    doctype = config["doctype"]

    existing_count = frappe.db.count(doctype)
    if existing_count > 0 and not force_update:
        frappe.msgprint(
            f"⚠ {doctype} ya tiene {existing_count} registros. "
            "Use force_update=True para actualizar."
        )
        return existing_count

    rows = _get_catalog_data(catalog_name)
    if not rows:
        frappe.msgprint(f"⚠ No se obtuvieron datos para {catalog_name}")
        return 0

    records = []
    for row in rows:
        record = _build_record(row, config)
        if record["code"]:
            records.append(record)

    total = len(records)
    action = "Actualizando" if (existing_count > 0 and force_update) else "Importando"
    frappe.msgprint(f"{action} {total} registros en {doctype}...")

    for i in range(0, total, chunk_size):
        chunk = records[i:i + chunk_size]
        for rec in chunk:
            try:
                doc = frappe.get_doc(rec)
                doc.flags.ignore_permissions = True
                doc.insert()
            except frappe.DuplicateEntryError:
                if force_update:
                    try:
                        key = rec.get("name") or rec.get("code")
                        existing_doc = frappe.get_doc(doctype, key)
                        existing_doc.update(rec)
                        existing_doc.flags.ignore_permissions = True
                        existing_doc.save()
                    except Exception as update_err:
                        frappe.log_error(
                            f"Error actualizando {rec.get('code')} en {doctype}: {update_err}",
                            title=f"Catalog Update Error: {doctype}",
                        )
            except Exception as e:
                frappe.log_error(
                    f"Error insertando {rec.get('code')} en {doctype}: {e}",
                    title=f"Catalog Import Error: {doctype}",
                )
        frappe.db.commit()

    final_count = frappe.db.count(doctype)
    frappe.msgprint(f"✓ {doctype}: {final_count} registros")
    return final_count


# ═══════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════

def import_small_catalogs(force_update: bool = False):
    """Importa catálogos pequeños (<100 registros cada uno).

    Args:
        force_update: Si es True, actualiza registros existentes en lugar de saltarlos.
    """
    results = {}
    for catalog_name, config in SMALL_CATALOGS.items():
        count = _import_catalog(catalog_name, config, force_update=force_update)
        results[config["doctype"]] = count
    return results


def import_heavy_catalogs(force_update: bool = False):
    """Importa catálogos pesados (miles de registros). Ejecutar con bench execute.

    Args:
        force_update: Si es True, actualiza registros existentes en lugar de saltarlos.
    """
    results = {}
    for catalog_name, config in HEAVY_CATALOGS.items():
        count = _import_catalog(catalog_name, config, chunk_size=20_000, force_update=force_update)
        results[config["doctype"]] = count
    return results


def import_all(force_update: bool = False):
    """Importa todos los catálogos SAT.

    Args:
        force_update: Si es True, actualiza registros existentes en lugar de saltarlos.
            Útil cuando el SAT publica nuevos códigos sin borrar el catálogo completo.

    Uso:
        bench --site dev.localhost execute erpnext_mexico.sat_catalogs.catalog_importer.import_all
        bench --site dev.localhost execute erpnext_mexico.sat_catalogs.catalog_importer.import_all --kwargs '{"force_update": true}'
    """
    frappe.msgprint("═══ Importando catálogos SAT pequeños ═══")
    small = import_small_catalogs(force_update=force_update)

    frappe.msgprint("═══ Importando catálogos SAT pesados ═══")
    heavy = import_heavy_catalogs(force_update=force_update)

    results = {**small, **heavy}
    total = sum(results.values())
    frappe.msgprint(f"\n═══ Total: {total} registros en {len(results)} catálogos ═══")
    return results
