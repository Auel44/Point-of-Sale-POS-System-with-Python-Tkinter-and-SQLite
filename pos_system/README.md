# POS System

A desktop Point of Sale application built with Python, Tkinter, and SQLite.

This project includes role-based access control, sales and payment workflows, inventory and product management, customer records, receipts, reporting, and audit logging.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Role Permissions](#role-permissions)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup and Run](#setup-and-run)
- [Configuration Notes](#configuration-notes)
- [Security Controls](#security-controls)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Overview

The POS System is designed for small-to-medium retail operations that need:

- Controlled access by user role
- Reliable transaction workflows
- Traceable activity through audit logs
- Practical reporting and export options

## Features

- Secure authentication using bcrypt password hashing
- Role and permission checks in UI and backend logic
- Sales processing with historical lookup
- Payment handling for cash, card, and mobile money
- Receipt preview and PNG export
- Product management (add, update, delete, search, barcode)
- Inventory tracking, stock adjustment workflows, and inventory search
- Customer profiles with purchase history and CSV export
- Reports with cashier filters (ID or username)
- Audit trail with hash-chained integrity checks
- Password reset ticket workflow from login (username-only submission)
- Password reset ticket admin panel with status filters (OPEN, RESOLVED, CLOSED, ALL)
- Password reset resolution with immediate status updates in the dashboard table
- Dynamic ticket badge in dashboard navigation for open reset requests
- Role-aware Sales panel (Manager and Admin are history-focused, no cart tab)
- Sales History cashier filtering with per-cashier totals
- Payments search by payment ID, sale ID, and cashier username
- User management enhancements (address column, update user details action, role updates)
- Themed confirmation dialogs centered on the dashboard window

## Role Permissions

### Cashier

- Access to Sales, Payments, and Receipts
- Limited to own sales, payments, and receipts
- No export access for sales or payment records
- Receives explicit stock-limit warnings when entered quantity exceeds available stock

### Manager

- Access to Sales, Payments, Receipts, Reports, Inventory, Customers, and Product Management
- Sales view focused on history (no cart tab)
- Payments include date-range totals and CSV export
- Reports support cashier filtering by ID or username
- Payments panel supports search by payment ID, sale ID, and cashier username
- Product and inventory modules are available with manager-level operational controls

### Admin

- Full system access
- Includes User Management and Audit Logs
- Product module is read-only for stock/product updates performed by operational roles
- Inventory module allows visibility of stock and adjustment logs with actor tracking

## Tech Stack

- Python 3.10+
- Tkinter (desktop UI)
- SQLite (local data storage)

## Architecture

The application follows a three-layer structure:

- Presentation layer: Tkinter screens and dashboard navigation
- Application layer: business logic in modules
- Data layer: SQLite persistence and database setup utilities

## Project Structure

```text
pos_system/
|-- main.py
|-- DOCUMENTATION.md
|-- requirements.txt
|-- database/
|-- modules/
|-- ui/
|-- utils/
|-- tests/
|-- receipts/
`-- logs/
```

## Setup and Run

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd pos_system
```

### 2. Create and activate a virtual environment (recommended)

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python main.py
```

On Windows, you can optionally use pythonw.exe to run without a terminal window.

## Configuration Notes

- Default database file: pos_system.db
- Receipt output folder: receipts/
- Audit and application logs: logs/

### Default Accounts

Admin

- Username: support.administrator
- Password: Thealmighty20@

Manager

- Username: eabbebn
- Password: Ebenezerabban20@

Cashier

- Username: skaaosm
- Password: Lookandsee20@

Change these passwords immediately after first login.

## Security Controls

Implemented controls include:

- Bcrypt password hashing
- Password complexity policy enforcement
- Password uniqueness enforcement across users (new password cannot match another user's password)
- Account lockout on repeated failed login attempts
- Automatic logout after inactivity timeout
- Permission checks for restricted actions
- Audit event logging with integrity hash chaining
- Parameterized SQL queries
- Deleted user archival in a dedicated table with permanent login block for archived usernames

## Documentation

For full technical and functional details, see DOCUMENTATION.md.

## Troubleshooting

- Run commands from the pos_system directory to avoid import path issues.
- If admin login is not available, run the app once to trigger database initialization.
- If a newly deleted username cannot be recreated, this is expected behavior; archived deleted usernames are blocked by design.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Make and test your changes.
4. Open a pull request with a clear summary of the update.
