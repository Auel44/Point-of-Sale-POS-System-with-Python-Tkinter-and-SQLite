"""Login screen UI for POS authentication."""

import tkinter as tk
from tkinter import ttk, messagebox

from modules.auth import login as auth_login
from modules.tickets import create_reset_ticket
from ui.dashboard import DashboardScreen
from ui.theme import apply_modern_theme


class ForgotPasswordDialog:
	"""Dialog for submitting a password reset ticket with confirmation."""

	def __init__(self, parent: tk.Widget) -> None:
		self.result = False
		self.username = ""
		
		self.dialog = tk.Toplevel(parent)
		self.dialog.title("Submit Password Reset Ticket")
		self.dialog.geometry("520x320")
		self.dialog.resizable(False, False)
		self.dialog.transient(parent)
		self.dialog.grab_set()
		apply_modern_theme(self.dialog)

		self.main_frame = ttk.Frame(self.dialog)
		self.main_frame.pack(expand=True, fill="both")
		
		self._show_form()

	def _show_form(self) -> None:
		"""Display the password reset request form."""
		for widget in self.main_frame.winfo_children():
			widget.destroy()

		container = ttk.Frame(self.main_frame, padding=24)
		container.pack(expand=True, fill="both")

		ttk.Label(container, text="Password Reset Ticket", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 4))
		ttk.Label(
			container,
			text="Enter your username to open a support ticket. Your access stays on the login page while the request is reviewed.",
			style="CardSub.TLabel",
			wraplength=470,
		).pack(anchor="w", pady=(0, 16))

		form = ttk.Frame(container, padding=12, relief="solid", borderwidth=1)
		form.pack(fill="x", pady=(0, 16))
		form.columnconfigure(1, weight=1)

		ttk.Label(form, text="Username *", style="SectionSub.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))
		self.username_var = tk.StringVar()
		username_entry = ttk.Entry(form, textvariable=self.username_var, width=30)
		username_entry.grid(row=0, column=1, sticky="ew", pady=(0, 6))
		username_entry.focus_set()

		self.error_label = ttk.Label(container, text="", foreground="#c62828", wraplength=470)
		self.error_label.pack(anchor="w", pady=(0, 12))

		button_frame = ttk.Frame(container)
		button_frame.pack(fill="x")

		ttk.Button(button_frame, text="Continue", command=self._submit, style="Primary.TButton").pack(side="left", padx=(0, 8))
		ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side="left")
		username_entry.bind("<Return>", self._submit)

	def _submit(self, _event: tk.Event | None = None) -> str:
		"""Validate and show confirmation before submitting."""
		username = self.username_var.get().strip()

		if not username:
			self.error_label.config(text="Username is required")
			return "break"

		# Show confirmation screen
		self._show_confirmation(username)
		return "break"

	def _show_confirmation(self, username: str) -> None:
		"""Display confirmation screen before submission."""
		for widget in self.main_frame.winfo_children():
			widget.destroy()

		container = ttk.Frame(self.main_frame, padding=24)
		container.pack(expand=True, fill="both")

		ttk.Label(container, text="Confirm Request", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 4))
		ttk.Label(
			container,
			text="A password reset ticket will be created for this username:",
			style="CardSub.TLabel",
		).pack(anchor="w", pady=(0, 16))

		# Confirmation details box
		details_frame = ttk.Frame(container, padding=12, relief="solid", borderwidth=1)
		details_frame.pack(fill="x", pady=(0, 16))

		detail_rows = [
			("Username:", username),
		]
		
		for label, value in detail_rows:
			label_widget = ttk.Label(details_frame, text=label, style="SectionSub.TLabel")
			label_widget.pack(anchor="w")
			value_widget = ttk.Label(details_frame, text=value, foreground="#1976d2", font=("TkDefaultFont", 10))
			value_widget.pack(anchor="w", pady=(0, 8))

		ttk.Label(container, text="An administrator will review this request and provide a temporary password.", style="CardSub.TLabel", foreground="#666", wraplength=470).pack(anchor="w", pady=(0, 16))

		button_frame = ttk.Frame(container)
		button_frame.pack(fill="x")

		def _confirm() -> None:
			"""Submit the confirmed request."""
			if create_reset_ticket(username):
				self.result = True
				self._show_submitted(username)
			else:
				for widget in self.main_frame.winfo_children():
					widget.destroy()
				self._show_form()
				self.username_var.set(username)
				self.error_label.config(text="Username not found. Please check and try again.")

		ttk.Button(button_frame, text="Submit Request", command=_confirm, style="Primary.TButton").pack(side="left", padx=(0, 8))
		ttk.Button(button_frame, text="Back", command=self._show_form).pack(side="left")

	def _show_submitted(self, username: str) -> None:
		"""Show final success state after request submission."""
		for widget in self.main_frame.winfo_children():
			widget.destroy()

		container = ttk.Frame(self.main_frame, padding=24)
		container.pack(expand=True, fill="both")

		ttk.Label(container, text="Request Submitted", style="CardTitle.TLabel").pack(anchor="w", pady=(0, 6))
		ttk.Label(
			container,
			text=f"Your password reset ticket for '{username}' has been submitted successfully.",
			style="CardSub.TLabel",
			wraplength=470,
		).pack(anchor="w", pady=(0, 10))
		ttk.Label(
			container,
			text="An administrator will resolve your ticket and share a temporary password.",
			style="CardSub.TLabel",
			wraplength=470,
		).pack(anchor="w", pady=(0, 18))

		ttk.Button(container, text="Close", command=self.dialog.destroy, style="Primary.TButton").pack(anchor="w")



class LoginScreen:
	"""Render and control the login form."""

	def __init__(self) -> None:
		self.root = tk.Tk()
		self.root.title("POS System - Login")
		self.root.geometry("700x700")
		self.root.resizable(False, False)
		apply_modern_theme(self.root)

		# Main container with gradient-like background
		container = ttk.Frame(self.root, padding=0)
		container.pack(expand=True, fill="both")

		# Header section with branding
		header = ttk.Frame(container, padding=40, style="Header.TFrame")
		header.pack(fill="x")

		title = ttk.Label(header, text="CheckoutOS", style="Title.TLabel")
		title.pack(pady=(0, 6))
		
		subtitle = ttk.Label(
			header,
			text="Retail operations, simplified and secured.",
			style="Subtitle.TLabel",
		)
		subtitle.pack(pady=(0, 0))

		# Main content area
		content = ttk.Frame(container, padding=0)
		content.pack(expand=True, fill="both", padx=40, pady=20)
		content.columnconfigure(0, weight=1)

		# Card container
		card = ttk.Frame(content, padding=32, style="Card.TFrame")
		card.pack(expand=True, fill="both")
		card.columnconfigure(0, weight=1)

		# Sign in heading
		heading = ttk.Frame(card, style="Card.TFrame")
		heading.pack(fill="x", pady=(0, 24))
		
		ttk.Label(heading, text="Sign In", style="CardTitle.TLabel").pack(anchor="w")
		ttk.Label(
			heading, 
			text="Enter your credentials to access the dashboard",
			style="CardSub.TLabel"
		).pack(anchor="w", pady=(4, 0))

		# Form fields
		form = ttk.Frame(card, style="Card.TFrame")
		form.pack(fill="x", pady=(0, 20))
		form.columnconfigure(0, weight=1)

		# Username field
		username_label = ttk.Label(form, text="Username", style="SectionSub.TLabel")
		username_label.pack(anchor="w", pady=(0, 8))
		
		self.username_var = tk.StringVar()
		self.username_entry = ttk.Entry(form, textvariable=self.username_var, width=40)
		self.username_entry.pack(fill="x", pady=(0, 18))

		# Password field with visibility toggle
		password_label = ttk.Label(form, text="Password", style="SectionSub.TLabel")
		password_label.pack(anchor="w", pady=(0, 8))
		
		password_container = ttk.Frame(form, style="Card.TFrame")
		password_container.pack(fill="x", pady=(0, 6))
		password_container.columnconfigure(0, weight=1)
		
		self.password_var = tk.StringVar()
		self.password_entry = ttk.Entry(password_container, textvariable=self.password_var, show="*", width=37)
		self.password_entry.grid(row=0, column=0, sticky="ew")
		
		self.show_password = False
		eye_button = ttk.Button(
			password_container, 
			text="👁", 
			width=3, 
			command=self._toggle_password_visibility
		)
		eye_button.grid(row=0, column=1, padx=(4, 0))

		# Error message area
		self.error_label = ttk.Label(form, text="", foreground="#c62828")
		self.error_label.pack(anchor="w", pady=(0, 16))

		# Primary action button
		login_button = ttk.Button(
			form, 
			text="Sign In", 
			command=self.handle_login, 
			style="Primary.TButton"
		)
		login_button.pack(fill="x", pady=(0, 12))

		# Secondary action - Forgot password (prominent)
		forgot_container = ttk.Frame(form, style="Card.TFrame")
		forgot_container.pack(fill="x", pady=(0, 0))
		forgot_container.columnconfigure(0, weight=1)

		forgot_text = ttk.Label(
			forgot_container,
			text="Don't have access to your account?",
			style="CardSub.TLabel",
		)
		forgot_text.pack(anchor="w", pady=(0, 8))

		forgot_button = ttk.Button(
			forgot_container,
			text="📧 Submit Password Reset Request",
			command=self._show_forgot_password_dialog
		)
		forgot_button.pack(fill="x")

		self.root.bind("<Return>", self.handle_login)
		self.username_entry.focus_set()

	def _toggle_password_visibility(self) -> None:
		"""Toggle password visibility between masked and plain text."""
		self.show_password = not self.show_password
		self.password_entry.config(show="" if self.show_password else "*")

	def _show_forgot_password_dialog(self) -> None:
		"""Open the forgot password dialog."""
		ForgotPasswordDialog(self.root)

	def handle_login(self, _event: tk.Event | None = None) -> None:
		"""Authenticate the user and open the dashboard on success."""
		username = self.username_var.get().strip()
		password = self.password_var.get()

		result = auth_login(username, password)

		if isinstance(result, str) and result.startswith("locked:"):
			minutes = result.split(":")[1]
			self.error_label.config(
				text=f"Account locked. Try again in {minutes} minute(s)."
			)
			return

		if result is None:
			self.error_label.config(text="Invalid username or password")
			return

		self.error_label.config(text="")
		self.root.destroy()
		dashboard = DashboardScreen(result)
		dashboard.run()

	def run(self) -> None:
		self.root.mainloop()


