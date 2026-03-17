"""
Interfaz abstracta para Proveedores Autorizados de Certificación (PAC).
Implementa Strategy Pattern para permitir selección de PAC por empresa.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StampResult:
    """Resultado del timbrado de un CFDI."""
    uuid: str
    xml_stamped: str
    fecha_timbrado: str
    sello_sat: str
    no_certificado_sat: str
    cadena_original_tfd: str
    success: bool = True
    error_message: str = ""


@dataclass
class CancelResult:
    """Resultado de la cancelación de un CFDI."""
    success: bool
    acuse_xml: str = ""
    status: str = ""  # "Cancelado", "EnProceso", "Rechazado", "NoExiste"
    error_message: str = ""


@dataclass
class StatusResult:
    """Estado de un CFDI ante el SAT."""
    is_cancellable: bool = False
    status: str = ""  # "Vigente", "Cancelado", "NoEncontrado"
    cancellation_status: str = ""  # "EnProceso", "CancelacionSinAceptacion", etc.
    error_message: str = ""


class PACInterface(ABC):
    """Interfaz base que todo adaptador de PAC debe implementar."""

    @abstractmethod
    def stamp(self, xml_signed: str) -> StampResult:
        """
        Enviar XML firmado al PAC para timbrado fiscal.
        
        Args:
            xml_signed: XML del CFDI firmado con CSD (con atributo Sello).
            
        Returns:
            StampResult con UUID, XML timbrado y metadatos del timbre.
        """
        ...

    @abstractmethod
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
        Solicitar cancelación de un CFDI ante el SAT vía PAC.
        
        Args:
            uuid: Folio fiscal del CFDI a cancelar.
            rfc_emisor: RFC del emisor.
            certificate: Contenido binario del .cer del CSD.
            key: Contenido binario del .key del CSD.
            password: Contraseña del .key.
            reason: Motivo de cancelación (01, 02, 03, 04).
            substitute_uuid: UUID del CFDI sustituto (solo para motivo 01).
            
        Returns:
            CancelResult con estado de la cancelación.
        """
        ...

    @abstractmethod
    def get_status(
        self,
        uuid: str,
        rfc_emisor: str,
        rfc_receptor: str,
        total: str,
    ) -> StatusResult:
        """
        Consultar estado de un CFDI ante el SAT.
        
        Args:
            uuid: Folio fiscal.
            rfc_emisor: RFC del emisor.
            rfc_receptor: RFC del receptor.
            total: Monto total del CFDI.
            
        Returns:
            StatusResult con estado actual y si es cancelable.
        """
        ...
