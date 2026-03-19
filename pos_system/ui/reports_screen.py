"""Reports and analytics UI."""

from __future__ import annotations

import csv
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from modules.auth import CURRENT_USER
from modules.reports import (
	cashier_report,
	daily_sales_report,
	inventory_report,
	product_performance_report,
	weekly_sales_report,
)
from ui.theme import apply_modern_theme


class ReportsScreen(tk.Toplevel):
	"""View business reports and export visible results as CSV."""
	ALLOWED_ROLES = {"Admin", "Manager"}

	REPORT_TYPES = [
		"Daily Sales",
		"Weekly Sales",
		"Product Performance",
		"Inventory",
		"Cashier",
	]

	def __init__(self, parent: tk.Misc, user: dict[str, Any] | None = None) -> None:
		super().__init__(parent)
		active_user = user or CURRENT_USER or {}
		role = str(active_user.get("role", ""))
		if role not in self.ALLOWED_ROLES:
			messagebox.showerror(
				"Access Denied",
				"Only Manager and Admin users can access Reports.",
				parent=self,
			)
			self.destroy()
			return

		self.title("Reports")
		self.geometry("980x580")
		self.minsize(760, 460)
		self.grab_set()
		apply_modern_theme(self)

		self._rows: list[dict[str, Any]] = []
		self._table_columns: list[str] = []

		self._build_ui()
		self._run_report()

	def _build_ui(self) -> None:
		container = ttk.Frame(self, padding=12)
		container.pack(expand=True, fill="both")

		header = ttk.Frame(container, style="Card.TFrame", padding=(12, 10))
		header.pack(fill="x", pady=(0, 8))
		ttk.Label(header, text="Analytics & Reports", style="SectionTitle.TLabel").pack(side="left")
		ttk.Label(header, text="Live Data", style="SuccessBadge.TLabel").pack(side="right")

		controls = ttk.Frame(container, style="Card.TFrame", padding=(12, 10))
		controls.pack(fill="x", pady=(8, 10))

		ttk.Label(controls, text="Report:").grid(row=0, column=0, sticky="w", padx=(0, 6))
		self._report_var = tk.StringVar(value=self.REPORT_TYPES[0])
		report_combo = ttk.Combobox(
			controls,
			textvariable=self._report_var,
			values=self.REPORT_TYPES,
			state="readonly",
			width=22,
		)
		report_combo.grid(row=0, column=1, sticky="w")
		report_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_report_changed())

		today = datetime.now().strftime("%Y-%m-%d")
		ttk.Label(controls, text="Start Date:").grid(row=0, column=2, sticky="w", padx=(14, 6))
		self._start_var = tk.StringVar(value=today)
		ttk.Entry(controls, textvariable=self._start_var, width=12).grid(row=0, column=3, sticky="w")

		ttk.Label(controls, text="End Date:").grid(row=0, column=4, sticky="w", padx=(14, 6))
		self._end_var = tk.StringVar(value=today)
		ttk.Entry(controls, textvariable=self._end_var, width=12).grid(row=0, column=5, sticky="w")

		ttk.Label(controls, text="Cashier ID:").grid(row=0, column=6, sticky="w", padx=(14, 6))
		self._cashier_var = tk.StringVar(value="1")
		self._cashier_entry = ttk.Entry(controls, textvariable=self._cashier_var, width=8)
		self._cashier_entry.grid(row=0, column=7, sticky="w")

		ttk.Button(controls, text="Run", command=self._run_report, style="Primary.TButton").grid(
			row=0, column=8, padx=(14, 6)
		)
		ttk.Button(controls, text="Export CSV", command=self._export_csv).grid(row=0, column=9)

		# Results table
		table_frame = ttk.Frame(container, style="Card.TFrame", padding=(8, 8))
		table_frame.pack(expand=True, fill="both")

		self.table = ttk.Treeview(table_frame, columns=(), show="headings", selectmode="browse")
		vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
		hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
		self.table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

		self.table.pack(side="left", expand=True, fill="both")
		vsb.pack(side="right", fill="y")
		hsb.pack(side="bottom", fill="x")

		self._status_var = tk.StringVar(value="Ready")
		ttk.Label(container, textvariable=self._status_var, style="InfoBadge.TLabel").pack(
			anchor="w", pady=(5, 0)
		)

		self._on_report_changed()

	def _on_report_changed(self) -> None:
		report = self._report_var.get()
		# Cashier ID is only relevant for Cashier report
		if report == "Cashier":
			self._cashier_entry.config(state="normal")
		else:
			self._cashier_entry.config(state="disabled")

	def _run_report(self) -> None:
		report = self._report_var.get()
		start = self._start_var.get().strip()
		end = self._end_var.get().strip()

		try:
			if report == "Daily Sales":
				data = daily_sales_report(start)
				top = "; ".join(
					f"{p['product_name']}({p['units_sold']})" for p in data["top_products"]
				) or "-"
				rows = [
					{
						"date": data["date"],
						"total_sales": data["total_sales"],
						"transactions": data["transactions"],
						"top_products": top,
					}
				]

			elif report == "Weekly Sales":
				rows = weekly_sales_report(start)

			elif report == "Product Performance":
				rows = product_performance_report()

			elif report == "Inventory":
				rows = inventory_report()

			elif report == "Cashier":
				cashier_id = int(self._cashier_var.get().strip())
				data = cashier_report(cashier_id, start, end)
				rows = [
					{
						"cashier_id": data["user_id"],
						"username": data["username"],
						"role": data["role"],
						"start": data["start"],
						"end": data["end"],
						"total_sales": data["total_sales"],
						"transactions": data["transactions"],
					}
				]

			else:
				rows = []

		except Exception as exc:
			messagebox.showerror("Report Error", str(exc), parent=self)
			return

		self._render_rows(rows)

	def _render_rows(self, rows: list[dict[str, Any]]) -> None:
		# Clear current table
		for item in self.table.get_children():
			self.table.delete(item)

		if not rows:
			self.table.configure(columns=())
			self._table_columns = []
			self._rows = []
			self._status_var.set("No data found")
			return

		columns = list(rows[0].keys())
		self.table.configure(columns=columns)
		self._table_columns = columns
		self._rows = rows

		for col in columns:
			self.table.heading(col, text=col.replace("_", " ").title())
			self.table.column(col, width=140, anchor="w")

		for row in rows:
			self.table.insert("", "end", values=[row.get(col, "") for col in columns])

		self._status_var.set(f"{len(rows)} row(s) displayed")

	def _export_csv(self) -> None:
		if not self._rows or not self._table_columns:
			messagebox.showinfo("Export", "Run a report first.", parent=self)
			return

		filename = filedialog.asksaveasfilename(
			parent=self,
			defaultextension=".csv",
			filetypes=[("CSV Files", "*.csv")],
			initialfile="report_export.csv",
		)
		if not filename:
			return

		try:
			with open(filename, "w", newline="", encoding="utf-8") as csv_file:
				writer = csv.DictWriter(csv_file, fieldnames=self._table_columns)
				writer.writeheader()
				writer.writerows(self._rows)
			messagebox.showinfo("Export", f"Report saved to:\n{filename}", parent=self)
		except OSError as exc:
			messagebox.showerror("Export Error", str(exc), parent=self)
