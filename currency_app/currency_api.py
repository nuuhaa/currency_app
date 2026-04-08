import requests
import frappe
from frappe.utils import now_datetime


def get_exchange_rate(from_currency="USD", to_currency="EGP"):
    url = f"https://open.er-api.com/v6/latest/{from_currency}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    data = response.json()

    if data.get("result") != "success":
        frappe.throw("Failed to fetch exchange rate")

    rate = data.get("rates", {}).get(to_currency)

    if rate is None:
        frappe.throw(f"Currency {to_currency} not found")

    return rate


def update_currency_rate(from_currency="USD", to_currency="EGP"):
    rate = get_exchange_rate(from_currency, to_currency)

    existing_name = frappe.db.get_value(
        "Currency Rate",
        {
            "from_currency": from_currency,
            "to_currency": to_currency
        },
        "name"
    )

    if existing_name:
        doc = frappe.get_doc("Currency Rate", existing_name)

        if doc.exchange_rate != rate:
            doc.exchange_rate = rate
            doc.last_updated_on = now_datetime()
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            return f"Updated: {doc.name} = {rate}"

        return f"No change: {doc.name} = {rate}"

    doc = frappe.get_doc({
        "doctype": "Currency Rate",
        "from_currency": from_currency,
        "to_currency": to_currency,
        "exchange_rate": rate,
        "last_updated_on": now_datetime()
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return f"Created: {doc.name} = {rate}"


def run_hourly_currency_updates():
    pairs = [
        ("USD", "EGP"),
    ]

    for from_currency, to_currency in pairs:
        try:
            result = update_currency_rate(from_currency, to_currency)
            frappe.logger().info(result)
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Currency update failed for {from_currency}-{to_currency}"
            )