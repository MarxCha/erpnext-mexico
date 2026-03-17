# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MXDigitalCertificate(Document):
	def validate(self):
		self.validate_rfc()

	def validate_rfc(self):
		"""Valida formato de RFC."""
		from erpnext_mexico.utils.rfc_validator import validate_rfc

		if self.mx_rfc:
			validate_rfc(self.mx_rfc)
