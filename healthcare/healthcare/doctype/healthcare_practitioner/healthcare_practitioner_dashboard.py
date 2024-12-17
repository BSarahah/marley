from frappe import _


def get_data():
	return {
		"heatmap": True,
		"heatmap_message": _("This is based on transactions against this Healthcare Practitioner."),
		"fieldname": "practitioner",
		"transactions": [
			{
				"label": _("Appointments and Beneficiary Encounters"),
				"items": ["Beneficiary Appointment", "Beneficiary Encounter", "Fee Validity"],
			},
			{"label": _("Consultation"), "items": ["Clinical Procedure", "Lab Test"]},
		],
	}
