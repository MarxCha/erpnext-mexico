# ERPNext México — Localización Fiscal Completa

## Proyecto
Frappe App de localización fiscal mexicana para ERPNext. Producto de MD Consultoría SC.
Dual distribution: Frappe Cloud Marketplace (open source) + servicio gestionado con marca MD.

## Stack
- **Framework**: Frappe v15/v16 (Python 3.11+, MariaDB, Redis, Vue.js 3)
- **Required App**: ERPNext (frappe/erpnext)
- **CFDI Engine**: `satcfdi` (pip install satcfdi) — genera XML, firma CSD, timbra vía PAC
- **PACs soportados**: Finkok/Quadrum (primario), SW Sapien (secundario)
- **Licencia**: GPL-3.0

## Alcance del MVP
1. **CFDI 4.0** — Facturación electrónica completa (tipos I, E, T, N, P)
2. **Complemento de Pagos 2.0** — Flujo PUE/PPD con parcialidades
3. **Nómina electrónica 1.2 Rev E** — ISR, IMSS, INFONAVIT, subsidio al empleo
4. **DIOT 2025** — Declaración informativa TXT 54 campos
5. **Carta Porte 3.1** — Transporte de mercancías
6. **Contabilidad electrónica** — Catálogo cuentas, balanza, pólizas (Anexo 24)

## Arquitectura
- NO es fork de ERPNext — es Frappe App independiente que extiende via hooks
- Modelo: India Compliance (github.com/resilient-tech/india-compliance)
- Multi-PAC via Strategy Pattern + satcfdi como motor unificado
- Custom Fields prefijados con `mx_` para evitar colisiones
- Catálogos SAT como DocTypes importados desde Excel oficial

## Comandos Frecuentes
```bash
# Desarrollo
bench new-app erpnext_mexico
bench get-app erpnext_mexico /path/to/repo
bench --site dev.localhost install-app erpnext_mexico
bench --site dev.localhost migrate
bench --site dev.localhost clear-cache

# Testing
bench --site dev.localhost run-tests --app erpnext_mexico
bench --site dev.localhost run-tests --module erpnext_mexico.cfdi.tests

# Catálogos SAT
bench --site dev.localhost execute erpnext_mexico.sat_catalogs.catalog_importer.import_all

# Fixtures
bench --site dev.localhost export-fixtures --app erpnext_mexico
```

## Reglas de Código
- Prefijo `mx_` en todos los custom fields
- Docstrings en español para lógica fiscal, en inglés para lógica técnica
- Type hints obligatorios en funciones públicas
- Tests con CSD de prueba SAT: RFC `EKU9003173C9` (persona moral)
- Sandbox Finkok: `demo-facturacion.finkok.com`
- Sandbox SW Sapien: `api.test.sw.com.mx`
- Nunca hardcodear credenciales de PAC — siempre desde MX CFDI Settings
- XML CFDI debe validar contra XSD oficial del SAT antes de enviar a PAC

## Archivos de Contexto
- `.context/STATUS.md` — Estado actual del sprint
- `.context/PLAN-current.md` — Plan de sprint activo con tareas
- `.context/DECISIONS.md` — Decisiones técnicas tomadas
- `.context/BLOCKERS.md` — Blockers activos
- `.context/ARCHITECTURE.md` — Arquitectura detallada de módulos
- `.context/FISCAL-REQUIREMENTS.md` — Requisitos fiscales mexicanos
- `.context/PAC-INTEGRATION.md` — Guía de integración con PACs
- `.context/SPRINT-PLAN.md` — Roadmap completo de 5 sprints
- `.context/PROMPT-MASTER.md` — Prompt maestro para implementación
