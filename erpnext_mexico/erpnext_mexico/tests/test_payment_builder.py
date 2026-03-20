# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

"""Tests para payment_builder.py — CFDI Complemento de Pagos 2.0.

Unit tests sin Frappe ni satcfdi reales.
Se stubbean en sys.modules antes de importar el módulo bajo prueba,
siguiendo el mismo patrón que test_xml_builder.py y test_nomina_builder.py.

Cubre:
- _to_datetime       — conversión de posting_date a datetime
- _parse_serie_folio — extracción de serie/folio del nombre de factura
- _get_tipo_cambio   — tipo de cambio para moneda del pago
- _get_equivalencia_dr — equivalencia entre moneda de factura y moneda de pago
- _build_impuestos_dr  — ImpuestosDR proporcional al monto pagado
- _get_pagos_anteriores — suma de pagos previos aplicados a una factura
- _get_num_parcialidad  — número de parcialidad del pago actual
"""

import sys
import types
import unittest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, call


# ──────────────────────────────────────────────────────────────────────────────
# Fakes para satcfdi.create.cfd.pago20
# ──────────────────────────────────────────────────────────────────────────────

class _FakeTrasladoDR:
    def __init__(self, *, base_dr, impuesto_dr, tipo_factor_dr,
                 tasa_o_cuota_dr, importe_dr):
        self.base_dr = base_dr
        self.impuesto_dr = impuesto_dr
        self.tipo_factor_dr = tipo_factor_dr
        self.tasa_o_cuota_dr = tasa_o_cuota_dr
        self.importe_dr = importe_dr


class _FakeImpuestosDR:
    def __init__(self, *, traslados_dr=None, retenciones_dr=None):
        self.traslados_dr = traslados_dr or []
        self.retenciones_dr = retenciones_dr or []


class _FakeDoctoRelacionado:
    def __init__(self, *, id_documento, moneda_dr, num_parcialidad,
                 imp_saldo_ant, imp_pagado, objeto_imp_dr,
                 serie=None, folio=None, equivalencia_dr=None,
                 impuestos_dr=None):
        self.id_documento = id_documento
        self.moneda_dr = moneda_dr
        self.num_parcialidad = num_parcialidad
        self.imp_saldo_ant = imp_saldo_ant
        self.imp_pagado = imp_pagado
        self.objeto_imp_dr = objeto_imp_dr
        self.serie = serie
        self.folio = folio
        self.equivalencia_dr = equivalencia_dr
        self.impuestos_dr = impuestos_dr


class _FakePago:
    def __init__(self, *, fecha_pago, forma_de_pago_p, moneda_p,
                 docto_relacionado, tipo_cambio_p=None):
        self.fecha_pago = fecha_pago
        self.forma_de_pago_p = forma_de_pago_p
        self.moneda_p = moneda_p
        self.docto_relacionado = docto_relacionado
        self.tipo_cambio_p = tipo_cambio_p


class _FakePagos:
    def __init__(self, *, pago):
        self.pago = pago


class _FakeEmisorCFDI:
    def __init__(self, *, rfc, nombre, regimen_fiscal):
        self.rfc = rfc
        self.nombre = nombre
        self.regimen_fiscal = regimen_fiscal


class _FakeReceptorCFDI:
    def __init__(self, *, rfc, nombre, domicilio_fiscal_receptor,
                 regimen_fiscal_receptor, uso_cfdi):
        self.uso_cfdi = uso_cfdi


class _FakeConceptoCFDI:
    def __init__(self, *, clave_prod_serv, cantidad, clave_unidad,
                 descripcion, valor_unitario, objeto_imp):
        self.clave_prod_serv = clave_prod_serv


class _FakeComprobante:
    def __init__(self, *, emisor, lugar_expedicion, receptor, conceptos,
                 tipo_de_comprobante, moneda, exportacion, complemento=None):
        self.tipo_de_comprobante = tipo_de_comprobante
        self.moneda = moneda
        self.complemento = complemento


# ──────────────────────────────────────────────────────────────────────────────
# Instalar stubs en sys.modules (antes de importar el módulo bajo prueba)
# ──────────────────────────────────────────────────────────────────────────────

def _install_stubs():
    """Registra stubs ligeros para frappe y satcfdi.

    Omite instalación si los módulos reales ya están cargados
    (entorno bench de Frappe con módulos reales disponibles).
    """
    if "frappe" in sys.modules and hasattr(sys.modules["frappe"], "get_doc"):
        return

    # -- frappe stub ----------------------------------------------------------
    frappe_stub = MagicMock()
    frappe_stub._ = lambda s, *a: s
    frappe_stub.throw = MagicMock(side_effect=Exception("frappe.throw called"))
    frappe_stub.msgprint = MagicMock()
    frappe_stub.utils.getdate = lambda s: date.fromisoformat(str(s))
    frappe_stub.db.sql = MagicMock(return_value=[[Decimal("0")]])
    frappe_stub.db.get_value = MagicMock(return_value=None)
    frappe_stub.get_cached_doc = MagicMock()
    sys.modules.setdefault("frappe", frappe_stub)

    # -- satcfdi stubs --------------------------------------------------------
    pago20_stub = types.ModuleType("satcfdi.create.cfd.pago20")
    pago20_stub.TrasladoDR = _FakeTrasladoDR
    pago20_stub.ImpuestosDR = _FakeImpuestosDR
    pago20_stub.DoctoRelacionado = _FakeDoctoRelacionado
    pago20_stub.Pago = _FakePago
    pago20_stub.Pagos = _FakePagos

    cfdi40_stub = types.ModuleType("satcfdi.create.cfd.cfdi40")
    cfdi40_stub.Emisor = _FakeEmisorCFDI
    cfdi40_stub.Receptor = _FakeReceptorCFDI
    cfdi40_stub.Concepto = _FakeConceptoCFDI
    cfdi40_stub.Comprobante = _FakeComprobante

    cfd_stub = types.ModuleType("satcfdi.create.cfd")
    cfd_stub.cfdi40 = cfdi40_stub
    cfd_stub.pago20 = pago20_stub

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
        ("satcfdi.create.cfd.pago20", pago20_stub),
        ("satcfdi.models", models_stub),
    ]:
        sys.modules.setdefault(name, mod)


_install_stubs()


# Importar helpers bajo prueba
from erpnext_mexico.cfdi.payment_builder import (  # noqa: E402
    _to_datetime,
    _parse_serie_folio,
    _get_tipo_cambio,
    _get_equivalencia_dr,
    _build_impuestos_dr,
    _get_pagos_anteriores,
    _get_num_parcialidad,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de construcción de objetos fake
# ──────────────────────────────────────────────────────────────────────────────

def _make_payment_entry(
    *,
    moneda="MXN",
    source_exchange_rate=None,
    paid_from_exchange_rate=None,
):
    """Construye un Payment Entry fake con los atributos mínimos."""
    pe = MagicMock()
    pe.paid_from_account_currency = moneda
    pe.source_exchange_rate = source_exchange_rate
    pe.paid_from_account_exchange_rate = paid_from_exchange_rate
    return pe


def _make_tax_row(rate, description, account_head="IVA Trasladado - MX"):
    """Construye una fila de impuesto fake con acceso por atributo.

    frappe.db.sql(..., as_dict=True) devuelve frappe.Dict objects, que
    soportan acceso por atributo (tax.rate). Usamos MagicMock para replicar
    este comportamiento sin necesitar el módulo frappe real.
    """
    row = MagicMock()
    row.rate = rate
    row.description = description
    row.account_head = account_head
    return row


# ──────────────────────────────────────────────────────────────────────────────
# TestToDatetime
# ──────────────────────────────────────────────────────────────────────────────

class TestToDatetime(unittest.TestCase):
    """Tests para _to_datetime — convierte posting_date a datetime."""

    def test_str_iso_returns_datetime(self):
        """Una cadena 'YYYY-MM-DD' válida debe retornar un datetime."""
        result = _to_datetime("2024-06-15")
        self.assertIsInstance(result, datetime)

    def test_str_iso_correct_date_parts(self):
        """Los componentes year/month/day deben corresponder a la cadena."""
        result = _to_datetime("2024-06-15")
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)

    def test_str_iso_time_is_midnight(self):
        """La hora resultante debe ser 00:00:00 (inicio del día)."""
        result = _to_datetime("2024-01-01")
        self.assertEqual(result.hour, 0)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.second, 0)

    def test_date_object_returns_datetime(self):
        """Un objeto date de Python debe convertirse a datetime."""
        d = date(2024, 3, 20)
        result = _to_datetime(d)
        self.assertIsInstance(result, datetime)

    def test_date_object_correct_parts(self):
        """Los campos del objeto date deben preservarse en el datetime."""
        d = date(2024, 3, 20)
        result = _to_datetime(d)
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 3)
        self.assertEqual(result.day, 20)

    def test_date_object_time_is_midnight(self):
        """Un date convertido debe tener hora 00:00:00."""
        result = _to_datetime(date(2025, 12, 31))
        self.assertEqual(result.hour, 0)
        self.assertEqual(result.second, 0)

    def test_datetime_object_returned_as_is(self):
        """Un datetime ya construido debe devolverse sin modificación."""
        dt = datetime(2024, 7, 4, 9, 30, 0)
        result = _to_datetime(dt)
        self.assertIs(result, dt)

    def test_datetime_preserves_time_components(self):
        """Un datetime con hora específica no debe perder la hora."""
        dt = datetime(2024, 7, 4, 9, 30, 45)
        result = _to_datetime(dt)
        self.assertEqual(result.hour, 9)
        self.assertEqual(result.minute, 30)
        self.assertEqual(result.second, 45)

    def test_invalid_type_returns_datetime_instance(self):
        """Para un tipo no reconocido debe retornar un datetime (datetime.now)."""
        result = _to_datetime(None)
        self.assertIsInstance(result, datetime)

    def test_integer_type_returns_datetime_instance(self):
        """Un entero no reconocido debe retornar datetime.now sin lanzar."""
        result = _to_datetime(12345)
        self.assertIsInstance(result, datetime)

    def test_first_day_of_year(self):
        """Fecha borde 1 de enero debe procesarse sin errores."""
        result = _to_datetime("2024-01-01")
        self.assertEqual(result.month, 1)
        self.assertEqual(result.day, 1)

    def test_last_day_of_year(self):
        """Fecha borde 31 de diciembre debe procesarse sin errores."""
        result = _to_datetime("2024-12-31")
        self.assertEqual(result.month, 12)
        self.assertEqual(result.day, 31)


# ──────────────────────────────────────────────────────────────────────────────
# TestParseSerieFollio
# ──────────────────────────────────────────────────────────────────────────────

class TestParseSerieFollio(unittest.TestCase):
    """Tests para _parse_serie_folio — extrae serie y folio del nombre."""

    def test_standard_naming_convention(self):
        """'FACT-2024-00001' → serie='FACT', folio='2024-00001'."""
        serie, folio = _parse_serie_folio("FACT-2024-00001")
        self.assertEqual(serie, "FACT")
        self.assertEqual(folio, "2024-00001")

    def test_only_first_dash_splits(self):
        """Solo el primer guión separa serie de folio; el resto pertenece al folio."""
        serie, folio = _parse_serie_folio("INV-2024-00123")
        self.assertEqual(serie, "INV")
        self.assertEqual(folio, "2024-00123")

    def test_no_dash_returns_none_serie(self):
        """Sin guión la serie debe ser None y el folio el nombre completo."""
        serie, folio = _parse_serie_folio("FACTURA001")
        self.assertIsNone(serie)
        self.assertEqual(folio, "FACTURA001")

    def test_no_dash_folio_truncated_at_40(self):
        """Sin guión el folio no debe exceder 40 caracteres."""
        long_name = "A" * 50
        serie, folio = _parse_serie_folio(long_name)
        self.assertIsNone(serie)
        self.assertLessEqual(len(folio), 40)

    def test_serie_truncated_at_25(self):
        """La serie no debe exceder 25 caracteres."""
        long_serie = "S" * 30 + "-0001"
        serie, folio = _parse_serie_folio(long_serie)
        self.assertLessEqual(len(serie), 25)

    def test_folio_truncated_at_40(self):
        """El folio no debe exceder 40 caracteres."""
        long_folio = "FACT-" + "9" * 50
        serie, folio = _parse_serie_folio(long_folio)
        self.assertLessEqual(len(folio), 40)

    def test_single_dash_prefix(self):
        """'A-001' → serie='A', folio='001'."""
        serie, folio = _parse_serie_folio("A-001")
        self.assertEqual(serie, "A")
        self.assertEqual(folio, "001")

    def test_typical_erpnext_series_acc(self):
        """'ACC-SINV-2024-00001' → serie='ACC', folio='SINV-2024-00001'."""
        serie, folio = _parse_serie_folio("ACC-SINV-2024-00001")
        self.assertEqual(serie, "ACC")
        self.assertEqual(folio, "SINV-2024-00001")

    def test_empty_string_returns_none_serie_empty_folio(self):
        """Cadena vacía → (None, '') sin error."""
        serie, folio = _parse_serie_folio("")
        self.assertIsNone(serie)
        self.assertEqual(folio, "")

    def test_dash_only(self):
        """Solo guión '-' → serie='', folio=''."""
        serie, folio = _parse_serie_folio("-")
        self.assertEqual(serie, "")
        self.assertEqual(folio, "")


# ──────────────────────────────────────────────────────────────────────────────
# TestGetTipoCambio
# ──────────────────────────────────────────────────────────────────────────────

class TestGetTipoCambio(unittest.TestCase):
    """Tests para _get_tipo_cambio — tipo de cambio del pago."""

    def test_mxn_returns_one(self):
        """Moneda MXN siempre retorna Decimal('1') sin importar el payment entry."""
        pe = _make_payment_entry(moneda="MXN", source_exchange_rate=18.5)
        result = _get_tipo_cambio(pe, "MXN")
        self.assertEqual(result, Decimal("1"))

    def test_mxn_explicit_decimal(self):
        """El valor exacto retornado para MXN debe ser Decimal('1'), no float."""
        pe = _make_payment_entry(moneda="MXN")
        result = _get_tipo_cambio(pe, "MXN")
        self.assertIsInstance(result, Decimal)
        self.assertEqual(result, Decimal("1"))

    def test_usd_uses_source_exchange_rate(self):
        """Para USD usa source_exchange_rate del payment entry."""
        pe = _make_payment_entry(moneda="USD", source_exchange_rate=17.25)
        result = _get_tipo_cambio(pe, "USD")
        self.assertEqual(result, Decimal("17.25"))

    def test_usd_uses_paid_from_exchange_rate_fallback(self):
        """Sin source_exchange_rate cae back a paid_from_account_exchange_rate."""
        pe = _make_payment_entry(
            moneda="USD",
            source_exchange_rate=None,
            paid_from_exchange_rate=16.50,
        )
        result = _get_tipo_cambio(pe, "USD")
        self.assertEqual(result, Decimal("16.5"))

    def test_foreign_currency_no_rate_returns_one(self):
        """Sin ningún tipo de cambio disponible retorna Decimal('1') como fallback."""
        pe = _make_payment_entry(
            moneda="EUR",
            source_exchange_rate=None,
            paid_from_exchange_rate=None,
        )
        result = _get_tipo_cambio(pe, "EUR")
        self.assertEqual(result, Decimal("1"))

    def test_result_is_always_decimal(self):
        """El resultado debe ser siempre un Decimal, nunca float."""
        pe = _make_payment_entry(moneda="USD", source_exchange_rate=19.999)
        result = _get_tipo_cambio(pe, "USD")
        self.assertIsInstance(result, Decimal)

    def test_zero_source_rate_falls_to_paid_from(self):
        """Un source_exchange_rate de 0 (falsy) debe caer al paid_from_account_exchange_rate."""
        pe = _make_payment_entry(
            moneda="USD",
            source_exchange_rate=0,
            paid_from_exchange_rate=18.0,
        )
        result = _get_tipo_cambio(pe, "USD")
        # 0 es falsy → debe usar el fallback paid_from_account_exchange_rate
        self.assertEqual(result, Decimal("18"))


# ──────────────────────────────────────────────────────────────────────────────
# TestGetEquivalenciaDR
# ──────────────────────────────────────────────────────────────────────────────

class TestGetEquivalenciaDR(unittest.TestCase):
    """Tests para _get_equivalencia_dr — equivalencia entre monedas."""

    def test_same_currency_returns_one(self):
        """SAT CRP20277: monedaDR == monedaP → equivalencia = 1."""
        pe = _make_payment_entry(moneda="MXN", source_exchange_rate=18.0)
        result = _get_equivalencia_dr("MXN", "MXN", pe)
        self.assertEqual(result, Decimal("1"))

    def test_same_currency_usd_returns_one(self):
        """Cuando ambas monedas son USD la equivalencia debe ser 1."""
        pe = _make_payment_entry(moneda="USD", source_exchange_rate=1.0)
        result = _get_equivalencia_dr("USD", "USD", pe)
        self.assertEqual(result, Decimal("1"))

    def test_different_currencies_uses_source_rate(self):
        """Factura en MXN, pago en USD → usa source_exchange_rate."""
        pe = _make_payment_entry(moneda="USD", source_exchange_rate=17.5)
        result = _get_equivalencia_dr("MXN", "USD", pe)
        self.assertEqual(result, Decimal("17.5"))

    def test_different_currencies_no_rate_returns_one(self):
        """Sin tipo de cambio disponible retorna Decimal('1')."""
        pe = _make_payment_entry(
            moneda="EUR",
            source_exchange_rate=None,
            paid_from_exchange_rate=None,
        )
        result = _get_equivalencia_dr("MXN", "EUR", pe)
        self.assertEqual(result, Decimal("1"))

    def test_result_is_decimal(self):
        """La equivalencia debe ser siempre Decimal."""
        pe = _make_payment_entry(moneda="USD", source_exchange_rate=20.123)
        result = _get_equivalencia_dr("MXN", "USD", pe)
        self.assertIsInstance(result, Decimal)

    def test_same_currency_ignores_exchange_rate(self):
        """Aunque haya tipo de cambio, si monedas iguales retorna 1."""
        pe = _make_payment_entry(moneda="MXN", source_exchange_rate=0.0001)
        result = _get_equivalencia_dr("MXN", "MXN", pe)
        self.assertEqual(result, Decimal("1"))


# ──────────────────────────────────────────────────────────────────────────────
# TestBuildImpuestosDR
# ──────────────────────────────────────────────────────────────────────────────

class TestBuildImpuestosDR(unittest.TestCase):
    """Tests para _build_impuestos_dr — IVA proporcional al monto pagado.

    frappe.db.sql(..., as_dict=True) devuelve frappe.Dict (acceso por atributo).
    El mock debe proveer MagicMock objects, no plain dicts, porque el código
    de producción accede a tax.rate, tax.description, tax.account_head.
    """

    def _mock_taxes(self, rows):
        """Configura frappe.db.sql para retornar filas con acceso por atributo.

        Acepta filas como dicts {'rate': x, 'description': y, 'account_head': z}
        y los convierte a MagicMock objects para que tax.rate etc. funcionen.
        """
        mock_rows = []
        for row in rows:
            if isinstance(row, dict):
                mock_row = _make_tax_row(
                    rate=row.get("rate", 0),
                    description=row.get("description", ""),
                    account_head=row.get("account_head", ""),
                )
            else:
                mock_row = row
            mock_rows.append(mock_row)
        sys.modules["frappe"].db.sql = MagicMock(return_value=mock_rows)

    def test_iva_16_traslado_created(self):
        """IVA 16% debe crear un TrasladoDR con impuesto_dr='002'."""
        self._mock_taxes([{
            "rate": 16,
            "description": "IVA 16%",
            "account_head": "IVA Trasladado - MX",
        }])
        imp_pagado = Decimal("1160")
        grand_total = Decimal("1160")
        result = _build_impuestos_dr("FACT-001", imp_pagado, grand_total)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.traslados_dr), 1)
        self.assertEqual(result.traslados_dr[0].impuesto_dr, "002")

    def test_iva_16_tasa_o_cuota(self):
        """El TrasladoDR para IVA 16% debe tener tasa_o_cuota_dr=0.160000."""
        self._mock_taxes([{
            "rate": 16,
            "description": "IVA 16%",
            "account_head": "IVA Trasladado - MX",
        }])
        result = _build_impuestos_dr("FACT-001", Decimal("1160"), Decimal("1160"))
        self.assertEqual(
            result.traslados_dr[0].tasa_o_cuota_dr,
            Decimal("0.160000"),
        )

    def test_iva_16_base_calculation(self):
        """Base DR = imp_pagado / (1 + tasa) redondeada a 2 decimales."""
        self._mock_taxes([{
            "rate": 16,
            "description": "IVA 16%",
            "account_head": "IVA Trasladado",
        }])
        imp_pagado = Decimal("1160.00")
        grand_total = Decimal("1160.00")
        result = _build_impuestos_dr("FACT-001", imp_pagado, grand_total)
        traslado = result.traslados_dr[0]
        # 1160 / 1.16 = 1000.00
        self.assertEqual(traslado.base_dr, Decimal("1000.00"))

    def test_iva_16_importe_calculation(self):
        """Importe DR = base_dr * tasa, redondeado a 2 decimales."""
        self._mock_taxes([{
            "rate": 16,
            "description": "IVA 16%",
            "account_head": "IVA Trasladado",
        }])
        result = _build_impuestos_dr("FACT-001", Decimal("1160.00"), Decimal("1160.00"))
        traslado = result.traslados_dr[0]
        # base=1000 * 0.16 = 160.00
        self.assertEqual(traslado.importe_dr, Decimal("160.00"))

    def test_iva_8_border_zone(self):
        """IVA 8% (zona fronteriza) debe crear TrasladoDR con tasa 0.080000."""
        self._mock_taxes([{
            "rate": 8,
            "description": "IVA 8%",
            "account_head": "IVA Trasladado Frontera",
        }])
        result = _build_impuestos_dr("FACT-002", Decimal("1080.00"), Decimal("1080.00"))
        self.assertIsNotNone(result)
        self.assertEqual(
            result.traslados_dr[0].tasa_o_cuota_dr,
            Decimal("0.080000"),
        )

    def test_iva_8_base_and_importe(self):
        """Para IVA 8%: base = 1080/1.08 = 1000, importe = 80."""
        self._mock_taxes([{
            "rate": 8,
            "description": "IVA 8%",
            "account_head": "IVA Trasladado Frontera",
        }])
        result = _build_impuestos_dr("FACT-002", Decimal("1080.00"), Decimal("1080.00"))
        traslado = result.traslados_dr[0]
        self.assertEqual(traslado.base_dr, Decimal("1000.00"))
        self.assertEqual(traslado.importe_dr, Decimal("80.00"))

    def test_tipo_factor_dr_is_tasa(self):
        """tipo_factor_dr debe ser 'Tasa' (catálogo SAT)."""
        self._mock_taxes([{
            "rate": 16,
            "description": "IVA 16%",
            "account_head": "IVA Trasladado",
        }])
        result = _build_impuestos_dr("FACT-001", Decimal("1160.00"), Decimal("1160.00"))
        self.assertEqual(result.traslados_dr[0].tipo_factor_dr, "Tasa")

    def test_no_iva_rows_returns_none(self):
        """Sin filas de IVA debe retornar None (no se construye ImpuestosDR)."""
        self._mock_taxes([])
        result = _build_impuestos_dr("FACT-003", Decimal("500.00"), Decimal("500.00"))
        self.assertIsNone(result)

    def test_iva_identified_by_account_head(self):
        """IVA debe detectarse por el account_head aunque description no lo diga."""
        self._mock_taxes([{
            "rate": 16,
            "description": "Impuesto indirecto",
            "account_head": "IVA Trasladado - Empresa",
        }])
        result = _build_impuestos_dr("FACT-004", Decimal("1160.00"), Decimal("1160.00"))
        self.assertIsNotNone(result)
        self.assertEqual(len(result.traslados_dr), 1)

    def test_iva_identified_by_valor_agregado_description(self):
        """'Valor Agregado' en descripción también debe detectarse como IVA."""
        self._mock_taxes([{
            "rate": 16,
            "description": "Impuesto al Valor Agregado 16%",
            "account_head": "Tax Account",
        }])
        result = _build_impuestos_dr("FACT-005", Decimal("1160.00"), Decimal("1160.00"))
        self.assertIsNotNone(result)

    def test_non_iva_tax_excluded(self):
        """ISR u otros impuestos no IVA no deben generar TrasladoDR."""
        self._mock_taxes([{
            "rate": 10,
            "description": "ISR Retenido",
            "account_head": "ISR Retenido - MX",
        }])
        result = _build_impuestos_dr("FACT-006", Decimal("1100.00"), Decimal("1100.00"))
        self.assertIsNone(result)

    def test_zero_rate_row_excluded(self):
        """Filas de IVA con tasa 0 no deben generar TrasladoDR."""
        self._mock_taxes([{
            "rate": 0,
            "description": "IVA 0%",
            "account_head": "IVA Exento",
        }])
        result = _build_impuestos_dr("FACT-007", Decimal("1000.00"), Decimal("1000.00"))
        self.assertIsNone(result)

    def test_partial_payment_proportional_base(self):
        """Un pago parcial debe calcular la base proporcional correctamente."""
        self._mock_taxes([{
            "rate": 16,
            "description": "IVA 16%",
            "account_head": "IVA Trasladado",
        }])
        # Pago de 580 sobre una factura de 1160 (50%)
        imp_pagado = Decimal("580.00")
        grand_total = Decimal("1160.00")
        result = _build_impuestos_dr("FACT-008", imp_pagado, grand_total)
        self.assertIsNotNone(result)
        traslado = result.traslados_dr[0]
        # base = 580 / 1.16 = 500.00
        self.assertEqual(traslado.base_dr, Decimal("500.00"))
        # importe = 500 * 0.16 = 80.00
        self.assertEqual(traslado.importe_dr, Decimal("80.00"))

    def test_frappe_db_sql_called_with_invoice_name(self):
        """frappe.db.sql debe invocarse con el nombre de la factura como segundo arg."""
        self._mock_taxes([])
        _build_impuestos_dr("FACT-TEST-999", Decimal("100.00"), Decimal("100.00"))
        call_args = sys.modules["frappe"].db.sql.call_args
        # call signature: sql(query_str, invoice_name, as_dict=True)
        self.assertEqual(call_args[0][1], "FACT-TEST-999")


# ──────────────────────────────────────────────────────────────────────────────
# TestGetPagosAnteriores
# ──────────────────────────────────────────────────────────────────────────────

class TestGetPagosAnteriores(unittest.TestCase):
    """Tests para _get_pagos_anteriores — suma pagos previos a una factura."""

    def _set_sql_result(self, value):
        """Configura frappe.db.sql para retornar el valor dado."""
        sys.modules["frappe"].db.sql = MagicMock(return_value=[[value]])

    def test_no_previous_payments_returns_zero(self):
        """Sin pagos anteriores debe retornar Decimal('0')."""
        self._set_sql_result(Decimal("0"))
        result = _get_pagos_anteriores("FACT-2024-00001", "PAY-001")
        self.assertEqual(result, Decimal("0"))

    def test_single_previous_payment(self):
        """Un pago anterior debe retornar ese monto como Decimal."""
        self._set_sql_result(Decimal("5000.00"))
        result = _get_pagos_anteriores("FACT-2024-00001", "PAY-002")
        self.assertEqual(result, Decimal("5000.00"))

    def test_multiple_previous_payments_summed(self):
        """La DB suma internamente via COALESCE; el resultado es el total retornado."""
        self._set_sql_result(Decimal("12500.50"))
        result = _get_pagos_anteriores("FACT-2024-00001", "PAY-003")
        self.assertEqual(result, Decimal("12500.50"))

    def test_empty_sql_result_returns_zero(self):
        """Un resultado vacío de la DB debe retornar Decimal('0')."""
        sys.modules["frappe"].db.sql = MagicMock(return_value=[])
        result = _get_pagos_anteriores("FACT-2024-00001", "PAY-001")
        self.assertEqual(result, Decimal("0"))

    def test_result_is_decimal_type(self):
        """El resultado siempre debe ser Decimal, nunca float ni str."""
        self._set_sql_result(Decimal("999.99"))
        result = _get_pagos_anteriores("FACT-2024-00001", "PAY-001")
        self.assertIsInstance(result, Decimal)

    def test_sql_called_with_correct_params(self):
        """frappe.db.sql debe llamarse con invoice_name y payment_name en la tupla."""
        self._set_sql_result(Decimal("0"))
        _get_pagos_anteriores("FACT-2024-00042", "PAY-CURRENT-001")
        call_args = sys.modules["frappe"].db.sql.call_args
        positional_args = call_args[0]
        # El segundo argumento es la tupla de parámetros SQL: (invoice_name, payment_name)
        self.assertIn("FACT-2024-00042", positional_args[1])
        self.assertIn("PAY-CURRENT-001", positional_args[1])

    def test_fractional_amount_preserved(self):
        """Montos con centavos deben preservarse sin redondeo."""
        self._set_sql_result(Decimal("3333.33"))
        result = _get_pagos_anteriores("FACT-001", "PAY-001")
        self.assertEqual(result, Decimal("3333.33"))

    def test_large_amount(self):
        """Montos grandes (facturas corporativas) deben manejarse sin desborde."""
        self._set_sql_result(Decimal("9999999.99"))
        result = _get_pagos_anteriores("FACT-001", "PAY-001")
        self.assertEqual(result, Decimal("9999999.99"))


# ──────────────────────────────────────────────────────────────────────────────
# TestGetNumParcialidad
# ──────────────────────────────────────────────────────────────────────────────

class TestGetNumParcialidad(unittest.TestCase):
    """Tests para _get_num_parcialidad — número de parcialidad del pago."""

    def _set_sql_count(self, count):
        """Configura frappe.db.sql para retornar el conteo dado."""
        sys.modules["frappe"].db.sql = MagicMock(return_value=[[count]])

    def test_first_payment_returns_one(self):
        """Sin pagos anteriores (count=0) el número de parcialidad es 1."""
        self._set_sql_count(0)
        result = _get_num_parcialidad("FACT-2024-00001", "PAY-001")
        self.assertEqual(result, 1)

    def test_second_payment_returns_two(self):
        """Con un pago anterior la parcialidad es 2."""
        self._set_sql_count(1)
        result = _get_num_parcialidad("FACT-2024-00001", "PAY-002")
        self.assertEqual(result, 2)

    def test_third_payment_returns_three(self):
        """Con dos pagos anteriores la parcialidad es 3."""
        self._set_sql_count(2)
        result = _get_num_parcialidad("FACT-2024-00001", "PAY-003")
        self.assertEqual(result, 3)

    def test_large_parcialidad(self):
        """Parcialidades grandes (pagos en muchas cuotas) deben calcularse bien."""
        self._set_sql_count(11)
        result = _get_num_parcialidad("FACT-2024-00001", "PAY-012")
        self.assertEqual(result, 12)

    def test_empty_sql_result_returns_one(self):
        """Si la consulta no retorna filas, asume 0 anteriores → parcialidad 1."""
        sys.modules["frappe"].db.sql = MagicMock(return_value=[])
        result = _get_num_parcialidad("FACT-2024-00001", "PAY-001")
        self.assertEqual(result, 1)

    def test_result_is_integer(self):
        """El número de parcialidad debe ser int, no Decimal ni float."""
        self._set_sql_count(3)
        result = _get_num_parcialidad("FACT-2024-00001", "PAY-004")
        self.assertIsInstance(result, int)

    def test_sql_called_with_correct_params(self):
        """frappe.db.sql debe invocarse con invoice_name y current_payment_name."""
        self._set_sql_count(0)
        _get_num_parcialidad("FACT-2024-00099", "PAY-CURRENT-XYZ")
        call_args = sys.modules["frappe"].db.sql.call_args
        positional_args = call_args[0]
        self.assertIn("FACT-2024-00099", positional_args[1])
        self.assertIn("PAY-CURRENT-XYZ", positional_args[1])

    def test_current_payment_excluded_from_count(self):
        """El pago actual debe estar excluido de la cuenta (verificado via SQL params)."""
        self._set_sql_count(0)
        _get_num_parcialidad("FACT-001", "PAY-ACTUAL")
        call_args = sys.modules["frappe"].db.sql.call_args
        positional_args = call_args[0]
        # El nombre del pago actual debe aparecer en los params del WHERE pe.name != %s
        self.assertIn("PAY-ACTUAL", positional_args[1])


if __name__ == "__main__":
    unittest.main()
