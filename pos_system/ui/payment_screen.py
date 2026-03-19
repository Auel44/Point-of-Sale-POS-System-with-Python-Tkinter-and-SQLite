"""Payment screen — method selection, cash change calculation, and confirm."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from modules.payments import process_payment
from modules.sales import create_sale
from ui.theme import apply_modern_theme, themed_confirm_dialog
from utils.validators import is_valid_price

PAYMENT_METHODS = ["Cash", "Mobile Money", "Card"]


class PaymentScreen(tk.Toplevel):
	"""Handles payment entry after cart checkout.

	Receives the cart snapshot and totals from SalesScreen, calls
	create_sale + process_payment on confirm, then shows a receipt summary.
	"""
	ALLOWED_ROLES = {"Admin", "Manager", "Cashier"}

	def __init__(
		self,
		parent: tk.Misc,
		user: dict[str, Any],
		cart: list[dict[str, Any]],
		discount: float,
		tax: float,
		grand_total: float,
		customer_id: int | None = None,
		on_success: Any | None = None,
	) -> None:
		super().__init__(parent)
		role = str(user.get("role", ""))
		if role not in self.ALLOWED_ROLES:
			messagebox.showerror("Access Denied", "You are not authorized to process payments.", parent=self)
			self.destroy()
			return

		self.title("Payment")
		self.geometry("520x560")
		self.minsize(500, 520)
		self.resizable(True, True)
		self.grab_set()
		apply_modern_theme(self)

		self._user = user
		self._cart = cart
		self._discount = discount
		self._tax = tax
		self._grand_total = grand_total
		self._customer_id = customer_id
		self._on_success = on_success

		self._build_ui()

	# ------------------------------------------------------------------
	# Layout
	# ------------------------------------------------------------------

	def _build_ui(self) -> None:
		frame = ttk.Frame(self, padding=(14, 12), style="Card.TFrame")
		frame.pack(expand=True, fill="both")
		frame.columnconfigure(1, weight=1)

		ttk.Label(frame, text="Payment", style="SectionTitle.TLabel").grid(
			row=0, column=0, sticky="w", pady=(0, 4)
		)
		self._pay_state_label = ttk.Label(frame, text="Awaiting Confirmation", style="InfoBadge.TLabel")
		self._pay_state_label.grid(row=0, column=1, sticky="e", pady=(0, 4))
		ttk.Label(
			frame,
			text="Review totals and capture payment.",
			style="SectionSub.TLabel",
		).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))

		# summary card
		summary = ttk.Frame(frame, padding=(12, 10), style="Card.TFrame")
		summary.grid(row=2, column=0, columnspan=2, sticky="ew")
		summary.columnconfigure(1, weight=1)

		row = 0
		ttk.Label(summary, text="Order Summary", style="SectionTitle.TLabel").grid(
			row=row, column=0, sticky="w", pady=(0, 6)
		)

		# ── Order summary ────────────────────────────────────────────
		row += 1
		ttk.Label(summary, text="Items:", style="SectionSub.TLabel").grid(row=row, column=0, sticky="w", pady=2)
		ttk.Label(summary, text=str(sum(i["quantity"] for i in self._cart))).grid(
			row=row, column=1, sticky="e"
		)

		row += 1
		ttk.Label(summary, text="Subtotal:", style="SectionSub.TLabel").grid(row=row, column=0, sticky="w", pady=2)
		subtotal = sum(i["price"] * i["quantity"] for i in self._cart)
		ttk.Label(summary, text=f"GH₵ {subtotal:.2f}").grid(row=row, column=1, sticky="e")

		row += 1
		ttk.Label(summary, text="Discount:", style="SectionSub.TLabel").grid(row=row, column=0, sticky="w", pady=2)
		ttk.Label(summary, text=f"- GH₵ {self._discount:.2f}").grid(
			row=row, column=1, sticky="e"
		)

		row += 1
		ttk.Label(summary, text="Tax:", style="SectionSub.TLabel").grid(row=row, column=0, sticky="w", pady=2)
		ttk.Label(summary, text=f"GH₵ {self._tax:.2f}").grid(row=row, column=1, sticky="e")

		ttk.Separator(summary, orient="horizontal").grid(
			row=row + 1, column=0, columnspan=2, sticky="ew", pady=8
		)

		row += 2
		ttk.Label(summary, text="Grand Total:", font=("Segoe UI", 12, "bold")).grid(
			row=row, column=0, sticky="w", pady=2
		)
		ttk.Label(
			summary, text=f"GH₵ {self._grand_total:.2f}", font=("Segoe UI", 12, "bold")
		).grid(row=row, column=1, sticky="e")

		# ── Payment method ───────────────────────────────────────────
		method_card = ttk.Frame(frame, padding=(12, 10), style="Card.TFrame")
		method_card.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
		method_card.columnconfigure(1, weight=1)

		row = 0
		ttk.Label(method_card, text="Payment Method", style="SectionTitle.TLabel").grid(
			row=row, column=0, sticky="w", pady=(0, 8)
		)

		row += 1
		ttk.Label(method_card, text="Type:", style="SectionSub.TLabel").grid(
			row=row, column=0, sticky="w", pady=4
		)
		self._method_var = tk.StringVar(value=PAYMENT_METHODS[0])
		method_combo = ttk.Combobox(
			method_card,
			textvariable=self._method_var,
			values=PAYMENT_METHODS,
			state="readonly",
			width=18,
		)
		method_combo.grid(row=row, column=1, sticky="e")
		method_combo.bind("<<ComboboxSelected>>", self._on_method_changed)

		# ── Amount tendered (Cash only) ──────────────────────────────
		row += 1
		self._tendered_label = ttk.Label(method_card, text="Amount Tendered (GH₵):", style="SectionSub.TLabel")
		self._tendered_label.grid(row=row, column=0, sticky="w", pady=4)
		self._tendered_var = tk.StringVar()
		self._tendered_entry = ttk.Entry(
			method_card, textvariable=self._tendered_var, width=20, justify="right"
		)
		self._tendered_entry.grid(row=row, column=1, sticky="e")
		self._tendered_var.trace_add("write", self._on_tendered_changed)

		row += 1
		self._change_label = ttk.Label(method_card, text="Change:", style="SectionSub.TLabel")
		self._change_label.grid(row=row, column=0, sticky="w")
		self._change_value_lbl = ttk.Label(method_card, text="GH₵ 0.00", style="InfoBadge.TLabel")
		self._change_value_lbl.grid(row=row, column=1, sticky="e")

		# ── Error label ──────────────────────────────────────────────
		row = 4
		self._error_var = tk.StringVar()
		ttk.Label(
			frame, textvariable=self._error_var, foreground="red", font=("Segoe UI", 9),
			wraplength=380,
		).grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))

		# ── Buttons ──────────────────────────────────────────────────
		row += 1
		btn_frame = ttk.Frame(frame)
		btn_frame.grid(row=row, column=0, columnspan=2, sticky="e", pady=(12, 0))
		ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")
		ttk.Button(
			btn_frame, text="Confirm Payment", command=self._confirm, style="Primary.TButton"
		).pack(side="right", padx=(0, 8))

	# ------------------------------------------------------------------
	# Interaction handlers
	# ------------------------------------------------------------------

	def _on_method_changed(self, _event: Any = None) -> None:
		is_cash = self._method_var.get() == "Cash"
		state = "normal" if is_cash else "disabled"
		self._tendered_label.config(foreground="" if is_cash else "gray")
		self._tendered_entry.config(state=state)
		self._change_label.config(foreground="" if is_cash else "gray")
		self._change_value_lbl.config(foreground="" if is_cash else "gray")
		self._error_var.set("")
		self._pay_state_label.config(text="Cash" if is_cash else "Digital Payment")
		if not is_cash:
			self._change_value_lbl.config(text="N/A")

	def _on_tendered_changed(self, *_args: Any) -> None:
		if is_valid_price(self._tendered_var.get()):
			tendered = float(self._tendered_var.get())
			change = tendered - self._grand_total
			self._change_value_lbl.config(
				text=f"GH₵ {change:.2f}",
				style="SuccessBadge.TLabel" if change >= 0 else "WarningBadge.TLabel",
			)
		else:
			self._change_value_lbl.config(text="GH₵ 0.00", style="InfoBadge.TLabel")

	# ------------------------------------------------------------------
	# Confirm payment
	# ------------------------------------------------------------------

	def _confirm(self) -> None:
		self._error_var.set("")
		method = self._method_var.get()

		# Validate cash tendered
		if method == "Cash":
			if not is_valid_price(self._tendered_var.get()):
				self._error_var.set("Enter a valid amount tendered.")
				return
			try:
				tendered = float(self._tendered_var.get())
			except ValueError:
				self._error_var.set("Enter a valid amount tendered.")
				return
			if tendered < self._grand_total:
				self._error_var.set(
					f"Amount tendered (GH₵ {tendered:.2f}) is less than "
					f"the total (GH₵ {self._grand_total:.2f})."
				)
				return
		else:
			tendered = self._grand_total  # Non-cash: exact amount

		if not themed_confirm_dialog(
			self,
			"Confirm Payment",
			f"Proceed with payment of GH₵ {self._grand_total:.2f} via {method}?",
		):
			return

		try:
			# Persist sale
			sale_id = create_sale(
				user_id=self._user["user_id"],
				customer_id=self._customer_id,
				items=self._cart,
				payment_method=method,
				discount=self._discount,
			)
			# Persist payment
			change = process_payment(sale_id, tendered, method)
		except Exception as exc:
			self._error_var.set(f"Payment failed: {exc}")
			return

		if callable(self._on_success):
			try:
				self._on_success(sale_id)
			except Exception:
				pass

		self._show_receipt(sale_id, method, tendered, change)

	# ------------------------------------------------------------------
	# Receipt summary
	# ------------------------------------------------------------------

	def _show_receipt(
		self, sale_id: int, method: str, tendered: float, change: float
	) -> None:
		"""Display a simple on-screen receipt summary after payment."""
		self.destroy()

		# Import deferred to avoid a circular import with future receipt module
		from ui.receipt_preview import ReceiptPreview

		ReceiptPreview(
			self.master,
			sale_id=sale_id,
			cart=self._cart,
			discount=self._discount,
			tax=self._tax,
			grand_total=self._grand_total,
			method=method,
			tendered=tendered,
			change=change,
		)
