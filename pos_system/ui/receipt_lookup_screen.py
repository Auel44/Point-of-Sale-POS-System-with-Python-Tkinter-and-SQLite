"""Receipt lookup screen for opening a previous sale receipt by sale id."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from modules.sales import get_sale_by_id
from ui.receipt_preview import ReceiptPreview
from ui.theme import apply_modern_theme


class ReceiptLookupScreen(tk.Toplevel):
	"""Simple utility screen to fetch and open receipts by sale number."""

	ALLOWED_ROLES = {"Admin", "Manager", "Cashier"}

	def __init__(self, parent: tk.Misc, user: dict[str, Any]) -> None:
		super().__init__(parent)
		role = str(user.get("role", ""))
		if role not in self.ALLOWED_ROLES:
			messagebox.showerror("Access Denied", "You are not authorized to view receipts.", parent=self)
			self.destroy()
			return

		self.title("POS - Receipts")
		self.geometry("460x240")
		self.resizable(False, False)
		self.grab_set()
		apply_modern_theme(self)

		self._sale_id_var = tk.StringVar()
		self._error_var = tk.StringVar()
		self._build_ui()

	def _build_ui(self) -> None:
		container = ttk.Frame(self, padding=(14, 12), style="Card.TFrame")
		container.pack(expand=True, fill="both")

		ttk.Label(container, text="Receipt Lookup", style="SectionTitle.TLabel").pack(anchor="w")
		ttk.Label(
			container,
			text="Enter an existing sale ID to open the generated receipt.",
			style="SectionSub.TLabel",
		).pack(anchor="w", pady=(2, 12))

		row = ttk.Frame(container, style="Card.TFrame")
		row.pack(fill="x")
		ttk.Label(row, text="Sale ID:", style="SectionSub.TLabel").pack(side="left", padx=(0, 8))
		entry = ttk.Entry(row, textvariable=self._sale_id_var, width=18)
		entry.pack(side="left")
		entry.bind("<Return>", lambda _e: self._open_receipt())
		entry.focus_set()

		ttk.Button(
			container,
			text="Open Receipt",
			command=self._open_receipt,
			style="Primary.TButton",
		).pack(anchor="e", pady=(12, 0))

		ttk.Label(container, textvariable=self._error_var, foreground="red").pack(anchor="w", pady=(10, 0))

	def _open_receipt(self) -> None:
		self._error_var.set("")
		raw = self._sale_id_var.get().strip()
		if not raw or not raw.isdigit():
			self._error_var.set("Enter a valid numeric sale ID.")
			return

		sale_id = int(raw)
		sale = get_sale_by_id(sale_id)
		if sale is None:
			self._error_var.set(f"Sale #{sale_id} was not found.")
			return

		ReceiptPreview(self, sale_id=sale_id)
