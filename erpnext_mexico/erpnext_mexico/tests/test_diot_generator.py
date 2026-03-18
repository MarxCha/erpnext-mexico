# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

"""Tests para el generador DIOT.

These are pure unit tests for the helper functions in diot_generator.py.
They run without a live Frappe site: `frappe` is stubbed in sys.modules
before the module under test is imported so no database or network access
is needed.
"""

import sys
import types
import unittest
from unittest.mock import MagicMock


# ──────────────────────────────────────────────────────────────────────────────
# Inject frappe stub before importing the module under test
# ──────────────────────────────────────────────────────────────────────────────

def _install_frappe_stub():
    # Skip stubs if running inside Frappe bench (real modules available)
    if "frappe" in sys.modules and hasattr(sys.modules["frappe"], "get_doc"):
        return
    if "frappe" in sys.modules:
        return  # already installed by another test module in the same run

    frappe_stub = types.ModuleType("frappe")
    frappe_stub._ = lambda s: s
    frappe_stub.throw = MagicMock(side_effect=Exception)
    frappe_stub.whitelist = lambda *args, **kwargs: (lambda fn: fn) if not args else args[0]
    frappe_stub.get_all = MagicMock(return_value=[])
    frappe_stub.db = MagicMock()
    frappe_stub.msgprint = MagicMock()

    # frappe.utils stub (used by diot_generator at module level)
    utils_stub = types.ModuleType("frappe.utils")
    import datetime
    utils_stub.getdate = lambda s: datetime.date.fromisoformat(str(s))
    utils_stub.get_last_day = lambda d: d.replace(day=28)  # simplified
    frappe_stub.utils = utils_stub

    sys.modules["frappe"] = frappe_stub
    sys.modules["frappe.utils"] = utils_stub


_install_frappe_stub()

from erpnext_mexico.diot.diot_generator import (  # noqa: E402
    _build_diot_line,
    _classify_taxes_from_list,
    _fmt_amount,
    _safe_name,
)

DIOT_FIELD_COUNT = 24


# ──────────────────────────────────────────────────────────────────────────────
# _fmt_amount
# ──────────────────────────────────────────────────────────────────────────────

class TestFmtAmount(unittest.TestCase):
    """Tests for _fmt_amount."""

    def test_positive_float_rounded_up(self):
        self.assertEqual(_fmt_amount(1500.75), "1501")

    def test_positive_float_rounded_down(self):
        self.assertEqual(_fmt_amount(1500.25), "1500")

    def test_zero(self):
        self.assertEqual(_fmt_amount(0), "0")

    def test_none_returns_zero(self):
        self.assertEqual(_fmt_amount(None), "0")

    def test_negative_clamped_to_zero(self):
        """DIOT does not accept negatives; they must be clamped to 0."""
        self.assertEqual(_fmt_amount(-500), "0")

    def test_large_amount(self):
        self.assertEqual(_fmt_amount(1_000_000.0), "1000000")

    def test_integer_input(self):
        self.assertEqual(_fmt_amount(250), "250")


# ──────────────────────────────────────────────────────────────────────────────
# _safe_name
# ──────────────────────────────────────────────────────────────────────────────

class TestSafeName(unittest.TestCase):
    """Tests for _safe_name."""

    def test_strips_dots_and_spaces(self):
        self.assertEqual(_safe_name("Mi Empresa S.A. de C.V."), "Mi_Empresa_S_A__de_C_V_")

    def test_empty_string_returns_company(self):
        self.assertEqual(_safe_name(""), "company")

    def test_none_returns_company(self):
        self.assertEqual(_safe_name(None), "company")

    def test_alphanumeric_unchanged(self):
        self.assertEqual(_safe_name("Empresa2025"), "Empresa2025")

    def test_hyphens_preserved(self):
        self.assertEqual(_safe_name("Empresa-MX"), "Empresa-MX")


# ──────────────────────────────────────────────────────────────────────────────
# _build_diot_line — field count
# ──────────────────────────────────────────────────────────────────────────────

class TestBuildDIOTLine(unittest.TestCase):
    """Tests for _build_diot_line."""

    def _nacional_data(self, **overrides):
        base = {
            "tipo_tercero": "Nacional",
            "tipo_operacion": "Otros",
            "rfc": "EKU9003173C9",
            "nombre": "Test Company",
            "valor_16": 0,
            "valor_8": 0,
            "valor_0": 0,
            "valor_exento": 0,
            "iva_retenido": 0,
        }
        base.update(overrides)
        return base

    def test_line_has_exactly_24_fields(self):
        """Every DIOT line must produce exactly 24 pipe-separated fields."""
        line = _build_diot_line(self._nacional_data(valor_16=10000))
        fields = line.split("|")
        self.assertEqual(len(fields), DIOT_FIELD_COUNT)

    def test_nacional_tipo_tercero_code(self):
        """Nacional maps to code '04'."""
        line = _build_diot_line(self._nacional_data())
        self.assertEqual(line.split("|")[0], "04")

    def test_extranjero_tipo_tercero_code(self):
        """Extranjero maps to code '05'."""
        data = {
            "tipo_tercero": "Extranjero",
            "tipo_operacion": "Otros",
            "rfc": "",
            "nit": "12345",
            "nombre": "Foreign Corp",
            "pais_residencia": "US",
            "nacionalidad": "Estadounidense",
            "valor_16": 0,
            "valor_8": 0,
            "valor_0": 25000,
            "valor_exento": 0,
            "iva_retenido": 0,
        }
        line = _build_diot_line(data)
        fields = line.split("|")
        self.assertEqual(fields[0], "05")

    def test_servicios_profesionales_tipo_operacion_code(self):
        """Servicios Profesionales maps to code '85'."""
        line = _build_diot_line(
            self._nacional_data(tipo_operacion="Servicios Profesionales", valor_16=50000)
        )
        self.assertEqual(line.split("|")[1], "85")

    def test_arrendamiento_tipo_operacion_code(self):
        """Arrendamiento maps to code '06'."""
        line = _build_diot_line(self._nacional_data(tipo_operacion="Arrendamiento"))
        self.assertEqual(line.split("|")[1], "06")

    def test_valor_16_in_field_8(self):
        """valor_16 must appear in field index 7 (campo 8, 0-indexed)."""
        line = _build_diot_line(self._nacional_data(valor_16=50000))
        self.assertEqual(line.split("|")[7], "50000")

    def test_iva_retenido_in_field_19(self):
        """iva_retenido must appear in field index 18 (campo 19, 0-indexed)."""
        line = _build_diot_line(self._nacional_data(valor_16=50000, iva_retenido=8000))
        self.assertEqual(line.split("|")[18], "8000")

    def test_valor_0_in_field_17(self):
        """valor_0 (tasa 0%) must appear in field index 16 (campo 17, 0-indexed)."""
        line = _build_diot_line(self._nacional_data(valor_0=20000))
        self.assertEqual(line.split("|")[16], "20000")

    def test_valor_exento_in_field_18(self):
        """valor_exento must appear in field index 17 (campo 18, 0-indexed)."""
        line = _build_diot_line(self._nacional_data(valor_exento=5000))
        self.assertEqual(line.split("|")[17], "5000")

    def test_nacional_extranjero_fields_empty_for_nacional(self):
        """NIT, nombre, país, nacionalidad must be blank for Nacional suppliers."""
        line = _build_diot_line(self._nacional_data())
        fields = line.split("|")
        self.assertEqual(fields[3], "")   # NIT
        self.assertEqual(fields[4], "")   # nombre extranjero
        self.assertEqual(fields[5], "")   # país residencia
        self.assertEqual(fields[6], "")   # nacionalidad

    def test_extranjero_fields_populated(self):
        """NIT, nombre, país, nacionalidad must be set for Extranjero suppliers."""
        data = {
            "tipo_tercero": "Extranjero",
            "tipo_operacion": "Otros",
            "rfc": "",
            "nit": "12345",
            "nombre": "Foreign Corp",
            "pais_residencia": "US",
            "nacionalidad": "Estadounidense",
            "valor_16": 0,
            "valor_8": 0,
            "valor_0": 25000,
            "valor_exento": 0,
            "iva_retenido": 0,
        }
        fields = _build_diot_line(data).split("|")
        self.assertEqual(fields[3], "12345")
        self.assertEqual(fields[4], "Foreign Corp")
        self.assertEqual(fields[5], "US")
        self.assertEqual(fields[6], "Estadounidense")

    def test_rfc_padded_to_13_for_nacional(self):
        """Nacional RFC field must be left-justified and space-padded to 13 chars."""
        # EKU9003173C9 is 12 chars (persona moral) → padded to 13
        line = _build_diot_line(self._nacional_data(rfc="EKU9003173C9"))
        rfc_field = line.split("|")[2]
        self.assertEqual(len(rfc_field), 13)
        self.assertTrue(rfc_field.startswith("EKU9003173C9"))

    def test_padding_fields_empty_at_end(self):
        """The last 4 fields (indices 20-23) must be empty padding."""
        line = _build_diot_line(self._nacional_data())
        fields = line.split("|")
        for idx in range(20, 24):
            self.assertEqual(fields[idx], "")

    def test_negative_amounts_clamped_to_zero(self):
        """Negative monetary values must appear as '0' in the output."""
        line = _build_diot_line(self._nacional_data(valor_16=-5000, iva_retenido=-100))
        fields = line.split("|")
        self.assertEqual(fields[7], "0")   # valor_16
        self.assertEqual(fields[18], "0")  # iva_retenido


# ──────────────────────────────────────────────────────────────────────────────
# _classify_taxes_from_list
# ──────────────────────────────────────────────────────────────────────────────

class TestClassifyTaxesFromList(unittest.TestCase):
    """Tests for _classify_taxes_from_list."""

    def _iva_tax(self, rate, amount, description="IVA", account="IVA Trasladado",
                 charge_type="On Net Total"):
        return {
            "charge_type": charge_type,
            "rate": rate,
            "tax_amount": amount,
            "description": description,
            "account_head": account,
        }

    def test_iva_16_assigns_full_net_to_base_16(self):
        """Net total flows into base_16 when IVA 16% is present."""
        taxes = [self._iva_tax(16, 1600, "IVA 16%")]
        result = _classify_taxes_from_list(taxes, 10000.0)
        self.assertEqual(result["base_16"], 10000.0)
        self.assertEqual(result["base_8"], 0.0)
        self.assertEqual(result["base_0"], 0.0)
        self.assertEqual(result["base_exento"], 0.0)

    def test_iva_8_assigns_full_net_to_base_8(self):
        """Net total flows into base_8 when IVA 8% is present (no IVA 16%)."""
        taxes = [self._iva_tax(8, 800, "IVA 8%")]
        result = _classify_taxes_from_list(taxes, 10000.0)
        self.assertEqual(result["base_8"], 10000.0)
        self.assertEqual(result["base_16"], 0.0)

    def test_no_iva_assigns_full_net_to_exento(self):
        """When no IVA rows exist, net total goes to base_exento."""
        result = _classify_taxes_from_list([], 5000.0)
        self.assertEqual(result["base_exento"], 5000.0)
        self.assertEqual(result["base_16"], 0.0)

    def test_iva_0_assigns_full_net_to_base_0(self):
        """When only IVA 0% is present, net total goes to base_0."""
        taxes = [self._iva_tax(0, 0, "IVA 0%")]
        result = _classify_taxes_from_list(taxes, 3000.0)
        self.assertEqual(result["base_0"], 3000.0)
        self.assertEqual(result["base_exento"], 0.0)

    def test_iva_16_takes_priority_over_iva_8(self):
        """When both IVA 16% and IVA 8% rows appear, 16% wins."""
        taxes = [
            self._iva_tax(16, 1600, "IVA 16%"),
            self._iva_tax(8, 800, "IVA 8%"),
        ]
        result = _classify_taxes_from_list(taxes, 10000.0)
        self.assertEqual(result["base_16"], 10000.0)
        self.assertEqual(result["base_8"], 0.0)

    def test_retention_detected_by_negative_amount(self):
        """IVA row with negative tax_amount is treated as retention."""
        taxes = [
            self._iva_tax(16, 1600, "IVA 16%"),
            self._iva_tax(10.6667, -1066.67, "IVA Retenido 2/3", "IVA Retenido"),
        ]
        result = _classify_taxes_from_list(taxes, 10000.0)
        self.assertAlmostEqual(result["iva_retenido"], 1066.67, places=2)
        self.assertEqual(result["base_16"], 10000.0)

    def test_retention_detected_by_keyword_retenido(self):
        """Retention detected via 'RETENIDO' keyword in description."""
        taxes = [
            self._iva_tax(16, 1600, "IVA 16%"),
            self._iva_tax(10.6667, 1066.67, "IVA RETENIDO 2/3", "IVA Retenido"),
        ]
        result = _classify_taxes_from_list(taxes, 10000.0)
        self.assertAlmostEqual(result["iva_retenido"], 1066.67, places=2)

    def test_retiro_keyword_not_treated_as_retention(self):
        """'RETIRO' must NOT trigger retention logic (avoid false positive)."""
        # "RETIRO" could appear in account names unrelated to IVA retention
        taxes = [self._iva_tax(16, 1600, "IVA 16% RETIRO DE PRODUCTO", "IVA Trasladado")]
        result = _classify_taxes_from_list(taxes, 10000.0)
        # Should be treated as normal IVA 16%, not as a retention
        self.assertEqual(result["iva_retenido"], 0.0)
        self.assertEqual(result["base_16"], 10000.0)

    def test_non_iva_rows_ignored(self):
        """ISR and other non-IVA tax rows must not affect DIOT classification."""
        taxes = [
            self._iva_tax(16, 1600, "IVA 16%"),
            {"charge_type": "On Net Total", "rate": 10, "tax_amount": 1000,
             "description": "ISR Retenido", "account_head": "ISR Retenido"},
        ]
        result = _classify_taxes_from_list(taxes, 10000.0)
        self.assertEqual(result["base_16"], 10000.0)
        self.assertEqual(result["iva_retenido"], 0.0)  # ISR is not IVA retention

    def test_non_on_net_total_charge_type_ignored(self):
        """Rows with charge_type other than 'On Net Total' are excluded."""
        taxes = [
            self._iva_tax(16, 1600, "IVA 16%", charge_type="Actual"),
        ]
        result = _classify_taxes_from_list(taxes, 10000.0)
        self.assertEqual(result["base_16"], 0.0)
        self.assertEqual(result["base_exento"], 10000.0)


if __name__ == "__main__":
    unittest.main()
