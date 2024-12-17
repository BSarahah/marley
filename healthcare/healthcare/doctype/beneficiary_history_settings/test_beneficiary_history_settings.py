# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, strip_html

from healthcare.healthcare.doctype.beneficiary_appointment.test_beneficiary_appointment import (
	create_beneficiary,
)


class TestBeneficiaryHistorySettings(FrappeTestCase):
	def setUp(self):
		dt = create_custom_doctype()
		settings = frappe.get_single("Beneficiary History Settings")
		settings.append(
			"custom_doctypes",
			{
				"document_type": dt.name,
				"date_fieldname": "date",
				"selected_fields": json.dumps(
					[
						{"label": "Date", "fieldname": "date", "fieldtype": "Date"},
						{"label": "Rating", "fieldname": "rating", "fieldtype": "Rating"},
						{"label": "Feedback", "fieldname": "feedback", "fieldtype": "Small Text"},
					]
				),
			},
		)
		settings.save()

	def test_custom_doctype_medical_record(self):
		# tests for medical record creation of standard doctypes in test_beneficiary_medical_record.py
		beneficiary = create_beneficiary()
		doc = create_doc(beneficiary)
		# check for medical record
		medical_rec = frappe.db.exists(
			"Beneficiary Medical Record", {"status": "Open", "reference_name": doc.name}
		)
		self.assertTrue(medical_rec)

		medical_rec = frappe.get_doc("Beneficiary Medical Record", medical_rec)
		expected_subject = "Date:{0}Rating:0.3Feedback:Test Beneficiary History Settings".format(
			frappe.utils.format_date(getdate())
		)
		self.assertEqual(strip_html(medical_rec.subject), expected_subject)
		self.assertEqual(medical_rec.beneficiary, beneficiary)
		self.assertEqual(medical_rec.communication_date, getdate())


def create_custom_doctype():
	if not frappe.db.exists("DocType", "Test Beneficiary Feedback"):
		doc = frappe.get_doc(
			{
				"doctype": "DocType",
				"module": "Healthcare",
				"custom": 1,
				"is_submittable": 1,
				"fields": [
					{"label": "Date", "fieldname": "date", "fieldtype": "Date"},
					{"label": "Beneficiary", "fieldname": "beneficiary", "fieldtype": "Link", "options": "Beneficiary"},
					{"label": "Rating", "fieldname": "rating", "fieldtype": "Rating"},
					{"label": "Feedback", "fieldname": "feedback", "fieldtype": "Small Text"},
				],
				"permissions": [{"role": "System Manager", "read": 1}],
				"name": "Test Beneficiary Feedback",
			}
		)
		doc.insert()
		return doc
	else:
		return frappe.get_doc("DocType", "Test Beneficiary Feedback")


def create_doc(beneficiary):
	doc = frappe.get_doc(
		{
			"doctype": "Test Beneficiary Feedback",
			"beneficiary": beneficiary,
			"date": getdate(),
			"rating": 0.3,
			"feedback": "Test Beneficiary History Settings",
		}
	).insert()
	doc.submit()

	return doc
