"""Authentication and lightweight session helpers for the POS system."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import bcrypt

from database.db_connection import get_connection
from utils.helpers import log_error
import modules.audit as audit


CURRENT_USER: dict[str, Any] | None = None

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def hash_password(plain_password: str) -> str:
	"""Hash a plain-text password using bcrypt."""
	hashed_bytes = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
	return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed: str) -> bool:
	"""Return True when a plain password matches a bcrypt hash."""
	try:
		return bcrypt.checkpw(plain_password.encode("utf-8"), hashed.encode("utf-8"))
	except ValueError:
		return False


def _record_failed_attempt(user_id: int) -> None:
	"""Increment failed attempts; lock the account if limit is reached."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"UPDATE Users SET failed_attempts = failed_attempts + 1 WHERE user_id = ?",
				(user_id,),
			)
			cursor.execute("SELECT failed_attempts FROM Users WHERE user_id = ?", (user_id,))
			attempts = cursor.fetchone()[0]
			if attempts >= MAX_FAILED_ATTEMPTS:
				locked_until = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
				cursor.execute(
					"UPDATE Users SET locked_until = ? WHERE user_id = ?",
					(locked_until, user_id),
				)
			conn.commit()
	except Exception as exc:
		log_error("auth._record_failed_attempt", exc)


def _clear_failed_attempts(user_id: int) -> None:
	"""Reset the failed attempt counter after a successful login."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"UPDATE Users SET failed_attempts = 0, locked_until = NULL WHERE user_id = ?",
				(user_id,),
			)
			conn.commit()
	except Exception as exc:
		log_error("auth._clear_failed_attempts", exc)


def login(username: str, password: str) -> dict[str, Any] | None | str:
	"""Authenticate a user and return a session-safe user object on success.

	Returns:
	  - dict with user info on success
	  - "locked" string if the account is currently locked out
	  - None if credentials are wrong or user not found
	"""
	global CURRENT_USER

	if not username or not password:
		return None

	try:
		with get_connection() as connection:
			cursor = connection.cursor()
			cursor.execute(
				"SELECT 1 FROM DeletedUsers WHERE LOWER(username) = LOWER(?)",
				(username.strip(),),
			)
			if cursor.fetchone() is not None:
				audit.record("LOGIN_BLOCKED_DELETED", detail=f"username={username.strip()}")
				return None
			cursor.execute(
				"""
				SELECT user_id, username, password_hash, role, failed_attempts, locked_until
				FROM Users
				WHERE username = ?
				""",
				(username.strip(),),
			)
			row = cursor.fetchone()
	except Exception as exc:
		log_error("auth.login", exc)
		return None

	if row is None:
		return None

	user_id, db_username, password_hash, role, failed_attempts, locked_until = row

	# Check lockout
	if locked_until:
		try:
			lock_time = datetime.fromisoformat(locked_until)
			if datetime.now() < lock_time:
				remaining = int((lock_time - datetime.now()).total_seconds() / 60) + 1
				audit.record("LOGIN_LOCKED", detail=f"username={username.strip()}")
				return f"locked:{remaining}"
		except ValueError:
			pass  # malformed timestamp — ignore lock

	if not verify_password(password, password_hash):
		_record_failed_attempt(user_id)
		audit.record("LOGIN_FAILURE", detail=f"username={username.strip()}")
		return None

	_clear_failed_attempts(user_id)

	CURRENT_USER = {
		"user_id": user_id,
		"username": db_username,
		"role": role,
	}
	audit.record("LOGIN_SUCCESS", user=CURRENT_USER)
	return CURRENT_USER


def logout() -> None:
	"""Clear the active in-memory session."""
	global CURRENT_USER
	if CURRENT_USER:
		audit.record("LOGOUT", user=CURRENT_USER)
	CURRENT_USER = None


def change_password(username: str, old_password: str, new_password: str) -> bool:
	"""Allow a user to change their password by verifying the old password first.
	
	Returns True if password was changed successfully, False otherwise.
	"""
	if not username or not old_password or not new_password:
		return False

	try:
		from utils.validators import password_policy_error
		from modules.users import is_password_in_use

		error = password_policy_error(new_password)
		if error:
			return False

		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"SELECT user_id, password_hash FROM Users WHERE username = ?",
				(username.strip(),),
			)
			row = cursor.fetchone()
			if not row:
				return False

			user_id, stored_hash = row
			if not verify_password(old_password, stored_hash):
				return False
			if is_password_in_use(new_password, exclude_user_id=int(user_id)):
				return False

			cursor.execute(
				"UPDATE Users SET password_hash = ? WHERE username = ?",
				(hash_password(new_password), username.strip()),
			)
			conn.commit()

			if cursor.rowcount > 0:
				audit.record(
					"PASSWORD_CHANGED",
					user={"username": username.strip(), "user_id": user_id},
					detail=f"user_initiated_change",
				)
				return True
			return False
	except Exception as exc:
		log_error("auth.change_password", exc)
		return False
