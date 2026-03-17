# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

"""Tests para verificar integridad de fixtures de catálogos SAT."""

import json
import os
import unittest


FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "sat_catalogs",
    "fixtures",
)

# Conteo mínimo esperado por catálogo
EXPECTED_COUNTS = {
    "mx_fiscal_regime.json": 19,
    "mx_payment_form.json": 20,
    "mx_payment_method.json": 2,
    "mx_cfdi_use.json": 20,
    "mx_tax_object.json": 4,
    "mx_export_type.json": 4,
    "mx_cancellation_reason.json": 4,
    "mx_relation_type.json": 9,
    "mx_voucher_type.json": 5,
    "mx_tax_type.json": 3,
    "mx_tax_factor_type.json": 3,
}


class TestCatalogFixtures(unittest.TestCase):
    """Verifica que los fixtures JSON existen y son válidos."""

    def test_fixtures_directory_exists(self):
        self.assertTrue(os.path.isdir(FIXTURES_DIR), f"Directorio no existe: {FIXTURES_DIR}")

    def test_all_fixture_files_exist(self):
        for filename in EXPECTED_COUNTS:
            filepath = os.path.join(FIXTURES_DIR, filename)
            self.assertTrue(os.path.isfile(filepath), f"Fixture faltante: {filename}")

    def test_fixture_valid_json(self):
        for filename in EXPECTED_COUNTS:
            filepath = os.path.join(FIXTURES_DIR, filename)
            if not os.path.isfile(filepath):
                continue
            with open(filepath) as f:
                data = json.load(f)
            self.assertIsInstance(data, list, f"{filename} no es un array JSON")

    def test_fixture_minimum_records(self):
        for filename, min_count in EXPECTED_COUNTS.items():
            filepath = os.path.join(FIXTURES_DIR, filename)
            if not os.path.isfile(filepath):
                continue
            with open(filepath) as f:
                data = json.load(f)
            self.assertGreaterEqual(
                len(data), min_count,
                f"{filename}: esperado >= {min_count} registros, tiene {len(data)}",
            )

    def test_fixture_records_have_required_fields(self):
        for filename in EXPECTED_COUNTS:
            filepath = os.path.join(FIXTURES_DIR, filename)
            if not os.path.isfile(filepath):
                continue
            with open(filepath) as f:
                data = json.load(f)
            for i, record in enumerate(data):
                self.assertIn("doctype", record, f"{filename}[{i}]: falta 'doctype'")
                self.assertIn("code", record, f"{filename}[{i}]: falta 'code'")
                self.assertIn("description", record, f"{filename}[{i}]: falta 'description'")

    def test_no_duplicate_codes(self):
        for filename in EXPECTED_COUNTS:
            filepath = os.path.join(FIXTURES_DIR, filename)
            if not os.path.isfile(filepath):
                continue
            with open(filepath) as f:
                data = json.load(f)
            codes = [r["code"] for r in data]
            self.assertEqual(len(codes), len(set(codes)), f"{filename}: códigos duplicados")


if __name__ == "__main__":
    unittest.main()
