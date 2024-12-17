# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class TreatmentPlanTemplate(Document):
	def validate(self):
		self.validate_age()

	def validate_age(self):
		if self.beneficiary_age_from and self.beneficiary_age_from < 0:
			frappe.throw(_("Beneficiary Age From cannot be less than 0"))
		if self.beneficiary_age_to and self.beneficiary_age_to < 0:
			frappe.throw(_("Beneficiary Age To cannot be less than 0"))
		if self.beneficiary_age_to and self.beneficiary_age_from and self.beneficiary_age_to < self.beneficiary_age_from:
			frappe.throw(_("Beneficiary Age To cannot be less than Beneficiary Age From"))
