# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

"""Tests para el constructor de Carta Porte 3.1 (cfdi/carta_porte_builder.py).

These are pure unit tests that run without a live Frappe site.
`frappe` and `satcfdi` are stubbed in sys.modules before the module under
test is imported so no database or network access is needed.

The helpers under test (_validate_company_fiscal_data,
_validate_carta_porte_data, _build_mercancias, _build_fecha_hora)
only construct satcfdi objects and validate Python MagicMocks, so lightweight
fakes for the satcfdi data-model classes are sufficient.
"""

import sys
import types
import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock


# ──────────────────────────────────────────────────────────────────────────────
# Minimal fakes for satcfdi.create.cfd.cartaporte31 data-model classes
# ──────────────────────────────────────────────────────────────────────────────

class _FakeDomicilio:
    def __init__(self, *, estado="", pais="MEX", codigo_postal="",
                 municipio=None, localidad=None, referencia=None, calle=None):
        self.estado = estado
        self.pais = pais
        self.codigo_postal = codigo_postal
        self.municipio = municipio
        self.localidad = localidad
        self.referencia = referencia
        self.calle = calle


class _FakeUbicacion:
    def __init__(self, *, tipo_ubicacion, id_ubicacion="", rfc_remitente_destinatario="",
                 fecha_hora_salida_llegada=None, distancia_recorrida=None, domicilio=None):
        self.tipo_ubicacion = tipo_ubicacion
        self.id_ubicacion = id_ubicacion
        self.rfc_remitente_destinatario = rfc_remitente_destinatario
        self.fecha_hora_salida_llegada = fecha_hora_salida_llegada
        self.distancia_recorrida = distancia_recorrida
        self.domicilio = domicilio


class _FakeMercancia:
    def __init__(self, *, bienes_transp="", descripcion="", cantidad=Decimal("1"),
                 clave_unidad="H87", peso_en_kg=Decimal("0.001"),
                 valor_mercancia=None, moneda=None):
        self.bienes_transp = bienes_transp
        self.descripcion = descripcion
        self.cantidad = cantidad
        self.clave_unidad = clave_unidad
        self.peso_en_kg = peso_en_kg
        self.valor_mercancia = valor_mercancia
        self.moneda = moneda


class _FakeAutotransporte:
    def __init__(self, *, perm_sct, num_permiso_sct, seguros,
                 identificacion_vehicular):
        self.perm_sct = perm_sct
        self.num_permiso_sct = num_permiso_sct
        self.seguros = seguros
        self.identificacion_vehicular = identificacion_vehicular


class _FakeSeguros:
    def __init__(self, *, asegura_resp_civil, poliza_resp_civil):
        self.asegura_resp_civil = asegura_resp_civil
        self.poliza_resp_civil = poliza_resp_civil


class _FakeIdentificacionVehicular:
    def __init__(self, *, config_vehicular, placa_vm, anio_modelo_vm):
        self.config_vehicular = config_vehicular
        self.placa_vm = placa_vm
        self.anio_modelo_vm = anio_modelo_vm


class _FakeMercancias:
    def __init__(self, *, peso_bruto_total=Decimal("0"), unidad_peso="KGM",
                 num_total_mercancias=0, mercancia=None, autotransporte=None):
        self.peso_bruto_total = peso_bruto_total
        self.unidad_peso = unidad_peso
        self.num_total_mercancias = num_total_mercancias
        self.mercancia = mercancia or []
        self.autotransporte = autotransporte


class _FakeTiposFigura:
    def __init__(self, *, tipo_figura, nombre_figura, rfc_figura=None,
                 num_licencia=None):
        self.tipo_figura = tipo_figura
        self.nombre_figura = nombre_figura
        self.rfc_figura = rfc_figura
        self.num_licencia = num_licencia


class _FakeCartaPorte:
    def __init__(self, *, id_ccp="", transp_internac="No",
                 ubicaciones=None, mercancias=None, figura_transporte=None):
        self.id_ccp = id_ccp
        self.transp_internac = transp_internac
        self.ubicaciones = ubicaciones or []
        self.mercancias = mercancias
        self.figura_transporte = figura_transporte or []


# ──────────────────────────────────────────────────────────────────────────────
# Inject stubs into sys.modules BEFORE importing the module under test
# ──────────────────────────────────────────────────────────────────────────────

def _install_stubs():
    """Register lightweight stubs for frappe and satcfdi."""
    # Skip stubs if running inside Frappe bench (real modules available)
    if "frappe" in sys.modules and hasattr(sys.modules["frappe"], "get_doc"):
        return

    # -- frappe stub ----------------------------------------------------------
    frappe_stub = types.ModuleType("frappe")
    frappe_stub._ = lambda s: s
    frappe_stub.throw = MagicMock(side_effect=Exception)
    frappe_stub.get_cached_doc = MagicMock()
    frappe_stub.get_single = MagicMock()
    frappe_stub.db = MagicMock()
    frappe_stub.log_error = MagicMock()
    # Handle both @frappe.whitelist and @frappe.whitelist() patterns
    frappe_stub.whitelist = lambda *args, **kwargs: (lambda fn: fn) if not args else args[0]

    utils_stub = types.ModuleType("frappe.utils")
    import datetime as _dt
    utils_stub.getdate = lambda s: _dt.date.fromisoformat(str(s)) if isinstance(s, str) else s
    frappe_stub.utils = utils_stub

    sys.modules.setdefault("frappe", frappe_stub)
    sys.modules.setdefault("frappe.utils", utils_stub)

    # -- satcfdi.create.cfd.cartaporte31 stub ---------------------------------
    cartaporte31_mod = types.ModuleType("satcfdi.create.cfd.cartaporte31")
    cartaporte31_mod.Domicilio = _FakeDomicilio
    cartaporte31_mod.Ubicacion = _FakeUbicacion
    cartaporte31_mod.Mercancia = _FakeMercancia
    cartaporte31_mod.Mercancias = _FakeMercancias
    cartaporte31_mod.CartaPorte = _FakeCartaPorte
    cartaporte31_mod.Autotransporte = _FakeAutotransporte
    cartaporte31_mod.Seguros = _FakeSeguros
    cartaporte31_mod.IdentificacionVehicular = _FakeIdentificacionVehicular
    cartaporte31_mod.TiposFigura = _FakeTiposFigura
    sys.modules.setdefault("satcfdi.create.cfd.cartaporte31", cartaporte31_mod)

    # -- satcfdi.create.cfd.cfdi40 stub ---------------------------------------
    cfdi40_mod = types.ModuleType("satcfdi.create.cfd.cfdi40")
    cfdi40_mod.Comprobante = MagicMock()
    cfdi40_mod.Emisor = MagicMock()
    cfdi40_mod.Receptor = MagicMock()
    cfdi40_mod.Concepto = MagicMock()
    sys.modules.setdefault("satcfdi.create.cfd.cfdi40", cfdi40_mod)

    cfd_mod = types.ModuleType("satcfdi.create.cfd")
    cfd_mod.cartaporte31 = cartaporte31_mod
    cfd_mod.cfdi40 = cfdi40_mod
    sys.modules.setdefault("satcfdi.create.cfd", cfd_mod)

    create_mod = types.ModuleType("satcfdi.create")
    create_mod.cfd = cfd_mod
    sys.modules.setdefault("satcfdi.create", create_mod)

    models_mod = types.ModuleType("satcfdi.models")
    models_mod.Signer = MagicMock()
    sys.modules.setdefault("satcfdi.models", models_mod)

    satcfdi_mod = types.ModuleType("satcfdi")
    satcfdi_mod.create = create_mod
    satcfdi_mod.models = models_mod
    sys.modules.setdefault("satcfdi", satcfdi_mod)


_install_stubs()


# ──────────────────────────────────────────────────────────────────────────────
# Duck-typing helper — works with both fake dataclasses and satcfdi ScalarMaps
# ──────────────────────────────────────────────────────────────────────────────

def _v(obj, sat_key):
    """Extract a value from either a ScalarMap (dict, SAT CamelCase keys)
    or a fake dataclass (snake_case attrs).
    """
    if isinstance(obj, dict):
        return obj.get(sat_key)
    import re
    snake = re.sub(r'(?<!^)(?=[A-Z])', '_', sat_key).lower()
    return getattr(obj, snake, getattr(obj, sat_key, None))


def _items(obj, sat_key):
    """Return the list stored at sat_key / snake_case attr."""
    val = _v(obj, sat_key)
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return list(val)
    return [val]


# Now safe to import the helpers under test
from erpnext_mexico.cfdi.carta_porte_builder import (  # noqa: E402
    _validate_company_fiscal_data,
    _validate_carta_porte_data,
    _build_mercancias,
    _build_autotransporte,
    _build_figura_transporte,
    _build_fecha_hora,
)


# ──────────────────────────────────────────────────────────────────────────────
# Test data factories
# ──────────────────────────────────────────────────────────────────────────────

def _make_company(rfc="EKU9003173C9", nombre_fiscal="Empresa SA de CV",
                  regimen_fiscal="601", lugar_expedicion="06600"):
    company = MagicMock()
    company.name = nombre_fiscal
    company.mx_rfc = rfc
    company.mx_nombre_fiscal = nombre_fiscal
    company.mx_regimen_fiscal = regimen_fiscal
    company.mx_lugar_expedicion = lugar_expedicion
    return company


def _make_full_delivery_note():
    """Create a Delivery Note mock with all required Carta Porte fields."""
    doc = MagicMock()
    doc.name = "DN-001"
    doc.company = "Empresa SA de CV"
    doc.customer = "CUST-001"
    doc.posting_date = date(2026, 3, 1)
    doc.posting_time = "08:00:00"
    doc.currency = "MXN"
    # Origen
    doc.mx_cp_origen = "06600"
    doc.mx_estado_origen = "CDMX"
    doc.mx_municipio_origen = "Cuauhtémoc"
    # Destino
    doc.mx_cp_destino = "64000"
    doc.mx_estado_destino = "NL"
    doc.mx_municipio_destino = "Monterrey"
    doc.mx_distancia_recorrida = Decimal("900")
    # Vehículo
    doc.mx_config_vehicular = "C2"
    doc.mx_peso_bruto_vehicular = Decimal("15")
    doc.mx_placa_vehiculo = "ABC1234"
    doc.mx_anio_modelo_vehiculo = 2022
    doc.mx_perm_sct = "TPAF01"
    doc.mx_num_permiso_sct = "SCT-0001"
    # Seguros
    doc.mx_aseguradora_resp_civil = "Aseguradora MX SA"
    doc.mx_poliza_resp_civil = "POL-001"
    # Conductor
    doc.mx_nombre_conductor = "José García"
    doc.mx_rfc_conductor = "GACJ800101XXX"
    doc.mx_num_licencia_conductor = "LIC-001"
    # Ítems
    item = MagicMock()
    item.description = "Producto A"
    item.item_name = "Producto A"
    item.item_code = "PA-001"
    item.qty = 10
    item.rate = 100
    item.amount = 1000
    item.mx_clave_prod_serv_cp = "24102300"
    item.mx_clave_unidad = "KGM"
    item.mx_peso_en_kg = 5
    item.weight_per_unit = 0
    doc.items = [item]
    return doc


# ──────────────────────────────────────────────────────────────────────────────
# Company validation tests
# ──────────────────────────────────────────────────────────────────────────────

class TestCartaPorteValidation(unittest.TestCase):
    """Tests for _validate_company_fiscal_data and _validate_carta_porte_data."""

    def test_validate_company_raises_on_missing_rfc(self):
        """Company without mx_rfc must raise."""
        company = _make_company(rfc=None)
        company.mx_rfc = None
        with self.assertRaises(Exception):
            _validate_company_fiscal_data(company)

    def test_validate_company_raises_on_empty_rfc(self):
        """Company with empty mx_rfc must raise."""
        company = _make_company(rfc="")
        with self.assertRaises(Exception):
            _validate_company_fiscal_data(company)

    def test_validate_company_raises_on_missing_nombre_fiscal(self):
        """Company without mx_nombre_fiscal must raise."""
        company = _make_company(nombre_fiscal=None)
        company.mx_nombre_fiscal = None
        with self.assertRaises(Exception):
            _validate_company_fiscal_data(company)

    def test_validate_company_raises_on_missing_lugar_expedicion(self):
        """Company without mx_lugar_expedicion must raise."""
        company = _make_company(lugar_expedicion=None)
        company.mx_lugar_expedicion = None
        with self.assertRaises(Exception):
            _validate_company_fiscal_data(company)

    def test_validate_company_passes_with_all_data(self):
        """Company with all required fields must not raise."""
        company = _make_company()
        _validate_company_fiscal_data(company)  # must not raise

    def test_validate_delivery_note_raises_on_missing_cp_origen(self):
        """Delivery Note without mx_cp_origen must raise."""
        doc = _make_full_delivery_note()
        doc.mx_cp_origen = None
        with self.assertRaises(Exception):
            _validate_carta_porte_data(doc)

    def test_validate_delivery_note_raises_on_missing_cp_destino(self):
        """Delivery Note without mx_cp_destino must raise."""
        doc = _make_full_delivery_note()
        doc.mx_cp_destino = None
        with self.assertRaises(Exception):
            _validate_carta_porte_data(doc)

    def test_validate_delivery_note_raises_on_missing_distancia(self):
        """Delivery Note without mx_distancia_recorrida must raise."""
        doc = _make_full_delivery_note()
        doc.mx_distancia_recorrida = None
        with self.assertRaises(Exception):
            _validate_carta_porte_data(doc)

    def test_validate_delivery_note_raises_on_missing_placa(self):
        """Delivery Note without mx_placa_vehiculo must raise."""
        doc = _make_full_delivery_note()
        doc.mx_placa_vehiculo = None
        with self.assertRaises(Exception):
            _validate_carta_porte_data(doc)

    def test_validate_delivery_note_raises_on_empty_items(self):
        """Delivery Note with no items must raise."""
        doc = _make_full_delivery_note()
        doc.items = []
        with self.assertRaises(Exception):
            _validate_carta_porte_data(doc)

    def test_validate_delivery_note_passes_with_all_data(self):
        """Delivery Note with all required fields and items must not raise."""
        doc = _make_full_delivery_note()
        _validate_carta_porte_data(doc)  # must not raise


# ──────────────────────────────────────────────────────────────────────────────
# Mercancias builder tests
# ──────────────────────────────────────────────────────────────────────────────

class TestCartaPorteHelpers(unittest.TestCase):
    """Tests for _build_mercancias and related Carta Porte helpers."""

    def _make_item(self, *, desc="Producto", qty=5, rate=100, amount=500,
                   clave_cp="24102300", clave_unidad="KGM", peso=2.0):
        item = MagicMock()
        item.description = desc
        item.item_name = desc
        item.item_code = "ITEM-001"
        item.qty = qty
        item.rate = rate
        item.amount = amount
        item.mx_clave_prod_serv_cp = clave_cp
        item.mx_clave_prod_serv = clave_cp
        item.mx_clave_unidad = clave_unidad
        item.mx_peso_en_kg = peso
        item.weight_per_unit = 0
        return item

    def _make_doc_with_items(self, items=None):
        doc = _make_full_delivery_note()
        if items is not None:
            doc.items = items
        return doc

    def test_build_mercancias_single_item_creates_one_mercancia(self):
        """One item in the Delivery Note must produce exactly one Mercancia node."""
        doc = self._make_doc_with_items([self._make_item()])
        mercancias = _build_mercancias(doc)
        self.assertEqual(len(_items(mercancias, "Mercancia")), 1)

    def test_build_mercancias_multiple_items(self):
        """Three items must produce three Mercancia nodes."""
        items = [
            self._make_item(desc="A", qty=2, peso=1),
            self._make_item(desc="B", qty=3, peso=2),
            self._make_item(desc="C", qty=1, peso=5),
        ]
        doc = self._make_doc_with_items(items)
        mercancias = _build_mercancias(doc)
        self.assertEqual(len(_items(mercancias, "Mercancia")), 3)

    def test_build_mercancias_peso_bruto_total_sums_all_items(self):
        """peso_bruto_total must be the sum of mx_peso_en_kg across all items.

        mx_peso_en_kg is the total weight for the item (not per-unit), so
        peso_bruto_total = sum(mx_peso_en_kg) across items.
        """
        items = [
            self._make_item(qty=2, peso=6),    # total 6 kg
            self._make_item(qty=5, peso=10),   # total 10 kg
        ]
        doc = self._make_doc_with_items(items)
        mercancias = _build_mercancias(doc)
        self.assertEqual(_v(mercancias, "PesoBrutoTotal"), Decimal("16"))

    def test_build_mercancias_num_total_mercancias_matches_item_count(self):
        """num_total_mercancias must equal the number of items."""
        items = [self._make_item() for _ in range(4)]
        doc = self._make_doc_with_items(items)
        mercancias = _build_mercancias(doc)
        self.assertEqual(_v(mercancias, "NumTotalMercancias"), 4)

    def test_build_mercancias_bienes_transp_from_clave_prod_serv_cp(self):
        """Mercancia bienes_transp must use mx_clave_prod_serv_cp when available."""
        item = self._make_item(clave_cp="24102300")
        doc = self._make_doc_with_items([item])
        mercancias = _build_mercancias(doc)
        merc_list = _items(mercancias, "Mercancia")
        self.assertEqual(_v(merc_list[0], "BienesTransp"), "24102300")

    def test_build_mercancias_valor_set_when_rate_positive(self):
        """When item.rate > 0, valor_mercancia must be set to item.amount."""
        item = self._make_item(rate=200, amount=1000)
        doc = self._make_doc_with_items([item])
        mercancias = _build_mercancias(doc)
        merc_list = _items(mercancias, "Mercancia")
        self.assertIsNotNone(_v(merc_list[0], "ValorMercancia"))
        self.assertEqual(_v(merc_list[0], "ValorMercancia"), Decimal("1000"))

    def test_build_mercancias_unidad_peso_is_kgm(self):
        """unidad_peso must always be 'KGM' (SAT standard for kilograms)."""
        doc = self._make_doc_with_items([self._make_item()])
        mercancias = _build_mercancias(doc)
        self.assertEqual(_v(mercancias, "UnidadPeso"), "KGM")


# ──────────────────────────────────────────────────────────────────────────────
# Autotransporte builder tests
# ──────────────────────────────────────────────────────────────────────────────

class TestBuildAutotransporte(unittest.TestCase):
    """Tests for _build_autotransporte."""

    def test_autotransporte_perm_sct_set(self):
        """Autotransporte must carry mx_perm_sct from the doc."""
        doc = _make_full_delivery_note()
        autotransporte = _build_autotransporte(doc)
        self.assertEqual(_v(autotransporte, "PermSCT"), "TPAF01")

    def test_autotransporte_num_permiso_set(self):
        """Autotransporte must carry mx_num_permiso_sct from the doc."""
        doc = _make_full_delivery_note()
        autotransporte = _build_autotransporte(doc)
        self.assertEqual(_v(autotransporte, "NumPermisoSCT"), "SCT-0001")

    def test_autotransporte_seguros_aseguradora_set(self):
        """Seguros must carry aseguradora from mx_aseguradora_resp_civil."""
        doc = _make_full_delivery_note()
        autotransporte = _build_autotransporte(doc)
        seguros = _v(autotransporte, "Seguros")
        self.assertEqual(_v(seguros, "AseguraRespCivil"), "Aseguradora MX SA")

    def test_autotransporte_seguros_poliza_set(self):
        """Seguros must carry poliza from mx_poliza_resp_civil."""
        doc = _make_full_delivery_note()
        autotransporte = _build_autotransporte(doc)
        seguros = _v(autotransporte, "Seguros")
        self.assertEqual(_v(seguros, "PolizaRespCivil"), "POL-001")

    def test_autotransporte_placa_vehiculo_set(self):
        """IdentificacionVehicular must carry placa from mx_placa_vehiculo."""
        doc = _make_full_delivery_note()
        autotransporte = _build_autotransporte(doc)
        id_veh = _v(autotransporte, "IdentificacionVehicular")
        self.assertEqual(_v(id_veh, "PlacaVM"), "ABC1234")

    def test_autotransporte_anio_modelo_is_int(self):
        """IdentificacionVehicular anio_modelo_vm must be an integer."""
        doc = _make_full_delivery_note()
        autotransporte = _build_autotransporte(doc)
        id_veh = _v(autotransporte, "IdentificacionVehicular")
        anio = _v(id_veh, "AnioModeloVM")
        self.assertIsInstance(anio, int)
        self.assertEqual(anio, 2022)


# ──────────────────────────────────────────────────────────────────────────────
# Figura de transporte tests
# ──────────────────────────────────────────────────────────────────────────────

class TestBuildFiguraTransporte(unittest.TestCase):
    """Tests for _build_figura_transporte."""

    def test_figura_has_tipo_figura_01_for_operator(self):
        """TiposFigura tipo_figura must be '01' (Operador) for default case."""
        doc = _make_full_delivery_note()
        figuras = _build_figura_transporte(doc)
        self.assertEqual(len(figuras), 1)
        self.assertEqual(_v(figuras[0], "TipoFigura"), "01")

    def test_figura_nombre_from_mx_nombre_conductor(self):
        """TiposFigura nombre_figura must come from mx_nombre_conductor."""
        doc = _make_full_delivery_note()
        figuras = _build_figura_transporte(doc)
        self.assertEqual(_v(figuras[0], "NombreFigura"), "José García")


# ──────────────────────────────────────────────────────────────────────────────
# _build_fecha_hora tests
# ──────────────────────────────────────────────────────────────────────────────

class TestBuildFechaHora(unittest.TestCase):
    """Tests for _build_fecha_hora helper."""

    def test_date_and_string_time_produces_datetime(self):
        """date + HH:MM:SS string must produce a datetime with correct values."""
        result = _build_fecha_hora(date(2026, 3, 1), "08:30:00")
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 3)
        self.assertEqual(result.day, 1)
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 30)

    def test_none_posting_time_defaults_to_midnight(self):
        """When posting_time is None, datetime must default to midnight (00:00:00)."""
        result = _build_fecha_hora(date(2026, 3, 1), None)
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.hour, 0)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.second, 0)

    def test_datetime_input_is_returned_unchanged(self):
        """When posting_date is already a datetime, it must be returned as-is."""
        dt = datetime(2026, 3, 1, 14, 30, 0)
        result = _build_fecha_hora(dt, "08:00:00")
        self.assertEqual(result, dt)

    def test_timedelta_posting_time_parsed_correctly(self):
        """timedelta (ERPNext internal format) must be parsed correctly to hours/minutes."""
        td = timedelta(hours=10, minutes=15, seconds=30)
        result = _build_fecha_hora(date(2026, 3, 1), td)
        self.assertEqual(result.hour, 10)
        self.assertEqual(result.minute, 15)
        self.assertEqual(result.second, 30)

    def test_string_posting_date_is_parsed(self):
        """String posting_date ('YYYY-MM-DD') must be parsed to a valid datetime."""
        result = _build_fecha_hora("2026-03-01", "09:00:00")
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2026)


if __name__ == "__main__":
    unittest.main()
