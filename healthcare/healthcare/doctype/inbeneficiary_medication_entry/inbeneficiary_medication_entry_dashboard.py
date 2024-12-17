from frappe import _


def get_data():
	return {
		"fieldname": "against_imoe",
		"internal_links": {"Inbeneficiary Medication Order": ["medication_orders", "against_imo"]},
		"transactions": [{"label": _("Reference"), "items": ["Inbeneficiary Medication Order"]}],
	}
