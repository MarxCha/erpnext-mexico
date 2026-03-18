"""
Utilidades compartidas para adaptadores PAC.

Funciones comunes usadas por todos los PACs soportados:
- call_with_timeout: envuelve llamadas PAC con timeout vía ThreadPoolExecutor
- extract_tfd_data: extrae metadatos del TimbreFiscalDigital
- map_environment: convierte string de config al enum Environment
- map_cancel_reason: convierte motivo SAT al enum CancelReason
"""

import concurrent.futures

from satcfdi.pacs import CancelReason, Environment


def call_with_timeout(func, *args, timeout: int = 30, **kwargs):
    """
    Call a function with a timeout. Raises TimeoutError if exceeded.

    Used to prevent PAC SOAP/REST calls from hanging indefinitely when
    the external service is down or unresponsive, which would exhaust
    gunicorn workers.

    Args:
        func: Callable to invoke.
        *args: Positional arguments forwarded to func.
        timeout: Maximum seconds to wait (default 30).
        **kwargs: Keyword arguments forwarded to func.

    Raises:
        TimeoutError: If func does not complete within timeout seconds.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"PAC call timed out after {timeout} seconds")


def extract_tfd_data(xml_bytes: bytes) -> dict:
    """
    Extrae atributos del nodo TimbreFiscalDigital del XML timbrado,
    incluyendo la cadena original del TFD.

    Returns:
        dict con FechaTimbrado, SelloSAT, NoCertificadoSAT, CadenaOriginal.
    """
    try:
        from lxml import etree

        if isinstance(xml_bytes, str):
            xml_bytes = xml_bytes.encode("utf-8")

        root = etree.fromstring(xml_bytes)
        ns = "http://www.sat.gob.mx/TimbreFiscalDigital"
        tfd = root.find(f".//{{{ns}}}TimbreFiscalDigital")
        if tfd is None:
            return {}

        data = {
            "FechaTimbrado": tfd.get("FechaTimbrado", ""),
            "SelloSAT": tfd.get("SelloSAT", ""),
            "NoCertificadoSAT": tfd.get("NoCertificadoSAT", ""),
        }

        # Build cadena original TFD per SAT spec:
        # ||Version|UUID|FechaTimbrado|RfcProvCertif|Leyenda|SelloCFD|NoCertificadoSAT|SelloSAT||
        cadena_parts = [
            tfd.get("Version", "1.1"),
            tfd.get("UUID", ""),
            tfd.get("FechaTimbrado", ""),
            tfd.get("RfcProvCertif", ""),
            tfd.get("Leyenda", ""),
            tfd.get("SelloCFD", ""),
            tfd.get("NoCertificadoSAT", ""),
            tfd.get("SelloSAT", ""),
        ]
        data["CadenaOriginal"] = "||" + "|".join(cadena_parts) + "||"

        return data
    except Exception as e:
        import frappe
        frappe.log_error(
            title="Error extracting TFD data",
            message=str(e)
        )
        return {}


def map_environment(environment: str) -> Environment:
    """Mapea string de configuración al enum Environment de satcfdi."""
    if environment.lower() in ("sandbox", "test"):
        return Environment.TEST
    return Environment.PRODUCTION


def map_cancel_reason(reason: str) -> CancelReason:
    """Mapea string de motivo SAT al enum CancelReason de satcfdi."""
    mapping = {
        "01": CancelReason.COMPROBANTE_EMITIDO_CON_ERRORES_CON_RELACION,
        "02": CancelReason.COMPROBANTE_EMITIDO_CON_ERRORES_SIN_RELACION,
        "03": CancelReason.NO_SE_LLEVO_A_CABO_LA_OPERACION,
        "04": CancelReason.OPERACION_NORMATIVA_RELACIONADA_EN_LA_FACTURA_GLOBAL,
    }
    if reason not in mapping:
        raise ValueError(f"Motivo de cancelación inválido: {reason}. Valores válidos: 01, 02, 03, 04")
    return mapping[reason]
