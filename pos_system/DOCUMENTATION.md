# POS System Documentation

Technical documentation for the desktop Point of Sale (POS) application.

## Table of Contents

- [1. Overview](#1-overview)
- [2. Architecture](#2-architecture)
- [3. Module Capabilities](#3-module-capabilities)
- [4. Role Permissions](#4-role-permissions)
- [5. Security Controls](#5-security-controls)
- [6. Data Model](#6-data-model)
- [7. Setup and Run](#7-setup-and-run)
- [8. Default Credentials](#8-default-credentials)
- [9. Validation Checklist](#9-validation-checklist)
- [10. Artifacts and Output](#10-artifacts-and-output)
- [11. Operational Notes](#11-operational-notes)

## 1. Overview

This project is a desktop POS solution designed for academic and practical retail workflows.

### Technology Stack

- Python
- Tkinter (desktop user interface)
- SQLite (local database)

### Primary Objectives

- Fast checkout and transaction recording
- Role-based access and workflow separation
- Product, inventory, and customer tracking
- Reporting and export support
- Security-first handling of users and transactions

## 2. Architecture

The application follows a three-layer structure.

### 2.1 Presentation Layer (UI)

- Login screen
- Dashboard with module navigation
- Embedded module views (Sales, Payments, Receipts, and more)

Implementation location: `ui/`

### 2.2 Application Layer (Business Logic)

Business rules and operations are implemented in modular services.

Implementation location: `modules/`

Core services include:

- Authentication and authorization
- Sales and checkout processing
- Payment handling
- Inventory management
- Reporting and exports
- User and permissions management
- Audit logging

### 2.3 Data Layer (Persistence)

- SQLite database file: `pos_system.db`
- Schema creation and setup: `database/db_setup.py`
- Database helpers and connection handling: `database/`

## 3. Module Capabilities

### 3.1 Authentication and Roles

- Login and logout flow
- Bcrypt password hashing
- Role-based access control (RBAC)
- Supported roles: Cashier, Manager, Admin
- Account lockout after repeated failed attempts
- Archived deleted users are blocked from future login attempts

### 3.2 Product Management

- Add, update, delete products
- Search and barcode support
- Product fields: ID, name, category, price, quantity, barcode

### 3.3 Inventory Management

- Automatic stock deduction after sales
- Manual stock adjustments
- Inventory visibility including low-stock checks
- Inventory search by ID, name, category, and barcode
- Adjustment logs include the acting user

### 3.4 Sales Processing

- Cart-based checkout for non-manager roles
- Product lookup and quantity handling
- Discount support
- Payment trigger and sale finalization
- Sales history with date-range filters
- Sales History cashier filter for manager/admin views
- Cashier-level total summaries in filtered history views
- Explicit warning dialogs when requested quantity exceeds available stock

### 3.5 Payments

- Payment methods: cash, mobile money, card
- Payment history display and date sorting
- Manager-only date range filtering and period totals
- Payment record search by payment ID, sale ID, and cashier username
- Payment rows include cashier username for traceability

### 3.6 Receipts

- Receipt generation from recorded sales
- Receipt preview by sale ID
- PNG receipt download support

### 3.7 Customer Management

- Add and update customer profiles
- Customer purchase history lookup
- CSV export for customer data

### 3.8 Reporting

- Daily sales
- Weekly sales
- Product performance
- Inventory reporting
- Cashier-focused reporting
- Cashier filter supports cashier ID and username
- Cashier selector supports dropdown choices and ID-username value parsing

### 3.9 User Management

- Admin-only user CRUD
- Role updates
- Password reset
- Self-delete prevention for active account
- User details update action includes role, full name, address, and gender updates
- User table includes address visibility
- Deleted user archival to `DeletedUsers` before removal from `Users`
- Archived deleted usernames cannot be recreated

### 3.10 Password Reset Tickets

- Username-only ticket creation from login flow
- Admin ticket queue with status filtering (OPEN, RESOLVED, CLOSED, ALL)
- Resolve flow generates temporary password and updates ticket status
- Resolve flow now keeps status consistent and visible immediately in UI
- Close flow supports non-reset ticket closure

### 3.11 Audit Logs

- Security and administrative event logging
- Hash-chained tamper-evident records
- Admin audit viewer and CSV export

## 4. Role Permissions

### 4.1 Cashier

Accessible modules:

- Sales
- Payments
- Receipts

Restrictions:

- Can view only own sales history
- Can view only own payment records
- Can load only own receipts
- Cannot export sales or payment records
- Sees stock-limit warning when entered cart quantity exceeds available stock

### 4.2 Manager

Accessible modules:

- Sales (history-focused)
- Payments
- Receipts
- Reports
- Inventory
- Customers
- Product Management

Additional capabilities:

- Payment date-range filtering
- Total payment amount for selected period
- Export filtered payment records
- Sales history cashier filter with per-cashier totals
- Payments search by payment ID, sale ID, and cashier username

### 4.3 Admin

- Full system access
- Includes User Management and Audit Logs
- Product and inventory operational actions are constrained by configured permissions

## 5. Security Controls

Implemented controls include:

- Bcrypt password hashing
- Role and permission enforcement in UI and backend
- Account lockout after repeated failed logins
- Inactivity auto-logout when timeout expires
- Password policy enforcement (length and complexity)
- Password uniqueness enforcement across all users
- Audit trail for security and admin actions
- Tamper-evident audit hash chaining
- Parameterized SQL queries
- Deleted user archival with permanent application-level login block

## 6. Data Model

Primary tables:

- Users
- DeletedUsers
- Products
- Customers
- Sales
- Sales_Items
- Payments
- Inventory
- AuditLog
- PasswordResetTickets

Default database file:

- `pos_system.db`

## 7. Setup and Run

### 7.1 Prerequisites

- Python 3.10+

### 7.2 Install Dependencies

Run from the `pos_system` directory:

```bash
pip install -r requirements.txt
```

### 7.3 Start the Application

Run from the `pos_system` directory:

```bash
python main.py
```

On Windows, you can use `pythonw.exe` for windowless startup.

## 8. Default Credentials

Default admin account:

- Username: `admin`
- Password: `admin123`

Change this password immediately in any non-test environment.

## 9. Validation Checklist

Recommended validation steps:

- Login with each role and verify module visibility
- Confirm Cashier cannot export sales or payment records
- Confirm Cashier sees only own sales, payments, and receipts
- Confirm Manager payment date filtering and period totals
- Confirm reports accept cashier ID and username filters
- Confirm reports cashier dropdown options populate and execute correctly
- Confirm stock-limit warning appears when entered quantity exceeds stock
- Confirm changed password is rejected when already used by another user
- Confirm deleted user is archived and cannot log in again
- Confirm archived deleted username cannot be recreated
- Confirm ticket status changes to RESOLVED immediately after successful solve
- Confirm inactivity timeout logs out the user automatically
- Confirm admin user-management operations
- Confirm audit logs are recorded for security events

## 10. Artifacts and Output

- Database: `pos_system.db`
- Receipts directory: `receipts/`
- Logs directory: `logs/`

## 11. Operational Notes

- The system is local-first and single-node by default (SQLite).
- For larger deployments, consider PostgreSQL or MySQL with centralized backup and monitoring.
- Hardware integrations (receipt printers, card readers, cash drawers) can be added in a future phase.
