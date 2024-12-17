// Copyright (c) 2016, ESS LLP and contributors
// For license information, please see license.txt
{% include 'healthcare/regional/india/abdm/js/beneficiary.js' %}

frappe.ui.form.on('Beneficiary', {
	refresh: function (frm) {
		frm.set_query('beneficiary', 'beneficiary_relation', function () {
			return {
				filters: [
					['Beneficiary', 'name', '!=', frm.doc.name]
				]
			};
		});
		frm.set_query('customer_group', {'is_group': 0});
		frm.set_query('default_price_list', { 'selling': 1});

		if (frappe.defaults.get_default('beneficiary_name_by') != 'Naming Series') {
			frm.toggle_display('naming_series', false);
		} else {
			erpnext.toggle_naming_series();
		}

		if (frappe.defaults.get_default('collect_registration_fee') && frm.doc.status == 'Disabled') {
			frm.add_custom_button(__('Invoice Beneficiary Registration'), function () {
				invoice_registration(frm);
			});
		}

		if (frm.doc.beneficiary_name && frappe.user.has_role('Physician')) {
			frm.add_custom_button(__('Beneficiary Progress'), function() {
				frappe.route_options = {'beneficiary': frm.doc.name};
				frappe.set_route('beneficiary-progress');
			}, __('View'));

			frm.add_custom_button(__('Beneficiary History'), function() {
				frappe.route_options = {'beneficiary': frm.doc.name};
				frappe.set_route('beneficiary_history');
			}, __('View'));
		}

		frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Beneficiary'};
		frm.toggle_display(['address_html', 'contact_html'], !frm.is_new());

		if (!frm.is_new()) {
			if ((frappe.user.has_role('Nursing User') || frappe.user.has_role('Physician'))) {
				frm.add_custom_button(__('Medical Record'), function () {
					create_medical_record(frm);
				}, __('Create'));
				frm.toggle_enable(['customer'], 0);
			}
			frappe.contacts.render_address_and_contact(frm);
			erpnext.utils.set_party_dashboard_indicators(frm);
		} else {
			frappe.contacts.clear_address_and_contact(frm);
		}
	},

	onload: function (frm) {
		if (frm.doc.dob) {
			$(frm.fields_dict['age_html'].wrapper).html(`${__('AGE')} : ${get_age(frm.doc.dob)}`);
		} else {
			$(frm.fields_dict['age_html'].wrapper).html('');
		}
	}
});

frappe.ui.form.on('Beneficiary', 'dob', function(frm) {
	if (frm.doc.dob) {
		let today = new Date();
		let birthDate = new Date(frm.doc.dob);
		if (today < birthDate) {
			frappe.msgprint(__('Please select a valid Date'));
			frappe.model.set_value(frm.doctype,frm.docname, 'dob', '');
		} else {
			let age_str = get_age(frm.doc.dob);
			$(frm.fields_dict['age_html'].wrapper).html(`${__('AGE')} : ${age_str}`);
		}
	} else {
		$(frm.fields_dict['age_html'].wrapper).html('');
	}
});

frappe.ui.form.on('Beneficiary Relation', {
	beneficiary_relation_add: function(frm){
		frm.fields_dict['beneficiary_relation'].grid.get_field('beneficiary').get_query = function(doc){
			let beneficiary_list = [];
			if(!doc.__islocal) beneficiary_list.push(doc.name);
			$.each(doc.beneficiary_relation, function(idx, val){
				if (val.beneficiary) beneficiary_list.push(val.beneficiary);
			});
			return { filters: [['Beneficiary', 'name', 'not in', beneficiary_list]] };
		};
	}
});

let create_medical_record = function (frm) {
	frappe.route_options = {
		'beneficiary': frm.doc.name,
		'status': 'Open',
		'reference_doctype': 'Beneficiary Medical Record',
		'reference_owner': frm.doc.owner
	};
	frappe.new_doc('Beneficiary Medical Record');
};

let get_age = function (birth) {
	let birth_moment = moment(birth);
	let current_moment = moment(Date());
	let diff = moment.duration(current_moment.diff(birth_moment));
	return `${diff.years()} ${__('Year(s)')} ${diff.months()} ${__('Month(s)')} ${diff.days()} ${__('Day(s)')}`
};

let create_vital_signs = function (frm) {
	if (!frm.doc.name) {
		frappe.throw(__('Please save the beneficiary first'));
	}
	frappe.route_options = {
		'beneficiary': frm.doc.name,
	};
	frappe.new_doc('Vital Signs');
};

let create_encounter = function (frm) {
	if (!frm.doc.name) {
		frappe.throw(__('Please save the beneficiary first'));
	}
	frappe.route_options = {
		'beneficiary': frm.doc.name,
	};
	frappe.new_doc('Beneficiary Encounter');
};

let invoice_registration = function (frm) {
	frappe.call({
		doc: frm.doc,
		method: 'invoice_beneficiary_registration',
		callback: function(data) {
			if (!data.exc) {
				if (data.message.invoice) {
					frappe.set_route('Form', 'Sales Invoice', data.message.invoice);
				}
				cur_frm.reload_doc();
			}
		}
	});
};
