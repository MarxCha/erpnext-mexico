# STATUS — ERPNext México

## Estado: 🟡 Sprint 0 — Fundación (EN PROGRESO)
**Fecha**: 2026-03-16
**Sprint**: 0 de 6
**Progreso**: 75% (código creado, pendiente: bench install + CI push)

## Completado en esta sesión
- Git init + .gitignore + LICENSE GPL-3.0
- 4 DocTypes de configuración (CFDI module): Settings, Certificate, PAC Credentials, Log
- 15 DocTypes de catálogos SAT (SAT Catalogs module)
- 11 fixtures JSON con datos reales del SAT
- catalog_importer.py (satcfdi.catalogs → DocTypes)
- Chart of Accounts mexicano (mexico_standard.json)
- Tax Templates: IVA 16%, 0%, exento, ISR ret 10%, IVA ret 10.6667%, combinados
- install.py actualizado: carga fixtures + tax templates
- 20 tests unitarios pasando (RFC validator + catalog fixtures)
- CI/CD: GitHub Actions (lint + tests) + .pre-commit-config.yaml
- modules.txt: ERPNext Mexico, CFDI, SAT Catalogs

## Próximo paso
- Resolver BLOCKER-004: configurar Frappe v15 local
- `bench install-app erpnext_mexico` + `bench migrate`
- Validar custom fields visibles en formularios
- Push a GitHub + activar CI

## Métricas
- DocTypes creados: 19 / 19 ✅
- Custom Fields: definidos en install.py (pendiente validar en bench)
- Catálogos SAT fixtures: 11 / 11 ✅
- Tests pasando: 20 / 20 ✅
- Cobertura: RFC validator + fixtures (standalone, sin Frappe)

## Dependencias externas
- [🔴] Entorno Frappe local (BLOCKER-004) — bloquea validación end-to-end
- [🔴] CSD prueba SAT EKU9003173C9 (BLOCKER-002)
- [🟡] Sandbox Finkok (BLOCKER-001, no bloquea Sprint 0)
- [✅] Catálogos SAT (BLOCKER-003 resuelto)
