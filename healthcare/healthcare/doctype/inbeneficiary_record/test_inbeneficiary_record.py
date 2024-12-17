# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime, today
from frappe.utils.make_random import get_random

from healthcare.healthcare.doctype.inbeneficiary_record.inbeneficiary_record import (
	admit_beneficiary,
	discharge_beneficiary,
	schedule_discharge,
)
from healthcare.healthcare.doctype.lab_test.test_lab_test import create_beneficiary_encounter
from healthcare.healthcare.utils import get_encounters_to_invoice


class TestInbeneficiaryRecord(FrappeTestCase):
	def test_admit_and_discharge(self):
		frappe.db.sql("""delete from `tabInbeneficiary Record`""")
		beneficiary = create_beneficiary()
		# Schedule Admission
		ip_record = create_inbeneficiary(beneficiary)
		ip_record.expected_length_of_stay = 0
		ip_record.save(ignore_permissions=True)
		self.assertEqual(ip_record.name, frappe.db.get_value("Beneficiary", beneficiary, "inbeneficiary_record"))
		self.assertEqual(ip_record.status, frappe.db.get_value("Beneficiary", beneficiary, "inbeneficiary_status"))

		# Admit
		service_unit = get_healthcare_service_unit()
		admit_beneficiary(ip_record, service_unit, now_datetime())
		self.assertEqual("Admitted", frappe.db.get_value("Beneficiary", beneficiary, "inbeneficiary_status"))
		self.assertEqual(
			"Occupied", frappe.db.get_value("Healthcare Service Unit", service_unit, "occupancy_status")
		)

		# Discharge
		schedule_discharge(frappe.as_json({"beneficiary": beneficiary}))
		self.assertEqual(
			"Vacant", frappe.db.get_value("Healthcare Service Unit", service_unit, "occupancy_status")
		)

		ip_record1 = frappe.get_doc("Inbeneficiary Record", ip_record.name)
		# Validate Pending Invoices
		self.assertRaises(frappe.ValidationError, ip_record.discharge)
		mark_invoiced_inbeneficiary_occupancy(ip_record1)

		discharge_beneficiary(ip_record1)

		self.assertEqual(None, frappe.db.get_value("Beneficiary", beneficiary, "inbeneficiary_record"))
		self.assertEqual(None, frappe.db.get_value("Beneficiary", beneficiary, "inbeneficiary_status"))

	def test_allow_discharge_despite_unbilled_services(self):
		frappe.db.sql("""delete from `tabInbeneficiary Record`""")
		setup_inbeneficiary_settings(key="allow_discharge_despite_unbilled_services", value=1)
		beneficiary = create_beneficiary()
		# Schedule Admission
		ip_record = create_inbeneficiary(beneficiary)
		ip_record.expected_length_of_stay = 0
		ip_record.save(ignore_permissions=True)

		# Admit
		service_unit = get_healthcare_service_unit()
		admit_beneficiary(ip_record, service_unit, now_datetime())

		# Discharge
		schedule_discharge(frappe.as_json({"beneficiary": beneficiary}))
		self.assertEqual(
			"Vacant", frappe.db.get_value("Healthcare Service Unit", service_unit, "occupancy_status")
		)

		ip_record = frappe.get_doc("Inbeneficiary Record", ip_record.name)
		# Should not validate Pending Invoices
		ip_record.discharge()

		self.assertEqual(None, frappe.db.get_value("Beneficiary", beneficiary, "inbeneficiary_record"))
		self.assertEqual(None, frappe.db.get_value("Beneficiary", beneficiary, "inbeneficiary_status"))

		setup_inbeneficiary_settings(key="allow_discharge_despite_unbilled_services", value=0)

	def test_do_not_bill_beneficiary_encounters_for_inbeneficiarys(self):
		frappe.db.sql("""delete from `tabInbeneficiary Record`""")
		setup_inbeneficiary_settings(key="do_not_bill_inbeneficiary_encounters", value=1)
		beneficiary = create_beneficiary()
		# Schedule Admission
		ip_record = create_inbeneficiary(beneficiary)
		ip_record.expected_length_of_stay = 0
		ip_record.save(ignore_permissions=True)

		# Admit
		service_unit = get_healthcare_service_unit()
		admit_beneficiary(ip_record, service_unit, now_datetime())

		# Beneficiary Encounter
		beneficiary_encounter = create_beneficiary_encounter()
		encounters = get_encounters_to_invoice(beneficiary, "_Test Company")
		encounter_ids = [entry.reference_name for entry in encounters]
		self.assertFalse(beneficiary_encounter.name in encounter_ids)

		# Discharge
		schedule_discharge(frappe.as_json({"beneficiary": beneficiary}))
		self.assertEqual(
			"Vacant", frappe.db.get_value("Healthcare Service Unit", service_unit, "occupancy_status")
		)

		ip_record = frappe.get_doc("Inbeneficiary Record", ip_record.name)
		mark_invoiced_inbeneficiary_occupancy(ip_record)
		discharge_beneficiary(ip_record)
		setup_inbeneficiary_settings(key="do_not_bill_inbeneficiary_encounters", value=0)

	def test_validate_overlap_admission(self):
		frappe.db.sql("""delete from `tabInbeneficiary Record`""")
		beneficiary = create_beneficiary()

		ip_record = create_inbeneficiary(beneficiary)
		ip_record.expected_length_of_stay = 0
		ip_record.save(ignore_permissions=True)
		ip_record_new = create_inbeneficiary(beneficiary)
		ip_record_new.expected_length_of_stay = 0
		self.assertRaises(frappe.ValidationError, ip_record_new.save)

		service_unit = get_healthcare_service_unit()
		admit_beneficiary(ip_record, service_unit, now_datetime())
		ip_record_new = create_inbeneficiary(beneficiary)
		self.assertRaises(frappe.ValidationError, ip_record_new.save)
		frappe.db.sql("""delete from `tabInbeneficiary Record`""")


def mark_invoiced_inbeneficiary_occupancy(ip_record):
	if ip_record.inbeneficiary_occupancies:
		for inbeneficiary_occupancy in ip_record.inbeneficiary_occupancies:
			inbeneficiary_occupancy.invoiced = 1
		ip_record.save(ignore_permissions=True)


def setup_inbeneficiary_settings(key, value):
	settings = frappe.get_single("Healthcare Settings")
	settings.set(key, value)
	settings.save()


def create_inbeneficiary(beneficiary):
	beneficiary_obj = frappe.get_doc("Beneficiary", beneficiary)
	inbeneficiary_record = frappe.new_doc("Inbeneficiary Record")
	inbeneficiary_record.beneficiary = beneficiary
	inbeneficiary_record.beneficiary_name = beneficiary_obj.beneficiary_name
	inbeneficiary_record.gender = beneficiary_obj.sex
	inbeneficiary_record.blood_group = beneficiary_obj.blood_group
	inbeneficiary_record.dob = beneficiary_obj.dob
	inbeneficiary_record.mobile = beneficiary_obj.mobile
	inbeneficiary_record.email = beneficiary_obj.email
	inbeneficiary_record.phone = beneficiary_obj.phone
	inbeneficiary_record.inbeneficiary = "Scheduled"
	inbeneficiary_record.scheduled_date = today()
	inbeneficiary_record.company = "_Test Company"
	return inbeneficiary_record


def get_healthcare_service_unit(unit_name=None):
	if not unit_name:
		service_unit = get_random(
			"Healthcare Service Unit", filters={"inbeneficiary_occupancy": 1, "company": "_Test Company"}
		)
	else:
		service_unit = frappe.db.exists(
			"Healthcare Service Unit", {"healthcare_service_unit_name": unit_name}
		)

	if not service_unit:
		service_unit = frappe.new_doc("Healthcare Service Unit")
		service_unit.healthcare_service_unit_name = unit_name or "_Test Service Unit Ip Occupancy"
		service_unit.company = "_Test Company"
		service_unit.service_unit_type = get_service_unit_type()
		service_unit.inbeneficiary_occupancy = 1
		service_unit.occupancy_status = "Vacant"
		service_unit.is_group = 0
		service_unit_parent_name = frappe.db.exists(
			{
				"doctype": "Healthcare Service Unit",
				"healthcare_service_unit_name": "_Test All Healthcare Service Units",
				"is_group": 1,
			}
		)
		if not service_unit_parent_name:
			parent_service_unit = frappe.new_doc("Healthcare Service Unit")
			parent_service_unit.healthcare_service_unit_name = "_Test All Healthcare Service Units"
			parent_service_unit.is_group = 1
			parent_service_unit.save(ignore_permissions=True)
			service_unit.parent_healthcare_service_unit = parent_service_unit.name
		else:
			service_unit.parent_healthcare_service_unit = service_unit_parent_name
		service_unit.save(ignore_permissions=True)
		return service_unit.name
	return service_unit


def get_service_unit_type():
	service_unit_type = get_random("Healthcare Service Unit Type", filters={"inbeneficiary_occupancy": 1})

	if not service_unit_type:
		service_unit_type = frappe.new_doc("Healthcare Service Unit Type")
		service_unit_type.service_unit_type = "_Test Service Unit Type Ip Occupancy"
		service_unit_type.inbeneficiary_occupancy = 1
		service_unit_type.save(ignore_permissions=True)
		return service_unit_type.name
	return service_unit_type


def create_beneficiary():
	beneficiary = frappe.db.exists("Beneficiary", "_Test IPD Beneficiary")
	if not beneficiary:
		beneficiary = frappe.new_doc("Beneficiary")
		beneficiary.first_name = "_Test IPD Beneficiary"
		beneficiary.sex = "Female"
		beneficiary.save(ignore_permissions=True)
		beneficiary = beneficiary.name
	return beneficiary
