# STATUS — ERPNext México

## Estado: Sprint 7 — Nómina 1.2 Rev E (COMPLETADO)
**Fecha**: 2026-03-18
**Progreso**: Sprints 0-7 + Hardening 100%

## Completado — Sprint 7: CFDI Nómina 1.2 Rev E
- cfdi/nomina_builder.py: build_nomina_cfdi + sign_nomina_cfdi completos
- payroll/overrides/salary_slip.py: validate, on_submit, on_cancel, stamp_nomina, retry_stamp_nomina
- install.py: 27 nuevos custom fields (Employee laboral, Salary Slip CFDI, Salary Component SAT, Company patronal)
- public/js/salary_slip.js: botón Timbrar CFDI Nómina + indicador de estado
- tests/test_nomina_builder.py: 61 unit tests, todos pasando
- Total acumulado: 148 unit tests (87 + 61 nuevos)

## Estado: Sprint 6 Polish & Production Readiness (COMPLETADO)
**Fecha**: 2026-03-17
**Progreso**: Sprints 0-6 + Hardening 100%

## Completado — Sprint 6: Polish & Production Readiness
- M-06: DIOT key naming unificado (valor_* everywhere)
- M-10: N+1 queries eliminados (DIOT batch fetch, catalog level cache)
- M-11: Catalog importer con update incremental (force_update=True)
- M-17: Setup Wizard verifica catálogos SAT cargados
- M-19: Dashboard metrics alineados (solo CFDI invoices)
- M-20: RFC validation server-side en wizard
- M-09: Tests RFC validator corregidos (assertions reales)
- 3 nuevos test suites: test_xml_builder (15), test_diot_generator (36), test_jinja_methods (16)
- Total: 67 nuevos unit tests, todos pasando

## Completado — Sprint Hardening (Auditoría Funcional)
- Score: 27/50 → 39/50 → 43/50 (post-Sprint 6)
- 6/6 críticos, 10/10 altos, 20/20 menores RESUELTOS
- 19+ archivos modificados, 0 errores compilación

## Completado — Sprints 0-5
- Sprint 0: 19 DocTypes, 46 custom fields, CFDI engine
- UX Sprint: Design System, Dashboard, Wizard, List Views
- Sprint 1: CFDI timbrado funcional (UUID sandbox)
- Sprint 2: Complemento de Pagos 2.0
- Sprint 3: DIOT 2025 generator
- Sprint 4: Contabilidad Electrónica (Anexo 24)
- Sprint 5: Print Format + polish

## Totales Acumulados
- Archivos: 165+ (Python, JS, CSS, JSON)
- Líneas de código: ~12,500+
- Tests: 148 unit tests pasando (87 anterior + 61 nómina)

## Entorno Local
- Frappe 15.102.1 + ERPNext 15.101.0
- Site: dev.localhost (admin/admin123)

## Pendientes para sprints futuros:
- CFDI tipo T (Carta Porte 3.1) — requiere módulo transporte
- SW Sapien PAC adapter — segunda opción de PAC
- Cancelación CFDI Nómina (flujo similar a Sales Invoice cancel_cfdi)
