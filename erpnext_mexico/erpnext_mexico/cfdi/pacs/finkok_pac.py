"""
Adaptador PAC para Finkok/Quadrum usando la biblioteca satcfdi.
PAC primario recomendado por costo-beneficio.

Sandbox: demo-facturacion.finkok.com
Docs: wiki.finkok.com

API satcfdi:
  - Finkok(username, password, environment=Environment.PRODUCTION|TEST)
  - .stamp(cfdi: CFDI) -> Document(document_id, xml)
  - .cancel(cfdi, reason: CancelReason, substitution_id, signer: Signer)
      -> CancelationAcknowledgment(code, acuse)
"""

from typing import Optional

from satcfdi.cfdi import CFDI
from satcfdi.models.signer import Signer
from satcfdi.pacs.finkok import (
    CancelReason,
    CancelationAcknowledgment,
    Environment,
    Finkok,
)
from satcfdi.pacs.finkok import cancelacion

from ..pac_interface import CancelResult, PACInterface, StampResult, StatusResult


def _map_environment(environment: str) -> Environment:
    """Mapea string de configuración al enum Environment de satcfdi."""
    if environment.lower() in ("sandbox", "test"):
        return Environment.TEST
    return Environment.PRODUCTION


def _map_cancel_reason(reason: str) -> CancelReason:
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


class FinkokPAC(PACInterface):
    """Implementación de PACInterface para Finkok vía satcfdi."""

    def __init__(self, username: str, password: str, environment: str = "Sandbox"):
        self._client = Finkok(
            username=username,
            password=password,
            environment=_map_environment(environment),
        )

    def stamp(self, xml_signed: str) -> StampResult:
        """
        Timbrar CFDI firmado vía Finkok.

        Args:
            xml_signed: XML del CFDI firmado con CSD como string.

        Returns:
            StampResult con UUID, XML timbrado y metadatos.
        """
        try:
            # satcfdi Finkok.stamp() espera un objeto CFDI, no un string
            cfdi_obj = CFDI.from_string(
                xml_signed.encode() if isinstance(xml_signed, str) else xml_signed
            )
            result = self._client.stamp(cfdi_obj)

            # result es Document(document_id: str, xml: bytes)
            xml_bytes = result.xml
            xml_str = xml_bytes.decode("utf-8") if isinstance(xml_bytes, bytes) else xml_bytes

            # Extraer metadatos del timbre desde el XML timbrado
            tfd_data = _extract_tfd_data(xml_bytes)

            return StampResult(
                uuid=result.document_id,
                xml_stamped=xml_str,
                fecha_timbrado=tfd_data.get("FechaTimbrado", ""),
                sello_sat=tfd_data.get("SelloSAT", ""),
                no_certificado_sat=tfd_data.get("NoCertificadoSAT", ""),
                cadena_original_tfd=tfd_data.get("CadenaOriginal", ""),
                success=True,
            )
        except Exception as e:
            return StampResult(
                uuid="",
                xml_stamped="",
                fecha_timbrado="",
                sello_sat="",
                no_certificado_sat="",
                cadena_original_tfd="",
                success=False,
                error_message=str(e),
            )

    def cancel(
        self,
        uuid: str,
        rfc_emisor: str,
        certificate: bytes,
        key: bytes,
        password: str,
        reason: str,
        substitute_uuid: Optional[str] = None,
    ) -> CancelResult:
        """
        Cancelar CFDI vía Finkok.

        Construye un Signer desde el CSD y arma la solicitud de cancelación
        firmada usando satcfdi.pacs.finkok.cancelacion.

        Args:
            uuid: Folio fiscal UUID del CFDI a cancelar.
            rfc_emisor: RFC del emisor del CFDI.
            certificate: Contenido binario del .cer (DER).
            key: Contenido binario del .key cifrado.
            password: Contraseña del .key.
            reason: Motivo SAT (01, 02, 03, 04).
            substitute_uuid: UUID sustituto (obligatorio para motivo 01).
        """
        try:
            cancel_reason = _map_cancel_reason(reason)

            # Construir Signer desde bytes del CSD
            signer = Signer.load(
                certificate=certificate,
                key=key,
                password=password,
            )

            folio = cancelacion.Folio(
                uuid=uuid,
                motivo=cancel_reason.value,
                folio_sustitucion=substitute_uuid if reason == "01" else None,
            )
            cancelacion_obj = cancelacion.Cancelacion(emisor=signer, folios=folio)

            result = self._client.cancel_comprobante(cancelacion_obj)

            # result es CancelationAcknowledgment(code, acuse)
            acuse_str = ""
            if result.acuse:
                acuse_str = result.acuse.decode("utf-8") if isinstance(result.acuse, bytes) else result.acuse

            return CancelResult(
                success=True,
                acuse_xml=acuse_str,
                status=str(result.code) if result.code else "Cancelado",
            )
        except Exception as e:
            return CancelResult(
                success=False,
                error_message=str(e),
            )

    def get_status(
        self,
        uuid: str,
        rfc_emisor: str,
        rfc_receptor: str,
        total: str,
    ) -> StatusResult:
        """
        Consultar estado de CFDI.

        Nota: satcfdi.pacs.finkok.Finkok no expone get_status directamente.
        Se delega al servicio SAT de consulta pública.
        """
        try:
            from satcfdi.verify import verify_cfdi

            result = verify_cfdi(
                uuid=uuid,
                emisor_rfc=rfc_emisor,
                receptor_rfc=rfc_receptor,
                total=total,
            )
            return StatusResult(
                is_cancellable=getattr(result, "is_cancellable", False),
                status=getattr(result, "estado", ""),
                cancellation_status=getattr(result, "estatus_cancelacion", ""),
            )
        except ImportError:
            # Si satcfdi.verify no está disponible, devolver estado desconocido
            return StatusResult(
                error_message="Consulta de estado no disponible en esta versión de satcfdi",
            )
        except Exception as e:
            return StatusResult(error_message=str(e))


def _extract_tfd_data(xml_bytes: bytes) -> dict:
    """
    Extrae atributos del nodo TimbreFiscalDigital del XML timbrado.

    Returns:
        dict con FechaTimbrado, SelloSAT, NoCertificadoSAT.
    """
    try:
        from lxml import etree

        root = etree.fromstring(xml_bytes)
        ns = "http://www.sat.gob.mx/TimbreFiscalDigital"
        tfd = root.find(f".//{{{ns}}}TimbreFiscalDigital")
        if tfd is None:
            return {}
        return {
            "FechaTimbrado": tfd.get("FechaTimbrado", ""),
            "SelloSAT": tfd.get("SelloSAT", ""),
            "NoCertificadoSAT": tfd.get("NoCertificadoSAT", ""),
        }
    except Exception:
        return {}


# ── Registro automático en el dispatcher ──
from ..pac_dispatcher import PACDispatcher  # noqa: E402

PACDispatcher.register("Finkok", FinkokPAC)
