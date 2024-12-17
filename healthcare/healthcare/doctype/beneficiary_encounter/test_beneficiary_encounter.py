# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase

from healthcare.healthcare.doctype.beneficiary_encounter.beneficiary_encounter import BeneficiaryEncounter


class TestBeneficiaryEncounter(FrappeTestCase):
	def setUp(self):
		try:
			gender_m = frappe.get_doc({"doctype": "Gender", "gender": "MALE"}).insert()
			gender_f = frappe.get_doc({"doctype": "Gender", "gender": "FEMALE"}).insert()
		except frappe.exceptions.DuplicateEntryError:
			gender_m = frappe.get_doc({"doctype": "Gender", "gender": "MALE"})
			gender_f = frappe.get_doc({"doctype": "Gender", "gender": "FEMALE"})

		self.beneficiary_male = frappe.get_doc(
			{
				"doctype": "Beneficiary",
				"first_name": "John",
				"sex": gender_m.gender,
			}
		).insert()
		self.beneficiary_female = frappe.get_doc(
			{
				"doctype": "Beneficiary",
				"first_name": "Curie",
				"sex": gender_f.gender,
			}
		).insert()
		self.practitioner = frappe.get_doc(
			{
				"doctype": "Healthcare Practitioner",
				"first_name": "Doc",
				"sex": "MALE",
			}
		).insert()
		try:
			self.care_plan_male = frappe.get_doc(
				{
					"doctype": "Treatment Plan Template",
					"template_name": "test plan - m",
					"gender": gender_m.gender,
				}
			).insert()
			self.care_plan_female = frappe.get_doc(
				{
					"doctype": "Treatment Plan Template",
					"template_name": "test plan - f",
					"gender": gender_f.gender,
				}
			).insert()
		except frappe.exceptions.DuplicateEntryError:
			self.care_plan_male = frappe.get_doc(
				{
					"doctype": "Treatment Plan Template",
					"template_name": "test plan - m",
					"gender": gender_m.gender,
				}
			)
			self.care_plan_female = frappe.get_doc(
				{
					"doctype": "Treatment Plan Template",
					"template_name": "test plan - f",
					"gender": gender_f.gender,
				}
			)

	def test_treatment_plan_template_filter(self):
		encounter = frappe.get_doc(
			{
				"doctype": "Beneficiary Encounter",
				"beneficiary": self.beneficiary_male.name,
				"practitioner": self.practitioner.name,
			}
		).insert()
		plans = BeneficiaryEncounter.get_applicable_treatment_plans(encounter.as_dict())
		self.assertEqual(plans[0]["name"], self.care_plan_male.template_name)

		encounter = frappe.get_doc(
			{
				"doctype": "Beneficiary Encounter",
				"beneficiary": self.beneficiary_female.name,
				"practitioner": self.practitioner.name,
			}
		).insert()
		plans = BeneficiaryEncounter.get_applicable_treatment_plans(encounter.as_dict())
		self.assertEqual(plans[0]["name"], self.care_plan_female.template_name)
