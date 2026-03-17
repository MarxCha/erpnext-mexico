# SPRINT-PLAN — ERPNext México (Plan Revisado v2)

## Resumen Ejecutivo
- **Timeline**: 15 semanas (6 sprints: 1×3sem + 5×2sem + 1×2sem buffer)
- **MVP Scope**: CFDI 4.0 + Complemento Pagos 2.0 + DIOT + Contabilidad Electrónica
- **Diferido a post-MVP**: Nómina Electrónica 1.2, Carta Porte 3.1
- **Motor CFDI**: satcfdi (PyPI)
- **PACs**: Finkok (primario) + SW Sapien (secundario)
- **Modelo arquitectónico**: India Compliance (resilient-tech/india-compliance)
- **Aprobado**: 2026-03-16 (Claude + Gemini cross-audit)

---

## Sprint 0 — Fundación (Semanas 1-3) ★ SPRINT ACTUAL
**Meta**: App instalable con DocTypes, catálogos SAT, custom fields y CI/CD

### Tareas
| # | Tarea | Owner (Skill/Agent) | Prioridad |
|---|-------|---------------------|-----------|
| 0.1 | Entorno Frappe local (Docker o bench nativo) | /bootstrap-v2 | P0-BLOCKER |
| 0.2 | CSD de prueba SAT (EKU9003173C9) | Marx (manual) | P0-BLOCKER |
| 0.3 | Cuenta sandbox Finkok | Marx (manual) | P0-BLOCKER |
| 0.4 | DocType JSON: MX CFDI Settings (Single, tabs) | /architect + /backend | P0 |
| 0.5 | DocType JSON: MX Digital Certificate (.cer parse) | /backend | P0 |
| 0.6 | DocType JSON: MX PAC Credentials | /backend | P0 |
| 0.7 | DocType JSON: MX CFDI Log | /backend | P0 |
| 0.8 | 15 DocType JSONs catálogos SAT | /database + /backend | P0 |
| 0.9 | catalog_importer.py (bulk_insert 20K chunks) | /database | P1 |
| 0.10 | Fixtures JSON catálogos pequeños (<100 regs) | /backend | P1 |
| 0.11 | Evaluar satcfdi.catalogs como fuente de datos | /integration | P1 |
| 0.12 | Validar install.py en bench real | /backend | P0 |
| 0.13 | Chart of Accounts (mexico_standard.json) | /database | P1 |
| 0.14 | Tax Templates (IVA 16%, 0%, exento, retenciones) | /backend | P1 |
| 0.15 | GitHub repo + .gitignore + LICENSE GPL-3.0 | /backend | P0 |
| 0.16 | GitHub Actions: ruff lint + pytest | /backend | P1 |
| 0.17 | Tests: RFC validator, catálogos cargados, custom fields | /test-v2 | P1 |
| 0.18 | property_setters.py (campos ERPNext existentes) | /backend | P2 |

### Criterios de Completitud
- `bench --site dev.localhost install-app erpnext_mexico` sin errores
- `bench migrate` sin errores
- 19 DocTypes creados (4 config + 15 catálogos)
- Catálogos pequeños cargados y consultables via Link Fields
- Custom fields visibles en Company, Customer, Supplier, Item, Sales Invoice
- CI verde en GitHub

### Riesgos Sprint 0
- Docker vs bench nativo: Docker más rápido de setup pero más lento en desarrollo
- Catálogos pesados (55K+70K registros): evaluar satcfdi.catalogs primero

---

## Sprint 1 — Timbrado CFDI (Semanas 4-5)
**Meta**: Timbrar factura de venta real en sandbox Finkok

### Tareas
| # | Tarea | Owner | Prioridad |
|---|-------|-------|-----------|
| 1.1 | MX Digital Certificate controller (parse .cer, expiry) | /backend | P0 |
| 1.2 | Validar xml_builder.py contra sandbox real | /integration | P0 |
| 1.3 | Flujo stamp completo en sandbox Finkok | /integration | P0 |
| 1.4 | sales_invoice.js: botón "Timbrar CFDI", badge estado | /frontend | P0 |
| 1.5 | customer.js: validación RFC en tiempo real | /frontend | P1 |
| 1.6 | item.js: buscador clave SAT autocompletado | /frontend | P1 |
| 1.7 | company.js: sección datos fiscales | /frontend | P2 |
| 1.8 | Tests: timbrado e2e sandbox, validaciones campos | /test-v2 | P0 |

### Criterios de Completitud
- UUID real de Finkok sandbox almacenado en Sales Invoice
- XML timbrado adjunto al documento
- MX CFDI Log con registro completo
- Client scripts funcionales en formularios
- Tests e2e pasando

### Riesgos Sprint 1
- satcfdi API puede diferir de documentación (pinear versión)
- Sandbox Finkok puede tener intermitencias

---

## Sprint 2 — Cancelación + Print + Crédito (Semanas 6-7)
**Meta**: Ciclo completo I + E + cancelación funcional

### Tareas
| # | Tarea | Owner | Prioridad |
|---|-------|-------|-----------|
| 2.1 | cancellation.py completo (motivos 01-04, estado) | /backend | P0 |
| 2.2 | cancel_cfdi() funcional vía PAC | /integration | P0 |
| 2.3 | Print Format CFDI (Jinja: QR, cadena original, sellos) | /frontend + /ui-design | P0 |
| 2.4 | credit_note.py: CFDI tipo "E" con TipoRelacion "01" | /backend | P1 |
| 2.5 | global_invoice.py: factura público general | /backend | P1 |
| 2.6 | UI cancelación: diálogo motivos, UUID sustituto | /frontend | P1 |
| 2.7 | Tests: cancelación, nota crédito, factura global | /test-v2 | P0 |

### Criterios de Completitud
- Cancelación exitosa en sandbox (al menos motivo 02)
- PDF CFDI con QR legible y datos fiscales completos
- Nota de crédito timbrada vinculada a factura original
- Tests pasando

---

## Sprint 3 — Complemento de Pagos 2.0 (Semanas 8-9) ⚠️ ALTO RIESGO
**Meta**: Flujo PPD completo con parcialidades timbrado en sandbox

### Tareas
| # | Tarea | Owner | Prioridad |
|---|-------|-------|-----------|
| 3.1 | payment_complement.py: parcialidades, saldos, Totales 2.0 | /backend | P0-CRÍTICO |
| 3.2 | Lógica PUE vs PPD auto-detect | /backend | P0 |
| 3.3 | ImpuestosDR por DoctoRelacionado | /backend | P0 |
| 3.4 | Multi-moneda: EquivalenciaDR, MonedaP vs MonedaDR | /backend | P1 |
| 3.5 | Hook on_submit Payment Entry → CFDI tipo "P" | /backend | P0 |
| 3.6 | payment_entry.js: indicadores PPD, botón complemento | /frontend | P1 |
| 3.7 | Tests: flujo PPD completo (factura → parciales → final) | /test-v2 | P0 |
| 3.8 | /swarm-verify post-implementación lógica fiscal | Swarm Verify | P0 |

### Criterios de Completitud
- CFDI tipo "P" timbrado en sandbox con nodo Totales 2.0
- Parcialidades correctas (NumParcialidad secuencial)
- Saldos cuadran (ImpSaldoAnt - ImpPagado = ImpSaldoInsoluto)
- Multi-moneda funcional (MXN + USD)
- Swarm Verify aprueba

### Riesgos Sprint 3 (señalado por Gemini como mayor riesgo)
- Conciliación tipos de cambio con EquivalenciaDR
- Nodos ImpuestosDR complejos cuando hay múltiples tasas
- satcfdi pago20 puede requerir ajustes

---

## Sprint 4 — Compras + DIOT (Semanas 10-11)
**Meta**: Importación XML compras + archivo DIOT generado

### Tareas
| # | Tarea | Owner | Prioridad |
|---|-------|-------|-----------|
| 4.1 | Importador XML compras → Purchase Invoice | /backend | P0 |
| 4.2 | Validación estado CFDI proveedor contra SAT | /integration | P1 |
| 4.3 | purchase_invoice.js: botón "Importar XML" | /frontend | P1 |
| 4.4 | DocType: MX DIOT Report + child table MX DIOT Line | /backend | P0 |
| 4.5 | diot_generator.py: TXT 54 campos, pipes | /backend | P0 |
| 4.6 | frappe.enqueue para generación DIOT masiva | /backend | P1 |
| 4.7 | Tests: import XML, DIOT format validation | /test-v2 | P0 |

### Criterios de Completitud
- XML de proveedor parseado → Purchase Invoice creada con datos fiscales
- DIOT TXT generado con formato correcto (54 campos, pipes)
- Totales DIOT cuadran contra contabilidad
- Tests pasando

---

## Sprint 5 — Contabilidad Electrónica + 2do PAC (Semanas 12-13)
**Meta**: 3 XMLs Anexo 24 + SW Sapien como PAC alternativo

### Tareas
| # | Tarea | Owner | Prioridad |
|---|-------|-------|-----------|
| 5.1 | chart_of_accounts_xml.py: Catálogo cuentas Anexo 24 v1.3 | /backend | P0 |
| 5.2 | trial_balance_xml.py: Balanza mensual | /backend | P0 |
| 5.3 | journal_entries_xml.py: Pólizas con UUID CFDI | /backend | P1 |
| 5.4 | DocType: MX Electronic Accounting | /backend | P1 |
| 5.5 | pacs/sw_sapien_pac.py: adapter completo | /integration | P1 |
| 5.6 | Scheduler: check_cancellation_status (hourly) | /backend | P2 |
| 5.7 | Scheduler: check_certificate_expiry (daily) | /backend | P2 |
| 5.8 | Tests: XML Anexo 24 validation, SW Sapien stamp | /test-v2 | P0 |

### Criterios de Completitud
- 3 XMLs de contabilidad electrónica generados correctamente
- SW Sapien timbra en sandbox
- Scheduler tasks funcionando
- Tests pasando

---

## Sprint 6 — QA + Release (Semanas 14-15)
**Meta**: App publicada en Frappe Cloud Marketplace

### Tareas
| # | Tarea | Owner | Prioridad |
|---|-------|-------|-----------|
| 6.1 | /audit — Code audit completo | /audit | P0 |
| 6.2 | /func-audit — Functional audit con scoring | /func-audit | P0 |
| 6.3 | Tests integración e2e (flujo completo I→P→DIOT→Cont.Elec) | /test-v2 | P0 |
| 6.4 | Coverage report (meta: >70%) | /test-v2 | P1 |
| 6.5 | Documentación usuario: instalación, configuración, uso | /doc-process | P0 |
| 6.6 | /doc-api — Documentación API (whitelisted methods) | /doc-api | P1 |
| 6.7 | README final + screenshots + logo | /frontend | P1 |
| 6.8 | Submit Frappe Cloud Marketplace | Marx (manual) | P0 |
| 6.9 | Landing page mdconsultoria.mx/erpnext-mexico | /frontend-design | P2 |
| 6.10 | /swarm-verify — QA final pre-release | Swarm Verify | P0 |
| 6.11 | /swarm-ship — Release checklist | Swarm Ship | P0 |

### Criterios de Completitud
- Code audit score > 80/100
- Functional audit score > 40/50
- Coverage > 70%
- App publicada en Marketplace
- Documentación completa

---

## Post-MVP (Mes 5+)

### Nómina Electrónica 1.2 Rev E (8-10 semanas estimadas)
- ISR calculator con tablas tarifarias por año/periodo
- IMSS calculator (7 ramas, tope 25×UMA, reforma gradual 2023-2030)
- INFONAVIT calculator
- Complemento Nómina 1.2 XML builder
- 13 DocTypes catálogos nómina
- MX Employee Fiscal Data, MX Payroll Settings, MX ISR Table, MX UMA Value
- Decisión pendiente: HRMS vs ERPNext Payroll legacy (BLOCKER-005)

### Carta Porte 3.1 (4-6 semanas estimadas)
- Solo si hay demanda real de clientes con transporte federal
- DocTypes: MX Carta Porte, MX Vehicle, MX Transport Operator
- Catálogos específicos (c_ClaveProdServCP, permisos SCT, etc.)

### Mejoras continuas
- Portal autofacturación
- Descarga masiva XML SAT (FIEL)
- Conciliación compras vs CFDIs recibidos
- Lista negra 69-B SAT
- Multi-empresa (holding con múltiples RFC)
- Addendas preconstruidas (Walmart, Soriana, etc.)
