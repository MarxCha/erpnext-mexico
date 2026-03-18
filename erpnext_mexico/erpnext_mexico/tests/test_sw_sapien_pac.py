# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

"""Tests para el adaptador SW Sapien PAC.

These are pure unit tests that run without a live Frappe site or network access.
`frappe` and `satcfdi` are stubbed in sys.modules before the module under test
is imported.

Scope:
  - _map_environment helper (sandbox/test → TEST, production → PRODUCTION)
  - SWSapienPAC class existence and registry in PACDispatcher
  - stamp() returns StampResult with success=False on exception (error path)
  - _map_cancel_reason helper for all four SAT motivos
"""

import sys
import types
import unittest
from enum import Enum
from unittest.mock import MagicMock, patch


# ──────────────────────────────────────────────────────────────────────────────
# Lightweight enums mirroring satcfdi's Environment and CancelReason
# ──────────────────────────────────────────────────────────────────────────────

class _FakeEnvironment(Enum):
    TEST = "TEST"
    PRODUCTION = "PRODUCTION"


class _FakeCancelReason(Enum):
    COMPROBANTE_EMITIDO_CON_ERRORES_CON_RELACION = "01"
    COMPROBANTE_EMITIDO_CON_ERRORES_SIN_RELACION = "02"
    NO_SE_LLEVO_A_CABO_LA_OPERACION = "03"
    OPERACION_NORMATIVA_RELACIONADA_EN_LA_FACTURA_GLOBAL = "04"


# ──────────────────────────────────────────────────────────────────────────────
# Inject stubs into sys.modules BEFORE importing the module under test
# ──────────────────────────────────────────────────────────────────────────────

def _install_stubs():
    """Register lightweight stubs for frappe and satcfdi.pacs.swsapien."""

    # -- frappe stub ----------------------------------------------------------
    frappe_stub = types.ModuleType("frappe")
    frappe_stub._ = lambda s: s
    frappe_stub.throw = MagicMock(side_effect=Exception)
    frappe_stub.get_single = MagicMock()
    frappe_stub.get_cached_doc = MagicMock()
    frappe_stub.get_doc = MagicMock()
    frappe_stub.db = MagicMock()
    frappe_stub.log_error = MagicMock()
    # Handle both @frappe.whitelist and @frappe.whitelist() patterns
    frappe_stub.whitelist = lambda *args, **kwargs: (lambda fn: fn) if not args else args[0]
    sys.modules.setdefault("frappe", frappe_stub)

    # -- satcfdi stubs --------------------------------------------------------
    # satcfdi.cfdi
    cfdi_mod = types.ModuleType("satcfdi.cfdi")
    cfdi_mod.CFDI = MagicMock()
    sys.modules.setdefault("satcfdi.cfdi", cfdi_mod)

    # satcfdi.models.signer
    signer_mod = types.ModuleType("satcfdi.models.signer")
    signer_mod.Signer = MagicMock()
    sys.modules.setdefault("satcfdi.models.signer", signer_mod)

    # satcfdi.models
    models_mod = types.ModuleType("satcfdi.models")
    models_mod.Signer = signer_mod.Signer
    sys.modules.setdefault("satcfdi.models", models_mod)

    # satcfdi.pacs.swsapien — provides Environment, CancelReason, SWSapien
    swsapien_mod = types.ModuleType("satcfdi.pacs.swsapien")
    swsapien_mod.Environment = _FakeEnvironment
    swsapien_mod.CancelReason = _FakeCancelReason
    swsapien_mod.CancelationAcknowledgment = MagicMock()
    swsapien_mod.SWSapien = MagicMock()
    sys.modules.setdefault("satcfdi.pacs.swsapien", swsapien_mod)

    # satcfdi.pacs.finkok — imported for cancelacion helpers
    cancelacion_mod = types.ModuleType("satcfdi.pacs.finkok.cancelacion")
    cancelacion_mod.Folio = MagicMock()
    cancelacion_mod.Cancelacion = MagicMock()

    finkok_mod = types.ModuleType("satcfdi.pacs.finkok")
    finkok_mod.cancelacion = cancelacion_mod
    finkok_mod.CancelReason = _FakeCancelReason
    finkok_mod.CancelationAcknowledgment = MagicMock()
    finkok_mod.Environment = _FakeEnvironment
    finkok_mod.Finkok = MagicMock()
    sys.modules.setdefault("satcfdi.pacs.finkok", finkok_mod)
    sys.modules.setdefault("satcfdi.pacs.finkok.cancelacion", cancelacion_mod)

    # satcfdi.pacs
    pacs_mod = types.ModuleType("satcfdi.pacs")
    pacs_mod.swsapien = swsapien_mod
    pacs_mod.finkok = finkok_mod
    sys.modules.setdefault("satcfdi.pacs", pacs_mod)

    # satcfdi.create.cfd.cfdi40
    cfdi40_mod = types.ModuleType("satcfdi.create.cfd.cfdi40")
    cfdi40_mod.Comprobante = MagicMock()
    cfdi40_mod.Emisor = MagicMock()
    cfdi40_mod.Receptor = MagicMock()
    cfdi40_mod.Concepto = MagicMock()
    sys.modules.setdefault("satcfdi.create.cfd.cfdi40", cfdi40_mod)

    cfd_mod = types.ModuleType("satcfdi.create.cfd")
    cfd_mod.cfdi40 = cfdi40_mod
    sys.modules.setdefault("satcfdi.create.cfd", cfd_mod)

    create_mod = types.ModuleType("satcfdi.create")
    create_mod.cfd = cfd_mod
    sys.modules.setdefault("satcfdi.create", create_mod)

    satcfdi_mod = types.ModuleType("satcfdi")
    satcfdi_mod.create = create_mod
    satcfdi_mod.models = models_mod
    satcfdi_mod.cfdi = cfdi_mod
    satcfdi_mod.pacs = pacs_mod
    sys.modules.setdefault("satcfdi", satcfdi_mod)

    # satcfdi.verify — optional, used inside get_status
    verify_mod = types.ModuleType("satcfdi.verify")
    verify_mod.verify_cfdi = MagicMock()
    sys.modules.setdefault("satcfdi.verify", verify_mod)

    # lxml stub (used by _extract_tfd_data)
    etree_mod = types.ModuleType("lxml.etree")
    etree_mod.fromstring = MagicMock(return_value=MagicMock())
    lxml_mod = types.ModuleType("lxml")
    lxml_mod.etree = etree_mod
    sys.modules.setdefault("lxml", lxml_mod)
    sys.modules.setdefault("lxml.etree", etree_mod)


_install_stubs()

# Now safe to import the modules under test
from erpnext_mexico.cfdi.pacs.sw_sapien_pac import (  # noqa: E402
    _map_environment,
    _map_cancel_reason,
    SWSapienPAC,
)
from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────────
# _map_environment tests
# ──────────────────────────────────────────────────────────────────────────────

class TestMapEnvironment(unittest.TestCase):
    """Tests for _map_environment helper."""

    def test_sandbox_string_returns_test(self):
        """'Sandbox' must map to Environment.TEST."""
        result = _map_environment("Sandbox")
        self.assertEqual(result, _FakeEnvironment.TEST)

    def test_sandbox_lowercase_returns_test(self):
        """Case-insensitive: 'sandbox' must also return TEST."""
        result = _map_environment("sandbox")
        self.assertEqual(result, _FakeEnvironment.TEST)

    def test_test_string_returns_test(self):
        """Alternate alias 'test' must also return Environment.TEST."""
        result = _map_environment("test")
        self.assertEqual(result, _FakeEnvironment.TEST)

    def test_production_string_returns_production(self):
        """'Production' must map to Environment.PRODUCTION."""
        result = _map_environment("Production")
        self.assertEqual(result, _FakeEnvironment.PRODUCTION)

    def test_production_uppercase_returns_production(self):
        """Case-insensitive: 'PRODUCTION' must return PRODUCTION."""
        result = _map_environment("PRODUCTION")
        self.assertEqual(result, _FakeEnvironment.PRODUCTION)

    def test_unknown_string_defaults_to_production(self):
        """Any unrecognized string must default to PRODUCTION (safe default)."""
        result = _map_environment("live")
        self.assertEqual(result, _FakeEnvironment.PRODUCTION)


# ──────────────────────────────────────────────────────────────────────────────
# _map_cancel_reason tests
# ──────────────────────────────────────────────────────────────────────────────

class TestMapCancelReason(unittest.TestCase):
    """Tests for _map_cancel_reason helper."""

    def test_motivo_01_maps_correctly(self):
        """Motivo '01' → COMPROBANTE_EMITIDO_CON_ERRORES_CON_RELACION."""
        result = _map_cancel_reason("01")
        self.assertEqual(result, _FakeCancelReason.COMPROBANTE_EMITIDO_CON_ERRORES_CON_RELACION)

    def test_motivo_02_maps_correctly(self):
        """Motivo '02' → COMPROBANTE_EMITIDO_CON_ERRORES_SIN_RELACION."""
        result = _map_cancel_reason("02")
        self.assertEqual(result, _FakeCancelReason.COMPROBANTE_EMITIDO_CON_ERRORES_SIN_RELACION)

    def test_motivo_03_maps_correctly(self):
        """Motivo '03' → NO_SE_LLEVO_A_CABO_LA_OPERACION."""
        result = _map_cancel_reason("03")
        self.assertEqual(result, _FakeCancelReason.NO_SE_LLEVO_A_CABO_LA_OPERACION)

    def test_motivo_04_maps_correctly(self):
        """Motivo '04' → OPERACION_NORMATIVA_RELACIONADA_EN_LA_FACTURA_GLOBAL."""
        result = _map_cancel_reason("04")
        self.assertEqual(result, _FakeCancelReason.OPERACION_NORMATIVA_RELACIONADA_EN_LA_FACTURA_GLOBAL)

    def test_invalid_motivo_raises_value_error(self):
        """Invalid motivo code must raise ValueError with hint."""
        with self.assertRaises(ValueError) as ctx:
            _map_cancel_reason("99")
        self.assertIn("99", str(ctx.exception))


# ──────────────────────────────────────────────────────────────────────────────
# SWSapienPAC registration
# ──────────────────────────────────────────────────────────────────────────────

class TestSWSapienPACRegistration(unittest.TestCase):
    """Tests verifying SWSapienPAC is registered in PACDispatcher."""

    def test_sw_sapien_in_available_pacs(self):
        """SWSapienPAC must register itself under the key 'SW Sapien'."""
        self.assertIn("SW Sapien", PACDispatcher.available_pacs())

    def test_sw_sapien_class_is_pac_interface_subclass(self):
        """SWSapienPAC must be a concrete subclass of PACInterface."""
        from erpnext_mexico.cfdi.pac_interface import PACInterface
        self.assertTrue(issubclass(SWSapienPAC, PACInterface))


# ──────────────────────────────────────────────────────────────────────────────
# stamp() error path
# ──────────────────────────────────────────────────────────────────────────────

class TestSWSapienPACStampErrorPath(unittest.TestCase):
    """Tests for the stamp() error handling path."""

    def _make_pac(self):
        """Construct a SWSapienPAC instance with a mock SWSapien client."""
        pac = SWSapienPAC.__new__(SWSapienPAC)
        pac._client = MagicMock()
        return pac

    def _ensure_frappe_log_error(self):
        """Ensure sys.modules["frappe"] has log_error as a MagicMock."""
        frappe_mod = sys.modules.get("frappe")
        if frappe_mod is not None and not callable(getattr(frappe_mod, "log_error", None)):
            frappe_mod.log_error = MagicMock()

    def test_stamp_exception_returns_stamp_result_with_success_false(self):
        """When the PAC client raises, stamp() must return StampResult(success=False)."""
        self._ensure_frappe_log_error()
        pac = self._make_pac()

        # Patch CFDI.from_string in the satcfdi.cfdi stub module
        from satcfdi import cfdi as cfdi_module
        with patch.object(cfdi_module.CFDI, "from_string", side_effect=RuntimeError("parse error")):
            result = pac.stamp("<cfdi/>")

        self.assertFalse(result.success)
        self.assertEqual(result.uuid, "")
        self.assertEqual(result.xml_stamped, "")
        self.assertIn("parse error", result.error_message)

    def test_stamp_exception_error_message_is_populated(self):
        """StampResult.error_message must contain the exception text on failure."""
        self._ensure_frappe_log_error()
        pac = self._make_pac()

        from satcfdi import cfdi as cfdi_module
        with patch.object(cfdi_module.CFDI, "from_string",
                          side_effect=ConnectionError("Timeout connecting to sw.com.mx")):
            result = pac.stamp("<cfdi/>")

        self.assertFalse(result.success)
        self.assertIn("Timeout", result.error_message)

    def test_stamp_exception_stamps_result_fields_are_empty_strings(self):
        """On failure, all string fields in StampResult must be empty strings."""
        self._ensure_frappe_log_error()
        pac = self._make_pac()

        from satcfdi import cfdi as cfdi_module
        with patch.object(cfdi_module.CFDI, "from_string", side_effect=Exception("boom")):
            result = pac.stamp("<cfdi/>")

        self.assertEqual(result.fecha_timbrado, "")
        self.assertEqual(result.sello_sat, "")
        self.assertEqual(result.no_certificado_sat, "")
        self.assertEqual(result.cadena_original_tfd, "")


# ──────────────────────────────────────────────────────────────────────────────
# cancel() error path
# ──────────────────────────────────────────────────────────────────────────────

class TestSWSapienPACCancelErrorPath(unittest.TestCase):
    """Tests for the cancel() error handling path."""

    def _make_pac(self):
        pac = SWSapienPAC.__new__(SWSapienPAC)
        pac._client = MagicMock()
        return pac

    def test_cancel_invalid_motivo_returns_cancel_result_false(self):
        """cancel() with invalid reason code must return CancelResult(success=False)."""
        pac = self._make_pac()

        # Ensure frappe stub has log_error before calling cancel()
        frappe_mod = sys.modules.get("frappe")
        if frappe_mod is not None and not callable(getattr(frappe_mod, "log_error", None)):
            frappe_mod.log_error = MagicMock()

        result = pac.cancel(
            uuid="00000000-0000-0000-0000-000000000000",
            rfc_emisor="EKU9003173C9",
            certificate=b"",
            key=b"",
            password="test",
            reason="99",  # invalid
        )

        self.assertFalse(result.success)
        self.assertIn("99", result.error_message)


if __name__ == "__main__":
    unittest.main()
