"""Step 13.3 final checklist verification script."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from database.db_connection import get_connection
from database.db_setup import initialize_database
from modules.auth import hash_password, login, logout
from modules.customers import add_customer, get_customer_by_id, search_customers, update_customer
from modules.payments import process_payment
from modules.products import add_product, delete_product, get_product_by_barcode, get_product_by_id, update_product
from modules.reports import daily_sales_report
from modules.sales import create_sale
from ui.dashboard import DashboardScreen


def _ensure_user(username: str, password: str, role: str) -> None:
	with get_connection() as conn:
		cur = conn.cursor()
		cur.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
		if cur.fetchone() is None:
			cur.execute(
				"INSERT INTO Users (username, password_hash, role) VALUES (?, ?, ?)",
				(username, hash_password(password), role),
			)
			conn.commit()


def _no_sql_concat_scan() -> bool:
	bad_patterns = ("execute(f\"", "execute( f\"", "cursor.execute(f\"")
	for py in PROJECT_ROOT.rglob("*.py"):
		if "venv" in py.parts or "__pycache__" in py.parts:
			continue
		text = py.read_text(encoding="utf-8", errors="ignore")
		if any(p in text for p in bad_patterns):
			return False
	return True


def run() -> None:
	initialize_database()
	_ensure_user("manager1", "manager123", "Manager")
	_ensure_user("cashier1", "cashier123", "Cashier")

	sfx = datetime.now().strftime("%H%M%S")
	today = datetime.now().strftime("%Y-%m-%d")
	all_ok = True

	# 1) Launch/bootstrap path
	try:
		initialize_database()
		ok = True
	except Exception:
		ok = False
	all_ok = all_ok and ok
	print("CHECK 1 launch/bootstrap:", "PASS" if ok else "FAIL")

	# 2) Login/logout for all 3 roles
	ok = True
	for username, password, role in [
		("admin", "admin123", "Admin"),
		("manager1", "manager123", "Manager"),
		("cashier1", "cashier123", "Cashier"),
	]:
		user = login(username, password)
		if not user or user.get("role") != role:
			ok = False
		logout()
	all_ok = all_ok and ok
	print("CHECK 2 login/logout all roles:", "PASS" if ok else "FAIL")

	# 3) Product + Customer CRUD
	ok = True
	barcode = f"CHK-P-{sfx}"
	if not add_product("Checklist Product", "General", 11.5, 9, barcode):
		ok = False
	p = get_product_by_barcode(barcode)
	if not p:
		ok = False
	else:
		if not update_product(p["product_id"], "Checklist Product 2", "General", 12.0, 7, barcode):
			ok = False
		p2 = get_product_by_id(p["product_id"])
		if not p2 or p2["product_name"] != "Checklist Product 2":
			ok = False

	cid = add_customer("Checklist Customer", "0201111111", "check@example.com", "Accra")
	c = get_customer_by_id(cid)
	if not c:
		ok = False
	if not update_customer(cid, "Checklist Customer 2", "0201111111", "check@example.com", "Kumasi"):
		ok = False
	if not search_customers("Checklist Customer 2"):
		ok = False

	all_ok = all_ok and ok
	print("CHECK 3 CRUD products/customers:", "PASS" if ok else "FAIL")

	# 4) End-to-end sale (add items -> checkout -> payment -> receipt-triggerable)
	ok = True
	if not p:
		ok = False
	else:
		sale_id = create_sale(
			1,
			cid,
			[{"product_id": p["product_id"], "quantity": 2, "price": 12.0}],
			"Cash",
			discount=1.0,
		)
		change = process_payment(sale_id, 30.0, "Cash")
		if abs(change - 7.0) > 1e-9:
			ok = False
	all_ok = all_ok and ok
	print("CHECK 4 complete sale flow:", "PASS" if ok else "FAIL")

	# 5) Inventory auto-deduct after sale
	ok = True
	if p:
		pa = get_product_by_id(p["product_id"])
		if not pa or pa["quantity"] > 7:
			ok = False
	else:
		ok = False
	all_ok = all_ok and ok
	print("CHECK 5 inventory auto-deduct:", "PASS" if ok else "FAIL")

	# 6) Reports accuracy (daily report reflects transactions)
	ok = daily_sales_report(today)["transactions"] >= 1
	all_ok = all_ok and ok
	print("CHECK 6 reports show data:", "PASS" if ok else "FAIL")

	# 7) No plain-text passwords in DB
	with get_connection() as conn:
		cur = conn.cursor()
		cur.execute("SELECT password_hash FROM Users")
		rows = [r[0] for r in cur.fetchall()]
	ok = all(isinstance(h, str) and h.startswith("$2") for h in rows)
	all_ok = all_ok and ok
	print("CHECK 7 no plain-text passwords:", "PASS" if ok else "FAIL")

	# 8) No raw SQL string interpolation in code (quick static guard)
	ok = _no_sql_concat_scan()
	all_ok = all_ok and ok
	print("CHECK 8 no raw SQL f-string execute:", "PASS" if ok else "FAIL")

	# 9) Cashier cannot access admin-only modules in dashboard nav
	cashier_modules = DashboardScreen.ROLE_MODULES["Cashier"]
	ok = "Product Management" not in cashier_modules and "User Management" not in cashier_modules
	all_ok = all_ok and ok
	print("CHECK 9 cashier restricted nav:", "PASS" if ok else "FAIL")

	# cleanup
	if p:
		delete_product(p["product_id"])

	print("STEP 13.3 SUMMARY:", "ALL PASS" if all_ok else "HAS FAILURES")


if __name__ == "__main__":
	run()
