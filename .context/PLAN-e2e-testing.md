# PLAN — Pruebas E2E Integrales: ERPNext Mexico

**Fecha**: 2026-03-19
**Objetivo**: Validar TODOS los flujos de negocio punta a punta, simulando el uso real de una empresa mexicana

---

## Filosofía

No tests aislados. Cada flujo E2E recorre el camino completo que haría un usuario real:
configurar → crear datos → ejecutar operación → verificar resultado → validar archivos generados.

Los flujos se encadenan: la factura del Flujo 1 se usa en el Flujo 2 (pagos), etc.

---

## Sprint T1: Setup & Configuración Base (Prerequisito)
**Duración**: ~10 min | **Herramienta**: Playwright + bench console

### Flujo 0: Configuración inicial de empresa mexicana
1. Verificar Company "MD Consultoria TI" existe con country=Mexico, currency=MXN
2. Configurar datos fiscales: RFC, Nombre Fiscal, Régimen Fiscal, CP
3. Verificar MX CFDI Settings: PAC=Finkok, sandbox=true, auto_stamp=true
4. Verificar MX PAC Credentials: Finkok con credenciales
5. Verificar MX Digital Certificate: EKU9003173C9 con CSD cargado
6. Crear Customer de prueba con datos mx_* (RFC receptor, uso CFDI, forma pago)
7. Crear Supplier de prueba con datos mx_* (RFC, tipo tercero DIOT)
8. Crear Item de prueba con mx_clave_prod_serv y mx_clave_unidad
9. Verificar catálogos SAT tienen datos (al menos los fixtures pequeños)

**Criterio**: Todos los datos base existen y son válidos para timbrar

---

## Sprint T2: CFDI Facturación (Flujo principal)
**Duración**: ~20 min | **Herramienta**: Playwright + API + bench

### Flujo 1: Factura de Ingreso (tipo I) — PUE
1. Crear Sales Invoice con customer de prueba
2. Verificar campos mx_* auto-populados (uso CFDI, forma pago del customer)
3. Asignar método pago PUE, forma pago "01" (Efectivo)
4. Submit → debe intentar timbrado automático contra Finkok sandbox
5. Verificar: mx_cfdi_uuid populated, mx_cfdi_status = "Timbrado"
6. Verificar: mx_xml_file adjunto (descargar y validar XML estructura)
7. Verificar: MX CFDI Log creado con datos del timbrado
8. Verificar: Print Format CFDI renderiza correctamente

### Flujo 2: Factura PPD (Pago en Parcialidades)
1. Crear Sales Invoice con método pago PPD
2. Verificar forma_pago = "99" (Por definir)
3. Submit → timbrado
4. Verificar UUID y status

### Flujo 3: Nota de Crédito (tipo E)
1. Crear Return/Credit Note desde Flujo 1
2. Verificar tipo comprobante "E" y relación con UUID original
3. Submit → timbrado
4. Verificar UUID propio

### Flujo 4: Retry de timbrado
1. Simular factura con mx_cfdi_status = "Error"
2. Ejecutar retry_stamp via API
3. Verificar rate limiting funciona (>5 intentos en 60s = bloqueado)

---

## Sprint T3: Complemento de Pagos 2.0
**Duración**: ~15 min

### Flujo 5: Pago completo (PUE linked)
1. Crear Payment Entry ligado a factura PPD del Flujo 2
2. Asignar mx_forma_pago SAT
3. Submit → debe generar complemento de pago
4. Verificar: mx_pago_uuid, mx_pago_xml, mx_pago_status = "Timbrado"
5. Verificar: XML del complemento tiene DoctoRelacionado correcto

### Flujo 6: Pago parcial
1. Crear Payment Entry parcial sobre factura PPD
2. Verificar parcialidad correcta en XML

---

## Sprint T4: Cancelación CFDI
**Duración**: ~10 min

### Flujo 7: Cancelación con sustitución (motivo 01)
1. Tomar factura de Flujo 3 (nota de crédito)
2. Ejecutar cancel_cfdi con motivo "01" y UUID sustituto
3. Verificar: mx_cfdi_status = "Cancelado", mx_cancellation_reason = "01"
4. Verificar: MX CFDI Log actualizado

### Flujo 8: Cancelación sin sustitución (motivo 02)
1. Tomar factura de prueba
2. Cancelar con motivo "02"
3. Verificar status

---

## Sprint T5: Nómina Electrónica 1.2
**Duración**: ~15 min | **Nota**: Requiere HRMS o mock

### Flujo 9: Nómina ordinaria
1. Verificar Employee tiene campos mx_* (CURP, NSS, RFC, tipo contrato)
2. Crear Salary Slip
3. Asignar mx_tipo_nomina = "O"
4. Submit → timbrado CFDI nómina
5. Verificar: mx_nomina_uuid, mx_nomina_xml
6. Verificar: XML tiene percepciones, deducciones, ISR, IMSS correctos

**Nota**: Si HRMS no está instalado, este flujo se testea solo a nivel de builder (sin submit real)

---

## Sprint T6: Carta Porte 3.1
**Duración**: ~10 min

### Flujo 10: Delivery Note con Carta Porte
1. Crear Delivery Note con mx_requires_carta_porte = true
2. Llenar datos: origen, destino, vehículo, conductor
3. Submit → timbrado complemento Carta Porte
4. Verificar: mx_carta_porte_uuid, mx_carta_porte_xml
5. Verificar: XML tiene ubicaciones, mercancías, autotransporte

---

## Sprint T7: DIOT 2025
**Duración**: ~10 min

### Flujo 11: Generación DIOT
1. Crear Purchase Invoices de prueba (nacional + extranjero)
2. Asignar datos mx_* en suppliers (tipo tercero, RFC, NIT)
3. Ejecutar generate_diot(company, month, year)
4. Verificar: TXT generado con 54 campos pipe-separated
5. Verificar: totales IVA cuadran con facturas
6. Ejecutar download_diot → verificar descarga archivo

---

## Sprint T8: Contabilidad Electrónica (Anexo 24)
**Duración**: ~10 min

### Flujo 12: Catálogo de Cuentas XML
1. Ejecutar generate_catalog_xml(company, year, month)
2. Verificar: XML válido con namespace SAT
3. Verificar: cuentas tienen código agrupador SAT

### Flujo 13: Balanza de Comprobación XML
1. Ejecutar generate_balanza_xml(company, year, month)
2. Verificar: XML con saldos iniciales, cargos, abonos, final

### Flujo 14: Pólizas del Período XML
1. Ejecutar generate_polizas_xml(company, year, month)
2. Verificar: XML con pólizas del período

---

## Sprint T9: UI & UX Validation (Playwright)
**Duración**: ~15 min

### Flujo 15: Navegación completa
1. Login → Home
2. Navegar a MX CFDI Settings → verificar tabs y campos
3. Navegar a Company → verificar sección "Datos Fiscales México"
4. Navegar a Customer → verificar campos mx_*
5. Navegar a Sales Invoice (new) → verificar campos CFDI
6. Navegar a MX Fiscal Dashboard → verificar métricas renderizan
7. Navegar a MX Setup Wizard → verificar pasos
8. Zero console errors (excepto socket.io esperado)

---

## Sprint T10: Auditoría Final
**Duración**: ~10 min

### Verificaciones cruzadas
1. Todos los tests unitarios pasan (196/196)
2. Todos los endpoints tienen rate limiting
3. PII sanitization activa en logs PAC
4. CSP headers en respuestas de páginas MX
5. No hay archivos huérfanos o imports rotos
6. Catálogos SAT cargados correctamente

---

## Asignación de Recursos

| Sprint | Agente(s) | Tool |
|--------|-----------|------|
| T1 | bench console + Playwright | Setup data |
| T2-T4 | general-purpose (API calls in Docker) | Timbrado E2E |
| T5-T6 | general-purpose (builders sin HRMS) | Nómina/Carta Porte |
| T7-T8 | general-purpose (generators) | DIOT/Contabilidad |
| T9 | Playwright MCP | Visual validation |
| T10 | security-reviewer | Final audit |

## Orden de Ejecución

```
T1 (Setup) → T2 (Facturación) → T3 (Pagos) → T4 (Cancelación)
                                                      ↓
T5 (Nómina) + T6 (Carta Porte) ← paralelo → T7 (DIOT) + T8 (Contabilidad)
                                                      ↓
                                              T9 (UI) → T10 (Auditoría)
```
