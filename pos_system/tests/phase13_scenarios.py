"""Phase 13 scenario checks (8 required integration scenarios)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

# Ensure project root is importable when running from tests/.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from database.db_connection import get_connection
from database.db_setup import initialize_database
from modules.auth import hash_password, login, logout
from modules.customers import add_customer, get_purchase_history
from modules.inventory import adjust_stock, get_inventory_log
from modules.payments import process_payment
from modules.products import add_product, delete_product, get_product_by_barcode
from modules.reports import daily_sales_report
from modules.sales import create_sale
from ui.dashboard import DashboardScreen


def _ensure_cashier_user() -> None:
	with get_connection() as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT user_id FROM Users WHERE username = ?", ("cashier1",))
		if cursor.fetchone() is None:
			cursor.execute(
				"""
				INSERT INTO Users (username, password_hash, role)
				VALUES (?, ?, ?)
				""",
				("cashier1", hash_password("cashier123"), "Cashier"),
			)
			conn.commit()


def run_phase13_checks() -> None:
	initialize_database()
	_ensure_cashier_user()

	today = datetime.now().strftime("%Y-%m-%d")
	suffix = datetime.now().strftime("%H%M%S")

	# Scenario 1: Register new product and verify listing
	barcode_a = f"P13-A-{suffix}"
	assert add_product("P13 Product A", "General", 12.0, 10, barcode_a)
	product_a = get_product_by_barcode(barcode_a)
	assert product_a is not None, "Scenario 1 failed: product not found after add"
	print("Scenario 1 PASS")

	# Scenario 2: Process sale with two products and confirm stock deduction
	barcode_b = f"P13-B-{suffix}"
	assert add_product("P13 Product B", "General", 7.0, 8, barcode_b)
	product_b = get_product_by_barcode(barcode_b)
	assert product_b is not None
	start_a = int(product_a["quantity"])
	start_b = int(product_b["quantity"])

	items = [
		{"product_id": product_a["product_id"], "quantity": 2, "price": 12.0},
		{"product_id": product_b["product_id"], "quantity": 1, "price": 7.0},
	]
	sale_id = create_sale(1, None, items, "Cash", discount=1.0)

	product_a_after = get_product_by_barcode(barcode_a)
	product_b_after = get_product_by_barcode(barcode_b)
	assert product_a_after and int(product_a_after["quantity"]) == start_a - 2
	assert product_b_after and int(product_b_after["quantity"]) == start_b - 1
	print("Scenario 2 PASS")

	# Scenario 3: Process cash payment and verify change calculation
	change = process_payment(sale_id, 40.0, "Cash")
	assert abs(change - 10.0) < 1e-9, f"Scenario 3 failed: expected 10.0 change, got {change}"
	print("Scenario 3 PASS")

	# Scenario 4: Wrong login credentials denied
	assert login("admin", "wrong-password") is None
	print("Scenario 4 PASS")

	# Scenario 5: Cashier role cannot access admin-only screens (nav-level)
	cashier_modules = DashboardScreen.ROLE_MODULES["Cashier"]
	assert "Product Management" not in cashier_modules
	assert "User Management" not in cashier_modules
	print("Scenario 5 PASS")

	# Scenario 6: Daily report totals match newly recorded sales delta
	before = daily_sales_report(today)
	barcode_c = f"P13-C-{suffix}"
	assert add_product("P13 Product C", "General", 5.0, 6, barcode_c)
	product_c = get_product_by_barcode(barcode_c)
	assert product_c is not None
	sale_id_2 = create_sale(
		1,
		None,
		[{"product_id": product_c["product_id"], "quantity": 2, "price": 5.0}],
		"Cash",
		discount=0.0,
	)
	process_payment(sale_id_2, 20.0, "Cash")
	after = daily_sales_report(today)
	delta = round(after["total_sales"] - before["total_sales"], 2)
	assert abs(delta - 10.0) < 1e-9, f"Scenario 6 failed: expected delta 10.0, got {delta}"
	print("Scenario 6 PASS")

	# Scenario 7: Manual stock adjustment recorded in inventory log
	assert adjust_stock(product_c["product_id"], 3, "Phase13 test restock")
	logs = get_inventory_log()
	assert any(
		l["product_id"] == product_c["product_id"] and l["change_amount"] == 3 and "Phase13" in l["reason"]
		for l in logs
	), "Scenario 7 failed: inventory log entry missing"
	print("Scenario 7 PASS")

	# Scenario 8: Register customer, attach to sale, verify purchase history
	customer_id = add_customer("P13 Customer", "0200000000", "p13@example.com", "Accra")
	assert customer_id > 0
	sale_id_3 = create_sale(
		1,
		customer_id,
		[{"product_id": product_b["product_id"], "quantity": 1, "price": 7.0}],
		"Cash",
		discount=0.0,
	)
	process_payment(sale_id_3, 10.0, "Cash")
	history = get_purchase_history(customer_id)
	assert any(h["sale_id"] == sale_id_3 for h in history), "Scenario 8 failed: sale missing from customer history"
	print("Scenario 8 PASS")

	# Cleanup test products
	delete_product(product_a["product_id"])
	delete_product(product_b["product_id"])
	delete_product(product_c["product_id"])
	logout()
	print("Phase 13 scenarios complete: ALL PASS")


if __name__ == "__main__":
	run_phase13_checks()
