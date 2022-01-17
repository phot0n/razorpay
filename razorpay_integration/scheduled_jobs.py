import frappe
from frappe.utils.data import flt
from frappe.utils.password import get_decrypted_password

from razorpay_integration.api import RazorpayPayment
from razorpay_integration.utils import get_epoch_time


def refund_payments() -> None:
	# full refunds
	log_doctype = "Razorpay Payment Log"
	setting_doctype = "Razorpay Settings"

	logs = frappe.get_all(
		log_doctype,
		filters={
			"status": "Refund",
			"refund_id": "",
			"payment_id": ["!=", ""] # adding this for additional check
		},
		fields=["name", "payment_id", "razorpay_setting", "amount"]
	)

	log_doctype = frappe.qb.DocType(log_doctype)
	for log in logs:
		api_key = frappe.db.get_value(
			setting_doctype,
			log.razorpay_setting,
			fieldname=["api_key"]
		)

		try:
			response = RazorpayPayment(
				api_key,
				get_decrypted_password(
					setting_doctype,
					log.razorpay_setting,
					fieldname="api_secret"
				)
			).refund_payment(log.payment_id)
		except Exception:
			continue

		frappe.qb.update(
			log_doctype
		).set(
			log_doctype.refund_id, response["id"]
		).set(
			log_doctype.refund_amount, flt(log.amount)
		).set(
			log_doctype.status, "Refunded"
		).where(
			log_doctype.name == log.name
		).run()


def update_payment_log_status_for_expired_links() -> None:
	log_doctype = frappe.qb.DocType("Razorpay Payment Log")

	frappe.qb.update(
		log_doctype
	).set(
		log_doctype.status, "Expired"
	).where(
		(log_doctype.status == "Created") &
		(log_doctype.valid_till <= get_epoch_time())
	).run()
