"""Dashboard UI with role-based navigation and logout."""

from typing import Any
import tkinter as tk
from tkinter import messagebox, ttk

from modules.auth import logout as auth_logout
from modules.permissions import ROLE_MODULES, can_access_module
from modules.tickets import count_open_tickets
from ui.dashboard_panels import (
	AuditLogsPanel,
	ChangePasswordPanel,
	CustomersPanel,
	InventoryPanel,
	PasswordResetTicketsPanel,
	PaymentsPanel,
	ProductManagementPanel,
	ReceiptsPanel,
	ReportsPanel,
	SalesPanel,
	UserManagementPanel,
)
from ui.theme import apply_modern_theme, themed_confirm_dialog

# Auto-logout after 15 minutes of no interaction
_IDLE_TIMEOUT_MS = 15 * 60 * 1000


class DashboardScreen:
	"""Dashboard shown after successful login."""

	ROLE_MODULES = ROLE_MODULES

	def __init__(self, user: dict[str, Any]) -> None:
		self.user = user
		self.role = str(user.get("role", "Cashier"))

		self.root = tk.Tk()
		self.root.title("POS System - Dashboard")
		self.root.geometry("920x560")
		self.root.minsize(920, 560)
		apply_modern_theme(self.root)

		self._build_layout()
		self._start_idle_timer()

	def _build_layout(self) -> None:
		main = ttk.Frame(self.root)
		main.pack(expand=True, fill="both")

		header = ttk.Frame(main, padding=(18, 14), style="Header.TFrame")
		header.pack(fill="x")
		main_title = ttk.Label(header, text="Operations Dashboard", style="CardTitle.TLabel")
		main_title.pack(side="left")

		account = ttk.Frame(header, style="Header.TFrame")
		account.pack(side="right")
		ttk.Label(account, text=f"{self.user.get('username')}", style="CardSub.TLabel").pack(
			side="left", padx=(0, 8)
		)
		ttk.Label(account, text=self.role, style="RoleBadge.TLabel").pack(side="left")

		body = ttk.Frame(main)
		body.pack(expand=True, fill="both")

		sidebar = ttk.Frame(body, padding=(12, 10), width=230, style="Sidebar.TFrame")
		sidebar.pack(side="left", fill="y")

		nav_label = ttk.Label(sidebar, text="Navigation", style="SidebarHeading.TLabel")
		nav_label.pack(anchor="w", pady=(0, 8))

		self.buttons: dict[str, ttk.Button] = {}
		for module_name in self.ROLE_MODULES.get(self.role, self.ROLE_MODULES["Cashier"]):
			text = module_name
			if module_name == "Password Reset Tickets":
				open_tickets = count_open_tickets()
				if open_tickets > 0:
					text = f"{module_name} ({open_tickets})"

			button = ttk.Button(
				sidebar,
				text=text,
				style="Nav.TButton",
				command=lambda name=module_name: self._open_module(name),
			)
			button.pack(fill="x", pady=3)
			self.buttons[module_name] = button

		logout_button = ttk.Button(sidebar, text="Logout", command=self._logout, style="Danger.TButton")
		logout_button.pack(fill="x", pady=(18, 0))

		content = ttk.Frame(body, padding=(20, 16), style="Card.TFrame")
		content.pack(side="left", expand=True, fill="both")

		self.content_title = ttk.Label(content, text="Welcome", style="CardTitle.TLabel")
		self.content_title.pack(anchor="w")

		self.content_message = ttk.Label(
			content,
			text="Select a module from the left sidebar to continue.",
			style="CardSub.TLabel",
		)
		self.content_message.pack(anchor="w", pady=(10, 0))

		self.content_host = ttk.Frame(content, style="Card.TFrame")
		self.content_host.pack(expand=True, fill="both", pady=(12, 0))

	def _clear_content_host(self) -> None:
		for child in self.content_host.winfo_children():
			child.destroy()

	def _show_inline_notice(self, title: str, message: str) -> None:
		self._clear_content_host()
		wrap = ttk.Frame(self.content_host, style="Card.TFrame", padding=(12, 10))
		wrap.pack(fill="both", expand=True)
		ttk.Label(wrap, text=title, style="SectionTitle.TLabel").pack(anchor="w")
		ttk.Label(wrap, text=message, style="SectionSub.TLabel", wraplength=620).pack(anchor="w", pady=(8, 0))

	def _refresh_ticket_badge(self) -> None:
		button = self.buttons.get("Password Reset Tickets")
		if button is None:
			return
		open_tickets = count_open_tickets()
		label = "Password Reset Tickets"
		if open_tickets > 0:
			label = f"Password Reset Tickets ({open_tickets})"
		button.config(text=label)

	def _set_active_nav(self, module_name: str) -> None:
		for btn in self.buttons.values():
			btn.configure(style="Nav.TButton")
		if module_name in self.buttons:
			self.buttons[module_name].configure(style="NavActive.TButton")

	def _open_module(self, module_name: str) -> None:
		"""Open module screens when available, otherwise show placeholder text."""
		self._refresh_ticket_badge()
		self._set_active_nav(module_name)
		if not can_access_module(self.user, module_name):
			self.content_title.config(text="Access Denied")
			self.content_message.config(text="You do not have permission to open this module.")
			self._show_inline_notice("Permission Required", f"Your role ({self.role}) cannot access {module_name}.")
			return

		if module_name == "Sales":
			self.content_title.config(text="Sales")
			self.content_message.config(text="Manage cart items directly in this dashboard section.")
			self._clear_content_host()
			panel = SalesPanel(self.content_host, user=self.user)
			panel.pack(expand=True, fill="both")
			return

		if module_name == "Payments":
			self.content_title.config(text="Payments")
			self.content_message.config(text="Recent payment transactions are shown below.")
			self._clear_content_host()
			panel = PaymentsPanel(self.content_host, user=self.user)
			panel.pack(expand=True, fill="both")
			return

		if module_name == "Receipts":
			self.content_title.config(text="Receipts")
			self.content_message.config(text="Lookup and preview receipts by sale ID below.")
			self._clear_content_host()
			panel = ReceiptsPanel(self.content_host, user=self.user)
			panel.pack(expand=True, fill="both")
			return

		if module_name == "Product Management":
			self.content_title.config(text="Product Management")
			self.content_message.config(text="Manage products directly in this dashboard section.")
			self._clear_content_host()
			panel = ProductManagementPanel(self.content_host, user=self.user)
			panel.pack(expand=True, fill="both")
			return

		if module_name == "Inventory":
			self.content_title.config(text="Inventory")
			self.content_message.config(text="View stock and apply adjustments below.")
			self._clear_content_host()
			panel = InventoryPanel(self.content_host, user=self.user)
			panel.pack(expand=True, fill="both")
			return

		if module_name == "Customers":
			self.content_title.config(text="Customers")
			self.content_message.config(text="Manage customer records and view history below.")
			self._clear_content_host()
			panel = CustomersPanel(self.content_host)
			panel.pack(expand=True, fill="both")
			return

		if module_name == "Reports":
			self.content_title.config(text="Reports")
			self.content_message.config(text="Run analytics and export CSV directly below.")
			self._clear_content_host()
			panel = ReportsPanel(self.content_host, user=self.user)
			panel.pack(expand=True, fill="both")
			return

		if module_name == "User Management":
			self.content_title.config(text="User Management")
			self.content_message.config(text="Manage user accounts, roles, and passwords below.")
			self._clear_content_host()
			panel = UserManagementPanel(self.content_host, current_user=self.user)
			panel.pack(expand=True, fill="both")
			return

		if module_name == "Change Password":
			self.content_title.config(text="Change Password")
			self.content_message.config(text="Update your account password securely.")
			self._clear_content_host()
			panel = ChangePasswordPanel(self.content_host, current_user=self.user)
			panel.pack(expand=True, fill="both")
			return

		if module_name == "Password Reset Tickets":
			self.content_title.config(text="Password Reset Tickets")
			self.content_message.config(text="Manage and resolve user password reset requests below.")
			self._clear_content_host()
			panel = PasswordResetTicketsPanel(self.content_host, current_user=self.user)
			panel.pack(expand=True, fill="both")
			return

		if module_name == "Audit Logs":
			self.content_title.config(text="Audit Logs")
			self.content_message.config(text="Review security-related events and export logs.")
			self._clear_content_host()
			panel = AuditLogsPanel(self.content_host, current_user=self.user)
			panel.pack(expand=True, fill="both")
			return

		self.content_title.config(text=module_name)
		self.content_message.config(text=f"{module_name} screen will be connected in upcoming phases.")
		self._clear_content_host()

	def _logout(self) -> None:
		"""Terminate session and return to login screen."""
		confirmed = themed_confirm_dialog(
			self.root,
			"Confirm Logout",
			"Are you sure you want to log out?",
		)
		if not confirmed:
			return
		self._do_logout()

	def _do_logout(self) -> None:
		"""Perform the actual logout — called by manual logout and auto-timeout."""
		auth_logout()
		self.root.destroy()
		from ui.login_screen import LoginScreen
		LoginScreen().run()

	# ------------------------------------------------------------------
	# Idle / session timeout
	# ------------------------------------------------------------------

	def _start_idle_timer(self) -> None:
		"""Bind all activity events and kick off the idle logout timer."""
		for event in ("<Motion>", "<KeyPress>", "<ButtonPress>"):
			self.root.bind_all(event, self._reset_idle_timer)
		self._idle_after_id: str | None = None
		self._reset_idle_timer()

	def _reset_idle_timer(self, _event: Any = None) -> None:
		"""Restart the idle logout countdown whenever the user interacts."""
		if self._idle_after_id:
			self.root.after_cancel(self._idle_after_id)
		self._idle_after_id = self.root.after(_IDLE_TIMEOUT_MS, self._auto_logout)

	def _auto_logout(self) -> None:
		"""Force logout immediately when idle timeout expires."""
		try:
			messagebox.showinfo(
				"Session Expired",
				"You have been automatically logged out due to inactivity.",
				parent=self.root,
			)
		except Exception:
			pass
		self._do_logout()

	def run(self) -> None:
		self.root.mainloop()
