"""User management operations for admin workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import modules.audit as audit
from database.db_connection import get_connection
from modules.auth import hash_password, verify_password
from modules.permissions import has_permission
from utils.helpers import log_error
from utils.validators import password_policy_error


def _can_manage_users(actor: dict[str, Any] | None) -> bool:
	return has_permission(actor, "manage_users")


def is_password_in_use(plain_password: str, exclude_user_id: int | None = None) -> bool:
	"""Return True when plain_password matches any existing user password hash."""
	if not plain_password:
		return False
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			if exclude_user_id is None:
				cursor.execute("SELECT password_hash FROM Users")
			else:
				cursor.execute(
					"SELECT password_hash FROM Users WHERE user_id != ?",
					(int(exclude_user_id),),
				)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("users.is_password_in_use", exc)
		return False

	for row in rows:
		stored_hash = str(row[0] or "")
		if stored_hash and verify_password(plain_password, stored_hash):
			return True
	return False


def get_all_users() -> list[dict[str, Any]]:
	"""Return all users ordered by username."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT user_id, username, role, full_name, address, gender
				FROM Users
				ORDER BY username COLLATE NOCASE ASC
				"""
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("users.get_all_users", exc)
		return []

	return [{"user_id": r[0], "username": r[1], "role": r[2], "full_name": r[3], "address": r[4], "gender": r[5]} for r in rows]


def create_user(username: str, plain_password: str, role: str, full_name: str = "", address: str = "", gender: str = "", actor: dict[str, Any] | None = None) -> bool:
	"""Create a user account."""
	if not _can_manage_users(actor):
		audit.record("PERMISSION_DENIED", user=actor, detail="create_user")
		return False
	if not username.strip() or not plain_password.strip() or role not in {"Admin", "Manager", "Cashier"}:
		return False
	policy_error = password_policy_error(plain_password)
	if policy_error:
		return False
	if is_password_in_use(plain_password):
		return False
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"SELECT 1 FROM DeletedUsers WHERE LOWER(username) = LOWER(?)",
				(username.strip(),),
			)
			if cursor.fetchone() is not None:
				return False
			cursor.execute(
				"""
				INSERT INTO Users (username, password_hash, role, full_name, address, gender)
				VALUES (?, ?, ?, ?, ?, ?)
				""",
				(username.strip(), hash_password(plain_password), role, full_name.strip(), address.strip(), gender.strip()),
			)
			conn.commit()
		audit.record("USER_CREATED", user=actor, detail=f"new_user={username.strip()} role={role}")
		return True
	except Exception as exc:
		log_error("users.create_user", exc)
		return False


def update_user_role(user_id: int, role: str, actor: dict[str, Any] | None = None) -> bool:
	"""Update role for a user."""
	if not _can_manage_users(actor):
		audit.record("PERMISSION_DENIED", user=actor, detail="update_user_role")
		return False
	if role not in {"Admin", "Manager", "Cashier"}:
		return False
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute("UPDATE Users SET role = ? WHERE user_id = ?", (role, int(user_id)))
			conn.commit()
			if cursor.rowcount > 0:
				audit.record("ROLE_UPDATED", user=actor, detail=f"target_user_id={user_id} new_role={role}")
				return True
			return False
	except Exception as exc:
		log_error("users.update_user_role", exc)
		return False


def update_user_details(
	user_id: int,
	full_name: str,
	address: str,
	gender: str,
	role: str,
	actor: dict[str, Any] | None = None,
) -> bool:
	"""Update editable profile details and role for a user."""
	if not _can_manage_users(actor):
		audit.record("PERMISSION_DENIED", user=actor, detail="update_user_details")
		return False
	if role not in {"Admin", "Manager", "Cashier"}:
		return False
	if gender and gender not in {"M", "F", "Other"}:
		return False
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				UPDATE Users
				SET full_name = ?, address = ?, gender = ?, role = ?
				WHERE user_id = ?
				""",
				(full_name.strip(), address.strip(), gender.strip(), role, int(user_id)),
			)
			conn.commit()
			if cursor.rowcount > 0:
				audit.record(
					"USER_DETAILS_UPDATED",
					user=actor,
					detail=f"target_user_id={user_id} role={role}",
				)
				return True
			return False
	except Exception as exc:
		log_error("users.update_user_details", exc)
		return False


def reset_user_password(user_id: int, new_plain_password: str, actor: dict[str, Any] | None = None) -> bool:
	"""Reset password for a user."""
	if not _can_manage_users(actor):
		audit.record("PERMISSION_DENIED", user=actor, detail="reset_user_password")
		return False
	if not new_plain_password.strip():
		return False
	policy_error = password_policy_error(new_plain_password)
	if policy_error:
		return False
	if is_password_in_use(new_plain_password, exclude_user_id=int(user_id)):
		return False
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"UPDATE Users SET password_hash = ? WHERE user_id = ?",
				(hash_password(new_plain_password), int(user_id)),
			)
			conn.commit()
			if cursor.rowcount > 0:
				audit.record("PASSWORD_RESET", user=actor, detail=f"target_user_id={user_id}")
				return True
			return False
	except Exception as exc:
		log_error("users.reset_user_password", exc)
		return False


def delete_user(user_id: int, actor: dict[str, Any] | None = None) -> bool:
	"""Delete a user by id."""
	if not _can_manage_users(actor):
		audit.record("PERMISSION_DENIED", user=actor, detail="delete_user")
		return False
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT user_id, username, role, full_name, address, gender
				FROM Users
				WHERE user_id = ?
				""",
				(int(user_id),),
			)
			row = cursor.fetchone()
			deleted_username = row[1] if row else str(user_id)
			if row is None:
				return False
			cursor.execute(
				"""
				INSERT OR REPLACE INTO DeletedUsers (
					original_user_id,
					username,
					role,
					full_name,
					address,
					gender,
					deleted_at,
					deleted_by_user_id,
					deleted_by_username
				)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
				""",
				(
					int(row[0]),
					str(row[1]),
					str(row[2] or ""),
					str(row[3] or ""),
					str(row[4] or ""),
					str(row[5] or ""),
					datetime.now().isoformat(),
					int(actor.get("user_id")) if actor and actor.get("user_id") is not None else None,
					str(actor.get("username")) if actor and actor.get("username") is not None else None,
				),
			)
			cursor.execute("DELETE FROM Users WHERE user_id = ?", (int(user_id),))
			conn.commit()
			if cursor.rowcount > 0:
				audit.record("USER_DELETED", user=actor, detail=f"deleted_user={deleted_username}")
				return True
			return False
	except Exception as exc:
		log_error("users.delete_user", exc)
		return False
