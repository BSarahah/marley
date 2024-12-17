# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, now_datetime

from healthcare.healthcare.doctype.healthcare_settings.healthcare_settings import get_account
from healthcare.healthcare.doctype.inbeneficiary_medication_entry.inbeneficiary_medication_entry import (
	get_drug_shortage_map,
	make_difference_stock_entry,
)
from healthcare.healthcare.doctype.inbeneficiary_medication_order.test_inbeneficiary_medication_order import (
	create_ipme,
	create_ipmo,
)
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


class TestInbeneficiaryMedicationEntry(FrappeTestCase):
	def setUp(self):
		frappe.db.sql("""delete from `tabInbeneficiary Record`""")
		frappe.db.sql("""delete from `tabInbeneficiary Medication Order`""")
		frappe.db.sql("""delete from `tabInbeneficiary Medication Entry`""")
		self.beneficiary = create_beneficiary()

		# Admit
		ip_record = create_inbeneficiary(self.beneficiary)
		ip_record.expected_length_of_stay = 0
		ip_record.save()
		ip_record.reload()
		service_unit = get_healthcare_service_unit()
		admit_beneficiary(ip_record, service_unit, now_datetime())
		self.ip_record = ip_record

	def test_filters_for_fetching_pending_mo(self):
		ipmo = create_ipmo(self.beneficiary)
		ipmo.submit()
		ipmo.reload()

		date = add_days(getdate(), -1)
		filters = frappe._dict(
			from_date=date,
			to_date=date,
			from_time="",
			to_time="",
			item_code="Dextromethorphan",
			beneficiary=self.beneficiary,
		)

		ipme = create_ipme(filters, update_stock=0)

		# 3 dosages per day
		self.assertEqual(len(ipme.medication_orders), 3)
		self.assertEqual(getdate(ipme.medication_orders[0].datetime), date)

	def test_ipme_with_stock_update(self):
		ipmo = create_ipmo(self.beneficiary)
		ipmo.submit()
		ipmo.reload()

		date = add_days(getdate(), -1)
		filters = frappe._dict(
			from_date=date,
			to_date=date,
			from_time="",
			to_time="",
			item_code="Dextromethorphan",
			beneficiary=self.beneficiary,
		)

		make_stock_entry()
		ipme = create_ipme(filters, update_stock=1)
		ipme.submit()
		ipme.reload()

		# test order completed
		is_order_completed = frappe.db.get_value(
			"Inbeneficiary Medication Order Entry", ipme.medication_orders[0].against_imoe, "is_completed"
		)
		self.assertEqual(is_order_completed, 1)

		# test stock entry
		stock_entry = frappe.db.exists("Stock Entry", {"inbeneficiary_medication_entry": ipme.name})
		self.assertTrue(stock_entry)

		# check references
		stock_entry = frappe.get_doc("Stock Entry", stock_entry)
		self.assertEqual(stock_entry.items[0].beneficiary, self.beneficiary)
		self.assertEqual(
			stock_entry.items[0].inbeneficiary_medication_entry_child, ipme.medication_orders[0].name
		)

	def test_drug_shortage_stock_entry(self):
		ipmo = create_ipmo(self.beneficiary)
		ipmo.submit()
		ipmo.reload()

		date = add_days(getdate(), -1)
		filters = frappe._dict(
			from_date=date,
			to_date=date,
			from_time="",
			to_time="",
			item_code="Dextromethorphan",
			beneficiary=self.beneficiary,
		)

		# check drug shortage
		ipme = create_ipme(filters, update_stock=1)
		ipme.warehouse = "Finished Goods - _TC"
		ipme.save()
		drug_shortage = get_drug_shortage_map(ipme.medication_orders, ipme.warehouse)
		self.assertEqual(drug_shortage.get("Dextromethorphan"), 3)

		# check material transfer for drug shortage
		make_stock_entry()
		stock_entry = make_difference_stock_entry(ipme.name)
		self.assertEqual(stock_entry.items[0].item_code, "Dextromethorphan")
		self.assertEqual(stock_entry.items[0].qty, 3)
		stock_entry.from_warehouse = "Stores - _TC"
		stock_entry.submit()

		ipme.reload()
		ipme.submit()

	def tearDown(self):
		# cleanup - Discharge
		schedule_discharge(frappe.as_json({"beneficiary": self.beneficiary}))
		self.ip_record.reload()
		mark_invoiced_inbeneficiary_occupancy(self.ip_record)

		self.ip_record.reload()
		discharge_beneficiary(self.ip_record)

		for entry in frappe.get_all("Inbeneficiary Medication Entry"):
			doc = frappe.get_doc("Inbeneficiary Medication Entry", entry.name)
			doc.cancel()

		for entry in frappe.get_all("Inbeneficiary Medication Order"):
			doc = frappe.get_doc("Inbeneficiary Medication Order", entry.name)
			doc.cancel()


def make_stock_entry(warehouse=None):
	frappe.db.set_value(
		"Company",
		"_Test Company",
		{
			"stock_adjustment_account": "Stock Adjustment - _TC",
			"default_inventory_account": "Stock In Hand - _TC",
		},
	)
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type = "Material Receipt"
	stock_entry.company = "_Test Company"
	stock_entry.to_warehouse = warehouse or "Stores - _TC"
	expense_account = get_account(None, "expense_account", "Healthcare Settings", "_Test Company")
	se_child = stock_entry.append("items")
	se_child.item_code = "Dextromethorphan"
	se_child.item_name = "Dextromethorphan"
	se_child.uom = "Nos"
	se_child.stock_uom = "Nos"
	se_child.qty = 6
	se_child.t_warehouse = "Stores - _TC"
	# in stock uom
	se_child.conversion_factor = 1.0
	se_child.expense_account = expense_account
	stock_entry.submit()
