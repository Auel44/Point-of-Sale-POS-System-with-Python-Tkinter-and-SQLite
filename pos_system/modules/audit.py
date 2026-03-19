"""Audit logging — records security-relevant events to the AuditLog table."""

from __future__ import annotations

from datetime import datetime
import hashlib
from typing import Any

from database.db_connection import get_connection
from modules.permissions import has_permission
from utils.helpers import log_error


_GENESIS_HASH = "GENESIS"


def _compute_hash(
	timestamp: str,
	user_id: int | None,
	username: str | None,
	action: str,
	detail: str,
	prev_hash: str,
) -> str:
	payload = f"{timestamp}|{user_id}|{username}|{action}|{detail}|{prev_hash}"
	return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record(action: str, user: dict[str, Any] | None = None, detail: str = "") -> None:
	"""Write one audit log entry.

	Args:
	    action:  Short description of the event, e.g. "LOGIN_SUCCESS".
	    user:    The user dict from the session (may be None for failed logins).
	    detail:  Any extra context, e.g. the affected username on a role change.
	             NEVER pass passwords or card data here.
	"""
	user_id = int(user["user_id"]) if user and "user_id" in user else None
	username = str(user["username"]) if user and "username" in user else None
	timestamp = datetime.now().isoformat(sep=" ", timespec="seconds")
	detail_value = detail or ""

	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"SELECT row_hash FROM AuditLog WHERE row_hash IS NOT NULL ORDER BY log_id DESC LIMIT 1"
			)
			last = cursor.fetchone()
			prev_hash = str(last[0]) if last and last[0] else _GENESIS_HASH
			row_hash = _compute_hash(timestamp, user_id, username, action, detail_value, prev_hash)
			cursor.execute(
				"""
				INSERT INTO AuditLog (timestamp, user_id, username, action, detail, prev_hash, row_hash)
				VALUES (?, ?, ?, ?, ?, ?, ?)
				""",
				(timestamp, user_id, username, action, detail or None, prev_hash, row_hash),
			)
			conn.commit()
	except Exception as exc:
		log_error("audit.record", exc)


def list_recent(limit: int = 500, actor: dict[str, Any] | None = None) -> list[dict[str, Any]]:
	"""Return recent audit log rows for admin viewing."""
	if not has_permission(actor, "view_audit_logs"):
		record("PERMISSION_DENIED", user=actor, detail="view_audit_logs")
		return []

	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT log_id, timestamp, user_id, username, action, detail, prev_hash, row_hash
				FROM AuditLog
				ORDER BY log_id DESC
				LIMIT ?
				""",
				(max(1, int(limit)),),
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("audit.list_recent", exc)
		return []

	results: list[dict[str, Any]] = []
	for row in rows:
		log_id, timestamp, user_id, username, action, detail, prev_hash, row_hash = row
		detail_value = str(detail or "")
		prev_value = str(prev_hash or _GENESIS_HASH)
		expected_hash = _compute_hash(
			str(timestamp),
			int(user_id) if user_id is not None else None,
			str(username) if username is not None else None,
			str(action),
			detail_value,
			prev_value,
		)
		results.append(
			{
				"log_id": log_id,
				"timestamp": timestamp,
				"user_id": user_id,
				"username": username,
				"action": action,
				"detail": detail,
				"prev_hash": prev_hash,
				"row_hash": row_hash,
				"hash_ok": bool(row_hash) and str(row_hash) == expected_hash,
			}
		)
	return results
