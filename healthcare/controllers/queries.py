import frappe


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_healthcare_service_units(doctype, txt, searchfield, start, page_len, filters):
	table = frappe.qb.DocType("Healthcare Service Unit")
	query = (
		frappe.qb.from_(table)
		.where(table.is_group == 0)
		.where(table.company == filters.get("company"))
		.where(table.name.like("%{0}%".format(txt)))
		.select("name")
		.get_sql()
	)

	if filters and filters.get("inbeneficiary_record"):
		from healthcare.healthcare.doctype.inbeneficiary_medication_entry.inbeneficiary_medication_entry import (
			get_current_healthcare_service_unit,
		)

		service_unit = get_current_healthcare_service_unit(filters.get("inbeneficiary_record"))

		# if the beneficiary is admitted, then appointments should be allowed against the admission service unit,
		# inspite of it being an Inbeneficiary Occupancy service unit
		if service_unit:
			query += " and (allow_appointments = 1 or name = {service_unit})".format(
				service_unit=frappe.db.escape(service_unit)
			)
		else:
			query += " and allow_appointments = 1"
	else:
		query += " and allow_appointments = 1"

	return frappe.db.sql(query, filters)
