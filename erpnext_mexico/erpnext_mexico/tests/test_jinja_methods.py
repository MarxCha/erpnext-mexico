# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

"""Tests para Jinja template helpers.

These are unit tests that run without a live Frappe site.
`frappe` is not imported by jinja_methods.py directly, but
amount_to_words.py may import it transitively. We install a
stub if needed.

The `qrcode` library may not be installed in all environments;
get_qr_code_data_uri has a built-in fallback to a 1×1 pixel PNG,
so all tests must accept both the full QR response and the fallback.
"""

import sys
import types
import unittest
from unittest.mock import MagicMock


# ──────────────────────────────────────────────────────────────────────────────
# Minimal stubs for optional transitive dependencies
# ──────────────────────────────────────────────────────────────────────────────

def _install_stubs():
    if "frappe" not in sys.modules:
        frappe_stub = types.ModuleType("frappe")
        frappe_stub._ = lambda s: s
        frappe_stub.throw = MagicMock(side_effect=Exception)
        sys.modules["frappe"] = frappe_stub

    if "frappe.utils" not in sys.modules:
        utils_stub = types.ModuleType("frappe.utils")
        sys.modules["frappe.utils"] = utils_stub


_install_stubs()


# ──────────────────────────────────────────────────────────────────────────────
# Tests: amount_to_words_mx
# ──────────────────────────────────────────────────────────────────────────────

class TestAmountToWords(unittest.TestCase):
    """Tests for amount_to_words_mx."""

    def test_is_callable(self):
        """amount_to_words_mx must be importable and callable."""
        from erpnext_mexico.utils.jinja_methods import amount_to_words_mx
        self.assertTrue(callable(amount_to_words_mx))

    def test_returns_string(self):
        """Must return a string for a standard MXN amount."""
        from erpnext_mexico.utils.jinja_methods import amount_to_words_mx
        result = amount_to_words_mx(1500.50)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_contains_pesos_for_mxn(self):
        """Output for MXN should reference 'PESO' (singular or plural)."""
        from erpnext_mexico.utils.jinja_methods import amount_to_words_mx
        result = amount_to_words_mx(1000.00)
        self.assertIn("PESO", result.upper())

    def test_zero_amount(self):
        """Zero amount must not raise and must return a string."""
        from erpnext_mexico.utils.jinja_methods import amount_to_words_mx
        result = amount_to_words_mx(0)
        self.assertIsInstance(result, str)

    def test_large_amount(self):
        """Large amounts must not raise."""
        from erpnext_mexico.utils.jinja_methods import amount_to_words_mx
        result = amount_to_words_mx(1_234_567.89)
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


# ──────────────────────────────────────────────────────────────────────────────
# Tests: format_rfc
# ──────────────────────────────────────────────────────────────────────────────

class TestFormatRFC(unittest.TestCase):
    """Tests for format_rfc."""

    def test_is_callable(self):
        from erpnext_mexico.utils.jinja_methods import format_rfc
        self.assertTrue(callable(format_rfc))

    def test_uppercases_and_strips(self):
        from erpnext_mexico.utils.jinja_methods import format_rfc
        self.assertEqual(format_rfc("  eku9003173c9  "), "EKU9003173C9")

    def test_none_returns_empty_string(self):
        from erpnext_mexico.utils.jinja_methods import format_rfc
        self.assertEqual(format_rfc(None), "")

    def test_empty_string_returns_empty_string(self):
        from erpnext_mexico.utils.jinja_methods import format_rfc
        self.assertEqual(format_rfc(""), "")


# ──────────────────────────────────────────────────────────────────────────────
# Tests: get_qr_code_data_uri
# ──────────────────────────────────────────────────────────────────────────────

# The fallback 1×1 pixel data URI returned when qrcode is not installed.
_FALLBACK_DATA_URI = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
_FALLBACK_PREFIX = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAY"

_QRCODE_AVAILABLE = False
try:
    import qrcode  # noqa: F401
    _QRCODE_AVAILABLE = True
except ImportError:
    pass


class TestQRCodeGeneration(unittest.TestCase):
    """Tests for get_qr_code_data_uri."""

    def test_is_callable(self):
        from erpnext_mexico.utils.jinja_methods import get_qr_code_data_uri
        self.assertTrue(callable(get_qr_code_data_uri))

    def test_returns_data_uri_prefix(self):
        """Result must always start with the PNG data URI prefix."""
        from erpnext_mexico.utils.jinja_methods import get_qr_code_data_uri
        result = get_qr_code_data_uri("https://example.com")
        self.assertTrue(result.startswith("data:image/png;base64,"),
                        f"Expected data URI prefix, got: {result[:60]}")

    def test_non_empty_result(self):
        """Result must be a non-empty string."""
        from erpnext_mexico.utils.jinja_methods import get_qr_code_data_uri
        result = get_qr_code_data_uri("test data")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_empty_input_does_not_raise(self):
        """Empty string must not raise — fallback or QR of empty data."""
        from erpnext_mexico.utils.jinja_methods import get_qr_code_data_uri
        result = get_qr_code_data_uri("")
        self.assertTrue(result.startswith("data:image/png;base64,"))

    @unittest.skipUnless(_QRCODE_AVAILABLE, "qrcode library not installed")
    def test_qrcode_result_larger_than_fallback(self):
        """When qrcode is installed, the real QR image must be larger than the 1px fallback."""
        from erpnext_mexico.utils.jinja_methods import get_qr_code_data_uri
        result = get_qr_code_data_uri("https://example.com/test")
        self.assertGreater(len(result), len(_FALLBACK_DATA_URI),
                           "Expected a real QR image, got the 1px fallback")

    @unittest.skipUnless(_QRCODE_AVAILABLE, "qrcode library not installed")
    def test_different_inputs_produce_different_qr(self):
        """Two different input strings must produce different QR data."""
        from erpnext_mexico.utils.jinja_methods import get_qr_code_data_uri
        r1 = get_qr_code_data_uri("https://example.com/a")
        r2 = get_qr_code_data_uri("https://example.com/b")
        self.assertNotEqual(r1, r2)

    def test_fallback_when_qrcode_missing(self):
        """When qrcode is not importable, the fallback 1px PNG is returned."""
        import importlib
        from unittest.mock import patch

        from erpnext_mexico.utils import jinja_methods

        with patch.dict(sys.modules, {"qrcode": None}):
            # Reload so ImportError branch is exercised
            importlib.reload(jinja_methods)
            result = jinja_methods.get_qr_code_data_uri("any data")
            self.assertTrue(result.startswith("data:image/png;base64,"))
            # After reload, restore original module
            importlib.reload(jinja_methods)


if __name__ == "__main__":
    unittest.main()
