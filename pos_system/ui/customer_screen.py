"""Customer management UI — search, add, edit, history, and loyalty points."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from modules.auth import CURRENT_USER
from modules.customers import (
	add_customer,
	get_all_customers,
	get_purchase_history,
	search_customers,
	update_customer,
)
from ui.theme import apply_modern_theme
from utils.validators import is_non_empty, is_valid_email


class CustomerScreen(tk.Toplevel):
	"""Searchable table of customers with add/edit and history views."""
	ALLOWED_ROLES = {"Admin", "Manager"}

	def __init__(self, parent: tk.Tk, user: dict[str, Any] | None = None) -> None:
		super().__init__(parent)
		active_user = user or CURRENT_USER or {}
		role = str(active_user.get("role", ""))
		if role not in self.ALLOWED_ROLES:
			messagebox.showerror(
				"Access Denied",
				"Only Manager and Admin users can access Customers.",
				parent=self,
			)
			self.destroy()
			return

		self.title("Customer Management")
		self.geometry("860x500")
		self.minsize(680, 380)
		self.grab_set()
		apply_modern_theme(self)

		self._build_ui()
		self._load_customers()

	# ------------------------------------------------------------------
	# Layout
	# ------------------------------------------------------------------

	def _build_ui(self) -> None:
		container = ttk.Frame(self, padding=12)
		container.pack(expand=True, fill="both")

		# Header
		header = ttk.Frame(container, style="Card.TFrame", padding=(12, 10))
		header.pack(fill="x", pady=(0, 8))
		title_wrap = ttk.Frame(header, style="Card.TFrame")
		title_wrap.pack(side="left")
		ttk.Label(title_wrap, text="Customer Management", style="SectionTitle.TLabel").pack(anchor="w")
		ttk.Label(
			title_wrap,
			text="Manage contacts, loyalty points, and purchase history.",
			style="SectionSub.TLabel",
		).pack(anchor="w")
		self._count_badge = ttk.Label(header, text="0 customers", style="InfoBadge.TLabel")
		self._count_badge.pack(side="right")

		# Search bar
		search_frame = ttk.Frame(container, style="Card.TFrame", padding=(12, 10))
		search_frame.pack(fill="x", pady=(0, 8))
		ttk.Label(search_frame, text="Search:", style="SectionSub.TLabel").pack(side="left", padx=(0, 6))
		self._search_var = tk.StringVar()
		search_entry = ttk.Entry(search_frame, textvariable=self._search_var, width=36)
		search_entry.pack(side="left")
		search_entry.bind("<KeyRelease>", lambda _e: self._load_customers())
		ttk.Button(search_frame, text="Clear", command=self._clear_search).pack(
			side="left", padx=(6, 0)
		)

		# Action buttons
		btn_bar = ttk.Frame(container, style="Card.TFrame", padding=(12, 8))
		btn_bar.pack(fill="x", pady=(0, 8))
		ttk.Button(btn_bar, text="Add Customer", command=self._open_add_dialog, style="Primary.TButton").pack(
			side="left", padx=(0, 6)
		)
		ttk.Button(btn_bar, text="Edit Customer", command=self._open_edit_dialog).pack(
			side="left", padx=(0, 6)
		)
		ttk.Button(btn_bar, text="View History", command=self._view_history).pack(
			side="left"
		)

		# Table
		table_frame = ttk.Frame(container, style="Card.TFrame", padding=(8, 8))
		table_frame.pack(expand=True, fill="both")

		cols = ("customer_id", "name", "phone", "email", "address", "loyalty_points")
		self.table = ttk.Treeview(
			table_frame, columns=cols, show="headings", selectmode="browse", height=14
		)
		headers = {
			"customer_id": ("ID", 50),
			"name": ("Name", 200),
			"phone": ("Phone", 120),
			"email": ("Email", 180),
			"address": ("Address", 160),
			"loyalty_points": ("Points", 60),
		}
		for col, (label, width) in headers.items():
			self.table.heading(col, text=label)
			anchor = "center" if col in ("customer_id", "loyalty_points") else "w"
			self.table.column(col, width=width, anchor=anchor)

		vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
		self.table.configure(yscrollcommand=vsb.set)
		self.table.pack(side="left", expand=True, fill="both")
		vsb.pack(side="right", fill="y")
		self.table.bind("<Double-1>", lambda _e: self._open_edit_dialog())

		self._status_var = tk.StringVar()
		ttk.Label(container, textvariable=self._status_var, style="InfoBadge.TLabel").pack(
			anchor="w", pady=(4, 0)
		)

	# ------------------------------------------------------------------
	# Data
	# ------------------------------------------------------------------

	def _load_customers(self) -> None:
		for row in self.table.get_children():
			self.table.delete(row)
		query = self._search_var.get().strip()
		customers = search_customers(query) if query else get_all_customers()
		for c in customers:
			self.table.insert(
				"",
				"end",
				values=(
					c["customer_id"],
					c["name"],
					c["phone"],
					c["email"],
					c["address"],
					c["loyalty_points"],
				),
			)
		self._status_var.set(f"{len(customers)} customer(s)")
		self._count_badge.config(text=f"{len(customers)} customers")

	def _clear_search(self) -> None:
		self._search_var.set("")
		self._load_customers()

	def _selected_customer_id(self) -> int | None:
		selected = self.table.selection()
		if not selected:
			return None
		return int(self.table.item(selected[0])["values"][0])

	# ------------------------------------------------------------------
	# Dialogs
	# ------------------------------------------------------------------

	def _open_add_dialog(self) -> None:
		CustomerFormDialog(self, on_save=self._load_customers)

	def _open_edit_dialog(self) -> None:
		cid = self._selected_customer_id()
		if cid is None:
			messagebox.showinfo("Edit Customer", "Select a customer first.", parent=self)
			return
		row = self.table.item(self.table.selection()[0])["values"]
		existing = {
			"customer_id": row[0],
			"name": row[1],
			"phone": row[2],
			"email": row[3],
			"address": row[4],
		}
		CustomerFormDialog(self, existing=existing, on_save=self._load_customers)

	def _view_history(self) -> None:
		cid = self._selected_customer_id()
		if cid is None:
			messagebox.showinfo("View History", "Select a customer first.", parent=self)
			return
		row = self.table.item(self.table.selection()[0])["values"]
		PurchaseHistoryDialog(self, customer_id=cid, customer_name=str(row[1]))


# -----------------------------------------------------------------------
# Customer form dialog (add + edit)
# -----------------------------------------------------------------------

class CustomerFormDialog(tk.Toplevel):
	"""Modal form for creating or updating a customer record."""

	FIELDS = [
		("Name *", "name"),
		("Phone", "phone"),
		("Email", "email"),
		("Address", "address"),
	]

	def __init__(
		self,
		parent: tk.Toplevel,
		existing: dict[str, Any] | None = None,
		on_save: Any = None,
	) -> None:
		super().__init__(parent)
		self._existing = existing
		self._on_save = on_save
		self.title("Edit Customer" if existing else "Add Customer")
		self.geometry("420x280")
		self.resizable(False, False)
		self.grab_set()
		self._build_form()

	def _build_form(self) -> None:
		frame = ttk.Frame(self, padding=(20, 16))
		frame.pack(expand=True, fill="both")
		frame.columnconfigure(1, weight=1)

		title = "Edit Customer" if self._existing else "Add Customer"
		ttk.Label(frame, text=title, font=("Segoe UI", 12, "bold")).grid(
			row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
		)

		self._vars: dict[str, tk.StringVar] = {}
		for row_idx, (label, key) in enumerate(self.FIELDS, start=1):
			ttk.Label(frame, text=label).grid(row=row_idx, column=0, sticky="w", pady=3)
			var = tk.StringVar(
				value=str(self._existing[key]) if self._existing else ""
			)
			self._vars[key] = var
			ttk.Entry(frame, textvariable=var, width=32).grid(
				row=row_idx, column=1, sticky="ew", padx=(8, 0)
			)

		self._error_var = tk.StringVar()
		ttk.Label(
			frame, textvariable=self._error_var, foreground="red", font=("Segoe UI", 9)
		).grid(row=len(self.FIELDS) + 1, column=0, columnspan=2, sticky="w", pady=(6, 0))

		btn_frame = ttk.Frame(frame)
		btn_frame.grid(
			row=len(self.FIELDS) + 2, column=0, columnspan=2, sticky="e", pady=(10, 0)
		)
		ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")
		ttk.Button(btn_frame, text="Save", command=self._save).pack(
			side="right", padx=(0, 6)
		)

	def _save(self) -> None:
		self._error_var.set("")
		name = self._vars["name"].get().strip()
		if not is_non_empty(name):
			self._error_var.set("Name is required.")
			return

		phone = self._vars["phone"].get().strip()
		email = self._vars["email"].get().strip()
		address = self._vars["address"].get().strip()
		if email and not is_valid_email(email):
			self._error_var.set("Email format is invalid.")
			return

		if self._existing:
			success = update_customer(
				self._existing["customer_id"], name, phone, email, address
			)
			if not success:
				self._error_var.set("Update failed — customer not found.")
				return
		else:
			add_customer(name, phone, email, address)

		if self._on_save:
			self._on_save()
		self.destroy()


# -----------------------------------------------------------------------
# Purchase history dialog
# -----------------------------------------------------------------------

class PurchaseHistoryDialog(tk.Toplevel):
	"""Shows all past purchases for a selected customer."""

	def __init__(
		self, parent: tk.Toplevel, customer_id: int, customer_name: str
	) -> None:
		super().__init__(parent)
		self.title(f"Purchase History — {customer_name}")
		self.geometry("520x360")
		self.resizable(False, False)
		self.grab_set()
		self._build(customer_id, customer_name)

	def _build(self, customer_id: int, customer_name: str) -> None:
		frame = ttk.Frame(self, padding=(16, 12))
		frame.pack(expand=True, fill="both")

		ttk.Label(
			frame,
			text=f"Purchase History: {customer_name}",
			font=("Segoe UI", 12, "bold"),
		).pack(anchor="w", pady=(0, 8))

		cols = ("sale_id", "date", "total_amount", "payment_method")
		tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
		headers = {
			"sale_id": ("Sale #", 70),
			"date": ("Date / Time", 160),
			"total_amount": ("Total (GH₵)", 110),
			"payment_method": ("Method", 110),
		}
		for col, (label, width) in headers.items():
			tree.heading(col, text=label)
			anchor = "center" if col == "sale_id" else (
				"e" if col == "total_amount" else "w"
			)
			tree.column(col, width=width, anchor=anchor)

		vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
		tree.configure(yscrollcommand=vsb.set)
		tree.pack(side="left", expand=True, fill="both")
		vsb.pack(side="right", fill="y")

		history = get_purchase_history(customer_id)
		for sale in history:
			tree.insert(
				"",
				"end",
				values=(
					sale["sale_id"],
					sale["date"],
					f"{sale['total_amount']:.2f}",
					sale["payment_method"],
				),
			)

		if not history:
			ttk.Label(frame, text="No purchase history found.", font=("Segoe UI", 9)).pack(
				anchor="w", pady=4
			)

		ttk.Button(self, text="Close", command=self.destroy).pack(pady=(0, 10))
