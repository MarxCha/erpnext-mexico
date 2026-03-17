# BLOCKERS — Blockers Activos

## BLOCKER-001: Cuentas sandbox de PACs
**Estado**: 🟡 Pendiente (no bloquea Sprint 0, bloquea Sprint 1)
**Impacto**: Sprint 1 no puede iniciar tests de timbrado sin esto
**Acción requerida**: Registrar cuenta sandbox en Finkok (demo-facturacion.finkok.com) y SW Sapien (developers.sw.com.mx)
**Owner**: Marx
**ETA**: Pre-Sprint 1 (antes de semana 4)

## BLOCKER-002: CSD de prueba del SAT
**Estado**: 🔴 Pendiente (requerido en Sprint 0, bloquea inicio de Sprint 1)
**Impacto**: No se puede firmar XML sin CSD. Sprint 0 (DocTypes/catálogos) no lo necesita, pero debe resolverse antes de Sprint 1.
**Acción requerida**: Descargar CSD de prueba para RFC EKU9003173C9. Verificar si satcfdi los incluye en su repo.
**Owner**: Marx / Dev
**ETA**: Sprint 0

## ~~BLOCKER-003: Catálogos SAT en formato Excel~~
**Estado**: ✅ RESUELTO (2026-03-16)
**Resolución**: satcfdi incluye catálogos embebidos via SQLite. Acceso: `satcfdi.catalogs.select()`. Validado con Gemini. No es necesario descargar Excel del SAT.
**Ver**: DEC-012

## BLOCKER-004: Entorno Frappe de desarrollo local
**Estado**: 🔴 Pendiente (bloquea TODO)
**Impacto**: No se puede desarrollar sin bench funcionando
**Acción requerida**: Configurar bench con Frappe v15 + ERPNext v15 en Mac Mini M4
**Opciones**: Docker (frappe/frappe_docker) o bench nativo con pyenv
**Owner**: Dev
**ETA**: Sprint 0, días 1-2

## ~~BLOCKER-005: Decisión sobre integración con HRMS~~
**Estado**: ✅ RESUELTO (2026-03-16)
**Resolución**: Nómina diferida a post-MVP (DEC-008). La decisión HRMS vs Payroll legacy se tomará cuando se implemente nómina.
