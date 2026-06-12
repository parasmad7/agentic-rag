"""Generate sample PDF documents for the health & fitness RAG system."""

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


def generate_safety_guidelines():
    path = PDF_DIR / "gym_safety_guidelines.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(_heading("Gym Safety Guidelines & Equipment Policy", styles))
    story.append(_body("Effective Date: January 1, 2025 | Version 2.0 | Approved by: Fitness Director", styles))
    story.append(_spacer())

    story.append(_subheading("1. General Safety Rules", styles))
    story.append(_body(
        "All members must complete a safety orientation before using gym equipment for the first time. "
        "Proper athletic footwear is required at all times on the gym floor — no sandals, open-toed shoes, "
        "or bare feet. Members must wipe down all equipment after use with the provided sanitizing spray and "
        "towels. Personal belongings must be stored in lockers, not left on the gym floor. No food is allowed "
        "on the gym floor; water bottles with sealed lids are permitted."
    , styles))
    story.append(_spacer())

    story.append(_subheading("2. Equipment Usage Rules", styles))
    equipment_data = [
        ["Equipment", "Max Duration", "Spotter Required", "Certification Needed"],
        ["Free Weights (< 20 kg)", "No limit", "No", "No"],
        ["Free Weights (20+ kg)", "No limit", "Yes", "No"],
        ["Squat Rack / Bench Press", "30 min during peak", "Yes for heavy lifts", "No"],
        ["Treadmill / Elliptical", "45 min during peak", "No", "No"],
        ["Cable Machines", "No limit", "No", "No"],
        ["Olympic Lifting Platform", "45 min", "Yes", "Yes — trainer approval"],
        ["Swimming Pool", "60 min per session", "Lifeguard on duty", "Swim test required"],
    ]
    t = Table(equipment_data, colWidths=[1.8 * inch, 1.5 * inch, 1.5 * inch, 1.7 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(_spacer())

    story.append(_subheading("3. Trainer Responsibilities", styles))
    story.append(_body(
        "All personal trainers must maintain current CPR/AED certification and their primary fitness certification. "
        "Trainers must conduct a brief safety check of equipment before each personal training session. "
        "Group class instructors must arrive at least 10 minutes before class start time to set up equipment "
        "and greet arriving members. Trainers are responsible for ensuring members use proper form — if a member "
        "is performing an exercise with dangerous form, the trainer must intervene regardless of whether it is "
        "their client. Maximum trainer-to-client ratio for group training is 1:8 for strength classes and 1:15 "
        "for cardio/yoga/pilates classes."
    , styles))
    story.append(_spacer())

    story.append(_subheading("4. Injury Prevention & Response", styles))
    story.append(_body(
        "Members experiencing any pain beyond normal exercise discomfort must stop immediately and notify staff. "
        "First aid kits are located at the front desk, each group class studio, and the pool area. AED devices "
        "are wall-mounted at three locations: main entrance, weight room, and pool deck. All incidents must be "
        "documented in the Incident Report system within 24 hours. Members returning from injuries lasting more "
        "than 2 weeks must obtain a physician clearance letter before resuming training."
    , styles))
    story.append(_spacer())

    story.append(_subheading("5. Class Safety Protocols", styles))
    story.append(_body(
        "All group fitness classes have maximum capacity limits that must not be exceeded under any circumstances. "
        "HIIT and strength classes require a brief warm-up period of at least 5 minutes. Yoga and pilates classes "
        "must include cool-down and stretching in the final 10 minutes. Members new to a class format must inform "
        "the instructor before class begins so modifications can be provided. Heart rate monitors are recommended "
        "for all cardio and HIIT classes — the gym provides loaner monitors at the front desk."
    , styles))
    story.append(_spacer())

    story.append(_subheading("6. Emergency Procedures", styles))
    story.append(_body(
        "In case of a medical emergency, call 911 immediately, then notify the front desk. Staff trained in "
        "CPR/AED should begin first response while waiting for EMS. The gym evacuation route is posted at all "
        "exits. Fire extinguishers are located in the kitchen area, laundry room, and each studio. Monthly "
        "safety drills are conducted on the first Monday of each month at 6:00 AM before opening."
    , styles))

    doc.build(story)
    print(f"  Generated: {path.name}")


def generate_q1_report():
    path = PDF_DIR / "q1_2025_fitness_report.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(_heading("Q1 2025 Fitness Center Report", styles))
    story.append(_body("Prepared by: Management Team | Date: April 5, 2025 | Classification: Internal", styles))
    story.append(_spacer())

    story.append(_subheading("1. Executive Summary", styles))
    story.append(_body(
        "Q1 2025 was a strong quarter for the fitness center. Total active memberships grew 15% year-over-year "
        "to 312 members. Revenue reached $128,000, up from $108,000 in Q4 2024. Group class attendance hit an "
        "all-time high with 2,840 total class visits across Q1. Member retention rate was 91%, exceeding our "
        "target of 88%. However, two areas need attention: trainer punctuality complaints increased, and "
        "nutrition program adoption among new members remains low at 35%."
    , styles))
    story.append(_spacer())

    story.append(_subheading("2. Membership Growth", styles))
    membership_data = [
        ["Plan Type", "Q1 2025", "Q4 2024", "Change"],
        ["Elite ($159.99/mo)", "45", "38", "+18.4%"],
        ["Premium ($109.99/mo)", "112", "98", "+14.3%"],
        ["Basic ($49.99/mo)", "155", "140", "+10.7%"],
        ["Total Active", "312", "276", "+13.0%"],
    ]
    t = Table(membership_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch, 1 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#d5e8d4")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(_spacer())

    story.append(_body(
        "The January new-year surge brought 28 new sign-ups, though 4 cancelled before the end of Q1 "
        "(85.7% new member retention). Elite memberships saw the highest growth driven by the new personal "
        "training perks added in December 2024. One member (Nina Kowalski) went inactive due to relocation."
    , styles))
    story.append(_spacer())

    story.append(_subheading("3. Class Attendance", styles))
    class_data = [
        ["Class Category", "Total Q1 Visits", "Avg per Session", "Capacity Utilization"],
        ["HIIT", "920", "18.4", "91%"],
        ["Yoga", "680", "17.0", "70%"],
        ["Cardio (Spin)", "540", "27.0", "90%"],
        ["Strength", "380", "12.7", "85%"],
        ["Pilates", "320", "13.3", "67%"],
        ["Total", "2,840", "-", "81%"],
    ]
    t2 = Table(class_data, colWidths=[2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t2)
    story.append(_spacer())

    story.append(_body(
        "HIIT classes continue to be the most popular format, with the Saturday Weekend Warrior class "
        "at 100% capacity every week and a waitlist of 8-12 members. Derek Washington's classes consistently "
        "fill up. Pilates utilization is below target — Sofia Andersson received punctuality complaints "
        "that may be affecting enrollment. Recommendation: address punctuality issue and consider a promotional "
        "trial for pilates classes."
    , styles))
    story.append(_spacer())

    story.append(_subheading("4. Trainer Performance", styles))
    trainer_data = [
        ["Trainer", "Avg Rating", "Sessions (Q1)", "Specialty"],
        ["Marcus Rivera", "4.9", "142", "Strength"],
        ["Yuki Tanaka", "4.8", "128", "Yoga"],
        ["Derek Washington", "4.5", "156", "HIIT"],
        ["Sofia Andersson", "3.4", "98", "Pilates"],
        ["Kwame Asante", "3.1", "110", "Cardio"],
        ["Rachel Kim", "4.6", "85", "Nutrition"],
    ]
    t3 = Table(trainer_data, colWidths=[2 * inch, 1.2 * inch, 1.3 * inch, 2 * inch])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (2, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t3)
    story.append(_spacer())

    story.append(_body(
        "Marcus Rivera and Yuki Tanaka are top performers with excellent member feedback. Derek Washington "
        "has the highest session volume but received feedback about class overcrowding. Sofia Andersson's "
        "rating dropped from 4.1 to 3.4 due to punctuality issues — two complaints filed in February. "
        "Kwame Asante received feedback about repetitive cardio routines. Recommendation: performance "
        "improvement plans for Sofia and Kwame, with 90-day review."
    , styles))
    story.append(_spacer())

    story.append(_subheading("5. Member Health Outcomes", styles))
    story.append(_body(
        "Among members with at least 2 body metric recordings in Q1, results were very encouraging. "
        "Average weight loss was 2.1 kg across 8 tracked members. Average body fat reduction was 1.4 "
        "percentage points. Average resting heart rate improved by 3.2 bpm. Standout results include "
        "Sarah Johnson (lost 2.7 kg, body fat down from 24.0% to 22.1%) and Tom Baker (lost 3.0 kg "
        "despite dietary challenges — referred to nutrition counseling). Members with personal trainers "
        "showed 40% better results than those training independently."
    , styles))
    story.append(_spacer())

    story.append(_subheading("6. Key Risks & Recommendations", styles))
    story.append(_body(
        "1. Trainer Quality: Sofia Andersson and Kwame Asante need improvement plans. Low trainer ratings "
        "directly correlate with membership cancellations — 3 of 4 Q1 cancellations cited trainer quality.\n\n"
        "2. Class Capacity: HIIT classes are consistently full. Add a second Saturday morning session to "
        "capture waitlist demand. Estimated revenue impact: +$2,400/month.\n\n"
        "3. Nutrition Adoption: Only 35% of new members engage with nutrition tracking. Bundle a free "
        "nutrition consultation with all new premium and elite sign-ups.\n\n"
        "4. Equipment Aging: Three treadmills and two spin bikes are past recommended replacement age. "
        "Budget $18,000 for Q2 equipment refresh.\n\n"
        "5. Member at Risk: Tom Baker (BMI 30.1, Stage 1 hypertension) needs close monitoring. "
        "Nutrition counseling is mandatory per health assessment protocol."
    , styles))

    doc.build(story)
    print(f"  Generated: {path.name}")


def generate_nutrition_guide():
    path = PDF_DIR / "nutrition_program_guide.pdf"
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BulletText", parent=styles["BodyText"], leftIndent=20, bulletIndent=10))
    story = []

    story.append(_heading("Nutrition Program Guide", styles))
    story.append(_body("Version 1.5 | Last Updated: January 15, 2025 | Owner: Rachel Kim, Nutrition Coach", styles))
    story.append(_spacer())

    story.append(_subheading("1. Overview", styles))
    story.append(_body(
        "This guide provides nutritional guidelines for all gym members. Proper nutrition is essential for "
        "achieving fitness goals — exercise alone accounts for only 20-30% of body composition changes, while "
        "nutrition drives 70-80%. All members are encouraged to log their meals in our nutrition tracking system "
        "and attend at least one nutrition consultation per quarter."
    , styles))
    story.append(_spacer())

    story.append(_subheading("2. Daily Macronutrient Targets by Goal", styles))
    macro_data = [
        ["Goal", "Calories", "Protein", "Carbs", "Fat"],
        ["Weight Loss", "TDEE - 500", "1.8g/kg body weight", "30-35% of calories", "25-30% of calories"],
        ["Muscle Building", "TDEE + 300", "2.0g/kg body weight", "40-45% of calories", "20-25% of calories"],
        ["Maintenance", "TDEE", "1.6g/kg body weight", "40-50% of calories", "25-30% of calories"],
        ["Endurance", "TDEE + 200", "1.4g/kg body weight", "50-55% of calories", "20-25% of calories"],
    ]
    t = Table(macro_data, colWidths=[1.3 * inch, 1.2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(_spacer())

    story.append(_subheading("3. Meal Timing", styles))
    story.append(_body(
        "Pre-workout meal: Eat 1-2 hours before exercise. Focus on easily digestible carbs and moderate "
        "protein. Example: banana with peanut butter, or oatmeal with protein powder. Avoid high-fat meals "
        "immediately before training as they slow digestion.\n\n"
        "Post-workout nutrition: Consume protein within 30-60 minutes after training. Target 20-40g protein "
        "plus carbs to replenish glycogen. A protein shake with fruit is ideal for convenience. Whole food "
        "meals are equally effective if consumed within the window.\n\n"
        "Daily meal frequency: 3-5 meals per day, spaced 3-4 hours apart. There is no metabolic advantage "
        "to eating more frequently — choose a pattern that supports adherence. The most important factor is "
        "hitting daily calorie and protein targets."
    , styles))
    story.append(_spacer())

    story.append(_subheading("4. Hydration Guidelines", styles))
    story.append(_body(
        "Minimum daily water intake: 2.5 liters for women, 3.0 liters for men. During exercise, drink "
        "200-300ml every 15-20 minutes. For sessions longer than 60 minutes, consider an electrolyte "
        "supplement. Dehydration of just 2% body weight can reduce exercise performance by up to 25%. "
        "Signs of inadequate hydration: dark urine, fatigue, headache, and decreased workout performance. "
        "Members should track water intake in the nutrition logging system alongside meals."
    , styles))
    story.append(_spacer())

    story.append(_subheading("5. Supplement Recommendations", styles))
    supplement_data = [
        ["Supplement", "Who Needs It", "Recommended Dose", "Timing"],
        ["Whey Protein", "Members not meeting protein targets", "25-30g per serving", "Post-workout"],
        ["Creatine Monohydrate", "Strength-focused members", "5g daily", "Any time, consistent"],
        ["Vitamin D", "All members (especially winter)", "2000-4000 IU daily", "With a meal"],
        ["Omega-3 Fish Oil", "Members with joint issues", "1-2g EPA+DHA daily", "With a meal"],
        ["Electrolytes", "Heavy sweaters, 60+ min sessions", "Per label", "During exercise"],
    ]
    t2 = Table(supplement_data, colWidths=[1.5 * inch, 2 * inch, 1.5 * inch, 1.5 * inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t2)
    story.append(_spacer())

    story.append(_subheading("6. Special Dietary Considerations", styles))
    story.append(_body(
        "Members with dietary restrictions (vegetarian, vegan, gluten-free, allergies) should schedule a "
        "one-on-one consultation with Rachel Kim to create a customized meal plan. Vegetarian and vegan "
        "members should pay special attention to protein sources: legumes, tofu, tempeh, seitan, and "
        "protein supplements can all help meet targets. Members with medical conditions (diabetes, kidney "
        "disease, eating disorders) must provide physician clearance before starting any nutrition program."
    , styles))
    story.append(_spacer())

    story.append(_subheading("7. Nutrition Logging Requirements", styles))
    story.append(_body(
        "All members on a structured nutrition plan must log meals at least 5 days per week. Logs should "
        "include: meal type, food description, estimated calories, and macronutrient breakdown. Water intake "
        "should be logged daily. Trainers review nutrition logs weekly for their personal training clients. "
        "Members consistently exceeding calorie targets by more than 20% will be flagged for a nutrition "
        "counseling session. Logs are reviewed during quarterly health assessments."
    , styles))

    doc.build(story)
    print(f"  Generated: {path.name}")


def setup():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating sample PDFs:")
    generate_safety_guidelines()
    generate_q1_report()
    generate_nutrition_guide()
    print("Done!")


if __name__ == "__main__":
    setup()
