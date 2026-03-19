"""Reporting and analytics module."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from database.db_connection import get_connection
from utils.helpers import log_error


def daily_sales_report(date: str) -> dict[str, Any]:
	"""Return daily totals and top-selling products for a date (YYYY-MM-DD)."""
	start = f"{date} 00:00:00"
	end = f"{date} 23:59:59"

	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT COALESCE(SUM(total_amount), 0), COUNT(*)
				FROM Sales
				WHERE date >= ? AND date <= ?
				""",
				(start, end),
			)
			total_sales, transactions = cursor.fetchone()

			cursor.execute(
				"""
				SELECT p.product_id, p.product_name,
				       SUM(si.quantity) AS units_sold,
				       SUM(si.quantity * si.price) AS revenue
				FROM Sales_Items si
				JOIN Sales s ON s.sale_id = si.sale_id
				JOIN Products p ON p.product_id = si.product_id
				WHERE s.date >= ? AND s.date <= ?
				GROUP BY p.product_id, p.product_name
				ORDER BY units_sold DESC, revenue DESC
				LIMIT 5
				""",
				(start, end),
			)
			top_products = [
				{
					"product_id": row[0],
					"product_name": row[1],
					"units_sold": row[2],
					"revenue": round(float(row[3] or 0), 2),
				}
				for row in cursor.fetchall()
			]
	except Exception as exc:
		log_error("reports.daily_sales_report", exc)
		return {"date": date, "total_sales": 0.0, "transactions": 0, "top_products": []}

	return {
		"date": date,
		"total_sales": round(float(total_sales or 0), 2),
		"transactions": int(transactions or 0),
		"top_products": top_products,
	}


def weekly_sales_report(start_date: str) -> list[dict[str, Any]]:
	"""Return day-by-day totals for 7 days starting from start_date."""
	start_dt = datetime.strptime(start_date, "%Y-%m-%d")
	end_dt = start_dt + timedelta(days=6)

	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT substr(date, 1, 10) AS sale_day,
				       COALESCE(SUM(total_amount), 0) AS total_sales,
				       COUNT(*) AS transactions
				FROM Sales
				WHERE date >= ? AND date <= ?
				GROUP BY sale_day
				ORDER BY sale_day ASC
				""",
				(
					f"{start_dt.strftime('%Y-%m-%d')} 00:00:00",
					f"{end_dt.strftime('%Y-%m-%d')} 23:59:59",
				),
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("reports.weekly_sales_report", exc)
		return []

	by_day = {
		row[0]: {
			"date": row[0],
			"total_sales": round(float(row[1] or 0), 2),
			"transactions": int(row[2] or 0),
		}
		for row in rows
	}

	result: list[dict[str, Any]] = []
	for offset in range(7):
		day = (start_dt + timedelta(days=offset)).strftime("%Y-%m-%d")
		result.append(by_day.get(day, {"date": day, "total_sales": 0.0, "transactions": 0}))
	return result


def product_performance_report() -> list[dict[str, Any]]:
	"""Return product performance sorted by units sold (desc)."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT p.product_id,
				       p.product_name,
				       COALESCE(SUM(si.quantity), 0) AS units_sold,
				       COALESCE(SUM(si.quantity * si.price), 0) AS revenue
				FROM Products p
				LEFT JOIN Sales_Items si ON si.product_id = p.product_id
				GROUP BY p.product_id, p.product_name
				ORDER BY units_sold DESC, revenue DESC, p.product_name ASC
				"""
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("reports.product_performance_report", exc)
		return []

	return [
		{
			"product_id": row[0],
			"product_name": row[1],
			"units_sold": int(row[2] or 0),
			"revenue": round(float(row[3] or 0), 2),
		}
		for row in rows
	]


def inventory_report(low_stock_threshold: int = 5) -> list[dict[str, Any]]:
	"""Return current stock levels and low-stock flags for each product."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT product_id, product_name, category, quantity, price
				FROM Products
				ORDER BY product_name COLLATE NOCASE ASC
				"""
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("reports.inventory_report", exc)
		return []

	return [
		{
			"product_id": row[0],
			"product_name": row[1],
			"category": row[2],
			"quantity": int(row[3]),
			"price": round(float(row[4]), 2),
			"low_stock": int(row[3]) <= low_stock_threshold,
		}
		for row in rows
	]


def cashier_report(user_id: int | str, start: str, end: str) -> dict[str, Any]:
	"""Return sales summary for a cashier between two dates (inclusive).

	user_id can be a numeric cashier ID or a cashier username.
	"""
	start_ts = f"{start} 00:00:00"
	end_ts = f"{end} 23:59:59"

	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			resolved_user_id: int
			if isinstance(user_id, int) or str(user_id).strip().isdigit():
				resolved_user_id = int(user_id)
				cursor.execute(
					"SELECT user_id, username, role FROM Users WHERE user_id = ?",
					(resolved_user_id,),
				)
			else:
				username = str(user_id).strip()
				cursor.execute(
					"SELECT user_id, username, role FROM Users WHERE LOWER(username) = LOWER(?)",
					(username,),
				)
			user_row = cursor.fetchone()
			if user_row is None:
				return {
					"user_id": user_id,
					"username": "Unknown",
					"role": "Unknown",
					"start": start,
					"end": end,
					"total_sales": 0.0,
					"transactions": 0,
					"sales": [],
				}

			resolved_user_id = int(user_row[0])
			cursor.execute(
				"""
				SELECT sale_id, date, total_amount, payment_method
				FROM Sales
				WHERE user_id = ? AND date >= ? AND date <= ?
				ORDER BY date DESC
				""",
				(resolved_user_id, start_ts, end_ts),
			)
			sales_rows = cursor.fetchall()
	except Exception as exc:
		log_error("reports.cashier_report", exc)
		return {
			"user_id": user_id,
			"username": "Unknown",
			"role": "Unknown",
			"start": start,
			"end": end,
			"total_sales": 0.0,
			"transactions": 0,
			"sales": [],
		}

	sales = [
		{
			"sale_id": row[0],
			"date": row[1],
			"total_amount": round(float(row[2] or 0), 2),
			"payment_method": row[3],
		}
		for row in sales_rows
	]
	total_sales = round(sum(item["total_amount"] for item in sales), 2)

	return {
		"user_id": user_row[0],
		"username": user_row[1],
		"role": user_row[2],
		"start": start,
		"end": end,
		"total_sales": total_sales,
		"transactions": len(sales),
		"sales": sales,
	}
