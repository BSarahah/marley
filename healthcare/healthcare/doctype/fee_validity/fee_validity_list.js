frappe.listview_settings['Fee Validity'] = {
	add_fields: ['practitioner', 'beneficiary', 'status', 'valid_till'],
	get_indicator: function (doc) {
		const color = {
			'Active': 'green',
			'Completed': 'green',
			'Expired': 'red',
			'Cancelled': 'red',
		};
		return [__(doc.status), color[doc.status], 'status,=,' + doc.status];
	}
}