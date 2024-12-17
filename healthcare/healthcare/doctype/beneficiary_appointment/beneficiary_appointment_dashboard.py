from frappe import _


def get_data():
	return {
		"fieldname": "appointment",
		"non_standard_fieldnames": {"Beneficiary Medical Record": "reference_name"},
		"transactions": [
			{
				"label": _("Consultations"),
				"items": ["Beneficiary Encounter", "Vital Signs", "Beneficiary Medical Record"],
			}
		],
	}
