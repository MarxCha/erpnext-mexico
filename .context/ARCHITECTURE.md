# ARCHITECTURE — ERPNext México

> **NOTA**: payroll/ y carta_porte/ son **POST-MVP** (DEC-008, DEC-009).
> No implementar en Sprints 0-6. Ver SPRINT-PLAN.md para el alcance del MVP.

## Visión General

```
┌─────────────────────────────────────────────────────┐
│                    ERPNext Core                       │
│  Sales Invoice │ Payment Entry │ Purchase Inv │ DN   │
└──────┬──────────┬──────────────┬─────────────┬──────┘
       │          │              │             │
       ▼          ▼              ▼             ▼
┌─────────────────────────────────────────────────────┐
│              erpnext_mexico (Frappe App)              │
│                                                       │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────────┐ │
│  │  CFDI    │ │ Pagos    │ │  DIOT  │ │Cont.Elec. │ │ ← MVP
│  │  Core    │ │   2.0    │ │  2025  │ │ Anexo 24  │ │
│  └────┬─────┘ └────┬─────┘ └───┬────┘ └─────┬─────┘ │
│       │             │           │             │       │
│  ┌────▼─────────────▼───────────▼─────────────▼────┐ │
│  │          Catálogos SAT (15+ DocTypes)            │ │
│  │          Fuente: satcfdi.catalogs (SQLite)       │ │
│  └─────────────────────┬───────────────────────────┘ │
│                        │                              │
│  ┌─────────────────────▼───────────────────────────┐ │
│  │         PAC Dispatcher (Strategy Pattern)        │ │
│  │    ┌─────────┐  ┌──────────┐                    │ │
│  │    │ Finkok  │  │SW Sapien │                    │ │
│  │    └────┬────┘  └────┬─────┘                    │ │
│  └─────────┼────────────┼──────────────────────────┘ │
│            └────────────┘                             │
│                         ▼                             │
│  ┌──────────────────────────────────────────────────┐ │
│  │         satcfdi (Python Library)                  │ │
│  │  XML Builder │ CSD Signer │ PAC Client │ PDF Gen │ │
│  └──────────────────────────────────────────────────┘ │
│                                                       │
│  ┌─ POST-MVP ─────────────────────────────────────┐  │
│  │  Nómina 1.2 Rev E │ Carta Porte 3.1            │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Estructura de Directorios

```
erpnext_mexico/
├── pyproject.toml
├── setup.py
├── requirements.txt              # satcfdi>=4.8.0
├── license.txt                   # GPL-3.0
├── README.md
│
├── erpnext_mexico/
│   ├── __init__.py              # __version__
│   ├── hooks.py                 # Configuración central
│   ├── install.py               # after_install: custom fields + fixtures
│   ├── uninstall.py             # cleanup
│   ├── modules.txt              # Lista de módulos
│   ├── patches.txt              # Migraciones
│   │
│   ├── cfdi/                    # ═══ MÓDULO 1: CFDI CORE ═══
│   │   ├── __init__.py
│   │   ├── doctype/
│   │   │   ├── mx_cfdi_settings/
│   │   │   │   ├── mx_cfdi_settings.json    # Schema
│   │   │   │   ├── mx_cfdi_settings.py      # Controller
│   │   │   │   └── mx_cfdi_settings.js      # Form script
│   │   │   ├── mx_digital_certificate/
│   │   │   │   ├── mx_digital_certificate.json
│   │   │   │   └── mx_digital_certificate.py  # Parse .cer, validate
│   │   │   ├── mx_cfdi_log/
│   │   │   │   ├── mx_cfdi_log.json
│   │   │   │   └── mx_cfdi_log.py
│   │   │   └── mx_pac_credentials/
│   │   │       ├── mx_pac_credentials.json
│   │   │       └── mx_pac_credentials.py
│   │   │
│   │   ├── xml_builder.py       # Genera XML CFDI 4.0 via satcfdi
│   │   ├── xml_signer.py        # Firma con CSD via satcfdi
│   │   ├── pac_interface.py     # ABC para PACs
│   │   ├── pac_dispatcher.py    # Strategy Pattern selector
│   │   ├── pacs/
│   │   │   ├── __init__.py
│   │   │   ├── finkok_pac.py    # Wrapper satcfdi.pacs.finkok
│   │   │   ├── sw_sapien_pac.py # Wrapper satcfdi.pacs.sw_sapien
│   │   │   └── # facturama_pac.py — NO en MVP (solo Finkok + SW Sapien)
│   │   │
│   │   ├── cancellation.py      # Flujo cancelación motivos 01-04
│   │   ├── tasks.py             # Scheduler: check status, cert expiry
│   │   ├── utils.py             # RFC validation, rounding rules
│   │   └── tests/
│   │       ├── test_xml_builder.py
│   │       ├── test_stamp_cycle.py
│   │       └── test_cancellation.py
│   │
│   ├── sat_catalogs/            # ═══ MÓDULO 2: CATÁLOGOS SAT ═══
│   │   ├── __init__.py
│   │   ├── doctype/
│   │   │   ├── mx_fiscal_regime/          # c_RegimenFiscal (~20 regs)
│   │   │   ├── mx_payment_form/           # c_FormaPago (~30 regs)
│   │   │   ├── mx_payment_method/         # c_MetodoPago (PUE/PPD)
│   │   │   ├── mx_cfdi_use/              # c_UsoCFDI (~25 regs)
│   │   │   ├── mx_product_service_key/    # c_ClaveProdServ (55K+ regs)
│   │   │   ├── mx_unit_key/              # c_ClaveUnidad (~2,300 regs)
│   │   │   ├── mx_postal_code/           # c_CodigoPostal (70K regs)
│   │   │   ├── mx_currency/              # c_Moneda (~180 regs)
│   │   │   ├── mx_tax_object/            # c_ObjetoImp (01/02/03)
│   │   │   ├── mx_export_type/           # c_Exportacion (01/02/03/04)
│   │   │   ├── mx_cancellation_reason/    # c_MotivoCancel (01-04)
│   │   │   ├── mx_relation_type/         # c_TipoRelacion
│   │   │   ├── mx_voucher_type/          # c_TipoDeComprobante (I/E/T/N/P)
│   │   │   ├── mx_tax_type/             # c_Impuesto (001/002/003)
│   │   │   └── mx_tax_factor_type/       # c_TipoFactor (Tasa/Cuota/Exento)
│   │   │
│   │   ├── catalog_importer.py  # Importa desde satcfdi.catalogs (SQLite). Fallback: Excel SAT
│   │   ├── fixtures/            # JSON pre-generados para catálogos pequeños
│   │   │   ├── mx_fiscal_regime.json
│   │   │   ├── mx_payment_form.json
│   │   │   ├── mx_payment_method.json
│   │   │   ├── mx_cfdi_use.json
│   │   │   └── ...
│   │   └── data/                # Excel originales del SAT (no en repo, .gitignore)
│   │       └── .gitkeep
│   │
│   ├── invoicing/               # ═══ MÓDULO 3: FACTURACIÓN ═══
│   │   ├── __init__.py
│   │   ├── overrides/
│   │   │   ├── sales_invoice.py     # validate + on_submit (→ stamp)
│   │   │   ├── purchase_invoice.py  # XML import + SAT validation
│   │   │   └── payment_entry.py     # on_submit (→ Complemento Pagos 2.0)
│   │   ├── payment_complement.py    # Lógica PPD: parcialidades, saldos
│   │   ├── credit_note.py          # CFDI tipo E con TipoRelacion
│   │   ├── global_invoice.py       # Factura global (InformacionGlobal)
│   │   └── tests/
│   │       ├── test_sales_invoice_stamp.py
│   │       ├── test_payment_complement.py
│   │       └── test_credit_note.py
│   │
│   ├── payroll/                 # ═══ MÓDULO 4: NÓMINA ELECTRÓNICA ═══
│   │   ├── __init__.py
│   │   ├── doctype/
│   │   │   ├── mx_payroll_settings/
│   │   │   ├── mx_employee_fiscal_data/   # CURP, NSS, SBC, etc.
│   │   │   ├── mx_isr_table/             # Tablas tarifarias
│   │   │   ├── mx_uma_value/             # Valores UMA por año
│   │   │   └── mx_minimum_wage/          # Salarios mínimos por zona
│   │   ├── overrides/
│   │   │   └── salary_slip.py     # validate + on_submit (→ stamp nómina)
│   │   ├── isr_calculator.py      # Art. 96 LISR, subsidio empleo
│   │   ├── imss_calculator.py     # Cuotas obrero por rama, tope 25×UMA
│   │   ├── infonavit_calculator.py
│   │   ├── nomina_xml_builder.py  # Complemento Nómina 1.2 Rev E
│   │   ├── catalogs/              # 13 catálogos específicos de nómina
│   │   │   ├── mx_perception_type/
│   │   │   ├── mx_deduction_type/
│   │   │   ├── mx_other_payment_type/
│   │   │   ├── mx_contract_type/
│   │   │   ├── mx_work_regime/
│   │   │   ├── mx_work_shift/
│   │   │   ├── mx_risk_class/
│   │   │   ├── mx_pay_period/
│   │   │   ├── mx_bank_sat/
│   │   │   ├── mx_state_sat/
│   │   │   ├── mx_disability_type/
│   │   │   ├── mx_overtime_type/
│   │   │   └── mx_separation_type/
│   │   └── tests/
│   │       ├── test_isr_calculator.py
│   │       ├── test_imss_calculator.py
│   │       └── test_nomina_stamp.py
│   │
│   ├── diot/                    # ═══ MÓDULO 5: DIOT ═══
│   │   ├── __init__.py
│   │   ├── doctype/
│   │   │   ├── mx_diot_report/
│   │   │   └── mx_diot_line/    # Child table: 54 campos
│   │   ├── diot_generator.py    # Agrupa Purchase Invoices → TXT
│   │   └── tests/
│   │       └── test_diot_generation.py
│   │
│   ├── carta_porte/             # ═══ MÓDULO 6: CARTA PORTE 3.1 ═══
│   │   ├── __init__.py
│   │   ├── doctype/
│   │   │   ├── mx_carta_porte/
│   │   │   ├── mx_vehicle/
│   │   │   ├── mx_transport_operator/
│   │   │   └── mx_carta_porte_merchandise/  # Child table
│   │   ├── overrides/
│   │   │   └── delivery_note.py
│   │   ├── carta_porte_xml_builder.py
│   │   ├── catalogs/            # Catálogos específicos Carta Porte
│   │   │   ├── mx_sct_permit_type/
│   │   │   ├── mx_vehicle_config/
│   │   │   ├── mx_trailer_subtype/
│   │   │   ├── mx_hazmat_material/
│   │   │   └── mx_product_service_key_cp/
│   │   └── tests/
│   │       └── test_carta_porte.py
│   │
│   ├── electronic_accounting/   # ═══ MÓDULO 7: CONTABILIDAD ELECTRÓNICA ═══
│   │   ├── __init__.py
│   │   ├── doctype/
│   │   │   └── mx_electronic_accounting/
│   │   ├── chart_of_accounts_xml.py    # Catálogo cuentas XML
│   │   ├── trial_balance_xml.py        # Balanza comprobación
│   │   ├── journal_entries_xml.py      # Pólizas
│   │   └── tests/
│   │       └── test_electronic_accounting.py
│   │
│   ├── setup/                   # ═══ DATOS DE INSTALACIÓN ═══
│   │   ├── chart_of_accounts/
│   │   │   └── mexico_standard.json     # CoA con código agrupador SAT
│   │   ├── tax_templates/
│   │   │   └── mexico_taxes.json        # IVA 16%, IVA 0%, ISR ret, IVA ret
│   │   └── print_formats/
│   │       ├── cfdi_invoice.json
│   │       ├── cfdi_payment.json
│   │       └── cfdi_payroll.json
│   │
│   ├── public/js/               # ═══ FRONTEND EXTENSIONS ═══
│   │   ├── sales_invoice.js     # Botón "Timbrar CFDI", campos visibles
│   │   ├── purchase_invoice.js  # Botón "Importar XML"
│   │   ├── payment_entry.js     # Auto-detect PPD, botón complemento
│   │   ├── customer.js          # RFC validation, SAT data fetch
│   │   ├── supplier.js          # RFC + tipo tercero DIOT
│   │   ├── item.js              # Buscador clave SAT
│   │   ├── company.js           # Configuración fiscal empresa
│   │   ├── employee.js          # Link a datos fiscales empleado
│   │   └── delivery_note.js     # Sección Carta Porte
│   │
│   ├── templates/               # ═══ PRINT FORMATS (JINJA) ═══
│   │   ├── cfdi_invoice.html    # PDF con QR, cadena original, sellos
│   │   ├── cfdi_payment.html
│   │   └── cfdi_payroll.html
│   │
│   └── utils/                   # ═══ UTILIDADES ═══
│       ├── __init__.py
│       ├── rfc_validator.py     # Regex + dígito verificador
│       ├── curp_validator.py
│       ├── sat_rounding.py      # Reglas de redondeo Anexo 20
│       ├── jinja_methods.py     # Helpers para print formats
│       └── amount_to_words.py   # "MIL QUINIENTOS PESOS 00/100 M.N."
```

## Interrelaciones entre Módulos

### Flujo de Facturación (Módulo 3 → 1 → PAC)
```
Sales Invoice.on_submit
  → invoicing/overrides/sales_invoice.py
    → cfdi/xml_builder.py (genera XML CFDI 4.0)
      → sat_catalogs/ (consulta códigos SAT)
    → cfdi/xml_signer.py (firma con CSD)
      → cfdi/doctype/mx_digital_certificate (lee certificado)
    → cfdi/pac_dispatcher.py (selecciona PAC)
      → cfdi/pacs/finkok_pac.py (timbra via satcfdi)
    → cfdi/doctype/mx_cfdi_log (registra operación)
    → Actualiza Sales Invoice (UUID, XML, PDF, status)
```

### Flujo de Pagos (Módulo 3 → 1 → PAC)
```
Payment Entry.on_submit
  → invoicing/overrides/payment_entry.py
    → invoicing/payment_complement.py
      → Detecta facturas PPD relacionadas
      → Calcula parcialidades y saldos
      → Genera CFDI tipo "P" con Complemento Pagos 2.0
    → cfdi/xml_builder.py + xml_signer.py + pac_dispatcher.py
    → Actualiza Payment Entry (UUID, XML)
```

### Flujo de Nómina (Módulo 4 → 1 → PAC)
```
Salary Slip.on_submit
  → payroll/overrides/salary_slip.py
    → payroll/isr_calculator.py (calcula ISR)
    → payroll/imss_calculator.py (calcula cuotas IMSS)
    → payroll/nomina_xml_builder.py (genera complemento 1.2)
    → cfdi/xml_builder.py (envuelve en CFDI tipo "N")
    → cfdi/xml_signer.py + pac_dispatcher.py
```

### Flujo DIOT (Módulo 5 → catálogos)
```
MX DIOT Report.generate()
  → diot/diot_generator.py
    → Lee Purchase Invoices del periodo
    → Agrupa por RFC de proveedor
    → Clasifica por tasa IVA y tipo operación
    → Genera TXT 54 campos delimitado por pipes
```

### Flujo Carta Porte (Módulo 6 → 1 → PAC)
```
Delivery Note.on_submit (si tiene Carta Porte)
  → carta_porte/overrides/delivery_note.py
    → carta_porte/carta_porte_xml_builder.py
      → Nodos: Ubicaciones, Mercancías, Autotransporte, FiguraTransporte
    → cfdi/xml_builder.py (CFDI tipo "T" o "I")
    → cfdi/xml_signer.py + pac_dispatcher.py
```

## Reglas de Diseño

1. **Nunca modificar código de ERPNext core** — solo hooks, custom fields y overrides
2. **satcfdi es el motor** — no reinventar XML generation ni firma digital
3. **Custom Fields siempre con prefijo `mx_`** y module="ERPNext Mexico"
4. **Catálogos SAT como DocTypes read-only** — importados una vez, actualizados por parches
5. **Cada PAC es un adapter** que implementa PACInterface
6. **MX CFDI Log registra TODO** — auditoría completa de operaciones fiscales
7. **Fixtures JSON para datos estáticos** — Custom Fields, Property Setters, Print Formats
8. **Tests con sandbox real** — usar CSD de prueba SAT + sandbox de PAC
