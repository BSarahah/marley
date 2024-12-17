frappe.provide('frappe.dashboards.chart_sources');

frappe.dashboards.chart_sources["Department wise Beneficiary Appointments"] = {
	method: "healthcare.healthcare.dashboard_chart_source.department_wise_beneficiary_appointments.department_wise_beneficiary_appointments.get",
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company")
		}
	]
};
