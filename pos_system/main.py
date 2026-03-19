"""Application entry point for the POS system."""

from __future__ import annotations

import importlib
import subprocess
import sys


def _ensure_runtime_dependency(module_name: str, package_name: str | None = None) -> None:
	"""Ensure a dependency can be imported in the active interpreter."""
	try:
		importlib.import_module(module_name)
		return
	except ModuleNotFoundError:
		pass

	pkg = package_name or module_name
	subprocess.check_call(
		[sys.executable, "-m", "pip", "install", pkg],
		stdout=subprocess.DEVNULL,
		stderr=subprocess.DEVNULL,
	)


def _bootstrap_imports() -> tuple[object, object]:
	"""Install required runtime packages before importing app modules."""
	_ensure_runtime_dependency("bcrypt")

	from database.db_setup import initialize_database
	from ui.login_screen import LoginScreen

	return initialize_database, LoginScreen


def main() -> None:
	"""Initialize storage and start the login UI."""
	initialize_database, LoginScreen = _bootstrap_imports()
	initialize_database()
	app = LoginScreen()
	app.run()


if __name__ == "__main__":
	main()
