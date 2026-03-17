"""
Dispatcher multi-PAC con Strategy Pattern.
Selecciona el PAC correcto según la configuración de la empresa.
"""

from typing import ClassVar

import frappe

from .pac_interface import PACInterface


class PACDispatcher:
    """Registry de PACs. Cada PAC se registra con su nombre y clase."""

    _registry: ClassVar[dict[str, type[PACInterface]]] = {}

    @classmethod
    def register(cls, name: str, pac_class: type[PACInterface]) -> None:
        """Registrar un adaptador de PAC."""
        cls._registry[name] = pac_class

    @classmethod
    def get_pac(cls, company: str) -> PACInterface:
        """
        Obtener instancia del PAC configurado para una empresa.
        
        Args:
            company: Nombre de la empresa en ERPNext.
            
        Returns:
            Instancia del PAC configurado.
            
        Raises:
            frappe.ValidationError si el PAC no está configurado o registrado.
        """
        settings = frappe.get_cached_doc("MX CFDI Settings", {"company": company})

        if not settings.pac_provider:
            frappe.throw(
                frappe._("No se ha configurado un PAC en MX CFDI Settings para {0}").format(company),
                title=frappe._("PAC no configurado"),
            )

        pac_name = settings.pac_provider

        if pac_name not in cls._registry:
            frappe.throw(
                frappe._("PAC '{0}' no está registrado. PACs disponibles: {1}").format(
                    pac_name, ", ".join(cls._registry.keys())
                ),
                title=frappe._("PAC no disponible"),
            )

        # Obtener credenciales
        if not settings.pac_credentials:
            frappe.throw(
                frappe._("No se han configurado credenciales para el PAC {0}").format(pac_name),
                title=frappe._("Credenciales faltantes"),
            )

        credentials = frappe.get_doc("MX PAC Credentials", settings.pac_credentials)

        return cls._registry[pac_name](
            username=credentials.username,
            password=credentials.get_password("password"),
            environment=settings.pac_environment or "Test",
        )

    @classmethod
    def available_pacs(cls) -> list[str]:
        """Lista de PACs registrados."""
        return list(cls._registry.keys())
