"""
Generador de XML CFDI 4.0 usando satcfdi.
Transforma datos de Sales Invoice / Payment Entry / Salary Slip
a objetos satcfdi para generar el XML fiscal.
"""

import os
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

    # Receptor — satcfdi usa domicilio_fiscal_receptor y regimen_fiscal_receptor
    receptor = cfdi40.Receptor(
        rfc=customer.mx_rfc,
        nombre=customer.mx_nombre_fiscal,
        domicilio_fiscal_receptor=customer.mx_domicilio_fiscal_cp,
        regimen_fiscal_receptor=customer.mx_regimen_fiscal,
        uso_cfdi=doc.mx_uso_cfdi,
    )

    # Conceptos
    conceptos = [_build_concepto(item) for item in doc.items]

    # tipo_cambio debe ser Decimal (no str); solo se incluye si la moneda no es MXN
    tipo_cambio = (
        Decimal(str(doc.conversion_rate)) if doc.currency and doc.currency != "MXN" else None
    )

    # Construir comprobante — lugar_expedicion es el 2do argumento posicional requerido
    comprobante = cfdi40.Comprobante(
        emisor=emisor,
        lugar_expedicion=company.mx_lugar_expedicion,
        receptor=receptor,
        conceptos=conceptos,
        forma_pago=doc.mx_forma_pago if doc.mx_metodo_pago == "PUE" else "99",
        metodo_pago=doc.mx_metodo_pago,
        tipo_de_comprobante="I",
        moneda=doc.currency or "MXN",
        tipo_cambio=tipo_cambio,
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
        company: Nombre de la empresa en ERPNext.

    Returns:
        CFDI firmado (con atributos Sello, NoCertificado, Certificado).
    """
    certificate = _get_active_certificate(company)

    # El campo de contraseña en MX Digital Certificate se llama 'key_password'
    signer = Signer.load(
        certificate=_get_file_bytes(certificate.certificate_file),
        key=_get_file_bytes(certificate.key_file),
        password=certificate.get_password("key_password"),
    )

    comprobante.sign(signer)
    return comprobante


def get_cfdi_xml_bytes(comprobante: cfdi40.Comprobante, pretty_print: bool = False) -> bytes:
    """
    Returns the XML representation of a Comprobante as bytes.

    Args:
        comprobante: Signed or unsigned Comprobante object.
        pretty_print: If True, output is indented for readability.

    Returns:
        UTF-8 encoded XML bytes including the XML declaration.
    """
    return comprobante.xml_bytes(pretty_print=pretty_print, xml_declaration=True)


def _build_concepto(item) -> cfdi40.Concepto:
    """Construye un Concepto CFDI desde un Sales Invoice Item."""
    traslados = []
    retenciones = []

    # Asumimos IVA 16% trasladado cuando ObjetoImp == "02"
    # satcfdi calcula Importe automáticamente durante sign() a partir de Base * TasaOCuota
    if item.mx_objeto_imp == "02":
        base = Decimal(str(item.amount)) - Decimal(str(item.discount_amount or 0))
        traslados.append(
            cfdi40.Traslado(
                impuesto="002",  # IVA
                tipo_factor="Tasa",
                tasa_o_cuota=Decimal("0.160000"),
                base=base,
                # importe se calcula automáticamente en sign()
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
        cantidad=Decimal(str(item.qty)),
        clave_unidad=item.mx_clave_unidad,
        unidad=item.uom,
        descripcion=item.description or item.item_name,
        valor_unitario=Decimal(str(item.rate)),
        # importe es calculado por satcfdi; no se pasa como str
        descuento=Decimal(str(item.discount_amount)) if item.discount_amount else None,
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
    """
    Obtiene el CSD activo para la empresa.

    Prioridad:
    1. MX CFDI Settings.default_certificate
    2. Primer registro MX Digital Certificate con status='Activo' para la empresa
    """
    settings = frappe.get_single("MX CFDI Settings")
    if settings.default_certificate:
        return frappe.get_doc("MX Digital Certificate", settings.default_certificate)

    # Fallback: buscar cualquier certificado activo de la empresa
    cert_name = frappe.db.get_value(
        "MX Digital Certificate",
        {"company": company, "status": "Activo"},
        "name",
    )
    if not cert_name:
        frappe.throw(
            _("No hay un Certificado de Sello Digital (CSD) activo para {0}").format(company),
            title=_("CSD no encontrado"),
        )
    return frappe.get_doc("MX Digital Certificate", cert_name)


def _get_file_bytes(file_url: str) -> bytes:
    """
    Lee el contenido binario de un archivo adjunto en Frappe v15.

    Para archivos privados (prefijo /private/files/) construye la ruta
    absoluta usando frappe.get_site_path(). Para archivos públicos usa
    frappe.get_site_path('public').
    """
    if not file_url:
        frappe.throw(_("URL de archivo vacía"))

    if file_url.startswith("/private/"):
        # /private/files/nombre.ext -> <site_path>/private/files/nombre.ext
        abs_path = frappe.get_site_path() + file_url
    elif file_url.startswith("/files/"):
        # /files/nombre.ext -> <site_path>/public/files/nombre.ext
        abs_path = frappe.get_site_path("public") + file_url
    else:
        frappe.throw(_("Ruta de archivo no reconocida: {0}").format(file_url))

    if not os.path.isfile(abs_path):
        frappe.throw(
            _("Archivo no encontrado en el servidor: {0}").format(abs_path),
            title=_("Archivo no encontrado"),
        )

    with open(abs_path, "rb") as f:
        return f.read()
