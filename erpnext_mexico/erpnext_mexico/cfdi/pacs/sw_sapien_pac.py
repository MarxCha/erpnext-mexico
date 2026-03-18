"""
Adaptador PAC para SW Sapien usando la biblioteca satcfdi.
PAC secundario soportado.

Sandbox: api.test.sw.com.mx
Docs: developers.sw.com.mx

API satcfdi:
  - SWSapien(token=None, user=None, password=None, environment=Environment.PRODUCTION|TEST)
  - .stamp(cfdi: CFDI, accept=Accept.XML) -> Document(document_id, xml)
  - .cancel_comprobante(cancelation: Cancelacion) -> CancelationAcknowledgment(code, acuse)
"""

from typing import Optional

from satcfdi.cfdi import CFDI
from satcfdi.create.cancela import cancelacion
from satcfdi.models.signer import Signer
from satcfdi.pacs.swsapien import CancelationAcknowledgment, SWSapien

from ..pac_interface import CancelResult, PACInterface, StampResult, StatusResult
from ..pac_utils import extract_tfd_data as _extract_tfd_data
from ..pac_utils import map_cancel_reason as _map_cancel_reason
from ..pac_utils import map_environment as _map_environment


class SWSapienPAC(PACInterface):
    """Implementación de PACInterface para SW Sapien vía satcfdi.

    Supports both token-based and user/password authentication.
    If token is provided, it takes precedence over user/password.
    """

    def __init__(
        self,
        user: str,
        password: str,
        environment: str = "Sandbox",
        token: Optional[str] = None,
    ):
        env = _map_environment(environment)
        if token:
            self._client = SWSapien(
                token=token,
                environment=env,
            )
        else:
            self._client = SWSapien(
                user=user,
                password=password,
                environment=env,
            )

    def stamp(self, xml_signed: str) -> StampResult:
        """
        Timbrar CFDI firmado vía SW Sapien.

        Args:
            xml_signed: XML del CFDI firmado con CSD como string.

        Returns:
            StampResult con UUID, XML timbrado y metadatos.
        """
        try:
            # satcfdi SWSapien.stamp() espera un objeto CFDI, no un string
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
            import frappe
            frappe.log_error(
                title="CFDI Stamp Error (SW Sapien)",
                message=f"{type(e).__name__}: {str(e)}"
            )
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
        Cancelar CFDI vía SW Sapien.

        Construye un Signer desde el CSD y arma la solicitud de cancelación
        firmada usando satcfdi.create.cancela.cancelacion.

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
            import frappe
            frappe.log_error(
                title="CFDI Cancel Error (SW Sapien)",
                message=f"{type(e).__name__}: {str(e)}"
            )
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

        SW Sapien no expone get_status directamente en satcfdi.
        Se delega al servicio SAT de consulta pública (igual que Finkok).
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


# ── Registro automático en el dispatcher ──
from ..pac_dispatcher import PACDispatcher  # noqa: E402

PACDispatcher.register("SW Sapien", SWSapienPAC)
