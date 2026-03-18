"""
Generador de CFDI Complemento de Pagos 2.0 usando satcfdi.
Transforma Payment Entry de ERPNext a CFDI tipo P.

Notas de implementación:
- ImpSaldoInsoluto es calculado automáticamente por satcfdi.create.cfd.pago20.Pagos.__init__
- Monto del Pago es calculado automáticamente a partir de DoctoRelacionado.ImpPagado
- fecha_pago requiere un objeto datetime, no str ni date
"""

from datetime import datetime
from decimal import Decimal

import frappe
from frappe import _

from satcfdi.create.cfd import cfdi40
from satcfdi.create.cfd import pago20
from satcfdi.models import Signer


def build_payment_cfdi(payment_entry) -> cfdi40.Comprobante:
    """
    Construye CFDI tipo P (Complemento de Pagos 2.0) desde un Payment Entry.

    Args:
        payment_entry: Documento Payment Entry de ERPNext ya cargado.

    Returns:
        cfdi40.Comprobante listo para firmar y timbrar.
    """
    company = frappe.get_cached_doc("Company", payment_entry.company)

    _validate_company_fiscal_data(company)

    emisor = cfdi40.Emisor(
        rfc=company.mx_rfc,
        nombre=company.mx_nombre_fiscal,
        regimen_fiscal=company.mx_regimen_fiscal,
    )

    receptor = _build_receptor(payment_entry)
    pagos_complemento = _build_pagos(payment_entry)

    comprobante = cfdi40.Comprobante(
        emisor=emisor,
        lugar_expedicion=company.mx_lugar_expedicion,
        receptor=receptor,
        tipo_de_comprobante="P",
        moneda="XXX",
        exportacion="01",
        complemento=pagos_complemento,
    )

    return comprobante


def sign_payment_cfdi(comprobante: cfdi40.Comprobante, company: str) -> cfdi40.Comprobante:
    """
    Firma el CFDI de pago con el CSD activo de la empresa.

    Args:
        comprobante: Objeto CFDI tipo P ya construido.
        company: Nombre de la empresa en ERPNext.

    Returns:
        CFDI firmado con Sello, NoCertificado, Certificado.
    """
    from erpnext_mexico.cfdi.xml_builder import _get_active_certificate, _get_file_bytes

    certificate = _get_active_certificate(company)
    signer = Signer.load(
        certificate=_get_file_bytes(certificate.certificate_file),
        key=_get_file_bytes(certificate.key_file),
        password=certificate.get_password("key_password"),
    )
    comprobante.sign(signer)
    return comprobante


# ── Helpers privados ──────────────────────────────────────────────────────────

def _validate_company_fiscal_data(company) -> None:
    """Valida que la empresa tenga todos los datos fiscales requeridos para CFDI tipo P."""
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


def _build_receptor(payment_entry) -> cfdi40.Receptor:
    """
    Construye el nodo Receptor del CFDI de pago.
    Para Complemento de Pagos el UsoCFDI siempre es 'CP01'.
    """
    if payment_entry.party_type == "Customer":
        party = frappe.get_cached_doc("Customer", payment_entry.party)
        party_name = party.customer_name
    elif payment_entry.party_type == "Supplier":
        party = frappe.get_cached_doc("Supplier", payment_entry.party)
        party_name = party.supplier_name
    else:
        frappe.throw(
            _("Tipo de contraparte no soportado para CFDI: {0}").format(payment_entry.party_type)
        )

    errors = []
    if not getattr(party, "mx_rfc", None):
        errors.append(_("RFC de {0} no configurado").format(payment_entry.party))
    if not getattr(party, "mx_nombre_fiscal", None):
        errors.append(_("Nombre fiscal de {0} no configurado").format(payment_entry.party))
    if not getattr(party, "mx_regimen_fiscal", None):
        errors.append(_("Régimen fiscal de {0} no configurado").format(payment_entry.party))
    if not getattr(party, "mx_domicilio_fiscal_cp", None):
        errors.append(_("Domicilio fiscal (CP) de {0} no configurado").format(payment_entry.party))
    if errors:
        frappe.throw("<br>".join(errors), title=_("Datos fiscales del receptor incompletos"))

    return cfdi40.Receptor(
        rfc=party.mx_rfc,
        nombre=party.mx_nombre_fiscal,
        domicilio_fiscal_receptor=party.mx_domicilio_fiscal_cp,
        regimen_fiscal_receptor=party.mx_regimen_fiscal,
        uso_cfdi="CP01",  # Siempre CP01 para Complemento de Pagos
    )


def _build_pagos(payment_entry) -> pago20.Pagos:
    """
    Construye el complemento Pagos 2.0 con todos los documentos relacionados.

    Notas:
    - ImpSaldoInsoluto es calculado por satcfdi automáticamente
    - Monto del Pago es calculado por satcfdi a partir de DoctoRelacionado.ImpPagado
    - fecha_pago requiere datetime; se convierte desde posting_date (date o str)
    """
    doctos = _build_doctos_relacionados(payment_entry)

    if not doctos:
        frappe.throw(
            _("No hay facturas con UUID CFDI vinculadas a este pago. "
              "Solo facturas PPD timbradas pueden generar Complemento de Pago."),
            title=_("Sin documentos relacionados"),
        )

    # forma_pago del Payment Entry (campo mx_forma_pago); default: 03 = Transferencia electrónica
    forma_pago = getattr(payment_entry, "mx_forma_pago", None)
    if not forma_pago:
        forma_pago = "03"  # Default: Transferencia electrónica
        frappe.msgprint(
            _("Forma de pago no especificada en el Payment Entry. Se usará '03 - Transferencia electrónica' por defecto."),
            indicator="orange",
            alert=True,
        )

    # Moneda del pago — usar la moneda de la cuenta de origen
    moneda_pago = payment_entry.paid_from_account_currency or "MXN"

    # fecha_pago requiere datetime; posting_date puede ser date o str
    fecha_pago = _to_datetime(payment_entry.posting_date)

    pago = pago20.Pago(
        fecha_pago=fecha_pago,
        forma_de_pago_p=forma_pago,
        moneda_p=moneda_pago,
        docto_relacionado=doctos,
        # monto: NO se pasa — satcfdi lo calcula desde sum(DoctoRelacionado.ImpPagado)
        # tipo_cambio_p: solo si la moneda del pago difiere de MXN
        tipo_cambio_p=_get_tipo_cambio(payment_entry, moneda_pago),
    )

    return pago20.Pagos(pago=[pago])


def _build_doctos_relacionados(payment_entry) -> list:
    """
    Construye la lista de DoctoRelacionado para cada factura PPD timbrada
    vinculada al Payment Entry.

    Solo procesa referencias de tipo Sales Invoice con método PPD y UUID.
    """
    doctos = []

    for ref in payment_entry.references:
        if ref.reference_doctype != "Sales Invoice":
            continue

        inv_data = frappe.db.get_value(
            "Sales Invoice",
            ref.reference_name,
            ["mx_metodo_pago", "mx_cfdi_uuid", "currency", "grand_total", "mx_objeto_imp"],
            as_dict=True,
        )

        if not inv_data:
            continue

        if inv_data.mx_metodo_pago != "PPD":
            continue

        if not inv_data.mx_cfdi_uuid:
            frappe.msgprint(
                _("Factura {0} usa PPD pero no tiene UUID CFDI. Se omitirá del complemento.").format(
                    ref.reference_name
                ),
                indicator="orange",
            )
            continue

        # Calcular parcialidad: cuántos pagos previos aplicados a esta factura
        pagos_anteriores_total = _get_pagos_anteriores(
            ref.reference_name, payment_entry.name
        )
        num_parcialidad = _get_num_parcialidad(ref.reference_name, payment_entry.name)

        grand_total = Decimal(str(inv_data.grand_total))
        imp_saldo_ant = max(grand_total - pagos_anteriores_total, Decimal("0"))
        imp_pagado = Decimal(str(ref.allocated_amount))

        # objeto_imp_dr: leer directamente de la factura; default "02" (con impuestos)
        inv_objeto_imp = inv_data.mx_objeto_imp or "02"

        # Extraer serie y folio del nombre de la factura para el complemento
        serie, folio = _parse_serie_folio(ref.reference_name)

        docto = pago20.DoctoRelacionado(
            id_documento=inv_data.mx_cfdi_uuid,
            moneda_dr=inv_data.currency or "MXN",
            num_parcialidad=num_parcialidad,
            imp_saldo_ant=imp_saldo_ant,
            imp_pagado=imp_pagado,
            objeto_imp_dr=inv_objeto_imp,
            serie=serie,
            folio=folio,
            # equivalencia_dr: solo si moneda de la factura difiere de la del pago
            equivalencia_dr=_get_equivalencia_dr(
                inv_data.currency or "MXN",
                payment_entry.paid_from_account_currency or "MXN",
                payment_entry,
            ),
            # ImpSaldoInsoluto es calculado automáticamente por satcfdi
        )
        doctos.append(docto)

    return doctos


def _get_pagos_anteriores(invoice_name: str, current_payment_name: str) -> Decimal:
    """
    Suma los montos ya aplicados a la factura en pagos anteriores, en la moneda
    de la factura (allocated_amount en Payment Entry Reference es siempre en la
    moneda del documento de referencia).

    Excluye el pago actual y solo considera pagos confirmados (docstatus=1).
    """
    result = frappe.db.sql(
        """
        SELECT COALESCE(SUM(per.allocated_amount), 0)
        FROM `tabPayment Entry Reference` per
        JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE per.reference_doctype = 'Sales Invoice'
          AND per.reference_name = %s
          AND pe.docstatus = 1
          AND pe.name != %s
        """,
        (invoice_name, current_payment_name),
    )
    return Decimal(str(result[0][0])) if result else Decimal("0")


def _get_num_parcialidad(invoice_name: str, current_payment_name: str) -> int:
    """
    Determina el número de parcialidad para esta factura.
    Cuenta los pagos anteriores ya aplicados (docstatus=1) + 1.
    """
    count = frappe.db.sql(
        """
        SELECT COUNT(DISTINCT pe.name)
        FROM `tabPayment Entry Reference` per
        JOIN `tabPayment Entry` pe ON pe.name = per.parent
        WHERE per.reference_doctype = 'Sales Invoice'
          AND per.reference_name = %s
          AND pe.docstatus = 1
          AND pe.name != %s
        """,
        (invoice_name, current_payment_name),
    )
    return (count[0][0] if count else 0) + 1


def _get_tipo_cambio(payment_entry, moneda_pago: str):
    """
    Retorna tipo_cambio_p si la moneda del pago difiere de MXN.
    Para pagos en MXN retorna None.
    """
    if moneda_pago == "MXN":
        return None
    conversion = getattr(payment_entry, "source_exchange_rate", None) or getattr(
        payment_entry, "paid_from_account_exchange_rate", None
    )
    if conversion and Decimal(str(conversion)) != Decimal("1"):
        return Decimal(str(conversion))
    return None


def _get_equivalencia_dr(moneda_dr: str, moneda_pago: str, payment_entry) -> Decimal | None:
    """
    Retorna equivalencia_dr cuando la moneda de la factura difiere de la del pago.
    Cuando son iguales retorna None (satcfdi asume 1:1).
    """
    if moneda_dr == moneda_pago:
        return None
    # Usar el tipo de cambio del pago como aproximación
    conversion = getattr(payment_entry, "source_exchange_rate", None)
    if conversion:
        return Decimal(str(conversion))
    frappe.msgprint(
        _("No se encontró tipo de cambio para la equivalencia DR. Se usará 1:1."),
        indicator="orange",
    )
    return Decimal("1")


def _parse_serie_folio(invoice_name: str) -> tuple[str | None, str | None]:
    """
    Extrae serie y folio del nombre de la factura para el nodo DoctoRelacionado.
    Ejemplo: 'FACT-2024-00001' -> serie='FACT', folio='2024-00001'
    Si no hay guión, retorna (None, invoice_name).
    """
    if "-" in invoice_name:
        parts = invoice_name.split("-", 1)
        return parts[0][:25], parts[1][:40]
    return None, invoice_name[:40]


def _to_datetime(date_value) -> datetime:
    """
    Convierte posting_date (str 'YYYY-MM-DD' o date) a datetime con hora 00:00:00.
    satcfdi requiere datetime, no solo date.
    """
    if isinstance(date_value, datetime):
        return date_value
    if hasattr(date_value, "year"):
        # Es un objeto date
        return datetime(date_value.year, date_value.month, date_value.day)
    if isinstance(date_value, str):
        from datetime import date as date_type
        d = frappe.utils.getdate(date_value)
        return datetime(d.year, d.month, d.day)
    return datetime.now()
