# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

"""Tests para cfdi_helpers.py — helpers compartidos de módulos CFDI.

Pure unit tests — run without a live Frappe site or network access.
`frappe` and its sub-modules are stubbed before the module under test
is imported, so these tests work in any Python environment.

Coverage:
  is_mexico_company
    - company with mx_rfc returns True
    - company without mx_rfc (None / empty) returns False
    - frappe.db.get_value is called with correct args

  get_cfdi_settings
    - returns the settings doc on success
    - returns None when frappe raises any exception
    - calls frappe.get_single with correct doctype

  save_cfdi_attachment
    - frappe.get_doc is called with correct dict fields
    - file_doc.save() is called with ignore_permissions=True
    - the created file doc is returned

  create_cfdi_log
    - frappe.get_doc is called once with "MX CFDI Log" doctype
    - result.uuid is forwarded to the log dict
    - result.xml_stamped is forwarded
    - result.fecha_timbrado is forwarded as stamped_at
    - insert() is called with ignore_permissions=True
    - pac_used is read from MX CFDI Settings via frappe.db

  handle_stamp_error
    - frappe.log_error is called with sanitized error message
    - log_error title contains doc.name
    - frappe.throw is called (i.e. exception is raised)
    - the throw message references doc.name

  check_stamp_rate_limit
    - under the document limit: cache is incremented and no exception
    - at the document limit: frappe.throw is raised
    - cache key includes the document name
    - cache.set is called with the correct window_seconds
    - custom max_attempts is respected
    - user-level rate limit (30/hour) is also enforced
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, call, patch


# ──────────────────────────────────────────────────────────────────────────────
# Stub installer
# ──────────────────────────────────────────────────────────────────────────────

def _install_stubs() -> None:
    """Register lightweight frappe stubs if the real module is absent.

    check_stamp_rate_limit uses frappe.session.user so the stub must
    expose a session attribute with a user field.
    """
    if "frappe" in sys.modules and hasattr(sys.modules["frappe"], "get_doc"):
        return

    frappe_stub = types.ModuleType("frappe")
    frappe_stub._ = lambda s: s
    frappe_stub.throw = MagicMock(side_effect=Exception("frappe.throw called"))
    frappe_stub.get_single = MagicMock()
    frappe_stub.get_doc = MagicMock()
    frappe_stub.db = MagicMock()
    frappe_stub.log_error = MagicMock()
    # Session stub — check_stamp_rate_limit accesses frappe.session.user
    _session = types.SimpleNamespace(user="test@example.com")
    frappe_stub.session = _session
    _cache_mock = MagicMock()
    _cache_mock.get = MagicMock(return_value=b"0")
    _cache_mock.set = MagicMock()
    frappe_stub.cache = MagicMock(return_value=_cache_mock)
    frappe_stub.whitelist = lambda *args, **kwargs: (
        (lambda fn: fn) if not args else args[0]
    )
    sys.modules["frappe"] = frappe_stub

    # erpnext_mexico.utils.sanitize — real module exists; stub only as fallback
    try:
        import erpnext_mexico.utils.sanitize  # noqa: F401
    except ImportError:
        sanitize_mod = types.ModuleType("erpnext_mexico.utils.sanitize")
        sanitize_mod.sanitize_log_message = lambda s: s
        utils_mod = types.ModuleType("erpnext_mexico.utils")
        utils_mod.sanitize = sanitize_mod
        erpnext_mx_mod = (
            sys.modules.get("erpnext_mexico") or types.ModuleType("erpnext_mexico")
        )
        erpnext_mx_mod.utils = utils_mod
        sys.modules.setdefault("erpnext_mexico", erpnext_mx_mod)
        sys.modules.setdefault("erpnext_mexico.utils", utils_mod)
        sys.modules["erpnext_mexico.utils.sanitize"] = sanitize_mod


_install_stubs()

# Safe to import now
from erpnext_mexico.cfdi.cfdi_helpers import (  # noqa: E402
    check_stamp_rate_limit,
    create_cfdi_log,
    get_cfdi_settings,
    handle_stamp_error,
    is_mexico_company,
    save_cfdi_attachment,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_doc(doctype="Sales Invoice", name="SINV-0001"):
    """Return a minimal mock doc object."""
    doc = MagicMock()
    doc.doctype = doctype
    doc.name = name
    return doc


def _make_stamp_result(
    uuid="ABCD-1234",
    xml_stamped="<cfdi/>",
    fecha_timbrado="2026-01-15T10:00:00",
):
    result = MagicMock()
    result.uuid = uuid
    result.xml_stamped = xml_stamped
    result.fecha_timbrado = fecha_timbrado
    return result


# ──────────────────────────────────────────────────────────────────────────────
# is_mexico_company tests
# ──────────────────────────────────────────────────────────────────────────────

class TestIsMexicoCompany(unittest.TestCase):
    """is_mexico_company returns True only when mx_rfc has a non-empty value."""

    def setUp(self):
        self._frappe = sys.modules["frappe"]
        self._frappe.db.get_value.reset_mock()

    def test_company_with_rfc_returns_true(self):
        self._frappe.db.get_value.return_value = "EKU9003173C9"
        self.assertTrue(is_mexico_company("Test Company"))

    def test_company_without_rfc_none_returns_false(self):
        self._frappe.db.get_value.return_value = None
        self.assertFalse(is_mexico_company("Empresa Sin RFC"))

    def test_company_with_empty_string_rfc_returns_false(self):
        self._frappe.db.get_value.return_value = ""
        self.assertFalse(is_mexico_company("Empresa Vacía"))

    def test_calls_get_value_with_company_doctype(self):
        self._frappe.db.get_value.return_value = "EKU9003173C9"
        is_mexico_company("Mi Empresa SA de CV")
        args = self._frappe.db.get_value.call_args
        self.assertEqual(args[0][0], "Company")

    def test_calls_get_value_with_correct_company_name(self):
        self._frappe.db.get_value.return_value = "RFC123456789"
        is_mexico_company("Mi Empresa SA de CV")
        args = self._frappe.db.get_value.call_args
        self.assertEqual(args[0][1], "Mi Empresa SA de CV")

    def test_calls_get_value_for_mx_rfc_field(self):
        self._frappe.db.get_value.return_value = "RFC123456789"
        is_mexico_company("Mi Empresa SA de CV")
        args = self._frappe.db.get_value.call_args
        self.assertEqual(args[0][2], "mx_rfc")

    def test_return_type_is_bool(self):
        self._frappe.db.get_value.return_value = "EKU9003173C9"
        result = is_mexico_company("Empresa")
        self.assertIsInstance(result, bool)


# ──────────────────────────────────────────────────────────────────────────────
# get_cfdi_settings tests
# ──────────────────────────────────────────────────────────────────────────────

class TestGetCfdiSettings(unittest.TestCase):
    """get_cfdi_settings wraps frappe.get_single with safe exception handling."""

    def setUp(self):
        self._frappe = sys.modules["frappe"]
        self._frappe.get_single.reset_mock()

    def test_returns_settings_doc_on_success(self):
        expected = MagicMock()
        self._frappe.get_single.return_value = expected
        result = get_cfdi_settings()
        self.assertIs(result, expected)

    def test_calls_get_single_with_correct_doctype(self):
        self._frappe.get_single.return_value = MagicMock()
        get_cfdi_settings()
        self._frappe.get_single.assert_called_once_with("MX CFDI Settings")

    def test_returns_none_on_exception(self):
        self._frappe.get_single.side_effect = Exception("DocType not found")
        result = get_cfdi_settings()
        self.assertIsNone(result)
        self._frappe.get_single.side_effect = None

    def test_returns_none_on_attribute_error(self):
        self._frappe.get_single.side_effect = AttributeError("no attr")
        result = get_cfdi_settings()
        self.assertIsNone(result)
        self._frappe.get_single.side_effect = None

    def test_returns_none_when_doctype_missing(self):
        self._frappe.get_single.side_effect = KeyError("MX CFDI Settings")
        result = get_cfdi_settings()
        self.assertIsNone(result)
        self._frappe.get_single.side_effect = None


# ──────────────────────────────────────────────────────────────────────────────
# save_cfdi_attachment tests
# ──────────────────────────────────────────────────────────────────────────────

class TestSaveCfdiAttachment(unittest.TestCase):
    """save_cfdi_attachment creates a private File doc attached to the parent doc."""

    def setUp(self):
        self._frappe = sys.modules["frappe"]
        self._file_doc = MagicMock()
        self._frappe.get_doc.reset_mock()
        self._frappe.get_doc.return_value = self._file_doc

    def _call(self, doc=None, filename="cfdi.xml", content="<xml/>",
              content_type="application/xml"):
        doc = doc or _make_doc()
        return save_cfdi_attachment(doc, filename, content, content_type)

    def test_get_doc_called_with_file_doctype(self):
        self._call()
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["doctype"], "File")

    def test_file_doc_has_correct_filename(self):
        self._call(filename="factura-001.xml")
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["file_name"], "factura-001.xml")

    def test_file_doc_attached_to_correct_doctype(self):
        doc = _make_doc(doctype="Sales Invoice")
        self._call(doc=doc)
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["attached_to_doctype"], "Sales Invoice")

    def test_file_doc_attached_to_correct_name(self):
        doc = _make_doc(name="SINV-2026-00001")
        self._call(doc=doc)
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["attached_to_name"], "SINV-2026-00001")

    def test_file_doc_content_is_forwarded(self):
        self._call(content="<cfdi>data</cfdi>")
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["content"], "<cfdi>data</cfdi>")

    def test_file_is_marked_private(self):
        self._call()
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["is_private"], 1)

    def test_save_called_with_ignore_permissions(self):
        self._call()
        self._file_doc.save.assert_called_once_with(ignore_permissions=True)

    def test_returns_file_doc(self):
        result = self._call()
        self.assertIs(result, self._file_doc)


# ──────────────────────────────────────────────────────────────────────────────
# create_cfdi_log tests
# ──────────────────────────────────────────────────────────────────────────────

class TestCreateCfdiLog(unittest.TestCase):
    """create_cfdi_log inserts an MX CFDI Log entry with timbrado metadata."""

    def setUp(self):
        self._frappe = sys.modules["frappe"]
        self._log_doc = MagicMock()
        self._frappe.get_doc.reset_mock()
        self._frappe.get_doc.return_value = self._log_doc
        self._frappe.db.get_single_value = MagicMock(return_value="Finkok")

    def _call(self, doc=None, result=None, cfdi_type="I"):
        doc = doc or _make_doc()
        result = result or _make_stamp_result()
        return create_cfdi_log(doc, result, cfdi_type)

    def test_get_doc_called_with_mx_cfdi_log_doctype(self):
        self._call()
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["doctype"], "MX CFDI Log")

    def test_log_has_reference_doctype(self):
        doc = _make_doc(doctype="Sales Invoice")
        self._call(doc=doc)
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["reference_doctype"], "Sales Invoice")

    def test_log_has_reference_name(self):
        doc = _make_doc(name="SINV-001")
        self._call(doc=doc)
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["reference_name"], "SINV-001")

    def test_log_has_correct_cfdi_type(self):
        self._call(cfdi_type="E")
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["cfdi_type"], "E")

    def test_log_uuid_matches_stamp_result(self):
        result = _make_stamp_result(uuid="UUID-TEST-001")
        self._call(result=result)
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["uuid"], "UUID-TEST-001")

    def test_log_xml_stamped_matches_stamp_result(self):
        result = _make_stamp_result(xml_stamped="<timbrado/>")
        self._call(result=result)
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["xml_stamped"], "<timbrado/>")

    def test_log_stamped_at_matches_fecha_timbrado(self):
        result = _make_stamp_result(fecha_timbrado="2026-03-20T12:00:00")
        self._call(result=result)
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["stamped_at"], "2026-03-20T12:00:00")

    def test_log_status_is_stamped(self):
        self._call()
        call_kwargs = self._frappe.get_doc.call_args[0][0]
        self.assertEqual(call_kwargs["status"], "Stamped")

    def test_log_pac_used_is_read_from_settings(self):
        self._frappe.db.get_single_value.return_value = "SW Sapien"
        self._call()
        self._frappe.db.get_single_value.assert_called_with(
            "MX CFDI Settings", "pac_provider"
        )

    def test_insert_called_with_ignore_permissions(self):
        self._call()
        self._log_doc.insert.assert_called_once_with(ignore_permissions=True)


# ──────────────────────────────────────────────────────────────────────────────
# handle_stamp_error tests
# ──────────────────────────────────────────────────────────────────────────────

class TestHandleStampError(unittest.TestCase):
    """handle_stamp_error logs and re-raises via frappe.throw."""

    def setUp(self):
        self._frappe = sys.modules["frappe"]
        self._frappe.log_error.reset_mock()
        self._frappe.throw.reset_mock()
        self._frappe.throw.side_effect = Exception("frappe.throw called")

    def _call(self, doc=None, error_message="Something went wrong"):
        doc = doc or _make_doc(name="SINV-ERR-001")
        return handle_stamp_error(doc, "mx_stamp_status", error_message)

    def test_log_error_is_called(self):
        with self.assertRaises(Exception):
            self._call()
        self._frappe.log_error.assert_called_once()

    def test_log_error_title_contains_doc_name(self):
        doc = _make_doc(name="SINV-ERR-999")
        with self.assertRaises(Exception):
            handle_stamp_error(doc, "mx_stamp_status", "boom")
        kwargs = self._frappe.log_error.call_args[1]
        self.assertIn("SINV-ERR-999", kwargs.get("title", ""))

    def test_log_error_message_contains_sanitized_error(self):
        with self.assertRaises(Exception):
            self._call(error_message="RawError XYZ")
        kwargs = self._frappe.log_error.call_args[1]
        self.assertIn("RawError XYZ", kwargs.get("message", ""))

    def test_throw_is_called_after_log(self):
        with self.assertRaises(Exception):
            self._call()
        self._frappe.log_error.assert_called_once()
        self._frappe.throw.assert_called_once()

    def test_throw_message_references_doc_name(self):
        doc = _make_doc(name="SINV-THROW-01")
        with self.assertRaises(Exception):
            handle_stamp_error(doc, "mx_stamp_status", "err")
        throw_args = self._frappe.throw.call_args[0]
        self.assertIn("SINV-THROW-01", throw_args[0])

    def test_exception_propagates_to_caller(self):
        """The caller must receive an exception, not a silent failure."""
        with self.assertRaises(Exception):
            self._call()


# ──────────────────────────────────────────────────────────────────────────────
# check_stamp_rate_limit tests
# ──────────────────────────────────────────────────────────────────────────────

class TestCheckStampRateLimit(unittest.TestCase):
    """check_stamp_rate_limit enforces per-document and per-user hourly caps.

    The implementation makes two separate frappe.cache() calls:
      1. document-level key  → limit governed by max_attempts parameter
      2. user-level key      → hard-coded 30 attempts / hour

    Each call to frappe.cache() returns the same cache mock object.
    We use a single cache mock whose .get() returns the same counter
    for simplicity; tests that need distinct values configure individually.
    """

    def _make_cache(self, current_attempts: int):
        """Cache mock that always returns current_attempts for any key."""
        cache = MagicMock()
        cache.get = MagicMock(return_value=str(current_attempts).encode())
        cache.set = MagicMock()
        return cache

    def _install_cache(self, cache):
        """Make frappe.cache() return the given mock on every call."""
        sys.modules["frappe"].cache = MagicMock(return_value=cache)

    def setUp(self):
        self._frappe = sys.modules["frappe"]
        self._frappe.throw.reset_mock()
        self._frappe.throw.side_effect = Exception("frappe.throw called")
        # Default: zero attempts so tests start from a clean state
        default_cache = self._make_cache(0)
        self._install_cache(default_cache)
        self._cache = default_cache

    def _call(self, doc_name="SINV-0001", max_attempts=10, window_seconds=3600):
        return check_stamp_rate_limit(
            doc_name, max_attempts=max_attempts, window_seconds=window_seconds
        )

    # -- happy path -----------------------------------------------------------

    def test_zero_attempts_does_not_raise(self):
        self._call()  # should not raise

    def test_under_limit_cache_set_called(self):
        """set() must be called at least once (document key increment)."""
        self._call(max_attempts=10)
        self._cache.set.assert_called()

    def test_cache_set_first_call_stores_incremented_value(self):
        """The first set() call (document counter) must store attempts+1."""
        cache = self._make_cache(4)
        self._install_cache(cache)
        self._call(max_attempts=10)
        first_set_args = cache.set.call_args_list[0][0]
        self.assertEqual(first_set_args[1], 5)

    def test_cache_set_uses_correct_window_seconds(self):
        cache = self._make_cache(0)
        self._install_cache(cache)
        self._call(max_attempts=10, window_seconds=7200)
        # Both set() calls should use the same window_seconds
        for set_call in cache.set.call_args_list:
            self.assertEqual(set_call[1].get("expires_in_sec"), 7200)

    def test_first_cache_key_contains_document_name(self):
        cache = self._make_cache(0)
        self._install_cache(cache)
        self._call(doc_name="SINV-KEY-TEST")
        first_key = cache.set.call_args_list[0][0][0]
        self.assertIn("SINV-KEY-TEST", first_key)

    # -- document limit -------------------------------------------------------

    def test_at_document_limit_raises_exception(self):
        cache = self._make_cache(10)
        self._install_cache(cache)
        with self.assertRaises(Exception):
            self._call(max_attempts=10)
        self._frappe.throw.assert_called()

    def test_over_document_limit_raises_exception(self):
        cache = self._make_cache(15)
        self._install_cache(cache)
        with self.assertRaises(Exception):
            self._call(max_attempts=10)

    def test_custom_max_attempts_triggers_at_threshold(self):
        """With max_attempts=3, exactly 3 attempts must trigger the limit."""
        cache = self._make_cache(3)
        self._install_cache(cache)
        with self.assertRaises(Exception):
            self._call(max_attempts=3)

    def test_custom_max_attempts_allows_below_threshold(self):
        """With max_attempts=5, 4 existing attempts must not raise."""
        cache = self._make_cache(4)
        self._install_cache(cache)
        self._call(max_attempts=5)  # should not raise

    def test_throw_message_contains_document_name(self):
        cache = self._make_cache(10)
        self._install_cache(cache)
        with self.assertRaises(Exception):
            self._call(doc_name="SINV-LIMIT-01", max_attempts=10)
        throw_args = self._frappe.throw.call_args[0]
        self.assertIn("SINV-LIMIT-01", throw_args[0])

    # -- user limit -----------------------------------------------------------

    def test_user_limit_exceeded_raises_exception(self):
        """When the user has >= 30 attempts, frappe.throw must be called."""
        # The function first checks the document counter (OK at 0),
        # then checks the user counter.  We need get() to return 0 for the
        # first call and 30 for the second.
        call_count = {"n": 0}

        def _get(key):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return b"0"   # document attempts — under limit
            return b"30"      # user attempts — at limit

        cache = MagicMock()
        cache.get = _get
        cache.set = MagicMock()
        self._install_cache(cache)
        with self.assertRaises(Exception):
            self._call(max_attempts=10)
        self._frappe.throw.assert_called()

    # -- edge cases -----------------------------------------------------------

    def test_none_cache_value_treated_as_zero(self):
        """Cold start (None from cache) must not raise for first attempt."""
        cache = MagicMock()
        cache.get = MagicMock(return_value=None)
        cache.set = MagicMock()
        self._install_cache(cache)
        self._call(max_attempts=10)  # should not raise
        cache.set.assert_called()

    def test_second_set_call_uses_user_key(self):
        """The second cache.set() call must operate on the user-scoped key."""
        cache = self._make_cache(0)
        self._install_cache(cache)
        self._call()
        second_key = cache.set.call_args_list[1][0][0]
        self.assertIn("user", second_key)


if __name__ == "__main__":
    unittest.main()
