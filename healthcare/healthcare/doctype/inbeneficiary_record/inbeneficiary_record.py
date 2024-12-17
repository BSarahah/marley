# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import json

import frappe
from frappe import _
from frappe.desk.reportview import get_match_cond
from frappe.model.document import Document
from frappe.utils import get_datetime, get_link_to_form, getdate, now_datetime, today

from healthcare.healthcare.doctype.nursing_task.nursing_task import NursingTask
from healthcare.healthcare.utils import validate_nursing_tasks


class InbeneficiaryRecord(Document):
	def after_insert(self):
		frappe.db.set_value("Beneficiary", self.beneficiary, "inbeneficiary_record", self.name)
		frappe.db.set_value("Beneficiary", self.beneficiary, "inbeneficiary_status", self.status)

		if self.admission_encounter:  # Update encounter
			frappe.db.set_value(
				"Beneficiary Encounter",
				self.admission_encounter,
				{"inbeneficiary_record": self.name, "inbeneficiary_status": self.status},
			)

			filters = {"order_group": self.admission_encounter, "docstatus": 1}
			medication_requests = frappe.get_all("Medication Request", filters, ["name"])
			service_requests = frappe.get_all("Service Request", filters, ["name"])

			for service_request in service_requests:
				frappe.db.set_value(
					"Service Request",
					service_request.name,
					{"inbeneficiary_record": self.name, "inbeneficiary_status": self.status},
				)

			for medication_request in medication_requests:
				frappe.db.set_value(
					"Medication Request",
					medication_request.name,
					{"inbeneficiary_record": self.name, "inbeneficiary_status": self.status},
				)

		if self.admission_nursing_checklist_template:
			NursingTask.create_nursing_tasks_from_template(
				template=self.admission_nursing_checklist_template,
				doc=self,
			)

	def validate(self):
		self.validate_dates()
		self.validate_already_scheduled_or_admitted()
		if self.status in ["Discharged", "Cancelled"]:
			frappe.db.set_value(
				"Beneficiary", self.beneficiary, {"inbeneficiary_status": None, "inbeneficiary_record": None}
			)

	def validate_dates(self):
		if (getdate(self.expected_discharge) < getdate(self.scheduled_date)) or (
			getdate(self.discharge_ordered_date) < getdate(self.scheduled_date)
		):
			frappe.throw(_("Expected and Discharge dates cannot be less than Admission Schedule date"))

		for entry in self.inbeneficiary_occupancies:
			if (
				entry.check_in
				and entry.check_out
				and get_datetime(entry.check_in) > get_datetime(entry.check_out)
			):
				frappe.throw(
					_("Row #{0}: Check Out datetime cannot be less than Check In datetime").format(entry.idx)
				)

	def validate_already_scheduled_or_admitted(self):
		query = """
			select name, status
			from `tabInbeneficiary Record`
			where (status = 'Admitted' or status = 'Admission Scheduled')
			and name != %(name)s and beneficiary = %(beneficiary)s
			"""

		ip_record = frappe.db.sql(query, {"name": self.name, "beneficiary": self.beneficiary}, as_dict=1)

		if ip_record:
			msg = _(
				("Already {0} Beneficiary {1} with Inbeneficiary Record ").format(ip_record[0].status, self.beneficiary)
				+ """ <b><a href="/app/Form/Inbeneficiary Record/{0}">{0}</a></b>""".format(ip_record[0].name)
			)
			frappe.throw(msg)

	@frappe.whitelist()
	def admit(self, service_unit, check_in, expected_discharge=None):
		admit_beneficiary(self, service_unit, check_in, expected_discharge)

	@frappe.whitelist()
	def discharge(self):
		discharge_beneficiary(self)

	@frappe.whitelist()
	def transfer(self, service_unit, check_in, leave_from):
		if leave_from:
			beneficiary_leave_service_unit(self, check_in, leave_from)
		if service_unit:
			transfer_beneficiary(self, service_unit, check_in)


@frappe.whitelist()
def schedule_inbeneficiary(args):
	admission_order = json.loads(args)  # admission order via Encounter
	if (
		not admission_order
		or not admission_order["beneficiary"]
		or not admission_order["admission_encounter"]
	):
		frappe.throw(_("Missing required details, did not create Inbeneficiary Record"))

	inbeneficiary_record = frappe.new_doc("Inbeneficiary Record")

	# Admission order details
	set_details_from_ip_order(inbeneficiary_record, admission_order)

	# Beneficiary details
	beneficiary = frappe.get_doc("Beneficiary", admission_order["beneficiary"])
	inbeneficiary_record.beneficiary = beneficiary.name
	inbeneficiary_record.beneficiary_name = beneficiary.beneficiary_name
	inbeneficiary_record.gender = beneficiary.sex
	inbeneficiary_record.blood_group = beneficiary.blood_group
	inbeneficiary_record.dob = beneficiary.dob
	inbeneficiary_record.mobile = beneficiary.mobile
	inbeneficiary_record.email = beneficiary.email
	inbeneficiary_record.phone = beneficiary.phone
	inbeneficiary_record.scheduled_date = today()

	# Set encounter details
	encounter = frappe.get_doc("Beneficiary Encounter", admission_order["admission_encounter"])
	if encounter and encounter.symptoms:  # Symptoms
		set_ip_child_records(inbeneficiary_record, "chief_complaint", encounter.symptoms)

	if encounter and encounter.diagnosis:  # Diagnosis
		set_ip_child_records(inbeneficiary_record, "diagnosis", encounter.diagnosis)

	if encounter and encounter.drug_prescription:  # Medication
		set_ip_child_records(inbeneficiary_record, "drug_prescription", encounter.drug_prescription)

	if encounter and encounter.lab_test_prescription:  # Lab Tests
		set_ip_child_records(inbeneficiary_record, "lab_test_prescription", encounter.lab_test_prescription)

	if encounter and encounter.procedure_prescription:  # Procedure Prescription
		set_ip_child_records(
			inbeneficiary_record, "procedure_prescription", encounter.procedure_prescription
		)

	if encounter and encounter.therapies:  # Therapies
		inbeneficiary_record.therapy_plan = encounter.therapy_plan
		set_ip_child_records(inbeneficiary_record, "therapies", encounter.therapies)

	inbeneficiary_record.status = "Admission Scheduled"
	inbeneficiary_record.save(ignore_permissions=True)


@frappe.whitelist()
def schedule_discharge(args):
	discharge_order = json.loads(args)
	inbeneficiary_record_id = frappe.db.get_value(
		"Beneficiary", discharge_order["beneficiary"], "inbeneficiary_record"
	)

	if inbeneficiary_record_id:

		inbeneficiary_record = frappe.get_doc("Inbeneficiary Record", inbeneficiary_record_id)
		check_out_inbeneficiary(inbeneficiary_record)
		set_details_from_ip_order(inbeneficiary_record, discharge_order)
		inbeneficiary_record.status = "Discharge Scheduled"
		inbeneficiary_record.save(ignore_permissions=True)

		frappe.db.set_value(
			"Beneficiary", discharge_order["beneficiary"], "inbeneficiary_status", inbeneficiary_record.status
		)
		if inbeneficiary_record.discharge_encounter:
			frappe.db.set_value(
				"Beneficiary Encounter",
				inbeneficiary_record.discharge_encounter,
				"inbeneficiary_status",
				inbeneficiary_record.status,
			)

		if inbeneficiary_record.discharge_nursing_checklist_template:
			NursingTask.create_nursing_tasks_from_template(
				inbeneficiary_record.discharge_nursing_checklist_template,
				inbeneficiary_record,
				start_time=now_datetime(),
			)


def set_details_from_ip_order(inbeneficiary_record, ip_order):
	for key in ip_order:
		inbeneficiary_record.set(key, ip_order[key])


def set_ip_child_records(inbeneficiary_record, inbeneficiary_record_child, encounter_child):
	for item in encounter_child:
		table = inbeneficiary_record.append(inbeneficiary_record_child)
		for df in table.meta.get("fields"):
			table.set(df.fieldname, item.get(df.fieldname))


def check_out_inbeneficiary(inbeneficiary_record):
	if inbeneficiary_record.inbeneficiary_occupancies:
		for inbeneficiary_occupancy in inbeneficiary_record.inbeneficiary_occupancies:
			if inbeneficiary_occupancy.left != 1:
				inbeneficiary_occupancy.left = True
				inbeneficiary_occupancy.check_out = now_datetime()
				frappe.db.set_value(
					"Healthcare Service Unit", inbeneficiary_occupancy.service_unit, "occupancy_status", "Vacant"
				)


def discharge_beneficiary(inbeneficiary_record):
	validate_nursing_tasks(inbeneficiary_record)

	validate_inbeneficiary_invoicing(inbeneficiary_record)

	validate_incompleted_service_requests(inbeneficiary_record)

	inbeneficiary_record.discharge_datetime = now_datetime()
	inbeneficiary_record.status = "Discharged"

	inbeneficiary_record.save(ignore_permissions=True)


def validate_inbeneficiary_invoicing(inbeneficiary_record):
	if frappe.db.get_single_value("Healthcare Settings", "allow_discharge_despite_unbilled_services"):
		return

	pending_invoices = get_pending_invoices(inbeneficiary_record)

	if pending_invoices:
		message = _("Cannot mark Inbeneficiary Record as Discharged since there are unbilled services. ")

		formatted_doc_rows = ""

		for doctype, docnames in pending_invoices.items():
			formatted_doc_rows += """
				<td>{0}</td>
				<td>{1}</td>
			</tr>""".format(
				doctype, docnames
			)

		message += """
			<table class='table'>
				<thead>
					<th>{0}</th>
					<th>{1}</th>
				</thead>
				{2}
			</table>
		""".format(
			_("Healthcare Service"), _("Documents"), formatted_doc_rows
		)

		frappe.throw(message, title=_("Unbilled Services"), is_minimizable=True, wide=True)


def get_pending_invoices(inbeneficiary_record):
	pending_invoices = {}
	if inbeneficiary_record.inbeneficiary_occupancies:
		service_unit_names = False
		for inbeneficiary_occupancy in inbeneficiary_record.inbeneficiary_occupancies:
			if not inbeneficiary_occupancy.invoiced:
				if is_service_unit_billable(inbeneficiary_occupancy.service_unit):
					if service_unit_names:
						service_unit_names += ", " + inbeneficiary_occupancy.service_unit
					else:
						service_unit_names = inbeneficiary_occupancy.service_unit
		if service_unit_names:
			pending_invoices["Inbeneficiary Occupancy"] = service_unit_names

	docs = ["Beneficiary Appointment", "Beneficiary Encounter", "Lab Test", "Clinical Procedure"]

	for doc in docs:
		doc_name_list = get_unbilled_inbeneficiary_docs(doc, inbeneficiary_record)
		if doc_name_list:
			pending_invoices = get_pending_doc(doc, doc_name_list, pending_invoices)

	return pending_invoices


def get_pending_doc(doc, doc_name_list, pending_invoices):
	if doc_name_list:
		doc_ids = False
		for doc_name in doc_name_list:
			doc_link = get_link_to_form(doc, doc_name.name)
			if doc_ids:
				doc_ids += ", " + doc_link
			else:
				doc_ids = doc_link
		if doc_ids:
			pending_invoices[doc] = doc_ids

	return pending_invoices


def get_unbilled_inbeneficiary_docs(doc, inbeneficiary_record):
	filters = {
		"beneficiary": inbeneficiary_record.beneficiary,
		"inbeneficiary_record": inbeneficiary_record.name,
		"docstatus": 1,
	}
	if doc in ["Service Request", "Medication Request"]:
		filters.update(
			{
				"billing_status": "Pending",
			}
		)
	else:
		if doc == "Beneficiary Encounter":
			filters.update(
				{
					"appointment": "",
				}
			)
		else:
			del filters["docstatus"]
		filters.update(
			{
				"invoiced": 0,
			}
		)
	if doc in ["Lab Test", "Clinical Procedure"]:
		filters.update(
			{
				"service_request": "",
			}
		)

	return frappe.db.get_list(
		doc,
		filters={
			"beneficiary": inbeneficiary_record.beneficiary,
			"inbeneficiary_record": inbeneficiary_record.name,
			"docstatus": 1,
			"invoiced": 0,
		},
	)


def admit_beneficiary(inbeneficiary_record, service_unit, check_in, expected_discharge=None):
	validate_nursing_tasks(inbeneficiary_record)

	inbeneficiary_record.admitted_datetime = check_in
	inbeneficiary_record.status = "Admitted"
	inbeneficiary_record.expected_discharge = expected_discharge

	inbeneficiary_record.set("inbeneficiary_occupancies", [])
	transfer_beneficiary(inbeneficiary_record, service_unit, check_in)

	frappe.db.set_value(
		"Beneficiary",
		inbeneficiary_record.beneficiary,
		{"inbeneficiary_status": "Admitted", "inbeneficiary_record": inbeneficiary_record.name},
	)


def transfer_beneficiary(inbeneficiary_record, service_unit, check_in):
	item_line = inbeneficiary_record.append("inbeneficiary_occupancies", {})
	item_line.service_unit = service_unit
	item_line.check_in = check_in

	inbeneficiary_record.save(ignore_permissions=True)

	frappe.db.set_value("Healthcare Service Unit", service_unit, "occupancy_status", "Occupied")


def beneficiary_leave_service_unit(inbeneficiary_record, check_out, leave_from):
	if inbeneficiary_record.inbeneficiary_occupancies:
		for inbeneficiary_occupancy in inbeneficiary_record.inbeneficiary_occupancies:
			if inbeneficiary_occupancy.left != 1 and inbeneficiary_occupancy.service_unit == leave_from:
				inbeneficiary_occupancy.left = True
				inbeneficiary_occupancy.check_out = check_out
				frappe.db.set_value(
					"Healthcare Service Unit", inbeneficiary_occupancy.service_unit, "occupancy_status", "Vacant"
				)
	inbeneficiary_record.save(ignore_permissions=True)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_leave_from(doctype, txt, searchfield, start, page_len, filters):
	docname = filters["docname"]

	query = """select io.service_unit
		from `tabInbeneficiary Occupancy` io, `tabInbeneficiary Record` ir
		where io.parent = '{docname}' and io.parentfield = 'inbeneficiary_occupancies'
		and io.left!=1 and io.parent = ir.name"""

	return frappe.db.sql(
		query.format(
			**{"docname": docname, "searchfield": searchfield, "mcond": get_match_cond(doctype)}
		),
		{"txt": "%%%s%%" % txt, "_txt": txt.replace("%", ""), "start": start, "page_len": page_len},
	)


def is_service_unit_billable(service_unit):
	service_unit_doc = frappe.qb.DocType("Healthcare Service Unit")
	service_unit_type = frappe.qb.DocType("Healthcare Service Unit Type")
	result = (
		frappe.qb.from_(service_unit_doc)
		.left_join(service_unit_type)
		.on(service_unit_doc.service_unit_type == service_unit_type.name)
		.select(service_unit_type.is_billable)
		.where(service_unit_doc.name == service_unit)
	).run(as_dict=1)
	return result[0].get("is_billable", 0)


@frappe.whitelist()
def set_ip_order_cancelled(inbeneficiary_record, reason, encounter=None):
	inbeneficiary_record = frappe.get_doc("Inbeneficiary Record", inbeneficiary_record)
	if inbeneficiary_record.status == "Admission Scheduled":
		inbeneficiary_record.status = "Cancelled"
		inbeneficiary_record.reason_for_cancellation = reason
		inbeneficiary_record.save(ignore_permissions=True)
		encounter_name = encounter if encounter else inbeneficiary_record.admission_encounter
		if encounter_name:
			frappe.db.set_value(
				"Beneficiary Encounter", encounter_name, {"inbeneficiary_status": None, "inbeneficiary_record": None}
			)


def validate_incompleted_service_requests(inbeneficiary_record):
	filters = {
		"beneficiary": inbeneficiary_record.beneficiary,
		"inbeneficiary_record": inbeneficiary_record.name,
		"docstatus": 1,
		"status": ["not in", ["Completed"]],
	}

	service_requests = frappe.db.get_list("Service Request", filters=filters, pluck="name")
	if service_requests and len(service_requests) > 0:
		service_requests = [
			get_link_to_form("Service Request", service_request) for service_request in service_requests
		]
		message = _("There are Orders yet to be carried out<br> {0}")

		frappe.throw(message.format(", ".join(service_requests)))
