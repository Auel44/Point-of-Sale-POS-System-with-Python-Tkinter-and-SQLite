"""Customer management module."""

from __future__ import annotations

from typing import Any

from database.db_connection import get_connection
from utils.helpers import log_error


def _to_customer_dict(row: tuple[Any, ...]) -> dict[str, Any]:
	return {
		"customer_id": row[0],
		"name": row[1],
		"phone": row[2],
		"email": row[3],
		"address": row[4],
		"loyalty_points": row[5],
	}


def add_customer(name: str, phone: str, email: str, address: str) -> int:
	"""Insert a new customer and return the new customer_id."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				INSERT INTO Customers (name, phone, email, address, loyalty_points)
				VALUES (?, ?, ?, ?, 0)
				""",
				(name.strip(), phone.strip(), email.strip(), address.strip()),
			)
			conn.commit()
			return cursor.lastrowid  # type: ignore[return-value]
	except Exception as exc:
		log_error("customers.add_customer", exc)
		return 0


def get_all_customers() -> list[dict[str, Any]]:
	"""Return all customers ordered by name."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT customer_id, name, phone, email, address, loyalty_points
				FROM Customers
				ORDER BY name COLLATE NOCASE ASC
				"""
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("customers.get_all_customers", exc)
		return []
	return [_to_customer_dict(row) for row in rows]


def get_customer_by_id(customer_id: int) -> dict[str, Any] | None:
	"""Return a single customer by id, or None when not found."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT customer_id, name, phone, email, address, loyalty_points
				FROM Customers WHERE customer_id = ?
				""",
				(customer_id,),
			)
			row = cursor.fetchone()
	except Exception as exc:
		log_error("customers.get_customer_by_id", exc)
		return None
	return _to_customer_dict(row) if row else None


def search_customers(query: str) -> list[dict[str, Any]]:
	"""Return customers whose name or phone matches the query."""
	pattern = f"%{query.strip()}%"
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT customer_id, name, phone, email, address, loyalty_points
				FROM Customers
				WHERE name LIKE ? OR phone LIKE ?
				ORDER BY name COLLATE NOCASE ASC
				""",
				(pattern, pattern),
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("customers.search_customers", exc)
		return []
	return [_to_customer_dict(row) for row in rows]


def update_customer(
	customer_id: int, name: str, phone: str, email: str, address: str
) -> bool:
	"""Update an existing customer's details and return True on success."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				UPDATE Customers
				SET name = ?, phone = ?, email = ?, address = ?
				WHERE customer_id = ?
				""",
				(name.strip(), phone.strip(), email.strip(), address.strip(), customer_id),
			)
			conn.commit()
			return cursor.rowcount > 0
	except Exception as exc:
		log_error("customers.update_customer", exc)
		return False


def get_purchase_history(customer_id: int) -> list[dict[str, Any]]:
	"""Return all sales associated with a customer, newest first."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT sale_id, date, total_amount, payment_method
				FROM Sales
				WHERE customer_id = ?
				ORDER BY date DESC
				""",
				(customer_id,),
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("customers.get_purchase_history", exc)
		return []
	return [
		{
			"sale_id": r[0],
			"date": r[1],
			"total_amount": r[2],
			"payment_method": r[3],
		}
		for r in rows
	]


def add_loyalty_points(customer_id: int, points: int) -> bool:
	"""Add loyalty points to a customer's balance and return True on success."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				UPDATE Customers
				SET loyalty_points = loyalty_points + ?
				WHERE customer_id = ?
				""",
				(int(points), customer_id),
			)
			conn.commit()
			return cursor.rowcount > 0
	except Exception as exc:
		log_error("customers.add_loyalty_points", exc)
		return False
