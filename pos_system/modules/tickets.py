"""Password reset ticket management for user support workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import modules.audit as audit
from database.db_connection import get_connection
from modules.permissions import has_permission
from utils.helpers import log_error


def _can_manage_tickets(actor: dict[str, Any] | None) -> bool:
	"""Check if actor has permission to manage password reset tickets."""
	return has_permission(actor, "manage_users")


def create_reset_ticket(username: str) -> bool:
	"""Create a new password reset ticket for a user who forgot their password.
	
	Args:
		username: The username of the account needing password reset
	
	Returns:
		True if ticket was created successfully, False otherwise
	"""
	normalized_username = username.strip()
	if not normalized_username:
		return False
	
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			
			# Verify user exists (case-insensitive) and store canonical username.
			cursor.execute(
				"SELECT user_id, username FROM Users WHERE LOWER(username) = LOWER(?)",
				(normalized_username,),
			)
			user_row = cursor.fetchone()
			if not user_row:
				return False
			canonical_username = str(user_row[1])
			
			# Create the ticket
			created_at = datetime.now().isoformat()
			cursor.execute(
				"""
				INSERT INTO PasswordResetTickets (username, email, created_at, status)
				VALUES (?, ?, ?, ?)
				""",
				(canonical_username, None, created_at, "OPEN"),
			)
			conn.commit()
			
			audit.record(
				"PASSWORD_RESET_TICKET_CREATED",
				detail=f"username={canonical_username}",
			)
			return True
	except Exception as exc:
		log_error("tickets.create_reset_ticket", exc)
		return False


def count_open_tickets() -> int:
	"""Return the number of open password reset tickets."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute("SELECT COUNT(*) FROM PasswordResetTickets WHERE status = 'OPEN'")
			count = cursor.fetchone()[0]
			return int(count)
	except Exception as exc:
		log_error("tickets.count_open_tickets", exc)
		return 0


def list_open_tickets() -> list[dict[str, Any]]:
	"""Return all open password reset tickets."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT ticket_id, username, email, created_at
				FROM PasswordResetTickets
				WHERE status = 'OPEN'
				ORDER BY created_at DESC
				"""
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("tickets.list_open_tickets", exc)
		return []
	
	return [
		{
			"ticket_id": r[0],
			"username": r[1],
			"email": r[2],
			"created_at": r[3],
		}
		for r in rows
	]


def list_all_tickets() -> list[dict[str, Any]]:
	"""Return all password reset tickets (open and resolved)."""
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			cursor.execute(
				"""
				SELECT ticket_id, username, email, created_at, status, resolved_at, resolved_by
				FROM PasswordResetTickets
				ORDER BY created_at DESC
				"""
			)
			rows = cursor.fetchall()
	except Exception as exc:
		log_error("tickets.list_all_tickets", exc)
		return []
	
	tickets = []
	for r in rows:
		ticket = {
			"ticket_id": r[0],
			"username": r[1],
			"email": r[2],
			"created_at": r[3],
			"status": r[4],
			"resolved_at": r[5],
			"resolved_by": r[6],
		}
		
		# Fetch resolver's username if applicable
		if r[6]:
			try:
				with get_connection() as conn2:
					cursor2 = conn2.cursor()
					cursor2.execute("SELECT username FROM Users WHERE user_id = ?", (r[6],))
					resolver_row = cursor2.fetchone()
					ticket["resolved_by_username"] = resolver_row[0] if resolver_row else "Unknown"
			except Exception:
				ticket["resolved_by_username"] = "Unknown"
		
		tickets.append(ticket)
	
	return tickets


def resolve_ticket(ticket_id: int, new_password: str, actor: dict[str, Any] | None = None) -> bool:
	"""Resolve a password reset ticket by setting a new temporary password.
	
	Args:
		ticket_id: The ID of the ticket to resolve
		new_password: The temporary password to set for the user
		actor: The admin user resolving the ticket
	
	Returns:
		True if ticket was resolved and password updated, False otherwise
	"""
	if not _can_manage_tickets(actor):
		audit.record("PERMISSION_DENIED", user=actor, detail="resolve_password_reset_ticket")
		return False
	
	if not new_password.strip():
		return False
	
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			
			# Get the ticket details
			cursor.execute(
				"SELECT username FROM PasswordResetTickets WHERE ticket_id = ? AND status = 'OPEN'",
				(int(ticket_id),),
			)
			ticket_row = cursor.fetchone()
			if not ticket_row:
				return False
			
			username = ticket_row[0]
			
			# Get the user
			cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
			user_row = cursor.fetchone()
			if not user_row:
				return False
			
			user_id = user_row[0]
			
			# Import here to avoid circular dependency
			from modules.auth import hash_password
			from modules.users import is_password_in_use

			# Enforce unique password usage across all other users.
			if is_password_in_use(new_password, exclude_user_id=int(user_id)):
				return False

			cursor.execute(
				"UPDATE Users SET password_hash = ? WHERE user_id = ?",
				(hash_password(new_password), int(user_id)),
			)
			if cursor.rowcount <= 0:
				return False
			
			# Mark ticket as resolved
			resolved_at = datetime.now().isoformat()
			cursor.execute(
				"""
				UPDATE PasswordResetTickets
				SET status = 'RESOLVED', resolved_at = ?, resolved_by = ?
				WHERE ticket_id = ?
				""",
				(resolved_at, actor["user_id"] if actor else None, int(ticket_id)),
			)
			if cursor.rowcount <= 0:
				return False
			conn.commit()
			
			audit.record(
				"PASSWORD_RESET_TICKET_RESOLVED",
				user=actor,
				detail=f"ticket_id={ticket_id} username={username}",
			)
			return True
	except Exception as exc:
		log_error("tickets.resolve_ticket", exc)
		return False


def close_ticket(ticket_id: int, actor: dict[str, Any] | None = None) -> bool:
	"""Close a ticket without resetting the password (e.g., duplicate ticket)."""
	if not _can_manage_tickets(actor):
		audit.record("PERMISSION_DENIED", user=actor, detail="close_password_reset_ticket")
		return False
	
	try:
		with get_connection() as conn:
			cursor = conn.cursor()
			resolved_at = datetime.now().isoformat()
			cursor.execute(
				"""
				UPDATE PasswordResetTickets
				SET status = 'CLOSED', resolved_at = ?, resolved_by = ?
				WHERE ticket_id = ?
				""",
				(resolved_at, actor["user_id"] if actor else None, int(ticket_id)),
			)
			conn.commit()
			
			if cursor.rowcount > 0:
				audit.record(
					"PASSWORD_RESET_TICKET_CLOSED",
					user=actor,
					detail=f"ticket_id={ticket_id}",
				)
				return True
			return False
	except Exception as exc:
		log_error("tickets.close_ticket", exc)
		return False
