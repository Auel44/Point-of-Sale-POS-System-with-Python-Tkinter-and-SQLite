"""Receipt generation module — formats and saves sale receipts."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from database.db_connection import get_connection
from utils.helpers import log_error

# Configurable store details
STORE_NAME = "My POS Store"
STORE_ADDRESS = "123 Main Street, Accra, Ghana"
STORE_PHONE = "+233 24 000 0000"
RECEIPT_WIDTH = 44  # characters wide for the text receipt


def _fetch_receipt_data(sale_id: int) -> dict[str, Any] | None:
	"""Pull all data needed for a receipt from the database."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()

			# Sale header
			cursor.execute(
				"""
				SELECT s.sale_id, s.date, s.total_amount, s.payment_method,
				       s.customer_id,
				       c.name, c.phone
				FROM Sales s
				LEFT JOIN Customers c ON c.customer_id = s.customer_id
				WHERE s.sale_id = ?
				""",
				(sale_id,),
			)
			row = cursor.fetchone()
			if row is None:
				return None

			sale = {
				"sale_id": row[0],
				"date": row[1],
				"total_amount": row[2],
				"payment_method": row[3],
				"customer_id": row[4],
				"customer_name": row[5] or "Walk-in Customer",
				"customer_phone": row[6] or "",
			}

			# Line items
			cursor.execute(
				"""
				SELECT p.product_name, si.quantity, si.price
				FROM Sales_Items si
				JOIN Products p ON p.product_id = si.product_id
				WHERE si.sale_id = ?
				""",
				(sale_id,),
			)
			sale["items"] = [
				{"product_name": r[0], "quantity": r[1], "price": r[2]}
				for r in cursor.fetchall()
			]

			# Payment record
			cursor.execute(
				"""
				SELECT amount_paid, change_given
				FROM Payments
				WHERE sale_id = ?
				""",
				(sale_id,),
			)
			pay_row = cursor.fetchone()
			sale["amount_paid"] = pay_row[0] if pay_row else sale["total_amount"]
			sale["change_given"] = pay_row[1] if pay_row else 0.0
	except Exception as exc:
		log_error("receipts._fetch_receipt_data", exc)
		return None

	return sale


def _divider(char: str = "-") -> str:
	return char * RECEIPT_WIDTH


def generate_receipt(sale_id: int) -> str:
	"""Return a formatted receipt string for the given sale.

	Also saves a copy to the receipts/ folder as a .txt file.
	Returns an empty string if the sale is not found.
	"""
	data = _fetch_receipt_data(sale_id)
	if data is None:
		return ""

	W = RECEIPT_WIDTH
	lines: list[str] = []

	# Header
	lines.append(_divider("="))
	lines.append(STORE_NAME.center(W))
	lines.append(STORE_ADDRESS.center(W))
	lines.append(STORE_PHONE.center(W))
	lines.append(_divider("="))

	lines.append(f"Receipt #: {data['sale_id']:<{W - 12}}")
	lines.append(f"Date     : {data['date']}")
	lines.append(f"Customer : {data['customer_name']}")
	if data["customer_phone"]:
		lines.append(f"Phone    : {data['customer_phone']}")
	lines.append(_divider())

	# Item header
	lines.append(f"{'Item':<22} {'Qty':>4} {'Price':>7} {'Total':>7}")
	lines.append(_divider())

	subtotal = 0.0
	for item in data["items"]:
		line_total = item["price"] * item["quantity"]
		subtotal += line_total
		name = item["product_name"][:21]
		lines.append(
			f"{name:<22} {item['quantity']:>4} {item['price']:>7.2f} {line_total:>7.2f}"
		)

	lines.append(_divider())

	# Totals
	discount = round(subtotal - data["total_amount"] + 0.0, 2)
	if discount > 0:
		lines.append(f"{'Subtotal':<{W - 10}}{subtotal:>9.2f}")
		lines.append(f"{'Discount':<{W - 10}}{-discount:>9.2f}")
	lines.append(f"{'TOTAL':<{W - 10}}{data['total_amount']:>9.2f}")
	lines.append(_divider())

	# Payment
	lines.append(f"{'Method':<{W - 10}}{data['payment_method']:>9}")
	lines.append(f"{'Amount Paid':<{W - 10}}{data['amount_paid']:>9.2f}")
	lines.append(f"{'Change':<{W - 10}}{data['change_given']:>9.2f}")
	lines.append(_divider("="))
	lines.append("Thank you for your purchase!".center(W))
	lines.append(_divider("="))

	receipt_text = "\n".join(lines)

	# Save to file
	_save_receipt_file(sale_id, data["date"], receipt_text)

	return receipt_text


def _save_receipt_file(sale_id: int, date_str: str, text: str) -> Path | None:
	"""Write the receipt text to receipts/receipt_<id>_<date>.txt."""
	try:
		receipts_dir = Path(__file__).resolve().parent.parent / "receipts"
		receipts_dir.mkdir(exist_ok=True)
		safe_date = date_str.replace(":", "-").replace(" ", "_")
		file_path = receipts_dir / f"receipt_{sale_id}_{safe_date}.txt"
		file_path.write_text(text, encoding="utf-8")
		return file_path
	except OSError:
		log_error("receipts._save_receipt_file", "Failed to write receipt file")
		return None


def get_receipt_file_path(sale_id: int) -> Path | None:
	"""Return the path of the most recently saved receipt .txt for a sale, or None."""
	receipts_dir = Path(__file__).resolve().parent.parent / "receipts"
	if not receipts_dir.exists():
		return None
	matches = sorted(receipts_dir.glob(f"receipt_{sale_id}_*.txt"))
	return matches[-1] if matches else None
