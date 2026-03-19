"""Shared visual theme for POS Tkinter screens."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def apply_modern_theme(root: tk.Misc) -> None:
	"""Apply a cohesive modern style palette to the active UI root/window."""
	style = ttk.Style(root)
	style.theme_use("clam")

	# Core palette (clean slate + navy accent, avoids default gray UI).
	bg = "#F3F6FA"
	surface = "#FFFFFF"
	ink = "#172033"
	muted = "#5E6B82"
	primary = "#0F5C8A"
	primary_hover = "#0B4A70"
	border = "#D8DEE9"
	danger = "#C64545"
	danger_hover = "#A73434"

	if isinstance(root, (tk.Tk, tk.Toplevel)):
		root.configure(bg=bg)

	style.configure(".", font=("Segoe UI", 10), foreground=ink)
	style.configure("TFrame", background=bg)
	style.configure("Card.TFrame", background=surface, relief="flat", borderwidth=0)
	style.configure("Sidebar.TFrame", background="#1E2A3A")
	style.configure("Header.TFrame", background=surface)

	style.configure("TLabel", background=bg, foreground=ink)
	style.configure("Title.TLabel", background=bg, foreground=ink, font=("Segoe UI Semibold", 20))
	style.configure("Heading.TLabel", background=bg, foreground=ink, font=("Segoe UI Semibold", 13))
	style.configure("SectionTitle.TLabel", background=surface, foreground=ink, font=("Segoe UI Semibold", 12))
	style.configure("SectionSub.TLabel", background=surface, foreground=muted, font=("Segoe UI", 9))
	style.configure(
		"SidebarHeading.TLabel",
		background="#1E2A3A",
		foreground="#E8EEF6",
		font=("Segoe UI Semibold", 12),
	)
	style.configure("Subtitle.TLabel", background=bg, foreground=muted, font=("Segoe UI", 10))
	style.configure("Muted.TLabel", background=bg, foreground=muted, font=("Segoe UI", 9))
	style.configure("CardTitle.TLabel", background=surface, foreground=ink, font=("Segoe UI Semibold", 13))
	style.configure("CardSub.TLabel", background=surface, foreground=muted, font=("Segoe UI", 10))
	style.configure(
		"RoleBadge.TLabel",
		background="#E8F2FB",
		foreground="#0F5C8A",
		font=("Segoe UI Semibold", 9),
		padding=(8, 4),
	)
	style.configure(
		"InfoBadge.TLabel",
		background="#EEF3FA",
		foreground="#2B4460",
		font=("Segoe UI Semibold", 9),
		padding=(8, 4),
	)
	style.configure(
		"SuccessBadge.TLabel",
		background="#E8F7EE",
		foreground="#1C7A45",
		font=("Segoe UI Semibold", 9),
		padding=(8, 4),
	)
	style.configure(
		"WarningBadge.TLabel",
		background="#FFF4E5",
		foreground="#9A5A00",
		font=("Segoe UI Semibold", 9),
		padding=(8, 4),
	)

	style.configure(
		"TEntry",
		padding=(10, 7),
		fieldbackground=surface,
		background=surface,
		bordercolor=border,
		relief="flat",
	)

	style.configure(
		"TButton",
		padding=(12, 8),
		relief="flat",
		borderwidth=0,
		focuscolor="",
	)
	style.configure("Primary.TButton", background=primary, foreground="#FFFFFF")
	style.map(
		"Primary.TButton",
		background=[("active", primary_hover), ("pressed", primary_hover)],
		foreground=[("disabled", "#CFD8E3")],
	)
	style.configure("Danger.TButton", background=danger, foreground="#FFFFFF")
	style.map("Danger.TButton", background=[("active", danger_hover), ("pressed", danger_hover)])

	style.configure(
		"Nav.TButton",
		background="#253448",
		foreground="#E8EEF6",
		padding=(12, 9),
	)
	style.configure(
		"NavActive.TButton",
		background="#3A587C",
		foreground="#FFFFFF",
		padding=(12, 9),
	)
	style.map(
		"Nav.TButton",
		background=[("active", "#30455F"), ("pressed", "#30455F")],
		foreground=[("active", "#FFFFFF")],
	)
	style.map(
		"NavActive.TButton",
		background=[("active", "#43668E"), ("pressed", "#43668E")],
		foreground=[("active", "#FFFFFF")],
	)

	style.configure("TLabelframe", background=bg, bordercolor=border, relief="solid")
	style.configure("TLabelframe.Label", background=bg, foreground=muted)

	style.configure("Treeview", rowheight=30, borderwidth=0, relief="flat")
	style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10), padding=(8, 7))


def themed_confirm_dialog(parent: tk.Misc, title: str, message: str) -> bool:
	"""Show a themed confirmation modal and return True on confirm."""
	result = {"confirmed": False}
	host = parent.winfo_toplevel()
	host.update_idletasks()
	dialog = tk.Toplevel(parent)
	dialog.title(title)
	dlg_w = 460
	dlg_h = 240
	host_w = max(1, host.winfo_width())
	host_h = max(1, host.winfo_height())
	host_x = host.winfo_rootx()
	host_y = host.winfo_rooty()
	x = host_x + (host_w - dlg_w) // 2
	y = host_y + (host_h - dlg_h) // 2
	dialog.geometry(f"{dlg_w}x{dlg_h}+{x}+{y}")
	dialog.resizable(False, False)
	dialog.transient(host)
	dialog.grab_set()
	apply_modern_theme(dialog)

	container = ttk.Frame(dialog, padding=20, style="Card.TFrame")
	container.pack(expand=True, fill="both")

	ttk.Label(container, text=title, style="CardTitle.TLabel").pack(anchor="w", pady=(0, 8))
	ttk.Label(container, text=message, style="CardSub.TLabel", wraplength=410).pack(anchor="w", pady=(0, 18))

	buttons = ttk.Frame(container, style="Card.TFrame")
	buttons.pack(anchor="w")

	def _confirm() -> None:
		result["confirmed"] = True
		dialog.destroy()

	ttk.Button(buttons, text="Confirm", command=_confirm, style="Primary.TButton").pack(side="left", padx=(0, 8))
	ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="left")

	dialog.wait_window()
	return bool(result["confirmed"])
