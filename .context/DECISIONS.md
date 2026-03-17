# DECISIONS — Registro de Decisiones Técnicas

## DEC-001: Frappe App independiente, NO fork de ERPNext
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado
**Contexto**: Decidir entre fork de ERPNext o app independiente
**Decisión**: App independiente que extiende via hooks
**Justificación**: Fork pierde actualizaciones upstream, multiplica mantenimiento. App independiente se beneficia de cada release de ERPNext/Frappe sin conflictos.
**Modelo**: India Compliance (github.com/resilient-tech/india-compliance)

## DEC-002: satcfdi como motor de CFDI
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado
**Contexto**: Construir XML builder propio vs usar biblioteca existente
**Decisión**: Usar `satcfdi` (PyPI, MIT license, 4.8.2)
**Justificación**: Mantiene catálogos SAT actualizados, integra 5 PACs, maneja firma digital. Reinventar esto tomaría meses y sería error-prone. MIT license compatible con GPL-3.0.

## DEC-003: Multi-PAC con Finkok primario + SW Sapien secundario
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado
**Contexto**: Elegir PAC único vs arquitectura multi-PAC
**Decisión**: Strategy Pattern multi-PAC. Finkok como default (más económico), SW Sapien como alternativa (REST nativo, más rápido).
**Justificación**: Evita vendor lock-in (problema de erpnext_mexico_compliance). El usuario elige su PAC.

## DEC-004: Licencia GPL-3.0
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado
**Contexto**: MIT vs GPL vs AGPL
**Decisión**: GPL-3.0 (compatible con ERPNext AGPL-3.0)
**Justificación**: ERPNext es GPL-3.0. Frappe es MIT. Apps sobre ERPNext generalmente usan GPL-3.0. Permite publicar en Marketplace con modelo freemium (core gratis, servicio gestionado de pago).

## DEC-005: Prefijo mx_ en todos los custom fields
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado
**Contexto**: Naming convention para custom fields
**Decisión**: Prefijo `mx_` en fieldname (ej: `mx_rfc`, `mx_cfdi_uuid`)
**Justificación**: Evita colisiones con otros apps de localización. Frappe best practice. India Compliance usa prefijo `gst_`.

## DEC-006: Catálogos SAT como DocTypes, no como tablas planas
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado
**Contexto**: Cómo almacenar los ~15 catálogos del SAT (algunos con 70K registros)
**Decisión**: Cada catálogo es un DocType propio con campos: code, description, valid_from, valid_to
**Justificación**: Link Fields en formularios dan autocompletado nativo. Permite filtrar por vigencia. Bulk import via fixtures JSON o catalog_importer.py para catálogos pesados.

## DEC-007: Dual distribution (Marketplace + servicio gestionado)
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado
**Contexto**: Solo Marketplace vs solo hosting vs ambos
**Decisión**: App gratuita en Frappe Marketplace + servicio gestionado MD a $500-2,000 MXN/mes
**Justificación**: Marketplace da distribución y credibilidad (publisher retiene 80% de ventas). Servicio gestionado da ingresos recurrentes y control sobre la experiencia.

## DEC-008: Diferir Nómina Electrónica a post-MVP
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado (Claude + Gemini)
**Contexto**: Incluir nómina en MVP de 15 semanas vs diferir
**Decisión**: Nómina 1.2 Rev E es post-MVP. No entra en los 6 sprints del MVP.
**Justificación**: Nómina es prácticamente una app independiente (ISR, IMSS, INFONAVIT, subsidio, 13 catálogos extra). Gemini concurre: "duplicaría el tiempo de desarrollo". El MVP entrega valor completo sin nómina (muchas PyMEs no manejan nómina propia). Estimado: 8-10 semanas adicionales post-MVP.

## DEC-009: Diferir Carta Porte 3.1 a post-MVP
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado (Claude + Gemini)
**Contexto**: Incluir Carta Porte en MVP vs diferir
**Decisión**: Carta Porte 3.1 es post-MVP, solo si hay demanda real.
**Justificación**: Solo aplica a empresas con transporte en vías federales (nicho). Bajo % de usuarios lo necesitaría. Estimado: 4-6 semanas adicionales.

## DEC-010: Sprints de 2 semanas (excepto Sprint 0)
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado
**Contexto**: Sprints de 3 semanas (original) vs 2 semanas (revisado)
**Decisión**: Sprint 0 = 3 semanas (fundación pesada). Sprints 1-6 = 2 semanas cada uno. Total: 15 semanas.
**Justificación**: Sprints cortos = feedback más rápido, menor riesgo de desvío. Recomendación alineada entre Claude y Gemini.

## DEC-011: Testing y CI desde Sprint 0
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado (recomendación Gemini)
**Contexto**: Tests al final vs desde el inicio
**Decisión**: CI (ruff + pytest) desde Sprint 0. Tests unitarios desde día 1.
**Justificación**: Gemini: "En Frappe, la deuda técnica crece exponencialmente". Validar XML contra XSD antes de enviar a PAC.

## DEC-012: satcfdi.catalogs como fuente de catálogos SAT
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado (validado con Gemini)
**Contexto**: Descargar Excel del SAT vs usar catálogos embebidos de satcfdi
**Decisión**: Usar `satcfdi.catalogs` (SQLite integrado) como fuente primaria. Fallback a Excel solo si satcfdi no tiene todos los campos.
**Justificación**: satcfdi incluye 55K+ ClaveProdServ, 70K+ CodigoPostal, todos los catálogos menores. Acceso: `catalogs.select('c_ClaveProdServ', '84111506')`. Elimina BLOCKER-003.

## DEC-013: Patrones India Compliance para install/setup
**Fecha**: 2026-03-16
**Estado**: ✅ Aprobado
**Contexto**: Fixtures Frappe tradicionales vs programmatic setup
**Decisión**: Usar `frappe.db.bulk_insert(chunk_size=20_000)` en after_install(). NO usar `fixtures/` + `bench export-fixtures`. property_setters.py separado.
**Justificación**: Patrón probado en India Compliance (app con 900+ stars). Más control, más rápido, duplicable en patches.txt para upgrades.
