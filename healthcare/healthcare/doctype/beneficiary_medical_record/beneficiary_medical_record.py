# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document


class BeneficiaryMedicalRecord(Document):
	def after_insert(self):
		if self.reference_doctype == "Beneficiary Medical Record":
			frappe.db.set_value("Beneficiary Medical Record", self.name, "reference_name", self.name)
