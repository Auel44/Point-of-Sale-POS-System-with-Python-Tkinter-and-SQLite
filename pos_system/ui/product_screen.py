"""Product management UI screen."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from modules.auth import CURRENT_USER
from modules import products
from ui.theme import apply_modern_theme, themed_confirm_dialog
from utils.validators import is_non_empty, is_valid_price, is_valid_quantity


class ProductScreen:
	"""UI for listing and managing products."""

	ALLOWED_ROLES = {"Admin"}

	def __init__(self, master: tk.Misc | None = None, user: dict[str, Any] | None = None) -> None:
		self._owns_root = master is None
		self.window = tk.Tk() if self._owns_root else tk.Toplevel(master)
		active_user = user or CURRENT_USER or {}
		role = str(active_user.get("role", ""))
		if role not in self.ALLOWED_ROLES:
			messagebox.showerror(
				"Access Denied",
				"Only Admin users can access Product Management.",
				parent=self.window,
			)
			self.window.destroy()
			return

		self.window.title("POS - Product Management")
		self.window.geometry("980x560")
		apply_modern_theme(self.window)

		self.search_var = tk.StringVar()
		self._build_layout()
		self.refresh_table()

	def _build_layout(self) -> None:
		container = ttk.Frame(self.window, padding=12)
		container.pack(expand=True, fill="both")

		header = ttk.Frame(container, style="Card.TFrame", padding=(12, 10))
		header.pack(fill="x", pady=(0, 10))
		title_wrap = ttk.Frame(header, style="Card.TFrame")
		title_wrap.pack(side="left")
		ttk.Label(title_wrap, text="Product Management", style="SectionTitle.TLabel").pack(anchor="w")
		ttk.Label(
			title_wrap,
			text="Catalog control, pricing, and stock setup.",
			style="SectionSub.TLabel",
		).pack(anchor="w")
		self._count_badge = ttk.Label(header, text="0 products", style="InfoBadge.TLabel")
		self._count_badge.pack(side="right")

		search_frame = ttk.Frame(container, style="Card.TFrame", padding=(12, 8))
		search_frame.pack(fill="x", pady=(0, 10))
		ttk.Label(search_frame, text="Search", style="SectionSub.TLabel").pack(side="left", padx=(0, 8))
		search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
		search_entry.pack(side="left")
		search_entry.bind("<KeyRelease>", lambda _e: self.refresh_table())
		ttk.Button(search_frame, text="Search", command=self.refresh_table, style="Primary.TButton").pack(
			side="left", padx=6
		)
		ttk.Button(search_frame, text="Clear", command=self._clear_search).pack(side="left")

		buttons = ttk.Frame(container, style="Card.TFrame", padding=(12, 8))
		buttons.pack(fill="x", pady=(0, 10))
		ttk.Button(buttons, text="Add Product", command=self._open_add_dialog, style="Primary.TButton").pack(
			side="left", padx=(0, 6)
		)
		ttk.Button(buttons, text="Edit Product", command=self._open_edit_dialog).pack(side="left", padx=(0, 6))
		ttk.Button(buttons, text="Delete Product", command=self._delete_selected_product, style="Danger.TButton").pack(
			side="left"
		)

		table_frame = ttk.Frame(container, style="Card.TFrame", padding=(8, 8))
		table_frame.pack(expand=True, fill="both")

		columns = ("product_id", "product_name", "category", "price", "quantity", "barcode")
		self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=16)

		self.table.heading("product_id", text="ID")
		self.table.heading("product_name", text="Product Name")
		self.table.heading("category", text="Category")
		self.table.heading("price", text="Price")
		self.table.heading("quantity", text="Quantity")
		self.table.heading("barcode", text="Barcode")

		self.table.column("product_id", width=70, anchor="center")
		self.table.column("product_name", width=250)
		self.table.column("category", width=160)
		self.table.column("price", width=100, anchor="e")
		self.table.column("quantity", width=90, anchor="center")
		self.table.column("barcode", width=200)

		scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
		self.table.configure(yscrollcommand=scrollbar.set)

		self.table.pack(side="left", expand=True, fill="both")
		scrollbar.pack(side="right", fill="y")

	def _clear_search(self) -> None:
		self.search_var.set("")
		self.refresh_table()

	def refresh_table(self) -> None:
		"""Reload table rows from storage based on current search query."""
		for item in self.table.get_children():
			self.table.delete(item)

		query = self.search_var.get().strip()
		rows = products.search_products(query) if query else products.get_all_products()

		for product in rows:
			self.table.insert(
				"",
				"end",
				values=(
					product["product_id"],
					product["product_name"],
					product["category"],
					f"{float(product['price']):.2f}",
					product["quantity"],
					product["barcode"],
				),
			)
		self._count_badge.config(text=f"{len(rows)} products")

	def _selected_product_id(self) -> int | None:
		selected = self.table.selection()
		if not selected:
			return None
		values = self.table.item(selected[0], "values")
		if not values:
			return None
		return int(values[0])

	def _open_add_dialog(self) -> None:
		ProductFormDialog(self.window, title="Add Product", on_submit=self._add_product)

	def _open_edit_dialog(self) -> None:
		product_id = self._selected_product_id()
		if product_id is None:
			messagebox.showwarning("No Selection", "Please select a product to edit.")
			return

		product = products.get_product_by_id(product_id)
		if product is None:
			messagebox.showerror("Not Found", "Selected product could not be found.")
			self.refresh_table()
			return

		ProductFormDialog(
			self.window,
			title="Edit Product",
			on_submit=lambda form_data: self._edit_product(product_id, form_data),
			initial_data=product,
		)

	def _add_product(self, form_data: dict[str, str]) -> bool:
		success = products.add_product(
			form_data["product_name"],
			form_data["category"],
			float(form_data["price"]),
			int(form_data["quantity"]),
			form_data["barcode"],
		)
		if success:
			self.refresh_table()
			messagebox.showinfo("Success", "Product added successfully.")
		else:
			messagebox.showerror("Error", "Failed to add product. Check values and barcode uniqueness.")
		return success

	def _edit_product(self, product_id: int, form_data: dict[str, str]) -> bool:
		success = products.update_product(
			product_id,
			form_data["product_name"],
			form_data["category"],
			float(form_data["price"]),
			int(form_data["quantity"]),
			form_data["barcode"],
		)
		if success:
			self.refresh_table()
			messagebox.showinfo("Success", "Product updated successfully.")
		else:
			messagebox.showerror("Error", "Failed to update product.")
		return success

	def _delete_selected_product(self) -> None:
		product_id = self._selected_product_id()
		if product_id is None:
			messagebox.showwarning("No Selection", "Please select a product to delete.")
			return

		if not themed_confirm_dialog(
			self.window,
			"Confirm Delete",
			"Are you sure you want to delete this product?",
		):
			return

		success = products.delete_product(product_id)
		if success:
			self.refresh_table()
			messagebox.showinfo("Deleted", "Product deleted successfully.")
		else:
			messagebox.showerror("Error", "Failed to delete product.")

	def run(self) -> None:
		if self._owns_root:
			self.window.mainloop()


class ProductFormDialog:
	"""Modal dialog for add/edit product forms."""

	def __init__(
		self,
		master: tk.Misc,
		title: str,
		on_submit,
		initial_data: dict[str, str] | None = None,
	) -> None:
		self.on_submit = on_submit
		self.window = tk.Toplevel(master)
		self.window.title(title)
		self.window.geometry("420x320")
		self.window.resizable(False, False)
		self.window.transient(master)
		self.window.grab_set()

		self.fields: dict[str, tk.StringVar] = {
			"product_name": tk.StringVar(value=(initial_data or {}).get("product_name", "")),
			"category": tk.StringVar(value=(initial_data or {}).get("category", "")),
			"price": tk.StringVar(value=str((initial_data or {}).get("price", ""))),
			"quantity": tk.StringVar(value=str((initial_data or {}).get("quantity", ""))),
			"barcode": tk.StringVar(value=(initial_data or {}).get("barcode", "")),
		}

		self._build_form()

	def _build_form(self) -> None:
		frame = ttk.Frame(self.window, padding=12)
		frame.pack(expand=True, fill="both")

		labels = [
			("Product Name", "product_name"),
			("Category", "category"),
			("Price", "price"),
			("Quantity", "quantity"),
			("Barcode", "barcode"),
		]

		for row_index, (label_text, key) in enumerate(labels):
			ttk.Label(frame, text=label_text).grid(row=row_index, column=0, sticky="w", pady=6)
			ttk.Entry(frame, textvariable=self.fields[key], width=30).grid(row=row_index, column=1, sticky="ew", pady=6)

		frame.columnconfigure(1, weight=1)

		buttons = ttk.Frame(frame)
		buttons.grid(row=len(labels), column=0, columnspan=2, pady=(14, 0), sticky="e")
		ttk.Button(buttons, text="Cancel", command=self.window.destroy).pack(side="right")
		ttk.Button(buttons, text="Save", command=self._submit).pack(side="right", padx=(0, 8))

	def _submit(self) -> None:
		data = {key: var.get().strip() for key, var in self.fields.items()}

		if not is_non_empty(data["product_name"]):
			messagebox.showwarning("Validation", "Product name is required.")
			return

		if not is_non_empty(data["price"]) or not is_non_empty(data["quantity"]):
			messagebox.showwarning("Validation", "Price and quantity are required.")
			return

		if not is_valid_price(data["price"]) or not is_valid_quantity(data["quantity"]):
			messagebox.showwarning("Validation", "Price must be a number and quantity must be a non-negative integer.")
			return

		success = self.on_submit(data)
		if success:
			self.window.destroy()
