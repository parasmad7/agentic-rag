"""Create and populate the SQLite sample database."""

from datetime import date

import sqlalchemy as sa

from agentic_rag.config import SQLITE_DB_PATH

metadata = sa.MetaData()

departments = sa.Table(
    "departments", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.String, nullable=False),
    sa.Column("budget", sa.Float, nullable=False),
    sa.Column("head", sa.String, nullable=False),
)

employees = sa.Table(
    "employees", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.String, nullable=False),
    sa.Column("email", sa.String, nullable=False),
    sa.Column("department_id", sa.Integer, sa.ForeignKey("departments.id")),
    sa.Column("role", sa.String, nullable=False),
    sa.Column("salary", sa.Float, nullable=False),
    sa.Column("hire_date", sa.Date, nullable=False),
)

vendors = sa.Table(
    "vendors", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.String, nullable=False),
    sa.Column("contact_email", sa.String),
    sa.Column("category", sa.String, nullable=False),
    sa.Column("status", sa.String, nullable=False, default="active"),
    sa.Column("onboarded_date", sa.Date),
)

invoices = sa.Table(
    "invoices", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("vendor_id", sa.Integer, sa.ForeignKey("vendors.id")),
    sa.Column("invoice_number", sa.String, nullable=False),
    sa.Column("amount", sa.Float, nullable=False),
    sa.Column("status", sa.String, nullable=False),  # paid | pending | overdue
    sa.Column("issue_date", sa.Date, nullable=False),
    sa.Column("due_date", sa.Date, nullable=False),
    sa.Column("paid_date", sa.Date),
)

purchase_orders = sa.Table(
    "purchase_orders", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("vendor_id", sa.Integer, sa.ForeignKey("vendors.id")),
    sa.Column("requester_id", sa.Integer, sa.ForeignKey("employees.id")),
    sa.Column("po_number", sa.String, nullable=False),
    sa.Column("total_amount", sa.Float, nullable=False),
    sa.Column("status", sa.String, nullable=False),  # approved | pending | rejected
    sa.Column("approval_level", sa.String),  # manager | director | vp
    sa.Column("created_date", sa.Date, nullable=False),
)

line_items = sa.Table(
    "line_items", metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("purchase_order_id", sa.Integer, sa.ForeignKey("purchase_orders.id")),
    sa.Column("description", sa.String, nullable=False),
    sa.Column("quantity", sa.Integer, nullable=False),
    sa.Column("unit_price", sa.Float, nullable=False),
)


def setup():
    SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SQLITE_DB_PATH.exists():
        SQLITE_DB_PATH.unlink()

    engine = sa.create_engine(f"sqlite:///{SQLITE_DB_PATH}")
    metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(departments.insert(), [
            {"id": 1, "name": "Engineering", "budget": 2_000_000, "head": "Alice Chen"},
            {"id": 2, "name": "Finance", "budget": 800_000, "head": "Bob Martinez"},
            {"id": 3, "name": "Operations", "budget": 1_200_000, "head": "Carol Williams"},
            {"id": 4, "name": "Sales", "budget": 1_500_000, "head": "David Kim"},
            {"id": 5, "name": "HR", "budget": 600_000, "head": "Eva Johnson"},
        ])

        conn.execute(employees.insert(), [
            {"id": 1, "name": "Alice Chen", "email": "alice@company.com", "department_id": 1, "role": "VP Engineering", "salary": 220000, "hire_date": date(2019, 3, 15)},
            {"id": 2, "name": "Bob Martinez", "email": "bob@company.com", "department_id": 2, "role": "CFO", "salary": 250000, "hire_date": date(2018, 1, 10)},
            {"id": 3, "name": "Carol Williams", "email": "carol@company.com", "department_id": 3, "role": "COO", "salary": 240000, "hire_date": date(2018, 6, 20)},
            {"id": 4, "name": "David Kim", "email": "david@company.com", "department_id": 4, "role": "VP Sales", "salary": 210000, "hire_date": date(2019, 9, 1)},
            {"id": 5, "name": "Eva Johnson", "email": "eva@company.com", "department_id": 5, "role": "HR Director", "salary": 180000, "hire_date": date(2020, 2, 14)},
            {"id": 6, "name": "Frank Lee", "email": "frank@company.com", "department_id": 1, "role": "Senior Engineer", "salary": 165000, "hire_date": date(2020, 7, 1)},
            {"id": 7, "name": "Grace Park", "email": "grace@company.com", "department_id": 1, "role": "Engineer", "salary": 140000, "hire_date": date(2021, 3, 15)},
            {"id": 8, "name": "Henry Adams", "email": "henry@company.com", "department_id": 2, "role": "Financial Analyst", "salary": 120000, "hire_date": date(2021, 6, 1)},
            {"id": 9, "name": "Iris Wang", "email": "iris@company.com", "department_id": 3, "role": "Operations Manager", "salary": 135000, "hire_date": date(2020, 11, 10)},
            {"id": 10, "name": "Jack Brown", "email": "jack@company.com", "department_id": 4, "role": "Account Executive", "salary": 130000, "hire_date": date(2022, 1, 15)},
            {"id": 11, "name": "Karen Davis", "email": "karen@company.com", "department_id": 1, "role": "Engineer", "salary": 135000, "hire_date": date(2022, 4, 1)},
            {"id": 12, "name": "Leo Nguyen", "email": "leo@company.com", "department_id": 3, "role": "Supply Chain Analyst", "salary": 115000, "hire_date": date(2022, 8, 15)},
        ])

        conn.execute(vendors.insert(), [
            {"id": 1, "name": "Acme Cloud Services", "contact_email": "sales@acmecloud.com", "category": "technology", "status": "active", "onboarded_date": date(2020, 1, 15)},
            {"id": 2, "name": "Global Office Supplies", "contact_email": "orders@globalsupplies.com", "category": "office_supplies", "status": "active", "onboarded_date": date(2019, 6, 1)},
            {"id": 3, "name": "TechHire Staffing", "contact_email": "contracts@techhire.com", "category": "staffing", "status": "active", "onboarded_date": date(2020, 3, 10)},
            {"id": 4, "name": "SecureNet Solutions", "contact_email": "info@securenet.com", "category": "technology", "status": "active", "onboarded_date": date(2021, 2, 20)},
            {"id": 5, "name": "Premier Catering", "contact_email": "events@premiercatering.com", "category": "food_services", "status": "inactive", "onboarded_date": date(2019, 11, 5)},
            {"id": 6, "name": "DataFlow Analytics", "contact_email": "support@dataflow.com", "category": "technology", "status": "active", "onboarded_date": date(2022, 1, 10)},
            {"id": 7, "name": "BuildRight Construction", "contact_email": "projects@buildright.com", "category": "facilities", "status": "active", "onboarded_date": date(2021, 9, 15)},
            {"id": 8, "name": "LegalEase Partners", "contact_email": "consult@legalease.com", "category": "legal", "status": "active", "onboarded_date": date(2020, 7, 1)},
        ])

        conn.execute(invoices.insert(), [
            {"id": 1, "vendor_id": 1, "invoice_number": "INV-2025-001", "amount": 45000, "status": "paid", "issue_date": date(2025, 1, 5), "due_date": date(2025, 2, 5), "paid_date": date(2025, 1, 28)},
            {"id": 2, "vendor_id": 1, "invoice_number": "INV-2025-002", "amount": 45000, "status": "paid", "issue_date": date(2025, 2, 5), "due_date": date(2025, 3, 5), "paid_date": date(2025, 3, 1)},
            {"id": 3, "vendor_id": 1, "invoice_number": "INV-2025-003", "amount": 48000, "status": "pending", "issue_date": date(2025, 3, 5), "due_date": date(2025, 4, 5), "paid_date": None},
            {"id": 4, "vendor_id": 2, "invoice_number": "INV-2025-004", "amount": 3200, "status": "paid", "issue_date": date(2025, 1, 15), "due_date": date(2025, 2, 15), "paid_date": date(2025, 2, 10)},
            {"id": 5, "vendor_id": 2, "invoice_number": "INV-2025-005", "amount": 2800, "status": "overdue", "issue_date": date(2025, 2, 15), "due_date": date(2025, 3, 15), "paid_date": None},
            {"id": 6, "vendor_id": 3, "invoice_number": "INV-2025-006", "amount": 75000, "status": "paid", "issue_date": date(2025, 1, 20), "due_date": date(2025, 2, 20), "paid_date": date(2025, 2, 18)},
            {"id": 7, "vendor_id": 4, "invoice_number": "INV-2025-007", "amount": 32000, "status": "paid", "issue_date": date(2025, 1, 10), "due_date": date(2025, 2, 10), "paid_date": date(2025, 2, 8)},
            {"id": 8, "vendor_id": 4, "invoice_number": "INV-2025-008", "amount": 32000, "status": "pending", "issue_date": date(2025, 3, 10), "due_date": date(2025, 4, 10), "paid_date": None},
            {"id": 9, "vendor_id": 6, "invoice_number": "INV-2025-009", "amount": 18500, "status": "overdue", "issue_date": date(2025, 1, 25), "due_date": date(2025, 2, 25), "paid_date": None},
            {"id": 10, "vendor_id": 7, "invoice_number": "INV-2025-010", "amount": 125000, "status": "paid", "issue_date": date(2025, 2, 1), "due_date": date(2025, 3, 1), "paid_date": date(2025, 3, 15)},
            {"id": 11, "vendor_id": 8, "invoice_number": "INV-2025-011", "amount": 15000, "status": "paid", "issue_date": date(2025, 2, 10), "due_date": date(2025, 3, 10), "paid_date": date(2025, 3, 5)},
            {"id": 12, "vendor_id": 3, "invoice_number": "INV-2025-012", "amount": 82000, "status": "pending", "issue_date": date(2025, 3, 20), "due_date": date(2025, 4, 20), "paid_date": None},
        ])

        conn.execute(purchase_orders.insert(), [
            {"id": 1, "vendor_id": 1, "requester_id": 6, "po_number": "PO-2025-001", "total_amount": 45000, "status": "approved", "approval_level": "director", "created_date": date(2024, 12, 20)},
            {"id": 2, "vendor_id": 2, "requester_id": 9, "po_number": "PO-2025-002", "total_amount": 3200, "status": "approved", "approval_level": "manager", "created_date": date(2025, 1, 5)},
            {"id": 3, "vendor_id": 3, "requester_id": 5, "po_number": "PO-2025-003", "total_amount": 150000, "status": "approved", "approval_level": "vp", "created_date": date(2025, 1, 10)},
            {"id": 4, "vendor_id": 4, "requester_id": 6, "po_number": "PO-2025-004", "total_amount": 64000, "status": "approved", "approval_level": "director", "created_date": date(2025, 1, 5)},
            {"id": 5, "vendor_id": 6, "requester_id": 7, "po_number": "PO-2025-005", "total_amount": 18500, "status": "approved", "approval_level": "manager", "created_date": date(2025, 1, 15)},
            {"id": 6, "vendor_id": 7, "requester_id": 3, "po_number": "PO-2025-006", "total_amount": 125000, "status": "approved", "approval_level": "vp", "created_date": date(2025, 1, 20)},
            {"id": 7, "vendor_id": 1, "requester_id": 11, "po_number": "PO-2025-007", "total_amount": 8500, "status": "pending", "approval_level": "manager", "created_date": date(2025, 3, 25)},
            {"id": 8, "vendor_id": 5, "requester_id": 9, "po_number": "PO-2025-008", "total_amount": 4200, "status": "rejected", "approval_level": "manager", "created_date": date(2025, 3, 1)},
        ])

        conn.execute(line_items.insert(), [
            {"id": 1, "purchase_order_id": 1, "description": "Cloud compute instances (annual)", "quantity": 12, "unit_price": 3750},
            {"id": 2, "purchase_order_id": 2, "description": "Ergonomic chairs", "quantity": 10, "unit_price": 250},
            {"id": 3, "purchase_order_id": 2, "description": "Standing desk converters", "quantity": 5, "unit_price": 140},
            {"id": 4, "purchase_order_id": 3, "description": "Contract software engineers (Q1)", "quantity": 3, "unit_price": 50000},
            {"id": 5, "purchase_order_id": 4, "description": "Firewall appliance", "quantity": 2, "unit_price": 12000},
            {"id": 6, "purchase_order_id": 4, "description": "Security audit service", "quantity": 1, "unit_price": 40000},
            {"id": 7, "purchase_order_id": 5, "description": "Data analytics platform license", "quantity": 1, "unit_price": 18500},
            {"id": 8, "purchase_order_id": 6, "description": "Office renovation - floor 3", "quantity": 1, "unit_price": 125000},
            {"id": 9, "purchase_order_id": 7, "description": "Additional cloud storage (500TB)", "quantity": 1, "unit_price": 8500},
            {"id": 10, "purchase_order_id": 8, "description": "Company anniversary catering", "quantity": 1, "unit_price": 4200},
        ])

    print(f"SQLite database created at {SQLITE_DB_PATH}")
    print("Tables: departments, employees, vendors, invoices, purchase_orders, line_items")


if __name__ == "__main__":
    setup()
