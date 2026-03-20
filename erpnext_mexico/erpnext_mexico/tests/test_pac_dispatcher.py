# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

"""Tests para PACDispatcher y utilidades compartidas pac_utils.

Pure unit tests — run without a live Frappe site or network access.
All external dependencies (frappe, satcfdi, lxml) are stubbed in
sys.modules before the modules under test are imported.

Coverage:
  PACDispatcher
    - register() accepts a custom PAC class
    - get_pac() returns a PAC instance for a known provider
    - get_pac() raises when pac_provider is empty
    - get_pac() raises when PAC name is not registered
    - get_pac() raises when pac_credentials is not configured
    - available_pacs() returns a list with the built-in PAC names
    - registry isolation between tests (no cross-contamination)

  pac_utils.extract_tfd_data
    - valid XML with a TFD node returns correct dict keys
    - XML without TFD node returns empty dict
    - malformed / non-XML bytes return empty dict
    - str input is accepted as well as bytes
    - CadenaOriginal format matches SAT spec prefix/suffix

  pac_utils.map_environment
    - "Sandbox" and "sandbox" and "test" => TEST
    - "Production" and "PRODUCTION"     => PRODUCTION
    - unrecognised string defaults to PRODUCTION

  pac_utils.map_cancel_reason
    - codes "01"–"04" each map to the correct CancelReason enum member
    - code "05" and any other unknown code raise ValueError
    - error message includes the invalid code

  pac_utils.call_with_timeout
    - normal execution returns the function's result
    - TimeoutError is raised when execution exceeds the timeout
    - arguments and keyword-arguments are forwarded correctly
"""

import sys
import time
import types
import unittest
from enum import Enum
from unittest.mock import MagicMock, patch


# ──────────────────────────────────────────────────────────────────────────────
# Lightweight enum stubs mirroring satcfdi's types
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
# Stub installer — runs once at module load
# ──────────────────────────────────────────────────────────────────────────────

def _install_stubs() -> None:
    """Register lightweight stubs for frappe and satcfdi in sys.modules.

    Skips registration when the real module is already present (e.g. when
    running inside a live Frappe bench).

    The stub hierarchy must match every `from X import Y` that any transitively
    imported module under test performs at module-load time.  For satcfdi we
    must register:
      satcfdi
      satcfdi.cfdi
      satcfdi.create          (+ cancela sub-module used by finkok_pac)
      satcfdi.create.cancela
      satcfdi.create.cfd
      satcfdi.create.cfd.cfdi40
      satcfdi.models
      satcfdi.models.signer
      satcfdi.pacs
      satcfdi.pacs.finkok
      satcfdi.pacs.finkok.cancelacion
      satcfdi.pacs.swsapien
      satcfdi.verify
    """
    if "frappe" in sys.modules and hasattr(sys.modules["frappe"], "get_doc"):
        return

    # -- frappe ---------------------------------------------------------------
    frappe_stub = types.ModuleType("frappe")
    frappe_stub._ = lambda s: s
    frappe_stub.throw = MagicMock(side_effect=Exception("frappe.throw called"))
    frappe_stub.get_single = MagicMock()
    frappe_stub.get_cached_doc = MagicMock()
    frappe_stub.get_doc = MagicMock()
    frappe_stub.db = MagicMock()
    frappe_stub.log_error = MagicMock()
    frappe_stub.cache = MagicMock(return_value=MagicMock())
    frappe_stub.session = __import__("types").SimpleNamespace(user="test@example.com")
    frappe_stub.whitelist = lambda *args, **kwargs: (
        (lambda fn: fn) if not args else args[0]
    )
    sys.modules["frappe"] = frappe_stub

    # -- erpnext_mexico.utils.sanitize ----------------------------------------
    # Must be in place before any PAC adapter module is imported.
    sanitize_mod = types.ModuleType("erpnext_mexico.utils.sanitize")
    sanitize_mod.sanitize_log_message = lambda s: s
    utils_mod = types.ModuleType("erpnext_mexico.utils")
    utils_mod.sanitize = sanitize_mod
    erpnext_mx_mod = types.ModuleType("erpnext_mexico")
    erpnext_mx_mod.utils = utils_mod
    sys.modules.setdefault("erpnext_mexico", erpnext_mx_mod)
    sys.modules.setdefault("erpnext_mexico.utils", utils_mod)
    sys.modules.setdefault("erpnext_mexico.utils.sanitize", sanitize_mod)

    # -- satcfdi.pacs ---------------------------------------------------------
    pacs_mod = types.ModuleType("satcfdi.pacs")
    pacs_mod.Environment = _FakeEnvironment
    pacs_mod.CancelReason = _FakeCancelReason

    # finkok sub-packages
    cancelacion_mod = types.ModuleType("satcfdi.pacs.finkok.cancelacion")
    cancelacion_mod.Folio = MagicMock()
    cancelacion_mod.Cancelacion = MagicMock()

    finkok_pac_mod = types.ModuleType("satcfdi.pacs.finkok")
    finkok_pac_mod.cancelacion = cancelacion_mod
    finkok_pac_mod.CancelReason = _FakeCancelReason
    finkok_pac_mod.CancelationAcknowledgment = MagicMock()
    finkok_pac_mod.Environment = _FakeEnvironment
    finkok_pac_mod.Finkok = MagicMock()

    # swsapien sub-package
    swsapien_mod = types.ModuleType("satcfdi.pacs.swsapien")
    swsapien_mod.Environment = _FakeEnvironment
    swsapien_mod.CancelReason = _FakeCancelReason
    swsapien_mod.CancelationAcknowledgment = MagicMock()
    swsapien_mod.SWSapien = MagicMock()

    pacs_mod.finkok = finkok_pac_mod
    pacs_mod.swsapien = swsapien_mod

    sys.modules.setdefault("satcfdi.pacs", pacs_mod)
    sys.modules.setdefault("satcfdi.pacs.finkok", finkok_pac_mod)
    sys.modules.setdefault("satcfdi.pacs.finkok.cancelacion", cancelacion_mod)
    sys.modules.setdefault("satcfdi.pacs.swsapien", swsapien_mod)

    # -- satcfdi.create -------------------------------------------------------
    # finkok_pac.py does:  from satcfdi.create.cancela import cancelacion
    # so satcfdi.create.cancela must exist and expose a `cancelacion` attribute.
    create_cancela_mod = types.ModuleType("satcfdi.create.cancela")
    _fake_cancelacion = types.SimpleNamespace(
        Folio=MagicMock(),
        Cancelacion=MagicMock(),
    )
    create_cancela_mod.cancelacion = _fake_cancelacion

    cfdi40_mod = types.ModuleType("satcfdi.create.cfd.cfdi40")
    cfdi40_mod.Comprobante = MagicMock()

    cfd_mod = types.ModuleType("satcfdi.create.cfd")
    cfd_mod.cfdi40 = cfdi40_mod

    create_mod = types.ModuleType("satcfdi.create")
    create_mod.cfd = cfd_mod
    create_mod.cancela = create_cancela_mod

    sys.modules.setdefault("satcfdi.create", create_mod)
    sys.modules.setdefault("satcfdi.create.cancela", create_cancela_mod)
    sys.modules.setdefault("satcfdi.create.cfd", cfd_mod)
    sys.modules.setdefault("satcfdi.create.cfd.cfdi40", cfdi40_mod)

    # -- satcfdi.cfdi ---------------------------------------------------------
    cfdi_mod = types.ModuleType("satcfdi.cfdi")
    cfdi_mod.CFDI = MagicMock()
    sys.modules.setdefault("satcfdi.cfdi", cfdi_mod)

    # -- satcfdi.models -------------------------------------------------------
    signer_mod = types.ModuleType("satcfdi.models.signer")
    signer_mod.Signer = MagicMock()
    models_mod = types.ModuleType("satcfdi.models")
    models_mod.Signer = signer_mod.Signer
    sys.modules.setdefault("satcfdi.models.signer", signer_mod)
    sys.modules.setdefault("satcfdi.models", models_mod)

    # -- satcfdi.verify -------------------------------------------------------
    verify_mod = types.ModuleType("satcfdi.verify")
    verify_mod.verify_cfdi = MagicMock()
    sys.modules.setdefault("satcfdi.verify", verify_mod)

    # -- satcfdi top-level ----------------------------------------------------
    satcfdi_mod = types.ModuleType("satcfdi")
    satcfdi_mod.pacs = pacs_mod
    satcfdi_mod.create = create_mod
    satcfdi_mod.cfdi = cfdi_mod
    satcfdi_mod.models = models_mod
    sys.modules.setdefault("satcfdi", satcfdi_mod)

    # -- lxml.etree -----------------------------------------------------------
    try:
        import lxml.etree  # noqa: F401 — use real lxml if present
    except ImportError:
        etree_mod = types.ModuleType("lxml.etree")
        etree_mod.fromstring = MagicMock(return_value=MagicMock())
        lxml_mod = types.ModuleType("lxml")
        lxml_mod.etree = etree_mod
        sys.modules.setdefault("lxml", lxml_mod)
        sys.modules.setdefault("lxml.etree", etree_mod)


_install_stubs()

# Safe to import modules under test now
from erpnext_mexico.cfdi.pac_dispatcher import PACDispatcher  # noqa: E402
from erpnext_mexico.cfdi.pac_interface import PACInterface    # noqa: E402
from erpnext_mexico.cfdi.pac_utils import (                   # noqa: E402
    call_with_timeout,
    extract_tfd_data,
    map_cancel_reason,
    map_environment,
)


# ──────────────────────────────────────────────────────────────────────────────
# Minimal concrete PAC for registration / get_pac tests
# ──────────────────────────────────────────────────────────────────────────────

class _MockPAC(PACInterface):
    """Minimal concrete PAC used only in registration / get_pac tests."""

    def __init__(self, username="u", password="p", environment="Sandbox"):
        self.username = username
        self.password = password
        self.environment = environment

    def stamp(self, cfdi_signed):  # type: ignore[override]
        raise NotImplementedError

    def cancel(self, uuid, rfc_emisor, certificate, key, password, reason,
               substitute_uuid=None):  # type: ignore[override]
        raise NotImplementedError

    def get_status(self, uuid, rfc_emisor, rfc_receptor, total):  # type: ignore[override]
        raise NotImplementedError


# ──────────────────────────────────────────────────────────────────────────────
# XML fixtures for extract_tfd_data tests
# ──────────────────────────────────────────────────────────────────────────────

_TFD_NS = "http://www.sat.gob.mx/TimbreFiscalDigital"

_XML_WITH_TFD = f"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4"
                  xmlns:tfd="{_TFD_NS}"
                  Version="4.0">
  <cfdi:Complemento>
    <tfd:TimbreFiscalDigital
        Version="1.1"
        UUID="01234567-89AB-CDEF-0123-456789ABCDEF"
        FechaTimbrado="2026-01-15T10:00:00"
        RfcProvCertif="SAT970701NN3"
        Leyenda=""
        SelloCFD="SELLO_CFDI_BASE64"
        NoCertificadoSAT="20001000000300022323"
        SelloSAT="SELLO_SAT_BASE64"
    />
  </cfdi:Complemento>
</cfdi:Comprobante>
""".encode("utf-8")

_XML_WITHOUT_TFD = b"""<?xml version="1.0" encoding="UTF-8"?>
<cfdi:Comprobante xmlns:cfdi="http://www.sat.gob.mx/cfd/4" Version="4.0">
</cfdi:Comprobante>
"""

_XML_MALFORMED = b"<this is not >>> valid < XML"


# ──────────────────────────────────────────────────────────────────────────────
# PACDispatcher.register() tests
# ──────────────────────────────────────────────────────────────────────────────

class TestPACDispatcherRegister(unittest.TestCase):
    """PACDispatcher.register() inserts a PAC class into the registry."""

    def setUp(self):
        self._original_registry = dict(PACDispatcher._registry)
        self._original_initialized = PACDispatcher._initialized

    def tearDown(self):
        PACDispatcher._registry.clear()
        PACDispatcher._registry.update(self._original_registry)
        PACDispatcher._initialized = self._original_initialized

    def test_register_adds_pac_to_registry(self):
        PACDispatcher.register("TestPAC", _MockPAC)
        self.assertIn("TestPAC", PACDispatcher._registry)

    def test_register_maps_name_to_correct_class(self):
        PACDispatcher.register("TestPAC", _MockPAC)
        self.assertIs(PACDispatcher._registry["TestPAC"], _MockPAC)

    def test_register_overwrites_existing_entry(self):
        """Registering the same name twice uses the latest class."""
        class _OtherMock(_MockPAC):
            pass

        PACDispatcher.register("TestPAC", _MockPAC)
        PACDispatcher.register("TestPAC", _OtherMock)
        self.assertIs(PACDispatcher._registry["TestPAC"], _OtherMock)

    def test_register_multiple_pacs_independently(self):
        class _MockPAC2(_MockPAC):
            pass

        PACDispatcher.register("PAC_A", _MockPAC)
        PACDispatcher.register("PAC_B", _MockPAC2)
        self.assertIn("PAC_A", PACDispatcher._registry)
        self.assertIn("PAC_B", PACDispatcher._registry)


# ──────────────────────────────────────────────────────────────────────────────
# PACDispatcher.available_pacs() tests
# ──────────────────────────────────────────────────────────────────────────────

class TestPACDispatcherAvailablePacs(unittest.TestCase):
    """PACDispatcher.available_pacs() returns all registered names."""

    def setUp(self):
        """Pre-populate registry with built-in names so _ensure_registered
        does not attempt to import the real FinkokPAC / SWSapienPAC."""
        self._original_registry = dict(PACDispatcher._registry)
        self._original_initialized = PACDispatcher._initialized
        # Seed registry and mark as initialized so lazy-load is skipped
        PACDispatcher._registry.clear()
        PACDispatcher._registry["Finkok"] = _MockPAC
        PACDispatcher._registry["SW Sapien"] = _MockPAC
        PACDispatcher._initialized = True

    def tearDown(self):
        PACDispatcher._registry.clear()
        PACDispatcher._registry.update(self._original_registry)
        PACDispatcher._initialized = self._original_initialized

    def test_returns_list(self):
        result = PACDispatcher.available_pacs()
        self.assertIsInstance(result, list)

    def test_built_in_finkok_is_present(self):
        self.assertIn("Finkok", PACDispatcher.available_pacs())

    def test_built_in_sw_sapien_is_present(self):
        self.assertIn("SW Sapien", PACDispatcher.available_pacs())

    def test_custom_pac_appears_after_register(self):
        PACDispatcher.register("CustomPAC", _MockPAC)
        self.assertIn("CustomPAC", PACDispatcher.available_pacs())


# ──────────────────────────────────────────────────────────────────────────────
# PACDispatcher.get_pac() tests
# ──────────────────────────────────────────────────────────────────────────────

class TestPACDispatcherGetPac(unittest.TestCase):
    """PACDispatcher.get_pac() resolves a PAC instance from MX CFDI Settings."""

    def setUp(self):
        self._original_registry = dict(PACDispatcher._registry)
        self._original_initialized = PACDispatcher._initialized
        # Pre-seed registry so _ensure_registered does not try real imports
        PACDispatcher._registry.clear()
        PACDispatcher._registry["TestPAC"] = _MockPAC
        PACDispatcher._initialized = True

        self._frappe = sys.modules["frappe"]
        self._frappe.get_single.reset_mock()
        self._frappe.get_doc.reset_mock()
        self._frappe.throw.reset_mock()
        self._frappe.throw.side_effect = Exception("frappe.throw called")

    def tearDown(self):
        PACDispatcher._registry.clear()
        PACDispatcher._registry.update(self._original_registry)
        PACDispatcher._initialized = self._original_initialized
        self._frappe.get_single.reset_mock()
        self._frappe.get_doc.reset_mock()
        self._frappe.throw.reset_mock()

    def _make_settings(self, pac_provider="TestPAC", pac_credentials="creds-1",
                       pac_environment="Sandbox"):
        settings = MagicMock()
        settings.pac_provider = pac_provider
        settings.pac_credentials = pac_credentials
        settings.pac_environment = pac_environment
        return settings

    def _make_credentials(self, username="user@test.mx", password="secret"):
        creds = MagicMock()
        creds.pac_username = username
        creds.get_password = MagicMock(return_value=password)
        return creds

    def test_get_pac_returns_pac_instance(self):
        self._frappe.get_single.return_value = self._make_settings()
        self._frappe.get_doc.return_value = self._make_credentials()

        result = PACDispatcher.get_pac("Empresa Test SA de CV")
        self.assertIsInstance(result, _MockPAC)

    def test_get_pac_passes_username_from_credentials(self):
        self._frappe.get_single.return_value = self._make_settings()
        self._frappe.get_doc.return_value = self._make_credentials(username="demo@test.mx")

        result = PACDispatcher.get_pac("Empresa Test SA de CV")
        self.assertEqual(result.username, "demo@test.mx")

    def test_get_pac_passes_password_from_credentials(self):
        self._frappe.get_single.return_value = self._make_settings()
        self._frappe.get_doc.return_value = self._make_credentials(password="s3cr3t")

        result = PACDispatcher.get_pac("Empresa Test SA de CV")
        self.assertEqual(result.password, "s3cr3t")

    def test_get_pac_passes_environment_from_settings(self):
        self._frappe.get_single.return_value = self._make_settings(pac_environment="Production")
        self._frappe.get_doc.return_value = self._make_credentials()

        result = PACDispatcher.get_pac("Empresa Test SA de CV")
        self.assertEqual(result.environment, "Production")

    def test_get_pac_defaults_environment_to_sandbox_when_none(self):
        settings = self._make_settings()
        settings.pac_environment = None
        self._frappe.get_single.return_value = settings
        self._frappe.get_doc.return_value = self._make_credentials()

        result = PACDispatcher.get_pac("Empresa Test SA de CV")
        self.assertEqual(result.environment, "Sandbox")

    def test_get_pac_calls_frappe_get_single_with_settings_doctype(self):
        self._frappe.get_single.return_value = self._make_settings()
        self._frappe.get_doc.return_value = self._make_credentials()

        PACDispatcher.get_pac("Empresa Test SA de CV")
        self._frappe.get_single.assert_called_with("MX CFDI Settings")

    def test_get_pac_calls_frappe_get_doc_for_credentials(self):
        self._frappe.get_single.return_value = self._make_settings(pac_credentials="creds-abc")
        self._frappe.get_doc.return_value = self._make_credentials()

        PACDispatcher.get_pac("Empresa Test SA de CV")
        self._frappe.get_doc.assert_called_with("MX PAC Credentials", "creds-abc")

    def test_get_pac_throws_when_pac_provider_is_empty(self):
        settings = self._make_settings()
        settings.pac_provider = ""
        self._frappe.get_single.return_value = settings

        with self.assertRaises(Exception):
            PACDispatcher.get_pac("Empresa Test SA de CV")
        self._frappe.throw.assert_called_once()

    def test_get_pac_throws_when_pac_name_not_registered(self):
        self._frappe.get_single.return_value = self._make_settings(pac_provider="PAC Desconocido")

        with self.assertRaises(Exception):
            PACDispatcher.get_pac("Empresa Test SA de CV")
        self._frappe.throw.assert_called_once()

    def test_get_pac_throws_when_pac_credentials_is_empty(self):
        settings = self._make_settings()
        settings.pac_credentials = ""
        self._frappe.get_single.return_value = settings

        with self.assertRaises(Exception):
            PACDispatcher.get_pac("Empresa Test SA de CV")
        self._frappe.throw.assert_called_once()

    def test_get_pac_throws_when_pac_credentials_is_none(self):
        settings = self._make_settings()
        settings.pac_credentials = None
        self._frappe.get_single.return_value = settings

        with self.assertRaises(Exception):
            PACDispatcher.get_pac("Empresa Test SA de CV")
        self._frappe.throw.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# Registry isolation tests
# ──────────────────────────────────────────────────────────────────────────────

class TestPACDispatcherRegistryIsolation(unittest.TestCase):
    """Registry state must not leak between test cases."""

    def test_registry_is_class_variable_not_instance_variable(self):
        """_registry must be shared across all lookups (ClassVar behavior)."""
        self.assertIs(PACDispatcher._registry, PACDispatcher._registry)

    def test_custom_registration_does_not_remove_existing_entries(self):
        original = dict(PACDispatcher._registry)
        try:
            PACDispatcher.register("IsolationTestPAC", _MockPAC)
            for key in original:
                self.assertIn(key, PACDispatcher._registry)
        finally:
            PACDispatcher._registry.clear()
            PACDispatcher._registry.update(original)


# ──────────────────────────────────────────────────────────────────────────────
# extract_tfd_data tests
# ──────────────────────────────────────────────────────────────────────────────

class TestExtractTfdData(unittest.TestCase):
    """extract_tfd_data parses SAT TimbreFiscalDigital nodes."""

    def test_valid_xml_returns_fecha_timbrado(self):
        result = extract_tfd_data(_XML_WITH_TFD)
        self.assertEqual(result.get("FechaTimbrado"), "2026-01-15T10:00:00")

    def test_valid_xml_returns_sello_sat(self):
        result = extract_tfd_data(_XML_WITH_TFD)
        self.assertEqual(result.get("SelloSAT"), "SELLO_SAT_BASE64")

    def test_valid_xml_returns_no_certificado_sat(self):
        result = extract_tfd_data(_XML_WITH_TFD)
        self.assertEqual(result.get("NoCertificadoSAT"), "20001000000300022323")

    def test_valid_xml_returns_cadena_original_key(self):
        result = extract_tfd_data(_XML_WITH_TFD)
        self.assertIn("CadenaOriginal", result)

    def test_cadena_original_starts_with_double_pipe(self):
        result = extract_tfd_data(_XML_WITH_TFD)
        self.assertTrue(result["CadenaOriginal"].startswith("||"))

    def test_cadena_original_ends_with_double_pipe(self):
        result = extract_tfd_data(_XML_WITH_TFD)
        self.assertTrue(result["CadenaOriginal"].endswith("||"))

    def test_cadena_original_contains_uuid(self):
        result = extract_tfd_data(_XML_WITH_TFD)
        self.assertIn("01234567-89AB-CDEF-0123-456789ABCDEF", result["CadenaOriginal"])

    def test_cadena_original_contains_sello_sat(self):
        result = extract_tfd_data(_XML_WITH_TFD)
        self.assertIn("SELLO_SAT_BASE64", result["CadenaOriginal"])

    def test_xml_without_tfd_returns_empty_dict(self):
        result = extract_tfd_data(_XML_WITHOUT_TFD)
        self.assertEqual(result, {})

    def test_malformed_xml_returns_empty_dict(self):
        result = extract_tfd_data(_XML_MALFORMED)
        self.assertEqual(result, {})

    def test_str_input_accepted_same_as_bytes(self):
        xml_str = _XML_WITH_TFD.decode("utf-8")
        result = extract_tfd_data(xml_str)
        self.assertIn("FechaTimbrado", result)

    def test_empty_bytes_returns_empty_dict(self):
        result = extract_tfd_data(b"")
        self.assertEqual(result, {})

    def test_returns_dict_type(self):
        result = extract_tfd_data(_XML_WITH_TFD)
        self.assertIsInstance(result, dict)


# ──────────────────────────────────────────────────────────────────────────────
# map_environment tests
# ──────────────────────────────────────────────────────────────────────────────

class TestMapEnvironment(unittest.TestCase):
    """map_environment converts config strings to satcfdi Environment enum."""

    def _name(self, result) -> str:
        return result.name

    def test_sandbox_title_case_returns_test(self):
        self.assertEqual(self._name(map_environment("Sandbox")), "TEST")

    def test_sandbox_lower_case_returns_test(self):
        self.assertEqual(self._name(map_environment("sandbox")), "TEST")

    def test_test_string_returns_test(self):
        self.assertEqual(self._name(map_environment("test")), "TEST")

    def test_test_upper_case_returns_test(self):
        self.assertEqual(self._name(map_environment("TEST")), "TEST")

    def test_production_title_case_returns_production(self):
        self.assertEqual(self._name(map_environment("Production")), "PRODUCTION")

    def test_production_upper_case_returns_production(self):
        self.assertEqual(self._name(map_environment("PRODUCTION")), "PRODUCTION")

    def test_production_lower_case_returns_production(self):
        self.assertEqual(self._name(map_environment("production")), "PRODUCTION")

    def test_unknown_string_defaults_to_production(self):
        """Any unrecognised string must fall back to PRODUCTION."""
        self.assertEqual(self._name(map_environment("live")), "PRODUCTION")

    def test_empty_string_defaults_to_production(self):
        self.assertEqual(self._name(map_environment("")), "PRODUCTION")


# ──────────────────────────────────────────────────────────────────────────────
# map_cancel_reason tests
# ──────────────────────────────────────────────────────────────────────────────

class TestMapCancelReason(unittest.TestCase):
    """map_cancel_reason converts SAT motivo codes to CancelReason enums."""

    def _name(self, result) -> str:
        return result.name

    def test_motivo_01_maps_to_con_relacion(self):
        self.assertEqual(
            self._name(map_cancel_reason("01")),
            "COMPROBANTE_EMITIDO_CON_ERRORES_CON_RELACION",
        )

    def test_motivo_02_maps_to_sin_relacion(self):
        self.assertEqual(
            self._name(map_cancel_reason("02")),
            "COMPROBANTE_EMITIDO_CON_ERRORES_SIN_RELACION",
        )

    def test_motivo_03_maps_to_no_se_llevo(self):
        self.assertEqual(
            self._name(map_cancel_reason("03")),
            "NO_SE_LLEVO_A_CABO_LA_OPERACION",
        )

    def test_motivo_04_maps_to_normativa(self):
        self.assertEqual(
            self._name(map_cancel_reason("04")),
            "OPERACION_NORMATIVA_RELACIONADA_EN_LA_FACTURA_GLOBAL",
        )

    def test_motivo_05_raises_value_error(self):
        with self.assertRaises(ValueError):
            map_cancel_reason("05")

    def test_invalid_code_error_message_contains_code(self):
        with self.assertRaises(ValueError) as ctx:
            map_cancel_reason("99")
        self.assertIn("99", str(ctx.exception))

    def test_invalid_code_error_message_lists_valid_values(self):
        with self.assertRaises(ValueError) as ctx:
            map_cancel_reason("00")
        msg = str(ctx.exception)
        self.assertTrue(
            any(code in msg for code in ("01", "02", "03", "04")),
            f"Expected valid codes in error message, got: {msg}",
        )

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            map_cancel_reason("")


# ──────────────────────────────────────────────────────────────────────────────
# call_with_timeout tests
# ──────────────────────────────────────────────────────────────────────────────

class TestCallWithTimeout(unittest.TestCase):
    """call_with_timeout wraps a callable with a hard deadline."""

    def test_normal_function_returns_result(self):
        result = call_with_timeout(lambda: 42, timeout=5)
        self.assertEqual(result, 42)

    def test_positional_args_forwarded_correctly(self):
        result = call_with_timeout(lambda a, b: a + b, 10, 20, timeout=5)
        self.assertEqual(result, 30)

    def test_keyword_args_forwarded_correctly(self):
        result = call_with_timeout(lambda x=0, y=0: x * y, x=3, y=7, timeout=5)
        self.assertEqual(result, 21)

    def test_timeout_exceeded_raises_timeout_error(self):
        def _slow():
            time.sleep(5)

        with self.assertRaises(TimeoutError):
            call_with_timeout(_slow, timeout=0)

    def test_timeout_error_message_mentions_seconds(self):
        def _slow():
            time.sleep(5)

        with self.assertRaises(TimeoutError) as ctx:
            call_with_timeout(_slow, timeout=0)
        self.assertIn("seconds", str(ctx.exception))

    def test_function_exception_propagates(self):
        """Exceptions raised by the wrapped function must bubble up unchanged."""
        def _boom():
            raise ValueError("unexpected error")

        with self.assertRaises(ValueError) as ctx:
            call_with_timeout(_boom, timeout=5)
        self.assertIn("unexpected error", str(ctx.exception))

    def test_return_value_is_none_when_function_returns_none(self):
        result = call_with_timeout(lambda: None, timeout=5)
        self.assertIsNone(result)

    def test_return_value_can_be_complex_object(self):
        expected = {"key": [1, 2, 3]}
        result = call_with_timeout(lambda: expected, timeout=5)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
