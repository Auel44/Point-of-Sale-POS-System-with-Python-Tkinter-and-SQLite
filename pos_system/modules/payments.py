"""Payment processing module."""

from __future__ import annotations

from typing import Any

from database.db_connection import get_connection
from utils.helpers import log_error


def process_payment(sale_id: int, amount_paid: float, payment_method: str) -> float:
	"""Record a payment and return the change amount.

	Inserts a row into Payments and returns (amount_paid - sale total).
	Raises ValueError when amount_paid is less than the sale total.
	"""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"SELECT total_amount FROM Sales WHERE sale_id = ?",
				(sale_id,),
			)
			row = cursor.fetchone()
			if row is None:
				raise ValueError(f"Sale {sale_id} not found.")
			total: float = row[0]

			change = round(amount_paid - total, 2)
			if change < 0:
				raise ValueError(
					f"Amount paid (GH₵ {amount_paid:.2f}) is less than total (GH₵ {total:.2f})."
				)

			cursor.execute(
				"""
				INSERT INTO Payments (sale_id, amount_paid, payment_method, change_given)
				VALUES (?, ?, ?, ?)
				""",
				(sale_id, round(amount_paid, 2), payment_method.strip(), change),
			)
			conn.commit()
	except ValueError:
		raise
	except Exception as exc:
		log_error("payments.process_payment", exc)
		raise

	return change


def get_payment_by_sale(sale_id: int) -> dict[str, Any] | None:
	"""Return the payment record for a sale, or None when not found."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT payment_id, sale_id, amount_paid, payment_method, change_given
				FROM Payments
				WHERE sale_id = ?
				""",
				(sale_id,),
			)
			row = cursor.fetchone()
	except Exception as exc:
		log_error("payments.get_payment_by_sale", exc)
		return None

	if row is None:
		return None
	return {
		"payment_id": row[0],
		"sale_id": row[1],
		"amount_paid": row[2],
		"payment_method": row[3],
		"change_given": row[4],
	}


def list_recent_payments(limit: int = 200, user_id: int | None = None) -> list[dict[str, Any]]:
	"""Return recent payments with sale metadata for the Payments screen."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			if user_id is None:
				cursor.execute(
					"""
					SELECT p.payment_id, p.sale_id, s.date, p.amount_paid, p.payment_method,
					       p.change_given, s.total_amount, COALESCE(u.username, '')
					FROM Payments p
					JOIN Sales s ON s.sale_id = p.sale_id
					LEFT JOIN Users u ON u.user_id = s.user_id
					ORDER BY s.date DESC, p.payment_id DESC
					LIMIT ?
					""",
					(max(1, int(limit)),),
				)
			else:
				cursor.execute(
					"""
					SELECT p.payment_id, p.sale_id, s.date, p.amount_paid, p.payment_method,
					       p.change_given, s.total_amount, COALESCE(u.username, '')
					FROM Payments p
					JOIN Sales s ON s.sale_id = p.sale_id
					LEFT JOIN Users u ON u.user_id = s.user_id
					WHERE s.user_id = ?
					ORDER BY s.date DESC, p.payment_id DESC
					LIMIT ?
					""",
					(int(user_id), max(1, int(limit))),
				)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("payments.list_recent_payments", exc)
		return []

	return [
		{
			"payment_id": row[0],
			"sale_id": row[1],
			"date": row[2],
			"amount_paid": row[3],
			"payment_method": row[4],
			"change_given": row[5],
			"sale_total": row[6],
			"cashier_username": row[7],
		}
		for row in rows
	]


def list_payments_by_date_range(start: str, end: str, user_id: int | None = None) -> list[dict[str, Any]]:
	"""Return payments within [start, end] date range, optionally for a specific cashier."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			if user_id is None:
				cursor.execute(
					"""
					SELECT p.payment_id, p.sale_id, s.date, p.amount_paid, p.payment_method,
					       p.change_given, s.total_amount, COALESCE(u.username, '')
					FROM Payments p
					JOIN Sales s ON s.sale_id = p.sale_id
					LEFT JOIN Users u ON u.user_id = s.user_id
					WHERE s.date >= ? AND s.date <= ?
					ORDER BY s.date DESC, p.payment_id DESC
					""",
					(f"{start} 00:00:00", f"{end} 23:59:59"),
				)
			else:
				cursor.execute(
					"""
					SELECT p.payment_id, p.sale_id, s.date, p.amount_paid, p.payment_method,
					       p.change_given, s.total_amount, COALESCE(u.username, '')
					FROM Payments p
					JOIN Sales s ON s.sale_id = p.sale_id
					LEFT JOIN Users u ON u.user_id = s.user_id
					WHERE s.date >= ? AND s.date <= ? AND s.user_id = ?
					ORDER BY s.date DESC, p.payment_id DESC
					""",
					(f"{start} 00:00:00", f"{end} 23:59:59", int(user_id)),
				)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("payments.list_payments_by_date_range", exc)
		return []

	return [
		{
			"payment_id": row[0],
			"sale_id": row[1],
			"date": row[2],
			"amount_paid": row[3],
			"payment_method": row[4],
			"change_given": row[5],
			"sale_total": row[6],
			"cashier_username": row[7],
		}
		for row in rows
	]
