import frappe
from frappe import DuplicateEntryError


def create_encounter(beneficiary, practitioner, submit=False):
	encounter = frappe.new_doc("Beneficiary Encounter")
	encounter.beneficiary = beneficiary
	encounter.practitioner = practitioner
	encounter.save()
	if submit:
		encounter.submit()
	return encounter
