from frappe import _


def get_data():
	return {
		"fieldname": "encounter",
		"non_standard_fieldnames": {
			"Beneficiary Medical Record": "reference_name",
			"Inbeneficiary Medication Order": "beneficiary_encounter",
			"Nursing Task": "reference_name",
			"Service Request": "order_group",
			"Medication Request": "order_group",
		},
		"transactions": [
			{"label": _("Records"), "items": ["Vital Signs", "Beneficiary Medical Record"]},
			{
				"label": _("Orders"),
				"items": [
					"Inbeneficiary Medication Order",
					"Nursing Task",
					"Service Request",
					"Medication Request",
				],
			},
		],
		"disable_create_buttons": ["Inbeneficiary Medication Order"],
	}
