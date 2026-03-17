# FISCAL-REQUIREMENTS — Requisitos Fiscales Mexicanos

## 1. CFDI 4.0 (Comprobante Fiscal Digital por Internet)

### Estructura XML
- Namespace: `http://www.sat.gob.mx/cfd/4`
- XSD: `http://www.sat.gob.mx/sitio_internet/cfd/4/cfdv40.xsd`
- XSLT cadena original: `http://www.sat.gob.mx/sitio_internet/cfd/4/cadenaoriginal_4_0/cadenaoriginal_4_0.xslt`

### Nodo Comprobante (atributos obligatorios)
| Atributo | Tipo | Descripción |
|---|---|---|
| Version | xs:string | Siempre "4.0" |
| Fecha | xs:dateTime | ISO 8601, máx 72h antes del timbrado |
| Sello | xs:string | Base64 RSA-SHA256 de cadena original |
| FormaPago | catCFDI:c_FormaPago | "01"=Efectivo, "03"=Transferencia, etc. |
| NoCertificado | xs:string | 20 dígitos del CSD |
| Certificado | xs:string | Base64 del .cer |
| SubTotal | tdCFDI:t_Importe | Suma de importes de conceptos |
| Descuento | tdCFDI:t_Importe | Opcional, suma descuentos |
| Moneda | catCFDI:c_Moneda | "MXN", "USD", etc. |
| TipoCambio | xs:decimal | Obligatorio si Moneda ≠ MXN |
| Total | tdCFDI:t_Importe | SubTotal - Descuento + Traslados - Retenciones |
| TipoDeComprobante | catCFDI:c_TipoDeComprobante | I/E/T/N/P |
| Exportacion | catCFDI:c_Exportacion | "01"=No aplica (default), "02"/"03"/"04" |
| MetodoPago | catCFDI:c_MetodoPago | "PUE" o "PPD" |
| LugarExpedicion | catCFDI:c_CodigoPostal | CP del domicilio fiscal emisor |
| Confirmacion | xs:string | Solo si Total > $2,000,000,000 MXN o TC fuera de rango |

### Nodo Emisor
| Campo | Obligatorio | Descripción |
|---|---|---|
| Rfc | ✅ | 12 (moral) o 13 (física) caracteres |
| Nombre | ✅ | DEBE coincidir con registro SAT exactamente |
| RegimenFiscal | ✅ | Catálogo c_RegimenFiscal (e.g., "601"=General Ley) |

### Nodo Receptor
| Campo | Obligatorio | Descripción |
|---|---|---|
| Rfc | ✅ | Receptor RFC o "XAXX010101000" (público general) |
| Nombre | ✅ | DEBE coincidir con SAT |
| DomicilioFiscalReceptor | ✅ | Código postal del receptor |
| RegimenFiscalReceptor | ✅ | Régimen del receptor |
| UsoCFDI | ✅ | "G01"=Adquisición mercancías, "G03"=Gastos general, etc. |

### Nodo Concepto (por cada línea)
| Campo | Obligatorio | Descripción |
|---|---|---|
| ClaveProdServ | ✅ | c_ClaveProdServ (UNSPSC, 55K+ claves) |
| NoIdentificacion | Opcional | Código interno del producto |
| Cantidad | ✅ | Decimal ≥ 0.000001 |
| ClaveUnidad | ✅ | c_ClaveUnidad ("H87"=Pieza, "E48"=Servicio, etc.) |
| Unidad | Opcional | Texto libre de la unidad |
| Descripcion | ✅ | Texto libre |
| ValorUnitario | ✅ | Precio unitario antes de descuento |
| Importe | ✅ | Cantidad × ValorUnitario (hasta 6 decimales) |
| Descuento | Opcional | Por concepto |
| ObjetoImp | ✅ | "01"=No sujeto, "02"=Sí sujeto, "03"=Sí sin desglose |

### Impuestos por Concepto (dentro de Concepto/Impuestos/Traslados)
| Campo | Descripción |
|---|---|
| Base | Importe - Descuento del concepto |
| Impuesto | "002"=IVA, "003"=IEPS |
| TipoFactor | "Tasa", "Cuota", "Exento" |
| TasaOCuota | "0.160000" para IVA 16%, 6 decimales |
| Importe | Base × TasaOCuota (redondeado a 2 decimales) |

### Proceso de Sellado
1. Generar XML sin Sello
2. Aplicar XSLT oficial → cadena original (texto plano)
3. Hash SHA-256 de cadena original
4. Firmar hash con llave privada RSA del CSD (.key)
5. Codificar firma en Base64 → atributo Sello
6. Incluir certificado .cer en Base64 → atributo Certificado

### Validaciones del PAC al timbrar
- Estructura XML válida contra XSD
- CSD vigente y no revocado
- Sello correcto (refirmar para verificar)
- RFC emisor coincide con CSD
- Nombre emisor/receptor coincide con LRFC del SAT
- Valores de catálogos válidos y vigentes
- Reglas de negocio (UsoCFDI vs RegimenFiscal compatible)
- No duplicado (mismo RFC emisor + RFC receptor + Total + UUID de concepto + fecha)

---

## 2. Complemento de Pagos 2.0

### Cuándo se usa
- Factura original tipo "I" con MetodoPago="PPD" y FormaPago="99"
- Al recibir cada pago: CFDI tipo "P" con complemento

### Estructura del CFDI tipo "P"
```
Comprobante
  TipoDeComprobante="P"
  Total="0"
  SubTotal="0"
  Moneda="XXX"
  MetodoPago=NO SE INCLUYE
  FormaPago=NO SE INCLUYE
  Conceptos
    Concepto
      ClaveProdServ="84111506"
      ClaveUnidad="ACT"
      Cantidad="1"
      Descripcion="Pago"
      ValorUnitario="0"
      Importe="0"
  Complemento
    pago20:Pagos
      pago20:Totales (NUEVO en 2.0)
        TotalRetencionesIVA, TotalRetencionesISR, TotalRetencionesIEPS
        TotalTrasladosBaseIVA16, TotalTrasladosImpuestoIVA16, etc.
      pago20:Pago
        FechaPago (xs:dateTime)
        FormaDePagoP (c_FormaPago, e.g., "03")
        MonedaP ("MXN")
        Monto (total pagado)
        pago20:DoctoRelacionado (1 por factura pagada)
          IdDocumento (UUID factura original)
          Serie, Folio
          MonedaDR, EquivalenciaDR
          NumParcialidad (secuencial: 1, 2, 3...)
          ImpSaldoAnt (saldo antes de este pago)
          ImpPagado (monto aplicado a esta factura)
          ImpSaldoInsoluto (ImpSaldoAnt - ImpPagado)
          ObjetoImpDR
          pago20:ImpuestosDR (desglose por DoctoRelacionado)
          pago20:ImpuestosP (resumen por Pago)
```

### Reglas de negocio
- ∑ ImpPagado de todos los DoctoRelacionado = Monto del Pago
- ImpSaldoInsoluto = ImpSaldoAnt - ImpPagado (exacto)
- NumParcialidad debe ser secuencial por UUID de factura
- Plazo: emitir a más tardar el día 5 del mes siguiente al pago

---

## 3. Nómina Electrónica 1.2 Revisión E (vigente enero 2026)

### Estructura
CFDI tipo "N" + Complemento de Nómina:
```
Comprobante TipoDeComprobante="N"
  Concepto ClaveProdServ="84111505" ClaveUnidad="ACT"
    (un solo concepto; SubTotal = TotalPercepciones + TotalOtrosPagos)
    (Descuento = TotalDeducciones)
  Complemento
    nomina12:Nomina
      Version="1.2"
      TipoNomina="O" (Ordinaria) / "E" (Extraordinaria)
      FechaPago, FechaInicialPago, FechaFinalPago
      NumDiasPagados
      TotalPercepciones, TotalDeducciones, TotalOtrosPagos
      
      nomina12:Emisor
        RegistroPatronal (del IMSS, 11 caracteres)
        
      nomina12:Receptor
        Curp, NumSeguridadSocial, FechaInicioRelLaboral
        Antigüedad (ISO 8601 duration: "P5Y3M")
        TipoContrato, TipoRegimen, TipoJornada, RiesgoDelPuesto
        PeriodicidadPago, Banco, CuentaBancaria, SalarioBaseCotApor
        SalarioDiarioIntegrado, ClaveEntFed, NumEmpleado
      
      nomina12:Percepciones
        TotalSueldos, TotalGravado, TotalExento
        nomina12:Percepcion (tipo, clave, concepto, importeGravado, importeExento)
          TipoPercepcion: 001=Sueldos, 002=Gratificación anual (aguinaldo)
            003=PTU, 004=Reembolsos, 005=Fondo ahorro, 019=Horas extra
            025=Prima vacacional, 039=Jubilación, 054/055=Días descanso (nuevo Rev E)
      
      nomina12:Deducciones
        TotalOtrasDeducciones, TotalImpuestosRetenidos
        nomina12:Deduccion (tipo, clave, concepto, importe)
          TipoDeduccion: 001=Seguridad social, 002=ISR
            004=Otros, 005=Aportación INFONAVIT, 006=Descuento INFONAVIT
            108-111=Nuevas claves Rev E
      
      nomina12:OtrosPagos
        nomina12:OtroPago
          TipoOtroPago: 002=Subsidio al empleo (con SubsidioAlEmpleo)
```

### Cálculos ISR (Art. 96 LISR)
1. Base gravable mensual = ∑ percepciones gravadas del periodo × factor de proporción mensual
2. Buscar en tabla tarifaria: LímiteInferior, LímiteSuperior, CuotaFija, TasaSobreExcedente
3. ISR = CuotaFija + (BaseGravable - LímiteInferior) × TasaSobreExcedente
4. Subsidio al empleo = cuota fija según tabla (máx $628 MXN mensual en 2026)
5. ISR a retener = ISR - Subsidio (si > 0)

### Cuotas IMSS Obrero (porcentajes 2026 sobre SBC)
| Rama | Cuota Obrero |
|---|---|
| Enfermedades y Maternidad (prestaciones en especie) | 0.40% |
| Enfermedades y Maternidad (gastos médicos pensionados) | 0.375% |
| Enfermedades y Maternidad (prestaciones en dinero) | 0.250% |
| Invalidez y Vida | 0.625% |
| Retiro | 0% (solo patronal) |
| Cesantía en Edad Avanzada y Vejez | 1.125% |
| Guarderías | 0% (solo patronal) |
| **Total obrero aprox** | **~2.775%** |

Tope SBC: 25 × UMA mensual (~$85,755 MXN en 2026)

---

## 4. DIOT 2025 (formato TXT 54 campos)

### Formato
- Delimitador: pipe `|`
- Encoding: UTF-8
- Una línea por proveedor por periodo

### Campos principales (54 total)
| # | Campo | Descripción |
|---|---|---|
| 1 | TipoTercero | 04=Nacional, 05=Extranjero, 15=Global |
| 2 | TipoOperacion | 03=Servicios profesionales, 06=Arrendamiento, 85=Otros |
| 3 | RFC | Del proveedor (13 chars) |
| 4 | IDFiscal | Para extranjeros |
| 5 | NombreExtranjero | Si aplica |
| 6 | PaisResidencia | Para extranjeros |
| 7 | Nacionalidad | Para extranjeros |
| 8-54 | Valores | Desglose por tasa IVA (16%, 8%, 0%, exento, no objeto) |

### Generación
1. Consultar Purchase Invoices del mes
2. Agrupar por RFC de proveedor
3. Clasificar montos por tasa de IVA
4. Generar línea TXT por proveedor
5. Validar totales contra contabilidad

---

## 5. Carta Porte 3.1

### Aplicabilidad
- Transporte de mercancías en vías federales
- CFDI tipo "T" (traslado propio) o tipo "I" (transporte contratado)

### Nodos principales
```
CartaPorte Version="3.1"
  IdCCP (UUID)
  TranspInternac="No"
  Ubicaciones
    Ubicacion TipoEstacion="01" (Origen)
      Domicilio (Calle, NumExt, Colonia, Localidad, Municipio, Estado, País, CP)
      FechaHoraSalidaLlegada
    Ubicacion TipoEstacion="02" (Destino)
      DistanciaRecorrida (KM obligatorio)
  Mercancias PesoBrutoTotal UnidadPeso
    Mercancia
      BienesTransp (c_ClaveProdServCP)
      Descripcion, Cantidad, ClaveUnidad, PesoEnKg
      MaterialPeligroso, CveMaterialPeligroso (si aplica)
  Autotransporte
    PermSCT, NumPermisoSCT
    IdentificacionVehicular (ConfigVehicular, PesoBruto, PlacaVM, AnioModeloVM)
    Seguros (AseguraRespCivil, PolizaRespCivil, AseguraCarga, PolizaCarga)
    Remolques (SubTipoRem, Placa) — máx 2
  FiguraTransporte
    TiposFigura
      TipoFigura="01" (Operador)
      RFCFigura, NumLicencia, NombreFigura
```

---

## 6. Contabilidad Electrónica (Anexo 24)

### Catálogo de Cuentas (CT)
```xml
<Catalogo Version="1.3" RFC="..." Mes="01" Anio="2026">
  <Ctas CodAgworldn="100" NumCta="1000" Desc="Activo" SubCtaDe="" Nivel="1" Natur="D"/>
  <Ctas CodAgrup="101" NumCta="1010" Desc="Caja" SubCtaDe="1000" Nivel="2" Natur="D"/>
</Catalogo>
```
- Se envía al inicio y cada vez que se modifica una cuenta de primer nivel
- CodAgrup = código agrupador del SAT (catálogo oficial)

### Balanza de Comprobación (BN)
```xml
<Balanza Version="1.3" RFC="..." Mes="01" Anio="2026" TipoEnvio="N">
  <Ctas NumCta="1010" SaldoIni="50000.00" Debe="15000.00" Haber="8000.00" SaldoFin="57000.00"/>
</Balanza>
```
- Mensual, 3er día hábil del 2do mes siguiente (PM) / 5to día hábil (PF)

### Pólizas (PL) — Solo bajo requerimiento SAT
```xml
<Polizas Version="1.3" RFC="..." Mes="01" Anio="2026" TipoSolicitud="AF">
  <Poliza NumUnIdenPol="1" Fecha="2026-01-15" Concepto="Venta mercancía">
    <Transaccion NumCta="4010" DesCta="Ventas" Debe="0" Haber="10000.00">
      <CompNal UUID_CFDI="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" MontoTotal="10000.00"/>
    </Transaccion>
  </Poliza>
</Polizas>
```

---

## 7. Cancelación de CFDI

### Motivos (c_MotivoCancel)
| Código | Motivo | ¿Requiere UUID sustituto? |
|---|---|---|
| 01 | Comprobante emitido con errores con relación | ✅ (UUID del CFDI sustituto) |
| 02 | Comprobante emitido con errores sin relación | ❌ |
| 03 | No se llevó a cabo la operación | ❌ |
| 04 | Operación nominativa (nombre en CFDI global) | ❌ |

### Flujo
1. Emisor solicita cancelación vía PAC (con motivo + UUID sustituto si aplica)
2. Si factura > $1,000 MXN y receptor ≠ público general → requiere aceptación del receptor
3. Receptor tiene 3 días hábiles para aceptar/rechazar
4. Si no responde → se cancela automáticamente
5. Facturas < $1,000 MXN o a público general → cancelación inmediata

### Excepciones a aceptación del receptor
- Facturas tipo N (nómina)
- Facturas tipo E (egreso/nota de crédito)
- Facturas tipo T (traslado)
- Facturas tipo P (pago)
- Facturas emitidas al RFC genérico XAXX010101000
- Facturas con monto ≤ $1,000 MXN
