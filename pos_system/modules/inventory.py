"""Inventory tracking and stock management logic."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from database.db_connection import get_connection
from utils.helpers import log_error


def _timestamp() -> str:
	"""Return a consistent timestamp string for inventory records."""
	return datetime.now().isoformat(timespec="seconds")


def deduct_stock(product_id: int, quantity_sold: int) -> bool:
	"""Deduct stock after a sale and write an inventory log record."""
	if quantity_sold <= 0:
		return False

	try:
		with get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute("SELECT quantity FROM Products WHERE product_id = ?", (product_id,))
			row = cursor.fetchone()
			if row is None:
				return False

			current_quantity = int(row[0])
			if current_quantity < quantity_sold:
				return False

			new_quantity = current_quantity - quantity_sold
			cursor.execute(
				"UPDATE Products SET quantity = ? WHERE product_id = ?",
				(new_quantity, product_id),
			)
			cursor.execute(
				"""
				INSERT INTO Inventory (product_id, change_amount, reason, date)
				VALUES (?, ?, ?, ?)
				""",
				(product_id, -quantity_sold, "Sale transaction", _timestamp()),
			)
			connection.commit()
			return True
	except Exception as exc:
		log_error("inventory.deduct_stock", exc)
		return False


def adjust_stock(product_id: int, change_amount: int, reason: str, actor: dict[str, Any] | None = None) -> bool:
	"""Manually adjust stock and write an inventory log record."""
	if change_amount == 0:
		return False

	try:
		with get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute("SELECT quantity FROM Products WHERE product_id = ?", (product_id,))
			row = cursor.fetchone()
			if row is None:
				return False

			current_quantity = int(row[0])
			new_quantity = current_quantity + change_amount
			if new_quantity < 0:
				return False

			cursor.execute(
				"UPDATE Products SET quantity = ? WHERE product_id = ?",
				(new_quantity, product_id),
			)
			cursor.execute(
				"""
				INSERT INTO Inventory (product_id, change_amount, reason, date, user_id)
				VALUES (?, ?, ?, ?, ?)
				""",
				(product_id, change_amount, reason.strip() or "Manual adjustment", _timestamp(), actor.get("user_id") if actor else None),
			)
			connection.commit()
			return True
	except Exception as exc:
		log_error("inventory.adjust_stock", exc)
		return False


def get_low_stock_products(threshold: int = 5) -> list[dict[str, Any]]:
	"""Return products with quantity less than or equal to threshold."""
	try:
		with get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				"""
				SELECT product_id, product_name, category, price, quantity, barcode
				FROM Products
				WHERE quantity <= ?
				ORDER BY quantity ASC, product_name COLLATE NOCASE ASC
				""",
				(threshold,),
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("inventory.get_low_stock_products", exc)
		return []

	return [
		{
			"product_id": row[0],
			"product_name": row[1],
			"category": row[2],
			"price": row[3],
			"quantity": row[4],
			"barcode": row[5],
		}
		for row in rows
	]


def get_inventory_log() -> list[dict[str, Any]]:
	"""Return all inventory change records with product details."""
	try:
		with get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				"""
				SELECT i.inventory_id, i.product_id, p.product_name, i.change_amount, i.reason, i.date, u.username
				FROM Inventory i
				JOIN Products p ON p.product_id = i.product_id
				LEFT JOIN Users u on u.user_id = i.user_id
				ORDER BY i.inventory_id DESC
				"""
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("inventory.get_inventory_log", exc)
		return []

	return [
		{
			"inventory_id": row[0],
			"product_id": row[1],
			"product_name": row[2],
			"change_amount": row[3],
			"reason": row[4],
			"date": row[5],
			"username": row[6],
		}
		for row in rows
	]
