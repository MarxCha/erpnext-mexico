"""
Generador de CFDI Nómina 1.2 Rev E usando satcfdi.
Transforma Salary Slip de ERPNext a CFDI tipo N con complemento nomina12.

Notas de implementación:
- tipo_de_comprobante="N" para nómina
- moneda siempre "MXN" para nómina nacional
- exportacion siempre "01" (no aplica)
- uso_cfdi del receptor siempre "CN01" (Nómina)
- SubTotal = total_percepciones (satcfdi calcula automáticamente)
- Total = percepciones - deducciones + otros_pagos (satcfdi calcula)
- Percepciones y Deducciones: los totales son calculados por satcfdi
"""

from datetime import date, datetime
from decimal import Decimal

import frappe
from frappe import _

from satcfdi.create.cfd import cfdi40
from satcfdi.create.cfd import nomina12
from satcfdi.models import Signer


# ── Tipos de percepción SAT (catálogo c_TipoPercepcion) ──
TIPO_PERCEPCION_SUELDOS = "001"
TIPO_PERCEPCION_GRATIFICACION = "002"
TIPO_PERCEPCION_HORAS_EXTRA = "019"
TIPO_PERCEPCION_PRIMA_VACACIONAL = "005"
TIPO_PERCEPCION_OTRAS = "047"  # Otros ingresos por salarios

# Tipos de deducción SAT (catálogo c_TipoDeduccion)
TIPO_DEDUCCION_SEGURIDAD_SOCIAL = "001"  # IMSS empleado
TIPO_DEDUCCION_ISR = "002"
TIPO_DEDUCCION_INFONAVIT = "003"
TIPO_DEDUCCION_OTRAS = "007"  # Otras deducciones

# Otro pago SAT
TIPO_OTRO_PAGO_SUBSIDIO = "002"  # Subsidio al empleo


def build_nomina_cfdi(salary_slip) -> cfdi40.Comprobante:
    """
    Construye CFDI tipo N (Nómina 1.2 Rev E) desde un Salary Slip de ERPNext.

    Args:
        salary_slip: Documento Salary Slip de ERPNext ya cargado.

    Returns:
        cfdi40.Comprobante listo para firmar y timbrar.
    """
    company = frappe.get_cached_doc("Company", salary_slip.company)
    employee = frappe.get_cached_doc("Employee", salary_slip.employee)

    _validate_company_fiscal_data(company)
    _validate_employee_fiscal_data(employee, salary_slip.employee)

    # Emisor CFDI (empresa)
    cfdi_emisor = cfdi40.Emisor(
        rfc=company.mx_rfc,
        nombre=company.mx_nombre_fiscal,
        regimen_fiscal=company.mx_regimen_fiscal,
    )

    # Receptor CFDI (empleado)
    employee_rfc = getattr(employee, "mx_rfc", None) or "XAXX010101000"
    cfdi_receptor = cfdi40.Receptor(
        rfc=employee_rfc,
        nombre=employee.employee_name,
        domicilio_fiscal_receptor=company.mx_lugar_expedicion,  # CP de expedición
        regimen_fiscal_receptor="605",  # Sueldos y Salarios e ingresos asimilados
        uso_cfdi="CN01",  # Nómina
    )

    # Complemento Nómina 1.2
    nomina_complemento = _build_nomina_complemento(salary_slip, employee, company)

    # Para tipo N: sub_total y total son calculados automáticamente por satcfdi
    # No se pasan conceptos — el complemento nómina los reemplaza
    # Se requiere un concepto genérico tipo N según SAT
    concepto_nomina = cfdi40.Concepto(
        clave_prod_serv="84111505",   # Servicios de nómina
        cantidad=Decimal("1"),
        clave_unidad="ACT",
        descripcion="Pago de nómina",
        valor_unitario=Decimal(str(salary_slip.gross_pay or 0)),
        objeto_imp="01",  # No objeto de impuesto (nómina no lleva IVA)
    )

    comprobante = cfdi40.Comprobante(
        emisor=cfdi_emisor,
        lugar_expedicion=company.mx_lugar_expedicion,
        receptor=cfdi_receptor,
        conceptos=[concepto_nomina],
        tipo_de_comprobante="N",
        moneda="MXN",
        exportacion="01",
        complemento=nomina_complemento,
        serie=_get_serie(salary_slip),
        folio=salary_slip.name[:40] if salary_slip.name else None,
    )

    return comprobante


def sign_nomina_cfdi(comprobante: cfdi40.Comprobante, company: str) -> cfdi40.Comprobante:
    """
    Firma el CFDI de nómina con el CSD activo de la empresa.

    Args:
        comprobante: Objeto CFDI tipo N ya construido.
        company: Nombre de la empresa en ERPNext.

    Returns:
        CFDI firmado con Sello, NoCertificado, Certificado.
    """
    from erpnext_mexico.cfdi.xml_builder import _get_active_certificate, _get_file_bytes

    certificate = _get_active_certificate(company)
    signer = Signer.load(
        certificate=_get_file_bytes(certificate.certificate_file),
        key=_get_file_bytes(certificate.key_file),
        password=certificate.get_password("key_password"),
    )
    comprobante.sign(signer)
    return comprobante


# ── Helpers privados ──────────────────────────────────────────────────────────

def _build_nomina_complemento(salary_slip, employee, company) -> nomina12.Nomina:
    """
    Construye el complemento nomina12.Nomina con todos sus nodos.

    Mapeo ERPNext → SAT Nómina 1.2:
    - salary_slip.start_date      → fecha_inicial_pago
    - salary_slip.end_date        → fecha_final_pago
    - salary_slip.posting_date    → fecha_pago
    - salary_slip.total_working_days → num_dias_pagados
    - salary_slip.earnings        → percepciones
    - salary_slip.deductions      → deducciones
    """
    fecha_pago = _to_date(salary_slip.posting_date)
    fecha_inicial = _to_date(salary_slip.start_date)
    fecha_final = _to_date(salary_slip.end_date)
    num_dias = Decimal(str(salary_slip.total_working_days or 1))

    # Nodo Emisor nómina (datos IMSS del patrón)
    nomina_emisor = _build_nomina_emisor(company)

    # Nodo Receptor nómina (datos laborales del empleado)
    nomina_receptor = _build_nomina_receptor(salary_slip, employee)

    # Percepciones
    percepciones = _build_percepciones(salary_slip)

    # Deducciones (solo si hay)
    deducciones = _build_deducciones(salary_slip)

    # Otros pagos (subsidio al empleo)
    otros_pagos = _build_otros_pagos(salary_slip)

    return nomina12.Nomina(
        tipo_nomina=_get_tipo_nomina(salary_slip),
        fecha_pago=fecha_pago,
        fecha_inicial_pago=fecha_inicial,
        fecha_final_pago=fecha_final,
        num_dias_pagados=num_dias,
        emisor=nomina_emisor,
        receptor=nomina_receptor,
        percepciones=percepciones,
        deducciones=deducciones if deducciones else None,
        otros_pagos=otros_pagos if otros_pagos else None,
    )


def _build_nomina_emisor(company) -> nomina12.Emisor:
    """
    Construye el nodo Emisor del complemento nómina.
    Solo lleva registro_patronal (IMSS) — no el RFC, que ya va en el CFDI Emisor.
    """
    registro_patronal = getattr(company, "mx_registro_patronal", None)
    curp_patron = getattr(company, "mx_curp", None)  # Solo para personas físicas

    return nomina12.Emisor(
        registro_patronal=registro_patronal or None,
        curp=curp_patron or None,
    )


def _build_nomina_receptor(salary_slip, employee) -> nomina12.Receptor:
    """
    Construye el nodo Receptor del complemento nómina con datos laborales del empleado.
    """
    curp = getattr(employee, "mx_curp", None)
    nss = getattr(employee, "mx_nss", None)
    sbc = getattr(employee, "mx_sbc", None)
    sdi = getattr(employee, "mx_sdi", None)

    # Tipo de contrato — leer del campo mx_tipo_contrato o default "01" (indefinido)
    tipo_contrato = getattr(employee, "mx_tipo_contrato", None) or "01"

    # Tipo de régimen fiscal para salarios — default "02" (Sueldos)
    tipo_regimen = getattr(employee, "mx_tipo_regimen_nomina", None) or "02"

    # Periodicidad de pago — inferir desde salary_slip o campo del empleado
    periodicidad = _get_periodicidad_pago(salary_slip, employee)

    # Número de empleado
    num_empleado = employee.name

    # Antigüedad en formato PnYnM (ISO 8601 duration)
    antiguedad = _calc_antiguedad(employee)

    # Estado donde trabaja el empleado
    clave_ent_fed = getattr(employee, "mx_clave_ent_fed", None)

    return nomina12.Receptor(
        curp=curp,
        tipo_contrato=tipo_contrato,
        tipo_regimen=tipo_regimen,
        num_empleado=num_empleado,
        periodicidad_pago=periodicidad,
        num_seguridad_social=nss or None,
        fecha_inicio_rel_laboral=_to_date(employee.date_of_joining) if employee.date_of_joining else None,
        antiguedad=antiguedad or None,
        tipo_jornada=getattr(employee, "mx_tipo_jornada", None) or None,
        departamento=employee.department or None,
        puesto=employee.designation or None,
        riesgo_puesto=getattr(employee, "mx_riesgo_puesto", None) or None,
        banco=getattr(employee, "mx_banco_sat", None) or None,
        cuenta_bancaria=getattr(employee, "mx_cuenta_clabe", None) or None,
        salario_base_cot_apor=Decimal(str(sbc)) if sbc else None,
        salario_diario_integrado=Decimal(str(sdi)) if sdi else None,
        clave_ent_fed=clave_ent_fed or None,
    )


def _build_percepciones(salary_slip) -> nomina12.Percepciones:
    """
    Construye las Percepciones del complemento nómina desde las earnings del Salary Slip.

    Mapeo de Salary Component a tipo SAT:
    - Prioridad 1: campo mx_tipo_percepcion_sat del Salary Component
    - Default: "001" (Sueldos y Salarios)

    Split gravado/exento:
    - Simplificado: todo gravado (importe_exento=0)
    - Si el componente tiene mx_importe_exento_pct, aplica el porcentaje exento
    """
    percepciones_list = []

    for row in (salary_slip.earnings or []):
        if not row.amount or row.amount <= 0:
            continue

        # Obtener tipo de percepción SAT desde el Salary Component
        tipo_percepcion = _get_tipo_percepcion(row)

        # Clave interna del concepto (usar abbreviation del componente o 'P01')
        clave = _get_component_clave(row.salary_component, "P")

        # Nombre del concepto
        concepto = row.salary_component_abbr or row.salary_component

        # Split gravado/exento
        importe_gravado, importe_exento = _split_gravado_exento(row)

        percepciones_list.append(
            nomina12.Percepcion(
                tipo_percepcion=tipo_percepcion,
                clave=clave,
                concepto=concepto[:100],  # SAT limita a 100 chars
                importe_gravado=importe_gravado,
                importe_exento=importe_exento,
            )
        )

    if not percepciones_list:
        frappe.throw(
            _("El Salary Slip no tiene conceptos de pago (earnings). "
              "No se puede generar CFDI nómina sin percepciones."),
            title=_("Sin percepciones"),
        )

    # satcfdi calcula automáticamente TotalSueldos, TotalSeparacionIndemnizacion,
    # TotalJubilacionPensionRetiro, TotalGravado, TotalExento desde la lista
    return nomina12.Percepciones(percepcion=percepciones_list)


def _build_deducciones(salary_slip) -> nomina12.Deducciones | None:
    """
    Construye las Deducciones del complemento nómina desde las deductions del Salary Slip.

    Mapeo de Salary Component a tipo SAT:
    - Prioridad 1: campo mx_tipo_deduccion_sat del Salary Component
    - Default: "007" (Otras deducciones)

    Tipos especiales auto-detectados:
    - ISR / RETENCION ISR → "002"
    - IMSS / SEGURIDAD SOCIAL → "001"
    - INFONAVIT → "003"
    """
    deducciones_list = []

    for row in (salary_slip.deductions or []):
        if not row.amount or row.amount <= 0:
            continue

        tipo_deduccion = _get_tipo_deduccion(row)
        clave = _get_component_clave(row.salary_component, "D")
        concepto = row.salary_component_abbr or row.salary_component

        deducciones_list.append(
            nomina12.Deduccion(
                tipo_deduccion=tipo_deduccion,
                clave=clave,
                concepto=concepto[:100],
                importe=Decimal(str(row.amount)).quantize(Decimal("0.01")),
            )
        )

    if not deducciones_list:
        return None

    # satcfdi calcula TotalOtrasDeducciones y TotalImpuestosRetenidos automáticamente
    return nomina12.Deducciones(deduccion=deducciones_list)


def _build_otros_pagos(salary_slip) -> list[nomina12.OtroPago] | None:
    """
    Construye OtrosPagos si existe subsidio al empleo o conceptos adicionales.

    El subsidio al empleo (tipo 002) se detecta buscando earnings con
    mx_tipo_percepcion_sat='subsidio' o el campo mx_subsidio_al_empleo en el slip.
    """
    otros_pagos = []

    # Verificar si el slip tiene subsidio al empleo
    subsidio_importe = getattr(salary_slip, "mx_subsidio_al_empleo", None)
    if subsidio_importe and Decimal(str(subsidio_importe)) > 0:
        importe = Decimal(str(subsidio_importe)).quantize(Decimal("0.01"))
        otros_pagos.append(
            nomina12.OtroPago(
                tipo_otro_pago=TIPO_OTRO_PAGO_SUBSIDIO,
                clave="SUB01",
                concepto="Subsidio al empleo",
                importe=importe,
                subsidio_al_empleo=importe,
            )
        )

    # Buscar en earnings con tipo especial subsidio
    for row in (salary_slip.earnings or []):
        if not row.amount or row.amount <= 0:
            continue
        comp_data = _get_salary_component_data(row.salary_component)
        if comp_data and comp_data.get("mx_tipo_percepcion_sat") == "subsidio":
            importe = Decimal(str(row.amount)).quantize(Decimal("0.01"))
            # Evitar duplicar si ya se cargó por mx_subsidio_al_empleo
            if not any(op.importe == importe for op in otros_pagos):
                otros_pagos.append(
                    nomina12.OtroPago(
                        tipo_otro_pago=TIPO_OTRO_PAGO_SUBSIDIO,
                        clave="SUB01",
                        concepto="Subsidio al empleo",
                        importe=importe,
                        subsidio_al_empleo=importe,
                    )
                )

    return otros_pagos if otros_pagos else None


# ── Helpers de mapeo ──────────────────────────────────────────────────────────

def _get_tipo_percepcion(row) -> str:
    """
    Determina el tipo de percepción SAT para una earning row.

    Prioridad:
    1. Campo mx_tipo_percepcion_sat en Salary Component
    2. Detección por nombre del componente
    3. Default: "001" (Sueldos y Salarios)
    """
    comp_data = _get_salary_component_data(row.salary_component)
    if comp_data:
        sat_type = comp_data.get("mx_tipo_percepcion_sat")
        if sat_type and sat_type not in ("subsidio", "", None):
            return sat_type

    # Detección por nombre
    nombre = (row.salary_component or "").upper()
    if any(k in nombre for k in ("HORA EXTRA", "HORAS EXTRA", "SOBRETIEMPO")):
        return "019"
    if any(k in nombre for k in ("PRIMA VACACIONAL", "VACACIONES")):
        return "005"
    if any(k in nombre for k in ("GRATIFICACION", "BONO", "AGUINALDO")):
        return "002"
    if any(k in nombre for k in ("COMISION",)):
        return "010"
    if any(k in nombre for k in ("FONDO AHORRO", "FONDO DE AHORRO")):
        return "006"

    return TIPO_PERCEPCION_SUELDOS  # "001" — Sueldos y Salarios


def _get_tipo_deduccion(row) -> str:
    """
    Determina el tipo de deducción SAT para una deduction row.

    Prioridad:
    1. Campo mx_tipo_deduccion_sat en Salary Component
    2. Detección por nombre del componente
    3. Default: "007" (Otras deducciones)
    """
    comp_data = _get_salary_component_data(row.salary_component)
    if comp_data:
        sat_type = comp_data.get("mx_tipo_deduccion_sat")
        if sat_type and sat_type not in ("", None):
            return sat_type

    # Detección automática por nombre
    nombre = (row.salary_component or "").upper()
    if any(k in nombre for k in ("ISR", "RETENCION ISR", "IMPUESTO")):
        return TIPO_DEDUCCION_ISR  # "002"
    if any(k in nombre for k in ("IMSS", "SEGURIDAD SOCIAL", "CUOTA")):
        return TIPO_DEDUCCION_SEGURIDAD_SOCIAL  # "001"
    if any(k in nombre for k in ("INFONAVIT",)):
        return TIPO_DEDUCCION_INFONAVIT  # "003"
    if any(k in nombre for k in ("CREDITO INFONAVIT", "DESCUENTO INFONAVIT")):
        return TIPO_DEDUCCION_INFONAVIT

    return TIPO_DEDUCCION_OTRAS  # "007"


def _get_salary_component_data(component_name: str) -> dict | None:
    """
    Obtiene datos del Salary Component con campos SAT mx_.
    Usa caché de frappe para optimizar N queries en percepciones/deducciones.
    """
    if not component_name:
        return None
    try:
        return frappe.db.get_value(
            "Salary Component",
            component_name,
            ["mx_tipo_percepcion_sat", "mx_tipo_deduccion_sat"],
            as_dict=True,
        )
    except Exception:
        return None


def _split_gravado_exento(row) -> tuple[Decimal, Decimal]:
    """
    Divide el importe de una percepción en gravado y exento.

    Si el Salary Component tiene mx_pct_exento (porcentaje exento 0-100),
    aplica la división. De lo contrario todo es gravado.
    """
    total = Decimal(str(row.amount)).quantize(Decimal("0.01"))

    comp_data = _get_salary_component_data(row.salary_component)
    pct_exento = 0
    if comp_data:
        pct_exento = float(comp_data.get("mx_pct_exento", 0) or 0)

    if pct_exento > 0:
        exento = (total * Decimal(str(pct_exento / 100))).quantize(Decimal("0.01"))
        gravado = total - exento
    else:
        gravado = total
        exento = Decimal("0.00")

    return gravado, exento


def _get_component_clave(component_name: str, prefix: str = "C") -> str:
    """
    Genera una clave de concepto para SAT desde el nombre del componente.
    SAT requiere clave alfanumérica de hasta 15 caracteres.
    Formato: prefix + primeras 14 letras/números del nombre.
    """
    if not component_name:
        return f"{prefix}001"
    # Remover espacios y caracteres especiales, truncar a 14 chars
    clean = "".join(c for c in component_name.upper() if c.isalnum())[:14]
    return clean or f"{prefix}001"


def _get_tipo_nomina(salary_slip) -> str:
    """
    Determina el tipo de nómina SAT.
    "O" = Ordinaria (quincena, semana, mes regular)
    "E" = Extraordinaria (finiquito, liquidación, aguinaldo)
    """
    tipo = getattr(salary_slip, "mx_tipo_nomina", None)
    if tipo in ("O", "E"):
        return tipo
    # Heurística: si es finiquito/liquidación o tiene componentes extraordinarios
    nombre_slip = (salary_slip.name or "").upper()
    if any(k in nombre_slip for k in ("FINIQUITO", "LIQUIDACION", "AGUINALDO")):
        return "E"
    return "O"  # Ordinaria por defecto


def _get_periodicidad_pago(salary_slip, employee) -> str:
    """
    Determina la periodicidad de pago SAT (catálogo c_PeriodicidadPago).

    Códigos SAT:
    01 = Diario, 02 = Semanal, 03 = Catorcenal, 04 = Quincenal,
    05 = Mensual, 06 = Bimestral, 07 = Unidad obra, 08 = Comisión,
    09 = Precio alzado, 10 = Decenal, 99 = Otra periodicidad

    Prioridad:
    1. Campo mx_periodicidad_pago del Employee
    2. Inferir desde payroll_frequency del Salary Slip
    """
    periodicidad = getattr(employee, "mx_periodicidad_pago", None)
    if periodicidad:
        return periodicidad

    # Inferir desde salary_slip.payroll_frequency
    freq = getattr(salary_slip, "payroll_frequency", None) or ""
    freq = freq.upper()

    # Check longer/more-specific keys first to avoid "WEEKLY" matching "BIWEEKLY"
    mapping = [
        ("BIWEEKLY", "03"),
        ("BIMONTHLY", "06"),
        ("FORTNIGHTLY", "04"),
        ("DAILY", "01"),
        ("WEEKLY", "02"),
        ("MONTHLY", "05"),
    ]
    for key, code in mapping:
        if key in freq:
            return code

    # Default quincenal (más común en México)
    return "04"


def _calc_antiguedad(employee) -> str | None:
    """
    Calcula la antigüedad del empleado en formato PnYnM (ISO 8601 duration).

    Ejemplo: P2Y3M = 2 años, 3 meses
    """
    if not employee.date_of_joining:
        return None
    try:
        joining = _to_date(employee.date_of_joining)
        today = date.today()
        years = today.year - joining.year
        months = today.month - joining.month
        if months < 0:
            years -= 1
            months += 12
        if years < 0:
            return "P0Y0M"
        return f"P{years}Y{months}M"
    except Exception:
        return None


def _get_serie(salary_slip) -> str | None:
    """Extrae la serie del Salary Slip para el CFDI."""
    naming = getattr(salary_slip, "naming_series", None)
    if naming:
        return naming.replace(".", "").replace("-", "")[:25]
    return "NOM"


def _to_date(value) -> date:
    """Convierte str 'YYYY-MM-DD' o datetime/date a date."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return frappe.utils.getdate(value)
    return date.today()


# ── Validaciones ──────────────────────────────────────────────────────────────

def _validate_company_fiscal_data(company) -> None:
    """Valida que la empresa tenga todos los datos fiscales requeridos para CFDI tipo N."""
    errors = []
    if not company.mx_rfc:
        errors.append(_("RFC de la empresa no configurado"))
    if not company.mx_nombre_fiscal:
        errors.append(_("Nombre fiscal de la empresa no configurado"))
    if not company.mx_regimen_fiscal:
        errors.append(_("Régimen fiscal de la empresa no configurado"))
    if not company.mx_lugar_expedicion:
        errors.append(_("Lugar de expedición (CP) no configurado"))
    if errors:
        frappe.throw("<br>".join(errors), title=_("Datos fiscales de empresa incompletos"))


def _validate_employee_fiscal_data(employee, employee_name: str) -> None:
    """Valida que el empleado tenga los datos fiscales mínimos para nómina."""
    errors = []
    curp = getattr(employee, "mx_curp", None)
    if not curp:
        errors.append(_("CURP del empleado {0} no configurado").format(employee_name))
    elif len(curp) != 18:
        errors.append(_("CURP del empleado {0} debe tener 18 caracteres").format(employee_name))
    if errors:
        frappe.throw("<br>".join(errors), title=_("Datos fiscales del empleado incompletos"))
