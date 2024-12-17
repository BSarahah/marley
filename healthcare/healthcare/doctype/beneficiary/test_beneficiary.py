# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and Contributors
# See license.txt


import os

import frappe
from frappe.tests.utils import FrappeTestCase

from healthcare.healthcare.doctype.beneficiary_appointment.test_beneficiary_appointment import (
	create_beneficiary,
)


class TestBeneficiary(FrappeTestCase):
	def test_customer_created(self):
		frappe.db.sql("""delete from `tabBeneficiary`""")
		frappe.db.set_value("Healthcare Settings", None, "link_customer_to_beneficiary", 1)
		beneficiary = create_beneficiary()
		self.assertTrue(frappe.db.get_value("Beneficiary", beneficiary, "customer"))

	def test_beneficiary_registration(self):
		frappe.db.sql("""delete from `tabBeneficiary`""")
		settings = frappe.get_single("Healthcare Settings")
		settings.collect_registration_fee = 1
		settings.registration_fee = 500
		settings.save()

		beneficiary = create_beneficiary()
		beneficiary = frappe.get_doc("Beneficiary", beneficiary)
		self.assertEqual(beneficiary.status, "Disabled")

		# check sales invoice and beneficiary status
		result = beneficiary.invoice_beneficiary_registration()
		self.assertTrue(frappe.db.exists("Sales Invoice", result.get("invoice")))
		self.assertTrue(beneficiary.status, "Active")

		settings.collect_registration_fee = 0
		settings.save()

	def test_beneficiary_contact(self):
		frappe.db.sql("""delete from `tabBeneficiary` where name like '_Test Beneficiary%'""")
		frappe.db.sql("""delete from `tabCustomer` where name like '_Test Beneficiary%'""")
		frappe.db.sql("""delete from `tabContact` where name like'_Test Beneficiary%'""")
		frappe.db.sql("""delete from `tabDynamic Link` where parent like '_Test Beneficiary%'""")

		beneficiary = create_beneficiary(
			beneficiary_name="_Test Beneficiary Contact", email="test-beneficiary@example.com", mobile="+91 0000000001"
		)
		customer = frappe.db.get_value("Beneficiary", beneficiary, "customer")
		self.assertTrue(customer)
		self.assertTrue(
			frappe.db.exists(
				"Dynamic Link", {"parenttype": "Contact", "link_doctype": "Beneficiary", "link_name": beneficiary}
			)
		)
		self.assertTrue(
			frappe.db.exists(
				"Dynamic Link", {"parenttype": "Contact", "link_doctype": "Customer", "link_name": customer}
			)
		)

		# a second beneficiary linking with same customer
		new_beneficiary = create_beneficiary(
			email="test-beneficiary@example.com", mobile="+91 0000000009", customer=customer
		)
		self.assertTrue(
			frappe.db.exists(
				"Dynamic Link", {"parenttype": "Contact", "link_doctype": "Beneficiary", "link_name": new_beneficiary}
			)
		)
		self.assertTrue(
			frappe.db.exists(
				"Dynamic Link", {"parenttype": "Contact", "link_doctype": "Customer", "link_name": customer}
			)
		)

	def test_beneficiary_user(self):
		frappe.db.sql("""delete from `tabUser` where email='test-beneficiary-user@example.com'""")
		frappe.db.sql("""delete from `tabDynamic Link` where parent like '_Test Beneficiary%'""")
		frappe.db.sql("""delete from `tabBeneficiary` where name like '_Test Beneficiary%'""")

		beneficiary = create_beneficiary(
			beneficiary_name="_Test Beneficiary User",
			email="test-beneficiary-user@example.com",
			mobile="+91 0000000009",
			create_user=True,
		)
		user = frappe.db.get_value("Beneficiary", beneficiary, "user_id")
		self.assertTrue(frappe.db.exists("User", user))

		new_beneficiary = frappe.get_doc(
			{
				"doctype": "Beneficiary",
				"first_name": "_Test Beneficiary Duplicate User",
				"sex": "Male",
				"email": "test-beneficiary-user@example.com",
				"mobile": "+91 0000000009",
				"invite_user": 1,
			}
		)

		self.assertRaises(frappe.exceptions.DuplicateEntryError, new_beneficiary.insert)

	def test_beneficiary_image_update_should_update_customer_image(self):
		settings = frappe.get_single("Healthcare Settings")
		settings.link_customer_to_beneficiary = 1
		settings.save()

		beneficiary_name = create_beneficiary()
		beneficiary = frappe.get_doc("Beneficiary", beneficiary_name)
		beneficiary.image = os.path.abspath("assets/frappe/images/default-avatar.png")
		beneficiary.save()

		customer = frappe.get_doc("Customer", beneficiary.customer)
		self.assertEqual(customer.image, beneficiary.image)

	def test_multiple_paients_linked_with_same_customer(self):
		frappe.db.sql("""delete from `tabBeneficiary`""")
		frappe.db.set_single_value("Healthcare Settings", "link_customer_to_beneficiary", 1)

		beneficiary_name_1 = create_beneficiary(beneficiary_name="John Doe")
		p1_customer_name = frappe.get_value("Beneficiary", beneficiary_name_1, "customer")
		p1_customer = frappe.get_doc("Customer", p1_customer_name)
		self.assertEqual(p1_customer.customer_name, "John Doe")

		beneficiary_name_2 = create_beneficiary(beneficiary_name="Jane Doe", customer=p1_customer.name)
		p2_customer_name = frappe.get_value("Beneficiary", beneficiary_name_2, "customer")
		p2_customer = frappe.get_doc("Customer", p2_customer_name)

		self.assertEqual(p1_customer_name, p2_customer_name)
		self.assertEqual(p2_customer.customer_name, "John Doe")
