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
    _initialized: ClassVar[bool] = False

    @classmethod
    def _ensure_registered(cls) -> None:
        """Lazy-load PAC adapters on first use."""
        if cls._initialized:
            return
        from erpnext_mexico.cfdi.pacs.finkok_pac import FinkokPAC
        from erpnext_mexico.cfdi.pacs.sw_sapien_pac import SWSapienPAC
        cls._registry.setdefault("Finkok", FinkokPAC)
        cls._registry.setdefault("SW Sapien", SWSapienPAC)
        cls._initialized = True

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
        cls._ensure_registered()
        settings = frappe.get_single("MX CFDI Settings")

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

        pac_class = cls._registry[pac_name]

        # SWSapienPAC expects `user` while FinkokPAC and others expect `username`.
        # Inspect the constructor to pass the correct keyword argument.
        import inspect
        init_params = inspect.signature(pac_class.__init__).parameters
        username_kwarg = "user" if "user" in init_params else "username"

        return pac_class(
            **{username_kwarg: credentials.pac_username},
            password=credentials.get_password("pac_password"),
            environment=settings.pac_environment or "Sandbox",
        )

    @classmethod
    def available_pacs(cls) -> list[str]:
        """Lista de PACs registrados."""
        cls._ensure_registered()
        return list(cls._registry.keys())
