# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime

from healthcare.healthcare.doctype.inbeneficiary_record.inbeneficiary_record import (
	admit_beneficiary,
	discharge_beneficiary,
	schedule_discharge,
)
from healthcare.healthcare.doctype.inbeneficiary_record.test_inbeneficiary_record import (
	create_inbeneficiary,
	create_beneficiary,
	get_healthcare_service_unit,
	mark_invoiced_inbeneficiary_occupancy,
)


class TestInbeneficiaryMedicationOrder(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("""delete from `tabInbeneficiary Record`""")
		self.beneficiary = create_beneficiary()

		# Admit
		ip_record = create_inbeneficiary(self.beneficiary)
		ip_record.expected_length_of_stay = 0
		ip_record.save()
		ip_record.reload()
		service_unit = get_healthcare_service_unit()
		admit_beneficiary(ip_record, service_unit, now_datetime())
		self.ip_record = ip_record

	def test_order_creation(self):
		ipmo = create_ipmo(self.beneficiary)
		ipmo.submit()
		ipmo.reload()

		# 3 dosages per day for 2 days
		self.assertEqual(len(ipmo.medication_orders), 6)
		self.assertEqual(ipmo.medication_orders[0].date, add_days(getdate(), -1))

		prescription_dosage = frappe.get_doc("Prescription Dosage", "1-1-1")
		for i in range(len(prescription_dosage.dosage_strength)):
			self.assertEqual(
				ipmo.medication_orders[i].time, prescription_dosage.dosage_strength[i].strength_time
			)

		self.assertEqual(ipmo.medication_orders[3].date, getdate())

	def test_inbeneficiary_validation(self):
		# Discharge
		schedule_discharge(frappe.as_json({"beneficiary": self.beneficiary}))

		self.ip_record.reload()
		mark_invoiced_inbeneficiary_occupancy(self.ip_record)

		self.ip_record.reload()
		discharge_beneficiary(self.ip_record)

		ipmo = create_ipmo(self.beneficiary)
		# inbeneficiary validation
		self.assertRaises(frappe.ValidationError, ipmo.insert)

	def test_status(self):
		ipmo = create_ipmo(self.beneficiary)
		ipmo.submit()
		ipmo.reload()

		self.assertEqual(ipmo.status, "Pending")

		filters = frappe._dict(
			from_date=add_days(getdate(), -1), to_date=add_days(getdate(), -1), from_time="", to_time=""
		)
		ipme = create_ipme(filters)
		ipme.submit()
		ipmo.reload()
		self.assertEqual(ipmo.status, "In Process")

		filters = frappe._dict(from_date=getdate(), to_date=getdate(), from_time="", to_time="")
		ipme = create_ipme(filters)
		ipme.submit()
		ipmo.reload()
		self.assertEqual(ipmo.status, "Completed")

	def tearDown(self):
		if frappe.db.get_value("Beneficiary", self.beneficiary, "inbeneficiary_record"):
			# cleanup - Discharge
			schedule_discharge(frappe.as_json({"beneficiary": self.beneficiary}))
			self.ip_record.reload()
			mark_invoiced_inbeneficiary_occupancy(self.ip_record)

			self.ip_record.reload()
			discharge_beneficiary(self.ip_record)

		for doctype in ["Inbeneficiary Medication Entry", "Inbeneficiary Medication Order"]:
			frappe.db.sql("delete from `tab{doctype}`".format(doctype=doctype))


def create_dosage_form():
	if not frappe.db.exists("Dosage Form", "Tablet"):
		frappe.get_doc({"doctype": "Dosage Form", "dosage_form": "Tablet"}).insert()


def create_drug(item=None):
	if not item:
		item = "Dextromethorphan"
	drug = frappe.db.exists("Item", {"item_code": "Dextromethorphan"})
	if not drug:
		drug = frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": "Dextromethorphan",
				"item_name": "Dextromethorphan",
				"item_group": "Products",
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"valuation_rate": 50,
				"opening_stock": 20,
			}
		).insert()


def get_orders():
	create_dosage_form()
	create_drug()
	return {
		"drug_code": "Dextromethorphan",
		"drug_name": "Dextromethorphan",
		"dosage": "1-1-1",
		"dosage_form": "Tablet",
		"period": "2 Day",
	}


def create_ipmo(beneficiary):
	orders = get_orders()
	ipmo = frappe.new_doc("Inbeneficiary Medication Order")
	ipmo.beneficiary = beneficiary
	ipmo.company = "_Test Company"
	ipmo.start_date = add_days(getdate(), -1)
	ipmo.add_order_entries(orders)

	return ipmo


def create_ipme(filters, update_stock=0):
	ipme = frappe.new_doc("Inbeneficiary Medication Entry")
	ipme.company = "_Test Company"
	ipme.posting_date = getdate()
	ipme.update_stock = update_stock
	if update_stock:
		ipme.warehouse = "Stores - _TC"
	for key, value in filters.items():
		ipme.set(key, value)
	ipme = ipme.get_medication_orders()

	return ipme
