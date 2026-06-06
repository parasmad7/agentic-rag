"""Populate MongoDB with sample collections."""

from datetime import datetime

from pymongo import MongoClient

from agentic_rag.config import MONGO_DB_NAME, MONGO_URI


def setup():
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB_NAME]

    db.customer_feedback.drop()
    db.vendor_reviews.drop()
    db.support_tickets.drop()

    db.customer_feedback.insert_many([
        {
            "customer_id": "CUST-001",
            "customer_name": "Riverside Healthcare",
            "channel": "survey",
            "rating": 4,
            "feedback": "Great onboarding experience. The engineering team was very responsive during integration. Minor delays in getting API documentation.",
            "product": "data_platform",
            "date": datetime(2025, 2, 15),
            "sentiment": "positive",
        },
        {
            "customer_id": "CUST-002",
            "customer_name": "Metro Financial Group",
            "channel": "email",
            "rating": 2,
            "feedback": "Support response times have degraded significantly in Q1. Took 3 days to get a response on a critical billing issue. Considering alternatives.",
            "product": "analytics_suite",
            "date": datetime(2025, 3, 1),
            "sentiment": "negative",
        },
        {
            "customer_id": "CUST-003",
            "customer_name": "TechStart Inc",
            "channel": "survey",
            "rating": 5,
            "feedback": "Excellent product. The new reporting features saved us 10 hours per week. Account manager David has been incredibly helpful.",
            "product": "analytics_suite",
            "date": datetime(2025, 1, 20),
            "sentiment": "positive",
        },
        {
            "customer_id": "CUST-004",
            "customer_name": "GreenLeaf Manufacturing",
            "channel": "phone",
            "rating": 3,
            "feedback": "Product works well but pricing has increased 20% with no clear value addition. Need better transparency on pricing changes.",
            "product": "data_platform",
            "date": datetime(2025, 2, 28),
            "sentiment": "neutral",
        },
        {
            "customer_id": "CUST-005",
            "customer_name": "Pacific Logistics",
            "channel": "survey",
            "rating": 1,
            "feedback": "System went down twice in February during peak operations. Cost us significant revenue. Escalated to VP level.",
            "product": "data_platform",
            "date": datetime(2025, 3, 5),
            "sentiment": "negative",
        },
        {
            "customer_id": "CUST-006",
            "customer_name": "Summit Education",
            "channel": "survey",
            "rating": 4,
            "feedback": "The platform handles our data processing needs well. Would love to see better MongoDB integration in the next release.",
            "product": "data_platform",
            "date": datetime(2025, 3, 10),
            "sentiment": "positive",
        },
        {
            "customer_id": "CUST-007",
            "customer_name": "Bay Area Retail",
            "channel": "email",
            "rating": 3,
            "feedback": "Decent product but the invoice process is confusing. Received duplicate invoices twice in Q1. Billing team eventually resolved it.",
            "product": "analytics_suite",
            "date": datetime(2025, 3, 12),
            "sentiment": "neutral",
        },
    ])

    db.vendor_reviews.insert_many([
        {
            "vendor_id": 1,
            "vendor_name": "Acme Cloud Services",
            "reviewer": "Frank Lee",
            "department": "Engineering",
            "rating": 5,
            "review": "Excellent uptime (99.99%). Support team responds within 1 hour. Price is competitive. Strongly recommend renewing the annual contract.",
            "review_date": datetime(2025, 3, 1),
            "categories": ["reliability", "support", "pricing"],
        },
        {
            "vendor_id": 2,
            "vendor_name": "Global Office Supplies",
            "reviewer": "Iris Wang",
            "department": "Operations",
            "rating": 3,
            "review": "Delivery times have slipped from 2 days to 5 days. Product quality is fine but logistics need improvement. Invoice for Feb was $400 over the PO amount.",
            "review_date": datetime(2025, 3, 5),
            "categories": ["delivery", "invoicing"],
        },
        {
            "vendor_id": 3,
            "vendor_name": "TechHire Staffing",
            "reviewer": "Eva Johnson",
            "department": "HR",
            "rating": 4,
            "review": "Good quality candidates. Placement time averages 3 weeks. One contractor had to be replaced mid-project but TechHire handled it quickly.",
            "review_date": datetime(2025, 2, 20),
            "categories": ["quality", "responsiveness"],
        },
        {
            "vendor_id": 4,
            "vendor_name": "SecureNet Solutions",
            "reviewer": "Frank Lee",
            "department": "Engineering",
            "rating": 4,
            "review": "Security audit was thorough and identified 3 critical vulnerabilities we missed. Firewall appliances working well. Support could be faster.",
            "review_date": datetime(2025, 2, 25),
            "categories": ["quality", "support"],
        },
        {
            "vendor_id": 7,
            "vendor_name": "BuildRight Construction",
            "reviewer": "Carol Williams",
            "department": "Operations",
            "rating": 2,
            "review": "Floor 3 renovation ran 2 weeks over schedule and $15K over budget. Quality of work was acceptable but project management was poor. Final invoice exceeded the approved PO by 12%.",
            "review_date": datetime(2025, 3, 20),
            "categories": ["project_management", "budget", "invoicing"],
        },
    ])

    db.support_tickets.insert_many([
        {
            "ticket_id": "TKT-2025-001",
            "customer_id": "CUST-002",
            "customer_name": "Metro Financial Group",
            "subject": "Billing discrepancy on January invoice",
            "description": "Invoice INV-2025-004 shows $3,200 but our PO was for $2,800. Need clarification on the $400 difference.",
            "priority": "high",
            "status": "resolved",
            "assigned_to": "Henry Adams",
            "created_date": datetime(2025, 1, 18),
            "resolved_date": datetime(2025, 1, 25),
            "resolution": "The $400 difference was due to expedited shipping charges. Credit issued to customer.",
            "category": "billing",
        },
        {
            "ticket_id": "TKT-2025-002",
            "customer_id": "CUST-005",
            "customer_name": "Pacific Logistics",
            "subject": "Platform outage during peak hours",
            "description": "Data platform was unreachable for 4 hours on Feb 12. This occurred during our peak shipping hours and caused significant operational disruption.",
            "priority": "critical",
            "status": "resolved",
            "assigned_to": "Frank Lee",
            "created_date": datetime(2025, 2, 12),
            "resolved_date": datetime(2025, 2, 13),
            "resolution": "Root cause was a database connection pool exhaustion. Increased pool size and added auto-scaling. Credited customer for downtime.",
            "category": "platform",
        },
        {
            "ticket_id": "TKT-2025-003",
            "customer_id": "CUST-005",
            "customer_name": "Pacific Logistics",
            "subject": "Second platform outage in February",
            "description": "Another outage on Feb 26, lasting 2 hours. Customer threatening to churn. VP-level escalation requested.",
            "priority": "critical",
            "status": "resolved",
            "assigned_to": "Alice Chen",
            "created_date": datetime(2025, 2, 26),
            "resolved_date": datetime(2025, 2, 27),
            "resolution": "Unrelated to first outage - caused by a misconfigured load balancer after a deployment. Implemented deployment safeguards. Offered 2 months free.",
            "category": "platform",
        },
        {
            "ticket_id": "TKT-2025-004",
            "customer_id": "CUST-001",
            "customer_name": "Riverside Healthcare",
            "subject": "API documentation outdated",
            "description": "Several API endpoints documented in the developer portal return 404. Need updated docs for v3 API.",
            "priority": "medium",
            "status": "open",
            "assigned_to": "Grace Park",
            "created_date": datetime(2025, 3, 8),
            "resolved_date": None,
            "resolution": None,
            "category": "documentation",
        },
        {
            "ticket_id": "TKT-2025-005",
            "customer_id": "CUST-004",
            "customer_name": "GreenLeaf Manufacturing",
            "subject": "Request for pricing breakdown",
            "description": "Customer wants detailed breakdown of their 20% price increase. Need Finance to provide cost justification.",
            "priority": "medium",
            "status": "open",
            "assigned_to": "Henry Adams",
            "created_date": datetime(2025, 3, 2),
            "resolved_date": None,
            "resolution": None,
            "category": "billing",
        },
        {
            "ticket_id": "TKT-2025-006",
            "customer_id": "CUST-007",
            "customer_name": "Bay Area Retail",
            "subject": "Duplicate invoices received",
            "description": "Customer received two copies of INV-2025-005. One was sent via email and another via postal mail. Need to reconcile.",
            "priority": "low",
            "status": "resolved",
            "assigned_to": "Henry Adams",
            "created_date": datetime(2025, 3, 15),
            "resolved_date": datetime(2025, 3, 18),
            "resolution": "Duplicate was caused by a system migration. Only the email version is valid. Updated mailing list.",
            "category": "billing",
        },
    ])

    print(f"MongoDB database '{MONGO_DB_NAME}' populated:")
    print(f"  customer_feedback: {db.customer_feedback.count_documents({})} documents")
    print(f"  vendor_reviews: {db.vendor_reviews.count_documents({})} documents")
    print(f"  support_tickets: {db.support_tickets.count_documents({})} documents")

    client.close()


if __name__ == "__main__":
    setup()
