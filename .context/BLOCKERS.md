# BLOCKERS — Blockers Activos

## BLOCKER-001: Cuentas sandbox de PACs
**Estado**: 🟡 Parcialmente resuelto
**Progreso**: Cuenta Finkok creada (marx_chavez@yahoo.com en facturacion.finkok.com, 2026-03-18).
**Pendiente**: Configurar credenciales en MX PAC Credentials del ERPNext. Registrar SW Sapien sandbox.
**Owner**: Marx
**ETA**: Sesión actual o siguiente

## ~~BLOCKER-002: CSD de prueba del SAT~~
**Estado**: ✅ RESUELTO (2026-03-19)
**Resolución**: CSD de prueba descargados desde repo satcfdi (GitHub SAT-CFDI/python-satcfdi).
RFC: EKU9003173C9 (ESCUELA KEMPER URGATE). Certificate: 30001000000400002434. Password: 12345678a.
Ubicación: tests/fixtures/csd/eku9003173c9_csd.{cer,key,txt}. Validado con satcfdi.models.Signer.
Válidos hasta mayo 2027.

## ~~BLOCKER-003: Catálogos SAT en formato Excel~~
**Estado**: ✅ RESUELTO (2026-03-16)
**Resolución**: satcfdi incluye catálogos embebidos via SQLite. Acceso: `satcfdi.catalogs.select()`. Validado con Gemini. No es necesario descargar Excel del SAT.
**Ver**: DEC-012

## ~~BLOCKER-004: Entorno Frappe de desarrollo local~~
**Estado**: ✅ RESUELTO (2026-03-19)
**Resolución**: Docker Compose con frappe/bench image. 4 contenedores: Frappe+ERPNext+erpnext_mexico, MariaDB 10.11, Redis x2.
URL: http://localhost:8080. Setup wizard completado con Mexico, MXN, America/Mexico_City.
Hot-reload activo via watchdog. 196/196 tests passing.

## ~~BLOCKER-005: Decisión sobre integración con HRMS~~
**Estado**: ✅ RESUELTO (2026-03-16)
**Resolución**: Nómina diferida a post-MVP (DEC-008). La decisión HRMS vs Payroll legacy se tomará cuando se implemente nómina.
