from frappe import _


def get_data():
	return {
		"heatmap": True,
		"heatmap_message": _(
			"This is based on transactions against this Beneficiary. See timeline below for details"
		),
		"fieldname": "beneficiary",
		"non_standard_fieldnames": {"Payment Entry": "party"},
		"transactions": [
			{
				"label": _("Appointments and Encounters"),
				"items": ["Beneficiary Appointment", "Vital Signs", "Beneficiary Encounter"],
			},
			{"label": _("Lab Tests and Vital Signs"), "items": ["Lab Test", "Sample Collection"]},
			{
				"label": _("Rehab and Physiotherapy"),
				"items": ["Beneficiary Assessment", "Therapy Session", "Therapy Plan"],
			},
			{"label": _("Surgery"), "items": ["Clinical Procedure"]},
			{"label": _("Admissions"), "items": ["Inbeneficiary Record", "Inbeneficiary Medication Order"]},
			{"label": _("Billing and Payments"), "items": ["Sales Invoice", "Payment Entry"]},
		],
	}
