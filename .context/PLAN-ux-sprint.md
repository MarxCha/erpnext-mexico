# PLAN UX/UI — ERPNext México Design System + Dashboard

## Objetivo
Crear un design system diferenciado y un dashboard fiscal interactivo para ERPNext México.
Inspirado en: Marvilo (dark bold), Carbonteq (light clean), Opndoo (ERP tables).

## Sprints

### Sprint UX-1: Design System Foundation (CSS + Typography)
- Custom CSS variables (colores, spacing, radii, shadows)
- Tipografía: DM Sans (headings) + Source Sans 3 (body)
- Status pills component (Timbrado, Pendiente, Error, Cancelado)
- Card component reutilizable (metric cards)
- Dark mode toggle support
- **Output**: `public/css/erpnext_mexico.css`

### Sprint UX-2: Fiscal Dashboard Page
- Custom Frappe Page: "mx-fiscal-dashboard"
- Cards métricas: CFDIs timbrados, pendientes, errores, monto facturado
- Gráfica de CFDIs por mes (frappe.Chart)
- Lista rápida de últimos 10 CFDIs con status pills
- Accesos rápidos: MX CFDI Settings, catálogos, DIOT
- **Output**: `erpnext_mexico/mx_fiscal_dashboard/`

### Sprint UX-3: Setup Wizard Page
- Wizard step-by-step para primera configuración fiscal
- Steps: Empresa → RFC/Régimen → CSD Upload → PAC Config → Verificación
- Progress bar visual, validación en cada step
- **Output**: `erpnext_mexico/mx_setup_wizard/`

### Sprint UX-4: Enhanced Components
- CFDI Log list view mejorada con status pills + filtros
- Catalog search overlay (typeahead para c_ClaveProdServ)
- Sales Invoice CFDI panel mejorado (visual status card)
- **Output**: Updates a JS existentes + nuevos componentes

## Recursos Asignados

| Agent | Responsabilidad | Archivos owns |
|---|---|---|
| Agent 1: Design System | CSS, variables, componentes base | public/css/, public/fonts/ |
| Agent 2: Dashboard | Frappe Page Python + Jinja + JS | mx_fiscal_dashboard/ |
| Agent 3: Wizard | Setup wizard page completa | mx_setup_wizard/ |
| Agent 4: Components | Status pills, CFDI panel, catalog search | public/js/, list views |

## Verificación
- [ ] CSS carga sin errores en Frappe
- [ ] Dashboard renderiza con datos mock
- [ ] Wizard completa los 5 steps
- [ ] Status pills visibles en CFDI Log listview
- [ ] bench build exitoso
