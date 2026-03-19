"""Centralized role-permission rules for POS authorization."""

from __future__ import annotations

from typing import Any


ROLE_MODULES: dict[str, list[str]] = {
	"Cashier": ["Sales", "Payments", "Receipts", "Change Password"],
	"Manager": [
		"Sales",
		"Payments",
		"Receipts",
		"Change Password",
		"Reports",
		"Inventory",
		"Customers",
		"Product Management",
	],
	"Admin": [
		"Sales",
		"Payments",
		"Receipts",
		"Change Password",
		"Audit Logs",
		"Reports",
		"Inventory",
		"Customers",
		"Product Management",
		"User Management",
		"Password Reset Tickets",
	],
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
	"Cashier": {
		"process_sales",
		"view_payments",
		"view_receipts",
	},
	"Manager": {
		"process_sales",
		"view_payments",
		"view_receipts",
		"view_reports",
		"manage_inventory",
		"manage_customers",
		"manage_products",
	},
	"Admin": {
		"process_sales",
		"view_payments",
		"view_receipts",
		"view_reports",
		"manage_inventory",
		"manage_customers",
		"manage_products",
		"manage_users",
		"view_audit_logs",
	},
}


def role_of(user: dict[str, Any] | None) -> str:
	"""Return normalized role name, defaulting to Cashier."""
	if not user:
		return "Cashier"
	return str(user.get("role", "Cashier"))


def has_permission(user: dict[str, Any] | None, permission: str) -> bool:
	"""Return True when user's role grants the given permission."""
	role = role_of(user)
	return permission in ROLE_PERMISSIONS.get(role, set())


def can_access_module(user: dict[str, Any] | None, module_name: str) -> bool:
	"""Return True when role allows access to a dashboard module."""
	role = role_of(user)
	return module_name in ROLE_MODULES.get(role, ROLE_MODULES["Cashier"])
