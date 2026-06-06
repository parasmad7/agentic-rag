"""Generate sample PDF documents for the RAG system."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from agentic_rag.config import PDF_DIR


def _heading(text: str, styles) -> Paragraph:
    return Paragraph(text, styles["Heading1"])


def _subheading(text: str, styles) -> Paragraph:
    return Paragraph(text, styles["Heading2"])


def _body(text: str, styles) -> Paragraph:
    return Paragraph(text, styles["BodyText"])


def _spacer() -> Spacer:
    return Spacer(1, 0.2 * inch)


def generate_expense_policy():
    path = PDF_DIR / "expense_policy.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(_heading("Company Expense & Procurement Policy", styles))
    story.append(_body("Effective Date: January 1, 2025 | Version 3.2 | Approved by: Bob Martinez, CFO", styles))
    story.append(_spacer())

    story.append(_subheading("1. Purpose", styles))
    story.append(_body(
        "This policy establishes the guidelines and approval requirements for all company expenditures, "
        "including procurement of goods and services, travel expenses, and vendor payments. All employees "
        "are expected to comply with these guidelines when making purchases on behalf of the company."
    , styles))
    story.append(_spacer())

    story.append(_subheading("2. Approval Thresholds", styles))
    story.append(_body(
        "All purchase orders and expense requests must be approved according to the following thresholds. "
        "These thresholds were updated from the 2024 policy to reflect the company's growth."
    , styles))
    story.append(_spacer())

    approval_data = [
        ["Amount Range", "Required Approval", "Turnaround Time"],
        ["Up to $5,000", "Direct Manager", "1 business day"],
        ["$5,001 - $50,000", "Department Director", "3 business days"],
        ["$50,001 - $100,000", "VP Level", "5 business days"],
        ["Over $100,000", "CFO + VP Level", "7 business days"],
    ]
    t = Table(approval_data, colWidths=[2 * inch, 2.5 * inch, 2 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(_spacer())

    story.append(_subheading("3. Vendor Payment Terms", styles))
    story.append(_body(
        "All vendor invoices must be paid within 30 days of the invoice date (Net-30). For preferred vendors "
        "with annual contracts exceeding $100,000, payment terms may be extended to Net-45 with CFO approval. "
        "Early payment discounts (2/10 Net-30) should be taken whenever the discount exceeds the company's "
        "cost of capital. Late payments incur a 1.5% monthly penalty and must be reported to the Finance department."
    , styles))
    story.append(_spacer())

    story.append(_subheading("4. Vendor Onboarding Requirements", styles))
    story.append(_body(
        "All new vendors must complete the onboarding process before any purchase orders can be issued. "
        "The onboarding process includes: (a) W-9 or W-8BEN form submission, (b) Insurance certificate verification, "
        "(c) Background check for vendors with facility access, (d) Data security assessment for technology vendors, "
        "(e) Contract review by Legal department. The typical onboarding timeline is 2-4 weeks."
    , styles))
    story.append(_spacer())

    story.append(_subheading("5. Expense Categories", styles))
    category_data = [
        ["Category", "Budget Code", "Annual Limit"],
        ["Technology & Software", "TECH-100", "$500,000"],
        ["Office Supplies", "OPS-200", "$50,000"],
        ["Staffing & Contractors", "HR-300", "$800,000"],
        ["Facilities & Maintenance", "FAC-400", "$300,000"],
        ["Legal & Compliance", "LEG-500", "$200,000"],
        ["Food & Events", "EVT-600", "$75,000"],
    ]
    t2 = Table(category_data, colWidths=[2.5 * inch, 2 * inch, 2 * inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t2)
    story.append(_spacer())

    story.append(_subheading("6. Non-Compliant Spending", styles))
    story.append(_body(
        "Purchases made without proper approval will be flagged in the monthly compliance report. "
        "Employees who repeatedly violate this policy may face disciplinary action. Vendors who submit "
        "invoices exceeding the approved PO amount by more than 10% will have their invoices held pending "
        "review. Any invoice discrepancy must be resolved within 15 business days."
    , styles))
    story.append(_spacer())

    story.append(_subheading("7. Inactive Vendor Policy", styles))
    story.append(_body(
        "Vendors with no purchase orders in the past 12 months will be marked as inactive. Inactive vendors "
        "must go through a simplified re-onboarding process before new purchase orders can be issued. This "
        "includes updated insurance certificates and a review of contract terms."
    , styles))

    doc.build(story)
    print(f"  Generated: {path.name}")


def generate_q1_report():
    path = PDF_DIR / "q1_2025_financial_report.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(_heading("Q1 2025 Financial Report", styles))
    story.append(_body("Prepared by: Finance Department | Date: April 5, 2025 | Classification: Internal", styles))
    story.append(_spacer())

    story.append(_subheading("1. Executive Summary", styles))
    story.append(_body(
        "Q1 2025 showed solid revenue growth of 12% quarter-over-quarter, reaching $42M in total revenue. "
        "Operating expenses increased by 8% due to planned infrastructure investments and new hires. "
        "Net income was $6.2M, representing a 14.8% net margin. Customer retention rate remained strong "
        "at 94%, though two high-value customers flagged concerns about platform reliability."
    , styles))
    story.append(_spacer())

    story.append(_subheading("2. Revenue Breakdown", styles))
    revenue_data = [
        ["Product", "Q1 2025", "Q4 2024", "Change"],
        ["Data Platform", "$24.5M", "$21.8M", "+12.4%"],
        ["Analytics Suite", "$14.2M", "$12.7M", "+11.8%"],
        ["Professional Services", "$3.3M", "$3.0M", "+10.0%"],
        ["Total", "$42.0M", "$37.5M", "+12.0%"],
    ]
    t = Table(revenue_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch, 1 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ecf0f1")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(_spacer())

    story.append(_subheading("3. Operating Expenses", styles))
    expense_data = [
        ["Department", "Budget", "Actual", "Variance"],
        ["Engineering", "$2,000,000", "$1,850,000", "-7.5%"],
        ["Finance", "$800,000", "$780,000", "-2.5%"],
        ["Operations", "$1,200,000", "$1,350,000", "+12.5%"],
        ["Sales", "$1,500,000", "$1,420,000", "-5.3%"],
        ["HR", "$600,000", "$580,000", "-3.3%"],
    ]
    t2 = Table(expense_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t2)
    story.append(_spacer())

    story.append(_body(
        "Operations exceeded budget by 12.5% primarily due to the Floor 3 renovation project managed by "
        "BuildRight Construction, which ran $15,000 over the approved purchase order amount. This has been "
        "flagged for review under the expense policy's non-compliant spending guidelines."
    , styles))
    story.append(_spacer())

    story.append(_subheading("4. Vendor Performance Summary", styles))
    story.append(_body(
        "Vendor payment compliance was 83.3% for Q1 (10 of 12 invoices paid on time). Two invoices are "
        "currently overdue: INV-2025-005 from Global Office Supplies ($2,800) and INV-2025-009 from "
        "DataFlow Analytics ($18,500). The DataFlow invoice is flagged as high priority due to the amount. "
        "Total vendor spend for Q1 was $523,500 across 8 active vendors."
    , styles))
    story.append(_spacer())

    story.append(_subheading("5. Customer Health", styles))
    story.append(_body(
        "Average customer satisfaction score was 3.14 out of 5 based on 7 feedback responses. Two critical "
        "platform outages in February impacted Pacific Logistics (CUST-005), leading to a VP-level escalation. "
        "The engineering team implemented safeguards including connection pool scaling and deployment checks. "
        "Metro Financial Group (CUST-002) reported degraded support response times and is considered at-risk "
        "for churn. Recommended actions: (1) Dedicated support engineer for Pacific Logistics, "
        "(2) Support SLA review for Metro Financial, (3) Proactive outreach to GreenLeaf regarding pricing concerns."
    , styles))
    story.append(_spacer())

    story.append(_subheading("6. Key Risks & Recommendations", styles))
    story.append(_body(
        "1. Platform Reliability: Two outages in one month is unacceptable. Engineering should prioritize "
        "infrastructure redundancy in Q2. Budget: $150,000 additional cloud spend.\n\n"
        "2. Vendor Compliance: BuildRight Construction's budget overrun violated procurement policy. "
        "Recommend freezing new POs to BuildRight pending review.\n\n"
        "3. Customer Churn Risk: Metro Financial and Pacific Logistics represent $2.1M ARR combined. "
        "Losing either would impact Q2 targets significantly.\n\n"
        "4. Overdue Invoices: $21,300 in overdue vendor payments. Finance team should prioritize resolution "
        "to maintain vendor relationships."
    , styles))

    doc.build(story)
    print(f"  Generated: {path.name}")


def generate_vendor_guide():
    path = PDF_DIR / "vendor_onboarding_guide.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BulletText", parent=styles["BodyText"], leftIndent=20, bulletIndent=10))
    story = []

    story.append(_heading("Vendor Onboarding Guide", styles))
    story.append(_body("Version 2.1 | Last Updated: January 15, 2025 | Owner: Operations Department", styles))
    story.append(_spacer())

    story.append(_subheading("1. Overview", styles))
    story.append(_body(
        "This guide outlines the standard process for onboarding new vendors. All vendors must complete "
        "this process before purchase orders can be issued. The onboarding process typically takes 2-4 weeks "
        "depending on vendor category and complexity."
    , styles))
    story.append(_spacer())

    story.append(_subheading("2. Vendor Categories", styles))
    category_data = [
        ["Category", "Risk Level", "Additional Requirements"],
        ["Technology", "High", "Security assessment, data handling review"],
        ["Office Supplies", "Low", "Standard documentation only"],
        ["Staffing", "Medium", "Background checks, insurance verification"],
        ["Facilities", "Medium", "Insurance, safety certifications"],
        ["Food Services", "Low", "Health permits, insurance"],
        ["Legal", "High", "Conflict of interest check, NDA"],
    ]
    t = Table(category_data, colWidths=[1.5 * inch, 1.5 * inch, 3.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(_spacer())

    story.append(_subheading("3. Required Documentation", styles))
    story.append(_body(
        "All vendors must submit the following documentation: (a) Completed vendor registration form, "
        "(b) W-9 form (domestic) or W-8BEN (international), (c) Certificate of insurance with minimum "
        "$1M general liability coverage, (d) Banking information for ACH payments, (e) Signed master "
        "service agreement or purchase terms. Technology vendors must additionally provide SOC 2 Type II "
        "report or equivalent security certification."
    , styles))
    story.append(_spacer())

    story.append(_subheading("4. Approval Workflow", styles))
    story.append(_body(
        "Step 1: Requesting department submits vendor request via procurement portal. "
        "Step 2: Operations team conducts initial screening (1-2 business days). "
        "Step 3: Category-specific assessments are initiated. "
        "Step 4: Legal reviews contract terms (3-5 business days for standard contracts). "
        "Step 5: Finance sets up vendor in payment system. "
        "Step 6: Vendor receives welcome packet and primary contact information. "
        "Total timeline: 10-20 business days depending on vendor category."
    , styles))
    story.append(_spacer())

    story.append(_subheading("5. Performance Monitoring", styles))
    story.append(_body(
        "All active vendors are reviewed quarterly using the following criteria: delivery timeliness, "
        "invoice accuracy, quality of goods/services, responsiveness to issues, and contract compliance. "
        "Vendors scoring below 3.0 out of 5.0 on the quarterly review will be placed on a performance "
        "improvement plan. Vendors failing to improve within two consecutive quarters may have their "
        "contracts terminated."
    , styles))
    story.append(_spacer())

    story.append(_subheading("6. Inactive Vendor Reactivation", styles))
    story.append(_body(
        "Vendors marked as inactive (no POs in 12 months) must complete a simplified reactivation process: "
        "(a) Updated insurance certificates, (b) Confirmation of banking details, (c) Review of any contract "
        "amendments. Reactivation typically takes 3-5 business days. If the vendor has been inactive for more "
        "than 24 months, full re-onboarding is required."
    , styles))

    doc.build(story)
    print(f"  Generated: {path.name}")


def setup():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating sample PDFs:")
    generate_expense_policy()
    generate_q1_report()
    generate_vendor_guide()
    print("Done!")


if __name__ == "__main__":
    setup()
