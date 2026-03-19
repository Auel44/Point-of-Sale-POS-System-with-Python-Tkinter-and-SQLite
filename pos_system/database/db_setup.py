"""Database schema initialization for the POS system."""

import bcrypt

from database.db_connection import get_connection


def initialize_database() -> None:
	"""Create all required POS tables if they do not already exist."""
	with get_connection() as connection:
		cursor = connection.cursor()

		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS Users (
				user_id INTEGER PRIMARY KEY AUTOINCREMENT,
				username TEXT UNIQUE NOT NULL,
				password_hash TEXT NOT NULL,
				role TEXT NOT NULL CHECK(role IN ('Admin', 'Manager', 'Cashier')),
				full_name TEXT,
				address TEXT,
				gender TEXT,
				failed_attempts INTEGER NOT NULL DEFAULT 0,
				locked_until TEXT
			);
			"""
		)

		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS Products (
				product_id INTEGER PRIMARY KEY AUTOINCREMENT,
				product_name TEXT NOT NULL,
				category TEXT,
				price REAL NOT NULL,
				quantity INTEGER NOT NULL DEFAULT 0,
				barcode TEXT UNIQUE,
				added_by_user_id INTEGER,
				FOREIGN KEY (added_by_user_id) REFERENCES Users(user_id)
			);
			"""
		)

		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS Customers (
				customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT NOT NULL,
				phone TEXT,
				email TEXT,
				address TEXT,
				loyalty_points INTEGER DEFAULT 0
			);
			"""
		)

		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS Sales (
				sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
				date TEXT NOT NULL,
				user_id INTEGER NOT NULL,
				customer_id INTEGER,
				total_amount REAL NOT NULL,
				payment_method TEXT,
				FOREIGN KEY (user_id) REFERENCES Users(user_id),
				FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)
			);
			"""
		)

		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS Sales_Items (
				sale_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
				sale_id INTEGER NOT NULL,
				product_id INTEGER NOT NULL,
				quantity INTEGER NOT NULL,
				price REAL NOT NULL,
				FOREIGN KEY (sale_id) REFERENCES Sales(sale_id),
				FOREIGN KEY (product_id) REFERENCES Products(product_id)
			);
			"""
		)

		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS Payments (
				payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
				sale_id INTEGER NOT NULL,
				amount_paid REAL NOT NULL,
				payment_method TEXT NOT NULL,
				change_given REAL DEFAULT 0,
				FOREIGN KEY (sale_id) REFERENCES Sales(sale_id)
			);
			"""
		)

		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS Inventory (
				inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
				product_id INTEGER NOT NULL,
				change_amount INTEGER NOT NULL,
				reason TEXT,
				date TEXT NOT NULL,
				user_id INTEGER,
				FOREIGN KEY (product_id) REFERENCES Products(product_id),
				FOREIGN KEY (user_id) REFERENCES Users(user_id)
			);
			"""
		)

		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS AuditLog (
				log_id INTEGER PRIMARY KEY AUTOINCREMENT,
				timestamp TEXT NOT NULL,
				user_id INTEGER,
				username TEXT,
				action TEXT NOT NULL,
				detail TEXT,
				prev_hash TEXT,
				row_hash TEXT
			);
			"""
		)

		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS PasswordResetTickets (
				ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
				username TEXT NOT NULL,
				email TEXT,
				created_at TEXT NOT NULL,
				status TEXT NOT NULL DEFAULT 'OPEN',
				resolved_at TEXT,
				resolved_by INTEGER,
				new_password TEXT,
				FOREIGN KEY (resolved_by) REFERENCES Users(user_id)
			);
			"""
		)

		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS DeletedUsers (
				deleted_id INTEGER PRIMARY KEY AUTOINCREMENT,
				original_user_id INTEGER,
				username TEXT UNIQUE NOT NULL,
				role TEXT,
				full_name TEXT,
				address TEXT,
				gender TEXT,
				deleted_at TEXT NOT NULL,
				deleted_by_user_id INTEGER,
				deleted_by_username TEXT
			);
			"""
		)

		cursor.execute("SELECT user_id FROM Users WHERE username = ?", ("admin",))
		admin_user = cursor.fetchone()
		if admin_user is None:
			password_hash = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
			cursor.execute(
				"""
				INSERT INTO Users (username, password_hash, role)
				VALUES (?, ?, ?)
				""",
				("admin", password_hash, "Admin"),
			)

		connection.commit()

	# -- Migrations: safely add new columns to existing databases --
	with get_connection() as connection:
		cursor = connection.cursor()
		existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(Users)")}
		if "failed_attempts" not in existing_cols:
			cursor.execute("ALTER TABLE Users ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0")
		if "locked_until" not in existing_cols:
			cursor.execute("ALTER TABLE Users ADD COLUMN locked_until TEXT")
		audit_cols = {row[1] for row in cursor.execute("PRAGMA table_info(AuditLog)")}
		if "prev_hash" not in audit_cols:
			cursor.execute("ALTER TABLE AuditLog ADD COLUMN prev_hash TEXT")
		if "row_hash" not in audit_cols:
			cursor.execute("ALTER TABLE AuditLog ADD COLUMN row_hash TEXT")
		product_cols = {row[1] for row in cursor.execute("PRAGMA table_info(Products)")}
		if "added_by_user_id" not in product_cols:
			cursor.execute("ALTER TABLE Products ADD COLUMN added_by_user_id INTEGER")
		inventory_cols = {row[1] for row in cursor.execute("PRAGMA table_info(Inventory)")}
		if "user_id" not in inventory_cols:
			cursor.execute("ALTER TABLE Inventory ADD COLUMN user_id INTEGER")
		# Ensure deleted-users archive table exists for older databases.
		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS DeletedUsers (
				deleted_id INTEGER PRIMARY KEY AUTOINCREMENT,
				original_user_id INTEGER,
				username TEXT UNIQUE NOT NULL,
				role TEXT,
				full_name TEXT,
				address TEXT,
				gender TEXT,
				deleted_at TEXT NOT NULL,
				deleted_by_user_id INTEGER,
				deleted_by_username TEXT
			)
			"""
		)
		connection.commit()
