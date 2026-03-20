"""E2E Test: DIOT 2025 generation.

Tests the full DIOT (Declaracion Informativa de Operaciones con Terceros) pipeline:
1. Creates test Purchase Invoices with supplier data and IVA taxes
2. Executes the DIOT generator
3. Validates the TXT output format (pipe-separated, 24 fields per line)
"""
import frappe
import traceback


def run():
    """Execute all DIOT E2E tests."""
    company = "MD Consultoria TI"
    year = 2026
    month = 3
    supplier_name = "Proveedor Prueba MX"

    print("=" * 70)
    print("E2E TEST: DIOT 2025 Generation")
    print("=" * 70)
    print(f"Company: {company}")
    print(f"Period: {year}-{month:02d}")
    print(f"Supplier: {supplier_name}")
    print()

    frappe.set_user("Administrator")

    # Phase 1: Preflight checks
    _preflight(company, supplier_name)

    # Phase 2: Ensure test Purchase Invoice exists
    pinv_name = _ensure_purchase_invoice(company, supplier_name, year, month)

    # Phase 3: Run DIOT generator
    _test_generate_diot(company, year, month)

    # Phase 4: Test edge case — empty period
    _test_empty_period(company)

    print()
    print("=" * 70)
    print("E2E DIOT COMPLETE")
    print("=" * 70)


def _preflight(company: str, supplier_name: str):
    """Verify prerequisites."""
    print("-" * 50)
    print("[PREFLIGHT] Checking company and supplier...")
    print("-" * 50)

    # Company
    if not frappe.db.exists("Company", company):
        print(f"  FAIL: Company '{company}' not found!")
        raise SystemExit(1)
    print(f"  Company '{company}' exists: OK")

    # Supplier
    if not frappe.db.exists("Supplier", supplier_name):
        print(f"  FAIL: Supplier '{supplier_name}' not found!")
        raise SystemExit(1)

    sup_data = frappe.db.get_value(
        "Supplier", supplier_name,
        ["mx_rfc", "mx_tipo_tercero_diot", "supplier_name"],
        as_dict=True,
    )
    print(f"  Supplier '{supplier_name}' exists: OK")
    print(f"    mx_rfc: {sup_data.get('mx_rfc', '(not set)')}")
    print(f"    mx_tipo_tercero_diot: {sup_data.get('mx_tipo_tercero_diot', '(not set)')}")

    # Accounts
    expense_account = frappe.db.get_value("Account", {
        "company": company, "root_type": "Expense", "is_group": 0,
    }, "name")
    payable_account = frappe.db.get_value("Account", {
        "company": company, "root_type": "Liability", "is_group": 0,
        "account_type": "Payable",
    }, "name")
    iva_account = frappe.db.get_value("Account", {
        "company": company, "is_group": 0, "account_type": "Tax",
    }, "name")
    print(f"  Expense account: {expense_account}")
    print(f"  Payable account: {payable_account}")
    print(f"  IVA account: {iva_account}")
    print()


def _ensure_purchase_invoice(company: str, supplier_name: str, year: int, month: int) -> str:
    """Create a submitted Purchase Invoice for the test period if none exists."""
    print("-" * 50)
    print("[PHASE 2] Ensuring Purchase Invoice exists...")
    print("-" * 50)

    from_date = f"{year}-{month:02d}-01"
    to_date = f"{year}-{month:02d}-31"

    existing = frappe.get_all("Purchase Invoice", filters={
        "company": company,
        "supplier": supplier_name,
        "docstatus": 1,
        "posting_date": ["between", [from_date, to_date]],
    }, fields=["name"], limit_page_length=1)

    if existing:
        print(f"  Found existing submitted PI: {existing[0].name}")
        print()
        return existing[0].name

    print("  No submitted PI found for this period. Creating one...")

    # Get required accounts
    expense_account = frappe.db.get_value("Account", {
        "company": company, "root_type": "Expense", "is_group": 0,
    }, "name")
    payable_account = frappe.db.get_value("Account", {
        "company": company, "root_type": "Liability", "is_group": 0,
        "account_type": "Payable",
    }, "name")
    iva_account = frappe.db.get_value("Account", {
        "company": company, "is_group": 0, "account_type": "Tax",
    }, "name")
    cost_center = frappe.db.get_value("Cost Center", {
        "company": company, "is_group": 0,
    }, "name")

    if not all([expense_account, payable_account, iva_account, cost_center]):
        print(f"  FAIL: Missing required accounts/cost center")
        print(f"    expense_account={expense_account}")
        print(f"    payable_account={payable_account}")
        print(f"    iva_account={iva_account}")
        print(f"    cost_center={cost_center}")
        raise SystemExit(1)

    # Get company default currency
    company_currency = frappe.db.get_value("Company", company, "default_currency") or "MXN"

    pinv = frappe.get_doc({
        "doctype": "Purchase Invoice",
        "supplier": supplier_name,
        "company": company,
        "posting_date": f"{year}-{month:02d}-15",
        "due_date": f"{year}-{month:02d}-28",
        "credit_to": payable_account,
        "currency": company_currency,
        "conversion_rate": 1.0,
        "buying_price_list": frappe.db.get_value("Price List", {"buying": 1}, "name") or "Standard Buying",
        "cost_center": cost_center,
        "items": [{
            "item_name": "Servicio de prueba DIOT",
            "description": "Servicio profesional para prueba E2E DIOT",
            "qty": 1,
            "rate": 10000.0,
            "expense_account": expense_account,
            "cost_center": cost_center,
        }],
        "taxes": [{
            "charge_type": "On Net Total",
            "account_head": iva_account,
            "description": "IVA 16%",
            "rate": 16,
            "cost_center": cost_center,
        }],
    })

    try:
        pinv.insert(ignore_permissions=True)
        print(f"  Created PI: {pinv.name}")

        pinv.submit()
        frappe.db.commit()
        print(f"  Submitted PI: {pinv.name} (docstatus={pinv.docstatus})")
        print(f"    net_total: {pinv.net_total}")
        print(f"    grand_total: {pinv.grand_total}")
        print(f"    total_taxes_and_charges: {pinv.total_taxes_and_charges}")
        print()
        return pinv.name

    except Exception as e:
        print(f"  FAIL creating PI: {type(e).__name__}: {e}")
        traceback.print_exc()
        frappe.db.rollback()
        raise SystemExit(1)


def _test_generate_diot(company: str, year: int, month: int):
    """Test the DIOT generator with real data."""
    print("-" * 50)
    print("[PHASE 3] Testing DIOT Generation")
    print("-" * 50)

    from erpnext_mexico.diot.diot_generator import generate_diot

    try:
        result = generate_diot(company=company, month=month, year=year)

        print(f"  Return type: {type(result).__name__}")
        print(f"  Keys: {list(result.keys())}")
        print(f"  filename: {result.get('filename')}")
        print(f"  supplier_count: {result.get('supplier_count')}")
        print(f"  total_lines: {result.get('total_lines')}")

        content = result.get("content", "")
        print(f"  content length: {len(content)} chars")

        # Assertion 1: result is a dict with expected keys
        assert isinstance(result, dict), "Result must be a dict"
        for key in ["filename", "content", "supplier_count", "total_lines"]:
            assert key in result, f"Missing key: {key}"

        # Assertion 2: has content
        assert content, "Content must not be empty"
        print("  ASSERT content non-empty: PASS")

        # Assertion 3: filename format
        filename = result["filename"]
        assert filename.startswith("DIOT_"), f"Filename must start with DIOT_, got: {filename}"
        assert filename.endswith(".txt"), f"Filename must end with .txt, got: {filename}"
        assert f"{year}{month:02d}" in filename, f"Filename must contain period {year}{month:02d}"
        print(f"  ASSERT filename format: PASS ({filename})")

        # Assertion 4: supplier count > 0
        assert result["supplier_count"] > 0, "Must have at least 1 supplier"
        print(f"  ASSERT supplier_count > 0: PASS ({result['supplier_count']})")

        # Assertion 5: total_lines > 0
        assert result["total_lines"] > 0, "Must have at least 1 line"
        print(f"  ASSERT total_lines > 0: PASS ({result['total_lines']})")

        # Assertion 6: each line has exactly 24 pipe-separated fields
        lines = content.strip().split("\n")
        print(f"  Total lines in content: {len(lines)}")
        for i, line in enumerate(lines):
            fields = line.split("|")
            assert len(fields) == 24, (
                f"Line {i+1} must have 24 fields, got {len(fields)}: {line[:100]}"
            )
        print("  ASSERT all lines have 24 pipe-separated fields: PASS")

        # Assertion 7: validate first line structure for Nacional supplier
        first_fields = lines[0].split("|")
        print(f"  First line fields:")
        print(f"    [0] Tipo tercero:  '{first_fields[0]}'")
        print(f"    [1] Tipo operacion: '{first_fields[1]}'")
        print(f"    [2] RFC:           '{first_fields[2]}' (len={len(first_fields[2])})")
        print(f"    [3] NIT:           '{first_fields[3]}'")
        print(f"    [4] Nombre ext:    '{first_fields[4]}'")
        print(f"    [7] Valor 16%:     '{first_fields[7]}'")
        print(f"    [16] Valor 0%:     '{first_fields[16]}'")
        print(f"    [17] Valor exento: '{first_fields[17]}'")
        print(f"    [18] IVA retenido: '{first_fields[18]}'")

        # Tipo tercero should be 04 (Nacional) for our test supplier
        assert first_fields[0] == "04", f"Expected tipo_tercero '04', got '{first_fields[0]}'"
        print("  ASSERT tipo_tercero == '04' (Nacional): PASS")

        # RFC field should be 13 chars, padded
        assert len(first_fields[2]) == 13, (
            f"RFC field must be 13 chars, got {len(first_fields[2])}"
        )
        assert first_fields[2].strip() == "AAA010101AAA", (
            f"RFC should be AAA010101AAA, got '{first_fields[2].strip()}'"
        )
        print("  ASSERT RFC field 13 chars with correct value: PASS")

        # Valor 16% should be > 0 (we created an invoice with IVA 16%)
        valor_16 = int(first_fields[7])
        assert valor_16 > 0, f"Expected valor_16 > 0, got {valor_16}"
        print(f"  ASSERT valor_16 > 0: PASS ({valor_16})")

        # Amount fields should be integers (no decimals, no commas)
        for idx in [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]:
            val = first_fields[idx]
            assert val.isdigit() or val == "0", (
                f"Field {idx+1} must be integer, got '{val}'"
            )
        print("  ASSERT all amount fields are integers: PASS")

        # Last 4 fields should be empty
        for idx in range(20, 24):
            assert first_fields[idx] == "", (
                f"Field {idx+1} (padding) must be empty, got '{first_fields[idx]}'"
            )
        print("  ASSERT last 4 fields are empty padding: PASS")

        # Print full content for inspection
        print()
        print("  Full DIOT content:")
        for i, line in enumerate(lines):
            print(f"    Line {i+1}: {line}")

        print()
        print("  DIOT GENERATION: OK")

    except Exception as e:
        print(f"  DIOT GENERATION: FAIL - {type(e).__name__}: {e}")
        traceback.print_exc()


def _test_empty_period(company: str):
    """Test DIOT generator returns empty result for a period with no invoices."""
    print()
    print("-" * 50)
    print("[PHASE 4] Testing empty period (no invoices)")
    print("-" * 50)

    from erpnext_mexico.diot.diot_generator import generate_diot

    try:
        # Use a month far in the future where no invoices exist
        result = generate_diot(company=company, month=1, year=2099)

        assert isinstance(result, dict), "Result must be a dict"
        assert result.get("content") == "", f"Expected empty content, got: {result.get('content')!r}"
        assert result.get("supplier_count") == 0, f"Expected 0 suppliers, got {result.get('supplier_count')}"
        assert result.get("total_lines") == 0, f"Expected 0 lines, got {result.get('total_lines')}"

        print("  ASSERT empty period returns empty result: PASS")
        print("  EMPTY PERIOD: OK")

    except Exception as e:
        print(f"  EMPTY PERIOD: FAIL - {type(e).__name__}: {e}")
        traceback.print_exc()
