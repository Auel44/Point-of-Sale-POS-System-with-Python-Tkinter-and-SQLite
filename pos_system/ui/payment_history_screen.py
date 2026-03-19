"""Payments screen for browsing recorded payment transactions."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from modules.payments import list_recent_payments
from ui.theme import apply_modern_theme


class PaymentHistoryScreen(tk.Toplevel):
	"""Read-only recent payments list for operations staff."""

	ALLOWED_ROLES = {"Admin", "Manager", "Cashier"}

	def __init__(self, parent: tk.Misc, user: dict[str, Any]) -> None:
		super().__init__(parent)
		role = str(user.get("role", ""))
		if role not in self.ALLOWED_ROLES:
			self.destroy()
			return

		self.title("POS - Payments")
		self.geometry("860x520")
		self.minsize(760, 420)
		self.grab_set()
		apply_modern_theme(self)

		self._build_ui()
		self._load_rows()

	def _build_ui(self) -> None:
		container = ttk.Frame(self, padding=(12, 10), style="Card.TFrame")
		container.pack(expand=True, fill="both")

		header = ttk.Frame(container, style="Card.TFrame")
		header.pack(fill="x", pady=(0, 8))
		ttk.Label(header, text="Payments", style="SectionTitle.TLabel").pack(side="left")
		self._count_lbl = ttk.Label(header, text="0 records", style="InfoBadge.TLabel")
		self._count_lbl.pack(side="right")

		ttk.Label(
			container,
			text="Recent payment transactions recorded in the system.",
			style="SectionSub.TLabel",
		).pack(anchor="w", pady=(0, 10))

		cols = ("payment_id", "sale_id", "date", "method", "sale_total", "amount_paid", "change")
		self._tree = ttk.Treeview(container, columns=cols, show="headings", height=16)
		headers = {
			"payment_id": ("Payment #", 90, "center"),
			"sale_id": ("Sale #", 80, "center"),
			"date": ("Date", 180, "w"),
			"method": ("Method", 130, "w"),
			"sale_total": ("Sale Total", 110, "e"),
			"amount_paid": ("Amount Paid", 120, "e"),
			"change": ("Change", 90, "e"),
		}
		for col, (label, width, anchor) in headers.items():
			self._tree.heading(col, text=label)
			self._tree.column(col, width=width, anchor=anchor)

		vsb = ttk.Scrollbar(container, orient="vertical", command=self._tree.yview)
		self._tree.configure(yscrollcommand=vsb.set)
		self._tree.pack(side="left", expand=True, fill="both")
		vsb.pack(side="right", fill="y")

		btns = ttk.Frame(self, padding=(12, 8), style="Card.TFrame")
		btns.pack(fill="x")
		ttk.Button(btns, text="Refresh", command=self._load_rows, style="Primary.TButton").pack(
			side="right"
		)

	def _load_rows(self) -> None:
		for item in self._tree.get_children():
			self._tree.delete(item)

		rows = list_recent_payments(limit=500)
		for row in rows:
			self._tree.insert(
				"",
				"end",
				values=(
					row["payment_id"],
					row["sale_id"],
					row["date"],
					row["payment_method"],
					f"{float(row['sale_total']):.2f}",
					f"{float(row['amount_paid']):.2f}",
					f"{float(row['change_given']):.2f}",
				),
			)
		self._count_lbl.config(text=f"{len(rows)} records")
