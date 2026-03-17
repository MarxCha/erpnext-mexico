"""
Adaptador PAC para Finkok/Quadrum usando la biblioteca satcfdi.
PAC primario recomendado por costo-beneficio.

Sandbox: demo-facturacion.finkok.com
Docs: wiki.finkok.com
"""

from typing import Optional

from satcfdi.pacs import finkok

from ..pac_interface import PACInterface, StampResult, CancelResult, StatusResult


class FinkokPAC(PACInterface):
    """Implementación de PACInterface para Finkok vía satcfdi."""

    def __init__(self, username: str, password: str, environment: str = "Test"):
        self.env = finkok.Environment(
            username=username,
            password=password,
            environment="test" if environment == "Test" else "production",
        )

    def stamp(self, xml_signed: str) -> StampResult:
        """Timbrar CFDI firmado vía Finkok."""
        try:
            result = self.env.stamp(xml_signed)
            return StampResult(
                uuid=str(result.uuid),
                xml_stamped=result.xml,
                fecha_timbrado=str(result.fecha_timbrado),
                sello_sat=getattr(result, "sello_sat", ""),
                no_certificado_sat=getattr(result, "no_certificado_sat", ""),
                cadena_original_tfd=getattr(result, "cadena_original", ""),
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
        """Cancelar CFDI vía Finkok."""
        try:
            result = self.env.cancel(
                uuid=uuid,
                rfc=rfc_emisor,
                certificate=certificate,
                key=key,
                password=password,
                reason=reason,
                substitute_uuid=substitute_uuid,
            )
            return CancelResult(
                success=True,
                acuse_xml=getattr(result, "acuse", ""),
                status=getattr(result, "status", "Cancelado"),
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
        """Consultar estado de CFDI vía Finkok."""
        try:
            result = self.env.get_status(
                uuid=uuid,
                rfc_emisor=rfc_emisor,
                rfc_receptor=rfc_receptor,
                total=total,
            )
            return StatusResult(
                is_cancellable=getattr(result, "is_cancellable", False),
                status=getattr(result, "status", ""),
                cancellation_status=getattr(result, "cancellation_status", ""),
            )
        except Exception as e:
            return StatusResult(error_message=str(e))


# ── Registro automático en el dispatcher ──
from ..pac_dispatcher import PACDispatcher

PACDispatcher.register("Finkok", FinkokPAC)
