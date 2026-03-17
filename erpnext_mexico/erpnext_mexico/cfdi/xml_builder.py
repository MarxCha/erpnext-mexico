"""
Generador de XML CFDI 4.0 usando satcfdi.
Transforma datos de Sales Invoice / Payment Entry / Salary Slip
a objetos satcfdi para generar el XML fiscal.
"""

from decimal import Decimal
from typing import Optional

import frappe
from frappe import _

from satcfdi.create.cfd import cfdi40
from satcfdi.models import Signer


def build_cfdi_from_sales_invoice(doc) -> cfdi40.Comprobante:
    """
    Construye un objeto CFDI 4.0 desde un Sales Invoice de ERPNext.
    
    Args:
        doc: frappe.get_doc("Sales Invoice", name) ya cargado.
        
    Returns:
        cfdi40.Comprobante listo para firmar y timbrar.
    """
    company = frappe.get_cached_doc("Company", doc.company)
    customer = frappe.get_cached_doc("Customer", doc.customer)

    # Validaciones previas
    _validate_fiscal_data(company, customer, doc)

    # Emisor
    emisor = cfdi40.Emisor(
        rfc=company.mx_rfc,
        nombre=company.mx_nombre_fiscal,
        regimen_fiscal=company.mx_regimen_fiscal,
    )

    # Receptor
    receptor = cfdi40.Receptor(
        rfc=customer.mx_rfc,
        nombre=customer.mx_nombre_fiscal,
        uso_cfdi=doc.mx_uso_cfdi,
        domicilio_fiscal_receptor=customer.mx_domicilio_fiscal_cp,
        regimen_fiscal_receptor=customer.mx_regimen_fiscal,
    )

    # Conceptos
    conceptos = []
    for item in doc.items:
        concepto = _build_concepto(item)
        conceptos.append(concepto)

    # Construir comprobante
    comprobante = cfdi40.Comprobante(
        emisor=emisor,
        receptor=receptor,
        conceptos=conceptos,
        forma_pago=doc.mx_forma_pago if doc.mx_metodo_pago == "PUE" else "99",
        metodo_pago=doc.mx_metodo_pago,
        tipo_de_comprobante="I",
        moneda=doc.currency or "MXN",
        tipo_cambio=str(doc.conversion_rate) if doc.currency != "MXN" else None,
        lugar_expedicion=company.mx_lugar_expedicion,
        exportacion=doc.mx_exportacion or "01",
        serie=doc.naming_series.replace(".", "").replace("-", "")[:25] if doc.naming_series else None,
        folio=doc.name[:40] if doc.name else None,
    )

    return comprobante


def sign_cfdi(comprobante: cfdi40.Comprobante, company: str) -> cfdi40.Comprobante:
    """
    Firma el CFDI con el Certificado de Sello Digital (CSD) de la empresa.
    
    Args:
        comprobante: Objeto CFDI ya construido.
        company: Nombre de la empresa.
        
    Returns:
        CFDI firmado (con atributos Sello, NoCertificado, Certificado).
    """
    certificate = _get_active_certificate(company)

    signer = Signer.load(
        certificate=_get_file_bytes(certificate.certificate_file),
        key=_get_file_bytes(certificate.key_file),
        password=certificate.get_password("password"),
    )

    comprobante.sign(signer)
    return comprobante


def _build_concepto(item) -> cfdi40.Concepto:
    """Construye un Concepto CFDI desde un Sales Invoice Item."""
    # Determinar impuestos trasladados y retenidos del item
    traslados = []
    retenciones = []

    # TODO: Mapear taxes del item a impuestos SAT
    # Por ahora, asumimos IVA 16% trasladado si ObjetoImp == "02"
    if item.mx_objeto_imp == "02":
        base = Decimal(str(item.amount)) - Decimal(str(item.discount_amount or 0))
        traslados.append(
            cfdi40.Traslado(
                impuesto="002",  # IVA
                tipo_factor="Tasa",
                tasa_o_cuota="0.160000",
                base=str(base),
            )
        )

    impuestos = None
    if traslados or retenciones:
        impuestos = cfdi40.Impuestos(
            traslados=traslados or None,
            retenciones=retenciones or None,
        )

    return cfdi40.Concepto(
        clave_prod_serv=item.mx_clave_prod_serv,
        cantidad=str(item.qty),
        clave_unidad=item.mx_clave_unidad,
        unidad=item.uom,
        descripcion=item.description or item.item_name,
        valor_unitario=str(item.rate),
        importe=str(item.amount),
        descuento=str(item.discount_amount) if item.discount_amount else None,
        objeto_imp=item.mx_objeto_imp or "02",
        no_identificacion=item.item_code,
        impuestos=impuestos,
    )


def _validate_fiscal_data(company, customer, doc) -> None:
    """Validaciones obligatorias antes de generar XML."""
    errors = []

    if not company.mx_rfc:
        errors.append(_("RFC de la empresa no configurado"))
    if not company.mx_nombre_fiscal:
        errors.append(_("Nombre fiscal de la empresa no configurado"))
    if not company.mx_regimen_fiscal:
        errors.append(_("Régimen fiscal de la empresa no configurado"))
    if not company.mx_lugar_expedicion:
        errors.append(_("Lugar de expedición (CP) no configurado"))

    if not customer.mx_rfc:
        errors.append(_("RFC del cliente no configurado"))
    if not customer.mx_nombre_fiscal:
        errors.append(_("Nombre fiscal del cliente no configurado"))
    if not customer.mx_regimen_fiscal:
        errors.append(_("Régimen fiscal del cliente no configurado"))
    if not customer.mx_domicilio_fiscal_cp:
        errors.append(_("Domicilio fiscal (CP) del cliente no configurado"))

    if not doc.mx_uso_cfdi:
        errors.append(_("Uso CFDI no seleccionado"))
    if not doc.mx_metodo_pago:
        errors.append(_("Método de pago no seleccionado"))

    for i, item in enumerate(doc.items, 1):
        if not item.mx_clave_prod_serv:
            errors.append(_("Línea {0}: Clave Producto/Servicio SAT no configurada").format(i))
        if not item.mx_clave_unidad:
            errors.append(_("Línea {0}: Clave Unidad SAT no configurada").format(i))

    if errors:
        frappe.throw(
            "<br>".join(errors),
            title=_("Datos fiscales incompletos"),
        )


def _get_active_certificate(company: str):
    """Obtiene el CSD activo de la empresa."""
    cert_name = frappe.db.get_value(
        "MX Digital Certificate",
        {"company": company, "is_default": 1, "status": "Active"},
        "name",
    )
    if not cert_name:
        frappe.throw(
            _("No hay un Certificado de Sello Digital (CSD) activo para {0}").format(company),
            title=_("CSD no encontrado"),
        )
    return frappe.get_doc("MX Digital Certificate", cert_name)


def _get_file_bytes(file_url: str) -> bytes:
    """Lee el contenido binario de un archivo adjunto en Frappe."""
    file_doc = frappe.get_doc("File", {"file_url": file_url})
    return file_doc.get_content()
