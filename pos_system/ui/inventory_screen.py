"""Inventory management UI — current stock levels and adjustment history."""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from modules.auth import CURRENT_USER
from modules.inventory import adjust_stock, get_inventory_log
from modules.products import get_all_products
from ui.theme import apply_modern_theme

LOW_STOCK_THRESHOLD = 5


class InventoryScreen(tk.Toplevel):
	"""Shows stock levels for all products and a full adjustment log."""
	ALLOWED_ROLES = {"Admin", "Manager"}

	def __init__(self, parent: tk.Tk, user: dict[str, Any] | None = None) -> None:
		super().__init__(parent)
		active_user = user or CURRENT_USER or {}
		role = str(active_user.get("role", ""))
		if role not in self.ALLOWED_ROLES:
			messagebox.showerror(
				"Access Denied",
				"Only Manager and Admin users can access Inventory.",
				parent=self,
			)
			self.destroy()
			return

		self.title("Inventory Management")
		self.geometry("880x540")
		self.minsize(700, 420)
		self.grab_set()
		apply_modern_theme(self)

		self._build_ui()
		self._load_stock()
		self._load_log()

	# ------------------------------------------------------------------
	# Layout
	# ------------------------------------------------------------------

	def _build_ui(self) -> None:
		title_bar = ttk.Frame(self, padding=(16, 10), style="Card.TFrame")
		title_bar.pack(fill="x")

		title_wrap = ttk.Frame(title_bar, style="Card.TFrame")
		title_wrap.pack(side="left")
		ttk.Label(title_wrap, text="Inventory Management", style="SectionTitle.TLabel").pack(anchor="w")
		ttk.Label(
			title_wrap,
			text="Track stock levels and adjustments in real time.",
			style="SectionSub.TLabel",
		).pack(anchor="w")

		self._low_badge = ttk.Label(title_bar, text="Low Stock: 0", style="InfoBadge.TLabel")
		self._low_badge.pack(side="right", padx=(8, 0))

		ttk.Button(title_bar, text="Refresh", command=self._refresh).pack(
			side="right", padx=(0, 0)
		)
		ttk.Button(
			title_bar,
			text="Adjust Stock",
			command=self._open_adjust_dialog,
			style="Primary.TButton",
		).pack(
			side="right", padx=(0, 6)
		)

		notebook = ttk.Notebook(self, padding=(10, 4))
		notebook.pack(expand=True, fill="both")

		stock_tab = ttk.Frame(notebook, padding=6)
		notebook.add(stock_tab, text="Current Stock")
		self._build_stock_tab(stock_tab)

		log_tab = ttk.Frame(notebook, padding=6)
		notebook.add(log_tab, text="Adjustment Log")
		self._build_log_tab(log_tab)

	def _build_stock_tab(self, parent: ttk.Frame) -> None:
		tree_frame = ttk.Frame(parent)
		tree_frame.pack(expand=True, fill="both")

		cols = ("id", "name", "category", "barcode", "price", "quantity")
		self.stock_tree = ttk.Treeview(
			tree_frame, columns=cols, show="headings", selectmode="browse"
		)

		headers = {
			"id": ("ID", 50),
			"name": ("Product Name", 220),
			"category": ("Category", 120),
			"barcode": ("Barcode", 120),
			"price": ("Price (GH₵)", 100),
			"quantity": ("Qty", 70),
		}
		for col, (label, width) in headers.items():
			self.stock_tree.heading(col, text=label)
			anchor = "center" if col in ("id", "price", "quantity") else "w"
			self.stock_tree.column(col, width=width, anchor=anchor)

		# Low-stock rows are displayed in red bold
		self.stock_tree.tag_configure(
			"low_stock", foreground="#cc0000", font=("Segoe UI", 9, "bold")
		)

		vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.stock_tree.yview)
		self.stock_tree.configure(yscrollcommand=vsb.set)
		self.stock_tree.pack(side="left", expand=True, fill="both")
		vsb.pack(side="right", fill="y")

		self.stock_status = ttk.Label(parent, text="", style="InfoBadge.TLabel")
		self.stock_status.pack(anchor="w", pady=(4, 0))

	def _build_log_tab(self, parent: ttk.Frame) -> None:
		tree_frame = ttk.Frame(parent)
		tree_frame.pack(expand=True, fill="both")

		cols = ("log_id", "product", "change", "reason", "date")
		self.log_tree = ttk.Treeview(
			tree_frame, columns=cols, show="headings", selectmode="browse"
		)

		headers = {
			"log_id": ("Log #", 60),
			"product": ("Product", 220),
			"change": ("Change", 80),
			"reason": ("Reason", 230),
			"date": ("Date / Time", 160),
		}
		for col, (label, width) in headers.items():
			self.log_tree.heading(col, text=label)
			anchor = "center" if col in ("log_id", "change") else "w"
			self.log_tree.column(col, width=width, anchor=anchor)

		self.log_tree.tag_configure("positive", foreground="#007700")
		self.log_tree.tag_configure("negative", foreground="#cc0000")

		vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.log_tree.yview)
		self.log_tree.configure(yscrollcommand=vsb.set)
		self.log_tree.pack(side="left", expand=True, fill="both")
		vsb.pack(side="right", fill="y")

	# ------------------------------------------------------------------
	# Data loading
	# ------------------------------------------------------------------

	def _load_stock(self) -> None:
		for row in self.stock_tree.get_children():
			self.stock_tree.delete(row)

		products = get_all_products()
		low_count = 0
		for p in products:
			qty = p["quantity"]
			is_low = qty <= LOW_STOCK_THRESHOLD
			if is_low:
				low_count += 1
			self.stock_tree.insert(
				"",
				"end",
				values=(
					p["product_id"],
					p["product_name"],
					p["category"],
					p.get("barcode", ""),
					f"{p['price']:.2f}",
					qty,
				),
				tags=("low_stock",) if is_low else (),
			)

		status = f"{len(products)} product(s) total"
		if low_count:
			status += f"  •  {low_count} low-stock item(s) highlighted"
		self.stock_status.config(text=status)
		self._low_badge.config(
			text=f"Low Stock: {low_count}",
			style="WarningBadge.TLabel" if low_count else "SuccessBadge.TLabel",
		)

	def _load_log(self) -> None:
		for row in self.log_tree.get_children():
			self.log_tree.delete(row)

		for entry in get_inventory_log():
			change = entry["change_amount"]
			tag = "positive" if change > 0 else "negative"
			display_change = f"+{change}" if change > 0 else str(change)
			self.log_tree.insert(
				"",
				"end",
				values=(
					entry["inventory_id"],
					entry["product_name"],
					display_change,
					entry["reason"],
					entry["date"],
				),
				tags=(tag,),
			)

	def _refresh(self) -> None:
		self._load_stock()
		self._load_log()

	# ------------------------------------------------------------------
	# Adjust Stock dialog
	# ------------------------------------------------------------------

	def _open_adjust_dialog(self) -> None:
		AdjustStockDialog(self, on_save=self._refresh)


class AdjustStockDialog(tk.Toplevel):
	"""Modal dialog for adjusting product stock quantity."""

	def __init__(self, parent: tk.Toplevel, on_save) -> None:
		super().__init__(parent)
		self.title("Adjust Stock")
		self.geometry("440x270")
		self.resizable(False, False)
		self.grab_set()

		self._on_save = on_save
		self._products = get_all_products()
		self._build_form()

	def _build_form(self) -> None:
		frame = ttk.Frame(self, padding=(20, 16))
		frame.pack(expand=True, fill="both")
		frame.columnconfigure(1, weight=1)

		ttk.Label(frame, text="Adjust Stock", font=("Segoe UI", 12, "bold")).grid(
			row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
		)

		# Product selector
		ttk.Label(frame, text="Product:").grid(row=1, column=0, sticky="w", pady=4)
		product_names = [
			f"{p['product_name']} (ID:{p['product_id']})" for p in self._products
		]
		self._product_var = tk.StringVar()
		combo = ttk.Combobox(
			frame,
			textvariable=self._product_var,
			values=product_names,
			state="readonly",
			width=30,
		)
		combo.grid(row=1, column=1, sticky="ew", padx=(8, 0))
		if product_names:
			combo.current(0)

		# Change amount
		ttk.Label(frame, text="Change Amount:").grid(row=2, column=0, sticky="w", pady=4)
		self._change_var = tk.StringVar()
		ttk.Entry(frame, textvariable=self._change_var, width=32).grid(
			row=2, column=1, sticky="ew", padx=(8, 0)
		)
		ttk.Label(
			frame,
			text="  Positive to add stock, negative to remove.",
			font=("Segoe UI", 8),
		).grid(row=3, column=1, sticky="w", padx=(8, 0))

		# Reason
		ttk.Label(frame, text="Reason:").grid(row=4, column=0, sticky="w", pady=4)
		self._reason_var = tk.StringVar()
		ttk.Entry(frame, textvariable=self._reason_var, width=32).grid(
			row=4, column=1, sticky="ew", padx=(8, 0)
		)

		# Error label
		self._error_var = tk.StringVar()
		ttk.Label(
			frame, textvariable=self._error_var, foreground="red", font=("Segoe UI", 9)
		).grid(row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

		# Buttons
		btn_frame = ttk.Frame(frame)
		btn_frame.grid(row=6, column=0, columnspan=2, sticky="e", pady=(12, 0))
		ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")
		ttk.Button(btn_frame, text="Save", command=self._save).pack(
			side="right", padx=(0, 6)
		)

	def _save(self) -> None:
		self._error_var.set("")

		if not self._products:
			self._error_var.set("No products available.")
			return

		selection = self._product_var.get()
		try:
			product_id = int(selection.split("ID:")[1].rstrip(")"))
		except (IndexError, ValueError):
			self._error_var.set("Please select a product.")
			return

		try:
			change = int(self._change_var.get().strip())
		except ValueError:
			self._error_var.set("Change amount must be a whole number (e.g. 10 or -5).")
			return

		if change == 0:
			self._error_var.set("Change amount cannot be zero.")
			return

		reason = self._reason_var.get().strip()
		if not reason:
			self._error_var.set("Reason is required.")
			return

		success = adjust_stock(product_id, change, reason)
		if success:
			self._on_save()
			self.destroy()
		else:
			self._error_var.set("Adjustment failed — stock cannot go below zero.")
