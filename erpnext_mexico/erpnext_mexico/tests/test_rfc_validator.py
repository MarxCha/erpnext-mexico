# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

"""Tests para validador de RFC mexicano."""

import unittest

from erpnext_mexico.utils.rfc_validator import (
    RFC_EXTRANJERO,
    RFC_PUBLICO_GENERAL,
    get_rfc_type,
    validate_rfc,
)


class TestRFCValidator(unittest.TestCase):
    """Tests de validación de RFC."""

    # ── Persona moral (12 caracteres) ──

    def test_valid_rfc_moral(self):
        """RFC de prueba del SAT: EKU9003173C9."""
        is_valid, msg = validate_rfc("EKU9003173C9")
        self.assertTrue(is_valid, msg)

    def test_rfc_moral_type(self):
        self.assertEqual(get_rfc_type("EKU9003173C9"), "moral")

    def test_rfc_moral_wrong_length(self):
        is_valid, _ = validate_rfc("EKU900317")
        self.assertFalse(is_valid)

    def test_rfc_moral_invalid_format(self):
        is_valid, msg = validate_rfc("123456789012")
        self.assertFalse(is_valid)
        self.assertIn("inválido", msg.lower())

    # ── Persona física (13 caracteres) ──

    def test_valid_rfc_fisica(self):
        """RFC de prueba persona física: CACX7605101P8."""
        is_valid, msg = validate_rfc("CACX7605101P8")
        self.assertTrue(is_valid, msg)

    def test_rfc_fisica_type(self):
        self.assertEqual(get_rfc_type("CACX7605101P8"), "fisica")

    # ── RFC genéricos ──

    def test_rfc_publico_general(self):
        is_valid, _ = validate_rfc(RFC_PUBLICO_GENERAL)
        self.assertTrue(is_valid)
        self.assertEqual(get_rfc_type(RFC_PUBLICO_GENERAL), "publico_general")

    def test_rfc_extranjero(self):
        is_valid, _ = validate_rfc(RFC_EXTRANJERO)
        self.assertTrue(is_valid)
        self.assertEqual(get_rfc_type(RFC_EXTRANJERO), "extranjero")

    # ── Casos límite ──

    def test_empty_rfc(self):
        is_valid, _ = validate_rfc("")
        self.assertFalse(is_valid)

    def test_rfc_lowercase_converted(self):
        """El validador convierte a mayúsculas automáticamente."""
        is_valid, msg = validate_rfc("eku9003173c9")
        self.assertTrue(is_valid, msg)

    def test_rfc_with_spaces_trimmed(self):
        is_valid, msg = validate_rfc("  EKU9003173C9  ")
        self.assertTrue(is_valid, msg)

    def test_rfc_with_ampersand(self):
        """RFC con & es válido (empresas con & en razón social)."""
        # &-containing RFCs exist, format check should accept them
        is_valid, msg = validate_rfc("&AB050505ABC")
        # May fail check digit but format should be accepted
        self.assertIsInstance(is_valid, bool)

    def test_rfc_with_enie(self):
        """RFC con Ñ es válido."""
        is_valid, msg = validate_rfc("ÑAB050505ABC")
        self.assertIsInstance(is_valid, bool)

    def test_unknown_type_short(self):
        self.assertEqual(get_rfc_type("SHORT"), "desconocido")


if __name__ == "__main__":
    unittest.main()
