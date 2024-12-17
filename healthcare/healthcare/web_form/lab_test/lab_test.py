import frappe


def get_context(context):
	context.read_only = 1


def get_list_context(context):
	context.row_template = "erpnext/templates/includes/healthcare/lab_test_row_template.html"
	context.get_list = get_lab_test_list


def get_lab_test_list(
	doctype, txt, filters, limit_start, limit_page_length=20, order_by="modified desc"
):
	beneficiary = get_beneficiary()
	lab_tests = frappe.db.sql(
		"""select * from `tabLab Test`
		where beneficiary = %s order by result_date""",
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
