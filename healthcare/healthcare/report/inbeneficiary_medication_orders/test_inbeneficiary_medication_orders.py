# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import datetime

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, now_datetime

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
from healthcare.healthcare.report.inbeneficiary_medication_orders.inbeneficiary_medication_orders import (
	execute,
)


class TestInbeneficiaryMedicationOrders(FrappeTestCase):
	@classmethod
	def setUpClass(self):
		frappe.db.sql("delete from `tabInbeneficiary Medication Order` where company='_Test Company'")
		frappe.db.sql("delete from `tabInbeneficiary Medication Entry` where company='_Test Company'")
		self.beneficiary = create_beneficiary()
		self.ip_record = create_records(self.beneficiary)

	def test_inbeneficiary_medication_orders_report(self):
		filters = {
			"company": "_Test Company",
			"from_date": getdate(),
			"to_date": getdate(),
			"beneficiary": "_Test IPD Beneficiary",
			"service_unit": "_Test Service Unit Ip Occupancy - _TC",
		}

		report = execute(filters)

		expected_data = [
			{
				"beneficiary": "_Test IPD Beneficiary",
				"inbeneficiary_record": self.ip_record.name,
				"practitioner": None,
				"drug": "Dextromethorphan",
				"drug_name": "Dextromethorphan",
				"dosage": 1.0,
				"dosage_form": "Tablet",
				"date": getdate(),
				"time": datetime.timedelta(seconds=32400),
				"is_completed": 0,
				"healthcare_service_unit": "_Test Service Unit Ip Occupancy - _TC",
			},
			{
				"beneficiary": "_Test IPD Beneficiary",
				"inbeneficiary_record": self.ip_record.name,
				"practitioner": None,
				"drug": "Dextromethorphan",
				"drug_name": "Dextromethorphan",
				"dosage": 1.0,
				"dosage_form": "Tablet",
				"date": getdate(),
				"time": datetime.timedelta(seconds=50400),
				"is_completed": 0,
				"healthcare_service_unit": "_Test Service Unit Ip Occupancy - _TC",
			},
			{
				"beneficiary": "_Test IPD Beneficiary",
				"inbeneficiary_record": self.ip_record.name,
				"practitioner": None,
				"drug": "Dextromethorphan",
				"drug_name": "Dextromethorphan",
				"dosage": 1.0,
				"dosage_form": "Tablet",
				"date": getdate(),
				"time": datetime.timedelta(seconds=75600),
				"is_completed": 0,
				"healthcare_service_unit": "_Test Service Unit Ip Occupancy - _TC",
			},
		]

		self.assertEqual(expected_data, report[1])

		filters = frappe._dict(from_date=getdate(), to_date=getdate(), from_time="", to_time="")
		ipme = create_ipme(filters)
		ipme.submit()

		filters = {
			"company": "_Test Company",
			"from_date": getdate(),
			"to_date": getdate(),
			"beneficiary": "_Test IPD Beneficiary",
			"service_unit": "_Test Service Unit Ip Occupancy - _TC",
			"show_completed_orders": 0,
		}

		report = execute(filters)
		self.assertEqual(len(report[1]), 0)

	def tearDown(self):
		if frappe.db.get_value("Beneficiary", self.beneficiary, "inbeneficiary_record"):
			# cleanup - Discharge
			schedule_discharge(frappe.as_json({"beneficiary": self.beneficiary}))
			self.ip_record.reload()
			mark_invoiced_inbeneficiary_occupancy(self.ip_record)

			self.ip_record.reload()
			discharge_beneficiary(self.ip_record)

		for entry in frappe.get_all("Inbeneficiary Medication Entry"):
			doc = frappe.get_doc("Inbeneficiary Medication Entry", entry.name)
			doc.cancel()
			doc.delete()

		for entry in frappe.get_all("Inbeneficiary Medication Order"):
			doc = frappe.get_doc("Inbeneficiary Medication Order", entry.name)
			doc.cancel()
			doc.delete()


def create_records(beneficiary):
	frappe.db.sql("""delete from `tabInbeneficiary Record`""")

	# Admit
	ip_record = create_inbeneficiary(beneficiary)
	ip_record.expected_length_of_stay = 0
	ip_record.save()
	ip_record.reload()
	service_unit = get_healthcare_service_unit("_Test Service Unit Ip Occupancy")
	admit_beneficiary(ip_record, service_unit, now_datetime())

	ipmo = create_ipmo(beneficiary)
	ipmo.submit()

	return ip_record
