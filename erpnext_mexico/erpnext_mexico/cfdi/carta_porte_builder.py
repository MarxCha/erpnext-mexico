"""
Generador de CFDI tipo T (Traslado) con Complemento Carta Porte 3.1 usando satcfdi.
Transforma Delivery Note de ERPNext a CFDI con el complemento de transporte.

Notas de implementación:
- CFDI tipo T no lleva SubTotal/Total ni impuestos — solo mercancias y datos de transporte
- moneda="XXX" es requerida por el SAT para CFDIs tipo T (traslado)
- id_ccp es un UUID v4 único que identifica este complemento ante el SAT
- Las mercancias se leen directamente de los ítems del Delivery Note
- Los datos del vehículo y conductor se leen de los custom fields mx_ del Delivery Note
"""

import uuid
from datetime import datetime
from decimal import Decimal

import frappe
from frappe import _

from satcfdi.create.cfd import cfdi40
from satcfdi.create.cfd.cartaporte31 import (
    CartaPorte,
    Ubicacion,
    Domicilio,
    Mercancias,
    Mercancia,
    Autotransporte,
    IdentificacionVehicular,
    Seguros,
    TiposFigura,
)
from satcfdi.models import Signer


def build_carta_porte_cfdi(delivery_note) -> cfdi40.Comprobante:
    """
    Construye CFDI tipo T con Complemento Carta Porte 3.1 desde un Delivery Note.

    Args:
        delivery_note: Documento Delivery Note de ERPNext ya cargado.

    Returns:
        cfdi40.Comprobante listo para firmar y timbrar.
    """
    company = frappe.get_cached_doc("Company", delivery_note.company)

    _validate_company_fiscal_data(company)
    _validate_carta_porte_data(delivery_note)

    emisor = cfdi40.Emisor(
        rfc=company.mx_rfc,
        nombre=company.mx_nombre_fiscal,
        regimen_fiscal=company.mx_regimen_fiscal,
    )

    receptor = _build_receptor(delivery_note)
    carta_porte_complemento = _build_carta_porte_complement(delivery_note, company)

    # CFDI tipo T requiere un concepto fijo per SAT spec (mismo patrón que tipo P)
    concepto_traslado = cfdi40.Concepto(
        clave_prod_serv="78101800",
        cantidad=Decimal("1"),
        clave_unidad="E48",  # Unidad de servicio
        descripcion="Servicio de transporte de carga",
        valor_unitario=Decimal("0"),
        objeto_imp="01",  # No objeto del impuesto
    )

    comprobante = cfdi40.Comprobante(
        emisor=emisor,
        lugar_expedicion=company.mx_lugar_expedicion,
        receptor=receptor,
        conceptos=[concepto_traslado],
        tipo_de_comprobante="T",
        moneda="XXX",
        exportacion="01",
        complemento=carta_porte_complemento,
    )

    return comprobante


def sign_carta_porte_cfdi(comprobante: cfdi40.Comprobante, company: str) -> cfdi40.Comprobante:
    """
    Firma el CFDI de Carta Porte con el CSD activo de la empresa.

    Args:
        comprobante: Objeto CFDI tipo T ya construido.
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
    """Valida que la empresa tenga todos los datos fiscales requeridos para CFDI tipo T."""
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


def _validate_carta_porte_data(doc) -> None:
    """
    Valida los campos mínimos del Delivery Note para generar la Carta Porte.
    Campos validados: origen, destino, vehículo, conductor, ítems con clave SAT.
    """
    errors = []

    # Origen
    if not getattr(doc, "mx_cp_origen", None):
        errors.append(_("Código Postal de origen (mx_cp_origen) no configurado"))
    if not getattr(doc, "mx_estado_origen", None):
        errors.append(_("Estado de origen (mx_estado_origen) no configurado"))

    # Destino
    if not getattr(doc, "mx_cp_destino", None):
        errors.append(_("Código Postal de destino (mx_cp_destino) no configurado"))
    if not getattr(doc, "mx_estado_destino", None):
        errors.append(_("Estado de destino (mx_estado_destino) no configurado"))
    if not getattr(doc, "mx_distancia_recorrida", None):
        errors.append(_("Distancia recorrida (mx_distancia_recorrida) no configurada"))

    # Vehículo
    if not getattr(doc, "mx_config_vehicular", None):
        errors.append(_("Configuración vehicular (mx_config_vehicular) no configurada"))
    if not getattr(doc, "mx_placa_vehiculo", None):
        errors.append(_("Placa del vehículo (mx_placa_vehiculo) no configurada"))
    if not getattr(doc, "mx_anio_modelo_vehiculo", None):
        errors.append(_("Año modelo del vehículo (mx_anio_modelo_vehiculo) no configurado"))
    if not getattr(doc, "mx_perm_sct", None):
        errors.append(_("Tipo de permiso SCT (mx_perm_sct) no configurado"))
    if not getattr(doc, "mx_num_permiso_sct", None):
        errors.append(_("Número de permiso SCT (mx_num_permiso_sct) no configurado"))

    # Seguros
    if not getattr(doc, "mx_aseguradora_resp_civil", None):
        errors.append(_("Aseguradora de responsabilidad civil (mx_aseguradora_resp_civil) no configurada"))
    if not getattr(doc, "mx_poliza_resp_civil", None):
        errors.append(_("Póliza de responsabilidad civil (mx_poliza_resp_civil) no configurada"))

    # Conductor
    if not getattr(doc, "mx_nombre_conductor", None):
        errors.append(_("Nombre del conductor (mx_nombre_conductor) no configurado"))

    # Ítems
    if not doc.items:
        errors.append(_("El Delivery Note no tiene ítems"))

    for i, item in enumerate(doc.items, 1):
        if not getattr(item, "mx_clave_prod_serv_cp", None) and not getattr(item, "mx_clave_prod_serv", None):
            errors.append(
                _("Línea {0}: Clave Producto/Servicio Carta Porte SAT no configurada").format(i)
            )
        if not getattr(item, "mx_clave_unidad", None):
            errors.append(_("Línea {0}: Clave Unidad SAT no configurada").format(i))
        if not getattr(item, "weight_per_unit", None) and not getattr(item, "mx_peso_en_kg", None):
            errors.append(_("Línea {0}: Peso en KG no configurado (mx_peso_en_kg o weight_per_unit)").format(i))

    if errors:
        frappe.throw("<br>".join(errors), title=_("Datos de Carta Porte incompletos"))


def _build_receptor(delivery_note) -> cfdi40.Receptor:
    """
    Construye el nodo Receptor del CFDI de traslado.
    Para CFDI tipo T el receptor es el destinatario (cliente).
    UsoCFDI = 'S01' (Sin efectos fiscales) para traslados.
    """
    customer = frappe.get_cached_doc("Customer", delivery_note.customer)

    errors = []
    if not getattr(customer, "mx_rfc", None):
        errors.append(_("RFC del cliente no configurado"))
    if not getattr(customer, "mx_nombre_fiscal", None):
        errors.append(_("Nombre fiscal del cliente no configurado"))
    if not getattr(customer, "mx_regimen_fiscal", None):
        errors.append(_("Régimen fiscal del cliente no configurado"))
    if not getattr(customer, "mx_domicilio_fiscal_cp", None):
        errors.append(_("Domicilio fiscal (CP) del cliente no configurado"))
    if errors:
        frappe.throw("<br>".join(errors), title=_("Datos fiscales del receptor incompletos"))

    return cfdi40.Receptor(
        rfc=customer.mx_rfc,
        nombre=customer.mx_nombre_fiscal,
        domicilio_fiscal_receptor=customer.mx_domicilio_fiscal_cp,
        regimen_fiscal_receptor=customer.mx_regimen_fiscal,
        uso_cfdi="S01",  # Sin efectos fiscales — traslados
    )


def _build_carta_porte_complement(doc, company) -> CartaPorte:
    """
    Construye el nodo CartaPorte 3.1 completo con ubicaciones, mercancias y figura transporte.
    """
    id_ccp = str(uuid.uuid4())

    # Transporte internacional: leer del documento o default "No"
    transp_internac = getattr(doc, "mx_transp_internac", None) or "No"

    ubicaciones = _build_ubicaciones(doc, company)
    mercancias = _build_mercancias(doc)
    figura_transporte = _build_figura_transporte(doc)

    return CartaPorte(
        id_ccp=id_ccp,
        transp_internac=transp_internac,
        ubicaciones=ubicaciones,
        mercancias=mercancias,
        figura_transporte=figura_transporte,
    )


def _build_ubicaciones(doc, company) -> list:
    """
    Construye la lista de ubicaciones [Origen, Destino].

    Origen: dirección de la empresa (almacén de envío) o los campos mx_*_origen del DN.
    Destino: dirección del cliente o los campos mx_*_destino del DN.
    """
    # RFC para Origen: RFC de la empresa emisora
    rfc_origen = company.mx_rfc

    # RFC para Destino: RFC del cliente
    customer_rfc = frappe.db.get_value("Customer", doc.customer, "mx_rfc") or "XAXX010101000"

    # Fecha y hora de salida del origen
    fecha_hora_salida = _build_fecha_hora(doc.posting_date, doc.posting_time)

    origen = Ubicacion(
        tipo_ubicacion="Origen",
        id_ubicacion="OR" + "000001",
        rfc_remitente_destinatario=rfc_origen,
        fecha_hora_salida_llegada=fecha_hora_salida,
        domicilio=Domicilio(
            estado=getattr(doc, "mx_estado_origen", None) or "MEX",
            pais="MEX",
            codigo_postal=getattr(doc, "mx_cp_origen", None) or company.mx_lugar_expedicion,
            municipio=getattr(doc, "mx_municipio_origen", None) or None,
            localidad=getattr(doc, "mx_localidad_origen", None) or None,
            referencia=getattr(doc, "mx_referencia_origen", None) or None,
            calle=getattr(doc, "mx_calle_origen", None) or None,
        ),
    )

    distancia_km = Decimal(str(doc.mx_distancia_recorrida or "1"))

    # Fecha de llegada estimada: misma fecha + 1 hora por simplicidad
    from datetime import timedelta
    fecha_hora_llegada = fecha_hora_salida + timedelta(hours=1)

    destino = Ubicacion(
        tipo_ubicacion="Destino",
        id_ubicacion="DE" + "000001",
        rfc_remitente_destinatario=customer_rfc,
        fecha_hora_salida_llegada=fecha_hora_llegada,
        distancia_recorrida=distancia_km,
        domicilio=Domicilio(
            estado=getattr(doc, "mx_estado_destino", None) or "MEX",
            pais="MEX",
            codigo_postal=getattr(doc, "mx_cp_destino", None),
            municipio=getattr(doc, "mx_municipio_destino", None) or None,
            localidad=getattr(doc, "mx_localidad_destino", None) or None,
            referencia=getattr(doc, "mx_referencia_destino", None) or None,
            calle=getattr(doc, "mx_calle_destino", None) or None,
        ),
    )

    return [origen, destino]


def _build_mercancias(doc) -> Mercancias:
    """
    Construye el nodo Mercancias con la lista de bienes transportados.
    Cada ítem del Delivery Note se convierte en un nodo Mercancia.
    """
    lista_mercancias = []
    peso_bruto_total = Decimal("0")

    for item in doc.items:
        # Clave SAT para Carta Porte: preferir mx_clave_prod_serv_cp, luego mx_clave_prod_serv
        bienes_transp = (
            getattr(item, "mx_clave_prod_serv_cp", None)
            or getattr(item, "mx_clave_prod_serv", None)
            or "01010101"  # Genérico si no está configurado
        )

        cantidad = Decimal(str(item.qty))
        clave_unidad = getattr(item, "mx_clave_unidad", None) or "H87"  # H87 = Pieza

        # Peso: usar peso específico para carta porte o weight_per_unit del ítem
        peso_item = (
            getattr(item, "mx_peso_en_kg", None)
            or (float(getattr(item, "weight_per_unit", 0) or 0) * float(item.qty))
        )
        peso_en_kg = Decimal(str(peso_item or "0.001"))  # Mínimo simbólico si no está definido
        peso_bruto_total += peso_en_kg

        # Valor de la mercancía (opcional en traslados internos)
        valor_mercancia = None
        moneda_mercancia = None
        if getattr(item, "rate", None) and float(item.rate or 0) > 0:
            valor_mercancia = Decimal(str(item.amount))
            moneda_mercancia = getattr(doc, "currency", "MXN")

        mercancia = Mercancia(
            bienes_transp=bienes_transp,
            descripcion=(item.description or item.item_name or item.item_code)[:100],
            cantidad=cantidad,
            clave_unidad=clave_unidad,
            peso_en_kg=peso_en_kg,
            valor_mercancia=valor_mercancia,
            moneda=moneda_mercancia,
        )
        lista_mercancias.append(mercancia)

    autotransporte = _build_autotransporte(doc)

    return Mercancias(
        peso_bruto_total=peso_bruto_total,
        unidad_peso="KGM",
        num_total_mercancias=len(lista_mercancias),
        mercancia=lista_mercancias,
        autotransporte=autotransporte,
    )


def _build_autotransporte(doc) -> Autotransporte:
    """
    Construye el nodo Autotransporte con datos del permiso SCT,
    seguro de responsabilidad civil e identificación del vehículo.
    """
    seguros = Seguros(
        asegura_resp_civil=doc.mx_aseguradora_resp_civil,
        poliza_resp_civil=doc.mx_poliza_resp_civil,
    )

    identificacion_vehicular = IdentificacionVehicular(
        config_vehicular=doc.mx_config_vehicular,
        peso_bruto_vehicular=Decimal(str(getattr(doc, "mx_peso_bruto_vehicular", 0) or 0)),
        placa_vm=doc.mx_placa_vehiculo,
        anio_modelo_vm=int(doc.mx_anio_modelo_vehiculo),
    )

    return Autotransporte(
        perm_sct=doc.mx_perm_sct,
        num_permiso_sct=doc.mx_num_permiso_sct,
        seguros=seguros,
        identificacion_vehicular=identificacion_vehicular,
    )


def _build_figura_transporte(doc) -> list:
    """
    Construye la lista de figuras de transporte.
    Por defecto: un operador (tipo_figura="01") con los datos del conductor.
    """
    figura = TiposFigura(
        tipo_figura="01",  # 01 = Operador
        nombre_figura=doc.mx_nombre_conductor,
        rfc_figura=getattr(doc, "mx_rfc_conductor", None) or None,
        num_licencia=getattr(doc, "mx_num_licencia_conductor", None) or None,
    )
    return [figura]


def _build_fecha_hora(posting_date, posting_time) -> datetime:
    """
    Construye un objeto datetime combinando posting_date y posting_time del Delivery Note.
    satcfdi requiere datetime para fecha_hora_salida_llegada.
    """
    if isinstance(posting_date, datetime):
        return posting_date

    # Convertir posting_date (str 'YYYY-MM-DD' o date) a date
    if hasattr(posting_date, "year"):
        d = posting_date
    else:
        d = frappe.utils.getdate(posting_date)

    # posting_time puede ser timedelta, str 'HH:MM:SS' o None
    hour, minute, second = 0, 0, 0
    if posting_time:
        if hasattr(posting_time, "seconds"):
            # timedelta
            total_seconds = int(posting_time.total_seconds())
            hour = total_seconds // 3600
            minute = (total_seconds % 3600) // 60
            second = total_seconds % 60
        elif isinstance(posting_time, str) and ":" in posting_time:
            parts = posting_time.split(":")
            hour = int(parts[0]) if parts[0] else 0
            minute = int(parts[1]) if len(parts) > 1 else 0
            second = int(parts[2]) if len(parts) > 2 else 0

    return datetime(d.year, d.month, d.day, hour, minute, second)
