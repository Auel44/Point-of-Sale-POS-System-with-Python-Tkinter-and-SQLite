"""Sales screen — barcode scanning, cart management, and checkout."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from modules.products import get_product_by_barcode, get_product_by_id, search_products
from ui.theme import apply_modern_theme, themed_confirm_dialog
from utils.validators import is_valid_price

TAX_RATE = 0.0  # Set to e.g. 0.15 for 15% VAT when required


class SalesScreen(tk.Toplevel):
	"""Cart-based sales entry screen."""
	ALLOWED_ROLES = {"Admin", "Manager", "Cashier"}

	def __init__(self, parent: tk.Tk, user: dict[str, Any]) -> None:
		super().__init__(parent)
		role = str(user.get("role", ""))
		if role not in self.ALLOWED_ROLES:
			messagebox.showerror("Access Denied", "You are not authorized to process sales.", parent=self)
			self.destroy()
			return

		self.title("POS - Sales")
		self.geometry("900x560")
		self.minsize(700, 440)
		self.grab_set()
		apply_modern_theme(self)

		self.user = user
		# cart: list of {"product_id", "product_name", "unit_price", "quantity"}
		self._cart: list[dict[str, Any]] = []

		self._build_ui()

	# ------------------------------------------------------------------
	# Layout
	# ------------------------------------------------------------------

	def _build_ui(self) -> None:
		# ── Top card: title + barcode entry ──────────────────────────
		top = ttk.Frame(self, padding=(14, 12), style="Card.TFrame")
		top.pack(fill="x")

		title_wrap = ttk.Frame(top, style="Card.TFrame")
		title_wrap.pack(side="left")
		ttk.Label(title_wrap, text="Sales Checkout", style="SectionTitle.TLabel").pack(anchor="w")
		ttk.Label(
			title_wrap,
			text="Scan barcode or type a code to add items.",
			style="SectionSub.TLabel",
		).pack(anchor="w")

		barcode_frame = ttk.Frame(top, style="Card.TFrame")
		barcode_frame.pack(side="right")
		ttk.Label(barcode_frame, text="Barcode / ID / Name:", style="SectionSub.TLabel").pack(
			side="left", padx=(0, 6)
		)
		self._barcode_var = tk.StringVar()
		barcode_entry = ttk.Entry(barcode_frame, textvariable=self._barcode_var, width=26)
		barcode_entry.pack(side="left")
		barcode_entry.bind("<Return>", lambda _e: self._add_by_barcode())
		barcode_entry.focus_set()
		ttk.Button(
			barcode_frame, text="Add Item", command=self._add_by_barcode, style="Primary.TButton"
		).pack(
			side="left", padx=(6, 0)
		)

		# ── Cart table card ───────────────────────────────────────────
		cart_frame = ttk.Frame(self, padding=(12, 10), style="Card.TFrame")
		cart_frame.pack(expand=True, fill="both")
		header_row = ttk.Frame(cart_frame, style="Card.TFrame")
		header_row.pack(fill="x", pady=(0, 8))
		ttk.Label(header_row, text="Cart Items", style="SectionTitle.TLabel").pack(side="left")
		self._item_count_label = ttk.Label(header_row, text="0 items", style="InfoBadge.TLabel")
		self._item_count_label.pack(side="right")

		cols = ("product_id", "product_name", "unit_price", "quantity", "subtotal")
		self.cart_tree = ttk.Treeview(
			cart_frame, columns=cols, show="headings", selectmode="browse", height=14
		)

		headers = {
			"product_id": ("ID", 50),
			"product_name": ("Product Name", 280),
			"unit_price": ("Unit Price", 100),
			"quantity": ("Qty", 70),
			"subtotal": ("Subtotal", 110),
		}
		for col, (label, width) in headers.items():
			self.cart_tree.heading(col, text=label)
			anchor = "e" if col in ("unit_price", "subtotal") else (
				"center" if col in ("product_id", "quantity") else "w"
			)
			self.cart_tree.column(col, width=width, anchor=anchor)

		vsb = ttk.Scrollbar(cart_frame, orient="vertical", command=self.cart_tree.yview)
		self.cart_tree.configure(yscrollcommand=vsb.set)
		self.cart_tree.pack(side="left", expand=True, fill="both")
		vsb.pack(side="right", fill="y")
		self.cart_tree.bind("<Double-1>", lambda _e: self._edit_quantity())

		# ── Cart action buttons ──────────────────────────────────────
		btn_bar = ttk.Frame(self, padding=(12, 4), style="Card.TFrame")
		btn_bar.pack(fill="x")
		ttk.Button(btn_bar, text="Edit Quantity", command=self._edit_quantity, style="Primary.TButton").pack(
			side="left", padx=(0, 6)
		)
		ttk.Button(btn_bar, text="Remove Item", command=self._remove_item).pack(
			side="left", padx=(0, 6)
		)
		ttk.Button(btn_bar, text="Clear Cart", command=self._clear_cart, style="Danger.TButton").pack(side="left")

		# ── Totals panel ─────────────────────────────────────────────
		totals_frame = ttk.Frame(self, padding=(14, 10), style="Card.TFrame")
		totals_frame.pack(fill="x")
		totals_frame.columnconfigure(1, weight=1)
		ttk.Label(totals_frame, text="Order Summary", style="SectionTitle.TLabel").grid(
			row=0, column=0, sticky="w", pady=(0, 8)
		)

		ttk.Label(totals_frame, text="Discount (GH₵):", style="SectionSub.TLabel").grid(
			row=1, column=2, sticky="e", padx=(0, 6)
		)
		self._discount_var = tk.StringVar(value="0")
		discount_entry = ttk.Entry(
			totals_frame, textvariable=self._discount_var, width=10, justify="right"
		)
		discount_entry.grid(row=1, column=3, sticky="w")
		discount_entry.bind("<KeyRelease>", lambda _e: self._refresh_totals())

		ttk.Label(totals_frame, text="Subtotal:", style="SectionSub.TLabel").grid(
			row=1, column=4, sticky="e", padx=(20, 6)
		)
		self._subtotal_lbl = ttk.Label(totals_frame, text="GH₵ 0.00", font=("Segoe UI", 10))
		self._subtotal_lbl.grid(row=1, column=5, sticky="e")

		ttk.Label(totals_frame, text=f"Tax ({int(TAX_RATE*100)}%):", style="SectionSub.TLabel").grid(
			row=2, column=4, sticky="e", padx=(20, 6), pady=(2, 0)
		)
		self._tax_lbl = ttk.Label(totals_frame, text="GH₵ 0.00", font=("Segoe UI", 10))
		self._tax_lbl.grid(row=2, column=5, sticky="e")

		ttk.Label(totals_frame, text="Grand Total:", font=("Segoe UI", 11, "bold")).grid(
			row=3, column=4, sticky="e", padx=(20, 6), pady=(4, 0)
		)
		self._grand_total_lbl = ttk.Label(
			totals_frame, text="GH₵ 0.00", font=("Segoe UI", 12, "bold")
		)
		self._grand_total_lbl.grid(row=3, column=5, sticky="e")

		# ── Checkout button ──────────────────────────────────────────
		checkout_frame = ttk.Frame(self, padding=(12, 8), style="Card.TFrame")
		checkout_frame.pack(fill="x")
		ttk.Button(
			checkout_frame,
			text="Proceed to Payment  →",
			command=self._checkout,
			style="Primary.TButton",
		).pack(side="right")

		self._error_var = tk.StringVar()
		ttk.Label(
			checkout_frame, textvariable=self._error_var, foreground="red", font=("Segoe UI", 9)
		).pack(side="left")

	# ------------------------------------------------------------------
	# Cart logic
	# ------------------------------------------------------------------

	def _resolve_product(self, query: str) -> dict[str, Any] | None:
		"""Resolve a product by barcode, id, or name/category search."""
		product = get_product_by_barcode(query)
		if product is not None:
			return product

		if query.isdigit():
			product = get_product_by_id(int(query))
			if product is not None:
				return product

		matches = search_products(query)
		if len(matches) == 1:
			return matches[0]

		if len(matches) > 1:
			preview = ", ".join(
				f"{p['product_id']}:{p['product_name']}" for p in matches[:5]
			)
			self._error_var.set(
				f"Multiple matches for '{query}'. Use barcode or ID. Examples: {preview}"
			)
			return None

		return None

	def _add_by_barcode(self) -> None:
		"""Look up a product and add it to cart."""
		self._error_var.set("")
		query = self._barcode_var.get().strip()
		if not query:
			return

		product = self._resolve_product(query)
		if product is None:
			if not self._error_var.get():
				self._error_var.set(f"No product found for '{query}'.")
			return

		if product["quantity"] <= 0:
			self._error_var.set(f"'{product['product_name']}' is out of stock.")
			return

		# If already in cart, increment quantity (up to available stock)
		for item in self._cart:
			if item["product_id"] == product["product_id"]:
				new_qty = item["quantity"] + 1
				if new_qty > product["quantity"]:
					self._error_var.set(
						f"Only {product['quantity']} unit(s) of '{product['product_name']}' available."
					)
					return
				item["quantity"] = new_qty
				self._refresh_cart_tree()
				self._refresh_totals()
				self._barcode_var.set("")
				return

		self._cart.append(
			{
				"product_id": product["product_id"],
				"product_name": product["product_name"],
				"unit_price": product["price"],
				"quantity": 1,
			}
		)
		self._refresh_cart_tree()
		self._refresh_totals()
		self._barcode_var.set("")

	def _refresh_cart_tree(self) -> None:
		for row in self.cart_tree.get_children():
			self.cart_tree.delete(row)
		total_units = 0
		for item in self._cart:
			subtotal = item["unit_price"] * item["quantity"]
			total_units += int(item["quantity"])
			self.cart_tree.insert(
				"",
				"end",
				values=(
					item["product_id"],
					item["product_name"],
					f"{item['unit_price']:.2f}",
					item["quantity"],
					f"{subtotal:.2f}",
				),
			)
		self._item_count_label.config(text=f"{total_units} item(s)")

	def _refresh_totals(self) -> None:
		subtotal = sum(i["unit_price"] * i["quantity"] for i in self._cart)
		if is_valid_price(self._discount_var.get()):
			discount = max(0.0, float(self._discount_var.get()))
		else:
			discount = 0.0
		taxable = max(0.0, subtotal - discount)
		tax = round(taxable * TAX_RATE, 2)
		grand_total = round(taxable + tax, 2)

		self._subtotal_lbl.config(text=f"GH₵ {subtotal:.2f}")
		self._tax_lbl.config(text=f"GH₵ {tax:.2f}")
		self._grand_total_lbl.config(text=f"GH₵ {grand_total:.2f}")

	def _edit_quantity(self) -> None:
		"""Prompt user to change quantity of the selected cart item."""
		selected = self.cart_tree.selection()
		if not selected:
			messagebox.showinfo("Edit Quantity", "Select an item first.", parent=self)
			return
		idx = self.cart_tree.index(selected[0])
		item = self._cart[idx]

		new_qty = simpledialog.askinteger(
			"Edit Quantity",
			f"New quantity for '{item['product_name']}':",
			parent=self,
			minvalue=1,
		)
		if new_qty is None:
			return

		# Re-fetch latest stock to validate
		from modules.products import get_product_by_id

		product = get_product_by_id(item["product_id"])
		if product and new_qty > product["quantity"]:
			messagebox.showerror(
				"Stock",
				f"Only {product['quantity']} unit(s) available.",
				parent=self,
			)
			return

		item["quantity"] = new_qty
		self._refresh_cart_tree()
		self._refresh_totals()

	def _remove_item(self) -> None:
		selected = self.cart_tree.selection()
		if not selected:
			messagebox.showinfo("Remove Item", "Select an item first.", parent=self)
			return
		idx = self.cart_tree.index(selected[0])
		self._cart.pop(idx)
		self._refresh_cart_tree()
		self._refresh_totals()

	def _clear_cart(self) -> None:
		if not self._cart:
			return
		if themed_confirm_dialog(self, "Clear Cart", "Remove all items from the cart?"):
			self._cart.clear()
			self._refresh_cart_tree()
			self._refresh_totals()

	# ------------------------------------------------------------------
	# Checkout
	# ------------------------------------------------------------------

	def _checkout(self) -> None:
		self._error_var.set("")
		if not self._cart:
			self._error_var.set("Cart is empty — add at least one item before checkout.")
			return

		if is_valid_price(self._discount_var.get()):
			discount = max(0.0, float(self._discount_var.get()))
		else:
			discount = 0.0

		subtotal = sum(i["unit_price"] * i["quantity"] for i in self._cart)
		taxable = max(0.0, subtotal - discount)
		tax = round(taxable * TAX_RATE, 2)
		grand_total = round(taxable + tax, 2)

		# Build a snapshot of cart items (product_id, quantity, price per unit)
		cart_snapshot = [
			{
				"product_id": item["product_id"],
				"product_name": item["product_name"],
				"quantity": item["quantity"],
				"price": item["unit_price"],
			}
			for item in self._cart
		]

		# Open payment screen, passing cart data, totals, and session user
		from ui.payment_screen import PaymentScreen

		PaymentScreen(
			self,
			user=self.user,
			cart=cart_snapshot,
			discount=discount,
			tax=tax,
			grand_total=grand_total,
		)
