# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

"""Tests para nomina_builder.py — CFDI Nómina 1.2 Rev E.

Unit tests sin Frappe ni satcfdi reales.
Se stubbean en sys.modules antes de importar el módulo bajo prueba,
siguiendo el mismo patrón que test_xml_builder.py.
"""

import sys
import types
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock


# ──────────────────────────────────────────────────────────────────────────────
# Fakes para satcfdi.create.cfd.nomina12
# ──────────────────────────────────────────────────────────────────────────────

class _FakeEmisorNomina:
    def __init__(self, registro_patronal=None, curp=None):
        self.registro_patronal = registro_patronal
        self.curp = curp


class _FakeReceptorNomina:
    def __init__(self, *, curp, tipo_contrato, tipo_regimen, num_empleado,
                 periodicidad_pago, num_seguridad_social=None,
                 fecha_inicio_rel_laboral=None, antiguedad=None,
                 tipo_jornada=None, departamento=None, puesto=None,
                 riesgo_puesto=None, banco=None, cuenta_bancaria=None,
                 salario_base_cot_apor=None, salario_diario_integrado=None,
                 clave_ent_fed=None, sub_contratacion=None):
        self.curp = curp
        self.tipo_contrato = tipo_contrato
        self.tipo_regimen = tipo_regimen
        self.num_empleado = num_empleado
        self.periodicidad_pago = periodicidad_pago
        self.num_seguridad_social = num_seguridad_social
        self.antiguedad = antiguedad


class _FakePercepcion:
    def __init__(self, *, tipo_percepcion, clave, concepto,
                 importe_gravado, importe_exento):
        self.tipo_percepcion = tipo_percepcion
        self.clave = clave
        self.concepto = concepto
        self.importe_gravado = importe_gravado
        self.importe_exento = importe_exento


class _FakePercepciones:
    def __init__(self, percepcion):
        self.percepcion = percepcion


class _FakeDeduccion:
    def __init__(self, *, tipo_deduccion, clave, concepto, importe):
        self.tipo_deduccion = tipo_deduccion
        self.clave = clave
        self.concepto = concepto
        self.importe = importe


class _FakeDeducciones:
    def __init__(self, deduccion):
        self.deduccion = deduccion


class _FakeOtroPago:
    def __init__(self, *, tipo_otro_pago, clave, concepto, importe,
                 subsidio_al_empleo=None):
        self.tipo_otro_pago = tipo_otro_pago
        self.importe = importe
        self.subsidio_al_empleo = subsidio_al_empleo


class _FakeNomina:
    def __init__(self, *, tipo_nomina, fecha_pago, fecha_inicial_pago,
                 fecha_final_pago, num_dias_pagados, emisor=None,
                 receptor, percepciones, deducciones=None, otros_pagos=None):
        self.tipo_nomina = tipo_nomina
        self.fecha_pago = fecha_pago
        self.receptor = receptor
        self.percepciones = percepciones
        self.deducciones = deducciones
        self.otros_pagos = otros_pagos


class _FakeEmisorCFDI:
    def __init__(self, *, rfc, nombre, regimen_fiscal):
        self.rfc = rfc


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
                 tipo_de_comprobante, moneda, exportacion, complemento=None,
                 serie=None, folio=None):
        self.tipo_de_comprobante = tipo_de_comprobante
        self.moneda = moneda
        self.exportacion = exportacion
        self.complemento = complemento


# ──────────────────────────────────────────────────────────────────────────────
# Instalar stubs en sys.modules (module-level, antes de los imports)
# ──────────────────────────────────────────────────────────────────────────────

def _install_stubs():
    # Skip stubs if running inside Frappe bench (real modules available)
    if "frappe" in sys.modules and hasattr(sys.modules["frappe"], "get_doc"):
        return

    # frappe stub
    frappe_stub = MagicMock()
    frappe_stub._ = lambda s, *a: s
    frappe_stub.throw = MagicMock(side_effect=Exception("frappe.throw called"))
    frappe_stub.msgprint = MagicMock()
    frappe_stub.utils.getdate = lambda s: date.fromisoformat(str(s))
    frappe_stub.db.get_value = MagicMock(return_value=None)
    sys.modules.setdefault("frappe", frappe_stub)

    # satcfdi stubs
    nomina12_stub = types.ModuleType("satcfdi.create.cfd.nomina12")
    nomina12_stub.Nomina = _FakeNomina
    nomina12_stub.Emisor = _FakeEmisorNomina
    nomina12_stub.Receptor = _FakeReceptorNomina
    nomina12_stub.Percepcion = _FakePercepcion
    nomina12_stub.Percepciones = _FakePercepciones
    nomina12_stub.Deduccion = _FakeDeduccion
    nomina12_stub.Deducciones = _FakeDeducciones
    nomina12_stub.OtroPago = _FakeOtroPago

    cfdi40_stub = types.ModuleType("satcfdi.create.cfd.cfdi40")
    cfdi40_stub.Emisor = _FakeEmisorCFDI
    cfdi40_stub.Receptor = _FakeReceptorCFDI
    cfdi40_stub.Concepto = _FakeConceptoCFDI
    cfdi40_stub.Comprobante = _FakeComprobante

    cfd_stub = types.ModuleType("satcfdi.create.cfd")
    cfd_stub.cfdi40 = cfdi40_stub
    cfd_stub.nomina12 = nomina12_stub

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
        ("satcfdi.create.cfd.nomina12", nomina12_stub),
        ("satcfdi.models", models_stub),
    ]:
        sys.modules.setdefault(name, mod)


_install_stubs()


# ──────────────────────────────────────────────────────────────────────────────
# Duck-typing helper — works with both fake dataclasses and satcfdi ScalarMaps
# ──────────────────────────────────────────────────────────────────────────────

def _v(obj, sat_key):
    """Extract a value from either a ScalarMap (dict, SAT CamelCase keys)
    or a fake dataclass (snake_case attrs).  Supports simple dot access on
    nested objects via a single key only.
    """
    if isinstance(obj, dict):
        return obj.get(sat_key)
    import re
    snake = re.sub(r'(?<!^)(?=[A-Z])', '_', sat_key).lower()
    return getattr(obj, snake, getattr(obj, sat_key, None))


def _items(obj, sat_key):
    """Return the list stored at sat_key / snake_case attr; used for
    Percepciones.percepcion, Deducciones.deduccion, etc.
    """
    val = _v(obj, sat_key)
    if val is None:
        return []
    # satcfdi may return a list or a ScalarMap-wrapped list
    if isinstance(val, (list, tuple)):
        return list(val)
    return [val]


# Importar helpers a nivel de módulo (igual que test_xml_builder.py)
from erpnext_mexico.cfdi.nomina_builder import (  # noqa: E402
    _get_component_clave,
    _get_tipo_percepcion,
    _get_tipo_deduccion,
    _split_gravado_exento,
    _get_tipo_nomina,
    _get_periodicidad_pago,
    _calc_antiguedad,
    _to_date,
    _validate_employee_fiscal_data,
    _build_percepciones,
    _build_deducciones,
    _build_otros_pagos,
    _build_nomina_emisor,
)

from erpnext_mexico.payroll.overrides.salary_slip import (  # noqa: E402
    _is_mexico_company,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers para construir objetos fake
# ──────────────────────────────────────────────────────────────────────────────

def _make_earning(component, amount, abbr=None):
    row = MagicMock()
    row.salary_component = component
    row.salary_component_abbr = abbr or component[:3].upper()
    row.amount = amount
    return row


def _make_deduction(component, amount, abbr=None):
    row = MagicMock()
    row.salary_component = component
    row.salary_component_abbr = abbr or component[:3].upper()
    row.amount = amount
    return row


def _make_salary_slip(
    earnings=None, deductions=None, gross=10000.0,
    payroll_frequency="Monthly",
):
    slip = MagicMock()
    slip.name = "SAL-2026-0001"
    slip.employee = "EMP-001"
    slip.company = "Test Co"
    slip.start_date = "2026-01-01"
    slip.end_date = "2026-01-15"
    slip.posting_date = "2026-01-15"
    slip.total_working_days = 15
    slip.gross_pay = gross
    slip.earnings = earnings or []
    slip.deductions = deductions or []
    slip.naming_series = "SAL-.YYYY.-"
    slip.mx_tipo_nomina = "O"
    slip.mx_subsidio_al_empleo = None
    slip.payroll_frequency = payroll_frequency
    return slip


def _make_employee():
    emp = MagicMock()
    emp.name = "EMP-001"
    emp.employee_name = "Juan Pérez García"
    emp.mx_curp = "PEGJ900101HMCRRN01"
    emp.mx_nss = "12345678901"
    emp.mx_rfc = "PEGJ900101ABC"
    emp.mx_sbc = Decimal("500.00")
    emp.mx_sdi = Decimal("550.00")
    emp.mx_tipo_contrato = "01"
    emp.mx_tipo_regimen_nomina = "02"
    emp.mx_periodicidad_pago = "05"
    emp.mx_tipo_jornada = "01"
    emp.mx_riesgo_puesto = "1"
    emp.mx_clave_ent_fed = "MEX"
    emp.mx_banco_sat = "002"
    emp.mx_cuenta_clabe = "123456789012345678"
    emp.department = "Desarrollo"
    emp.designation = "Desarrollador"
    emp.date_of_joining = "2024-01-01"
    return emp


def _make_company():
    co = MagicMock()
    co.name = "Test Co"
    co.mx_rfc = "TST900101ABC"
    co.mx_nombre_fiscal = "Test Company SA de CV"
    co.mx_regimen_fiscal = "601"
    co.mx_lugar_expedicion = "52000"
    co.mx_registro_patronal = "A1234567890"
    co.mx_curp = None
    return co


# ──────────────────────────────────────────────────────────────────────────────
# Test Cases
# ──────────────────────────────────────────────────────────────────────────────

class TestGetComponentClave(unittest.TestCase):
    """Tests para _get_component_clave."""

    def test_normal_name_is_alphanumeric(self):
        clave = _get_component_clave("Sueldo Base", "P")
        self.assertTrue(clave.isalnum())
        self.assertLessEqual(len(clave), 15)

    def test_empty_string_returns_prefix_default(self):
        self.assertEqual(_get_component_clave("", "P"), "P001")

    def test_none_returns_prefix_default(self):
        self.assertEqual(_get_component_clave(None, "D"), "D001")

    def test_spaces_stripped(self):
        clave = _get_component_clave("ISR Retencion", "D")
        self.assertNotIn(" ", clave)

    def test_max_14_chars_content(self):
        clave = _get_component_clave("A" * 20, "P")
        self.assertLessEqual(len(clave), 14)


class TestGetTipoPercepcion(unittest.TestCase):
    """Tests para _get_tipo_percepcion."""

    def setUp(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value=None)

    def test_default_sueldos(self):
        row = _make_earning("Sueldo Quincenal", 5000)
        self.assertEqual(_get_tipo_percepcion(row), "001")

    def test_horas_extra(self):
        row = _make_earning("Horas Extra", 500)
        self.assertEqual(_get_tipo_percepcion(row), "019")

    def test_prima_vacacional(self):
        row = _make_earning("Prima Vacacional", 1000)
        self.assertEqual(_get_tipo_percepcion(row), "005")

    def test_gratificacion(self):
        row = _make_earning("Gratificacion Anual", 2000)
        self.assertEqual(_get_tipo_percepcion(row), "002")

    def test_comision(self):
        row = _make_earning("Comision de Ventas", 3000)
        self.assertEqual(_get_tipo_percepcion(row), "010")

    def test_sat_field_overrides_heuristic(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value={
            "mx_tipo_percepcion_sat": "030",
            "mx_tipo_deduccion_sat": None,
            "mx_pct_exento": 0,
        })
        row = _make_earning("Horas Extra", 500)
        # El campo SAT debe ganar sobre la heurística
        self.assertEqual(_get_tipo_percepcion(row), "030")


class TestGetTipoDeduccion(unittest.TestCase):
    """Tests para _get_tipo_deduccion."""

    def setUp(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value=None)

    def test_isr(self):
        self.assertEqual(_get_tipo_deduccion(_make_deduction("ISR", 800)), "002")

    def test_retencion_isr(self):
        self.assertEqual(_get_tipo_deduccion(_make_deduction("Retencion ISR", 800)), "002")

    def test_imss(self):
        self.assertEqual(_get_tipo_deduccion(_make_deduction("IMSS Empleado", 400)), "001")

    def test_seguridad_social(self):
        self.assertEqual(_get_tipo_deduccion(_make_deduction("Cuota Seguridad Social", 400)), "001")

    def test_infonavit(self):
        self.assertEqual(_get_tipo_deduccion(_make_deduction("INFONAVIT", 300)), "003")

    def test_otras(self):
        self.assertEqual(_get_tipo_deduccion(_make_deduction("Descuento Prestamo", 500)), "007")

    def test_sat_field_overrides(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value={
            "mx_tipo_percepcion_sat": None,
            "mx_tipo_deduccion_sat": "005",
        })
        row = _make_deduction("ISR", 800)
        self.assertEqual(_get_tipo_deduccion(row), "005")


class TestSplitGravadoExento(unittest.TestCase):
    """Tests para _split_gravado_exento."""

    def setUp(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value={
            "mx_tipo_percepcion_sat": "001",
            "mx_tipo_deduccion_sat": None,
            "mx_pct_exento": 0,
        })

    def test_all_gravado_by_default(self):
        row = _make_earning("Sueldo", 5000)
        gravado, exento = _split_gravado_exento(row)
        self.assertEqual(gravado, Decimal("5000.00"))
        self.assertEqual(exento, Decimal("0.00"))

    def test_50_pct_exento(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value={
            "mx_tipo_percepcion_sat": "005",
            "mx_tipo_deduccion_sat": None,
            "mx_pct_exento": 50,
        })
        row = _make_earning("Prima Vacacional", 1000)
        gravado, exento = _split_gravado_exento(row)
        self.assertEqual(gravado, Decimal("500.00"))
        self.assertEqual(exento, Decimal("500.00"))

    def test_sum_equals_total(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value={
            "mx_tipo_percepcion_sat": "005",
            "mx_tipo_deduccion_sat": None,
            "mx_pct_exento": 30,
        })
        row = _make_earning("Componente", 3333)
        gravado, exento = _split_gravado_exento(row)
        self.assertEqual(gravado + exento, Decimal("3333.00"))

    def test_100_pct_exento(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value={
            "mx_tipo_percepcion_sat": "019",
            "mx_tipo_deduccion_sat": None,
            "mx_pct_exento": 100,
        })
        row = _make_earning("Exento Total", 2000)
        gravado, exento = _split_gravado_exento(row)
        self.assertEqual(gravado, Decimal("0.00"))
        self.assertEqual(exento, Decimal("2000.00"))


class TestGetTipoNomina(unittest.TestCase):
    """Tests para _get_tipo_nomina."""

    def test_ordinaria_by_field(self):
        slip = _make_salary_slip()
        self.assertEqual(_get_tipo_nomina(slip), "O")

    def test_extraordinaria_by_field(self):
        slip = _make_salary_slip()
        slip.mx_tipo_nomina = "E"
        self.assertEqual(_get_tipo_nomina(slip), "E")

    def test_extraordinaria_by_name_finiquito(self):
        slip = _make_salary_slip()
        slip.mx_tipo_nomina = None
        slip.name = "FINIQUITO-2026-001"
        self.assertEqual(_get_tipo_nomina(slip), "E")

    def test_extraordinaria_by_name_aguinaldo(self):
        slip = _make_salary_slip()
        slip.mx_tipo_nomina = None
        slip.name = "AGUINALDO-2025"
        self.assertEqual(_get_tipo_nomina(slip), "E")

    def test_ordinaria_default_no_field(self):
        slip = _make_salary_slip()
        slip.mx_tipo_nomina = None
        slip.name = "SAL-2026-0001"
        self.assertEqual(_get_tipo_nomina(slip), "O")


class TestGetPeriodicidadPago(unittest.TestCase):
    """Tests para _get_periodicidad_pago."""

    def test_from_employee_field(self):
        slip = _make_salary_slip()
        emp = _make_employee()
        emp.mx_periodicidad_pago = "04"
        self.assertEqual(_get_periodicidad_pago(slip, emp), "04")

    def test_monthly_inference(self):
        slip = _make_salary_slip(payroll_frequency="Monthly")
        emp = _make_employee()
        emp.mx_periodicidad_pago = None
        self.assertEqual(_get_periodicidad_pago(slip, emp), "05")

    def test_weekly_inference(self):
        slip = _make_salary_slip(payroll_frequency="Weekly")
        emp = _make_employee()
        emp.mx_periodicidad_pago = None
        self.assertEqual(_get_periodicidad_pago(slip, emp), "02")

    def test_biweekly_inference(self):
        slip = _make_salary_slip(payroll_frequency="Fortnightly")
        emp = _make_employee()
        emp.mx_periodicidad_pago = None
        self.assertEqual(_get_periodicidad_pago(slip, emp), "04")

    def test_default_quincenal(self):
        slip = _make_salary_slip(payroll_frequency="Unknown")
        emp = _make_employee()
        emp.mx_periodicidad_pago = None
        self.assertEqual(_get_periodicidad_pago(slip, emp), "04")


class TestCalcAntiguedad(unittest.TestCase):
    """Tests para _calc_antiguedad."""

    def test_format_iso8601(self):
        emp = _make_employee()
        emp.date_of_joining = "2020-01-01"
        result = _calc_antiguedad(emp)
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("P"))
        self.assertIn("Y", result)
        self.assertIn("M", result)

    def test_none_when_no_joining(self):
        emp = _make_employee()
        emp.date_of_joining = None
        self.assertIsNone(_calc_antiguedad(emp))

    def test_years_computed(self):
        emp = _make_employee()
        emp.date_of_joining = "2020-03-18"  # Approx 6 years
        result = _calc_antiguedad(emp)
        self.assertIsNotNone(result)
        # Should contain some number of years (5 or 6 depending on today)
        self.assertTrue(
            "5Y" in result or "6Y" in result,
            f"Expected 5 or 6 years in '{result}'",
        )

    def test_new_employee_zero(self):
        emp = _make_employee()
        emp.date_of_joining = str(date.today())
        result = _calc_antiguedad(emp)
        self.assertIsNotNone(result)
        self.assertTrue(result.startswith("P"))


class TestToDate(unittest.TestCase):
    """Tests para _to_date."""

    def test_from_string(self):
        self.assertEqual(_to_date("2026-01-15"), date(2026, 1, 15))

    def test_from_date_object(self):
        d = date(2026, 3, 1)
        self.assertEqual(_to_date(d), d)

    def test_from_datetime(self):
        from datetime import datetime
        dt = datetime(2026, 6, 15, 12, 0, 0)
        self.assertEqual(_to_date(dt), date(2026, 6, 15))


class TestValidateEmployeeFiscalData(unittest.TestCase):
    """Tests para _validate_employee_fiscal_data."""

    def setUp(self):
        # Reset throw to raise Exception for invalid cases
        sys.modules["frappe"].throw = MagicMock(side_effect=Exception("validation error"))

    def test_valid_employee_no_throw(self):
        sys.modules["frappe"].throw = MagicMock()  # Should NOT raise
        emp = _make_employee()
        _validate_employee_fiscal_data(emp, "EMP-001")
        sys.modules["frappe"].throw.assert_not_called()

    def test_missing_curp_raises(self):
        emp = _make_employee()
        emp.mx_curp = None
        with self.assertRaises(Exception):
            _validate_employee_fiscal_data(emp, "EMP-001")

    def test_short_curp_raises(self):
        emp = _make_employee()
        emp.mx_curp = "TOOSHORT"
        with self.assertRaises(Exception):
            _validate_employee_fiscal_data(emp, "EMP-001")

    def test_valid_18char_curp(self):
        sys.modules["frappe"].throw = MagicMock()
        emp = _make_employee()
        emp.mx_curp = "ABCD123456HDFRRR01"  # exactly 18 chars
        _validate_employee_fiscal_data(emp, "EMP-001")
        sys.modules["frappe"].throw.assert_not_called()


class TestBuildPercepciones(unittest.TestCase):
    """Tests para _build_percepciones."""

    def setUp(self):
        sys.modules["frappe"].throw = MagicMock(side_effect=Exception("no earnings"))
        sys.modules["frappe"].db.get_value = MagicMock(return_value={
            "mx_tipo_percepcion_sat": "001",
            "mx_tipo_deduccion_sat": None,
            "mx_pct_exento": 0,
        })

    def test_empty_earnings_raises(self):
        slip = _make_salary_slip(earnings=[])
        with self.assertRaises(Exception):
            _build_percepciones(slip)

    def test_zero_amount_raises(self):
        slip = _make_salary_slip(earnings=[_make_earning("Sueldo", 0)])
        with self.assertRaises(Exception):
            _build_percepciones(slip)

    def test_single_earning_builds_percepcion(self):
        sys.modules["frappe"].throw = MagicMock()
        slip = _make_salary_slip(earnings=[_make_earning("Sueldo Base", 5000)])
        result = _build_percepciones(slip)
        self.assertIsNotNone(result)
        percs = _items(result, "Percepcion")
        self.assertEqual(len(percs), 1)
        self.assertEqual(_v(percs[0], "TipoPercepcion"), "001")
        self.assertEqual(_v(percs[0], "ImporteGravado"), Decimal("5000.00"))
        self.assertEqual(_v(percs[0], "ImporteExento"), Decimal("0.00"))

    def test_multiple_earnings(self):
        sys.modules["frappe"].throw = MagicMock()
        slip = _make_salary_slip(earnings=[
            _make_earning("Sueldo Base", 5000),
            _make_earning("Prima Vacacional", 1000),
        ])
        result = _build_percepciones(slip)
        self.assertEqual(len(_items(result, "Percepcion")), 2)

    def test_concepto_truncated_at_100(self):
        sys.modules["frappe"].throw = MagicMock()
        long_name = "A" * 120
        slip = _make_salary_slip(earnings=[_make_earning(long_name, 100)])
        result = _build_percepciones(slip)
        percs = _items(result, "Percepcion")
        self.assertLessEqual(len(_v(percs[0], "Concepto")), 100)


class TestBuildDeducciones(unittest.TestCase):
    """Tests para _build_deducciones."""

    def setUp(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value={
            "mx_tipo_percepcion_sat": None,
            "mx_tipo_deduccion_sat": None,
        })

    def test_empty_deductions_returns_none(self):
        slip = _make_salary_slip(deductions=[])
        self.assertIsNone(_build_deducciones(slip))

    def test_zero_amount_skipped(self):
        slip = _make_salary_slip(deductions=[_make_deduction("ISR", 0)])
        self.assertIsNone(_build_deducciones(slip))

    def test_isr_deduction(self):
        slip = _make_salary_slip(deductions=[_make_deduction("ISR", 800)])
        result = _build_deducciones(slip)
        self.assertIsNotNone(result)
        deds = _items(result, "Deduccion")
        self.assertEqual(_v(deds[0], "TipoDeduccion"), "002")
        self.assertEqual(_v(deds[0], "Importe"), Decimal("800.00"))

    def test_multiple_deductions(self):
        slip = _make_salary_slip(deductions=[
            _make_deduction("ISR", 800),
            _make_deduction("IMSS Empleado", 400),
            _make_deduction("INFONAVIT", 300),
        ])
        result = _build_deducciones(slip)
        self.assertEqual(len(_items(result, "Deduccion")), 3)


class TestBuildOtrosPagos(unittest.TestCase):
    """Tests para _build_otros_pagos."""

    def setUp(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value=None)

    def test_no_subsidio_returns_none(self):
        slip = _make_salary_slip()
        slip.mx_subsidio_al_empleo = None
        self.assertIsNone(_build_otros_pagos(slip))

    def test_zero_subsidio_returns_none(self):
        slip = _make_salary_slip()
        slip.mx_subsidio_al_empleo = 0
        self.assertIsNone(_build_otros_pagos(slip))

    def test_subsidio_creates_otro_pago(self):
        slip = _make_salary_slip()
        slip.mx_subsidio_al_empleo = 500.0
        result = _build_otros_pagos(slip)
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(_v(result[0], "TipoOtroPago"), "002")
        self.assertEqual(_v(result[0], "Importe"), Decimal("500.00"))
        subsidio = _v(result[0], "SubsidioAlEmpleo")
        subsidio_val = _v(subsidio, "SubsidioCausado") if isinstance(subsidio, dict) else (
            getattr(subsidio, "subsidio_causado", subsidio) if subsidio is not None else Decimal("500.00")
        )
        self.assertIsNotNone(_v(result[0], "SubsidioAlEmpleo"))


class TestBuildNominaEmisor(unittest.TestCase):
    """Tests para _build_nomina_emisor."""

    def test_con_registro_patronal(self):
        co = _make_company()
        result = _build_nomina_emisor(co)
        self.assertIsNotNone(result)
        self.assertEqual(_v(result, "RegistroPatronal"), "A1234567890")

    def test_sin_registro_patronal(self):
        co = _make_company()
        co.mx_registro_patronal = None
        result = _build_nomina_emisor(co)
        self.assertIsNone(_v(result, "RegistroPatronal"))

    def test_curp_none_for_moral(self):
        co = _make_company()
        result = _build_nomina_emisor(co)
        self.assertIsNone(_v(result, "Curp"))


class TestIsMexicoCompany(unittest.TestCase):
    """Tests para _is_mexico_company desde salary_slip.py."""

    def test_true_when_rfc_present(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value="TST900101ABC")
        self.assertTrue(_is_mexico_company("Test Co"))

    def test_false_when_rfc_none(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value=None)
        self.assertFalse(_is_mexico_company("Foreign Co"))

    def test_false_when_rfc_empty(self):
        sys.modules["frappe"].db.get_value = MagicMock(return_value="")
        self.assertFalse(_is_mexico_company("Empty Co"))


if __name__ == "__main__":
    unittest.main()
