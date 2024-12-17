import frappe


def get_context(context):
	context.read_only = 1


def get_list_context(context):
	context.row_template = "erpnext/templates/includes/healthcare/appointment_row_template.html"
	context.get_list = get_appointment_list


def get_appointment_list(
	doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified desc"
):
	beneficiary = get_beneficiary()
	lab_tests = frappe.db.sql(
		"""select * from `tabBeneficiary Appointment`
		where beneficiary = %s and (status = 'Open' or status = 'Scheduled') order by appointment_date""",
		beneficiary,
		as_dict=True,
	)
	return lab_tests


def get_beneficiary():
	return frappe.get_value("Beneficiary", {"email": frappe.session.user}, "name")


def has_website_permission(doc, ptype, user, verbose=False):
	if doc.beneficiary == get_beneficiary():
		return True
	else:
		return False
