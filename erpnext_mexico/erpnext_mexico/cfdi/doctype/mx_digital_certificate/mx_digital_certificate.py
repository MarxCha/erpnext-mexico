# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MXDigitalCertificate(Document):
	def validate(self):
		self.validate_rfc()
		if self.certificate_file:
			self.parse_certificate()

	def validate_rfc(self):
		"""Valida formato de RFC."""
		from erpnext_mexico.utils.rfc_validator import validate_rfc

		if self.mx_rfc:
			validate_rfc(self.mx_rfc)

	def parse_certificate(self):
		"""Parse .cer file to extract certificate metadata using satcfdi."""
		if not self.certificate_file:
			return
		if not self.certificate_file.lower().endswith('.cer'):
			frappe.throw(_("El archivo de certificado debe tener extensión .cer"))

		try:
			from cryptography import x509
			from cryptography.hazmat.backends import default_backend

			cer_bytes = self._get_file_bytes(self.certificate_file)
			if len(cer_bytes) > 10240:
				frappe.throw(_("Archivo de certificado demasiado grande (máximo 10KB)"))

			cert = x509.load_der_x509_certificate(cer_bytes, default_backend())

			# Extract serial number — SAT stores as decimal string
			self.certificate_number = str(cert.serial_number)

			# Validity dates
			self.valid_from = cert.not_valid_before_utc.strftime("%Y-%m-%d %H:%M:%S")
			self.valid_to = cert.not_valid_after_utc.strftime("%Y-%m-%d %H:%M:%S")

			# Extract subject common name (certificate owner)
			try:
				cn = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
				self.certificate_owner = cn[0].value if cn else ""
			except Exception:
				self.certificate_owner = ""

			# Auto-set status based on expiry
			from frappe.utils import now_datetime

			if cert.not_valid_after_utc.replace(tzinfo=None) < now_datetime():
				self.status = "Expirado"
			else:
				self.status = "Activo"

		except ImportError:
			frappe.msgprint(
				"Instale la biblioteca 'cryptography' para parsear certificados CSD automáticamente.",
				indicator="orange",
			)
		except Exception as e:
			frappe.msgprint(
				f"No se pudo parsear el certificado: {str(e)}",
				indicator="orange",
			)

	def _get_file_bytes(self, file_url: str) -> bytes:
		"""Read file content from Frappe file system."""
		if not file_url:
			return b""
		from frappe.utils.file_manager import get_file

		_fname, content = get_file(file_url)
		if isinstance(content, str):
			content = content.encode()
		return content
