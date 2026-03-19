"""Sales transaction processing module."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from database.db_connection import get_connection
from modules.inventory import deduct_stock
from modules.products import get_product_by_id
from utils.helpers import log_error


def _to_sale_dict(row: tuple[Any, ...]) -> dict[str, Any]:
	return {
		"sale_id": row[0],
		"date": row[1],
		"user_id": row[2],
		"customer_id": row[3],
		"total_amount": row[4],
		"payment_method": row[5],
		"cashier_username": row[6] if len(row) > 6 else "",
	}


def create_sale(
	user_id: int,
	customer_id: int | None,
	items: list[dict[str, Any]],
	payment_method: str,
	discount: float = 0.0,
) -> int:
	"""Persist a new sale and return the new sale_id.

	items format: [{"product_id": int, "quantity": int, "price": float}, ...]
	"""
	if not items:
		raise ValueError("At least one sale item is required.")

	# Pre-check stock availability to avoid persisting impossible sales.
	for item in items:
		product = get_product_by_id(int(item["product_id"]))
		if product is None:
			raise ValueError(f"Product {item['product_id']} not found.")
		if int(item["quantity"]) <= 0:
			raise ValueError("Item quantity must be greater than zero.")
		if int(item["quantity"]) > int(product["quantity"]):
			raise ValueError(
				f"Insufficient stock for {product['product_name']}: "
				f"requested {item['quantity']}, available {product['quantity']}"
			)

	subtotal = sum(item["price"] * item["quantity"] for item in items)
	total_amount = max(0.0, subtotal - discount)
	date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				INSERT INTO Sales (date, user_id, customer_id, total_amount, payment_method)
				VALUES (?, ?, ?, ?, ?)
				""",
				(date_str, user_id, customer_id, round(total_amount, 2), payment_method),
			)
			sale_id: int = cursor.lastrowid  # type: ignore[assignment]

			for item in items:
				cursor.execute(
					"""
					INSERT INTO Sales_Items (sale_id, product_id, quantity, price)
					VALUES (?, ?, ?, ?)
					""",
					(sale_id, item["product_id"], item["quantity"], item["price"]),
				)

			conn.commit()
	except Exception as exc:
		log_error("sales.create_sale", exc)
		raise

	# Deduct inventory after sale rows are persisted.
	for item in items:
		if not deduct_stock(item["product_id"], item["quantity"]):
			log_error("sales.create_sale", f"Failed stock deduction for sale {sale_id}")
			raise ValueError("Failed to deduct stock for one or more sale items.")

	return sale_id


def get_sale_by_id(sale_id: int) -> dict[str, Any] | None:
	"""Return sale header row plus its line items, or None when not found."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT sale_id, date, user_id, customer_id, total_amount, payment_method
				FROM Sales
				WHERE sale_id = ?
				""",
				(sale_id,),
			)
			row = cursor.fetchone()
			if row is None:
				return None
			sale = _to_sale_dict(row)

			cursor.execute(
				"""
				SELECT si.sale_item_id, si.product_id, p.product_name, si.quantity, si.price
				FROM Sales_Items si
				JOIN Products p ON p.product_id = si.product_id
				WHERE si.sale_id = ?
				""",
				(sale_id,),
			)
			sale["items"] = [
				{
					"sale_item_id": r[0],
					"product_id": r[1],
					"product_name": r[2],
					"quantity": r[3],
					"price": r[4],
				}
				for r in cursor.fetchall()
			]
	except Exception as exc:
		log_error("sales.get_sale_by_id", exc)
		return None

	return sale


def get_sales_by_date_range(
	start: str,
	end: str,
	user_id: int | None = None,
	cashier_username: str | None = None,
) -> list[dict[str, Any]]:
	"""Return all sales whose date falls within [start, end] (inclusive).

	start and end should be date strings in 'YYYY-MM-DD' format.
	"""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			if user_id is not None:
				cursor.execute(
					"""
					SELECT s.sale_id, s.date, s.user_id, s.customer_id, s.total_amount, s.payment_method,
					       COALESCE(u.username, '')
					FROM Sales s
					LEFT JOIN Users u ON u.user_id = s.user_id
					WHERE s.date >= ? AND s.date <= ? AND s.user_id = ?
					ORDER BY s.date DESC
					""",
					(f"{start} 00:00:00", f"{end} 23:59:59", int(user_id)),
				)
			elif cashier_username:
				cursor.execute(
					"""
					SELECT s.sale_id, s.date, s.user_id, s.customer_id, s.total_amount, s.payment_method,
					       COALESCE(u.username, '')
					FROM Sales s
					LEFT JOIN Users u ON u.user_id = s.user_id
					WHERE s.date >= ? AND s.date <= ? AND LOWER(COALESCE(u.username, '')) = LOWER(?)
					ORDER BY s.date DESC
					""",
					(f"{start} 00:00:00", f"{end} 23:59:59", cashier_username.strip()),
				)
			else:
				cursor.execute(
					"""
					SELECT s.sale_id, s.date, s.user_id, s.customer_id, s.total_amount, s.payment_method,
					       COALESCE(u.username, '')
					FROM Sales s
					LEFT JOIN Users u ON u.user_id = s.user_id
					WHERE s.date >= ? AND s.date <= ?
					ORDER BY s.date DESC
					""",
					(f"{start} 00:00:00", f"{end} 23:59:59"),
				)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("sales.get_sales_by_date_range", exc)
		return []

	return [_to_sale_dict(row) for row in rows]
