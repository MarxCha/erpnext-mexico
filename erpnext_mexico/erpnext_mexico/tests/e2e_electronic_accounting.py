"""E2E Test: Electronic Accounting (Anexo 24).

Tests the three XML generators for Contabilidad Electrónica:
1. Catálogo de Cuentas
2. Balanza de Comprobación
3. Pólizas del Período
"""
import frappe


def run():
    """Execute all Electronic Accounting E2E tests."""
    company = "MD Consultoria TI"
    year = 2026
    month = 3

    print("=" * 70)
    print("E2E TEST: Electronic Accounting (Anexo 24)")
    print("=" * 70)
    print(f"Company: {company}")
    print(f"Period: {year}-{month:02d}")
    print()

    # Pre-flight: check company exists and has RFC
    _preflight(company)

    # Run tests
    _test_catalog_xml(company, year, month)
    print()
    _test_balanza_xml(company, year, month)
    print()
    _test_polizas_xml(company, year, month)

    print()
    print("=" * 70)
    print("E2E COMPLETE")
    print("=" * 70)


def _preflight(company: str):
    """Verify prerequisites before running tests."""
    print("[PREFLIGHT] Checking company and RFC...")

    if not frappe.db.exists("Company", company):
        print(f"  WARN: Company '{company}' not found. Creating won't be attempted.")
        return

    doc = frappe.get_doc("Company", company)
    rfc = doc.get("mx_rfc")
    print(f"  Company found: {company}")
    print(f"  mx_rfc: {rfc or '(not set)'}")

    if not rfc:
        print("  Setting mx_rfc = 'EKU9003173C9' (SAT test RFC)...")
        doc.set("mx_rfc", "EKU9003173C9")
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print("  RFC set successfully.")

    # Check we have accounts
    account_count = frappe.db.count("Account", {"company": company})
    print(f"  Accounts in chart: {account_count}")

    # Check GL entries in period
    gl_count = frappe.db.count("GL Entry", {
        "company": company,
        "posting_date": ["between", ["2026-03-01", "2026-03-31"]],
        "is_cancelled": 0,
    })
    print(f"  GL Entries in 2026-03: {gl_count}")
    print()


def _test_catalog_xml(company: str, year: int, month: int):
    """Test 1: Catálogo de Cuentas XML."""
    print("-" * 50)
    print("[TEST 1] Catálogo de Cuentas XML")
    print("-" * 50)

    from erpnext_mexico.electronic_accounting.catalog_xml import generate_catalog_xml

    try:
        # Set session user to Administrator to pass permission checks
        frappe.set_user("Administrator")

        result = generate_catalog_xml(company=company, year=year, month=month)

        print(f"  Return type: {type(result).__name__}")
        print(f"  Length: {len(result)} chars")

        # Validate XML structure
        assert isinstance(result, str), "Expected string result"
        assert '<?xml version=' in result, "Missing XML declaration"
        assert 'CatalogoCuentas' in result, "Missing CatalogoCuentas namespace"
        assert 'Version="1.3"' in result, "Missing Version 1.3"
        assert 'RFC="EKU9003173C9"' in result or 'RFC=' in result, "Missing RFC attribute"
        assert f'Mes="{month:02d}"' in result, "Missing Mes attribute"
        assert f'Anio="{year}"' in result, "Missing Anio attribute"

        # Count Ctas elements
        ctas_count = result.count("<BCE:Ctas") + result.count("<Ctas") + result.count(":Ctas ")
        # More reliable: count NumCta occurrences
        numcta_count = result.count('NumCta=')
        print(f"  Account entries (NumCta): {numcta_count}")

        # Show first 500 chars
        print(f"  Preview:\n{result[:500]}")

        # Parse with lxml to validate well-formedness
        from lxml import etree
        tree = etree.fromstring(result.encode("utf-8"))
        children = list(tree)
        print(f"  XML well-formed: YES ({len(children)} child elements)")

        print("  CATALOG: OK")

    except Exception as e:
        print(f"  CATALOG: FAIL - {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def _test_balanza_xml(company: str, year: int, month: int):
    """Test 2: Balanza de Comprobación XML."""
    print("-" * 50)
    print("[TEST 2] Balanza de Comprobación XML")
    print("-" * 50)

    from erpnext_mexico.electronic_accounting.balanza_xml import generate_balanza_xml

    try:
        frappe.set_user("Administrator")

        result = generate_balanza_xml(company=company, year=year, month=month)

        print(f"  Return type: {type(result).__name__}")
        print(f"  Length: {len(result)} chars")

        assert isinstance(result, str), "Expected string result"
        assert '<?xml version=' in result, "Missing XML declaration"
        assert 'BalanzaComprobacion' in result, "Missing BalanzaComprobacion namespace"
        assert 'Version="1.3"' in result, "Missing Version 1.3"
        assert 'TipoEnvio="N"' in result, "Missing TipoEnvio"

        numcta_count = result.count('NumCta=')
        print(f"  Account entries (NumCta): {numcta_count}")

        # Parse XML
        from lxml import etree
        tree = etree.fromstring(result.encode("utf-8"))
        children = list(tree)
        print(f"  XML well-formed: YES ({len(children)} Ctas elements)")

        # Check that balanza has proper attributes on Ctas
        if children:
            first = children[0]
            attrs = dict(first.attrib)
            print(f"  First Ctas attrs: {attrs}")
            assert "SaldoIni" in attrs, "Missing SaldoIni"
            assert "Debe" in attrs, "Missing Debe"
            assert "Haber" in attrs, "Missing Haber"
            assert "SaldoFin" in attrs, "Missing SaldoFin"

        print(f"  Preview:\n{result[:500]}")
        print("  BALANZA: OK")

    except Exception as e:
        print(f"  BALANZA: FAIL - {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def _test_polizas_xml(company: str, year: int, month: int):
    """Test 3: Pólizas del Período XML."""
    print("-" * 50)
    print("[TEST 3] Pólizas del Período XML")
    print("-" * 50)

    from erpnext_mexico.electronic_accounting.polizas_xml import generate_polizas_xml

    try:
        frappe.set_user("Administrator")

        result = generate_polizas_xml(
            company=company,
            year=year,
            month=month,
            tipo_solicitud="AF",
            num_orden="ABC123",
        )

        print(f"  Return type: {type(result).__name__}")
        print(f"  Length: {len(result)} chars")

        assert isinstance(result, str), "Expected string result"
        assert '<?xml version=' in result, "Missing XML declaration"
        assert 'PolizasPeriodo' in result, "Missing PolizasPeriodo namespace"
        assert 'Version="1.3"' in result, "Missing Version 1.3"
        assert 'TipoSolicitud="AF"' in result, "Missing TipoSolicitud"
        assert 'NumOrden="ABC123"' in result, "Missing NumOrden"

        poliza_count = result.count('NumUnIdenPol=')
        transaccion_count = result.count('Concepto=') - poliza_count  # Concepto appears in both
        print(f"  Poliza entries: {poliza_count}")

        # Parse XML
        from lxml import etree
        tree = etree.fromstring(result.encode("utf-8"))
        ns = "http://www.sat.gob.mx/esquemas/ContabilidadE/1_3/PolizasPeriodo"
        polizas = tree.findall(f"{{{ns}}}Poliza")
        print(f"  XML well-formed: YES ({len(polizas)} Poliza elements)")

        if polizas:
            first_poliza = polizas[0]
            print(f"  First Poliza attrs: {dict(first_poliza.attrib)}")
            transacciones = first_poliza.findall(f"{{{ns}}}Transaccion")
            print(f"  Transacciones in first Poliza: {len(transacciones)}")
            if transacciones:
                print(f"  First Transaccion attrs: {dict(transacciones[0].attrib)}")

        print(f"  Preview:\n{result[:500]}")
        print("  POLIZAS: OK")

    except Exception as e:
        print(f"  POLIZAS: FAIL - {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
