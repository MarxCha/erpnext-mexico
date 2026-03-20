# STATUS — ERPNext México

## Estado: Sprint 2b — Verificación de Entorno (COMPLETADO)
**Fecha verificación**: 2026-03-19
**Verificado por**: Sprint 2b research pass (sin modificaciones al código)

---

## Contenedores Docker

| Contenedor | Estado | Puertos expuestos |
|---|---|---|
| erpnext-mx-frappe | UP (activo) | 8080→8000 (web), 9002→9000 (socketio), 6787→6787 (debugger) |
| erpnext-mx-mariadb | UP healthy | 3307→3306 |
| erpnext-mx-redis-cache | UP | (interno) |
| erpnext-mx-redis-queue | UP | (interno) |

Todos los contenedores estan corriendo. No es necesario iniciarlos.

**Sitio activo**: `erpnext-mexico.localhost`
**URL local**: http://localhost:8080

---

## Apps Instaladas en el Bench

| App | Version | Branch |
|---|---|---|
| frappe | 15.103.0 | version-15 |
| erpnext | 15.101.3 | version-15 |
| erpnext_mexico | 0.1.0 | UNVERSIONED (dev mount) |

La app `erpnext_mexico` esta montada como volumen live desde
`./erpnext_mexico` → `/home/frappe/frappe-bench/apps/erpnext_mexico`
Los cambios en el host se reflejan inmediatamente (hot-reload activo via watchdog).

---

## Estado del Código — Módulos Implementados

### Completado (Sprints 0-7 + Triple Audit Remediation)

| Módulo | Archivos clave | Estado |
|---|---|---|
| CFDI Engine (core) | `cfdi/xml_builder.py`, `cfdi/cfdi_helpers.py` | Completo |
| PAC Interface | `cfdi/pac_interface.py`, `cfdi/pac_dispatcher.py`, `cfdi/pac_utils.py` | Completo |
| PAC Finkok | `cfdi/pacs/finkok_pac.py` | Completo |
| PAC SW Sapien | `cfdi/pacs/sw_sapien_pac.py` | Completo |
| Invoicing Overrides | `invoicing/overrides/sales_invoice.py` | Completo |
| Payment Entry | `invoicing/overrides/payment_entry.py` | Completo |
| Purchase Invoice | `invoicing/overrides/purchase_invoice.py` | Completo |
| Nómina | `cfdi/nomina_builder.py`, `payroll/overrides/salary_slip.py` | Completo |
| Carta Porte | `cfdi/carta_porte_builder.py`, `carta_porte/overrides/delivery_note.py` | Completo |
| Complemento Pagos | `cfdi/payment_builder.py` | Completo |
| DIOT | `diot/diot_generator.py`, `diot/diot_report.py` | Completo |
| Contabilidad Electrónica | `electronic_accounting/balanza_xml.py`, `catalog_xml.py`, `polizas_xml.py` | Completo |
| Catálogos SAT | `sat_catalogs/doctype/` (15 DocTypes) + fixtures JSON | Completo |
| Config DocTypes | `cfdi/doctype/mx_cfdi_settings/`, `mx_digital_certificate/`, `mx_pac_credentials/`, `mx_cfdi_log/` | Completo |
| Setup | `setup/chart_of_accounts/mexico_standard.json`, `setup/tax_templates.py` | Completo |
| Utils | `utils/rfc_validator.py`, `utils/jinja_methods.py`, `utils/regional.py` | Completo |
| Print Format | `cfdi/print_format/cfdi_invoice_mx/`, `templates/cfdi_print.html` | Completo |
| Pages UI | `cfdi/page/mx_fiscal_dashboard/`, `mx_setup_wizard/`, `mx_diot_report/`, `mx_electronic_accounting/` | Completo |

### DocTypes registrados en hooks.py (doc_events activos)

- **Sales Invoice**: validate, on_submit (timbrado automático), on_cancel
- **Payment Entry**: validate, on_submit (Complemento Pagos), on_cancel
- **Purchase Invoice**: validate (solo validación)
- **Salary Slip**: validate, on_submit (Nómina 1.2), on_cancel
- **Delivery Note**: on_submit (Carta Porte 3.1), on_cancel

### Arquitectura PAC (Strategy Pattern)

```
PACInterface (abc)
    ├── FinkokPAC   → satcfdi.pacs.finkok.Finkok
    └── SWSapienPAC → satcfdi.pacs.swsapien.SWSapien

PACDispatcher.get_pac(company) → lee MX CFDI Settings → instancia PAC correcto
```

Dependencia principal: `satcfdi>=4.8.0` (declarada en pyproject.toml)
No hay dependencia de CFDI-Motor ni de ningún servicio REST externo propio.
El timbrado va directo a los PACs (Finkok o SW Sapien) via satcfdi.

---

## Integración con CFDI-Motor

**Resultado de búsqueda exhaustiva**: NO existe integración con CFDI-Motor.

No se encontraron referencias a:
- `cfdi_motor`, `CFDI_MOTOR`, `cfdi-motor`
- URLs de tipo `http://cfdi-motor.*`
- Llamadas HTTP hacia servicios externos propios de MD Consultoría

**Arquitectura actual**: ERPNext Mexico timbra directamente con PACs comerciales
(Finkok / SW Sapien) usando la biblioteca Python `satcfdi`. No pasa por CFDI-Motor.

**Implicación para integración futura**: Si se quiere que ERPNext Mexico use
CFDI-Motor como intermediario, habría que:
1. Crear un nuevo adaptador `cfdi/pacs/cfdi_motor_pac.py` que implemente `PACInterface`
2. Registrarlo en el dispatcher: `PACDispatcher.register("CFDI-Motor", CfdiMotorPAC)`
3. Llamar al endpoint REST de CFDI-Motor en lugar del PAC directo
El Strategy Pattern ya está preparado para eso sin cambios en el resto del sistema.

---

## Tests

| Estado | Cantidad |
|---|---|
| Passing | 192 |
| Failing | 4 |
| Total | 196 |

Archivos de test en `erpnext_mexico/tests/`:
- `test_xml_builder.py`
- `test_rfc_validator.py`
- `test_catalog_fixtures.py`
- `test_diot_generator.py`
- `test_nomina_builder.py`
- `test_carta_porte_builder.py`
- `test_jinja_methods.py`
- `test_sw_sapien_pac.py`

---

## Logs del Contenedor (últimas observaciones)

El servicio Frappe corre `bench start` con watchdog para hot-reload.
El scheduler corre con RQ (Redis Queue) — hay warnings de deprecación de
`datetime.utcnow()` en la librería `rq`, no son errores propios de la app.
No hay errores de inicialización ni de carga de la app en los logs recientes.

---

## Lo que Funciona

- Stack Docker completo levantado y estable
- App erpnext_mexico instalada y cargada en el sitio
- Hot-reload activo (cambios en host se reflejan sin rebuild)
- Motor CFDI: construcción XML, firma CSD, timbrado via Finkok y SW Sapien
- Módulos fiscales: Nómina 1.2, Carta Porte 3.1, Complemento Pagos 2.0
- Informes: DIOT 2025, Contabilidad Electrónica Anexo 24
- UI: Dashboard fiscal, Wizard de configuración, Print Format CFDI
- 192 de 196 tests pasando

## Lo que Está Pendiente / Deferred

| Item | Prioridad | Notas |
|---|---|---|
| 4 tests fallando | Media | Investigar causas exactas |
| Rate limiting en endpoints whitelisted | Media | Deferred de Triple Audit |
| CSP headers | Media | Deferred de Triple Audit |
| PAC timeout granular por endpoint | Baja | Actualmente 30s fijo |
| PII sanitization en logs | Media | Deferred de Triple Audit |
| Integración CFDI-Motor | Pendiente definición | Ver sección Integración arriba |
| Cancelación CFDI en on_cancel (sales_invoice) | Baja | Actualmente es manual via botón |

---

## Comando para Arrancar el Stack (si estuviera detenido)

```bash
cd /Users/marxchavez/Projects/erpnext-mexico/erpnext-mexico
docker compose up -d
```

Para ver logs en tiempo real:
```bash
docker compose logs -f frappe
```
