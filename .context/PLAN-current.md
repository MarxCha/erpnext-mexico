# PLAN-current — Sprint 0: Fundación (Semanas 1-3)

## Objetivo
App instalable con DocTypes de configuración, catálogos SAT cargados, custom fields visibles y CI/CD funcionando.

## Hallazgos Técnicos (validados con Gemini)
- **satcfdi incluye catálogos embebidos** via SQLite: `satcfdi.catalogs`
  - `catalogs.select('c_ClaveProdServ', '84111506')` → datos del producto
  - `catalogs.select('c_CodigoPostal', '06000')` → info CP
  - **DECISIÓN**: Usar satcfdi.catalogs para poblar DocTypes, NO descargar Excel del SAT
- **Pagos 2.0 completamente soportado**: `from satcfdi.create.cfd.pago20 import Pagos, Pago, DoctoRelacionado`

## Tareas por Fase

### Fase A: Infraestructura (días 1-2)
1. [ ] **BLOCKER-004**: Configurar entorno Frappe local
   - Opción 1: Docker (`frappe/frappe_docker`)
   - Opción 2: bench nativo con pyenv (Python 3.11)
   - **Owner**: /bootstrap-v2
   - **Criterio**: `bench start` funciona, ERPNext accesible en localhost:8000

2. [ ] **BLOCKER-002**: Obtener CSD de prueba SAT
   - RFC: EKU9003173C9 (persona moral)
   - Password: 12345678a
   - Fuente: portal SAT pruebas o incluidos en satcfdi
   - **Owner**: Marx (manual)

3. [ ] Git init + pyproject.toml + LICENSE GPL-3.0 + .gitignore
   - **Owner**: /backend

### Fase B: DocTypes de Configuración (días 3-6)
4. [ ] DocType JSON: **MX CFDI Settings** (Single)
   - Tabs: General | PAC | Certificados
   - Campos: pac_provider, pac_credentials (Link), pac_environment, auto_stamp_on_submit, company
   - depends_on progresivo (patrón India Compliance)
   - **Owner**: /architect + /backend

5. [ ] DocType JSON: **MX Digital Certificate**
   - Campos: company, rfc, certificate_file (.cer), key_file (.key), password (Password)
   - Read-only auto-parsed: certificate_number, valid_from, valid_to, status
   - Controller: on_save → parsear .cer con satcfdi, validar expiry
   - **Owner**: /backend

6. [ ] DocType JSON: **MX PAC Credentials**
   - Campos: pac_name (Select), username, password (Password), is_sandbox
   - **Owner**: /backend

7. [ ] DocType JSON: **MX CFDI Log**
   - Campos: reference_doctype (Link to DocType), reference_name (Dynamic Link)
   - cfdi_type (I/E/T/N/P), uuid, status, xml_signed, xml_stamped
   - pac_used, error_message, stamped_at, cancelled_at
   - **Owner**: /backend

### Fase C: Catálogos SAT (días 7-10)
8. [ ] 15 DocType JSONs de catálogos (schema: code, description, valid_from, valid_to)
   - Pequeños (fixtures JSON): MX Fiscal Regime, MX Payment Form, MX Payment Method, MX CFDI Use, MX Tax Object, MX Export Type, MX Cancellation Reason, MX Relation Type, MX Voucher Type, MX Tax Type, MX Tax Factor Type
   - Pesados (catalog_importer): MX Product Service Key, MX Unit Key, MX Postal Code, MX Currency SAT
   - **Owner**: /database + /backend

9. [ ] catalog_importer.py
   - Usar `satcfdi.catalogs` como fuente primaria (NO Excel)
   - `frappe.db.bulk_insert(chunk_size=20_000)` para catálogos pesados
   - Fallback: parsear Excel del SAT si satcfdi no tiene todos los campos
   - **Owner**: /database

10. [ ] Fixtures JSON para catálogos pequeños (<100 registros)
    - Generar desde satcfdi.catalogs → JSON → sat_catalogs/fixtures/
    - **Owner**: /backend

### Fase D: Custom Fields + Setup (días 11-13)
11. [ ] Validar install.py en bench real
    - `bench --site dev.localhost install-app erpnext_mexico`
    - Verificar custom fields aparecen en formularios
    - **Owner**: /backend

12. [ ] property_setters.py (modificar campos existentes ERPNext)
    - **Owner**: /backend

13. [ ] Chart of Accounts mexicano (mexico_standard.json)
    - Basado en código agrupador SAT (Anexo 24)
    - Subcuentas IVA: acreditable, por acreditar, trasladado, por trasladar
    - **Owner**: /database

14. [ ] Tax Templates: IVA 16%, IVA 0%, IVA exento, ISR ret 10%, IVA ret 10.6667%
    - **Owner**: /backend

### Fase E: CI + Tests (días 14-15)
15. [ ] GitHub Actions: ruff lint + pytest
    - **Owner**: /backend

16. [ ] Tests unitarios:
    - rfc_validator.py: personas física/moral, genéricos, dígito verificador
    - Catálogos cargados: verify_count de registros
    - Custom fields existence en DocTypes target
    - install/uninstall cycle
    - **Owner**: /test-v2

17. [ ] .pre-commit-config.yaml (ruff + mypy)
    - **Owner**: /backend

## Criterios de Completitud Sprint 0
- [ ] `bench install-app erpnext_mexico` sin errores
- [ ] `bench migrate` sin errores
- [ ] 19 DocTypes creados (4 config + 15 catálogos)
- [ ] Catálogos SAT cargados (al menos pequeños, pesados via bench execute)
- [ ] Custom fields visibles en Company, Customer, Supplier, Item, Sales Invoice
- [ ] MX CFDI Settings permite configurar PAC
- [ ] MX Digital Certificate parsea .cer
- [ ] CI verde en GitHub (lint + tests)
- [ ] CSD de prueba disponible para Sprint 1

## Blockers Pre-Sprint
| ID | Blocker | Status | ETA |
|---|---------|--------|-----|
| B-004 | Entorno Frappe local | 🔴 Pendiente | Día 1-2 |
| B-002 | CSD prueba SAT | 🔴 Pendiente | Día 1 |
| B-001 | Sandbox Finkok | 🟡 No bloquea Sprint 0 | Pre-Sprint 1 |
| B-003 | Catálogos SAT | ✅ Resuelto (satcfdi.catalogs) | - |
