# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

"""Tests para el generador de XML CFDI 4.0.

These are unit tests that run without a live Frappe site.
`frappe` and `satcfdi` are stubbed in sys.modules before importing the
module under test so that no network or database access is needed.

The helper functions under test (_get_iva_rate_for_item, _build_concepto)
only call satcfdi constructors and operate on Python objects, so we use
lightweight fakes for the satcfdi data-model classes.
"""

import sys
import types
import unittest
from decimal import Decimal
from unittest.mock import MagicMock


# ──────────────────────────────────────────────────────────────────────────────
# Minimal fakes for satcfdi data-model classes
# ──────────────────────────────────────────────────────────────────────────────

class _FakeTraslado:
    def __init__(self, *, impuesto, tipo_factor, tasa_o_cuota, base):
        self.impuesto = impuesto
        self.tipo_factor = tipo_factor
        self.tasa_o_cuota = tasa_o_cuota
        self.base = base


class _FakeRetencion:
    def __init__(self, *, impuesto, tipo_factor, tasa_o_cuota, base):
        self.impuesto = impuesto
        self.tipo_factor = tipo_factor
        self.tasa_o_cuota = tasa_o_cuota
        self.base = base


class _FakeImpuestos:
    def __init__(self, *, traslados=None, retenciones=None):
        self.traslados = traslados
        self.retenciones = retenciones


class _FakeConcepto:
    def __init__(self, *, clave_prod_serv, cantidad, clave_unidad, unidad,
                 descripcion, valor_unitario, descuento=None, objeto_imp,
                 no_identificacion=None, impuestos=None):
        self.clave_prod_serv = clave_prod_serv
        self.cantidad = cantidad
        self.clave_unidad = clave_unidad
        self.unidad = unidad
        self.descripcion = descripcion
        self.valor_unitario = valor_unitario
        self.descuento = descuento
        self.objeto_imp = objeto_imp
        self.no_identificacion = no_identificacion
        self.impuestos = impuestos


# ──────────────────────────────────────────────────────────────────────────────
# Inject stubs into sys.modules BEFORE importing the module under test
# ──────────────────────────────────────────────────────────────────────────────

def _install_stubs():
    """Register lightweight stubs for frappe and satcfdi."""

    # -- frappe stub ----------------------------------------------------------
    frappe_stub = types.ModuleType("frappe")
    frappe_stub._ = lambda s: s  # translation passthrough
    frappe_stub.throw = MagicMock(side_effect=Exception)
    frappe_stub.get_cached_doc = MagicMock()
    frappe_stub.get_single = MagicMock()
    frappe_stub.db = MagicMock()
    frappe_stub.whitelist = lambda fn: fn  # decorator passthrough
    sys.modules.setdefault("frappe", frappe_stub)

    # -- satcfdi stub ---------------------------------------------------------
    # We need: satcfdi, satcfdi.create, satcfdi.create.cfd, satcfdi.create.cfd.cfdi40
    # and satcfdi.models.Signer

    cfdi40_stub = types.ModuleType("satcfdi.create.cfd.cfdi40")
    cfdi40_stub.Comprobante = MagicMock()
    cfdi40_stub.Emisor = MagicMock()
    cfdi40_stub.Receptor = MagicMock()
    cfdi40_stub.Traslado = _FakeTraslado
    cfdi40_stub.Retencion = _FakeRetencion
    cfdi40_stub.Impuestos = _FakeImpuestos
    cfdi40_stub.Concepto = _FakeConcepto
    cfdi40_stub.CfdiRelacionados = MagicMock()
    cfdi40_stub.CfdiRelacionado = MagicMock()

    cfd_stub = types.ModuleType("satcfdi.create.cfd")
    cfd_stub.cfdi40 = cfdi40_stub

    create_stub = types.ModuleType("satcfdi.create")
    create_stub.cfd = cfd_stub

    models_stub = types.ModuleType("satcfdi.models")
    models_stub.Signer = MagicMock()

    satcfdi_stub = types.ModuleType("satcfdi")
    satcfdi_stub.create = create_stub
    satcfdi_stub.models = models_stub

    for name, mod in [
        ("satcfdi", satcfdi_stub),
        ("satcfdi.create", create_stub),
        ("satcfdi.create.cfd", cfd_stub),
        ("satcfdi.create.cfd.cfdi40", cfdi40_stub),
        ("satcfdi.models", models_stub),
    ]:
        sys.modules.setdefault(name, mod)


_install_stubs()

# Now safe to import the helpers
from erpnext_mexico.cfdi.xml_builder import (  # noqa: E402
    _build_concepto,
    _get_iva_rate_for_item,
)


# ──────────────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestGetIVARate(unittest.TestCase):
    """Tests for _get_iva_rate_for_item."""

    def _doc_with_tax(self, rate, description, account_head="IVA Trasladado - TEST"):
        tax = MagicMock()
        tax.rate = rate
        tax.description = description
        tax.account_head = account_head
        doc = MagicMock()
        doc.taxes = [tax]
        return doc

    def test_iva_16_percent_returns_decimal(self):
        """IVA 16% template returns Decimal('0.160000')."""
        doc = self._doc_with_tax(16, "IVA 16%")
        rate = _get_iva_rate_for_item(doc)
        self.assertEqual(rate, Decimal("0.160000"))

    def test_iva_8_percent_border_zone(self):
        """IVA 8% border zone template returns Decimal('0.080000')."""
        doc = self._doc_with_tax(8, "IVA 8%")
        rate = _get_iva_rate_for_item(doc)
        self.assertEqual(rate, Decimal("0.080000"))

    def test_exempt_no_iva_rows_returns_none(self):
        """When taxes list is empty, returns None (exempt / tasa 0)."""
        doc = MagicMock()
        doc.taxes = []
        rate = _get_iva_rate_for_item(doc)
        self.assertIsNone(rate)

    def test_retention_row_not_returned_as_iva_rate(self):
        """Negative-rate (retention) rows must not be treated as the IVA rate."""
        tax_iva = MagicMock()
        tax_iva.rate = 16
        tax_iva.description = "IVA 16%"
        tax_iva.account_head = "IVA Trasladado"

        tax_ret = MagicMock()
        tax_ret.rate = -10
        tax_ret.description = "ISR Retenido 10%"
        tax_ret.account_head = "ISR Retenido"

        doc = MagicMock()
        doc.taxes = [tax_iva, tax_ret]

        rate = _get_iva_rate_for_item(doc)
        self.assertEqual(rate, Decimal("0.160000"))

    def test_none_doc_returns_default_16(self):
        """When doc is None, returns the default 16% rate."""
        rate = _get_iva_rate_for_item(None)
        self.assertEqual(rate, Decimal("0.160000"))

    def test_only_retention_no_positive_iva_returns_none(self):
        """If all IVA rows are retentions (negative rate), returns None."""
        tax_ret = MagicMock()
        tax_ret.rate = -10.6667
        tax_ret.description = "IVA Retenido 2/3"
        tax_ret.account_head = "IVA Retenido"

        doc = MagicMock()
        doc.taxes = [tax_ret]

        rate = _get_iva_rate_for_item(doc)
        self.assertIsNone(rate)

    def test_rate_quantized_to_six_decimal_places(self):
        """Any non-standard rate is quantized to 6 decimal places."""
        doc = self._doc_with_tax(7.5, "IVA 7.5% especial")
        rate = _get_iva_rate_for_item(doc)
        # 7.5 / 100 = 0.075 → quantized → Decimal('0.075000')
        self.assertEqual(rate, Decimal("0.075000"))


class TestBuildConcepto(unittest.TestCase):
    """Tests for _build_concepto."""

    def _make_item(self, *, objeto_imp="02", amount=1000, discount_amount=0,
                   rate=1000, qty=1):
        item = MagicMock()
        item.mx_objeto_imp = objeto_imp
        item.amount = amount
        item.discount_amount = discount_amount
        item.mx_clave_prod_serv = "01010101"
        item.qty = qty
        item.mx_clave_unidad = "H87"
        item.uom = "Pieza"
        item.description = "Test item"
        item.item_name = "Test"
        item.rate = rate
        item.item_code = "ITEM-001"
        return item

    def _make_doc_with_iva(self, rate=16, description="IVA 16%",
                           account="IVA Trasladado"):
        tax = MagicMock()
        tax.rate = rate
        tax.description = description
        tax.account_head = account
        doc = MagicMock()
        doc.taxes = [tax]
        return doc

    def test_objeto_imp_02_with_iva_16_has_traslados(self):
        """Concepto with ObjetoImp 02 and IVA 16% must include traslados."""
        item = self._make_item()
        doc = self._make_doc_with_iva()
        concepto = _build_concepto(item, doc)
        self.assertIsNotNone(concepto)
        self.assertIsNotNone(concepto.impuestos)
        self.assertIsNotNone(concepto.impuestos.traslados)
        self.assertEqual(len(concepto.impuestos.traslados), 1)

    def test_objeto_imp_01_no_impuestos(self):
        """Concepto with ObjetoImp 01 (no objeto de impuesto) has no traslados."""
        item = self._make_item(objeto_imp="01")
        doc = self._make_doc_with_iva()
        concepto = _build_concepto(item, doc)
        self.assertIsNone(concepto.impuestos)

    def test_no_double_discount_base_uses_item_amount(self):
        """
        item.amount is already the net amount after discount.
        The traslado base must equal item.amount, NOT (amount - discount_amount).
        """
        item = self._make_item(amount=900, discount_amount=100, rate=1000)
        doc = self._make_doc_with_iva()
        concepto = _build_concepto(item, doc)
        traslado = concepto.impuestos.traslados[0]
        self.assertEqual(traslado.base, Decimal("900"))

    def test_iva_traslado_impuesto_code_is_002(self):
        """IVA traslado must use SAT code '002' for IVA."""
        item = self._make_item()
        doc = self._make_doc_with_iva()
        concepto = _build_concepto(item, doc)
        traslado = concepto.impuestos.traslados[0]
        self.assertEqual(traslado.impuesto, "002")

    def test_iva_traslado_tasa_o_cuota_matches_doc(self):
        """Traslado tasa_o_cuota must reflect the template rate (8% border)."""
        item = self._make_item()
        doc = self._make_doc_with_iva(rate=8, description="IVA 8%")
        concepto = _build_concepto(item, doc)
        traslado = concepto.impuestos.traslados[0]
        self.assertEqual(traslado.tasa_o_cuota, Decimal("0.080000"))

    def test_isr_retention_adds_retencion(self):
        """ISR retention row in taxes produces a Retencion with impuesto '001'."""
        item = self._make_item()
        tax_iva = MagicMock()
        tax_iva.rate = 16
        tax_iva.description = "IVA 16%"
        tax_iva.account_head = "IVA Trasladado"

        tax_isr = MagicMock()
        tax_isr.rate = -10
        tax_isr.description = "ISR Retenido"
        tax_isr.account_head = "ISR Retenido"

        doc = MagicMock()
        doc.taxes = [tax_iva, tax_isr]

        concepto = _build_concepto(item, doc)
        self.assertIsNotNone(concepto.impuestos.retenciones)
        ret = concepto.impuestos.retenciones[0]
        self.assertEqual(ret.impuesto, "001")  # ISR

    def test_no_doc_uses_default_16_rate(self):
        """When doc=None, the 16% default rate is used for objeto_imp 02."""
        item = self._make_item()
        concepto = _build_concepto(item, None)
        self.assertIsNotNone(concepto.impuestos)
        traslado = concepto.impuestos.traslados[0]
        self.assertEqual(traslado.tasa_o_cuota, Decimal("0.160000"))

    def test_exempt_taxes_list_no_traslados(self):
        """Objeto_imp 02 with empty taxes list produces no traslados (exento)."""
        item = self._make_item(objeto_imp="02")
        doc = MagicMock()
        doc.taxes = []
        concepto = _build_concepto(item, doc)
        # None IVA rate → no traslados → no impuestos object
        self.assertIsNone(concepto.impuestos)


if __name__ == "__main__":
    unittest.main()
