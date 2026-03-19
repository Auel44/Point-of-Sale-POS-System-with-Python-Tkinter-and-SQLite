"""General helper functions used across the POS app."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def log_error(source: str, error: Exception | str) -> None:
	"""Append an error entry to logs/errors.log.

	Logging should never crash business logic, so file write failures are ignored.
	"""
	try:
		root = Path(__file__).resolve().parent.parent
		log_dir = root / "logs"
		log_dir.mkdir(exist_ok=True)
		log_file = log_dir / "errors.log"
		timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		log_file.write_text(
			(log_file.read_text(encoding="utf-8") if log_file.exists() else "")
			+ f"[{timestamp}] {source}: {error}\n",
			encoding="utf-8",
		)
	except Exception:
		pass
