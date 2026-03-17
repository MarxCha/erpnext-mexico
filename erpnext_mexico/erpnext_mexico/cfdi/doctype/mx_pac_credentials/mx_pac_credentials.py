# Copyright (c) 2026, MD Consultoría SC and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MXPACCredentials(Document):
	def validate(self):
		self.set_urls()

	def set_urls(self):
		"""Establece URLs según PAC y ambiente."""
		urls = {
			"Finkok": {
				"sandbox": {
					"stamp": "https://demo-facturacion.finkok.com/servicios/soap/stamp.wsdl",
					"cancel": "https://demo-facturacion.finkok.com/servicios/soap/cancel.wsdl",
				},
				"production": {
					"stamp": "https://facturacion.finkok.com/servicios/soap/stamp.wsdl",
					"cancel": "https://facturacion.finkok.com/servicios/soap/cancel.wsdl",
				},
			},
			"SW Sapien": {
				"sandbox": {
					"stamp": "https://services.test.sw.com.mx/cfdi33/stamp/v3/b64",
					"cancel": "https://services.test.sw.com.mx/cfdi33/cancel/csd",
				},
				"production": {
					"stamp": "https://services.sw.com.mx/cfdi33/stamp/v3/b64",
					"cancel": "https://services.sw.com.mx/cfdi33/cancel/csd",
				},
			},
		}
		env = "sandbox" if self.is_sandbox else "production"
		if self.pac_name and self.pac_name in urls:
			self.stamp_url = urls[self.pac_name][env]["stamp"]
			self.cancel_url = urls[self.pac_name][env]["cancel"]
