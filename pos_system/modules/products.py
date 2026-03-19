"""Product management business logic for the POS system."""

from __future__ import annotations

from typing import Any

from database.db_connection import get_connection
from utils.helpers import log_error


def _to_product_dict(row: tuple[Any, ...]) -> dict[str, Any]:
	"""Convert a product table row to a dictionary shape used by the app."""
	return {
		"product_id": row[0],
		"product_name": row[1],
		"category": row[2],
		"price": row[3],
		"quantity": row[4],
		"barcode": row[5],
		"username": row[6],
	}


def get_all_products() -> list[dict[str, Any]]:
	"""Return all products ordered by name."""
	try:
		with get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				"""
				SELECT p.product_id, p.product_name, p.category, p.price, p.quantity, p.barcode, u.username
				FROM Products p
				LEFT JOIN Users u ON u.user_id = p.added_by_user_id
				ORDER BY p.product_name COLLATE NOCASE ASC
				"""
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("products.get_all_products", exc)
		return []

	return [_to_product_dict(row) for row in rows]


def get_product_by_barcode(barcode: str) -> dict[str, Any] | None:
	"""Return a single product by barcode, or None when not found."""
	try:
		with get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				"""
				SELECT p.product_id, p.product_name, p.category, p.price, p.quantity, p.barcode, u.username
				FROM Products p
				LEFT JOIN Users u ON u.user_id = p.added_by_user_id
				WHERE p.barcode = ?
				""",
				(barcode.strip(),),
			)
			row = cursor.fetchone()
	except Exception as exc:
		log_error("products.get_product_by_barcode", exc)
		return None

	return _to_product_dict(row) if row else None


def get_product_by_id(product_id: int) -> dict[str, Any] | None:
	"""Return a single product by id, or None when not found."""
	try:
		with get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				"""
				SELECT p.product_id, p.product_name, p.category, p.price, p.quantity, p.barcode, u.username
				FROM Products p
				LEFT JOIN Users u ON u.user_id = p.added_by_user_id
				WHERE p.product_id = ?
				""",
				(product_id,),
			)
			row = cursor.fetchone()
	except Exception as exc:
		log_error("products.get_product_by_id", exc)
		return None

	return _to_product_dict(row) if row else None


def add_product(
	name: str,
	category: str,
	price: float,
	quantity: int,
	barcode: str,
	actor: dict[str, Any] | None = None,
) -> bool:
	"""Insert a new product row and return True when successful."""
	try:
		with get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				"""
				INSERT INTO Products (product_name, category, price, quantity, barcode, added_by_user_id)
				VALUES (?, ?, ?, ?, ?, ?)
				""",
				(
					name.strip(),
					category.strip(),
					float(price),
					int(quantity),
					barcode.strip(),
					actor.get("user_id") if actor else None,
				),
			)
			connection.commit()
		return True
	except Exception as exc:
		log_error("products.add_product", exc)
		return False


def update_product(product_id: int, name: str, category: str, price: float, quantity: int, barcode: str) -> bool:
	"""Update an existing product and return True when a row is updated."""
	try:
		with get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				"""
				UPDATE Products
				SET product_name = ?, category = ?, price = ?, quantity = ?, barcode = ?
				WHERE product_id = ?
				""",
				(name.strip(), category.strip(), float(price), int(quantity), barcode.strip(), product_id),
			)
			connection.commit()
			return cursor.rowcount > 0
	except Exception as exc:
		log_error("products.update_product", exc)
		return False


def delete_product(product_id: int) -> bool:
	"""Delete a product by id and return True when a row is removed."""
	try:
		with get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute("DELETE FROM Products WHERE product_id = ?", (product_id,))
			connection.commit()
			return cursor.rowcount > 0
	except Exception as exc:
		log_error("products.delete_product", exc)
		return False


def search_products(query: str) -> list[dict[str, Any]]:
	"""Search products by name, category, or barcode."""
	search_value = f"%{query.strip()}%"
	try:
		with get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				"""
				SELECT p.product_id, p.product_name, p.category, p.price, p.quantity, p.barcode, u.username
				FROM Products p
				LEFT JOIN Users u ON u.user_id = p.added_by_user_id
				WHERE p.product_name LIKE ?
				   OR p.category LIKE ?
				   OR p.barcode LIKE ?
				ORDER BY p.product_name COLLATE NOCASE ASC
				""",
				(search_value, search_value, search_value),
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("products.search_products", exc)
		return []

	return [_to_product_dict(row) for row in rows]
