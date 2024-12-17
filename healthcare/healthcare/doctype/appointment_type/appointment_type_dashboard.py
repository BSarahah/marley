from frappe import _


def get_data():
	return {
		"fieldname": "appointment_type",
		"transactions": [
			{"label": _("Beneficiary Appointments"), "items": ["Beneficiary Appointment"]},
		],
	}
