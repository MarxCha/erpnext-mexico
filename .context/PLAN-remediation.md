# PLAN — Solventación Integral ERPNext Mexico

**Fecha**: 2026-03-19
**Objetivo**: Resolver TODOS los pendientes, dejar la app lista para producción
**Estado previo**: Sprints 0-7 completos, Triple Audit hecho, Docker levantado

---

## Sprint R1: Estabilización (Tests + Blockers)
**Duración**: ~30 min | **Prioridad**: CRÍTICA

### Tareas
1. **Fix 4 tests fallando** — Identificar y corregir
2. **BLOCKER-002**: Verificar CSD de prueba en satcfdi
3. **BLOCKER-001**: Verificar sandbox Finkok/SW Sapien (investigar credenciales de prueba de satcfdi)
4. **Actualizar BLOCKERS.md** — Marcar B-004 resuelto, actualizar B-001/B-002

### Criterio de éxito
- 196/196 tests passing
- Blockers actualizados con estado real

---

## Sprint R2: Seguridad Deferred (Triple Audit)
**Duración**: ~30 min | **Prioridad**: MEDIA-ALTA

### Tareas
1. **Rate limiting** en endpoints whitelisted (12 endpoints)
2. **PII sanitization** en logs (RFCs, nombres en error logs)
3. **CSP headers** — Content Security Policy para páginas CFDI

### Criterio de éxito
- Rate limiting activo en todos los endpoints @frappe.whitelist()
- Logs no exponen RFCs completos
- CSP headers configurados

---

## Sprint R3: Validación Visual + Funcional
**Duración**: ~20 min | **Prioridad**: MEDIA

### Tareas
1. **Playwright/Chrome DevTools**: Validar login, navegación a MX CFDI Settings, creación de Customer con campos mx_*
2. **Verificar UI**: Dashboard fiscal, Setup Wizard, List Views
3. **Console errors**: Zero JS errors en flujo principal

### Criterio de éxito
- Navegación completa sin errores
- Custom fields visibles en formularios
- Dashboard fiscal renderiza

---

## Sprint R4: Cierre y Documentación
**Duración**: ~10 min | **Prioridad**: BAJA

### Tareas
1. Actualizar STATUS.md, BLOCKERS.md, PLAN-current.md
2. Commit + push final
3. Reporte al CEO

### Criterio de éxito
- Todo commiteado y pusheado
- Contexto actualizado para próxima sesión

---

## Asignación de Recursos

| Sprint | Agentes/Tools | Modo |
|--------|--------------|------|
| R1 | test-backend (tests), general-purpose (CSD research) | Agent Teams paralelo |
| R2 | security-reviewer (audit), backend (implementación) | Secuencial |
| R3 | Playwright MCP / Chrome DevTools | Verificación visual |
| R4 | Single session | Commit + docs |
