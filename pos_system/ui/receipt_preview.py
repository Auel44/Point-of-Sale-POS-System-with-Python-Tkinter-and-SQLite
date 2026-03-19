"""Receipt preview screen — formatted receipt with Save as PNG and Close."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

try:
	from PIL import Image, ImageDraw, ImageFont
	_PIL_AVAILABLE = True
except ImportError:
	_PIL_AVAILABLE = False

from modules.receipts import generate_receipt
from ui.theme import apply_modern_theme


class ReceiptPreview(tk.Toplevel):
	"""Shows the formatted receipt after a completed payment.

	Calls generate_receipt(sale_id) to produce and save the text, then
	displays it in a scrollable monospaced Text widget.
	"""

	def __init__(
		self,
		parent: tk.Misc,
		sale_id: int,
		# The remaining parameters are kept for caller compatibility
		# but the text is generated fresh from the database.
		cart: list[dict[str, Any]] | None = None,
		discount: float = 0.0,
		tax: float = 0.0,
		grand_total: float = 0.0,
		method: str = "",
		tendered: float = 0.0,
		change: float = 0.0,
	) -> None:
		super().__init__(parent)
		self.title(f"Receipt — Sale #{sale_id}")
		self.geometry("480x540")
		self.resizable(False, True)
		self.grab_set()
		apply_modern_theme(self)

		self._sale_id = sale_id
		self._receipt_text = generate_receipt(sale_id)

		self._build_ui()

	# ------------------------------------------------------------------
	# Layout
	# ------------------------------------------------------------------

	def _build_ui(self) -> None:
		frame = ttk.Frame(self, padding=(12, 10))
		frame.pack(expand=True, fill="both")

		ttk.Label(frame, text="Receipt", font=("Segoe UI", 13, "bold")).pack(
			anchor="w", pady=(0, 8)
		)

		# Scrollable text area
		text_frame = ttk.Frame(frame)
		text_frame.pack(expand=True, fill="both")

		self._text = tk.Text(
			text_frame,
			font=("Courier New", 9),
			wrap="none",
			state="disabled",
			relief="flat",
			background="#f9f9f9",
		)
		vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self._text.yview)
		hsb = ttk.Scrollbar(text_frame, orient="horizontal", command=self._text.xview)
		self._text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

		vsb.pack(side="right", fill="y")
		hsb.pack(side="bottom", fill="x")
		self._text.pack(side="left", expand=True, fill="both")

		# Populate
		self._text.config(state="normal")
		if self._receipt_text:
			self._text.insert("1.0", self._receipt_text)
		else:
			self._text.insert("1.0", "(Receipt data not available.)")
		self._text.config(state="disabled")

		# Buttons
		btn_frame = ttk.Frame(frame)
		btn_frame.pack(fill="x", pady=(10, 0))

		ttk.Button(
			btn_frame, text="Save as PNG", command=self._print_receipt
		).pack(side="left", padx=(0, 6))

		ttk.Button(
			btn_frame, text="Close", command=self._close
		).pack(side="right")

	# ------------------------------------------------------------------
	# Actions
	# ------------------------------------------------------------------

	def _print_receipt(self) -> None:
		"""Save the receipt as a PNG image file."""
		if not self._receipt_text:
			messagebox.showinfo("Save", "No receipt loaded to save.", parent=self)
			return
		if not _PIL_AVAILABLE:
			messagebox.showerror(
				"Save Error",
				"Pillow is required for PNG export. Install it with: pip install pillow",
				parent=self,
			)
			return
		path = filedialog.asksaveasfilename(
			parent=self,
			defaultextension=".png",
			filetypes=[("PNG Image", "*.png")],
			initialfile=f"receipt_{self._sale_id}.png",
		)
		if not path:
			return
		try:
			lines = self._receipt_text.splitlines() or [""]
			font = ImageFont.load_default()
			line_height = 18
			padding = 16
			width = 560
			height = max(220, padding * 2 + line_height * len(lines))
			image = Image.new("RGB", (width, height), "white")
			draw = ImageDraw.Draw(image)
			y = padding
			for line in lines:
				draw.text((padding, y), line, fill="black", font=font)
				y += line_height
			image.save(path, format="PNG")
			messagebox.showinfo("Saved", f"Receipt saved as PNG:\n{path}", parent=self)
		except OSError as exc:
			messagebox.showerror("Save Error", str(exc), parent=self)

	def _close(self) -> None:
		self.destroy()
		# Walk up to find and clear the SalesScreen cart if still open
		try:
			parent = self.master
			while parent is not None:
				if hasattr(parent, "_cart") and hasattr(parent, "_refresh_cart_tree"):
					parent._cart.clear()
					parent._refresh_cart_tree()
					parent._refresh_totals()
					break
				parent = getattr(parent, "master", None)
		except Exception:
			pass
