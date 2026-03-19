"""Input validation helpers for UI and module guardrails."""

from __future__ import annotations

import re
import random
import string


def is_valid_price(value: str | float | int) -> bool:
	"""Return True for numeric values >= 0."""
	try:
		return float(value) >= 0
	except (TypeError, ValueError):
		return False


def is_valid_quantity(value: str | float | int) -> bool:
	"""Return True for non-negative integers."""
	try:
		int_value = int(value)
		return int_value >= 0 and float(value) == int_value
	except (TypeError, ValueError):
		return False


def is_valid_email(value: str) -> bool:
	"""Basic email format check."""
	if not isinstance(value, str):
		return False
	email = value.strip()
	if not email:
		return False
	return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


def is_non_empty(value: str) -> bool:
	"""Return True for non-blank strings."""
	return isinstance(value, str) and bool(value.strip())


def password_policy_error(value: str) -> str | None:
	"""Return a human-readable password policy error, or None when valid."""
	if not isinstance(value, str):
		return "Password is required."
	password = value.strip()
	if len(password) < 10:
		return "Password must be at least 10 characters long."
	if not re.search(r"[A-Z]", password):
		return "Password must include at least one uppercase letter."
	if not re.search(r"[a-z]", password):
		return "Password must include at least one lowercase letter."
	if not re.search(r"\d", password):
		return "Password must include at least one number."
	if not re.search(r"[^A-Za-z0-9]", password):
		return "Password must include at least one symbol."
	return None


def generate_password(length: int = 14) -> str:
	"""Generate a random password meeting policy requirements.
	
	Returns a password of at least 14 characters containing:
	- Uppercase letters
	- Lowercase letters
	- Numbers
	- Symbols
	"""
	if length < 10:
		length = 10
	
	# Define character sets
	uppercase = string.ascii_uppercase
	lowercase = string.ascii_lowercase
	digits = string.digits
	symbols = "!@#$%^&*-_=+"
	
	# Ensure at least one from each category
	password_chars = [
		random.choice(uppercase),
		random.choice(lowercase),
		random.choice(digits),
		random.choice(symbols),
	]
	
	# Fill the rest randomly from all categories
	all_chars = uppercase + lowercase + digits + symbols
	password_chars.extend(random.choice(all_chars) for _ in range(length - 4))
	
	# Shuffle to avoid predictable patterns
	random.shuffle(password_chars)
	
	return "".join(password_chars)


def generate_username_from_fullname(full_name: str, max_length: int = 7) -> str:
	"""Generate a letters-only username by blending all name parts.

	This uses a round-robin character pick across each word so multi-part
	names contribute to the final username while still honoring max_length.
	"""
	if not full_name:
		return ""

	import unicodedata

	name = unicodedata.normalize("NFKD", full_name)
	name = name.encode("ASCII", "ignore").decode("ASCII")
	parts = [
		"".join(ch for ch in token.lower() if ch.isalpha())
		for token in name.split()
	]
	parts = [part for part in parts if part]
	if not parts:
		return ""
	if max_length < 1:
		max_length = 1

	indices = [0] * len(parts)
	username_chars: list[str] = []
	while len(username_chars) < max_length:
		added_in_cycle = False
		for idx, part in enumerate(parts):
			if len(username_chars) >= max_length:
				break
			if indices[idx] < len(part):
				username_chars.append(part[indices[idx]])
				indices[idx] += 1
				added_in_cycle = True
		if not added_in_cycle:
			break

	return "".join(username_chars)

