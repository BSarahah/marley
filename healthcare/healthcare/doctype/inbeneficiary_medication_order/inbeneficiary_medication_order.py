# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr

from healthcare.healthcare.doctype.beneficiary_encounter.beneficiary_encounter import (
	get_prescription_dates,
)


class InbeneficiaryMedicationOrder(Document):
	def validate(self):
		self.validate_inbeneficiary()
		self.validate_duplicate()
		self.set_total_orders()
		self.set_status()

	def on_submit(self):
		self.validate_inbeneficiary()
		self.set_status()

	def on_cancel(self):
		self.set_status()

	def validate_inbeneficiary(self):
		if not self.inbeneficiary_record:
			frappe.throw(_("No Inbeneficiary Record found against beneficiary {0}").format(self.beneficiary))

	def validate_duplicate(self):
		existing_mo = frappe.db.exists(
			"Inbeneficiary Medication Order",
			{
				"beneficiary_encounter": self.beneficiary_encounter,
				"docstatus": ("!=", 2),
				"name": ("!=", self.name),
			},
		)
		if existing_mo:
			frappe.throw(
				_("An Inbeneficiary Medication Order {0} against Beneficiary Encounter {1} already exists.").format(
					existing_mo, self.beneficiary_encounter
				),
				frappe.DuplicateEntryError,
			)

	def set_total_orders(self):
		self.db_set("total_orders", len(self.medication_orders))

	def set_status(self):
		status = {"0": "Draft", "1": "Submitted", "2": "Cancelled"}[cstr(self.docstatus or 0)]

		if self.docstatus == 1:
			if not self.completed_orders:
				status = "Pending"
			elif self.completed_orders < self.total_orders:
				status = "In Process"
			else:
				status = "Completed"

		self.db_set("status", status)

	@frappe.whitelist()
	def add_order_entries(self, order):
		if order.get("drug_code"):
			dosage = frappe.get_doc("Prescription Dosage", order.get("dosage"))
			dates = get_prescription_dates(order.get("period"), self.start_date)
			for date in dates:
				for dose in dosage.dosage_strength:
					entry = self.append("medication_orders")
					entry.drug = order.get("drug_code")
					entry.drug_name = frappe.db.get_value("Item", order.get("drug_code"), "item_name")
					entry.dosage = dose.strength
					entry.dosage_form = order.get("dosage_form")
					entry.date = date
					entry.time = dose.strength_time
			self.end_date = dates[-1]
		return

	@frappe.whitelist()
	def get_from_encounter(self, encounter):
		beneficiary_encounter = frappe.get_doc("Beneficiary Encounter", encounter)
		if not beneficiary_encounter.drug_prescription:
			return
		for drug in beneficiary_encounter.drug_prescription:
			self.add_order_entries(drug)
