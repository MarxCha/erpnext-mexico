# RESOURCE-MATRIX — Asignación de Skills, Agents y Swarms

## Skills por Sprint

### Always-Load (activos en toda la sesión)
| Skill | Razón |
|-------|-------|
| `security` | Credenciales PAC, contraseñas CSD, XSS en XML |
| `semaforo-capacidad` | Monitoreo complejidad por sprint |

### Tier 1 — Auto-activación por contexto
| Skill | Sprints | Contexto |
|-------|---------|----------|
| `systematic-debugging` | 1-5 | Debugging sandbox PAC, errores timbrado |
| `verification-before-completion` | 0-6 | Verificación al cierre de cada sprint |
| `production-code-audit` | 5-6 | Auditoría pre-release |
| `typescript-expert` | N/A | No aplica (proyecto Python/JS vanilla) |

### Agentes Invocables por Sprint

```
Sprint 0 — Fundación
├── /architect      → Diseño DocType schemas JSON
├── /database       → Chart of Accounts, catálogos SAT, bulk_insert
├── /backend        → install.py, hooks.py validation, catalog_importer
├── /bootstrap-v2   → Entorno Docker/bench setup
├── /test-v2        → Tests unitarios iniciales
└── /integration    → Evaluar satcfdi.catalogs

Sprint 1 — Timbrado CFDI
├── /backend        → MX Digital Certificate controller, xml_builder
├── /integration    → Flujo stamp Finkok sandbox
├── /frontend       → sales_invoice.js, customer.js, item.js
└── /test-v2        → Tests e2e timbrado

Sprint 2 — Cancelación + Print
├── /backend        → cancellation.py, credit_note.py, global_invoice.py
├── /frontend       → UI cancelación, Print Format Jinja
├── /ui-design      → Diseño PDF CFDI (QR, sellos, cadena original)
└── /test-v2        → Tests cancelación, nota crédito

Sprint 3 — Complemento Pagos ⚠️
├── /backend        → payment_complement.py (CRÍTICO)
├── /integration    → Timbrado CFDI tipo "P" sandbox
├── /frontend       → payment_entry.js
├── /test-v2        → Tests flujo PPD completo
└── /swarm-verify   → Verificación post-implementación lógica fiscal

Sprint 4 — Compras + DIOT
├── /backend        → XML importer, diot_generator.py, frappe.enqueue
├── /frontend       → purchase_invoice.js
└── /test-v2        → Tests DIOT format

Sprint 5 — Cont. Electrónica + 2do PAC
├── /backend        → XMLs Anexo 24, scheduler tasks
├── /integration    → SW Sapien PAC adapter
└── /test-v2        → Tests XML validation

Sprint 6 — QA + Release
├── /audit          → Code audit completo
├── /func-audit     → Functional audit (scoring 0-50)
├── /test-v2        → Coverage report, integration e2e
├── /doc-process    → Documentación usuario
├── /doc-api        → Documentación API
├── /frontend-design → Landing page (si hay tiempo)
├── /swarm-verify   → QA final
└── /swarm-ship     → Release checklist
```

## Agent Teams (cuando aplique)

### Sprint 1: Frontend + Backend en paralelo
```
Agent Team: "CFDI Timbrado"
Spawn 2 teammates:
1. BackendDev — owns: cfdi/, invoicing/overrides/
2. FrontendDev — owns: public/js/, templates/
Criterio: Timbrado funcional + UI funcional
```

### Sprint 3: Verificación cruzada Pagos
```
Agent Team: "Pagos Verification"
Spawn 3 teammates:
1. PaymentDev — owns: invoicing/payment_complement.py
2. TestWriter — owns: invoicing/tests/test_payment_complement.py
3. FiscalReviewer — valida lógica contra FISCAL-REQUIREMENTS.md
Criterio: Parcialidades correctas + saldos cuadran + XML válido
```

### Sprint 6: Multi-angle Review
```
Agent Team: "Pre-Release Review"
Spawn 3 teammates:
1. SecurityReviewer — OWASP, credenciales, XSS en XML
2. FiscalReviewer — compliance SAT, catálogos vigentes
3. PerformanceReviewer — queries N+1, bulk operations, timeouts
Criterio: Reporte unificado con severity
```

## Swarms

### /swarm-plan (Sprint 0)
- Usar para planificación detallada si se requiere replanning mid-sprint

### /swarm-build (Sprints 1-5)
- Vision + Builders + Experts para features complejas
- Activar especialmente en Sprint 3 (Pagos) por complejidad

### /swarm-verify (Sprints 3, 6)
- Guardians: verificación post-implementación
- Sprint 3: Lógica fiscal de pagos (parcialidades, saldos, impuestos)
- Sprint 6: QA final pre-release (regression, e2e, compliance)

### /swarm-ship (Sprint 6)
- Scribes: release checklist
- README, CHANGELOG, screenshots, Marketplace submission
- Handoff documentation

## Flujo Gemini (Cross-Audit)

| Fase | Cuándo | Qué |
|------|--------|-----|
| Plan review | Sprint 0 (hecho) | Evaluar plan ✅ |
| satcfdi validation | Sprint 0 ✅ | satcfdi.catalogs validado + Pagos 2.0 confirmado (DEC-012) |
| Mid-project review | Sprint 3 | Cross-audit después de Pagos |
| Pre-release review | Sprint 6 | Peer review código completo |
