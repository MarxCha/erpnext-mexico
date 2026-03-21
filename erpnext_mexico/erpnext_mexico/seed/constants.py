# -*- coding: utf-8 -*-
"""Constantes compartidas para seed data pipeline."""

COMPANY = "MD Consultoria TI"
COMPANY_RFC = "EKU9003173C9"
COMPANY_NOMBRE_FISCAL = "ESCUELA KEMPER URGATE"
COMPANY_REGIMEN = "601"
COMPANY_CP = "42501"

CUSTOMERS = [
    {
        "name": "Publico en General",
        "rfc": "XAXX010101000",
        "nombre_fiscal": "PUBLICO EN GENERAL",
        "regimen": "616",
        "cp": "42501",
        "uso_cfdi": "S01",
        "forma_pago": "01",
        "customer_type": "Individual",
    },
    {
        "name": "Grupo Financiero Banamex SA de CV",
        "rfc": "GFB920930JA6",
        "nombre_fiscal": "GRUPO FINANCIERO BANAMEX SA DE CV",
        "regimen": "601",
        "cp": "06600",
        "uso_cfdi": "G03",
        "forma_pago": "03",
        "customer_type": "Company",
    },
    {
        "name": "Soluciones Cloud MX SA de CV",
        "rfc": "AAA010101AAA",
        "nombre_fiscal": "SOLUCIONES CLOUD MX SA DE CV",
        "regimen": "601",
        "cp": "03100",
        "uso_cfdi": "G03",
        "forma_pago": "03",
        "customer_type": "Company",
    },
    {
        "name": "Universidad Nacional UNAM",
        "rfc": "UNA6812178Z3",
        "nombre_fiscal": "UNIVERSIDAD NACIONAL AUTONOMA DE MEXICO",
        "regimen": "603",
        "cp": "04510",
        "uso_cfdi": "G03",
        "forma_pago": "03",
        "customer_type": "Company",
    },
    {
        "name": "John Smith (Extranjero)",
        "rfc": "XEXX010101000",
        "nombre_fiscal": "JOHN SMITH",
        "regimen": "616",
        "cp": "42501",
        "uso_cfdi": "S01",
        "forma_pago": "03",
        "customer_type": "Individual",
    },
]

SUPPLIERS = [
    {
        "name": "Amazon Web Services Mexico",
        "rfc": "AWM130301T17",
        "tipo_tercero": "Nacional",
        "tipo_operacion": "Otros",
    },
    {
        "name": "Deloitte Mexico SC",
        "rfc": "DME070730JA3",
        "tipo_tercero": "Nacional",
        "tipo_operacion": "Servicios Profesionales",
    },
    {
        "name": "Telmex SA de CV",
        "rfc": "TME840315KT6",
        "tipo_tercero": "Nacional",
        "tipo_operacion": "Otros",
    },
    {
        "name": "Microsoft Corporation",
        "rfc": "XEXX010101000",
        "tipo_tercero": "Extranjero",
        "tipo_operacion": "Otros",
        "nit_extranjero": "91-1144442",
        "pais_residencia": "USA",
        "nacionalidad": "Estadounidense",
    },
    {
        "name": "Papeleria LUMEN SA de CV",
        "rfc": "PLU950101AAA",
        "tipo_tercero": "Nacional",
        "tipo_operacion": "Otros",
    },
]

ITEMS = [
    {"item_code": "CONS-TI-001", "item_name": "Consultoria en Tecnologias de Informacion",
     "clave_prod_serv": "84111506", "clave_unidad": "E48", "rate": 1500, "uom": "Hour"},
    {"item_code": "DEV-SW-001", "item_name": "Desarrollo de Software a la Medida",
     "clave_prod_serv": "81112100", "clave_unidad": "E48", "rate": 2000, "uom": "Hour"},
    {"item_code": "SOPORTE-001", "item_name": "Soporte Tecnico Mensual",
     "clave_prod_serv": "81112002", "clave_unidad": "E48", "rate": 8000, "uom": "Nos"},
    {"item_code": "HOSTING-001", "item_name": "Hospedaje en Nube (Reventa)",
     "clave_prod_serv": "81112300", "clave_unidad": "E48", "rate": 3500, "uom": "Nos"},
    {"item_code": "CAPACIT-001", "item_name": "Capacitacion Tecnica",
     "clave_prod_serv": "86101700", "clave_unidad": "E48", "rate": 12000, "uom": "Nos"},
    {"item_code": "LICENCIA-001", "item_name": "Licencia de Software (Reventa)",
     "clave_prod_serv": "43231500", "clave_unidad": "E48", "rate": 5000, "uom": "Nos"},
    {"item_code": "AUDIT-TI-001", "item_name": "Auditoria de Seguridad TI",
     "clave_prod_serv": "84111507", "clave_unidad": "E48", "rate": 25000, "uom": "Nos"},
    {"item_code": "PROYECTO-001", "item_name": "Gestion de Proyecto TI",
     "clave_prod_serv": "84111502", "clave_unidad": "E48", "rate": 15000, "uom": "Nos"},
]

EMPLOYEES = [
    {"employee_name": "Juan Perez Lopez", "first_name": "Juan", "last_name": "Perez Lopez",
     "rfc": "PELJ900101ABC", "date_of_birth": "1990-01-01", "date_of_joining": "2024-01-15",
     "gender": "Male", "designation": "Software Developer"},
    {"employee_name": "Maria Garcia Torres", "first_name": "Maria", "last_name": "Garcia Torres",
     "rfc": "GATM850515XYZ", "date_of_birth": "1985-05-15", "date_of_joining": "2023-06-01",
     "gender": "Female", "designation": "Project Manager"},
]
