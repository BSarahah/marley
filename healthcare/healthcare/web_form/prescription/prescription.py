import frappe


def get_context(context):
	context.read_only = 1


def get_list_context(context):
	context.row_template = "erpnext/templates/includes/healthcare/prescription_row_template.html"
	context.get_list = get_encounter_list


def get_encounter_list(
	doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified desc"
):
	beneficiary = get_beneficiary()
	encounters = frappe.db.sql(
		"""select * from `tabBeneficiary Encounter`
		where beneficiary = %s order by creation desc""",
		beneficiary,
		as_dict=True,
	)
	return encounters


def get_beneficiary():
	return frappe.get_value("Beneficiary", {"email": frappe.session.user}, "name")


def has_website_permission(doc, ptype, user, verbose=False):
	if doc.beneficiary == get_beneficiary():
		return True
	else:
		return False
