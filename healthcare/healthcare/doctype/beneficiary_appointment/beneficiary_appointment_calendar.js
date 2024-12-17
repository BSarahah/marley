
frappe.views.calendar["Beneficiary Appointment"] = {
	field_map: {
		"start": "start",
		"end": "end",
		"id": "name",
		"title": "beneficiary",
		"allDay": "allDay",
		"eventColor": "color"
	},
	order_by: "appointment_date",
	gantt: true,
	get_events_method: "healthcare.healthcare.doctype.beneficiary_appointment.beneficiary_appointment.get_events"
};
