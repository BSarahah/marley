import frappe
from frappe import _

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)

	context.show_sidebar = True

	if frappe.db.exists("Beneficiary", {"email": frappe.session.user}):
		beneficiary = frappe.get_doc("Beneficiary", {"email": frappe.session.user})
		context.doc = beneficiary
		frappe.form_dict.new = 0
		frappe.form_dict.name = beneficiary.name


def get_beneficiary():
	return frappe.get_value("Beneficiary", {"email": frappe.session.user}, "name")


def has_website_permission(doc, ptype, user, verbose=False):
	if doc.name == get_beneficiary():
		return True
	else:
		return False
